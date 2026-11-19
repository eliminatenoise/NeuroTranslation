"""Fixed two-coefficient residual calibration for labeled Day 1 voltage arrays."""

from dataclasses import dataclass

import numpy as np

PENALTY = 0.1
FLOOR_V = 1e-12


@dataclass(frozen=True)
class Adapter:
    offset_v: float
    slope: float

    def predict(self, current, pooled):
        return pooled + self.offset_v + self.slope * (pooled - current)


def calibrate(current, pooled, target):
    """Use only Day 1 labels to solve the fixed, two-column ridge problem."""
    current = np.asarray(current, dtype=np.float64)
    pooled = np.asarray(pooled, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if (current.ndim != 1 or len(current) == 0 or current.shape != pooled.shape
            or current.shape != target.shape or not np.isfinite([current, pooled, target]).all()):
        raise ValueError("Calibration requires identical, finite labeled vectors")
    with np.errstate(over="ignore", invalid="ignore"):
        delta = pooled - current
        rms = float(np.sqrt(np.mean(delta * delta)))
    if not np.isfinite(rms):
        raise ValueError("Nonfinite pooled voltage change scale")
    scale = max(FLOOR_V, rms)
    q = delta / scale
    e = target - pooled
    mean_q = float(np.mean(q))
    a = 1 + PENALTY
    c = float(np.mean(q * q)) + PENALTY
    u = float(np.mean(e))
    v = float(np.mean(q * e))
    determinant = a * c - mean_q * mean_q
    offset = (c * u - mean_q * v) / determinant
    slope = (a * v - mean_q * u) / determinant / scale
    if not np.isfinite([offset, slope]).all():
        raise ValueError("Nonfinite adapter calibration")
    return Adapter(offset, slope)
