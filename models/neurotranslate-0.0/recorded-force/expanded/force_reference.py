"""NumPy runtime for the physical-reference force-plate forecast."""

import numpy as np


TASK = 'recorded_plate_loading_common_six_100ms'
CHANNELS = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS', 'named_plate_upward_force_mean')
MODE = 'latest-qualified-force-20ms-bin-times-0.100s-or-zero-v1'
HISTORY_BINS = 10
BIN_TICKS = 20
FORECAST_SECONDS = .100


def masked_history(values, observed=None):
    raw = np.asarray(values)
    if raw.ndim != 3 or raw.shape[1:] != (HISTORY_BINS, len(CHANNELS)) or raw.dtype.kind not in 'iuf':
        raise ValueError('Use a numeric batch of 10 ordered 20 ms bins with six EMG channels and one force channel.')
    if observed is not None:
        mask = np.asarray(observed)
        if mask.dtype != bool or mask.shape != raw.shape:
            raise ValueError('The observed mask must be Boolean and match the input shape.')
        raw = np.where(mask, raw, np.nan)
    raw = np.asarray(raw, dtype=np.float64)
    if np.isinf(raw).any() or np.any(np.abs(raw[np.isfinite(raw)]) > np.finfo('f').max):
        raise ValueError('Use finite float32-range observations or NaN for missing samples.')
    if np.any(raw[..., :-1] < 0):
        raise ValueError('EMG RMS magnitudes in volts cannot be negative.')
    return raw


def history_at_issue(values, bin_end_ticks, issue_tick, *, observed=None):
    """Select only the ten exact 20 ms bins through the issue on a native 1 kHz clock.

    The caller assigns earlier, calibrated same-plate measurements to their native
    clocks. An absent bin stays NaN. Off-grid and post-issue bins never enter the
    forecast. The full interval for each supplied bin ends on its declared tick.
    """
    values = np.asarray(values)
    ticks = np.asarray(bin_end_ticks)
    if (values.ndim != 2 or values.shape[1] != len(CHANNELS) or values.dtype.kind not in 'iuf'
            or ticks.dtype.kind != 'i' or ticks.shape != (len(values),)
            or np.any(ticks[1:] <= ticks[:-1])):
        raise ValueError('Supply ordered unique signed integer bin clocks and one seven-channel row per clock.')
    if (isinstance(issue_tick, (bool, np.bool_)) or not isinstance(issue_tick, (int, np.integer))
            or not 199 <= int(issue_tick) <= np.iinfo(np.int64).max):
        raise ValueError('The issue needs a signed native 1 kHz clock and room for 200 ms of history.')
    mask = np.ones(values.shape, dtype=bool) if observed is None else np.asarray(observed)
    if mask.dtype != bool or mask.shape != values.shape:
        raise ValueError('The observed mask must be Boolean and match the clocked values.')
    wanted = int(issue_tick) + np.arange(-180, 1, BIN_TICKS, dtype=np.int64)
    positions = np.searchsorted(ticks, wanted)
    slots = np.flatnonzero(positions < len(ticks))
    slots = slots[ticks[positions[slots]] == wanted[slots]]
    selected = np.full((1, HISTORY_BINS, len(CHANNELS)), np.nan)
    selected[0, slots] = np.where(mask[positions[slots]], values[positions[slots]], np.nan)
    return masked_history(selected)


def impulse_reference(history):
    """Use the newest observed vertical force mean, or zero when every force bin is missing."""
    force = history[..., -1]
    reversed_force = force[:, ::-1]
    known = np.isfinite(reversed_force)
    latest = np.take_along_axis(reversed_force, np.argmax(known, axis=1)[:, None], axis=1)[:, 0]
    return np.where(known.any(axis=1), latest * FORECAST_SECONDS, 0.)


def sigmoid(logit):
    small = np.exp(-np.abs(logit))
    return np.where(logit >= 0, 1 / (1 + small), small / (1 + small))


class PhysicalReference:
    def __init__(self, portable):
        schema = portable.tasks.get(TASK, {})
        if (str(portable.arrays.get('physical_reference', '')) != MODE
                or tuple(schema.get('channels', [])) != CHANNELS
                or schema.get('history_steps') != HISTORY_BINS or schema.get('horizon_ticks') != 100):
            raise ValueError('Expected the physical-reference checkpoint for this measured force-plate task.')
        self.portable = portable

    @classmethod
    def load(cls, path, inference):
        """Pass the existing published NumPy inference module as the decoder."""
        return cls(inference.JointModel.load(path))

    def components(self, history, *, observed=None):
        clean = masked_history(history, observed)
        if not len(clean) or not np.isfinite(clean).any(axis=(1, 2)).all():
            raise ValueError('Each forecast needs an observed value in its past history.')
        raw = self.portable.predict(TASK, clean).astype(np.float64)
        return raw[:, 0], impulse_reference(clean), raw[:, 1]

    def predict(self, history, *, observed=None):
        """Return new-load probability and signed 100 ms impulse in N s for each history."""
        logit, reference, correction = self.components(history, observed=observed)
        return np.column_stack((sigmoid(logit), reference + correction))

    def predict_at_issue(self, values, bin_end_ticks, issue_tick, *, observed=None):
        history = history_at_issue(values, bin_end_ticks, issue_tick, observed=observed)
        return self.predict(history)
