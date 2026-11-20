"""Portable walking landmark prediction. Requires Python 3 and NumPy."""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MARKERS = tuple(f"{side}_{joint}" for joint in ("FAL", "FLE", "RSP", "IAS") for side in ("L", "R"))
MUSCLES = tuple("R_" + name for name in (
    "tibialis_anterior", "soleus", "gastrocnemius_medialis", "vastus_medialis",
    "rectus_femoris", "semitendinosus", "gluteus_maximus", "gluteus_medius"))
MODELS = ("ridge_markers", "ridge_combined", "transformer_markers", "transformer_combined",
          "persistence", "velocity")


def tokens(markers_mm, emg_rms_uv):
    """Eight rows of centered position, within-token movement, flags, RMS and flags."""
    x = np.asarray(markers_mm, dtype=float)
    if x.shape[-3:] != (40, 8, 3):
        raise ValueError("Expected 40 frames, 8 landmarks and 3 coordinates.")
    x = np.where(np.isfinite(x).all(axis=-1, keepdims=True), x, np.nan)
    end, start = x[..., 4::5, :, :], x[..., ::5, :, :]
    center = end[..., 6:8, :].mean(axis=-2, keepdims=True)
    pos, move = end - center, end - start
    shape = pos.shape[:-2] + (24,)
    shape_emg = pos.shape[:-2] + (8,)
    emg = np.full(shape_emg, np.nan) if emg_rms_uv is None else np.asarray(emg_rms_uv, dtype=float)
    if emg.shape != shape_emg or (emg[np.isfinite(emg)] < 0).any():
        raise ValueError("Expected eight RMS tokens of eight nonnegative microvolt values.")
    return np.concatenate((pos.reshape(shape), move.reshape(shape), np.isfinite(pos[..., 0]),
                           np.isfinite(move[..., 0]), emg, np.isfinite(emg)), axis=-1)


def load_weights(path=None):
    with np.load(path or HERE / "weights.npz", allow_pickle=False) as packed:
        return {k: packed[k] for k in packed.files}


def standardize(features, w, family):
    d = 64 if family == "markers" else 80
    z = (np.asarray(features)[..., :d] - w[family + ".mean"]) / w[family + ".sd"]
    return np.where(np.isfinite(z), z, 0.0)


def net_residual(z, w, family):
    def p(key):
        return w[family + "." + key]

    def affine(x, name):
        return x @ p(name + ".weight").T + p(name + ".bias")

    def norm(x, name):
        mu = x.mean(axis=-1, keepdims=True)
        scale = np.sqrt(((x-mu)**2).mean(axis=-1, keepdims=True) + 1e-5)
        return (x-mu)/scale * p(name + ".weight") + p(name + ".bias")

    h = affine(z.astype("f4"), "embed") + p("pos")
    batch, length, width = h.shape
    heads = int(p("heads").item())
    parts = affine(norm(h, "ln1"), "qkv").reshape(batch, length, 3, heads, width//heads)
    q, k, v = [parts[:, :, j].transpose(0, 2, 1, 3) for j in range(3)]
    score = q @ k.swapaxes(-2, -1) / np.sqrt(np.float32(width//heads))
    attn = np.exp(score - score.max(axis=-1, keepdims=True))
    values = (attn / attn.sum(axis=-1, keepdims=True)) @ v
    h = h + affine(values.transpose(0, 2, 1, 3).reshape(h.shape), "out")
    h = h + affine(np.maximum(affine(norm(h, "ln2"), "ff1"), 0), "ff2")
    return affine(h[:, -1], "head")


def run_tokens(features, w, model):
    x = np.asarray(features)
    if x.ndim != 3 or x.shape[1:] != (8,80) or model not in MODELS:
        raise ValueError("Expected a batch of eight by 80 input tokens and a supported model.")
    if model == "persistence":
        return np.zeros((len(x), 6, 3))
    if model == "velocity":
        v = x[:, -1, 24:42].reshape(-1, 6, 3)
        return np.where(np.isfinite(v), 5*v, 0.)
    family = model.split("_")[1]
    z = standardize(x, w, family)
    y = z.reshape(len(x), -1) @ w[family + ".beta"] + w[family + ".intercept"]
    if model.startswith("transformer"):
        y = y + net_residual(z, w, family) * w[family + ".resid_sd"]
    return y.reshape(-1, 6, 3)


def predict(markers_mm, emg_rms_uv=None, model="transformer_combined", weights=None):
    inputs = tokens(markers_mm, emg_rms_uv)
    if inputs.ndim != 2:
        raise ValueError("predict() expects one history.")
    return run_tokens(inputs[None], weights if weights is not None else load_weights(), model)[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=HERE / "example.json")
    parser.add_argument("--model", choices=MODELS, default="transformer_combined")
    args = parser.parse_args()
    example = json.loads(args.input.read_bytes())
    value = predict(example["markers_mm"], example.get("emg_rms_uv"), args.model)
    print(json.dumps({"model": args.model, "landmarks": MARKERS[:6], "displacement_mm": value.tolist()}, indent=2))
