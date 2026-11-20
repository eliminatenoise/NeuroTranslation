"""Forecast supported right-elbow change from four causal bins."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CUES = ("flexion", "extension")
MECHANICS = ["cue01", "m3", "m3-m2", "m2-m1", "m1-m0"]
SIGNAL = ["s1-s0", "s2-s0", "s3-s0"]
RIDGES = ("cue_mechanics", "cue_mechanics_c3", "cue_mechanics_eog", "temporal_attention")


def bins(sample, key):
    values = sample.get(key)
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        raise ValueError(f"{key} requires four finite numbers, oldest first")
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or
           not math.isfinite(v) for v in values):
        raise ValueError(f"{key} requires finite numeric values")
    return values


def input_cue(sample):
    cue = sample.get("cue")
    if cue not in CUES:
        raise ValueError("cue must be flexion or extension")
    return cue


def feature_vector(name, sample, token_scale=None):
    cue = input_cue(sample)
    m0, m1, m2, m3 = bins(sample, "elbow_medians")
    x = [float(cue == "extension"), m3, m3 - m2, m2 - m1, m1 - m0]
    if name == "cue_mechanics":
        return x
    if name not in RIDGES:
        raise ValueError(f"unknown fitted method {name}")
    s = bins(sample, "eog_means" if name == "cue_mechanics_eog" else "c3_means")
    offsets = [v - s[0] for v in s]
    if name != "temporal_attention":
        return x + offsets[1:]
    tokens = [min(4.0, max(-4.0, v / token_scale)) for v in offsets]
    logits = [tokens[-1] * v + bias for v, bias in zip(tokens, (-0.75, -0.50, -0.25, 0))]
    weights = [math.exp(v - max(logits)) for v in logits]
    return x + [sum(v * w for v, w in zip(tokens, weights)) / sum(weights)]


def predict(name, model, sample, backend="python"):
    cue = input_cue(sample)
    if name == "persistence":
        return model["value"]
    if name == "cue_median":
        return model["by_cue"][cue]
    x = feature_vector(name, sample, model.get("token_scale"))
    if backend == "numpy":
        import numpy as np
        scaled = (np.asarray(x) - model["means"]) / model["scales"]
        return float(model["intercept"] + scaled @ model["weights"])
    if backend != "python":
        raise ValueError("backend must be python or numpy")
    return model["intercept"] + sum((v - mu) * w / sd for v, mu, sd, w in
                                    zip(x, model["means"], model["scales"], model["weights"], strict=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "example.json")
    parser.add_argument("--model", type=Path, default=HERE / "model.json")
    parser.add_argument("--method", choices=("all", "persistence", "cue_median", *RIDGES), default="all")
    parser.add_argument("--backend", choices=("python", "numpy"), default="python")
    args = parser.parse_args()
    sample = json.loads(args.input.read_text(encoding="utf-8"))
    models = json.loads(args.model.read_text(encoding="utf-8"))["models"]
    selected = models if args.method == "all" else [args.method]
    estimates = {name: predict(name, models[name], sample, args.backend) for name in selected}
    print(json.dumps({"cue": input_cue(sample), "units": "native elbow-sensor change",
                      "estimates": estimates}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
