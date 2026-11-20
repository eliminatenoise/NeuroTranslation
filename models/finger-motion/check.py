# SPDX-License-Identifier: CC0-1.0
"""Lightweight, recording-free checks of timeline, modalities and comparisons."""
from pathlib import Path

import numpy as np

from features import packet
from model import encoder_predict, load, ridge_predict
from recording import grid, glove_history, main_packets, target
from statistics_report import draws, matched_pairs


def check():
    # Descending unsigned values catch wraparound. Only the four future packets change.
    cut = np.array([400])
    flex = np.zeros((900, 5), dtype=np.uint16)
    flex[[440, 480, 520, 560]] = np.array([100, 20, 20, 50])[:, None]
    np.testing.assert_array_equal(target(flex, cut), np.full((1, 5), 110/3))
    np.testing.assert_equal(glove_history(flex,cut).max(), 0)
    assert grid(5, 1880) is None and grid(5, 1881) is not None
    assert grid(0, 1840) is None and grid(0, 1841) is not None

    rng = np.random.default_rng(140)
    cortical = rng.normal(size=(700, 46))
    p = main_packets(cortical, 1, 1, 0, cut)
    np.testing.assert_allclose(p[0], packet(cortical[121:401], 1, 1, 400))
    cortical[401:] += 1000
    np.testing.assert_array_equal(p, main_packets(cortical, 1, 1, 0, cut))
    assert p.shape == (1, 4, 152)
    for name, forward in (("ridge", ridge_predict), ("transformer", encoder_predict)):
        for mode, withheld in (("cue", slice(60,None)), ("cortex", slice(0,60))):
            w = load(Path(__file__).parent/"weights"/(name+"_"+mode+".npz"))
            x = p.copy()
            x[...,withheld] = np.nan
            np.testing.assert_array_equal(forward(p,mode,w), forward(x,mode,w))
    pairs, support, omitted = matched_pairs([2,3,2,4,3,2])
    np.testing.assert_equal(pairs, [[0,2],[1,4]])
    assert dict(support) == {2:1, 3:1} and dict(omitted) == {4:1, 2:1}
    assert draws(10).shape == (5000, 10)
    print("Passed timeline, packet, withheld-modality, pairing and resampling checks.")


if __name__ == "__main__":
    import torch
    torch.set_num_threads(2)
    check()
