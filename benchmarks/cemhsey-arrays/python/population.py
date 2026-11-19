"""Offline forearm surface-EMG pinch forecasts on the frozen CEMHSEY grid."""

from __future__ import annotations

import hashlib
from itertools import product
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from baseline import pinch as prior

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "PROTOCOL.md"
BASELINE_SHA256 = "292ec7a480ba7170ff6d09abc5b44a2f6cbc7e39f7ff3620f3e52af18d11ea80"
BASELINE_PROTOCOL_SHA256 = "7f790773248996b7893ba99168331419ddc3041406d55c13e928d09f8fe69b1a"
FIT_FORMAT = "cemhsey-pinch-grid-fit-v1"
AGGREGATE_FORMAT = "cemhsey-pinch-grid-aggregate-v1"
PACKET_FORMAT = "cemhsey-pinch-grid-issue-v1"
TIMING_MODE = "nominal_release_index"
TRAIN_DAYS = (1, 2)
TEST_DAYS = (5, 6)
TRAIN_PEOPLE = 3
TEST_PEOPLE = 4

GROUPS = 5
ROWS_PER_GROUP = 64
GRID_FEATURES = tuple(
    f"emg_{window}_grid_{grid}_log_median_contrast"
    for window in ("older", "recent")
    for grid in range(1, GROUPS + 1)
)
RANK_FEATURE = ("emg_channel_rank_persistence",)

AMPLITUDE = "history_phase_paired_emg"
OTHER_AMPLITUDE = "history_phase_other_emg"
GRID = "history_phase_paired_grid"
INTERLEAVED = "history_phase_interleaved_grid"
OTHER_GRID = "history_phase_other_grid_only"
OTHER_FULL = "history_phase_other_grid_full"
GRID_RANK = "history_phase_paired_grid_rank"
DERANGED_RANK = "history_phase_deranged_grid_rank"
OTHER_RANK = "history_phase_other_grid_rank_only"
MODEL_FEATURES = dict(prior.MODEL_FEATURES)
MODEL_FEATURES.update({
    name: MODEL_FEATURES[AMPLITUDE] + GRID_FEATURES
    for name in (GRID, INTERLEAVED, OTHER_GRID, OTHER_FULL)
})
MODEL_FEATURES.update({
    name: MODEL_FEATURES[GRID] + RANK_FEATURE
    for name in (GRID_RANK, DERANGED_RANK, OTHER_RANK)
})
CORE_CONTRASTS = {
    GRID: (AMPLITUDE, INTERLEAVED, OTHER_GRID, OTHER_FULL),
    GRID_RANK: (GRID, DERANGED_RANK, OTHER_RANK),
}
SWAPPED_AT_SCORE = {
    AMPLITUDE: (OTHER_AMPLITUDE,),
    GRID: (INTERLEAVED, OTHER_GRID, OTHER_FULL),
    GRID_RANK: (DERANGED_RANK, OTHER_RANK),
}


def validate_baseline():
    if (prior.sha256(Path(prior.__file__)) != BASELINE_SHA256
            or prior.sha256(prior.PROTOCOL_PATH) != BASELINE_PROTOCOL_SHA256):
        raise ValueError("Prior study source or protocol differs from the frozen snapshot")


def channel_derangement():
    """Move every recent-window index using one fixed content-independent cycle."""
    ring = np.array(sorted(
        range(prior.CHANNELS),
        key=lambda index: hashlib.sha256(
            f"cemhsey-pinch-channel-derangement-v1:{index}".encode("ascii")
        ).digest(),
    ))
    permutation = np.empty_like(ring)
    permutation[ring] = np.roll(ring, -1)
    permutation.flags.writeable = False
    return permutation


PERMUTATION = channel_derangement()


def window_rms(emg, ticks):
    """Extract each distinct guarded 100 ms window once per trial."""
    starts = np.concatenate((ticks - 60, ticks - 40))
    unique_starts, inverse = np.unique(starts, return_inverse=True)
    windows = np.empty((len(unique_starts), prior.CHANNELS), dtype=np.float64)
    prior.check_emg(emg, int(prior.emg_boundary(unique_starts[-1] + 20)))
    for index, start in enumerate(unique_starts):
        left = prior.emg_boundary(start)
        right = prior.emg_boundary(start + 20)
        windows[index] = np.sqrt(np.mean(np.square(emg[:, left:right]), axis=1))
    if not np.isfinite(windows).all():
        raise ValueError("Nonfinite surface EMG RMS within guarded support")
    older, recent = inverse.reshape(2, len(ticks))
    return windows, older, recent


def grid_contrasts(rms, interleaved=False):
    """Pool a physical grid or a fixed equal-size interleaved row group."""
    if interleaved:
        groups = rms.reshape(-1, ROWS_PER_GROUP, GROUPS).transpose(0, 2, 1)
    else:
        groups = rms.reshape(-1, GROUPS, ROWS_PER_GROUP)
    logs = np.log1p(np.median(groups, axis=-1))
    return logs - logs.mean(axis=1, keepdims=True)


def normalized_ranks(rms):
    """Midranks centered and scaled to unit Euclidean length, or zero if flat."""
    ranks = rankdata(rms, method="average", axis=1) - (prior.CHANNELS + 1) / 2
    norms = np.sqrt(np.sum(np.square(ranks), axis=1, keepdims=True))
    return np.divide(ranks, norms, out=np.zeros_like(ranks), where=norms != 0)


def emg_descriptors(emg, ticks):
    rms, older, recent = window_rms(emg, ticks)
    amplitude = np.log1p(np.quantile(rms, [0.5, 0.9], axis=1, method="linear").T)
    grid = grid_contrasts(rms)
    interleaved = grid_contrasts(rms, interleaved=True)
    ranks = normalized_ranks(rms)
    # Floating point rounding can exceed a mathematical endpoint by a few ulps.
    paired = np.clip(np.sum(ranks[older] * ranks[recent], axis=1), -1.0, 1.0)
    deranged = np.clip(np.sum(ranks[older] * ranks[recent][:, PERMUTATION], axis=1), -1.0, 1.0)
    return {
        "emg_summaries": np.column_stack((amplitude[older], amplitude[recent])),
        "grid_log_median_contrast": np.column_stack((grid[older], grid[recent])),
        "interleaved_log_median_contrast": np.column_stack((interleaved[older], interleaved[recent])),
        "paired_rank_persistence": paired[:, None],
        "deranged_rank_persistence": deranged[:, None],
    }


def extract_trial(force, emg):
    """Extract private predictors and the measured target, on the full exact support."""
    prior.check_force(force, prior.FORCE_TICKS)
    ticks = prior.ISSUE_TICKS
    target = force[ticks + prior.HORIZON]
    if not np.isfinite(target).all():
        raise ValueError("Nonfinite normalized force in target support")
    return {"force": prior.force_features(force, ticks), "target": target,
            **emg_descriptors(emg, ticks)}


def issue_packet(issue_tick, force_prefix, emg_prefix=None):
    """Describe one offline issue using only force/EMG prefixes, with no target."""
    if (isinstance(issue_tick, bool) or not isinstance(issue_tick, (int, np.integer))
            or not np.any(prior.ISSUE_TICKS == issue_tick)):
        raise ValueError("Issue tick is outside the frozen study grid")
    tick = int(issue_tick)
    prior.check_force(force_prefix, tick + 1)
    ticks = np.array([tick])
    force = prior.force_features(force_prefix, ticks)[0]
    fields = dict.fromkeys(("emg_summaries", "grid_log_median_contrast",
                            "paired_rank_persistence"))
    if emg_prefix is not None:
        emg = emg_descriptors(emg_prefix, ticks)
        fields.update({name: emg[name][0].tolist() for name in fields})
        fields["paired_rank_persistence"] = fields["paired_rank_persistence"][0]
    return {
        "format": PACKET_FORMAT,
        "protocol_sha256": prior.sha256(PROTOCOL),
        "issue_tick": tick,
        "target_tick": tick + prior.HORIZON,
        "force_now": float(force[0]),
        "force_deltas": force[1:].tolist(),
        **fields,
    }


def fit_ridge(features, outcome, model_name):
    if model_name in prior.MODEL_FEATURES:
        return prior.fit_ridge(features, outcome, model_name)
    # Retain the prior mean-loss convention and train-only scaling.
    center = features.mean(axis=0)
    scale = features.std(axis=0)
    scale[features.max(axis=0) == features.min(axis=0)] = 1.0
    centered = (features - center) / scale
    intercept = outcome.mean()
    coefficient = np.linalg.solve(
        centered.T @ centered / len(outcome) + prior.PENALTY * np.eye(centered.shape[1]),
        centered.T @ (outcome - intercept) / len(outcome),
    )
    return {"feature_names": list(MODEL_FEATURES[model_name]),
            "center": center.tolist(), "scale": scale.tolist(),
            "intercept": float(intercept), "coef": coefficient.tolist(),
            "add_force_now": True}


def source_hashes():
    validate_baseline()
    return {
        "protocol_sha256": prior.sha256(PROTOCOL),
        "population_sha256": prior.sha256(Path(__file__)),
        "baseline_sha256": BASELINE_SHA256,
        "baseline_protocol_sha256": BASELINE_PROTOCOL_SHA256,
    }


def validate_fit(fit):
    if (not isinstance(fit, dict) or fit.get("format") != FIT_FORMAT
            or fit.get("timing_mode") != TIMING_MODE
            or any(fit.get(key) != value for key, value in source_hashes().items())):
        raise ValueError("Fit is unbound from the exact model and protocol")
    models = fit.get("models")
    if not isinstance(models, dict) or set(models) != set(MODEL_FEATURES):
        raise ValueError("Fit has incorrect model inventory")
    for name, features in MODEL_FEATURES.items():
        fitted = models[name]
        width = len(features)
        if (not isinstance(fitted, dict) or fitted.get("feature_names") != list(features)
                or fitted.get("add_force_now") is not (name != "phase")
                or not prior.validation_numbers([fitted.get("intercept")], 1)
                or not prior.validation_numbers(fitted.get("center"), width)
                or not prior.validation_numbers(fitted.get("scale"), width, allow_zero=False)
                or not prior.validation_numbers(fitted.get("coef"), width)):
            raise ValueError("Invalid fitted coefficients or feature order")


def predict_issue(fit, packet):
    """Score a single offline issue packet in both prespecified fitted variants."""
    validate_fit(fit)
    if not isinstance(packet, dict):
        raise ValueError("Expected a single-issue object")
    tick = packet.get("issue_tick")
    if (packet.get("format") != PACKET_FORMAT
            or packet.get("protocol_sha256") != fit["protocol_sha256"]
            or type(tick) is not int or not np.any(prior.ISSUE_TICKS == tick)
            or type(packet.get("target_tick")) is not int or packet["target_tick"] != tick + prior.HORIZON
            or not prior.validation_numbers([packet.get("force_now")], 1)
            or not prior.validation_numbers(packet.get("force_deltas"), 4)):
        raise ValueError("Malformed issue input or mismatched protocol")
    force_now = packet["force_now"]
    base = [force_now] + packet["force_deltas"] + prior.phase_features(np.array([tick]))[0].tolist()
    designs = {"history_phase": base}
    amplitude = packet.get("emg_summaries")
    grid = packet.get("grid_log_median_contrast")
    rank = packet.get("paired_rank_persistence")
    if any(value is not None for value in (amplitude, grid, rank)):
        if (not prior.validation_numbers(amplitude, 4) or not prior.validation_numbers(grid, 10)
                or not prior.validation_numbers([rank], 1) or not -1 <= rank <= 1
                or any(value < 0 for value in amplitude)):
            raise ValueError("Malformed or incomplete surface EMG descriptors")
        designs |= {AMPLITUDE: base + amplitude, GRID: base + amplitude + grid,
                    GRID_RANK: base + amplitude + grid + [rank]}
    return {
        "issue_tick": tick, "target_tick": tick + prior.HORIZON,
        "predicted_normalized_force_by_model": {
            name: float(prior.predict_rows(fit["models"][name], np.array([features]), force_now)[0])
            for name, features in designs.items()
        },
    }


def trial_design(trial, donor):
    force, phase = trial["force"], prior.phase_features(prior.ISSUE_TICKS)
    base = np.column_stack((force, phase))
    current_global = np.column_stack((base, trial["emg_summaries"]))
    donor_global = np.column_stack((base, donor["emg_summaries"]))
    grid = trial["grid_log_median_contrast"]
    donor_grid = donor["grid_log_median_contrast"]
    current_grid = np.column_stack((current_global, grid))
    return {
        "phase": phase, "history": force, "history_phase": base,
        AMPLITUDE: current_global,
        OTHER_AMPLITUDE: donor_global,
        GRID: current_grid,
        INTERLEAVED: np.column_stack((current_global, trial["interleaved_log_median_contrast"])),
        OTHER_GRID: np.column_stack((current_global, donor_grid)),
        OTHER_FULL: np.column_stack((donor_global, donor_grid)),
        GRID_RANK: np.column_stack((current_grid, trial["paired_rank_persistence"])),
        DERANGED_RANK: np.column_stack((current_grid, trial["deranged_rank_persistence"])),
        OTHER_RANK: np.column_stack((current_grid, donor["paired_rank_persistence"])),
    }


def check_panel(trials, people_count, days):
    if (not isinstance(trials, dict) or any(not isinstance(key, tuple) or len(key) != 3
            or any(type(value) is not int or value < 1 for value in key) for key in trials)):
        raise ValueError("Invalid trial panel keys")
    people = {key[0] for key in trials}
    if len(people) != people_count or set(trials) != set(product(people, days, (1, 2))):
        raise ValueError("Panel does not match the preregistered design")
    length = len(prior.ISSUE_TICKS)
    widths = {
        "force": 5, "emg_summaries": 4, "grid_log_median_contrast": 10,
        "interleaved_log_median_contrast": 10, "paired_rank_persistence": 1,
        "deranged_rank_persistence": 1,
    }
    for trial in trials.values():
        arrays = {"target": (length,)}
        arrays.update({field: (length, width) for field, width in widths.items()})
        for name, shape in arrays.items():
            array = trial.get(name) if isinstance(trial, dict) else None
            if (not isinstance(array, np.ndarray) or array.shape != shape
                    or array.dtype != np.float64 or not np.isfinite(array).all()):
                raise ValueError("Trial lacks finite exact dimensions for the frozen study")


def fit_panel(trials):
    validate_baseline()
    check_panel(trials, TRAIN_PEOPLE, TRAIN_DAYS)
    ordered = list(prior.matched_trials(trials))
    designs = [trial_design(trial, donor) for _, trial, donor in ordered]
    target = np.concatenate([trial["target"] for _, trial, _ in ordered])
    residual = target - np.concatenate([trial["force"][:, 0] for _, trial, _ in ordered])
    fit = {
        "format": FIT_FORMAT,
        "timing_mode": TIMING_MODE,
        **source_hashes(),
        "models": {
            name: fit_ridge(np.concatenate([design[name] for design in designs]),
                            target if name == "phase" else residual, name)
            for name in MODEL_FEATURES
        },
    }
    validate_fit(fit)
    return fit


def score_panel(trials, fit):
    validate_fit(fit)
    check_panel(trials, TEST_PEOPLE, TEST_DAYS)
    days = TEST_DAYS
    errors = {}
    for _, trial, donor in prior.matched_trials(trials):
        current = trial["force"][:, 0]
        design = trial_design(trial, donor)
        scores = {"persistence": current}
        for name, matrix in design.items():
            scores[name] = prior.predict_rows(fit["models"][name], matrix, current)
        for fitted, controls in SWAPPED_AT_SCORE.items():
            for control in controls:
                key = f"{fitted}__score_using__{control}"
                scores[key] = prior.predict_rows(fit["models"][fitted], design[control], current)
        for name, predictions in scores.items():
            errors.setdefault(name, []).append(predictions - trial["target"])
    shape = (TEST_PEOPLE, len(days), 2, len(prior.ISSUE_TICKS))
    errors = {name: np.stack(rows).reshape(shape) for name, rows in errors.items()}
    phase = prior.phase_code(prior.ISSUE_TICKS)
    contrast_arms = {
        AMPLITUDE: ("history_phase", OTHER_AMPLITUDE),
        **CORE_CONTRASTS,
    }
    matched = {}
    decision = {}
    for candidate, baselines in contrast_arms.items():
        contrasts = {}
        for baseline in baselines:
            result = prior.primary_contrast(errors, baseline, candidate, days)
            result["people_favoring_candidate"] = result.pop("people_favoring_paired")
            contrasts[baseline] = result
        matched[candidate] = contrasts
        decision[candidate] = {
            "all_refit_mean_differences_positive": all(r["difference"] > 0 for r in contrasts.values()),
            "all_refit_ranges_and_indexed_days_positive": all(
                r["participant_resampling_range_2_5_to_97_5"][0] > 0
                and min(r["indexed_day_differences"].values()) > 0 for r in contrasts.values()
            ),
        }
    perturbations = {}
    for fitted, controls in SWAPPED_AT_SCORE.items():
        perturbations[fitted] = {}
        for control in controls:
            key = f"{fitted}__score_using__{control}"
            result = prior.primary_contrast(errors, key, fitted, days)
            result["people_favoring_candidate"] = result.pop("people_favoring_paired")
            perturbations[fitted][control] = result
    return {
        "format": AGGREGATE_FORMAT,
        **source_hashes(),
        "timing_mode": TIMING_MODE,
        "endpoint": "P200 pinch force normalized to same-day and grasp MVC",
        "measurement_units": "fraction of same-day and grasp MVC",
        "people": TEST_PEOPLE,
        "days_per_person": len(days),
        "repeats_per_person_day": 2,
        "trials": len(trials),
        "issue_ticks_per_trial": len(prior.ISSUE_TICKS),
        "issue_windows": len(trials) * len(prior.ISSUE_TICKS),
        "scores": {name: prior.error_metrics(value) for name, value in errors.items()},
        "scores_by_issue_phase": {
            label: {name: prior.error_metrics(value[..., phase == index])
                    for name, value in errors.items()}
            for index, label in enumerate(prior.PHASES)
        },
        "phase_ticks_per_trial": {
            label: int((phase == index).sum()) for index, label in enumerate(prior.PHASES)
        },
        "refit_mae_differences": matched,
        "same_fit_perturbation_mae_differences": perturbations,
        "direction_of_refit_comparisons": decision,
    }
