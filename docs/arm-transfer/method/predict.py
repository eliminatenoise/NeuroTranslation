"""Portable NumPy inference for the cued-arm models. Run python predict.py example.json."""

import argparse
import json
from pathlib import Path

import numpy as np

CUES = (
    "elbow flexion",
    "elbow extension",
    "supination",
    "pronation",
    "hand close",
    "hand open",
    "rest",
)
CHANNELS = ("elbow", "forearm_rotation", "index_near")
HORIZONS = (0.5, 1.0, 1.5)
METHODS = (
    "transformer",
    "transformer_no_cue",
    "mlp",
    "mlp_no_cue",
    "ridge",
    "ridge_no_cue",
    "cue",
    "unconditional",
    "still",
)
CUE_METHODS = ("transformer", "mlp", "ridge", "cue")


def tokens(bins):
    z = bins.copy()
    anchor = bins[:, -1, :3]
    z[:, :, :3] -= anchor[:, None, :]
    return z, anchor


def features(model, bins):
    s = model["scales"]
    z, a = tokens(bins)
    z = np.clip((z - s["token_mean"]) / s["token_sd"], -8, 8)
    a = np.clip((a - s["anchor_mean"]) / s["anchor_sd"], -8, 8)
    return z, a


def linear(h, w, name):
    return h @ np.asarray(w[name + ".weight"]).T + w[name + ".bias"]


def norm(h, w, name):
    c = h - h.mean(axis=-1, keepdims=True)
    return (
        c / np.sqrt(np.mean(c * c, axis=-1, keepdims=True) + 1e-5) * w[name + ".weight"]
        + w[name + ".bias"]
    )


def attention(w, z, a, cue):
    first = np.asarray(w["cue.weight"])[cue] + linear(a, w, "anchor")
    h = (
        np.concatenate([first[:, None, :], linear(z, w, "project")], axis=1)
        + w["position"]
    )
    q, k, v = [
        linear(h, w, key).reshape(-1, 5, 2, 4).swapaxes(1, 2) for key in ("q", "k", "v")
    ]
    dots = (q @ k.swapaxes(-1, -2)) / 2
    odds = np.exp(dots - dots.max(axis=-1, keepdims=True))
    context = (
        ((odds / odds.sum(axis=-1, keepdims=True)) @ v).swapaxes(1, 2).reshape(-1, 5, 8)
    )
    h = norm(h + linear(context, w, "attn_out"), w, "norm1")
    h = norm(h + linear(np.tanh(linear(h, w, "ff1")), w, "ff2"), w, "norm2")
    return linear(h[:, 0, :], w, "head")


def design(z, a, cue):
    indicator = np.zeros((len(z), 7))
    valid = cue < 7
    indicator[np.flatnonzero(valid), cue[valid]] = 1
    return np.column_stack([z.reshape(-1, 24), a, indicator])


def batch(model, bins, cue, method):
    if method not in METHODS:
        raise ValueError("Unknown method.")
    if method == "still":
        return np.zeros((len(bins), 3, 3))
    s = model["scales"]
    if method == "unconditional":
        return np.broadcast_to(s["target_mean"], (len(bins), 9)).reshape(-1, 3, 3)
    w = model["fits"][method]
    if method == "cue":
        return np.asarray(w["mean"])[cue].reshape(-1, 3, 3)
    z, a = features(model, bins)
    if method.endswith("_no_cue"):
        cue = np.full(len(cue), 7, dtype=int)
    if method.startswith("transformer"):
        pred = attention(w, z, a, cue)
    else:
        d = design(z, a, cue)
        if method.startswith("ridge"):
            pred = ((d - w["mean"]) / w["sd"]) @ w["coef"] + w["bias"]
        else:
            pred = linear(np.tanh(linear(d, w, "layer")), w, "head")
    return (pred * s["target_sd"] + s["target_mean"]).reshape(-1, 3, 3)


def predict(model, request):
    if not isinstance(request, dict) or set(request) - {"cue", "history", "method"}:
        raise ValueError("Supply cue, history and optionally method.")
    cue = request.get("cue")
    history = request.get("history")
    if cue not in CUES or type(history) is not list or len(history) != 4:
        raise ValueError("Supply one of the seven cues and four ordered history bins.")
    if any(
        type(row) is not list
        or len(row) != 6
        or any(type(v) not in (int, float) for v in row)
        for row in history
    ):
        raise ValueError("Each bin needs six numeric values.")
    bins = np.asarray(history, dtype=float)[None]
    if not np.isfinite(bins).all():
        raise ValueError("All instrument values must be finite.")
    method = request.get("method", "transformer")
    s = model["scales"]
    outside = np.any((bins < s["raw_min"]) | (bins > s["raw_max"]))
    with np.errstate(over="ignore", invalid="ignore"):
        y = batch(model, bins, np.array([CUES.index(cue)]), method)[0]
    if not np.isfinite(y).all():
        raise ValueError("Input exceeds numeric range.")
    return {
        "cue": cue,
        "method": method,
        "channels": list(CHANNELS),
        "horizons_s": list(HORIZONS),
        "delta": y.tolist(),
        "outside_fit_range": bool(outside),
    }


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", type=Path, default=here / "example.json")
    parser.add_argument("--model", type=Path, default=here / "model.json")
    args = parser.parse_args()
    print(
        json.dumps(
            predict(
                json.loads(args.model.read_text()), json.loads(args.request.read_text())
            ),
            indent=2,
        )
    )
