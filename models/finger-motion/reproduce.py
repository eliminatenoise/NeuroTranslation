# SPDX-License-Identifier: CC0-1.0
"""Fit the frozen readouts on the verified development prefix and export aggregate scores."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from model import encoder_fit, encoder_predict, ridge_fit, ridge_predict
from recording import EVAL_BOUNDS, FIT_BOUNDS, METHOD_HASH, load_prefix, partition
from statistics_report import report


def run(prefix, out, threads):
    if hashlib.sha256(Path(__file__).with_name("METHOD.md").read_bytes()).hexdigest() != METHOD_HASH:
        raise ValueError("Sealed method changed")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose an empty output directory")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    source = load_prefix(prefix)
    train, dev = (partition(source, bounds) for bounds in (FIT_BOUNDS, EVAL_BOUNDS))
    del source
    weights = out / "weights"
    weights.mkdir(exist_ok=False, parents=True)
    pred = {"training_mean": np.broadcast_to(train.y.mean(axis=0), dev.y.shape)}
    for name, fit, predict, modes in (
        ("ridge", ridge_fit, ridge_predict, ("cue", "cortex", "aligned", "history")),
        ("transformer", encoder_fit, encoder_predict, ("cue", "cortex", "aligned")),
    ):
        for mode in modes:
            key = name + "_" + mode
            w = fit(train.history if mode == "history" else train.packets, train.y, mode)
            np.savez_compressed(weights/(key + ".npz"), **w)
            pred[key] = predict(dev.history if mode == "history" else dev.packets, mode, w)
            if mode == "aligned":
                pred[name + "_earlier"] = predict(dev.wrong, mode, w)
    stats = report(train, dev, pred)
    (out/"results.json").write_text(json.dumps(stats, indent=2, allow_nan=False,
                                              default=lambda x: x.tolist())+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    run(args.prefix, args.output, args.threads)
