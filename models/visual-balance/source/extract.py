"""Rebuild the event arrays and private QC ledger from the pinned original files."""

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

import numpy as np
from acquire import COMMIT, STAGES, TREE, digest, selection
from scipy.io import loadmat

SCALP = [f"{bank}{i}" for bank in "ABCD" for i in range(1, 33)]
MUSCLES = ("tibialis_anterior", "soleus", "medial_gastrocnemius", "peroneus_longus")
NUISANCE = [
    "L_neck_emg",
    "R_neck_emg",
    "R_horizontal_eog",
    "L_horizontal_eog",
    "L_vertical_eog",
    *(f"{side}_leg_emg_{m}" for side in "LR" for m in MUSCLES),
]
AXES = ("mediolateral", "superiorinferior", "anteriorposterior")
MOTION = [f"Mocap_{body}_{axis}" for body in ("sacrum", "head") for axis in AXES]
CODES = {"rotate_cw": (1, "M_on_CW_WVZ"), "rotate_ccw": (-1, "M_on_CCW_WVZ")}


def tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def require(condition, msg):
    if not condition:
        raise ValueError(msg)


def parse_eeg(path):
    # EEGLAB can save the EEG struct as one variable or each field as a top-level variable.
    fields = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "EEG" in fields:
        eeg = fields["EEG"]
        return {k: getattr(eeg, k) for k in eeg._fieldnames}
    return fields


def channel_info(channels, eeg):
    names = [row["name"] for row in channels]
    require(
        len(names) == int(eeg["nbchan"]) == len(set(names)),
        "channel count or name ambiguity",
    )
    ordered = [(x.labels, x.type, x.units) for x in np.atleast_1d(eeg["chanlocs"])]
    require(
        ordered == [(r["name"], r["type"], r["units"]) for r in channels],
        "BIDS and SET channel identity",
    )
    indices = np.atleast_1d(eeg["etc"].good_chans).ravel()
    require(
        np.all(np.isfinite(indices)) and np.all(indices == np.floor(indices)),
        "nonintegral good_chans",
    )
    good = set(indices.astype(int) - 1)
    require(
        len(good) == len(indices) and good <= set(range(len(names))),
        "invalid good_chans",
    )
    lookup = {name: i for i, name in enumerate(names)}
    for name in SCALP + NUISANCE + MOTION:
        if name in lookup:
            if name in SCALP:
                expected = ("EEG", "microV")
            elif name in MOTION:
                expected = ("MISC", "mm")
            else:
                expected = ("EOG" if name.endswith("_eog") else "EMG", "microV")
            require(
                ordered[lookup[name]][1:] == expected,
                f"unverified type/units for {name}",
            )
    requested = SCALP + NUISANCE
    available = np.array(
        [name in lookup and lookup[name] in good for name in requested], dtype=bool
    )
    sources = [lookup[name] for name, ok in zip(requested, available) if ok]
    motion_ok = all(name in lookup and lookup[name] in good for name in MOTION)
    motion_cols = [lookup[name] for name in MOTION] if motion_ok else []
    missing = [name for name in requested + MOTION if name not in lookup]
    bad = [
        name
        for name in requested + MOTION
        if name in lookup and lookup[name] not in good
    ]
    return available, sources, motion_cols, missing, bad


def extract_person(person, files):
    table = tsv(files["channels.tsv"])
    events = tsv(files["events.tsv"])
    events_meta = json.loads(files["events.json"].read_bytes())
    require(
        events_meta["onset"]["Units"] == "second"
        and CODES.keys() <= events_meta["value"]["Levels"].keys(),
        "event metadata units/codes mismatch",
    )
    original = [row for row in events if row["value"] in CODES]
    side = json.loads(files["eeg.json"].read_bytes())
    eeg = parse_eeg(files["eeg.set"])
    rate, count, nchan = eeg["srate"], int(eeg["pnts"]), int(eeg["nbchan"])
    require(
        rate == side["SamplingFrequency"] == 256 and eeg["trials"] == 1,
        "continuous 256 Hz recording required",
    )
    require(
        math.isclose(side["RecordingDuration"], count / rate, rel_tol=0, abs_tol=1e-8),
        "source durations differ",
    )
    require(
        np.shape(eeg["times"]) == (count,)
        and np.allclose(
            eeg["times"], np.arange(count) * 1000 / rate, rtol=0, atol=1e-8
        ),
        "SET sample clock",
    )
    fdt = files["eeg.fdt"]
    require(
        eeg["data"] == fdt.name and fdt.stat().st_size == 4 * count * nchan,
        "FDT file pointer/shape",
    )
    available, sources, motion_cols, missing, bad = channel_info(table, eeg)
    data = np.memmap(fdt, mode="r", dtype="<f4", shape=(count, nchan))
    by_code = defaultdict(list)
    for index, event in enumerate(np.atleast_1d(eeg["event"])):
        by_code[str(event.type)].append((index, float(event.latency) - 1))
    ticks = [float(row["sample"]) for row in original]
    require(
        all(np.isfinite(ticks)) and all(a < b for a, b in pairwise(ticks)),
        "unordered BIDS rotation clock",
    )
    used = set()
    output = defaultdict(list)
    exclusions, flags_all, primary = {}, Counter(), Counter()
    max_onset_error, max_set_error = 0.0, 0.0
    directions = Counter()
    for ordinal, (row, tick) in enumerate(zip(original, ticks), 1):
        direction, code = CODES[row["value"]]
        flags = []
        matches = [
            (i, abs(t - tick)) for i, t in by_code[code] if abs(t - tick) <= 0.01
        ]
        onset_error = abs(float(row["onset"]) * rate - tick)
        if len(matches) != 1 or matches[0][0] in used or not onset_error <= 0.01:
            flags.append("event_clock")
        else:
            used.add(matches[0][0])
            max_onset_error = max(max_onset_error, onset_error)
            max_set_error = max(max_set_error, matches[0][1])
        cutoff = math.ceil(tick) + 32
        future = cutoff + 32
        if not motion_cols:
            flags.append("markers_unavailable")
        if cutoff - 167 < 0 or future + 8 >= count:
            flags.append("bounds")
        else:
            if motion_cols:
                # Expanded interval is inclusive at both ends; a single zero component is valid.
                motion = np.asarray(
                    data[cutoff - 167 : future + 9, motion_cols], dtype=np.float64
                ).reshape(-1, 2, 3)
                if not np.all(np.isfinite(motion)):
                    flags.append("motion_nonfinite")
                if np.any(np.all(motion == 0, axis=-1)):
                    flags.append("marker_zero")
                if np.any(np.linalg.norm(np.diff(motion, axis=0), axis=-1) > 20.0):
                    flags.append("step_over_20mm")
            signal = np.asarray(
                data[cutoff - 159 : cutoff + 1, sources], dtype=np.float64
            )
            if not np.all(np.isfinite(signal)):
                flags.append("signal_nonfinite")
        if flags:
            flags_all.update(flags)
            primary.update([flags[0]])
            exclusions[ordinal] = flags
            continue
        directions.update([str(direction)])
        binned = signal.reshape(8, 20, signal.shape[1])
        mean = np.zeros((8, len(available)), dtype=np.float64)
        rms = np.zeros_like(mean)
        mean[:, available] = np.mean(binned, axis=1)
        rms[:, available] = np.sqrt(np.mean(np.square(binned), axis=1))
        values = {
            "person": person,
            "event": ordinal,
            "direction": direction,
            "block": min(2, 3 * (ordinal - 1) // len(original)),
            "cutoff": cutoff,
            "motion_mm": motion[8:168] - motion[167],
            "future_delta_mm": motion[199] - motion[167],
            "eeg_mean_uv": mean[:, :128],
            "eeg_rms_uv": rms[:, :128],
            "nuisance_mean_uv": mean[:, 128:],
            "nuisance_rms_uv": rms[:, 128:],
            "eeg_good": available[:128],
            "nuisance_good": available[128:],
        }
        for key, val in values.items():
            output[key].append(val)
    retained = output.get("event", [])
    qc = {
        "original_rotations": len(original),
        "original_by_value": dict(Counter(row["value"] for row in original)),
        "other_BIDS_events": dict(
            Counter(row["value"] for row in events if row["value"] not in CODES)
        ),
        "original_SET_codes": {code: len(rows) for code, rows in by_code.items()},
        "samples": count,
        "channels": nchan,
        "reference": side.get("EEGReference"),
        "filters": side.get("SoftwareFilters"),
        "missing": missing,
        "author_bad": bad,
        "eeg_good": int(available[:128].sum()),
        "nuisance_good": int(available[128:].sum()),
        "retained": len(retained),
        "retained_by_direction": dict(directions),
        "qualified_both_directions": set(directions) == {"1", "-1"},
        "max_accepted_BIDS_onset_error_samples": max_onset_error,
        "max_accepted_SET_latency_error_samples": max_set_error,
        "primary_exclusion_counts": dict(primary),
        "independent_flag_counts": dict(flags_all),
        "excluded_original_ordinals": exclusions,
        "admitted_neighbors_of_excluded_ordinals": [
            i for i in retained if i - 1 in exclusions or i + 1 in exclusions
        ],
    }
    return {key: np.asarray(val) for key, val in output.items()}, qc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    raw = args.work / "raw"
    receipt = json.loads((args.work / f"{args.stage}-files.json").read_bytes())
    records, omissions, selected = selection(args.work / "catalogue", args.stage)
    require(
        (receipt["commit"], receipt["tree"], receipt["stage"], receipt["selected"])
        == (COMMIT, TREE, args.stage, selected),
        "source inventory stage or snapshot",
    )
    require(
        receipt["catalogue_omissions"] == omissions
        and set(receipt["files"]) == {r[0] for r in records},
        "inventory paths differ from versioned catalogue",
    )
    files = defaultdict(dict)
    for name, _, blob in records:
        path = raw / name
        info = receipt["files"][name]
        require(
            info["git_blob"] == blob
            and info["bytes"] == path.stat().st_size
            and digest(path) == info["sha256"],
            f"changed source bytes for {name}",
        )
        if "/" in name:
            files[name.split("/")[0]][name.rsplit("_", 1)[-1]] = path
    desc = json.loads((raw / "dataset_description.json").read_bytes())
    require(
        desc["License"] == "CC0" and desc["DatasetDOI"].endswith("ds003739.v1.0.3"),
        "dataset source identity",
    )
    out, per_person = defaultdict(list), {}
    for person in selected:
        if person in omissions:
            continue
        arrays, qc = extract_person(person, files[person])
        per_person[person] = qc
        for key, arr in arrays.items():
            out[key].append(arr)
    combined = {key: np.concatenate(parts, axis=0) for key, parts in out.items()}
    output = args.work / f"{args.stage}.npz"
    tmp = output.with_suffix(".tmp.npz")
    np.savez(tmp, **combined)
    tmp.replace(output)
    flags, primary = Counter(), Counter()
    for qc in per_person.values():
        flags.update(qc["independent_flag_counts"])
        primary.update(qc["primary_exclusion_counts"])
    totals = {
        "catalogue_selected": len(selected),
        "catalogue_omissions": len(omissions),
        "people_represented": len(np.unique(combined.get("person", []))),
        "people_with_both_directions": sum(
            q["qualified_both_directions"] for q in per_person.values()
        ),
        "original_rotations": sum(q["original_rotations"] for q in per_person.values()),
        "admitted": len(combined.get("event", [])),
        "independent_flag_counts": dict(flags),
        "primary_exclusions": dict(primary),
        "admitted_neighbors_of_excluded_ordinals": sum(
            len(q["admitted_neighbors_of_excluded_ordinals"])
            for q in per_person.values()
        ),
    }
    document = {
        "stage": args.stage,
        "npz_sha256": digest(output),
        "files_receipt_sha256": digest(args.work / f"{args.stage}-files.json"),
        "extraction_code_sha256": digest(Path(__file__)),
        "arrays": {
            k: {"shape": list(v.shape), "dtype": str(v.dtype)}
            for k, v in combined.items()
        },
        "catalogue_omissions": omissions,
        "totals": totals,
        "per_person": per_person,
    }
    (args.work / f"{args.stage}-qc.json").write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
