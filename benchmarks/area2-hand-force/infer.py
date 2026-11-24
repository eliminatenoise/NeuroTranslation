"""Apply the frozen Area 2 movement comparison to correctly ordered past samples."""

import argparse
from pathlib import Path
import numpy as np

ARMS = {
    "motion": ("motion",),
    "motion_force": ("motion", "force"),
    "motion_area2": ("motion", "counts"),
    "motion_force_area2": ("motion", "force", "counts"),
}
SHAPES = {"motion": (10, 2), "force": (10, 3), "counts": (65, 10)}


def forecasts(data, coefficients):
    rows = data["motion"].shape[0]
    for name, expected in SHAPES.items():
        values = data[name]
        if values.shape != (rows, *expected) or not np.isfinite(values).all():
            raise ValueError(f"Unexpected shape or nonfinite values in {name}.")
    estimates = {
        "stay_put": np.zeros((rows, 2)),
        "constant_velocity": -5.0 * data["motion"][:, -1, :],
    }
    for name, parts in ARMS.items():
        history = np.column_stack([data[key].reshape(rows, -1) for key in parts])
        mean, scale, weight, intercept = (
            coefficients[f"{name}_{field}"] for field in ("mean", "scale", "coefficient", "intercept")
        )
        estimates[name] = (history - mean) / scale @ weight + intercept
    return estimates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    weights = Path(__file__).with_name("linear-weights.npz")
    with np.load(args.inputs, allow_pickle=False) as data, np.load(weights, allow_pickle=False) as coefficients:
        estimates = forecasts(data, coefficients)
    with args.output.open("xb") as output:
        np.savez_compressed(output, **estimates)


if __name__ == "__main__":
    main()
