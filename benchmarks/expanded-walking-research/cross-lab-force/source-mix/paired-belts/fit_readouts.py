"""Learn separate force corrections for total belt load and its left/right split."""

from dataclasses import dataclass

import numpy as np


def force_pair(values):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2 or not len(values) or not np.isfinite(values).all():
        raise ValueError('Supply a finite left/right impulse pair for every window.')
    return values


def best_interpolation(change, residual, weights):
    """Minimize weighted absolute error on the line between two predictions."""
    changed = change != 0
    if not changed.any():
        return 0.0
    mass = np.abs(change[changed]) * weights[changed]
    roots = np.clip(residual[changed] / change[changed], 0.0, 1.0)
    order = np.argsort(roots, kind='stable')
    accumulated = np.cumsum(mass[order])
    median = np.searchsorted(accumulated, 0.5 * accumulated[-1])
    return float(roots[order[median]])


def components(steady_force, force_trend, model_force):
    steady, trend, model = map(force_pair, (steady_force, force_trend, model_force))
    if steady.shape != trend.shape or trend.shape != model.shape:
        raise ValueError('The three forecasts must cover the same windows in the same order.')
    reference_sum = trend.sum(axis=1)
    reference_split = steady[:, 0] - steady[:, 1]
    learned_sum = model.sum(axis=1)
    learned_split = model[:, 0] - model[:, 1]
    return reference_sum, reference_split, learned_sum - reference_sum, learned_split - reference_split


@dataclass(frozen=True)
class BeltBlend:
    total_weight: float
    split_weight: float

    def predict(self, steady_force, force_trend, model_force):
        total, split, total_change, split_change = components(steady_force, force_trend, model_force)
        total = total + self.total_weight * total_change
        split = split + self.split_weight * split_change
        return np.column_stack((total + split, total - split)) * 0.5


def fit_blend(steady_force, force_trend, model_force, measured, participant):
    """Fit two scalar weights with equal participant mass and no calibration from test people."""
    total, split, total_change, split_change = components(steady_force, force_trend, model_force)
    measured = force_pair(measured)
    participant = np.asarray(participant)
    if measured.shape != (len(total), 2) or participant.shape != total.shape:
        raise ValueError('Match the recorded forces and participant keys to the forecast windows.')
    people, inverse, counts = np.unique(participant, return_inverse=True, return_counts=True)
    weights = 1.0 / (len(people) * counts[inverse])
    a = best_interpolation(total_change, measured.sum(axis=1) - total, weights)
    fitted_total = total + a * total_change
    from_left = 2.0 * measured[:, 0] - fitted_total - split
    from_right = fitted_total - 2.0 * measured[:, 1] - split
    b = best_interpolation(np.tile(split_change, 2), np.concatenate((from_left, from_right)), np.tile(weights, 2))
    return BeltBlend(a, b)
