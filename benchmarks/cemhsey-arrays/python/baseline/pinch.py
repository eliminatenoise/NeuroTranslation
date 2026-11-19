"""Offline predictions for the prespecified CEMHSEY normalized pinch experiment."""

from __future__ import annotations

import hashlib
from itertools import groupby, product
from pathlib import Path

import numpy as np

FORCE_HZ = 200
EMG_HZ = 2048
CHANNELS = 320
FORCE_TICKS = 6000
HORIZON = 24
ISSUE_TICKS = np.arange(60, 5980, 10)
LAGS = np.array([5, 10, 20, 40])
PHASE_EDGES = np.array([0, 1000, 2000, 4000, 5000, 6000])
PHASES = ("initial_rest", "ramp_up", "hold", "release", "final_rest")
PENALTY = 0.01
TIMING_MODES = ("nominal_release_index", "force_only")
FORCE_FEATURES = ("force_now", "force_delta_5", "force_delta_10",
                  "force_delta_20", "force_delta_40")
PHASE_FEATURES = tuple(
    prefix + phase for prefix in ("phase_", "phase_age_") for phase in PHASES
)
EMG_FEATURES = ("emg_older_median", "emg_older_q90",
                "emg_recent_median", "emg_recent_q90")
MODEL_FEATURES = {
    "phase": PHASE_FEATURES,
    "history": FORCE_FEATURES,
    "history_phase": FORCE_FEATURES + PHASE_FEATURES,
    "history_phase_paired_emg": FORCE_FEATURES + PHASE_FEATURES + EMG_FEATURES,
    "history_phase_other_emg": FORCE_FEATURES + PHASE_FEATURES + EMG_FEATURES,
}
FIT_FORMAT = "cemhsey-pinch-fit-v1"
PACKET_FORMAT = "cemhsey-pinch-trial-v1"
PROTOCOL_PATH = Path(__file__).with_name("PROTOCOL.md")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def emg_boundary(force_tick):
    return (force_tick * EMG_HZ + FORCE_HZ - 1) // FORCE_HZ


def phase_code(ticks):
    return np.searchsorted(PHASE_EDGES[1:], ticks, side="right")


def phase_features(ticks):
    code = phase_code(ticks)
    age = (ticks - PHASE_EDGES[code]) / (PHASE_EDGES[code + 1] - PHASE_EDGES[code])
    indicators = np.eye(len(PHASES))[code]
    return np.column_stack((indicators, indicators * age[:, None]))


def check_force(force, min_samples):
    if force.dtype != np.float64 or force.ndim != 1 or force.size < min_samples:
        raise ValueError("Need a float64 normalized force vector with the prescribed support")


def check_emg(emg, min_samples):
    if (emg.dtype != np.float64 or emg.ndim != 2 or emg.shape[0] != CHANNELS
            or emg.shape[1] < min_samples):
        raise ValueError("Need a float64 EMG channels-by-time matrix with 320 channels")


def force_features(force, ticks):
    values = force[ticks]
    features = np.column_stack((values, values[:, None] - force[ticks[:, None] - LAGS]))
    if not np.isfinite(features).all():
        raise ValueError("Nonfinite force in feature support")
    return features


def emg_features(emg, ticks):
    features = np.empty((len(ticks), len(EMG_FEATURES)))
    boundaries = emg_boundary(ticks[:, None] - np.array([60, 40, 20]))
    # Use the same reduction order for a training row and a single prediction.
    for row, (start, middle, stop) in enumerate(boundaries):
        for column, (left, right) in enumerate(((start, middle), (middle, stop))):
            block = emg[:, left:right]
            rms = np.sqrt(np.mean(np.square(block), axis=1))
            features[row, 2 * column:2 * column + 2] = np.log1p(
                np.quantile(rms, [0.5, 0.9], method="linear")
            )
    if not np.isfinite(features).all():
        raise ValueError("Nonfinite EMG summary in feature support")
    return features


def extract_trial(force, emg):
    """Create private trial-level features on the one frozen support."""
    check_force(force, FORCE_TICKS)
    if emg is not None:
        check_emg(emg, emg_boundary(int(ISSUE_TICKS[-1]) - 20))
    target = force[ISSUE_TICKS + HORIZON]
    if not np.isfinite(target).all():
        raise ValueError("Nonfinite force in target support")
    return {
        "force": force_features(force, ISSUE_TICKS),
        "emg": None if emg is None else emg_features(emg, ISSUE_TICKS),
        "target": target,
    }


def packet_from_features(trial, timing_mode):
    if timing_mode not in TIMING_MODES or (
            timing_mode == "nominal_release_index") != (trial["emg"] is not None):
        raise ValueError("Packet mode and available features disagree")
    rows = []
    for index, issue in enumerate(ISSUE_TICKS):
        rows.append({
            "issue_tick": int(issue),
            "force_now": float(trial["force"][index, 0]),
            "force_deltas": trial["force"][index, 1:].tolist(),
            "emg_summaries": None if trial["emg"] is None else trial["emg"][index].tolist(),
            "measured_target": float(trial["target"][index]),
        })
    return {
        "format": PACKET_FORMAT,
        "protocol_sha256": sha256(PROTOCOL_PATH),
        "timing_mode": timing_mode,
        "rows": rows,
    }


def fit_ridge(features, outcome, model_name):
    center = features.mean(axis=0)
    scale = features.std(axis=0)
    scale[features.max(axis=0) == features.min(axis=0)] = 1.0
    centered = (features - center) / scale
    intercept = outcome.mean()
    regularizer = PENALTY * np.eye(centered.shape[1])
    coefficient = np.linalg.solve(
        (centered.T @ centered) / len(outcome) + regularizer,
        (centered.T @ (outcome - intercept)) / len(outcome),
    )
    if not np.isfinite(np.concatenate((center, scale, coefficient, [intercept]))).all():
        raise ValueError("Nonfinite fitted model")
    return {
        "feature_names": list(MODEL_FEATURES[model_name]),
        "center": center.tolist(),
        "scale": scale.tolist(),
        "intercept": float(intercept),
        "coef": coefficient.tolist(),
        "add_force_now": model_name != "phase",
    }


def predict_rows(model, features, force_now):
    standardized = (features - model["center"]) / model["scale"]
    prediction = float(model["intercept"]) + standardized @ model["coef"]
    if model["add_force_now"]:
        prediction = prediction + force_now
    if not np.isfinite(prediction).all():
        raise ValueError("Nonfinite prediction")
    return prediction


def predict_at(fit, issue_tick, force_prefix, emg_prefix=None):
    """Forecast one tick from sample-zero prefixes without indexing the target."""
    validate_fit(fit)
    if (isinstance(issue_tick, bool) or not isinstance(issue_tick, (int, np.integer))
            or issue_tick < ISSUE_TICKS[0] or issue_tick > ISSUE_TICKS[-1]
            or (issue_tick - ISSUE_TICKS[0]) % 10):
        raise ValueError("Issue tick is outside the prescribed study grid")
    check_force(force_prefix, issue_tick + 1)
    ticks = np.array([issue_tick])
    history = force_features(force_prefix, ticks)
    features = np.column_stack((history, phase_features(ticks)))
    name = "history_phase"
    if emg_prefix is not None:
        if fit["timing_mode"] != "nominal_release_index":
            raise ValueError("This fit does not qualify EMG")
        check_emg(emg_prefix, emg_boundary(issue_tick - 20))
        features = np.column_stack((features, emg_features(emg_prefix, ticks)))
        name = "history_phase_paired_emg"
    predicted = predict_rows(fit["models"][name], features, history[:, 0])
    return {"model": name, "issue_tick": int(issue_tick),
            "target_tick": int(issue_tick) + HORIZON,
            "predicted_normalized_force": float(predicted[0])}


def trial_design(trial, donor):
    history = trial["force"]
    phase = phase_features(ISSUE_TICKS)
    history_phase = np.column_stack((history, phase))
    columns = {"phase": phase, "history": history, "history_phase": history_phase}
    if trial["emg"] is not None:
        columns.update({
            "history_phase_paired_emg": np.column_stack((history_phase, trial["emg"])),
            "history_phase_other_emg": np.column_stack((history_phase, donor["emg"])),
        })
    return columns


def matched_trials(trials):
    """Sort private keys and pair repetitions 1 and 2 in both directions."""
    for group, records in groupby(sorted(trials), key=lambda key: key[:2]):
        keys = list(records)
        if [key[2] for key in keys] != [1, 2]:
            raise ValueError("Each included person and day needs both repeats")
        trial_a, trial_b = (trials[key] for key in keys)
        yield group, trial_a, trial_b
        yield group, trial_b, trial_a


def fit_panel(trials, timing_mode):
    check_panel(trials, timing_mode)
    designs = []
    residuals = []
    targets = []
    for _, trial, donor in matched_trials(trials):
        designs.append(trial_design(trial, donor))
        residuals.append(trial["target"] - trial["force"][:, 0])
        targets.append(trial["target"])
    target = np.concatenate(targets)
    residual = np.concatenate(residuals)
    models = {}
    for name in designs[0]:
        features = np.concatenate([design[name] for design in designs])
        models[name] = fit_ridge(features, target if name == "phase" else residual, name)
    return {
        "format": FIT_FORMAT,
        "protocol_sha256": sha256(PROTOCOL_PATH),
        "timing_mode": timing_mode,
        "models": models,
    }


def validation_numbers(values, size, allow_zero=True):
    if not isinstance(values, list) or len(values) != size:
        return False
    return all(
        type(value) in (int, float) and np.isfinite(value) and (allow_zero or value > 0)
        for value in values
    )


def validate_fit(fit, full=False):
    if (fit.get("format") != FIT_FORMAT
            or fit.get("protocol_sha256") != sha256(PROTOCOL_PATH)
            or fit.get("timing_mode") not in TIMING_MODES):
        raise ValueError("Unsupported or unbound fit")
    expected = set(MODEL_FEATURES)
    if fit["timing_mode"] == "force_only":
        expected = {"phase", "history", "history_phase"}
    models = fit.get("models")
    if not isinstance(models, dict) or (
            set(models) != expected and (
                full or set(models) != expected - {"history_phase_other_emg"})):
        raise ValueError("Fit has an incorrect model inventory")
    for name, model in models.items():
        features = list(MODEL_FEATURES[name])
        if (not isinstance(model, dict) or model.get("feature_names") != features
                or model.get("add_force_now") is not (name != "phase")
                or not validation_numbers([model.get("intercept")], 1)
                or not validation_numbers(model.get("center"), len(features))
                or not validation_numbers(model.get("scale"), len(features), allow_zero=False)
                or not validation_numbers(model.get("coef"), len(features))):
            raise ValueError("Fit has an invalid coefficient record")


def check_panel(trials, timing_mode):
    subjects = sorted({key[0] for key in trials})
    days = sorted({key[1] for key in trials})
    if not subjects or not days or set(trials) != set(product(subjects, days, (1, 2))):
        raise ValueError("The panel must be complete and balanced")
    if timing_mode not in TIMING_MODES or any(
        (trial["emg"] is not None) != (timing_mode == "nominal_release_index")
        for trial in trials.values()
    ):
        raise ValueError("The panel and the prespecified timing mode disagree")
    return subjects, days


def primary_contrast(errors, baseline, proposed, days):
    # Shape axes: person, indexed day, repeat, issue.
    day_differences = np.abs(errors[baseline]).mean(axis=(2, 3))
    day_differences -= np.abs(errors[proposed]).mean(axis=(2, 3))
    people = day_differences.mean(axis=1)
    possible_draws = np.array(list(product(range(len(people)), repeat=len(people))))
    bootstrap_means = people[possible_draws].mean(axis=1)
    return {
        "difference": float(people.mean()),
        "people_favoring_paired": int((people > 0).sum()),
        "cluster_resample_count": int(len(bootstrap_means)),
        "participant_resampling_range_2_5_to_97_5": np.quantile(
            bootstrap_means, [0.025, 0.975], method="linear"
        ).tolist(),
        "indexed_day_differences": {
            str(day): float(value)
            for day, value in zip(days, day_differences.mean(axis=0), strict=True)
        },
    }


def error_metrics(errors):
    return {"mae": float(np.abs(errors).mean()),
            "rmse": float(np.sqrt(np.square(errors).mean()))}


def score_panel(trials, fit):
    validate_fit(fit, full=True)
    people, days = check_panel(trials, fit["timing_mode"])
    errors = {}
    for _, trial, donor in matched_trials(trials):
        force_now = trial["force"][:, 0]
        outcome = trial["target"]
        rows = {"persistence": force_now}
        design = trial_design(trial, donor)
        for name, features in design.items():
            rows[name] = predict_rows(fit["models"][name], features, force_now)
        if "history_phase_paired_emg" in rows:
            rows["history_phase_paired_emg_swapped_at_score"] = predict_rows(
                fit["models"]["history_phase_paired_emg"],
                design["history_phase_other_emg"], force_now,
            )
        for name, prediction in rows.items():
            errors.setdefault(name, []).append(prediction - outcome)
    errors = {
        name: np.stack(rows).reshape(len(people), len(days), 2, len(ISSUE_TICKS))
        for name, rows in errors.items()
    }
    phase = phase_code(ISSUE_TICKS)
    contrasts = {}
    paired = "history_phase_paired_emg"
    for baseline in ("history_phase", "history_phase_other_emg"):
        if paired in errors:
            contrasts[f"{baseline}_minus_paired_emg"] = primary_contrast(
                errors, baseline, paired, days
            )
    return {
        "format": "cemhsey-pinch-aggregate-v1",
        "protocol_sha256": fit["protocol_sha256"],
        "timing_mode": fit["timing_mode"],
        "people": len(people),
        "days_per_person": len(days),
        "repeats_per_person_day": 2,
        "issue_ticks_per_trial": len(ISSUE_TICKS),
        "trials": len(trials),
        "issue_windows": len(trials) * len(ISSUE_TICKS),
        "scores": {name: error_metrics(value) for name, value in errors.items()},
        "scores_by_issue_phase": {
            label: {name: error_metrics(value[..., phase == index])
                    for name, value in errors.items()}
            for index, label in enumerate(PHASES)
        },
        "phase_ticks_per_trial": {
            label: int((phase == index).sum()) for index, label in enumerate(PHASES)
        },
        "paired_mae_contrasts": contrasts,
    }
