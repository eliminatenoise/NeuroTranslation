"""Read assessment records, preserving missing versus empty publisher-filtered outputs.

The source catalog describes filtered_data as an optional derivative. All checks
on the raw voltages, common clock, task labels, device and quality flags use
the same criteria as the frozen development qualifier.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from acquire import require, save_json


def grid(m, samples):
    raw = m["raw_data"]
    ats = m["ATS_data"]
    outlier, null, noisy = (m[k] for k in ("outlier_mask", "null_electrodes", "noisy_electrodes"))
    require(raw.shape == ats.shape == outlier.shape == (32, samples), "Disagreeing grid dimensions")
    require(noisy.shape == null.shape == (32,), "Invalid channel mask")
    require(all(np.isin(flags, (0, 1)).all() for flags in (outlier, null, noisy)), "Invalid flag values")
    matrix = m["matrix_description"]
    layout = matrix["electrode_configuration"]
    require(layout.shape == (8, 4) and sorted(layout.flatten().tolist()) == list(range(1, 33)), "Invalid channel map")
    return {
        "raw_shape": list(raw.shape), "raw_dtype": str(raw.dtype), "units_from_catalog": "microvolts",
        "raw_nonfinite": int(raw.size - np.count_nonzero(np.isfinite(raw))),
        "raw_all_zero_channels_1based": (np.flatnonzero(np.all(raw == 0, axis=1)) + 1).tolist(),
        "null_channels_1based": (np.flatnonzero(null) + 1).tolist(),
        "noisy_channels_1based": (np.flatnonzero(noisy) + 1).tolist(),
        "outlier_flag_cells": int(np.count_nonzero(outlier)), "total_cells": raw.size,
        "outlier_or_null_or_noisy_cells": int(np.count_nonzero(outlier | null[:, None] | noisy[:, None])),
        "ats_nonfinite": int(ats.size - np.count_nonzero(np.isfinite(ats))),
        "filtered_data_present": "filtered_data" in m,
        "filtered_data_cells": int(m["filtered_data"].size) if "filtered_data" in m else None,
        "layout_1based": layout.tolist(), "spacing_mm": float(matrix["ied_mm"]),
    }


def qualify(path, receipt):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    require(digest == receipt["member_sha256"] and path.stat().st_size == receipt["member_bytes"],
            "MAT differs from acquisition receipt")
    data = loadmat(path, simplify_cells=True)["data_estructure"]
    experiment = data["experiment_data"]
    frequency = float(experiment["sample_frequency"])
    time = np.asarray(experiment["time_vector"], dtype=np.float64)
    task = np.asarray(experiment["task_vector"])
    n = time.size
    require(frequency == 2000 and time.shape == task.shape == (n,), "Invalid common acquisition clock")
    error = np.abs(np.diff(time) - 1 / frequency)
    require(np.isfinite(time).all() and np.all(error <= 1e-12) and abs(time[0] - 1 / frequency) < 1e-12,
            "Nonuniform or unmatched acquisition clock")
    q = data["quaternions"]["data"].astype(np.float64)
    require(q.shape == (4, n), "Invalid orientation dimensions")
    norms = np.linalg.norm(q, axis=0)
    valid = np.isfinite(norms) & (norms > 0)
    changes = np.flatnonzero(np.any(np.diff(q, axis=1) != 0, axis=0)) + 1
    boundaries = np.r_[0, np.flatnonzero(np.diff(task) != 0) + 1, n]
    labels = {}
    for row in experiment["tasks_description"]:
        code = int(row["task_number"])
        description = str(row["task_description"])
        require(labels.setdefault(code, description) == description, "Conflicting task description")
    seen, counts = np.unique(task, return_counts=True)
    require(set(seen) <= set(labels), "Unmapped active task")
    support = {str(int(code)): {"description": labels[int(code)], "samples": int(count)}
               for code, count in zip(seen, counts, strict=True)}
    inputs = {site: grid(data[site], n) for site in ("brachial_matrix", "lumbar_matrix")}
    return {
        "member": receipt["member"], "member_sha256": digest,
        "stored_hz": frequency, "frames": n, "first_last_time_s": [float(time[0]), float(time[-1])],
        "elapsed_endpoint_span_s": float(time[-1] - time[0]), "largest_clock_step_error_s": float(error.max()),
        "duration_from_frame_count_s": n / frequency, "quaternion_labels": data["quaternions"]["labels"].tolist(),
        "quaternion_shape": list(q.shape), "finite_nonzero_quaternion_frames": int(valid.sum()),
        "adjacent_changes": len(changes), "adjacent_unchanged": n - 1 - len(changes),
        "median_gap_between_changes_samples": float(np.median(np.diff(changes))) if len(changes) > 1 else None,
        "task_codes": support, "task_segments": [{"code": int(task[a]), "begin": int(a), "end_exclusive": int(b)}
                                                 for a, b in zip(boundaries[:-1], boundaries[1:], strict=True)],
        "sites": inputs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="+")
    args = parser.parse_args()
    for path in args.records:
        receipt = json.loads(path.with_suffix(".source.json").read_bytes())
        report = qualify(path, receipt)
        save_json(path.with_suffix(".quality.json"), report)
        print(report["member"], report["frames"], report["finite_nonzero_quaternion_frames"], flush=True)


if __name__ == "__main__":
    main()
