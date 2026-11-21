"""Start with visible landmarks on frame one and use the trained model as history arrives."""
from pathlib import Path

import numpy as np

from forecaster import HISTORY, PROTOCOL, forecast, read_weights


def predict(xy, seconds, horizon_s, weights):
    """Return (positions, per-point method) for the most recent observation."""
    xy, seconds = np.asarray(xy, dtype=float), np.asarray(seconds, dtype=float)
    if xy.ndim != 3 or xy.shape[-1] != 2 or not xy.shape[0] or not xy.shape[1]:
        raise ValueError("Pass one or more frames of K 2-D landmarks")
    if seconds.shape != xy.shape[:1] or not np.isfinite(seconds).all() or np.any(np.diff(seconds)<=0):
        raise ValueError("Pass one increasing timestamp in seconds for each frame")
    if not np.isfinite(horizon_s) or horizon_s <= 0:
        raise ValueError("Pass a positive forecast horizon in seconds")
    available = np.isfinite(xy[-1]).all(1)
    positions = np.full_like(xy[-1], np.nan)
    positions[available] = xy[-1,available]
    methods = np.where(available, "last_position", "unobserved").astype("U16")
    if len(xy) >= HISTORY:
        t = seconds[-HISTORY:]
        if t[-1]-t[0] <= PROTOCOL["maximum_history_span_s"] and np.max(np.diff(t)) <= PROTOCOL["maximum_interframe_gap_s"]:
            learned = forecast(xy[-HISTORY:],t,horizon_s,weights)
            supported = np.isfinite(learned).all(1)
            positions[supported] = learned[supported]
            methods[supported] = "learned"
    return positions, methods


def fictional():
    """An invented geometric figure moves across a plane. Units and time are illustrative."""
    angles = np.linspace(0, 2*np.pi, 7, endpoint=False)
    start = np.column_stack([np.cos(angles), .4*np.sin(angles)])
    t = np.arange(5) * .025
    xy = np.stack([start + [3*z, -2*z] + .1*z*np.column_stack([np.cos(2*angles),np.sin(2*angles)])
                   for z in t])
    xy[:3,0] = np.nan
    xy[-1,-1] = np.nan
    return xy,t


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights",type=Path,default=Path(__file__).with_name("mixed-weights.json"))
    args=parser.parse_args()
    weights=read_weights(args.weights)
    xy,t=fictional()
    for length in (1,5):
        positions, methods=predict(xy[:length],t[:length],.12,weights)
        print(f"{length} observed frame(s), +120 ms; fictional positions and method used per point")
        for i,(point,method) in enumerate(zip(positions,methods)):
            print(f"{i+1:2}  {point}  {method}")
