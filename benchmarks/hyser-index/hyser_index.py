"""Released index sensor voltage forecast on Hyser 2.0.0 Random trials."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import math

import numpy as np

EXPERIMENT = "hyser-random-index-20261119-v1"
FORCE_RATE = 100
EMG_RATE = 2048
FORCE_SAMPLES = 2500
EMG_SAMPLES = 51200
HORIZON = 12
FORCE_LAGS = np.arange(-40, 1, dtype=np.int64)
BIN_OFFSETS = np.arange(-42, -1, 10, dtype=np.int64)
EARLIER_TICKS = 40
TICKS = np.arange(140, 2388, 5, dtype=np.int64)
VOLTAGE_FLOOR = 1e-12
ALPHAS = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0)
WITHIN_DAY_ALPHA = 1e-2
ARMS = ("persistence", "slope", "force", "aligned", "earlier", "same_phase_other_trial")
FITTED_ARMS = ARMS[2:]
CONTROLS = ("force", "earlier", "same_phase_other_trial", "persistence", "slope")
SOURCE_DOI = "10.13026/hxan-pe94"
SCHEMA = "hyser-index-release-voltage-weights-v1"
FEATURES = {
    "force_rate_hz": FORCE_RATE,
    "emg_rate_hz": EMG_RATE,
    "prediction_horizon_force_ticks": HORIZON,
    "force_lags_ticks_ordered": FORCE_LAGS.tolist(),
    "aligned_emg_bin_boundaries_ticks": BIN_OFFSETS.tolist(),
    "earlier_emg_shift_ticks": -EARLIER_TICKS,
    "emg_channel_groups_zero_based_half_open": [[0, 64], [64, 128], [128, 192], [192, 256], [0, 256]],
    "emg_rms_floor_v": VOLTAGE_FLOOR,
    "emg_feature_order": "bin oldest first, then groups in listed order",
    "emg_interval": "half-open ceiling endpoints on common nominal trigger lattice",
    "force_history_unit": "V",
    "target_unit": "V",
    "residual_reference": "released index sensor voltage at current force tick",
    "force_stream": "released Hyser 2.0.0 index force transducer voltage",
}


def participant_roles() -> dict[str, list[str]]:
    ids = [f"S{n:02}" for n in range(1, 21)]
    ordered = sorted(ids, key=lambda p: hashlib.sha256(f"{EXPERIMENT}/{p}".encode("ascii")).digest())
    return {"TRAIN": ordered[:12], "DEV": ordered[12:16], "FINAL": ordered[16:]}


def emg_boundary(force_tick: np.ndarray) -> np.ndarray:
    """First EMG sample at or after the given nominal force time."""
    return (force_tick * 512 + 24) // 25


def tick_vector(ticks: Sequence[int]) -> np.ndarray:
    ticks = np.asarray(ticks)
    if ticks.ndim != 1 or len(ticks) == 0 or ticks.dtype.kind not in "iu":
        raise ValueError("Expected a nonempty vector of integer force ticks")
    if np.any(ticks < 0) or np.any(ticks >= FORCE_SAMPLES):
        raise ValueError("Force tick outside the trial")
    return ticks.astype(np.int64, copy=False)


def force_history(force: np.ndarray, ticks: Sequence[int]) -> np.ndarray:
    ticks = tick_vector(ticks)
    if force.ndim != 1 or min(ticks) < 40 or max(ticks) >= len(force):
        raise ValueError("Force history requires 41 released index voltage samples through each tick")
    features = force[ticks[:, None] + FORCE_LAGS]
    if not np.isfinite(features).all():
        raise ValueError("Missing or nonfinite released force history")
    return features


def binned_emg(raw: np.ndarray, ticks: Sequence[int], shifts: Sequence[int] = (0,)) -> np.ndarray:
    """Return (shift, tick, 20) log RMS features from raw voltage and past bins."""
    ticks = tick_vector(ticks)
    intervals = np.array(shifts, dtype=np.int64)[:, None, None] + ticks[None, :, None] + BIN_OFFSETS
    bounds = emg_boundary(intervals)
    first, end = int(bounds.min()), int(bounds.max())
    if raw.ndim != 2 or raw.shape[1] != 256 or first < 0 or end > len(raw):
        raise ValueError("Raw EMG does not cover requested bins and 256 ordered channels")
    values = raw[first:end].reshape(-1, 4, 64)
    energy = np.einsum("tgc,tgc->tg", values, values, dtype=np.float64) / 64.0
    if not np.isfinite(energy).all():
        raise ValueError("Missing or nonfinite raw EMG in feature span")
    prefix = np.empty((len(energy) + 1, 4), dtype=np.float64)
    prefix[0] = 0.0
    np.cumsum(energy, axis=0, out=prefix[1:])
    widths = np.diff(bounds, axis=2)
    means = np.diff(prefix[bounds - first], axis=2) / widths[..., None]
    pooled = means.mean(axis=-1, keepdims=True)
    mean_square = np.concatenate([means, pooled], axis=-1)
    return (0.5 * np.log(np.maximum(mean_square, VOLTAGE_FLOOR**2))).reshape(len(shifts), len(ticks), 20)


@dataclass(frozen=True)
class Trial:
    force: np.ndarray
    current: np.ndarray
    truth: np.ndarray
    slope: np.ndarray
    aligned: np.ndarray
    earlier: np.ndarray


def extract_trial(raw: np.ndarray, force: np.ndarray, ticks: Sequence[int] = TICKS) -> Trial:
    if raw.shape != (EMG_SAMPLES, 256) or force.shape != (FORCE_SAMPLES,):
        raise ValueError("Trial shape differs from the pinned Hyser Random contract")
    ticks = tick_vector(ticks)
    if ticks.max() + HORIZON >= len(force):
        raise ValueError("Future evaluation target leaves the trial")
    histories = force_history(force, ticks)
    aligned, earlier = binned_emg(raw, ticks, (0, -EARLIER_TICKS))
    current, truth = histories[:, -1], force[ticks + HORIZON]
    if not np.isfinite(truth).all():
        raise ValueError("Missing or nonfinite future released force")
    past = np.arange(-10, 1, dtype=np.float64) + 5
    slope = (histories[:, -11:] @ past) / (past @ past)
    return Trial(histories, current, truth, current + HORIZON * slope, aligned, earlier)


@dataclass(frozen=True)
class Rows:
    features: np.ndarray
    current: np.ndarray
    truth: np.ndarray
    slope: np.ndarray


def pair_rows(trial: Trial, donor: Trial, arm: str) -> Rows:
    if len(trial.truth) != len(donor.truth):
        raise ValueError("Same-phase donor and scoring rows do not share the time grid")
    if arm in ("force", "persistence", "slope"):
        features = trial.force
    else:
        extras = {
            "aligned": trial.aligned, "earlier": trial.earlier, "same_phase_other_trial": donor.aligned,
        }[arm]
        features = np.column_stack((trial.force, extras))
    return Rows(features, trial.current, trial.truth, trial.slope)


def stack_rows(rows: Sequence[Rows]) -> Rows:
    return Rows(
        np.vstack([r.features for r in rows]), np.concatenate([r.current for r in rows]),
        np.concatenate([r.truth for r in rows]), np.concatenate([r.slope for r in rows]),
    )


@dataclass(frozen=True)
class Moments:
    count: int
    mean: np.ndarray
    mean_y: float
    scatter: np.ndarray
    cross: np.ndarray


def moments(rows: Rows) -> Moments:
    x = rows.features
    y = rows.truth - rows.current
    mean = x.mean(axis=0)
    mean_y = float(y.mean())
    centered = x - mean
    return Moments(len(y), mean, mean_y, centered.T @ centered, centered.T @ (y - mean_y))


def merge_moments(parts: Sequence[Moments]) -> Moments:
    counts = np.array([p.count for p in parts], dtype=np.float64)
    count = int(counts.sum())
    mean = np.average(np.stack([p.mean for p in parts]), axis=0, weights=counts)
    mean_y = float(np.average([p.mean_y for p in parts], weights=counts))
    scatter = sum(p.scatter + p.count * np.outer(p.mean - mean, p.mean - mean) for p in parts)
    cross = sum(p.cross + p.count * (p.mean - mean) * (p.mean_y - mean_y) for p in parts)
    return Moments(count, mean, mean_y, scatter, cross)


@dataclass(frozen=True)
class Ridge:
    alpha: float
    mean: np.ndarray
    scale: np.ndarray
    intercept: float
    coef: np.ndarray

    def predict(self, rows: Rows) -> np.ndarray:
        return rows.current + self.intercept + ((rows.features - self.mean) / self.scale) @ self.coef

    def encode(self) -> dict:
        return {
            "alpha": self.alpha,
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "intercept": self.intercept,
            "coef": self.coef.tolist(),
        }


def fit(moment: Moments, alpha: float) -> Ridge:
    scale = np.sqrt(np.maximum(np.diag(moment.scatter) / moment.count, 0.0))
    scale[scale <= 1e-14 * np.maximum(1.0, np.abs(moment.mean))] = 1.0
    covariance = (moment.scatter / moment.count) / np.outer(scale, scale)
    cross = (moment.cross / moment.count) / scale
    coef = np.linalg.solve(covariance + alpha * np.eye(len(scale)), cross)
    return Ridge(alpha, moment.mean, scale, moment.mean_y, coef)


def decode_ridge(record: dict, width: int) -> Ridge:
    mean, scale, coef = [np.asarray(record[name], dtype=np.float64) for name in ("mean", "scale", "coef")]
    alpha, intercept = float(record["alpha"]), float(record["intercept"])
    if any(x.shape != (width,) or not np.isfinite(x).all() for x in (mean, scale, coef)):
        raise ValueError("Malformed ridge arrays")
    if (scale <= 0).any() or alpha not in ALPHAS or not math.isfinite(intercept):
        raise ValueError("Malformed ridge normalization or intercept")
    return Ridge(alpha, mean, scale, intercept, coef)


def decode_predictors(weights: dict) -> dict[str, Ridge]:
    if weights.get("schema") != SCHEMA or weights.get("experiment") != EXPERIMENT or weights.get("features") != FEATURES:
        raise ValueError("Weight edition or feature contract mismatch")
    if set(weights["models"]) != {"force", "aligned"}:
        raise ValueError("Expected both predictive weight sets")
    return {arm: decode_ridge(weights["models"][arm], 41 if arm == "force" else 61) for arm in ("force", "aligned")}


def predict_trial(raw: np.ndarray, force: np.ndarray, ticks: Sequence[int], weights: dict) -> dict[str, np.ndarray]:
    """Apply frozen predictive models. This call does not read future force or raw EMG."""
    records = decode_predictors(weights)
    histories = force_history(force, ticks)
    aligned = binned_emg(raw, ticks)[0]
    predictions = {}
    for arm, feature_matrix in (("force", histories), ("aligned", np.column_stack((histories, aligned)))):
        rows = Rows(feature_matrix, histories[:, -1], np.empty(0), np.empty(0))
        predictions[arm] = records[arm].predict(rows)
    return predictions
