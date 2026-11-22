"""NumPy forecast for the past-load-gated NeuroTranslate checkpoints."""

import numpy as np

import force_reference as reference


MODE = 'latest-force-ge-20N-or-detached-load-probability-v1'
LOAD_N = 20.


def latest_admissible_force(history):
    force = history[:, ::-1, -1]
    observed = np.isfinite(force)
    latest = np.take_along_axis(force, np.argmax(observed, axis=1)[:, None], axis=1)[:, 0]
    return np.where(observed.any(axis=1), latest, np.nan)


def correction_weight(force, probability):
    return np.where(np.isfinite(force), np.where(force >= LOAD_N, 1., probability), np.nan)


class GateModel:
    def __init__(self, portable):
        if str(portable.arrays.get('correction_gate', '')) != MODE:
            raise ValueError('Expected a checkpoint trained with the past-load gate.')
        self.base = reference.PhysicalReference(portable)

    def predict(self, history, *, observed=None):
        clean = reference.masked_history(history, observed)
        logit, persistence, delta = self.base.components(clean)
        probability = reference.sigmoid(logit)
        force = latest_admissible_force(clean)
        weight = correction_weight(force, probability)
        return np.column_stack((probability, persistence + weight * delta))

    def predict_at_issue(self, values, bin_end_ticks, issue_tick, *, observed=None):
        return self.predict(reference.history_at_issue(values, bin_end_ticks, issue_tick, observed=observed))
