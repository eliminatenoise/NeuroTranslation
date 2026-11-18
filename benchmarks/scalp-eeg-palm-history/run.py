"""Reproduce the frozen six-participant archival EEG comparison."""

import argparse
from collections import Counter
from dataclasses import dataclass
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
DESIGN_SHA = "ccaff2ccda3a32ba182c78c0a111fd36295f5bb8b2b400acc46faa1436433fc9"
FIELDS = ("EEG", "t_ms", "x_mm", "lm_trial", "eeg_seg_idx")
FEATURES = (
    "palm_position_mm", "palm_velocity_mm_s",
    "eeg_older_C3_uv", "eeg_older_Cz_uv", "eeg_older_C4_uv",
    "eeg_newer_C3_uv", "eeg_newer_Cz_uv", "eeg_newer_C4_uv",
)
FEATURE_SUBSETS = {
    "time": [],
    "time_eeg": list(range(2, 8)),
    "time_palm": [0, 1],
    "time_palm_eeg": list(range(8)),
}
PAIRS = {
    "primary": ("time_palm_eeg", "time_palm"),
    "time_eeg_vs_time": ("time_eeg", "time"),
    "paired_vs_rotated_conditional": ("time_palm_eeg", "time_palm_eeg_rotated"),
    "paired_vs_rotated_timing": ("time_eeg", "time_eeg_rotated"),
}
WIN_TOLERANCE_MM2 = 1e-12


class GateError(ValueError):
    """The source or implementation failed a frozen study requirement."""


@dataclass
class Recording:
    features: np.ndarray
    target: np.ndarray
    custody: dict


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_design():
    path = ROOT / "DESIGN.json"
    if sha(path) != DESIGN_SHA:
        raise GateError("DESIGN.json fails the protocol seal")
    return json.loads(path.read_text(encoding="utf-8"))


def load_source(design, input_dir, heldout_open):
    path = ROOT / "SOURCE.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    seal = json.loads((ROOT / "PRESCORE-LOCK.json").read_text(encoding="utf-8"))
    hashes = {"design_sha256": DESIGN_SHA, "source_sha256": sha(path), "runner_sha256": sha(Path(__file__))}
    if any(seal[key] != digest for key, digest in hashes.items()):
        raise GateError("PRESCORE-LOCK.json disagrees with the analysis files")
    dataset = design["dataset"]
    roles = dataset["roles"]
    if evidence["release_commit"] != dataset["release_commit"] or evidence["roles"] != roles:
        raise GateError("Source release or roles violate the frozen design")
    participants = [subject for cohort in roles.values() for subject in cohort]
    if set(evidence["runs"]) != set(participants):
        raise GateError("Expected only the six fixed new run identities")
    if evidence["status"] != "supported_for_named_central_rows":
        raise GateError("Source binding does not support the named EEG columns")
    paths = {}
    for subject in participants:
        binding = evidence["runs"][subject]
        participant_num = int(subject.removeprefix("sub-"))
        if participant_num <= 6:
            raise GateError("Historical subjects are outside cohort scope")
        filename = f"{subject}_task-ihc_run-01_eeg_leap_R1.mat"
        if binding["basename"] != filename:
            raise GateError(f"Unexpected right-hand derivative filename for {subject}")
        named = binding["channels"]
        source_channels = design["features"]["channels"]
        columns = [row["index_zero_based"] for row in named]
        if (
            [row["name"] for row in named] != source_channels
            or any(row["type"] != "EEG" for row in named)
            or len(set(columns)) != len(source_channels)
            or any(type(idx) is not int or idx not in range(binding["n_channels"]) for idx in columns)
        ):
            raise GateError(f"Missing or invalid named channel binding for {subject}")
        if subject in heldout_open:
            paths[subject] = input_dir / filename
            if paths[subject].stat().st_size != binding["asset_bytes"] or sha(paths[subject]) != binding["asset_sha256"]:
                raise GateError(f"Asset identity mismatch for {subject}")
    return evidence, paths, hashes


def trial_datasets(handle):
    group = handle["OUT"]
    if not isinstance(group, h5py.Group):
        raise GateError("Expected the release OUT struct")
    columns = {}
    for field in FIELDS:
        dataset = group[field]
        if (
            not isinstance(dataset, h5py.Dataset)
            or dataset.ndim != 2
            or dataset.shape[1] != 1
            or h5py.check_dtype(ref=dataset.dtype) is not h5py.Reference
        ):
            raise GateError(f"Malformed HDF5 reference column {field}")
        columns[field] = dataset[:, 0]
    counts = {len(column) for column in columns.values()}
    if len(counts) != 1 or counts == {0}:
        raise GateError("Required derivative fields have different or empty trial counts")
    for references in zip(*columns.values(), strict=True):
        if any(not reference for reference in references):
            raise GateError("Missing trial object reference")
        datasets = {name: handle[reference] for name, reference in zip(columns, references, strict=True)}
        if any(not isinstance(obj, h5py.Dataset) or obj.dtype.kind not in "fiu" for obj in datasets.values()):
            raise GateError("Expected numeric derivative variables")
        yield datasets


def validate_trial_schema(datasets, channel_count):
    eeg, clock, palm = (datasets[field] for field in ("EEG", "t_ms", "x_mm"))
    if eeg.ndim != 2 or eeg.shape[1] != channel_count:
        raise GateError("EEG storage differs from the per-run samples × channel contract")
    sample_count = eeg.shape[0]
    if not sample_count or clock.shape != (1, sample_count) or palm.shape != (sample_count, 1):
        raise GateError("EEG, t_ms and x_mm differ from the release layout")
    if any(datasets[field].shape != (1, 1) for field in ("lm_trial", "eeg_seg_idx")):
        raise GateError("Expected scalar trial and segment IDs")


def source_id(dataset, minimum):
    raw = dataset[0, 0]
    if not np.isfinite(raw) or raw < minimum or raw != int(raw):
        raise GateError("Invalid trial or segment ID")
    return int(raw)


def clock_rows(clock, protocol, palm_series):
    anchor = protocol["anchor"]
    step = anchor["step_ms"]
    if not np.isfinite(clock).all() or not np.all(np.diff(clock) > 0):
        return None, "clock_nonfinite_or_nonincreasing"
    cue_index = int(np.searchsorted(clock, 0.0))
    if cue_index == 0 or cue_index == len(clock) or clock[cue_index] >= step:
        return None, "no_native_anchor_bracketing_event"
    relative = clock - clock[cue_index]
    ticks = np.rint(relative / step)
    if not np.all(np.diff(ticks) == 1) or np.any(np.abs(relative - ticks * step) > anchor["tolerance_ms"]):
        return None, "clock_gapped_or_off_lattice"
    finite_from_cue = np.flatnonzero(np.isfinite(palm_series[cue_index:]))
    if not finite_from_cue.size:
        return None, "no_finite_palm_at_or_after_native_cue"
    anchor_index = cue_index + int(finite_from_cue[0])
    target = anchor_index + np.array(anchor["score_offsets_ms"]) // step
    palm = target[:, None] - np.array(protocol["features"]["palm_lags_ms"]) // step
    eeg = np.stack([
        target[:, None] + np.arange(start, stop, step) // step
        for start, stop in protocol["features"]["eeg_bins_ms"]
    ], axis=1)
    if any(rows.min() < 0 or rows.max() >= len(clock) for rows in (target, palm, eeg)):
        return None, "required_time_support_unavailable"
    return (cue_index, anchor_index, target, palm, eeg), None


def materialize(palm_series, eeg_series, row_sets, protocol):
    _, _, target_rows, palm_rows, eeg_rows = row_sets
    target = palm_series[target_rows]
    if not np.isfinite(target).all():
        return None, "nonfinite_target"
    palm = palm_series[palm_rows]
    if not np.isfinite(palm).all():
        return None, "nonfinite_past_palm"
    eeg = eeg_series[eeg_rows]
    if not np.isfinite(eeg).all():
        return None, "nonfinite_eeg"
    lag_near, lag_far = protocol["features"]["palm_lags_ms"]
    velocity = (palm[:, 0] - palm[:, 1]) / ((lag_far - lag_near) / 1000)
    eeg_means = eeg.mean(axis=2, dtype=np.float64).reshape(len(target), -1)
    return (np.column_stack((palm[:, 0], velocity, eeg_means)), target), None


def read_recording(path, binding, protocol):
    source_columns = [channel["index_zero_based"] for channel in binding["channels"]]
    read_columns = sorted(source_columns)
    reorder = [read_columns.index(idx) for idx in source_columns]
    eligible = []
    exclusions = Counter()
    cue_lags = Counter()
    palm_delays = Counter()
    trial_ids = set()
    segment_ids = set()
    clock_ranges = {
        "target_event_time_ms": [],
        "first_available_palm_event_time_ms": [],
        "first_available_palm_after_native_cue_ms": [],
        "latest_palm_lead_ms": [],
        "latest_eeg_lead_ms": [],
    }
    with h5py.File(path, "r") as handle:
        for data in trial_datasets(handle):
            validate_trial_schema(data, binding["n_channels"])
            trial_id = source_id(data["lm_trial"], 0)
            segment_id = source_id(data["eeg_seg_idx"], 1)
            if trial_id in trial_ids or segment_id in segment_ids:
                raise GateError(f"Duplicate source trial or segment in {path.name}")
            trial_ids.add(trial_id)
            segment_ids.add(segment_id)
            clock = np.asarray(data["t_ms"][0], dtype=np.float64)
            palm = np.asarray(data["x_mm"][:, 0], dtype=np.float64)
            rows, problem = clock_rows(clock, protocol, palm)
            if problem:
                exclusions[problem] += 1
                continue
            eeg = np.asarray(data["EEG"][:, read_columns], dtype=np.float64)[:, reorder]
            values, problem = materialize(palm, eeg, rows, protocol)
            if problem:
                exclusions[problem] += 1
                continue
            cue, anchor, targets, palm_rows, eeg_rows = rows
            cue_lags[float(clock[cue])] += 1
            palm_delays[float(clock[anchor])] += 1
            clock_ranges["target_event_time_ms"].extend(clock[targets])
            clock_ranges["first_available_palm_event_time_ms"].append(float(clock[anchor]))
            clock_ranges["first_available_palm_after_native_cue_ms"].append(float(clock[anchor] - clock[cue]))
            clock_ranges["latest_palm_lead_ms"].extend(clock[targets] - clock[palm_rows[:, 0]])
            clock_ranges["latest_eeg_lead_ms"].extend(clock[targets] - clock[eeg_rows[:, -1, -1]])
            eligible.append((trial_id, *values))
    custody = {
        "released_trials": len(trial_ids),
        "eligible_trials": len(eligible),
        "exclusions": dict(sorted(exclusions.items())),
        "native_cue_lag_counts_ms": dict(sorted(cue_lags.items())),
        "first_available_palm_event_time_counts_ms": dict(sorted(palm_delays.items())),
        "source_clock_ranges": {
            key: [float(min(values)), float(max(values))] if values else None
            for key, values in clock_ranges.items()
        },
    }
    if not eligible:
        offsets = len(protocol["anchor"]["score_offsets_ms"])
        return Recording(np.empty((0, offsets, len(FEATURES))), np.empty((0, offsets)), custody)
    _, features, targets = zip(*sorted(eligible, key=lambda row: row[0]), strict=True)
    return Recording(np.stack(features), np.stack(targets), custody)


def fit_models(recordings, penalty):
    """Give each TRAIN participant and timing bin equal total weight."""
    features = np.concatenate([record.features for record in recordings])
    target = np.concatenate([record.target for record in recordings])
    weights = np.concatenate([
        np.full(len(record.target), 1.0 / (len(recordings) * len(record.target)))
        for record in recordings
    ])
    # Equal frame weighting is in the standardized transform and the normal equations.
    frame_weights = weights / target.shape[1]
    center = np.einsum("i,ijk->k", frame_weights, features)
    scale = np.sqrt(np.einsum("i,ijk->k", frame_weights, (features - center) ** 2))
    scale[np.ptp(features, axis=(0, 1)) == 0] = 1.0
    standardized = (features - center) / scale
    offset_feature_means = np.einsum("i,ijk->jk", weights, standardized)
    offset_target_means = np.einsum("i,ij->j", weights, target)
    x = (standardized - offset_feature_means) * np.sqrt(frame_weights[:, None, None])
    y = (target - offset_target_means) * np.sqrt(frame_weights[:, None])
    x = x.reshape(-1, x.shape[-1])
    y = y.ravel()

    models = {}
    for name, indices in FEATURE_SUBSETS.items():
        model = {
            "feature_indices": indices,
            "center": center[indices].tolist(),
            "scale": scale[indices].tolist(),
            "coefficients": [],
            "intercepts_mm": offset_target_means.tolist(),
        }
        if indices:
            matrix = x[:, indices]
            coefficients = np.linalg.solve(matrix.T @ matrix + penalty * np.eye(len(indices)), matrix.T @ y)
            model["coefficients"] = coefficients.tolist()
            model["intercepts_mm"] = (offset_target_means - offset_feature_means[:, indices] @ coefficients).tolist()
        models[name] = model
    return models, float(offset_target_means.mean())


def predict(features, model):
    standardized = (features[..., model["feature_indices"]] - model["center"]) / model["scale"]
    return standardized @ model["coefficients"] + model["intercepts_mm"]


def predictions(features, models, global_mean, horizon_seconds):
    result = {name: predict(features, model) for name, model in models.items()}
    result["global_mean"] = np.full(features.shape[:-1], global_mean)
    result["persistence"] = features[..., 0]
    result["velocity_extrapolation"] = features[..., 0] + features[..., 1] * horizon_seconds
    rotated = np.concatenate((features[..., :2], np.roll(features[..., 2:], -1, axis=0)), axis=2)
    for name in ("time_eeg", "time_palm_eeg"):
        result[f"{name}_rotated"] = predict(rotated, models[name])
    return result


def metrics(residual, axis=None):
    return {
        "rmse_mm": float(np.sqrt(np.mean(residual**2, axis=axis))),
        "mae_mm": float(np.mean(np.abs(residual), axis=axis)),
        "mean_signed_error_mm": float(np.mean(residual, axis=axis)),
    }


def trial_comparison(candidate, reference):
    delta = (candidate**2 - reference**2).mean(axis=1)
    lower = int(np.count_nonzero(delta < -WIN_TOLERANCE_MM2))
    higher = int(np.count_nonzero(delta > WIN_TOLERANCE_MM2))
    return {
        "candidate": lower,
        "tied": int(delta.size - lower - higher),
        "reference": higher,
        "trial_mse_delta_quantiles_mm2": dict(zip(
            ("p0", "p25", "p50", "p75", "p100"),
            np.quantile(delta, [0, 0.25, 0.5, 0.75, 1], method="linear").tolist(),
            strict=True,
        )),
    }


def score_recording(record, models, global_mean, protocol):
    offsets = protocol["anchor"]["score_offsets_ms"]
    horizon = protocol["features"]["palm_lags_ms"][0] / 1000
    residual = {
        name: value - record.target
        for name, value in predictions(record.features, models, global_mean, horizon).items()
    }
    result = {
        **record.custody,
        "frames": record.target.size,
        "metrics": {name: metrics(error) for name, error in residual.items()},
        "frame_offset_metrics": {
            str(offset): {name: metrics(error[:, index]) for name, error in residual.items()}
            for index, offset in enumerate(offsets)
        },
        "paired_trial_comparisons": {
            key: trial_comparison(residual[candidate], residual[baseline])
            for key, (candidate, baseline) in PAIRS.items()
        },
    }
    return result, residual


def balanced(metric_rows):
    return {
        "rmse_mm": float(np.sqrt(np.mean([row["rmse_mm"]**2 for row in metric_rows]))),
        "mae_mm": float(np.mean([row["mae_mm"] for row in metric_rows])),
        "mean_signed_error_mm": float(np.mean([row["mean_signed_error_mm"] for row in metric_rows])),
    }


def aggregate_cohort(names, results, residuals, offsets):
    methods = list(residuals[names[0]])
    out = {
        "participants": len(names),
        "trials": sum(results[name]["eligible_trials"] for name in names),
        "frames": sum(results[name]["frames"] for name in names),
        "participant_balanced": {
            method: balanced([results[name]["metrics"][method] for name in names]) for method in methods
        },
        "pooled_frames": {
            method: metrics(np.concatenate([residuals[name][method].ravel() for name in names]))
            for method in methods
        },
        "frame_offset_participant_balanced": {
            str(offset): {
                method: balanced([results[name]["frame_offset_metrics"][str(offset)][method] for name in names])
                for method in methods
            }
            for offset in offsets
        },
        "paired_trials": {
            key: trial_comparison(
                np.concatenate([residuals[name][candidate] for name in names]),
                np.concatenate([residuals[name][baseline] for name in names]),
            )
            for key, (candidate, baseline) in PAIRS.items()
        },
    }
    return out


def delta_for(metrics_by_method, candidate, baseline):
    return metrics_by_method[candidate]["rmse_mm"] - metrics_by_method[baseline]["rmse_mm"]


def dev_comparisons(names, results, aggregate):
    comparisons = {}
    for key, (candidate, baseline) in PAIRS.items():
        each = {name: delta_for(results[name]["metrics"], candidate, baseline) for name in names}
        leave_one = {}
        for leave_out in names:
            balanced_remaining = {
                method: balanced([results[name]["metrics"][method] for name in names if name != leave_out])
                for method in (candidate, baseline)
            }
            leave_one[leave_out] = delta_for(balanced_remaining, candidate, baseline)
        cohort = aggregate["participant_balanced"]
        comparisons[key] = {
            "candidate": candidate,
            "baseline": baseline,
            "candidate_rmse_mm": cohort[candidate]["rmse_mm"],
            "baseline_rmse_mm": cohort[baseline]["rmse_mm"],
            "candidate_minus_baseline_rmse_mm": delta_for(cohort, candidate, baseline),
            "per_participant_delta_rmse_mm": each,
            "dev_participants_favoring_candidate": sum(value < 0 for value in each.values()),
            "leave_one_participant_out_delta_rmse_mm": leave_one,
            "leave_one_participant_out_delta_range_mm": [min(leave_one.values()), max(leave_one.values())],
        }
    return comparisons


def model_state(protocol, evidence, hashes, models, mean):
    roles = protocol["dataset"]["roles"]
    return {
        "schema_version": 1,
        "kind": "offline_scalp_eeg_palm_ridge",
        "model_id": "iackd-r1-conditional-palm-availability-grid-v1",
        "analysis": "iackd_r1_conditional_palm_availability_grid",
        **hashes,
        "train_participants": roles["TRAIN"],
        "roles": roles,
        "release_commit": evidence["release_commit"],
        "terminology_registry": evidence["terminology_registry"],
        "train_asset_sha256": {name: evidence["runs"][name]["asset_sha256"] for name in roles["TRAIN"]},
        "dev_asset_sha256": {name: evidence["runs"][name]["asset_sha256"] for name in roles["DEV"]},
        "clock": {
            **{key: protocol["anchor"][key] for key in ("step_ms", "tolerance_ms", "score_offsets_ms")},
            "anchor": protocol["anchor"]["id"],
        },
        "features": {
            **{key: protocol["features"][key] for key in ("palm_lags_ms", "eeg_bins_ms", "channels")},
            "order": list(FEATURES),
            "units": ["mm", "mm/s", "uV", "uV", "uV", "uV", "uV", "uV"],
        },
        "target": {"field": "x_mm", "units": "mm", "axis": "device_horizontal_positive_right"},
        "global_mean_mm": mean,
        "ridge_lambda": protocol["models"]["lambda"],
        "models": models,
        "limits": [*protocol["scope_limits"][:3], protocol["scope_limits"][-2]],
    }


def emit(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def record_runtime(timings):
    pools = threadpool_info()
    for pool in pools:
        if "filepath" in pool:
            pool["library"] = Path(pool.pop("filepath")).name
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "h5py": h5py.__version__,
        "hdf5": h5py.version.hdf5_version,
        "platform": platform.system(),
        "allowed_logical_cpus": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "numeric_pools": pools,
        "stage_seconds": timings,
    }


def run(input_dir, output_dir):
    start = perf_counter()
    protocol = load_design()
    roles = protocol["dataset"]["roles"]
    subjects = [name for cohort in roles.values() for name in cohort]
    evidence, paths, hashes = load_source(protocol, input_dir, subjects)
    after_gate = perf_counter()
    recordings = {name: read_recording(paths[name], evidence["runs"][name], protocol) for name in subjects}
    after_load = perf_counter()
    out = {**hashes, "roles": roles, "terminology_registry": evidence["terminology_registry"]}
    minimum = protocol["eligibility"]["minimum_eligible_trials_per_participant"]
    if any(len(record.target) < minimum for record in recordings.values()):
        emit(output_dir / "RESULT.json", {
            **out,
            "status": "insufficient_eligible_trials",
            "reason": "Fewer than four matched trials in at least one participant. No model fit or scores.",
            "participants": {name: record.custody for name, record in recordings.items()},
        })
        return 2
    models, mean = fit_models([recordings[name] for name in roles["TRAIN"]], protocol["models"]["lambda"])
    emit(output_dir / "MODEL-STATE.json", model_state(protocol, evidence, hashes, models, mean))
    after_fit = perf_counter()
    paired = {name: score_recording(recordings[name], models, mean, protocol) for name in subjects}
    results = {name: report for name, (report, _) in paired.items()}
    residuals = {name: error for name, (_, error) in paired.items()}
    cohorts = {
        role: aggregate_cohort(names, results, residuals, protocol["anchor"]["score_offsets_ms"])
        for role, names in roles.items()
    }
    end = perf_counter()
    emit(output_dir / "RESULT.json", {
        **out,
        "status": "archival_development_scored",
        "model_state_sha256": sha(output_dir / "MODEL-STATE.json"),
        "individuals": results,
        "cohorts": cohorts,
        "dev_comparisons": dev_comparisons(roles["DEV"], results, cohorts["DEV"]),
        "trial_mse_tie_absolute_tolerance_mm2": WIN_TOLERANCE_MM2,
        "scope_limits": protocol["scope_limits"],
    })
    emit(output_dir / "RUNTIME.json", record_runtime({
        "source_custody": after_gate - start,
        "read_clock_and_features": after_load - after_gate,
        "fit_and_serialize_train_model": after_fit - after_load,
        "score": end - after_fit,
    }))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Directory holding the six exact source MAT inputs")
    parser.add_argument("--output", required=True, type=Path, help="New output directory")
    args = parser.parse_args()
    try:
        args.output.mkdir(exist_ok=False)
        with threadpool_limits(limits=1):
            return run(args.input, args.output)
    except (GateError, OSError, KeyError, ValueError) as error:
        print(f"Analysis stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
