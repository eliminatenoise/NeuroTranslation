# SPDX-License-Identifier: CC0-1.0
"""Run saved movement decoders on an invented sensor history."""
import argparse
import json
from pathlib import Path

import numpy as np

from features import packet
from model import encoder_predict, load, ridge_predict

HERE = Path(__file__).resolve().parent


def demo(weights):
    # Entirely generated from a fixed random seed, including all 46 contact signals.
    rng = np.random.default_rng(1729)
    t = np.arange(280)[:, None]/1000
    phase = np.linspace(0, 2*np.pi, 46, endpoint=False)
    counts = np.rint(380*np.sin(2*np.pi*20*t+phase)
                     + 125*np.sin(2*np.pi*87.5*t-2*phase)
                     + rng.normal(0, 65, (280, 46))).astype(np.int32)
    p = packet(counts, digit=2, phase=0, elapsed_ms=800)[None]
    past = rng.integers(200, 300, (1, 4, 5)).astype(np.float64)
    hist = np.concatenate([past.reshape(1, 20), abs(np.diff(past, axis=1)).reshape(1, 15)], axis=1)
    out = {}
    for family, forward, modes in (
        ("ridge", ridge_predict, ("cue", "cortex", "aligned", "history")),
        ("transformer", encoder_predict, ("cue", "cortex", "aligned")),
    ):
        for mode in modes:
            key = family + "_" + mode
            w = load(weights / (key + ".npz"))
            out[key] = forward(hist if mode == "history" else p, mode, w)[0].tolist()
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check against outputs stored with this release")
    args = parser.parse_args()
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    actual = demo(HERE/"weights")
    if args.check:
        reference = json.loads((HERE/"invented-result.json").read_text())
        for key, numbers in actual.items():
            np.testing.assert_allclose(numbers, reference[key], rtol=1e-5, atol=2e-4)
    print(json.dumps(actual, indent=2))
