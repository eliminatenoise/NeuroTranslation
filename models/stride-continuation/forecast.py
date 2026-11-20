"""NumPy reference for the 20 Hz CMU stride forecaster."""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STEPS = np.arange(1, 13, dtype=np.float64) / 20


def encode(history):
    """Encode a single observed prefix. The basis vectors occupy columns."""
    history = np.asarray(history, dtype=np.float64)
    if history.shape != (11, 18, 3) or not np.isfinite(history).all():
        raise ValueError("Expected 11 complete observations with 18 three-dimensional sites")
    right = (history[-1, 3] - history[-1, 2]).copy()
    right[2] = 0
    width = np.linalg.norm(right)
    if width < 40:
        raise ValueError("Last observed waist separation below 40 mm")
    right /= width
    up = np.array([0., 0., 1.])
    basis = np.column_stack((right, np.cross(up, right), up))
    hip = history[:, 2:4].mean(axis=1)
    body = (history - hip[:, None]) @ basis
    root = (hip - hip[-1]) @ basis
    x = np.concatenate((body.reshape(11, 54), root), axis=1) / 250.
    return x, basis, hip[-1], body[-1], -root[-5] / .20


def observed_residual(future, basis, origin, body0, velocity):
    hip = future[:, 2:4].mean(axis=1)
    body = (future - hip[:, None]) @ basis - body0
    root = (hip - origin) @ basis - STEPS[:, None] * velocity
    return np.concatenate((body.reshape(12, 54), root), axis=1) / 100.


def decode(residual, basis, origin, body0, velocity):
    residual = residual * 100.
    body = residual[:, :54].reshape(12, 18, 3) + body0
    body = body - body[:, 2:4].mean(axis=1, keepdims=True)
    root = residual[:, 54:] + STEPS[:, None] * velocity
    pelvis = root @ basis.T + origin
    return body @ basis.T + pelvis[:, None], pelvis


def load_weights(path):
    payload = json.loads(Path(path).read_text())
    if payload["format"] != "stride-attention-1":
        raise ValueError("Unknown checkpoint format")
    return payload["mode"], {k: np.asarray(v, dtype=np.float64) for k, v in payload["weights"].items()}


def residual_prediction(x, token, w):
    def linear(values, name):
        return values @ w[name + ".weight"].T + w[name + ".bias"]

    def norm(values, name):
        centred = values - values.mean(axis=-1, keepdims=True)
        return centred / np.sqrt((centred**2).mean(axis=-1, keepdims=True) + 1e-5) * w[name + ".weight"] + w[name + ".bias"]

    def heads(values):
        return values.reshape(11, 4, 12).transpose(1, 0, 2)

    h = linear(x, "input") + w["position"] + w["action.weight"][token]
    for index in range(2):
        pre = f"blocks.{index}."
        q, k, v = map(heads, np.split(linear(norm(h, pre + "ln1"), pre + "qkv"), 3, axis=-1))
        logits = q @ k.transpose(0, 2, 1) / np.sqrt(12.)
        attention = np.exp(logits - logits.max(axis=-1, keepdims=True))
        attention /= attention.sum(axis=-1, keepdims=True)
        mix = (attention @ v).transpose(1, 0, 2).reshape(11, 48)
        h = h + linear(mix, pre + "out")
        h = h + linear(np.maximum(linear(norm(h, pre + "ln2"), pre + "ff1"), 0.), pre + "ff2")
    anchors = linear(norm(h[-1], "final"), "readout").reshape(6, 57)
    previous = np.concatenate((np.zeros((1, 57)), anchors[:-1]))
    return np.stack(((previous + anchors) / 2, anchors), axis=1).reshape(12, 57)


def forecast(history_mm, times_s, action, weights):
    """Return absolute lab positions on the same seconds clock as the input."""
    times = np.asarray(times_s, dtype=np.float64)
    if times.shape != (11,) or not np.isfinite(times).all() or not np.allclose(np.diff(times), .05, atol=1e-6, rtol=0):
        raise ValueError("Input must contain 11 consecutive times 0.05 s apart")
    mode, w = weights
    if mode == "conditional":
        if action not in ("walk", "run"):
            raise ValueError("Conditional model requires walk or run")
        token = int(action == "run")
    elif mode == "history-only":
        token = 0
    else:
        raise ValueError("Unknown model mode")
    x, *geometry = encode(history_mm)
    positions, pelvis = decode(residual_prediction(x, token, w), *geometry)
    return {"timesS": (times[-1] + STEPS).tolist(), "positionsMm": positions.tolist(), "pelvisMm": pelvis.tolist()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", type=Path)
    parser.add_argument("--weights", type=Path, default=HERE / "conditional.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    sample = json.loads(args.example.read_text())
    history = sample.get("history", sample)
    result = forecast(history["positionsMm"], history["timesS"], sample.get("action"), load_weights(args.weights))
    text = json.dumps(result, allow_nan=False)
    if args.out:
        args.out.write_text(text + "\n")
    else:
        print(text)
