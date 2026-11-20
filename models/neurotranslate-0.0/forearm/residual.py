"""A person-balanced additive correction to a frozen two-angle forecast."""
import numpy as np

ARMS = {"motion": 2, "emg": 6}


def features(bins, anchor, forecast, arm):
    """Continuous covariates in physical units; no participant or future inputs."""
    if arm not in ARMS:
        raise ValueError("Choose a motion or emg correction")
    bins = np.asarray(bins, dtype=np.float64)
    anchor = np.asarray(anchor, dtype=np.float64)
    forecast = np.asarray(forecast, dtype=np.float64)
    n = len(bins)
    if n == 0 or bins.shape != (n, 16, ARMS[arm]) or anchor.shape != (n, 2) or forecast.shape != (n, 2):
        raise ValueError("Wrong number of bins, channels or angular axes")
    if not all(np.isfinite(x).all() for x in (bins, anchor, forecast)):
        raise ValueError("Forecasts and measurements must be finite")
    parts = [bins[:, :, :2].reshape(n, 32), anchor, forecast - anchor]
    if arm == "emg":
        if np.any(bins[:, :, 2:] < 0):
            raise ValueError("RMS amplitudes must be nonnegative")
        parts.append(bins[:, :, 2:].reshape(n, 64))
    return np.column_stack(parts)


def design(continuous, slot, state):
    slot = np.asarray(slot)
    if slot.shape != (len(continuous),) or slot.dtype.kind not in "iu" or np.any((slot < 0) | (slot > 5)):
        raise ValueError("Expected one integer cue slot 0 through 5 per row")
    scaled = (continuous - state["center"]) / state["scale"]
    return np.column_stack((scaled, np.eye(6)[slot]))


def apply(bins, anchor, forecast, slot, arm, state):
    x = design(features(bins, anchor, forecast, arm), slot, state)
    return forecast + x @ state["coef"]


def estimate(bins, anchor, forecast, slot, target, person, arm):
    """The caller supplies forecasts cross-fitted within just these people."""
    continuous = features(bins, anchor, forecast, arm)
    scale = continuous.std(axis=0)
    state = {"center": continuous.mean(axis=0), "scale": np.where(scale == 0., 1., scale)}
    x = design(continuous, slot, state)
    people, inverse, counts = np.unique(person, return_inverse=True, return_counts=True)
    weights = 1. / (len(people) * counts[inverse])
    xtw = x.T * weights
    penalty = np.r_[np.full(continuous.shape[1], .01), np.zeros(6)]
    gram = xtw @ x + np.diag(penalty)
    rhs = xtw @ (target - forecast)
    coef = np.linalg.solve(gram, rhs)
    if not np.isfinite(coef).all() or np.max(np.abs(gram @ coef - rhs)) > 1e-8:
        raise ArithmeticError("Ridge solution failed stationarity")
    return {**state, "coef": coef}
