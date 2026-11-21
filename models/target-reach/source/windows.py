"""Native 250-Hz source sample selection. Inputs can only look backward from their cutoff."""

import numpy as np

RATE = 250
INPUT_MS = np.array([0, 50, 100, 150, 200], dtype=int)
OUTPUT_MS = np.array([400, 600, 800], dtype=int)


def positions(markers):
    """Return a stable set of measured markers chosen from the first usable frame alone."""
    available = np.isfinite(markers).all(axis=2)
    rows = np.flatnonzero(available.any(axis=1))
    if not len(rows):
        return None, None, None
    anchor = int(rows[0])
    chosen = available[anchor]
    xyz = np.full((len(markers), 3), np.nan)
    mask = available[:, chosen].all(axis=1)
    xyz[mask] = markers[mask][:, chosen].mean(axis=1)
    return anchor, np.flatnonzero(chosen), xyz


def select_window(frame, xyz, anchor):
    """Input at or before nominal time by <= one period; output at or after within one period."""
    frame_ticks = frame - frame[anchor]
    ticks_ms_num = frame_ticks * 1000
    known = np.flatnonzero(np.isfinite(xyz).all(axis=1))
    known_time = ticks_ms_num[known]
    target = INPUT_MS * RATE
    j = np.searchsorted(known_time, target, side="right") - 1
    if np.any(j < 0) or np.any(target - known_time[j] > 1000):
        return None
    history = known[j]
    target = OUTPUT_MS * RATE
    j = np.searchsorted(known_time, target, side="left")
    outcomes = np.full((len(target), 3), np.nan)
    target_time = np.full(len(target), np.nan)
    valid = np.zeros(len(target), dtype=bool)
    for k, row in enumerate(j):
        if row < len(known) and known_time[row] - target[k] <= 1000:
            actual = known[row]
            outcomes[k] = (xyz[actual] - xyz[history[-1]]) / 1000
            target_time[k] = frame_ticks[actual] / RATE
            valid[k] = True
    return {
        "time": frame_ticks[history] / RATE,
        "xyz": xyz[history] / 1000,
        "y": outcomes,
        "valid": valid,
        "target_time": target_time,
    }


def crossing(frame, xyz, anchor):
    """First confirmed >=15 mm displacement in three consecutive native frames."""
    beyond = np.linalg.norm(xyz - xyz[anchor], axis=1) >= 15
    consecutive = np.diff(frame) == 1
    confirmed = np.flatnonzero(
        beyond[:-2] & beyond[1:-1] & beyond[2:] & consecutive[:-1] & consecutive[1:]
    )
    return int(confirmed[0] + 2) if len(confirmed) else None
