"""Forecast displacement of the pelvis and right heel on a 100 Hz recording clock."""
import json
from pathlib import Path

import numpy as np

OFFSETS = (10, 20, 30, 40)
INSTRUCTIONS = {"as usual": 4, "fast but not running": 5}
FITS = ("pace_phase", "cue_only", "linear_motion", "linear_cue", "encoder_motion",
        "encoder_cue", "random_cue")
BASELINES = ("hold", "repeat_100ms", "velocity_50ms", "condition_phase_mean")
USES_CUE = ("cue_only", "linear_cue", "encoder_cue", "random_cue", "condition_phase_mean")


def oriented(history):
    """Remove starting position and horizontal travel direction, using only the supplied history."""
    forward = history[:, -1, 0, :2] - history[:, 0, 0, :2]
    distance = np.linalg.norm(forward, axis=1, keepdims=True)
    if (distance < 10).any() or not np.isfinite(distance).all():
        raise ValueError("The pelvis must travel at least 10 mm horizontally over the 200 ms history.")
    heading = forward / distance
    basis = np.zeros((len(history), 3, 3), dtype=float)
    basis[:, :2, 0] = heading
    basis[:, 0, 1] = -heading[:, 1]
    basis[:, 1, 1] = heading[:, 0]
    basis[:, 2, 2] = 1
    centered = history - history[:, -1:, :1, :]
    return np.einsum("ntmi,nij->ntmj", centered, basis), basis


def summaries(history):
    edges = history[:, ::5]
    increments = np.diff(edges, axis=1).reshape(len(history), 4, 6)
    distance = np.linalg.norm(history[:, -1, 0, :2] - history[:, 0, 0, :2], axis=1)
    return increments, distance / 200


def features(mode, data, state, encoders):
    motion, speed = summaries(data["history_mm"])
    phase = (data["offset"][:, None] == OFFSETS).astype(float)
    if mode == "pace_phase":
        return np.column_stack((speed, phase))
    context = np.where(data["condition"] == 5, 1., -1.) if mode in USES_CUE else np.zeros(len(speed))
    if mode == "cue_only":
        return np.column_stack((phase, context, context[:, None] * phase))
    history = data["history_mm"]
    inputs = [motion.reshape(len(speed), 24), history[:, -1, 1] - history[:, -1, 0],
              speed, phase, context, context[:, None] * phase, context * speed]
    if mode.startswith(("encoder", "random")):
        from predict import linear, encode
        cfg, trained, random = encoders
        w = random if mode == "random_cue" else trained
        z = (motion - state["token_mean"]) / state["token_sd"]
        inputs.append(encode(cfg, w, linear(w, "project", z)))
    return np.column_stack(inputs)


def predict_batch(mode, data, state, encoders):
    history = data["history_mm"]
    recent = history[:, -1] - history[:, -11]
    if mode == "hold":
        return np.zeros_like(recent)
    if mode == "repeat_100ms":
        return recent
    if mode == "velocity_50ms":
        return 2 * (history[:, -1] - history[:, -6])
    if mode == "condition_phase_mean":
        return np.asarray([state["cell_means"][f"{int(c)}/{int(o)}"] for c, o in zip(
            data["condition"], data["offset"])])
    fitted = state["fits"][mode]
    x = features(mode, data, state, encoders)
    delta = fitted["bias"] + ((x - fitted["mean"]) / fitted["sd"]) @ fitted["coef"]
    shaped = delta.reshape(-1, 2, 3)
    return shaped if mode == "cue_only" else recent + shaped


def load_encoders(checkpoint, mode):
    from predict import read_checkpoint
    cfg, trained = read_checkpoint(checkpoint)
    random = {}
    if mode == "random_cue" or mode is None:
        raw = json.loads((Path(checkpoint).parent / "back_rotation/random-encoder.json").read_bytes())
        random = {k: np.asarray(v, dtype=float) for k, v in raw.items()}
    return cfg, trained, random


def forecast(record, state, encoders):
    mode = record.get("mode")
    if mode not in (*BASELINES, *FITS):
        raise ValueError("Choose a supported walking forecast method.")
    keys = {"domain", "mode", "offset_frames", "frame", "history_mm"}
    if mode in USES_CUE:
        keys.add("instruction")
    if set(record) != keys:
        raise ValueError("Required fields for this method: " + ", ".join(sorted(keys)))
    cue = record.get("instruction", "as usual")
    if type(cue) is int and cue in (4, 5):
        condition = cue
    elif isinstance(cue, str) and cue in INSTRUCTIONS:
        condition = INSTRUCTIONS[cue]
    else:
        raise ValueError('Choose “as usual” (4) or “fast but not running” (5).')
    offset = record["offset_frames"]
    if type(offset) is not int or offset not in OFFSETS:
        raise ValueError("Use 10, 20, 30 or 40 frames after the first right strike.")
    raw = np.asarray(record["history_mm"])
    if raw.shape != (21, 2, 3) or raw.dtype.kind not in "iuf" or not np.isfinite(raw).all():
        raise ValueError("history_mm needs 21 finite XYZ rows with pelvis first and right heel second.")
    history = raw.astype(float)[None]
    frame = record["frame"]
    if frame not in ("laboratory", "travel"):
        raise ValueError("Choose laboratory or travel for the coordinate frame.")
    with np.errstate(all="ignore"):
        transformed, basis = oriented(history)
        if frame == "travel" and not np.allclose(history, transformed, rtol=1e-9, atol=1e-6):
            raise ValueError("In travel coordinates the pelvis ends at zero, after moving along positive X.")
        inputs = {"history_mm": transformed, "offset": np.array([offset]), "condition": np.array([condition])}
        delta = predict_batch(mode, inputs, state, encoders)[0]
        if not np.isfinite(delta).all():
            raise ValueError("Input exceeds the numerical range of the walking forecast.")
        result = {"mode": mode, "horizon_ms_on_recording": 100, "axes": ["forward", "left", "up"],
                  "pelvis_delta_mm": delta[0].tolist(), "right_heel_delta_mm": delta[1].tolist()}
        if frame == "laboratory":
            lab = delta @ basis[0].T
            result["laboratory_axes"] = ["X", "Y", "Z"]
            result["laboratory_pelvis_delta_mm"] = lab[0].tolist()
            result["laboratory_right_heel_delta_mm"] = lab[1].tolist()
    return result
