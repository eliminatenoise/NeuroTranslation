"""Build causal window tokens and run the exported predictor with NumPy alone."""
import argparse
import json
import math
from pathlib import Path
import numpy as np

CHANNELS = ["Biceps", "SC6", "Thumb", "CP4", "ECG"]
WINDOWS = [[-15, -10], [5, 8]]
SPLIT = 10


def tokens(baseline, early):
    parts = []
    for values, length in [(baseline, 50), (early, 30)]:
        block = np.asarray(values, dtype=np.float64)
        if block.ndim != 3 or block.shape[1:] != (length, len(CHANNELS)):
            raise ValueError(f"Expected [events,{length},5] microvolt input.")
        if not np.isfinite(block).all():
            raise ValueError("Input contains a nonfinite voltage.")
        parts.append(block.reshape(-1, length // 5, 5, len(CHANNELS)).mean(axis=2))
    if len(parts[0]) != len(parts[1]):
        raise ValueError("The input windows have different event counts.")
    return np.concatenate(parts, axis=1)


def fit_transform(raw, target):
    means, scales = [], []
    for x in (raw[:, :SPLIT], raw[:, SPLIT:]):
        means.append(x.mean(axis=(0, 1)).tolist())
        scales.append(np.where(x.std(axis=(0, 1)) < 1e-8, 1.0, x.std(axis=(0, 1))).tolist())
    # No fitted model consumes baseline Biceps, including its moments.
    means[0][0], scales[0][0] = 0.0, 1.0
    target_scale = float(target.std())
    return {"mean": means, "sd": scales, "target_mean": float(target.mean()),
            "target_sd": 1.0 if target_scale < 1e-8 else target_scale}


def features(raw, index, transform, with_eng):
    order = np.asarray(index)
    if order.shape != (len(raw),) or not np.issubdtype(order.dtype, np.integer):
        raise ValueError("Supply one integer event index per event.")
    if (order < 0).any() or (order > 79).any():
        raise ValueError("The supported first-event indices are 0 through 79.")
    x = np.empty((*raw.shape[:2], len(CHANNELS) + 1), dtype=np.float64)
    for part, sl in enumerate((slice(None, SPLIT), slice(SPLIT, None))):
        x[:, sl, :5] = (raw[:, sl] - transform["mean"][part]) / transform["sd"][part]
    x[:, :SPLIT, 0] = 0
    if not with_eng:
        x[:, SPLIT:, 0] = 0
    x[:, :, 5] = order[:, None] / 79.0
    return x


def undo(y, transform):
    return y * transform["target_sd"] + transform["target_mean"]


def predict(raw, index, export, model_name="eng"):
    model = export["models"][model_name]
    w = {k: np.asarray(v, dtype=np.float64) for k, v in model.items()}
    transform = export["transform"]
    x = features(raw, index, transform, model_name != "noneng")

    def linear(z, name):
        return z @ w[name + ".weight"].T + w[name + ".bias"]

    def norm(z, name):
        centered = z - z.mean(axis=-1, keepdims=True)
        std = np.sqrt((centered ** 2).mean(axis=-1, keepdims=True) + 1e-5)
        return centered / std * w[name + ".weight"] + w[name + ".bias"]

    x = linear(x, "embed") + w["position"]
    qkv = linear(norm(x, "norm1"), "qkv")
    q, k, v = [a.reshape(len(x), 16, 2, 8).transpose(0, 2, 1, 3)
               for a in np.split(qkv, 3, axis=-1)]
    dots = (q @ k.swapaxes(-2, -1)) / math.sqrt(8)
    probs = np.exp(dots - dots.max(axis=-1, keepdims=True))
    probs /= probs.sum(axis=-1, keepdims=True)
    context = (probs @ v).transpose(0, 2, 1, 3).reshape(len(x), 16, 16)
    x = x + linear(context, "mix")
    h = linear(norm(x, "norm2"), "ff1")
    h = 0.5 * h * (1 + np.vectorize(math.erf, otypes=[float])(h / math.sqrt(2)))
    x = x + linear(h, "ff2")
    output = linear(norm(x, "outnorm").mean(axis=1), "readout")[:, 0]
    return undo(output, transform)


def main():
    parser = argparse.ArgumentParser(description="Predict SC6 from a baseline and an early window in microvolts.")
    parser.add_argument("input", type=Path, help="JSON object with baseline [50,5], early [30,5] and event_index")
    parser.add_argument("--weights", type=Path, default=Path(__file__).parent / "export/weights.json")
    args = parser.parse_args()
    example = json.loads(args.input.read_text())
    data = tokens([example["baseline"]], [example["early"]])
    export = json.loads(args.weights.read_text())
    result = {k: float(predict(data, [example["event_index"]], export, k)[0])
              for k in ("noneng", "eng")}
    print(json.dumps({"predicted_SC6_change_uV": result}, allow_nan=False))


if __name__ == "__main__":
    main()
