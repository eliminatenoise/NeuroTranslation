"""Run the prospective Lucchetti HM analysis on its two pinned v1 assets."""

import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
from time import perf_counter

import numpy as np
import scipy
from scipy.io import loadmat
from threadpoolctl import threadpool_info

from baseline import Design, Trial, evaluate


HERE = Path(__file__).resolve().parent
VIDEO_HZ = 125
EMG_HZ = 1000
RATIO = EMG_HZ // VIDEO_HZ
CHANNELS = (
    "DELPOS", "DELML", "DELANT", "TRICP", "BICEP", "FLXCRR",
    "FLXDIGS", "EXTCRR", "EXTDIGC", "ABDPOL", "FDORS", "ADDMIG",
)


def load_trials(file_path, subject, spec):
    if file_path.name != f"{subject}.mat" or file_path.stat().st_size != spec["bytes"]:
        raise ValueError(f"{subject} filename or length differs from its pinned v1 source")
    payload = file_path.read_bytes()
    if len(payload) != spec["bytes"] or sha256(payload).hexdigest() != spec["sha256"]:
        raise ValueError(f"{subject} file does not match its pinned v1 source")

    data = loadmat(io.BytesIO(payload), simplify_cells=True, variable_names=("s",))["s"]
    if (data["KinFreq"], data["EmgFreq"]) != (VIDEO_HZ, EMG_HZ):
        raise ValueError(f"{subject} nominal sample rates changed")
    tasks = data["DataULdom"]
    if len(tasks) != 6:
        raise ValueError(f"{subject} dominant-arm task structure changed")

    # Task and angle positions are pinned by the source evidence for these byte
    # identities. The author labels are stored as MATLAB MCOS strings.
    task = tasks[3]
    angles = task["Angles"]
    emg = task["EMG"]
    events = task["Events"]
    starts, stops = np.asarray(events["Start"]), np.asarray(events["End"])
    if (
        angles.shape != tuple(spec["angle_shape"])
        or emg.shape != tuple(spec["emg_shape"])
        or starts.tolist() != spec["starts"]
        or stops.tolist() != spec["stops"]
    ):
        raise ValueError(f"{subject} HM structure or movement intervals differ from the source contract")
    if len(starts) != 5 or len(stops) != 5 or not (stops[:-1] < starts[1:]).all():
        raise ValueError(f"{subject} requires five nonoverlapping ordered source movements")
    if not (starts >= 1).all() or not (starts <= stops).all() or stops[-1] > angles.shape[1]:
        raise ValueError(f"{subject} movement interval outside the kinematic grid")

    trials = []
    for index, (first, last) in enumerate(zip(starts, stops, strict=True), start=1):
        angle_start, angle_end = int(first) - 1, int(last) - 1
        emg_start, emg_end = RATIO * angle_start, RATIO * angle_end
        if emg_end >= emg.shape[1]:
            raise ValueError(f"{subject} movement {index} extends beyond the EMG grid")
        trials.append(Trial(
            subject=subject,
            session=f"{subject}.mat:DataULdom",
            trial=f"HM:{index}",
            source_trial=f"{spec['sha256']}:HM:{index}",
            channel_names=CHANNELS,
            emg_seconds=np.arange(emg_start, emg_end + 1) / EMG_HZ,
            emg=emg[:, emg_start:emg_end + 1].T,
            target_seconds=np.arange(angle_start, angle_end + 1) / VIDEO_HZ,
            target=angles[6, angle_start:angle_end + 1],
            target_start_row=angle_start,
            emg_start_row=emg_start,
        ))
    return trials


def run(hs01, hs02):
    start = perf_counter()
    lock_bytes = (HERE / "ASSETS.json").read_bytes()
    assets = json.loads(lock_bytes)
    design_bytes = (HERE / "DESIGN.json").read_bytes()
    design = json.loads(design_bytes)
    paths = {"HS01": hs01, "HS02": hs02}
    if set(assets["subjects"]) != set(paths):
        raise ValueError("asset lock must contain exactly HS01 and HS02")
    if len({spec["sha256"] for spec in assets["subjects"].values()}) != len(paths):
        raise ValueError("the two source assets must be distinct")
    if design["split"] != {
        "train_reference": ["HS01"], "development": ["HS02"],
        "reserved_metadata_only": ["HS03"],
    }:
        raise ValueError("split does not match the fixed run scope")
    trials = []
    durations = {}
    for subject, path in paths.items():
        load_start = perf_counter()
        trials.extend(load_trials(path, subject, assets["subjects"][subject]))
        durations[f"{subject}_verify_parse_extract"] = perf_counter() - load_start

    score_begin = perf_counter()
    result = evaluate(trials, ("HS01",), ("HS02",), Design(**design["design"]), VIDEO_HZ)
    durations["features_fit_and_score"] = perf_counter() - score_begin
    result["development_subjects"] = result.pop("test_subjects")
    for row in result["support"]:
        row["partition"] = {"train": "train_reference", "test": "development"}[row["partition"]]
    result["source_assets"] = assets
    result["interpretation"] = {
        "target": "stored optically derived ElbowFlx in degrees",
        "development_subject": "one separate healthy development subject, HS02",
        "interpretation": "offline stored coordinate only; physical clock offset and target availability delay unverified",
        "confirmation_asset_HS03_opened": False,
    }
    result["file_denominators"] = {}
    for subject in paths:
        rows = [row for row in result["support"] if row["subject"] == subject]
        counts = {
            field: sum(row[field] for row in rows)
            for field in ("scored_rows", "missing_target_rows", "unavailable_emg_history_rows", "target_rows_total")
        }
        counts["outside_annotated_movements"] = (
            assets["subjects"][subject]["angle_shape"][1] - counts["target_rows_total"]
        )
        result["file_denominators"][subject] = counts
    read_affinity = getattr(os, "sched_getaffinity", None)
    result["run_evidence"] = {
        "design_sha256": sha256(design_bytes).hexdigest(),
        "asset_lock_sha256": sha256(lock_bytes).hexdigest(),
        "software_sha256": {
            name: sha256((HERE / name).read_bytes()).hexdigest() for name in ("run.py", "baseline.py")
        },
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "affinity": sorted(read_affinity(0)) if read_affinity else None,
        "thread_pools": [
            {**pool, "filepath": Path(pool["filepath"]).name} for pool in threadpool_info()
        ],
        "stages_seconds": durations,
        "elapsed_run_seconds": perf_counter() - start,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hs01", type=Path, required=True)
    parser.add_argument("--hs02", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="write new UTF-8 JSON file instead of stdout")
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error(f"output file already exists: {args.output}")
    output = json.dumps(run(args.hs01, args.hs02), indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    main()
