"""Forecast the right-arm accelerometer axes 120 ms ahead from 16 XYZ samples."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from forecast import HERE, digest, load, predict_all


CHECKPOINT_HASH = "96018afd0b6f5e38f6af721a540a1b6bca55b0f4c7c4a321c535b3d2722d873b"


def read_history(path):
    with path.open(encoding="utf-8") as stream:
        rows = json.load(stream)
    if not (isinstance(rows, list) and len(rows) == 16 and
            all(isinstance(row, list) and len(row) == 3 and
                all(type(v) in (int, float) for v in row) for row in rows)):
        raise ValueError("Expected 16 consecutive [X, Y, Z] rows of JSON numbers, oldest first.")
    history = np.asarray(rows, dtype=np.float64)
    if not np.isfinite(history).all():
        raise ValueError("Every sensor reading must be finite.")
    return history


def forecast_file(path):
    history = read_history(path)
    checkpoint = HERE / "model.pt"
    if digest(checkpoint) != CHECKPOINT_HASH:
        raise ValueError("model.pt differs from the released checkpoint.")
    model, state = load(checkpoint)
    if digest(HERE / "forecast.py") != state["implementation"]:
        raise ValueError("forecast.py differs from the implementation used for the checkpoint.")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        estimates = predict_all(model, state, history[None])
    if not all(np.isfinite(values).all() for values in estimates.values()):
        raise ValueError("Input is outside the model's representable range.")
    return {"lead_ms": 120, "axis_order": ["X", "Y", "Z"], "units": "native sensor units",
            "forecasts": {name: values[0].tolist() for name, values in estimates.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="one JSON array with exactly 16 consecutive XYZ readings")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    try:
        result = forecast_file(args.input)
    except (OSError, ValueError, FloatingPointError, OverflowError) as error:
        parser.exit(2, f"Prediction failed: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
