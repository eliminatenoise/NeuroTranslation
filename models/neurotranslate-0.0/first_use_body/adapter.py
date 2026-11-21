"""JSON entry point for the mixed 2-D landmark fit."""
import math
from pathlib import Path

import numpy as np

from .first_use import predict as forecast
from .forecaster import read_weights


def number(value, name):
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} exceeds the floating-point range") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def frames_from_json(frames):
    if not isinstance(frames, list) or not frames or not isinstance(frames[0], list) or not frames[0]:
        raise ValueError("xy must contain at least one frame of at least one 2-D landmark")
    size = len(frames[0])
    xy = np.full((len(frames), size, 2), np.nan)
    for i, frame in enumerate(frames):
        if not isinstance(frame, list) or len(frame) != size:
            raise ValueError("Keep the same landmark slots, in the same order, in every frame")
        for j, point in enumerate(frame):
            if point is None:
                continue
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(f"xy[{i}][{j}] must be [x, y] or null")
            for axis, value in enumerate(point):
                if value is not None:
                    xy[i, j, axis] = number(value, f"xy[{i}][{j}][{axis}]")
    return xy


def predict(record):
    if set(record) != {"domain", "seconds", "xy", "horizon_s"}:
        raise ValueError("first_use_body requires domain, seconds, xy and horizon_s")
    xy = frames_from_json(record["xy"])
    if not isinstance(record["seconds"], list) or len(record["seconds"]) != len(xy):
        raise ValueError("Supply one timestamp in seconds for every observed frame")
    seconds = [number(t, "timestamp") for t in record["seconds"]]
    horizon = number(record["horizon_s"], "horizon_s")
    target = number(seconds[-1] + horizon, "target time")
    model = read_weights(Path(__file__).with_name("mixed-weights.json"))
    try:
        with np.errstate(over="raise"):
            positions, methods = forecast(xy, seconds, horizon, model)
    except FloatingPointError as exc:
        raise ValueError("Coordinates or times exceed the numerical range of the model") from exc
    return {"landmarks": xy.shape[1], "origin_s": seconds[-1], "target_s": target,
            "horizon_s": horizon, "xy": [None if m == "unobserved" else p.tolist()
                                         for p, m in zip(positions, methods)],
            "method": methods.tolist()}
