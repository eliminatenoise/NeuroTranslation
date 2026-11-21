"""Right-wrist methods fitted on the earliest sixteen selected training events."""

from itertools import product
import numpy as np
import attention
from bilateral import side_features

BANDS = ((8, 32), (76, 100))


def features(ecog, prior):
    # Positions: (event, time, joint, xy). ECoG/pose feature construction uses only
    # samples strictly earlier than the selected retrospective onset.
    neural = ecog.astype(np.float64, copy=False)
    centered = neural - neural.mean(axis=1, keepdims=True)
    window = np.hanning(neural.shape[1])
    freq = np.fft.rfftfreq(neural.shape[1], 1 / 500)
    spectrum = np.abs(np.fft.rfft(centered * window[None, :, None], axis=1)) ** 2 / (
        window @ window
    )
    bandpowers = [spectrum[:, (freq >= lo) & (freq <= hi), :].mean(axis=1) for lo, hi in BANDS]
    neural_x = np.log(np.maximum(np.concatenate(bandpowers, axis=1), 1e-12))
    p = prior.astype(np.float64, copy=False)
    relative = p[:, -1, :2, :] - p[:, -1, 2:3, :]
    movement = p[:, -1] - p[:, 0]
    pose_x = np.concatenate((relative.reshape(len(p), 4), movement.reshape(len(p), 6)), axis=1)
    velocity = movement[:, 0, None, :] * np.array([8, 15])[None, :, None] / 14
    return {
        "neural": neural_x,
        "pose": pose_x,
        "combined": np.column_stack((neural_x, pose_x)),
    }, velocity


def ridge_fit(x, y):
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < np.finfo(np.float64).eps] = 1.0
    z = (x - mean) / scale
    offset = y.mean(axis=0)
    gram = z.T @ z
    weight = np.linalg.solve(gram + 16.0 * np.eye(gram.shape[0]), z.T @ (y - offset))
    return dict(x_mean=mean, x_scale=scale, y_mean=offset, coef=weight)


def training(arrays):
    """The historical fits all used the first 16 eligible right-wrist events."""
    e = arrays["ecog_uv"][:16].astype(np.float64)
    p = arrays["prior_pose_px"][:16, :, :3].astype(np.float64)
    y = (arrays["future_wrist_px"][:16, :, 0] - p[:, -1, 0, None]).reshape(-1, 4)
    if len(p) != 16 or not all(np.isfinite(x).all() for x in (e, p, y)):
        raise ValueError("Historical fit requires sixteen complete right-wrist examples")
    spectral, vel = features(e, p)
    vel = vel.reshape(-1, 4)
    raw, _, _ = side_features(e, p)
    weights = {"train_mean": y.mean(axis=0)}
    for name, x in spectral.items():
        for key, value in ridge_fit(x, y).items():
            weights["spectral_" + name + "__" + key] = value
    for modality, treatment in product(("pose", "combined"), ("direct", "residual")):
        stem = f"{modality}_{treatment}"
        tokens, normalized, prior, stats = attention.prepare(raw, vel, y, modality, treatment)
        _, linear = attention.linear(tokens, y, prior)
        weights.update({stem + "__" + key: value for key, value in stats.items()})
        weights.update({"ridge_" + stem + "__" + key: value for key, value in linear.items()})
        for seed in attention.SEEDS:
            name = stem + "_" + str(seed)
            params, _, loss = attention.native_fit(
                tokens, normalized, attention.initial(seed), "cpu"
            )
            weights.update({name + "__" + key: value for key, value in params.items()})
            weights[name + "__loss"] = loss
    return weights


def forecast(data, weights):
    e = data["ecog_uv"].astype(float)
    p = data["prior_pose_px"][:, :, :3].astype(float)
    ok = (
        np.isfinite(e).all((1, 2))
        & np.isfinite(p).all((1, 2, 3))
        & ~(e == 0).all(2).any(1)
        & (np.ptp(e, axis=1) > 0).any(1)
    )
    e[~ok] = 0
    p[~ok] = 0
    spectral, velocity = features(e, p)
    vel = velocity.reshape(len(p), 4)
    raw, anchor, _ = side_features(e, p)
    deltas = {
        "zero": np.zeros_like(vel),
        "velocity": vel,
        "half_velocity": 0.5 * vel,
        "train_mean": np.broadcast_to(weights["train_mean"], vel.shape),
    }
    for name, x in spectral.items():
        stem = "spectral_" + name
        standardized = (x - weights[stem + "__x_mean"]) / weights[stem + "__x_scale"]
        deltas[stem] = standardized @ weights[stem + "__coef"] + weights[stem + "__y_mean"]
    for modality, treatment in product(("pose", "combined"), ("direct", "residual")):
        stem = f"{modality}_{treatment}"
        x = (raw - weights[stem + "__feature_mean"]) / weights[stem + "__feature_scale"]
        if modality == "pose":
            x[:, :, 10:] = 0
        prior = 0.5 * vel if treatment == "residual" else np.zeros_like(vel)
        ridge = "ridge_" + stem
        deltas[ridge] = (
            (x.reshape(len(x), -1) - weights[ridge + "__zmean"]) @ weights[ridge + "__coef"]
            + weights[ridge + "__offset"]
            + prior
        )
        for seed in attention.SEEDS:
            name = stem + "_" + str(seed)
            params = {k: weights[name + "__" + k] for k in attention.initial(seed)}
            deltas[name] = (
                attention.np_forward(x, params) * weights[stem + "__scale"]
                + weights[stem + "__center"]
                + prior
            )
    out = {}
    for key, value in deltas.items():
        full = np.full((len(vel), 2, 2, 2), np.nan)
        full[ok, :, 0, :] = value[ok].reshape(-1, 2, 2) + anchor[ok, None]
        out["legacy_" + key] = full
    return out
