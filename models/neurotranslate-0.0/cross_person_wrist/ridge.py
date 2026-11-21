"""Four role-and-horizon ridge regressions with three frozen velocity and persistence controls."""
import numpy as np

from .reference import ROLES
from .temporal import HORIZONS

PRIMARY = ("ridge", "damped_velocity", "velocity", "persistence")


def features(arm):
    return (arm - arm[-1, 0]).reshape(-1)


def velocity(arm, horizon):
    return (arm[-1, 0] - arm[0, 0]) * (horizon / 14)


def fit_heads(training):
    heads = {}
    for role in ROLES:
        for k, horizon in enumerate(HORIZONS):
            rows = []
            for sample, targets in training:
                arm = sample.arms.get(role)
                if arm is None or not np.isfinite(targets[role][k]).all():
                    continue
                delta = sample.frame.encode(targets[role][k]) - arm[-1, 0]
                rows.append((features(arm), delta, velocity(arm, horizon)))
            name = f"{role}_{horizon}"
            if not rows:
                heads[name] = {"count": 0}
                continue
            x, y, v = (np.stack(a) for a in zip(*rows))
            mean, std = x.mean(axis=0), x.std(axis=0)
            std[std < 1e-8] = 1
            z = (x - mean) / std
            bias = y.mean(axis=0)
            coef = np.linalg.solve(z.T @ z + len(rows) * np.eye(x.shape[1]), z.T @ (y-bias))
            denominator = float(np.sum(v*v))
            gain = float(np.clip(np.sum(v*y)/denominator, 0, 1)) if denominator else 0.
            heads[name] = dict(count=len(rows), mean=mean, std=std, coef=coef, bias=bias, gain=gain)
    return heads


def endpoints(arm, horizon, head):
    v = velocity(arm, horizon)
    z = (features(arm) - head["mean"]) / head["std"]
    shifts = (z @ head["coef"] + head["bias"], head["gain"] * v, v, np.zeros(2))
    return {name: arm[-1, 0] + delta for name, delta in zip(PRIMARY, shifts)}
