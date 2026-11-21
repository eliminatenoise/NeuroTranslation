"""Refit the three original body-and-cue Transformers on the September 7 rows."""
import argparse
import hashlib
from pathlib import Path

import numpy as np

from base_model import fit_transformer, training_scales, weights_by_original
from frozen_forecast import SEEDS, history_tokens, standardized
from reproduce import torch_setup


def refit(training, output):
    if hashlib.sha256(training.read_bytes()).hexdigest() != "40bb17cd64e61bfb4ef52b5ee943d27d50e1c82bbf487d58c623c4ed2d6666ab":
        raise ValueError("Expected the archived September 7 training arrays")
    torch_setup(1)
    output.mkdir(parents=True, exist_ok=False)
    with np.load(training, allow_pickle=False) as rows:
        raw = history_tokens(rows["pose"], rows["spikes"], rows["cue"])
        movement = rows["movement"]
        original = np.column_stack((rows["block"], rows["original"]))
        _, group = np.unique(original, axis=0, return_inverse=True)
        weights = weights_by_original(group)
        scales = training_scales(raw, movement, weights)
        base = dict(schema="chowdhury-motor-v1", arm="pose_cue", unit_guide=rows["unit_guide"], **scales)
    inputs = standardized(raw, base)
    targets = ((movement - scales["y_mean"]) / scales["y_scale"]).reshape(-1, 80)
    for seed in SEEDS:
        _, parameters, steps = fit_transformer(inputs, targets, weights, seed, "cpu")
        if steps != 216:
            raise RuntimeError(f"Unexpected number of minibatch updates: {steps}")
        np.savez_compressed(output / f"pose_cue-{seed}.npz", **base, **parameters)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("train", type=Path)
    cli.add_argument("destination", type=Path)
    args = cli.parse_args()
    refit(args.train, args.destination)
