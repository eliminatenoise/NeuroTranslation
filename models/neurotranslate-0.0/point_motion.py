"""Forecast a single marker's 200 ms displacement from nine positions 50 ms apart."""
import numpy as np

MODES = ("stationary", "velocity", "previous", "linear", "radial", "shared", "shuffled")
LEARNED = MODES[3:]


def coordinates(position):
    step = np.diff(position, axis=1)
    horizontal = position[:, -1, :2] - position[:, 0, :2]
    length = np.hypot(horizontal[:, 0], horizontal[:, 1])
    heading = np.zeros_like(horizontal)
    heading[:, 0] = 1
    np.divide(horizontal, length[:, None], out=heading, where=(length >= 1)[:, None])
    c, s = heading[:, 0, None], heading[:, 1, None]
    aligned = np.stack((step[:, :, 0]*c + step[:, :, 1]*s,
                        step[:, :, 1]*c - step[:, :, 0]*s, step[:, :, 2]), axis=-1)
    return aligned.reshape(-1, 4, 6), heading


def transform(v, heading, *, inverse=False):
    c, s = heading.T
    if inverse:
        s = -s
    return np.column_stack((v[:, 0]*c + v[:, 1]*s, v[:, 1]*c - v[:, 0]*s, v[:, 2]))


def normalize(x, weights, stem):
    return (x - weights[stem + ".mean"]) / weights[stem + ".scale"]


def scrambled(weights):
    keys = sorted(k for k in weights if k == "position" or k.startswith(("project.", "blocks.", "last_norm.")))
    rng = np.random.default_rng(3691)
    return {k: rng.permutation(weights[k].ravel()).reshape(weights[k].shape) for k in keys}


def features(mode, tokens, config, weights, linear, encode):
    flat = tokens.reshape(-1, 24)
    if mode == "linear":
        return flat
    if mode == "radial":
        raw = normalize(flat, weights, "point_motion.raw")
        centers = weights["point_motion.centres"]
        distance2 = np.maximum(0, np.sum(raw**2, axis=1)[:, None] + np.sum(centers**2, axis=1) - 2*raw@centers.T)
        extra = np.exp(-distance2 / (2 * weights["point_motion.bandwidth2"]))
    else:
        trunk = scrambled(weights) if mode == "shuffled" else weights
        values = normalize(tokens, weights, "point_motion.token")
        extra = encode(config, trunk, linear(trunk, "project", values))
    return np.column_stack((flat, extra))


def batch(mode, position, config, weights, linear, encode):
    if mode not in MODES:
        raise ValueError("Unknown point-motion forecast.")
    if mode == "stationary":
        return np.zeros_like(position[:, -1])
    velocity = 4*(position[:, -1] - position[:, -2])
    if mode == "velocity":
        return velocity
    if mode == "previous":
        return position[:, -1] - position[:, -5]
    tokens, heading = coordinates(position)
    design = features(mode, tokens, config, weights, linear, encode)
    stem = "point_motion." + mode
    correction = normalize(design, weights, stem) @ weights[stem + ".coef"] + weights[stem + ".bias"]
    return velocity + transform(correction, heading, inverse=True)


def forecast(record, config, weights, linear, encode):
    from knee.adapter import contains_boolean
    if not config.get("point_motion") or set(record) != {"domain", "mode", "positions_mm"}:
        raise ValueError("Supply a point-motion model, a method and nine positions in millimetres.")
    if not isinstance(record["mode"], str) or record["mode"] not in config["point_motion"]["modes"]:
        raise ValueError("This method is unavailable in this checkpoint. Reproduce the radial comparison from source.")
    x = record["positions_mm"]
    a = np.asarray(x)
    if a.shape != (9, 3) or a.dtype.kind not in "fiu" or contains_boolean(x) or not np.isfinite(a).all():
        raise ValueError("Each of the nine positions needs three finite millimetre coordinates.")
    with np.errstate(over="ignore",invalid="ignore"):
        result = batch(record["mode"], a[None].astype(float), config, weights, linear, encode)[0]
    if not np.isfinite(result).all():
        raise ValueError("Positions exceed the supported numerical range.")
    return {"displacement_xyz_mm":result.tolist(), "horizon_ms":200, "history_spacing_ms":50, "mode":record["mode"]}
