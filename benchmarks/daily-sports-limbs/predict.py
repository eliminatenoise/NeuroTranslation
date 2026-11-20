"""Forecast the next reading 120 ms ahead for one selected DSADS accelerometer."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from broader_learner import configure_cpu_runtime
from model import HERE, PARTS, digest, estimate, load_checkpoint, observation


def parse_record(record, body_part):
    if type(record) is not dict or set(record) != {"body_part", "timestamps_ms", "samples"}:
        raise ValueError("Expected body_part, timestamps_ms and samples")
    if body_part not in PARTS or record["body_part"] != body_part:
        raise ValueError("The requested body part must match the input sensor placement")
    times = record["timestamps_ms"]
    if (not isinstance(times, list) or len(times) != 16 or any(type(t) is not int for t in times)
            or any(b - a != 40 for a, b in zip(times, times[1:]))):
        raise ValueError("Provide 16 increasing integer millisecond timestamps, 40 ms apart")
    raw = record["samples"]
    if (not isinstance(raw, list) or len(raw) != 16 or any(
        not isinstance(row, list) or len(row) != 3 or any(type(v) not in (int,float) for v in row)
        for row in raw)):
        raise ValueError("Provide 16 complete [X, Y, Z] rows, oldest first")
    values = np.array(raw, dtype=np.float64)
    if not np.isfinite(values).all() or (abs(values) > np.finfo(np.float32).max).any():
        raise ValueError("Sensor readings must be finite and representable as float32")
    return values, times[-1] + 120


def forecast(model, state, record, body_part):
    values, target_time = parse_record(record, body_part)
    obs, query = observation(body_part, ("input-window",), np.array([15]), values[None], "DEV")
    mu, var = estimate(model, body_part, obs, query)
    norm = state["stats"][body_part]
    first, scale = np.array(norm["center"]), np.array(norm["scale"])
    weights = state["ridge"][body_part]
    residual = ((values-first)/scale).reshape(-1) @ weights["coef"].numpy() + weights["intercept"].numpy()
    r = values[-1] + residual * scale
    if not np.isfinite(r).all():
        raise ValueError("Ridge forecast outside finite numeric range")
    return {"body_part":body_part, "axis_order":["X","Y","Z"], "target_timestamp_ms":target_time,
            "lead_ms":120, "units":"stored accelerometer values in this sensor's own frame",
            "shared_forecast":mu[0].tolist(), "model_std_xyz":np.sqrt(var[0]).tolist(),
            "persistence":values[-1].tolist(), "ridge":r.tolist()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("body_part", choices=PARTS)
    p.add_argument("input", type=Path)
    args = p.parse_args()
    configure_cpu_runtime(1, 1, True)
    try:
        checkpoint = HERE / "model.pt"
        if digest(checkpoint) != json.loads((HERE/"results.json").read_text())["checkpoint_sha256"]:
            raise ValueError("Different model checkpoint")
        m, state = load_checkpoint(checkpoint)
        result = forecast(m, state, json.loads(args.input.read_text()), args.body_part)
    except (OSError, KeyError, ValueError, RuntimeError, FloatingPointError, OverflowError) as err:
        p.exit(2, f"Prediction failed: {err}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
