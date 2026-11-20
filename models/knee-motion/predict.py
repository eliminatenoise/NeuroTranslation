"""Predict bilateral knee flexion/extension estimates from five stored IMU frames."""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CHANNELS = ["right hip", "left hip", "right knee", "left knee", "right ankle", "left ankle"]
LAGS = [24, 18, 12, 6, 0]
MODELS = ("persistence", "slope", "knee_ridge", "all_ridge", "transformer")


def check_history(history):
    x = np.asarray(history, dtype=np.float64)
    if x.shape[-2:] != (5, 6) or x.ndim not in (2, 3) or not np.isfinite(x).all():
        raise ValueError("Expected five chronological rows of six finite angles in degrees.")
    return x


def transform(z, state):
    """One 24-wide historical attention block, with no tokens past the cutoff."""
    def linear(x, name):
        return x @ state[name + ".weight"].T + state[name + ".bias"]

    def norm(x, name):
        centered = x - x.mean(axis=-1, keepdims=True)
        return centered / np.sqrt((centered ** 2).mean(axis=-1, keepdims=True) + 1e-5) * state[name + ".weight"] + state[name + ".bias"]

    embedded = linear(z, "project") + state["position"]
    size, tokens, width = embedded.shape
    qkv = linear(norm(embedded, "attention_norm"), "qkv").reshape(size, tokens, 3, 4, 6)
    q, k, v = qkv.transpose(2, 0, 3, 1, 4)
    logits = (q @ k.swapaxes(-1, -2)) / np.sqrt(6)
    exp = np.exp(logits - logits.max(axis=-1, keepdims=True))
    mixed = ((exp / exp.sum(axis=-1, keepdims=True)) @ v).transpose(0, 2, 1, 3)
    z = embedded + linear(mixed.reshape(size, tokens, width), "attention_out")
    z = z + linear(np.maximum(linear(norm(z, "ff_norm"), "ff_in"), 0), "ff_out")
    return linear(norm(z[:, -1], "last_norm"), "readout")


def read_history(request):
    if not isinstance(request, dict):
        raise ValueError("Expected an object with history_degrees.")
    if "feature_order" in request and request["feature_order"] != CHANNELS:
        raise ValueError("The six channels must follow feature_order in example.json.")
    if "frames_before_cutoff" in request and request["frames_before_cutoff"] != LAGS:
        raise ValueError("The five history rows must be at frames 24, 18, 12, 6 and 0.")
    return check_history(request["history_degrees"])


@np.errstate(over="raise", invalid="raise", divide="raise")
def predict(history, weights, model="transformer"):
    x = check_history(history)
    single = x.ndim == 2
    x = x.reshape(-1, 5, 6)
    last = x[:, -1, 2:4]
    if model == "persistence":
        result = last.copy()
    elif model == "slope":
        result = last + (15 / 6) * (last - x[:, -2, 2:4])
    elif model in ("knee_ridge", "all_ridge"):
        source = x[:, :, 2:4] if model == "knee_ridge" else x
        features = source.reshape(len(x), -1)
        fit = weights[model]
        z = (features - fit["mean"]) / fit["scale"]
        result = last + z @ fit["coef"] + fit["intercept"]
    elif model == "transformer":
        fit = weights[model]
        z = (x - fit["mean"]) / fit["scale"]
        state = {key: np.asarray(value) for key, value in fit["state"].items()}
        result = last + 20 * transform(z, state)
    else:
        raise ValueError(f"Unknown model {model!r}")
    if not np.isfinite(result).all():
        raise ValueError("The forecast exceeds the finite numeric range.")
    return result[0] if single else result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", nargs="?", type=Path, default=HERE / "example.json")
    parser.add_argument("--weights", type=Path, default=HERE / "weights.json")
    parser.add_argument("--model", choices=MODELS, default="transformer")
    args = parser.parse_args()
    request = json.loads(args.history.read_text())
    weights = json.loads(args.weights.read_text())
    if weights.get("format") != "gait-knees-1" or weights.get("features") != CHANNELS or weights.get("lags_frames") != LAGS or weights.get("future_frames") != 15:
        parser.error("The weight file uses an incompatible format or channel/frame order.")
    try:
        result = predict(read_history(request), weights, args.model)
    except (ValueError, FloatingPointError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({"model": args.model, "future_frames": 15, "right_left_knee_degrees": result.tolist()}, allow_nan=False))


if __name__ == "__main__":
    main()
