"""Run the frozen offline EEG-to-palm-position development comparison."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter

import h5py
import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits


ROOT = Path(__file__).resolve().parent
DESIGN_SHA256 = "f6ec056e747fb3045ca5ed5a380fd31d2ce818ed6529a1fb2e3cfe0f69fd164e"
NATIVE_GRID_SHA256 = "5da46fcf84ca15172ff921bac7d71da825533ca0d286c6abeac5e86f160b77ee"
CHANNEL_EVIDENCE_SHA256 = "6a867167815524f764a5693c9604c67f8c542d45f05a5f0cb05efa35b7721a6b"
REQUIRED_FIELDS = ("EEG", "t_ms", "x_mm", "lm_trial", "eeg_seg_idx")


class GateError(ValueError):
    """Input or source evidence outside the frozen study contract."""


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_frozen_design():
    path = ROOT / "DESIGN.json"
    if sha256(path) != DESIGN_SHA256:
        raise GateError("Study design differs from the frozen SHA-256")
    return json.loads(path.read_text())


def verify_assets(design, paths):
    for role, path in paths.items():
        expected = design["roles"][role]
        if path.name != expected["basename"] or sha256(path) != expected["sha256"]:
            raise GateError(f"{role} requires the exact named release asset and frozen SHA-256")


def read_channel_gate(design, schema):
    path = ROOT / "CHANNEL-EVIDENCE.json"
    if sha256(path) != CHANNEL_EVIDENCE_SHA256:
        raise GateError("Channel evidence differs from its frozen SHA-256")
    evidence = json.loads(path.read_text())
    if evidence["status"] != "supported_for_named_central_rows":
        raise GateError(evidence["decision"])
    if evidence["design_sha256"] != DESIGN_SHA256:
        raise GateError("Channel source evidence is bound to a different design")
    for role, expected in design["roles"].items():
        mapping = evidence["roles"][role]
        if (
            mapping["asset_sha256"] != expected["sha256"]
            or [row["name"] for row in mapping["rows"]] != design["sampling"]["channels"]
            or len({row["index_zero_based"] for row in mapping["rows"]}) != 3
            or any(row["type"] != "EEG" for row in mapping["rows"])
            or any(row["index_zero_based"] not in range(mapping["n_channels"]) for row in mapping["rows"])
            or schema[role]["n_channels"] != mapping["n_channels"]
        ):
            raise GateError(f"{role} channel evidence does not match the exact ordered scalp EEG inputs")
    return evidence


def reference_columns(handle):
    group = handle["OUT"]
    if not isinstance(group, h5py.Group):
        raise GateError("Expected the release OUT struct group")
    columns = {}
    for field in REQUIRED_FIELDS:
        dataset = group[field]
        if (
            not isinstance(dataset, h5py.Dataset)
            or len(dataset.shape) != 2
            or dataset.shape[1] != 1
            or h5py.check_dtype(ref=dataset.dtype) is not h5py.Reference
        ):
            raise GateError(f"Malformed or unsupported HDF5 reference column {field}")
        columns[field] = dataset[:, 0]
    counts = {len(column) for column in columns.values()}
    if len(counts) != 1 or counts == {0}:
        raise GateError("OUT reference columns must have the same nonzero number of trials")
    return columns


def trials(handle):
    columns = reference_columns(handle)
    for references in zip(*columns.values(), strict=True):
        if any(not reference for reference in references):
            raise GateError("Missing HDF5 trial object reference")
        datasets = {name: handle[reference] for name, reference in zip(columns, references, strict=True)}
        for field, dataset in datasets.items():
            if not isinstance(dataset, h5py.Dataset) or dataset.dtype.kind not in "fiu":
                raise GateError(f"Expected real numeric HDF5 dataset for {field}")
        yield datasets


def matrix_shape(datasets):
    eeg = datasets["EEG"]
    clock = datasets["t_ms"]
    palm = datasets["x_mm"]
    if len(eeg.shape) != 2:
        raise GateError("Release EEG must be a two-axis matrix")
    n_samples, n_channels = eeg.shape
    if n_samples == 0 or n_channels == 0 or clock.shape != (1, n_samples) or palm.shape != (n_samples, 1):
        raise GateError("EEG, t_ms and x_mm dimensions disagree with the release HDF5 layout")
    if any(datasets[field].shape != (1, 1) for field in ("lm_trial", "eeg_seg_idx")):
        raise GateError("Expected one scalar for each trial identity field")
    return n_samples, n_channels


def inspect_schema(path):
    """Read HDF5 reference geometry only. Signal and trajectory samples are unopened."""
    with h5py.File(path, "r") as handle:
        geometry = [matrix_shape(trial) for trial in trials(handle)]
        channel_counts = {channels for _, channels in geometry}
        if len(channel_counts) != 1:
            raise GateError("EEG channel count varies within a run")
        return {
            "released_trials": len(geometry),
            "n_channels": next(iter(channel_counts)),
            "embedded_out_fields": list(handle["OUT"]),
            "top_level_groups": list(handle),
            "storage": "HDF5 EEG samples × channels; t_ms row; x_mm column",
        }


def nominal_groups(sampling):
    score_times = np.array(sampling["score_times_ms"])
    step = sampling["sample_step_ms"]
    bins = [np.arange(start, stop, step) for start, stop in sampling["feature_bins_ms_relative_to_target"]]
    return score_times, [score_times[:, None] + offsets for offsets in bins]


def clock_indices(clock, sampling, native_grid):
    step = sampling["sample_step_ms"]
    tolerance = sampling["grid_error_tolerance_ms"]
    if not np.isfinite(clock).all() or not np.all(np.diff(clock) > 0):
        return None, "clock_nonfinite_or_nonincreasing"
    origin = 0.0
    if native_grid:
        index = np.searchsorted(clock, 0, side="left")
        if index == 0 or index == len(clock) or clock[index] >= step:
            return None, "no_native_anchor_bracketing_event"
        origin = float(clock[index])
    relative_clock = clock - origin
    ticks = np.rint(relative_clock / step)
    if np.any(np.abs(relative_clock - ticks * step) > tolerance) or not np.all(np.diff(ticks) == 1):
        return None, "clock_not_continuous_on_selected_grid"
    score_times, feature_times = nominal_groups(sampling)
    target = score_times // step - int(ticks[0])
    features = [group // step - int(ticks[0]) for group in feature_times]
    if any(indices.min() < 0 or indices.max() >= len(clock) for indices in [target, *features]):
        return None, "analysis_time_support_unavailable"
    return (target, features, origin), None


def materialize_window(eeg, palm, target_indices, feature_indices):
    bins = [eeg[indices] for indices in feature_indices]
    target = palm[target_indices]
    if any(not np.isfinite(bin_samples).all() for bin_samples in bins):
        return None, "nonfinite_feature"
    if not np.isfinite(target).all():
        return None, "nonfinite_target"
    features = np.column_stack([bin_samples.mean(axis=1, dtype=np.float64) for bin_samples in bins])
    return (features, target), None


def source_index(dataset, minimum):
    value = dataset[0, 0]
    if not np.isfinite(value) or value < minimum or value != int(value):
        raise GateError("Invalid trial or segment identity")
    return int(value)


def read_windows(path, mapping, sampling, native_grid):
    row_indices = [row["index_zero_based"] for row in mapping["rows"]]
    sorted_rows = sorted(row_indices)
    inverse_order = [sorted_rows.index(row) for row in row_indices]
    windows = []
    exclusions = {}
    origin_counts = {}
    actual_target_range = []
    observed_trials = set()
    observed_segments = set()
    with h5py.File(path, "r") as handle:
        for trial in trials(handle):
            matrix_shape(trial)
            trial_id = source_index(trial["lm_trial"], minimum=0)
            segment_id = source_index(trial["eeg_seg_idx"], minimum=1)
            if trial_id in observed_trials or segment_id in observed_segments:
                raise GateError("Duplicate trial or segment identity in the released run")
            observed_trials.add(trial_id)
            observed_segments.add(segment_id)
            clock = trial["t_ms"][0, :]
            indices, reason = clock_indices(clock, sampling, native_grid)
            if reason is None:
                # The data API opens only these named columns. Feature materialization
                # can use only strictly prior samples in the current trial.
                eeg = trial["EEG"][:, sorted_rows][:, inverse_order]
                target_indices, feature_indices, origin = indices
                windows_and_target, reason = materialize_window(
                    eeg, trial["x_mm"][:, 0], target_indices, feature_indices
                )
            if reason is not None:
                exclusions[reason] = exclusions.get(reason, 0) + 1
                continue
            features, target = windows_and_target
            windows.append((trial_id, features, target))
            origin_counts[origin] = origin_counts.get(origin, 0) + 1
            actual_target_range.extend((float(clock[target_indices[0]]), float(clock[target_indices[-1]])))
    counts = {
        "released_trials": len(observed_trials),
        "eligible_trials": len(windows),
        "excluded_trials": exclusions,
        "eligible_anchor_lag_from_event_ms_counts": origin_counts,
        "eligible_target_times_relative_to_event_ms_range": (
            [min(actual_target_range), max(actual_target_range)] if actual_target_range else None
        ),
    }
    if not windows:
        return None, None, counts
    windows.sort(key=lambda row: row[0])
    _, features, targets = zip(*windows, strict=True)
    return np.stack(features), np.stack(targets), counts


def fit_ridge(features, target, alpha):
    train_x = features.reshape(-1, features.shape[-1])
    train_y = target.ravel()
    center = train_x.mean(axis=0)
    standard_deviation = train_x.std(axis=0)
    scale = np.where(standard_deviation == 0, 1.0, standard_deviation)
    standardized = (train_x - center) / scale
    target_mean = train_y.mean()
    penalties = alpha * np.eye(standardized.shape[1])
    weights = np.linalg.solve(standardized.T @ standardized + penalties, standardized.T @ (train_y - target_mean))
    return center, scale, weights, target_mean


def predict_ridge(features, model):
    center, scale, weights, target_mean = model
    standardized = (features - center) / scale
    return standardized @ weights + target_mean


def aggregate(prediction, target):
    residuals = prediction - target
    per_trial_mse = np.mean(residuals**2, axis=1)
    result = {"rmse_mm": float(np.sqrt(per_trial_mse.mean())), "signed_error_mm": float(residuals.mean())}
    return result, per_trial_mse


def paired_comparison(ridge_mse, reference_mse):
    delta = np.sqrt(ridge_mse.mean()) - np.sqrt(reference_mse.mean())
    comparisons = [
        np.sqrt(np.delete(ridge_mse, index).mean()) - np.sqrt(np.delete(reference_mse, index).mean())
        for index in range(len(ridge_mse))
    ]
    return {
        "ridge_minus_baseline_rmse_mm": float(delta),
        "dev_trials_with_lower_ridge_mse": int(np.count_nonzero(ridge_mse < reference_mse)),
        "leave_one_dev_trial_out_delta_range_mm": [float(min(comparisons)), float(max(comparisons))],
    }


def score(train, dev, alpha):
    train_features, train_target, train_counts = train
    dev_features, dev_target, dev_counts = dev
    ridge = fit_ridge(train_features, train_target, alpha)
    train_template = train_target.mean(axis=0)
    train_mean = train_target.mean()
    report = {}
    for role, features, target, counts in (
        ("TRAIN", train_features, train_target, train_counts),
        ("DEV", dev_features, dev_target, dev_counts),
    ):
        predictions = {
            "ridge": predict_ridge(features, ridge),
            "train_mean": train_mean,
            "train_time_template": train_template,
        }
        if role == "DEV":
            predictions["ridge_shifted_dev_trials"] = np.roll(predictions["ridge"], -1, axis=0)
        measures = {name: aggregate(prediction, target) for name, prediction in predictions.items()}
        report[role] = {
            **counts,
            "scored_samples": int(target.size),
            "metrics": {name: result for name, (result, _) in measures.items()},
        }
        if role == "DEV":
            ridge_mse = measures["ridge"][1]
            comparisons = {
                name: paired_comparison(ridge_mse, measures[name][1])
                for name in ("train_mean", "train_time_template")
            }
            report["dev_primary"] = {
                "comparisons": comparisons,
                "ridge_beat_both": all(item["ridge_minus_baseline_rmse_mm"] < 0 for item in comparisons.values()),
            }
    return report


def run(paths, check_source, native_grid):
    start = perf_counter()
    design = read_frozen_design()
    verify_assets(design, paths)
    schema = {role: inspect_schema(path) for role, path in paths.items()}
    schema_seconds = perf_counter() - start
    report = {
        "design_sha256": DESIGN_SHA256,
        "analysis": "native_grid" if native_grid else "exact_event_grid",
        "HDF5_schema": schema,
    }
    if native_grid:
        if sha256(ROOT / "DESIGN-NATIVE-GRID.json") != NATIVE_GRID_SHA256:
            raise GateError("Alternate design differs from the frozen SHA-256")
        report["native_grid_design_sha256"] = NATIVE_GRID_SHA256
    try:
        evidence = read_channel_gate(design, schema)
    except GateError as error:
        return {**report, "status": "source_gate_hold", "decision": str(error)}, 2
    report["channel_evidence_sha256"] = CHANNEL_EVIDENCE_SHA256
    if check_source:
        return {**report, "status": "source_gate_ready"}, 0
    window_start = perf_counter()
    train, dev = (
        read_windows(paths[role], evidence["roles"][role], design["sampling"], native_grid)
        for role in ("TRAIN", "DEV")
    )
    score_start = perf_counter()
    counts = {"TRAIN": train[2], "DEV": dev[2]}
    if any(role_counts["eligible_trials"] < 4 for role_counts in counts.values()):
        return {
            **report,
            "status": "insufficient_eligible_trials",
            "decision": "Fewer than four eligible trials in at least one role. No fit or scores computed.",
            "counts": counts,
        }, 2
    report["results"] = score(train, dev, design["model"]["alpha"])
    end = perf_counter()
    pools = threadpool_info()
    for pool in pools:
        if "filepath" in pool:
            pool["library"] = Path(pool.pop("filepath")).name
    report.update(
        {
            "status": "offline_dev_scored",
            "limitations": design["offline_limit"],
            "assets": design["roles"],
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "h5py": h5py.__version__,
                "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
                "numeric_pools": pools,
                "seconds_after_import": {
                    "custody_and_schema": schema_seconds,
                    "window_loading_after_gate": score_start - window_start,
                    "fit_and_score": end - score_start,
                    "total": end - start,
                },
            },
        }
    )
    return report, 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True, help="Exact admitted sub-02 R1 derivative")
    parser.add_argument("--dev", type=Path, required=True, help="Exact admitted sub-03 R1 derivative")
    parser.add_argument("--output", type=Path, help="Write aggregate JSON to a new file, default stdout")
    parser.add_argument("--check-source", action="store_true", help="Check custody and source geometry without scoring")
    parser.add_argument("--native-grid", action="store_true", help="Use the separately frozen native-anchor version")
    args = parser.parse_args()
    try:
        with threadpool_limits(limits=1):
            report, code = run({"TRAIN": args.train, "DEV": args.dev}, args.check_source, args.native_grid)
        payload = json.dumps(report, indent=2, allow_nan=False, sort_keys=True) + "\n"
        if args.output is None:
            sys.stdout.write(payload)
        else:
            with args.output.open("x") as stream:
                stream.write(payload)
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"Pilot stopped: {error}", file=sys.stderr)
        return 2
    return code


if __name__ == "__main__":
    sys.exit(main())
