"""Bilateral 30-token Transformer and five kinematic control rules."""
import numpy as np

HORIZONS = (8, 15)
SEEDS = (17, 43, 97)
SIDE = np.repeat(np.arange(2), 15)
OTHER = SIDE[:, None] != SIDE[None, :]
LAST = [14, 29]
MODES = ("intact", "blocked", "trained_swap")
BASES = ("zero", "mean_px", "mean_normalized", "constant_velocity", "kinematic_ridge")


def geometry(pose):
    x = np.asarray(pose, dtype=np.float64)
    if x.ndim != 4 or x.shape[1:] != (15, 6, 2):
        raise ValueError("prior_pose_px requires shape [N,15,6,2]")
    p = x.reshape(-1, 15, 2, 3, 2)
    wrist, elbow, shoulder = (p[:, :, :, j] for j in range(3))
    fore, upper = wrist - elbow, elbow - shoulder
    scale = np.median(np.linalg.norm(upper, axis=-1) + np.linalg.norm(fore, axis=-1), axis=1)
    valid = np.isfinite(p).all(axis=(1, 3, 4)) & np.isfinite(scale) & (scale > 1e-6)
    scale = np.where(valid, scale, np.nan)
    features = np.concatenate((fore, upper, shoulder - shoulder[:, -1:], wrist - wrist[:, -1:]), axis=-1)
    features = (features / scale[:, None, :, None]).transpose(0, 2, 1, 3)
    return features, scale, wrist[:, -1], shoulder[:, -1], valid


def earlier_donors(usable):
    """Indices into one chronological partition. Holes stay in their native positions."""
    result = np.full(len(usable), -1, int)
    previous = -1
    for i, valid in enumerate(usable):
        result[i] = previous
        if valid:
            previous = i
    return result


def ridge_design(pose):
    p = pose.reshape(-1, 15, 2, 3, 2)
    wrist, elbow, shoulder = (p[:, :, :, j] for j in range(3))
    series = np.stack((shoulder, elbow - shoulder, wrist - elbow), axis=-2)
    slopes = []
    for window in (4, 8, 15):
        t = np.arange(window) - (window - 1) / 2
        slopes.append(np.einsum("t,ntsja->nsja", t, series[:, -window:]) / (t @ t))
    # Axis-specific predictors include both image coordinates, for a fixed 18-vector per arm.
    return np.stack(slopes, axis=-2).reshape(len(p), 2, 18)


def network(features, weights, blocked):
    n = len(features)
    x = features @ weights["input"] + weights["input_bias"]
    x += weights["side"][None, :, None] + weights["time"][None, None]
    x = x.reshape(n, 30, 12)
    q, k, v = [(x @ weights[name]).reshape(n, 30, 2, 6).transpose(0, 2, 1, 3)
               for name in ("query", "key", "value")]
    logits = q @ k.swapaxes(-2, -1) / np.sqrt(6)
    logits += weights["other_bias"][None, :, None, None] * OTHER
    if blocked:
        logits = np.where(OTHER, -np.inf, logits)
    prob = np.exp(logits - logits.max(axis=-1, keepdims=True))
    prob /= prob.sum(axis=-1, keepdims=True)
    context = (prob @ v).transpose(0, 2, 1, 3).reshape(n, 30, 12)
    x = x + context @ weights["out"]
    x = x + np.tanh(x @ weights["ff_in"] + weights["ff_bias"]) @ weights["ff_out"]
    final = x[:, LAST]
    delta = np.tanh(final @ weights["decode"] + weights["decode_bias"])
    gate_logit = final @ weights["gate"] + weights["gate_bias"]
    gate = 1 / (1 + np.exp(-np.clip(gate_logit, -700, 700)))
    return (0.5 * gate * delta).reshape(n, 2, 2, 2).transpose(0, 2, 1, 3)


def corrections(features, weights, mode, donor_features=None):
    if mode in ("trained_swap", "intact_swapped"):
        if donor_features is None or features.shape != donor_features.shape:
            raise ValueError("A separately matched earlier donor is required for each event")
        return np.stack([
            network(np.stack((features[:, 0], donor_features[:, 1]), axis=1), weights, False)[:, :, 0],
            network(np.stack((donor_features[:, 0], features[:, 1]), axis=1), weights, False)[:, :, 1],
        ], axis=2)
    if mode not in ("intact", "blocked"):
        raise ValueError("Unknown Transformer mode")
    return network(features, weights, mode == "blocked")


def baseline(pose, prior, name):
    _, scale, wrist, _, _ = geometry(pose)
    if name == "zero":
        return np.zeros((len(pose), 2, 2, 2))
    if name == "mean_normalized":
        return np.broadcast_to(prior["mean"], (len(pose), 2, 2, 2))
    if name == "mean_px":
        return prior["mean_px"] / scale[:, None, :, None]
    if name == "constant_velocity":
        velocity = (wrist - pose[:, -5, [0, 3]]) / 4
        return np.stack([velocity * h / scale[:, :, None] for h in HORIZONS], axis=1)
    if name == "kinematic_ridge":
        design = ridge_design(pose) / scale[:, :, None]
        return np.stack([np.einsum("nsf,sfa->nsa", design * h, prior["ridge"][i])
                         + prior["ridge_bias"][i] for i, h in enumerate(HORIZONS)], axis=1)
    raise ValueError("Unknown baseline")


def outputs(displacement, scale, wrist, shoulder):
    change_px = displacement * scale[:, None, :, None]
    future = wrist[:, None] + change_px
    rooted = (wrist - shoulder)[:, None] / scale[:, None, :, None] + displacement
    initial_span = np.linalg.norm(wrist[:, 0] - wrist[:, 1], axis=-1)
    span = np.linalg.norm(future[:, :, 0] - future[:, :, 1], axis=-1) - initial_span[:, None]
    return {"displacement_normalized": displacement, "endpoint_px": future,
            "endpoint_from_last_shoulder_normalized": rooted, "span_change_px": span}
