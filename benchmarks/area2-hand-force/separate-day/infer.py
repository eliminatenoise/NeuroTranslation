"""Forecast planar hand displacement 100 ms after the issue time."""

import argparse
from pathlib import Path

import numpy as np


def forecasts(data, coefficients):
    motion, force, counts = (np.asarray(data[key], dtype=np.float64) for key in ("motion", "force", "counts"))
    rows = motion.shape[0] if motion.ndim else 0
    if not rows or motion.shape != (rows, 10, 2) or force.shape != (rows, 10, 3):
        raise ValueError("Supply ten hand-position pairs and ten three-axis force readings per row.")
    if counts.ndim != 3 or counts.shape[0] != rows or counts.shape[1] == 0 or counts.shape[2] != 10:
        raise ValueError("Supply ten event counts per Area 2 unit and at least one sorted unit per row.")
    if not all(np.isfinite(values).all() for values in (motion, force, counts)) or np.any(counts < 0):
        raise ValueError("Readings must be finite and event counts must be nonnegative.")

    activity = np.log1p(counts)
    summary = np.stack((activity.mean(axis=1), activity.std(axis=1), (counts > 0).mean(axis=1)), axis=-1)
    history = np.column_stack((motion.reshape(rows, 20), force.reshape(rows, 30)))
    history_with_activity = np.column_stack((history, summary.reshape(rows, 30)))

    def predict(history, name):
        mean, scale, weight, intercept = (
            coefficients[f"{name}_{field}"] for field in ("mean", "scale", "coefficient", "intercept")
        )
        return ((history - mean) / scale) @ weight + intercept

    motion_force = predict(history, "motion_force")
    pooled_area2 = predict(history_with_activity, "pooled_area2")
    difference = pooled_area2 - motion_force
    gate_inputs = np.log1p(np.column_stack((
        np.linalg.norm(motion[:, -1, :], axis=1),
        np.linalg.norm(force[:, -1, :] - force[:, 0, :], axis=1),
        np.linalg.norm(motion_force, axis=1),
        np.linalg.norm(difference, axis=1),
    )))
    normalized = np.clip((gate_inputs - coefficients["gate_mean"]) / coefficients["gate_scale"], -5, 5)
    gate = coefficients["gate_weights"]
    dynamic_weight = 1.0 / (1.0 + np.exp(-(gate[0] + normalized @ gate[1:])))
    estimates = {
        "stay_put": np.zeros_like(motion_force),
        "constant_velocity": -5.0 * motion[:, -1, :],
        "motion_force": motion_force,
        "pooled_area2": pooled_area2,
        "constant_mix": motion_force + float(coefficients["constant"]) * difference,
        "dynamic_mix": motion_force + dynamic_weight[:, None] * difference,
        "dynamic_weight": dynamic_weight,
    }
    if not all(np.isfinite(values).all() for values in estimates.values()):
        raise ValueError("The supplied readings or coefficients gave nonfinite forecasts.")
    return estimates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    weights = Path(__file__).with_name("blend-weights.npz")
    with np.load(args.inputs, allow_pickle=False) as data, np.load(weights, allow_pickle=False) as coefficients:
        estimates = forecasts(data, coefficients)
    with args.output.open("xb") as output:
        np.savez_compressed(output, **estimates)


if __name__ == "__main__":
    main()
