"""Forecast two stored knee angles from one complete four-second prefix."""
import argparse
import json
from pathlib import Path

import numpy as np


OFFSETS = np.array([-54, -42, -30, -21, -15, -9, -6, -3, 0])
PERIODS = np.arange(45, 181)
CHANNELS = ["right_knee_flexion_extension_deg", "left_knee_flexion_extension_deg"]
MODELS = ("prior_stride", "ridge_residual", "transformer_residual")


def phase_tokens(knees, cuts, periods):
    """Gather only present and earlier samples for an already selected period."""
    j = cuts[:, None] + OFFSETS
    previous = j - periods[:, None]
    fields = (knees[j], knees[previous], knees[previous + 15],
              knees[j] - knees[j - 3], knees[previous] - knees[previous - 3],
              np.broadcast_to(periods[:, None, None], (*j.shape, 1)))
    return np.concatenate(fields, axis=2), knees[cuts + 15 - periods]


def normalize(x, mean, scale):
    return (x - np.asarray(mean)) / np.asarray(scale)


def torch_export(z, state):
    """Evaluate the exported final checkpoint using NumPy in float64."""
    def linear(a, name):
        return a @ np.asarray(state[name + ".weight"]).T + np.asarray(state[name + ".bias"])

    def norm(a, name):
        mean = a.mean(axis=-1, keepdims=True)
        centered = a - mean
        value = centered / np.sqrt((centered ** 2).mean(axis=-1, keepdims=True) + 1e-5)
        return value * np.asarray(state[name + ".weight"]) + np.asarray(state[name + ".bias"])

    h = linear(z, "project") + np.asarray(state["position"])
    qkv = linear(norm(h, "attention_norm"), "qkv").reshape(len(h), 9, 3, 4, 6)
    q, k, v = qkv.transpose(2, 0, 3, 1, 4)
    logits = (q @ k.swapaxes(-1, -2)) / np.sqrt(6)
    attention = np.exp(logits - logits.max(axis=-1, keepdims=True))
    attention /= attention.sum(axis=-1, keepdims=True)
    mixed = (attention @ v).transpose(0, 2, 1, 3).reshape(len(h), 9, 24)
    h = h + linear(mixed, "attention_out")
    h = h + linear(np.maximum(0, linear(norm(h, "ff_norm"), "ff_in")), "ff_out")
    return linear(norm(h[:, -1], "last_norm"), "readout")


def predictions(tokens, anchor, weights):
    if weights["format"] != "two-knee-stride-weights-1":
        raise ValueError("Unrecognized weight format")
    z = normalize(tokens, weights["mean"], weights["scale"])
    linear = weights["ridge"]
    correction = (z.reshape(len(z), -1) - linear["center"]) @ np.asarray(linear["coef"]) + linear["intercept"]
    learned = torch_export(z, weights["transformer"]) * 10.
    return dict(prior_stride=anchor, ridge_residual=anchor + correction,
                transformer_residual=anchor + learned)


def forecast(frames, degrees, weights):
    """Return all three absolute right/left forecasts at the 15th later frame."""
    frames = np.asarray(frames)
    knees = np.asarray(degrees)
    if (frames.shape != (240,) or frames.dtype.kind not in "iuf" or
            not np.isfinite(frames).all() or not np.equal(frames, np.floor(frames)).all() or
            np.any(np.abs(frames.astype("f8")) > 2**52) or not np.all(np.diff(frames.astype("f8")) == 1)):
        raise ValueError("Supply 240 consecutive integer frame numbers, oldest first")
    if knees.shape != (240, 2) or knees.dtype.kind not in "iuf" or not np.isfinite(knees).all():
        raise ValueError("Supply 240 finite right/left knee pairs in degrees")
    knees = knees.astype(np.float64)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        recent = np.arange(180, 240)
        errors = np.square(knees[recent] - knees[recent - PERIODS[:, None]]).sum(axis=(1, 2))
        period = PERIODS[errors.argmin()]
        tokens, anchor = phase_tokens(knees, np.array([239]), np.array([period]))
        outcomes = predictions(tokens, anchor, weights)
    if not all(np.isfinite(value).all() for value in outcomes.values()):
        raise ValueError("Forecast exceeded the supported numerical range")
    return dict(period_frames=int(period), **{name: value[0].tolist() for name, value in outcomes.items()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", type=Path)
    parser.add_argument("--weights", type=Path, default=Path(__file__).with_name("weights.json"))
    args = parser.parse_args()
    prefix = json.loads(args.prefix.read_text())
    if prefix.get("format") != "two-knee-prefix-1" or prefix.get("channels") != CHANNELS:
        parser.error("Expected two-knee-prefix-1 with right/left channels as in example.json")
    print(json.dumps(forecast(prefix["frames"], prefix["degrees"], json.loads(args.weights.read_text())), indent=2))
