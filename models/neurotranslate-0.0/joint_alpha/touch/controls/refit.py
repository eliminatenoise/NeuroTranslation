"""Refit the four sensory-spike controls on a prepared Delhaye training split."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from predict import MODELS, features

PENALTY = 0.01
TRAIN_PEOPLE = {"U101", "U103", "U104", "U107", "U109", "U112", "U115"}


def loss(coef, design, y):
    eta = design @ coef[1:] + coef[0]
    rate = np.exp(eta)
    error = rate - y
    value = (rate - y * eta).mean() + (PENALTY / 2) * np.dot(coef[1:], coef[1:])
    grad = np.r_[error.mean(), design.T @ error / len(y) + PENALTY * coef[1:]]
    return value, grad


def fit_model(features_, y):
    mean = features_.mean(axis=0)
    scale = features_.std(axis=0)
    scale[scale < 1e-10] = 1.
    design = np.ascontiguousarray((features_ - mean) / scale)
    start = np.zeros(design.shape[1] + 1)
    start[0] = np.log(y.mean())
    result = minimize(loss, start, args=(design, y), method="L-BFGS-B", jac=True,
                      options={"maxiter": 300, "ftol": 1e-12, "gtol": 1e-7})
    if not result.success or not np.isfinite(result.x).all():
        raise ValueError(f"Fit failed: {result.message}")
    if abs(result.jac[0]) > 1e-5:
        raise ValueError("Intercept calibration failed")
    model = {"mean": mean.tolist(), "scale": scale.tolist(), "intercept": float(result.x[0]),
             "slopes": result.x[1:].tolist()}
    fit = {"iterations": int(result.nit), "optimizer_message": str(result.message),
           "train_objective_without_factorial": float(result.fun), "abs_gradient_max": float(np.max(abs(result.jac))),
           "training_mean_prediction_minus_observed": float(result.jac[0])}
    return model, fit


def refit(path):
    with np.load(path, allow_pickle=False) as src:
        if set(np.unique(src["group"]).tolist()) != TRAIN_PEOPLE:
            raise ValueError("Refit requires exactly the seven preregistered training people")
        designs = features(src["X"], src["previous_repeat_force"])
        y = src["y"]
    if y.shape != (len(y), 1) or not np.isin(y, np.arange(21)).all():
        raise ValueError("Expected a count of 0–20 spikes per future 20 ms window")
    y = y[:, 0].astype(np.float64)
    models = {MODELS[0]: {"mean_spikes_per_bin": float(y.mean())}}
    for name, design in designs.items():
        models[name], _ = fit_model(design, y)
    with Path(path).open("rb") as f:
        source_hash = hashlib.file_digest(f, "sha256").hexdigest()
    return {"format": 1, "task": "human_touch_afferent", "unit": "expected spikes in (t+20,t+40] ms",
            "training": {"people": sorted(TRAIN_PEOPLE), "rows": len(y), "archive_sha256": source_hash},
            "models": models}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_npz", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    bundle = refit(args.training_npz)
    with args.output_json.open("x") as f:
        json.dump(bundle, f, indent=2, allow_nan=False)
        f.write("\n")
