"""History-only geometry in one local frame; cm and elapsed source-native seconds."""
import numpy as np

TAPS = np.array([-1.0, -0.75, -0.5, -0.25, 0.0])
AGE = 0.05
EPS = 1e-10


def history_tokens(positions_cm, history_s, cutoff_s):
    """Four invariant tokens from five admitted observations in one 2D/3D frame.

    Caller verifies visibility, source identity, intervening clocks and eligibility.
    history_s is time on the same source/acquisition clock as cutoff_s.
    """
    pos = np.asarray(positions_cm, dtype=np.float64)
    tm = np.asarray(history_s, dtype=np.float64)
    if pos.shape not in ((5, 2), (5, 3)) or tm.shape != (5,) or not np.isscalar(cutoff_s):
        raise ValueError('Expected five 2D or 3D positions and five source times')
    ages = float(cutoff_s) + TAPS - tm
    if not (np.isfinite(pos).all() and np.isfinite(ages).all() and np.all(ages >= 0) and np.all(ages <= AGE + EPS)):
        raise ValueError('Non-finite, late or stale history')
    dt = np.diff(tm)
    if np.any(dt <= 0):
        raise ValueError('Source times must be strictly increasing')
    steps = np.diff(pos, axis=0)
    chord = np.linalg.norm(steps, axis=1)
    dots = np.sum(steps[:-1] * steps[1:], axis=1)
    lengths = chord[:-1] * chord[1:]
    cosine = np.divide(dots, lengths, where=lengths > 0, out=np.zeros(3))
    return np.column_stack((chord, dt, ages[1:], np.r_[0.0, np.linalg.norm(pos[2:] - pos[:-2],axis=1)],np.r_[0.0,np.clip(cosine,-1,1)]))
