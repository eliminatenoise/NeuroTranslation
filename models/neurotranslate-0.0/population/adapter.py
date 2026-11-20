"""Quarter-second histories in native seconds and centimetres; CA1 precedes PFC."""
import numpy as np


TAPS = np.arange(-4, 1, dtype=np.float64) * 0.25


def camera_tokens(cutoff_s, prior_time_s, prior_xy_cm):
    cutoff, times, xy = (np.asarray(a, dtype=np.float64) for a in (cutoff_s, prior_time_s, prior_xy_cm))
    if cutoff.ndim == 0:
        cutoff, times, xy = cutoff[None], times[None], xy[None]
    if cutoff.ndim != 1 or not len(cutoff) or times.shape != (len(cutoff), 5) or xy.shape != (len(cutoff), 5, 2):
        raise ValueError("Each forecast needs one cutoff, five source times and five 2D camera positions in cm")
    ages = cutoff[:, None] + TAPS - times
    duration = np.diff(times, axis=1)
    if (not np.isfinite(xy).all() or not np.isfinite(ages).all() or (duration <= 0).any()
            or (ages < -1e-9).any() or (ages > 0.075000001).any()):
        raise ValueError("Camera samples must be finite, strictly ordered and within 75 ms before their taps")
    steps = np.diff(xy, axis=1)
    length = np.linalg.norm(steps, axis=2)
    two_step = np.zeros_like(length)
    two_step[:, 1:] = np.linalg.norm(xy[:, 2:] - xy[:, :-2], axis=2)
    denom = length[:, 1:] * length[:, :-1]
    cosine = np.zeros_like(length)
    np.divide((steps[:, 1:] * steps[:, :-1]).sum(axis=2), denom, out=cosine[:, 1:], where=denom > 0)
    scaled_speed = 0.25 * length / duration
    tokens = np.stack([np.log1p(length), (duration - 0.25) / 0.05, ages[:, 1:] / 0.05,
                       np.log1p(two_step), np.clip(cosine, -1, 1), np.log1p(scaled_speed)], axis=2)
    if not np.isfinite(tokens).all():
        raise ValueError("Camera geometry exceeds the numeric range")
    return tokens, scaled_speed


def rates_for_bins(counts, units, batch_size):
    counts, units = (np.asarray(a, dtype=np.float64) for a in (counts, units))
    if counts.ndim == 2 and units.ndim == 1:
        counts, units = counts[None], units[None]
    if counts.shape != (batch_size, 4, 2) or units.shape != (batch_size, 2):
        raise ValueError("Each forecast needs four paired CA1/PFC count bins and two unit denominators")
    if (not np.isfinite(counts).all() or not np.isfinite(units).all() or (counts < 0).any()
            or (units <= 0).any() or (counts != np.floor(counts)).any() or (units != np.floor(units)).any()):
        raise ValueError("Spike counts must be nonnegative integers and unit counts must be positive integers")
    return np.log1p(counts / (0.25 * units[:, None, :]))


def readout_features(scaled_speed, states, rat_correction, rates=None):
    motion = np.column_stack((scaled_speed, states[:, -1, :]))
    if rates is None:
        return motion
    conditioned = rates * rat_correction[:, :, None]
    return np.column_stack((motion, rates.reshape(len(rates), 8), conditioned.reshape(len(rates), 8)))


def ridge_prediction(features, state):
    return np.maximum(0, ((features - state['mean']) / state['scale']) @ state['coef'] + state['intercept'])
