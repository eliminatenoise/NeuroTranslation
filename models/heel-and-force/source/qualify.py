"""Extract the two stored 100-ms outcomes on one prespecified partition of C2 walks."""
import argparse
from collections import Counter, defaultdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import tempfile
import zipfile
import zlib

import ezc3d
import numpy as np

from plate_contacts import ContactTable
from prepare_source import ARCHIVE_BYTES, ARCHIVE_SHA256, SUPPLEMENT_SHA256, check_archive
from right_contact import MUSCLES, point_on_platform, right_contact_geometry, right_emg_slice
from roster import build, supplement_manifest

HERE = Path(__file__).resolve().parent
PARTITIONS = {"train": "development", "assessment": "historic-assessment", "later-repeats": "later-repeats"}
LATER_HASH = "f61604d456a4cb9973c6fb0a2e702b1b5839a510de2540aea6d9a3c32dd6a068"
ORIGINAL_HASH = "94fe19bcb70fdc3c171754368ed432534baae5b14e39e76e966cd6ae58e4ccdf"
MARKERS = ("R_FCC", "R_FM2")
OFFSETS = (14, 24, 34, 44)
FIELDS = {"person": ("U7", ()), "repeat": ("i4", ()), "offset": ("i4", ()), "cutoff": ("i4", ()),
          "marker_mm": ("f8", (24, 2, 3)), "emg_uv": ("f8", (4, 8)), "heel_delta_mm": ("f8", (3,)),
          "force_n": ("f8", ()), "privileged_force_n": ("f8", (2,))}


def canonical(obj):
    return (json.dumps(obj, indent=2, allow_nan=False) + "\n").encode()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def stance_times(raw):
    """First named right stride, with exactly one intervening right foot-off."""
    params = raw["parameters"]["EVENT"]
    right = [(label, float(60 * minute + sec)) for side, label, (minute, sec) in
             zip(params["CONTEXTS"]["value"], params["LABELS"]["value"], params["TIMES"]["value"].T, strict=True)
             if side == "Right"]
    strikes = [(s, t) for s, t in right if s.startswith("Foot Strike")]
    first = [t for s, t in strikes if s == "Foot Strike1"]
    second = [t for s, t in strikes if s == "Foot Strike2"]
    if len(first) != 1 or len(second) != 1 or not np.isfinite([t for _, t in right]).all():
        return None
    start, end = first[0], second[0]
    last_time = (raw["data"]["points"].shape[-1] - 1) / 100
    if not -0.00001 <= start < end <= last_time + 0.00001:
        return None
    if sum(start < stamp <= end for _, stamp in strikes) != 1:
        return None
    off = [stamp for kind, stamp in right if kind == "Foot Off" and start < stamp < end]
    if len(off) != 1:
        return None
    return start, off[0], end


def verify_source_fields(raw, plate):
    params, data, hdr = raw["parameters"], raw["data"], raw["header"]
    n = data["points"].shape[-1]
    require(hdr["points"]["frame_rate"] == 100 and hdr["analogs"]["frame_rate"] == 1500 and
            hdr["points"]["first_frame"] == 0 and hdr["points"]["last_frame"] == n - 1 and
            data["analogs"].shape[-1] == 15 * n, "Unexpected C3D cropped clock or extent")
    require(params["POINT"]["UNITS"]["value"] == ["mm"] and
            params["FORCE_PLATFORM"]["TYPE"]["value"].ravel().tolist() == [2, 2],
            "Unexpected marker units or platform types")
    names = params["ANALOG"]["LABELS"]["value"]
    units = params["ANALOG"]["UNITS"]["value"]
    force_label = f"Fz{plate}"
    require(names.count(force_label) == 1, "Force channel identity")
    fcol = names.index(force_label)
    platform = data["platform"][plate - 1]
    require(params["FORCE_PLATFORM"]["CHANNEL"]["value"][2, plate - 1] == fcol + 1
            and units[fcol] == platform["unit_force"] == "N", "Force channel map or units")
    corners = platform["corners"]
    require(np.array_equal(corners, params["FORCE_PLATFORM"]["CORNERS"]["value"][:, :, plate - 1]),
            "Assigned corners differ between calibration and metadata")
    a, b, _, d = corners.T
    normal = np.cross(a - b, a - d)
    require(np.isfinite(normal).all() and np.linalg.norm(normal) > 0 and
            np.allclose(normal / np.linalg.norm(normal), [0., 0., -1.], atol=1e-7),
            "Force plate normal")
    force = platform["force"][2]
    require(np.array_equal(force, -data["analogs"][0, fcol], equal_nan=True), "Scaled force orientation")
    point_labels = params["POINT"]["LABELS"]["value"]
    require(all(point_labels.count(k) == 1 for k in MARKERS), "Marker identities")
    ids = [point_labels.index(k) for k in MARKERS]
    xyz = data["points"][:3, ids, :].transpose(2, 1, 0)
    residual = data["meta_points"]["residuals"][0, ids, :].T
    return xyz, residual, force, corners


def extract_trial(path, metadata, contact):
    raw = ezc3d.c3d(str(path), extract_forceplat_data=True)
    plate = contact["right_plate"]
    xyz, residual, force, corners = verify_source_fields(raw, plate)
    times = stance_times(raw)
    if times is None:
        metadata["trial_gate"] = "right_stride_or_intervening_off_not_unique_in_extent"
        return []
    first, off, second = times
    geometry = right_contact_geometry(raw, plate)
    strike = geometry["point_index"]
    require(strike == round(first * 100), "Strike frame mismatch")
    metadata.update(physical_first_last_point_frames=[1, len(xyz)], zero_based_strike=strike,
                    right_strike_off_next_strike_s=[first, off, second], strike_geometry=geometry,
                    assigned_corners_mm=corners.T.tolist())
    if not geometry["both_on_plate"]:
        metadata["trial_gate"] = "strike_marker_invalid_or_outside_assigned_platform"
        return []
    metadata["trial_gate"] = "four_fixed_offsets_examined"
    rows = []
    for offset in OFFSETS:
        t = strike + offset
        u = t + 10
        center = 15 * t + 7
        stop = center + 1
        target_first = 15 * u
        target_stop = target_first + 15
        window = {"offset": offset, "cutoff": t, "target": u, "reasons": []}
        metadata["windows"].append(window)
        reasons = window["reasons"]
        if t - 23 < 0 or stop - 360 < 0 or u >= len(xyz):
            reasons.append("outside_record_extent")
        if not first <= (target_first - 7) / 1500 <= (target_stop - 8) / 1500 < off:
            reasons.append("future_force_block_outside_annotated_right_contact")
        if reasons:
            continue
        past = xyz[t - 23:t + 1]
        past_res = residual[t - 23:t + 1]
        if not (np.isfinite(past).all() and np.isfinite(past_res).all() and (past_res >= 0).all()):
            reasons.append("invalid_past_marker_history")
        if not (np.isfinite(xyz[u]).all() and np.isfinite(residual[u]).all() and (residual[u] >= 0).all()
                and all(point_on_platform(p[:2], corners) for p in xyz[u])):
            reasons.append("invalid_or_off_platform_target_markers")
        volts, valid = right_emg_slice(raw, stop - 360, stop)
        if not valid.all():
            reasons.append("incomplete_past_EMG")
        future_force = force[target_first:target_stop]
        if not np.isfinite(future_force).all():
            reasons.append("invalid_force_target")
        if reasons:
            continue
        rms = np.sqrt(np.mean(np.square(volts.reshape(4, 90, len(MUSCLES))), axis=1)) * 1e6
        privileged = np.array([force[stop - 15:stop].mean(), force[stop - 165:stop - 150].mean()])
        window["privileged_finite"] = np.isfinite(privileged).tolist()
        rows.append({"person": metadata["person"], "repeat": metadata["repeat"], "offset": offset, "cutoff": t,
                     "marker_mm": past, "emg_uv": rms, "heel_delta_mm": xyz[u, 0] - xyz[t, 0],
                     "force_n": future_force.mean(), "privileged_force_n": privileged})
    return rows


def summarize(trials, rows):
    people = {t["person"] for t in trials}
    kept_repeats = defaultdict(set)
    by_trial = Counter((r["person"], r["repeat"]) for r in rows)
    strata = defaultdict(set)
    for r in rows:
        kept_repeats[r["person"]].add(r["repeat"])
        strata[r["person"], r["offset"]].add(r["repeat"])
    reasons = [w["reasons"] for t in trials for w in t["windows"]]
    return {"candidates_people": len(people), "candidates_trials": len(trials),
            "candidates_offsets_all_trials": len(OFFSETS) * len(trials),
            "trial_gate_counts": dict(Counter(t["trial_gate"] for t in trials)),
            "offsets_not_examined_due_to_trial_gate": 4 * sum(not t["windows"] for t in trials),
            "examined_offsets": len(reasons), "kept_offsets": len(rows),
            "examined_first_reason_counts": dict(Counter(w[0] if w else "kept" for w in reasons)),
            "examined_reason_counts_can_overlap": dict(Counter(v for w in reasons for v in w)),
            "people_with_kept_rows": len(kept_repeats), "trials_with_kept_rows": len(by_trial),
            "kept_rows_by_offset": dict(Counter(r["offset"] for r in rows)),
            "people_by_number_of_kept_repeats": dict(Counter(len(kept_repeats.get(p, ())) for p in people)),
            "trials_by_number_of_kept_rows": dict(Counter(by_trial[t["person"], t["repeat"]] for t in trials)),
            "rows_with_distinct_repeat_same_person_offset": sum(len(strata[r["person"], r["offset"]]) > 1 for r in rows),
            "rows_with_adjacent_repeat_same_person_offset": sum(any(abs(rep - r["repeat"]) == 1 for rep in
                strata[r["person"], r["offset"]]) for r in rows),
            "rows_with_complete_privileged_force": sum(bool(np.isfinite(r["privileged_force_n"]).all()) for r in rows)}


def table_rows(rows):
    return {key: np.asarray([r[key] for r in rows], dtype=dtype).reshape((len(rows),) + shape)
            for key, (dtype, shape) in FIELDS.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Original Figshare v8 ZIP")
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--partition", required=True, choices=list(PARTITIONS))
    parser.add_argument("--staged", type=Path, help="Reuse verified original-member C3Ds in this directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fit-seal", type=Path, help="Joint manifest for both frozen fit families")
    parser.add_argument("--fit-seal-sha256")
    args = parser.parse_args()
    if args.partition != "train":
        require(args.fit_seal and args.fit_seal_sha256 and sha(args.fit_seal.read_bytes()) == args.fit_seal_sha256,
                "Both model families must be frozen before either assessment partition")
    original_blob = (HERE / "original-members.json").read_bytes()
    require(sha(original_blob) == ORIGINAL_HASH, "Original member checksum list changed")
    original = json.loads(original_blob)
    if args.staged and args.partition not in original:
        parser.error("Only previously verified original partitions may use staged files")
    require(sha(args.supplement.read_bytes()) == SUPPLEMENT_SHA256, "Wrong supplementary DOCX")
    table = ContactTable(args.supplement)
    require(args.archive.stat().st_size == ARCHIVE_BYTES, "Wrong archive size")
    if not args.staged:
        check_archive(args.archive)
    args.output.mkdir(parents=True, exist_ok=True)
    stem = PARTITIONS[args.partition] + "-v1"
    trials, rows = [], []
    with zipfile.ZipFile(args.archive) as archive, tempfile.TemporaryDirectory(dir=args.output) as work:
        groups, split_payload = build(archive, table)
        require(sha(canonical(supplement_manifest(groups["later-repeats"], table))) == LATER_HASH,
                "Later-repeats directory or Table 2 metadata changed")
        for member in groups[args.partition]:
            name = Path(member["name"]).name
            person, condition, repeat = Path(name).stem.split("_")
            require(condition == "C2" and int(repeat) == member["repeat"] and len(person) == 7, "Member identity")
            contact = table.contacts(name)
            record = {"source_member": member, "person": person, "repeat": int(repeat), "contact": contact, "windows": []}
            trials.append(record)
            if contact["code"] not in ("12", "21"):
                record["trial_gate"] = "unknown_or_non_distinct_table2_code"
                continue
            if args.staged:
                source = args.staged / name
                require(not source.is_symlink() and source.resolve().parent == args.staged.resolve(), "Staging escape")
                blob = source.read_bytes()
            else:
                blob = archive.read(member["name"])
                source = Path(work) / name
                source.write_bytes(blob)
            digest = sha(blob)
            require(len(blob) == member["size"] and f"{zlib.crc32(blob):08x}" == member["crc32"], "Member integrity")
            if args.partition in original:
                require(digest == original[args.partition][f"{member['ordinal']}:{member['repeat']}"], "Member SHA256 mismatch")
            record["decoded_member_sha256"] = digest
            rows.extend(extract_trial(source, record, contact))
    arrays = table_rows(rows)
    bundle_path = args.output / f"{stem}.npz"
    # NumPy stores deterministic ZIP timestamps. Write complete bytes before publishing the result.
    with tempfile.NamedTemporaryFile(dir=args.output, suffix=".npz", delete=False) as handle:
        tmp = Path(handle.name)
        np.savez_compressed(handle, **arrays)
    tmp.replace(bundle_path)
    receipt = {"version": 1, "partition": args.partition, "dataset": "10.6084/m9.figshare.7734767.v8",
               "archive_sha256": ARCHIVE_SHA256, "supplement_sha256": SUPPLEMENT_SHA256,
               "original_split_sha256": sha(split_payload), "supplemental_selection_sha256": LATER_HASH,
               "fit_seal_sha256": args.fit_seal_sha256 if args.partition != "train" else None,
               "source_files_sha256": {p.name: sha(p.read_bytes()) for p in sorted(HERE.glob("*"))
                     if p.is_file() and (p.suffix == ".py" or p.name in ("protocol.json", "original-members.json", "requirements.txt"))},
               "dependencies": {name: version(name) for name in ("ezc3d", "numpy", "c3d")},
               "arrays_sha256": sha(bundle_path.read_bytes()),
               "arrays": {k: {"dtype": str(v.dtype), "shape": list(v.shape)} for k, v in arrays.items()},
               "summary": summarize(trials, rows), "trials": trials}
    (args.output / f"{stem}-receipt.json").write_bytes(canonical(receipt))
    print(json.dumps(receipt["summary"], indent=2))


if __name__ == "__main__":
    main()
