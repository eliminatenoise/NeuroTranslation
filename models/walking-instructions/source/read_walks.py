"""Read the two instructed walks from the original version-8 C3D recordings."""
import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import ezc3d
import numpy as np

from inventory import public_metadata, roster
from prepare_source import ARCHIVE_SHA256, check_archive

HERE = Path(__file__).resolve().parent
DIRECTORY_SHA = "4a0b275527f2c1862ec76bf38f4acd36a0af005ea5703b0a16cb7f9c80077d5b"
MARKERS = ("L_IAS", "R_IAS", "L_IPS", "R_IPS", "R_FCC")
OFFSETS = (10, 20, 30, 40)
FIELDS = {
    "person": ("U7", ()), "condition": ("i4", ()), "repeat": ("i4", ()),
    "offset": ("i4", ()), "cutoff": ("i4", ()), "history_mm": ("f8", (21, 2, 3)),
    "future_delta_mm": ("f8", (2, 3)),
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def encoded(obj):
    return (json.dumps(obj, indent=2, allow_nan=False) + "\n").encode()


def required(ok, msg):
    if not ok:
        raise ValueError(msg)


def strike_frames(raw, frames):
    event = raw["parameters"].get("EVENT", {})
    if not all(k in event for k in ("LABELS", "TIMES", "CONTEXTS")):
        return None
    strikes = []
    for side, label, (minutes, seconds) in zip(
        event["CONTEXTS"]["value"], event["LABELS"]["value"], event["TIMES"]["value"].T, strict=True
    ):
        if side != "Right" or not label.startswith("Foot Strike"):
            continue
        float_index = (60 * float(minutes) + float(seconds)) * 100
        if not np.isfinite(float_index):
            return None
        index = round(float_index)
        if abs(float_index - index) > 1e-4 or not 0 <= index < frames:
            return None
        strikes.append((index, label))
    strikes.sort()
    if len(strikes) < 2 or [label for _, label in strikes[:2]] != ["Foot Strike1", "Foot Strike2"]:
        return None
    first, second = [index for index, _ in strikes[:2]]
    return (first, second) if first < second else None


def window(xyz, valid, t, second):
    u = t + 10
    reasons = []
    if t - 20 < 0 or u >= len(xyz):
        reasons.append("outside_record_extent")
    if u >= second:
        reasons.append("target_reaches_or_follows_next_right_strike")
    if reasons:
        return reasons, None
    if not valid[t - 20:t + 1].all():
        reasons.append("invalid_history_markers")
    if not valid[u].all():
        reasons.append("invalid_target_markers")
    if reasons:
        return reasons, None
    past = xyz[t - 20:t + 1]
    pelvis = past[:, :4].mean(axis=1)
    heading = pelvis[-1, :2] - pelvis[0, :2]
    travel = np.linalg.norm(heading)
    if travel < 10:
        return ["past_pelvis_travel_below_10_mm"], None
    x, y = heading / travel
    basis = np.array([[x, -y, 0.], [y, x, 0.], [0., 0., 1.]])
    history = np.stack((pelvis, past[:, 4]), axis=1)
    future = np.stack((xyz[u, :4].mean(axis=0), xyz[u, 4]))
    return [], ((history - pelvis[-1]) @ basis, (future - history[-1]) @ basis)


def extract(path, trial):
    raw = ezc3d.c3d(str(path))
    points = raw["data"]["points"]
    frames = points.shape[2]
    header = raw["header"]["points"]
    params = raw["parameters"]["POINT"]
    required(header["frame_rate"] == 100 and header["first_frame"] == 0 and header["last_frame"] == frames - 1
             and params["RATE"]["value"].tolist() == [100] and params["UNITS"]["value"] == ["mm"],
             "Original optical clock or units changed")
    trial["stored_point_frames"] = frames
    strikes = strike_frames(raw, frames)
    labels = params["LABELS"]["value"]
    absent = [name for name in MARKERS if labels.count(name) != 1]
    trial["unavailable_or_ambiguous_markers"] = absent
    if absent or strikes is None:
        reasons = (["missing_or_ambiguous_required_marker"] if absent else []) + (
            ["missing_or_ambiguous_right_strikes"] if strikes is None else [])
        trial["windows"] = [{"offset": off, "reasons": reasons} for off in OFFSETS]
        return []
    channels = [labels.index(name) for name in MARKERS]
    xyz = points[:3, channels, :].transpose(2, 1, 0)
    residual = raw["data"]["meta_points"]["residuals"][0, channels, :].T
    valid = np.isfinite(xyz).all(axis=2) & np.isfinite(residual) & (residual >= 0)
    trial["invalid_stored_frames_by_marker"] = dict(zip(MARKERS, (~valid).sum(axis=0).tolist(), strict=True))
    trial["right_strikes_zero_based"] = list(strikes)
    trial["windows"] = []
    rows = []
    for offset in OFFSETS:
        cutoff = strikes[0] + offset
        reasons, result = window(xyz, valid, cutoff, strikes[1])
        trial["windows"].append({"offset": offset, "cutoff": cutoff, "target": cutoff + 10, "reasons": reasons})
        if result is not None:
            rows.append({"person": trial["person"], "condition": trial["condition"], "repeat": trial["repeat"],
                         "offset": offset, "cutoff": cutoff, "history_mm": result[0], "future_delta_mm": result[1]})
    return rows


def summarize(trials, rows):
    people = {t["person"] for t in trials}
    eligible = {c: {r["person"] for r in rows if r["condition"] == c} for c in (4, 5)}
    paired = eligible[4] & eligible[5]
    summary = {"rostered_people": len(people), "people_both": len(paired), "people_C4_only": len(eligible[4] - paired),
               "people_C5_only": len(eligible[5] - paired), "people_neither": len(people - (eligible[4] | eligible[5])),
               "conditions": {}}
    for c in (4, 5):
        selected = [t for t in trials if t["condition"] == c]
        kept = [r for r in rows if r["condition"] == c]
        reasons = Counter(reason for t in selected for w in t["windows"] for reason in w["reasons"])
        primary = [r for r in kept if r["person"] in paired]
        summary["conditions"][str(c)] = {
            "scheduled_trials": len(selected), "catalogued_trials": sum(t["member"] is not None for t in selected),
            "qualified_people": len(eligible[c]), "qualified_trials": len({(r["person"], r["repeat"]) for r in kept}),
            "scheduled_windows": len(selected) * len(OFFSETS), "qualified_windows": len(kept),
            "qualified_windows_by_offset": dict(sorted(Counter(r["offset"] for r in kept).items())),
            "exclusion_reasons_may_overlap": dict(reasons), "paired_primary_trials": len({(r["person"], r["repeat"]) for r in primary}),
            "paired_primary_windows": len(primary),
            "record_wide_invalid_stored_frames_by_marker": {m: sum(t.get("invalid_stored_frames_by_marker", {}).get(m, 0) for t in selected) for m in MARKERS},
        }
    return summary


def build(archive_path, partition, output, expected_hashes):
    check_archive(archive_path)
    directory = (HERE / "directory.json").read_bytes()
    required(sha(directory) == DIRECTORY_SHA, "Directory inventory changed")
    output.mkdir(parents=True, exist_ok=True)
    trials, rows, observed_hashes = [], [], {}
    with ZipFile(archive_path) as archive, TemporaryDirectory(dir=output) as tmp:
        selected = roster(archive)
        required(public_metadata(selected) == json.loads(directory), "Source roster or directory metadata changed")
        temp = Path(tmp) / "walk.c3d"
        for ordinal, person, condition, repeat, member in selected[partition]:
            trial = {"ordinal": ordinal, "person": person, "condition": condition, "repeat": repeat,
                     "member": member.filename if member else None}
            trials.append(trial)
            if member is None:
                trial["windows"] = [{"offset": off, "reasons": ["not_catalogued"]} for off in OFFSETS]
                continue
            blob = archive.read(member)  # ZipFile also checks the stored CRC32.
            digest = sha(blob)
            key = f"{ordinal}:{condition}:{repeat}"
            required(len(blob) == member.file_size, "Original member length differs")
            if expected_hashes is not None:
                required(expected_hashes.get(key) == digest, "Original member SHA-256 differs")
            observed_hashes[key] = digest
            trial["sha256"] = digest
            temp.write_bytes(blob)
            rows.extend(extract(temp, trial))
        if expected_hashes is not None:
            required(observed_hashes == expected_hashes, "Member digest inventory differs")
        arrays = {k: np.asarray([r[k] for r in rows], dtype=dtype).reshape((len(rows), *shape))
                  for k, (dtype, shape) in FIELDS.items()}
        name = f"{partition}.npz"
        temp_npz = Path(tmp) / name
        np.savez_compressed(temp_npz, **arrays)
        receipt = {"archive_sha256": ARCHIVE_SHA256, "partition": partition, "counts": summarize(trials, rows),
                   "npz_sha256": sha(temp_npz.read_bytes()), "versions": {p: version(p) for p in ("numpy", "ezc3d")},
                   "trials": trials}
        temp_json = Path(tmp) / f"{partition}-receipt.json"
        temp_json.write_bytes(encoded(receipt))
        temp_npz.replace(output / name)
        temp_json.replace(output / temp_json.name)
    return receipt, observed_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--partition", choices=("development", "historical"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fit-seal", type=Path)
    parser.add_argument("--fit-seal-sha256")
    args = parser.parse_args()
    if args.partition == "historical":
        required(args.fit_seal and args.fit_seal_sha256 and sha(args.fit_seal.read_bytes()) == args.fit_seal_sha256,
                 "Historical walks require the frozen fit manifest and its verified SHA-256")
    digests = json.loads((HERE / f"{args.partition}-members.json").read_bytes())
    receipt, _ = build(args.archive, args.partition, args.output, digests)
    print(json.dumps(receipt["counts"], indent=2))


if __name__ == "__main__":
    main()
