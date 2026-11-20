"""Predict the right heel change and right-contact platform load on one stored clock."""
import numpy as np

OFFSETS = (14, 24, 34, 44)
READOUTS = ("linear_motion", "linear_full", "encoder_motion_rank2", "encoder_full_rank2",
            "encoder_full_unrestricted", "random_full_rank2")
BASELINES = ("hold_heel", "velocity_heel", "recent_heel", "force_hold", "force_trend")
FULL = ("linear_full", "encoder_full_rank2", "encoder_full_unrestricted", "random_full_rank2")


def tokens(markers, emg):
    blocks = markers.reshape(-1, 4, 6, 2, 3)
    changes = blocks[:, :, -1] - blocks[:, :, 0]
    foot = blocks[:, :, -1, 1] - blocks[:, :, -1, 0]
    return np.concatenate([changes.reshape(-1, 4, 6), foot, np.log1p(emg)], axis=2)


def design(mode, data, state, encoder):
    history = tokens(data["marker_mm"], data["emg_uv"])
    z = (history - state["token_mean"]) / state["token_scale"]
    if mode not in FULL:
        z[:, :, 9:] = 0
    heel = data["marker_mm"][:, :, 0]
    pieces = [z.reshape(len(z), -1), heel[:, -1] - heel[:, -11],
              data["offset"][:, None] == np.asarray(OFFSETS)]
    if not mode.startswith("linear"):
        from predict import linear, encode
        cfg, original, random = encoder
        weights = random if mode == "random_full_rank2" else original
        pieces.append(encode(cfg, weights, linear(weights, "project", z[:, :, :6])))
    return np.column_stack(pieces)


def baseline(data, state):
    heel = data["marker_mm"][:, :, 0]
    typical = [state["phase_medians"][str(int(t))] for t in data["offset"]]
    return np.column_stack([heel[:, -1] - heel[:, -11], typical])


def batch(mode, data, state, encoder):
    result = baseline(data, state)
    if mode in READOUTS:
        fitted = state["fits"][mode]
        z = (design(mode, data, state, encoder) - fitted["mean"]) / fitted["scale"]
        if "decoder" in fitted:
            correction = (z @ fitted["factors"]) @ fitted["decoder"]
        else:
            correction = z @ fitted["coefficients"]
        return result + correction * state["target_scale"] + state["target_mean"]
    heel = data["marker_mm"][:, :, 0]
    if mode == "hold_heel":
        result[:, :3] = 0
    elif mode == "velocity_heel":
        result[:, :3] = (heel[:, -1] - heel[:, -7]) * (10 / 6)
    elif mode in ("force_hold", "force_trend"):
        current, previous = data["privileged_force_n"].T
        result[:, 3] = current if mode == "force_hold" else 2 * current - previous
    elif mode != "recent_heel":
        raise ValueError("Unknown heel and force method.")
    return result


def measurement(value, shape, name):
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "iuf":
        raise ValueError(f"{name} requires a numerical array of shape {shape}.")
    array = raw.astype(np.float64, copy=False)
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain finite measurements.")
    return array


def forecast(record, state, encoder):
    mode = record.get("mode")
    if mode not in (*BASELINES, *READOUTS):
        raise ValueError("Choose a supported heel and force method.")
    offset = record.get("offset_frames")
    if type(offset) is not int or offset not in OFFSETS:
        raise ValueError("Use 14, 24, 34 or 44 camera frames after right foot strike.")
    keys = {"domain", "mode", "offset_frames", "markers_mm"}
    if mode in FULL:
        keys.add("emg_rms_uv")
    if mode in ("force_hold", "force_trend"):
        keys.add("prior_plate_n")
    if set(record) != keys:
        raise ValueError("Required fields for this method: " + ", ".join(sorted(keys)))
    data = {"marker_mm": measurement(record["markers_mm"], (24, 2, 3), "markers_mm")[None],
            "offset": np.array([offset]), "emg_uv": np.zeros((1, 4, 8))}
    if mode in FULL:
        emg = measurement(record["emg_rms_uv"], (4, 8), "emg_rms_uv")
        if (emg < 0).any():
            raise ValueError("Each muscle amplitude must be nonnegative.")
        data["emg_uv"] = emg[None]
    if "prior_plate_n" in keys:
        data["privileged_force_n"] = measurement(record["prior_plate_n"], (2,), "prior_plate_n")[None]
    with np.errstate(over="ignore", invalid="ignore"):
        output = batch(mode, data, state, encoder)[0]
    if not np.isfinite(output).all():
        raise ValueError("Input exceeds the numerical range of the forecast.")
    return {"mode": mode, "horizon_frames": 10, "stored_horizon_ms": 100,
            "heel_delta_mm": output[:3].tolist(), "right_plate_load_n": float(output[3])}
