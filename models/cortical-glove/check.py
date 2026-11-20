# SPDX-License-Identifier: CC0-1.0
"""Regression checks on invented inputs. Does not open the admitted data file."""
from pathlib import Path
from types import SimpleNamespace
import tempfile

import numpy as np
from invented import invented
from model import BRAIN, band_features, load_checkpoint, ridge_fit, ridge_predict, tokens_from_history
from analysis_core import boot_draws, grid, make_partition, phase_arrays


def main():
    counts, glove, digit, phase, elapsed = invented()
    tokens = tokens_from_history(counts,glove,digit,phase,elapsed)
    np.testing.assert_equal(tokens[:,:5],glove)
    assert tokens.shape==(4,157)
    np.testing.assert_allclose(tokens[:,11], 1.)  # index/active intercept = 5 + 6
    np.testing.assert_allclose(tokens[:,12], [0.8,0.84,0.88,0.92])
    band = band_features(counts[:160])
    assert band[0]>band[46] and band[46+1]>band[1]
    np.testing.assert_allclose(band_features(counts[:160] + np.arange(160)[:,None]),band,atol=1e-12)
    assert grid(1,1600) is None
    assert np.all(grid(3,2003)%40==0) and grid(3,2003)[0] == 400
    rng=np.random.default_rng(9)
    n=24001
    attrs = dict(ecog=rng.integers(-50,51,(n,46)),flex=rng.integers(0,800,(n,5)))
    # A synthetic chronological sequence with two digits, sufficient donors, and a crossing trial.
    trials = [(d,s,s+2000,s+4000) for d,s in zip([1,2,1,1,2,2],range(0,24000,4000))]
    src=SimpleNamespace(**attrs,complete_trials=lambda:iter(trials))
    part=make_partition(src,(0,20001))
    assert part.digits == [1,1,2] and len(part.target)==204
    np.testing.assert_array_equal(part.earlier[...,:65],part.aligned[...,:65])
    np.testing.assert_allclose(part.earlier[68:136,:,BRAIN],part.aligned[:68,:,BRAIN])
    # Single-window online API agrees with the training extractor. Changes past cutoff affect only targets.
    t=840
    sample_before,y=phase_arrays(src,1,0,0,np.array([t]))
    deployed=tokens_from_history(src.ecog[t-279:t+1],src.flex[[t-120,t-80,t-40,t]],1,0,t)
    np.testing.assert_allclose(sample_before[0],deployed,atol=1e-11)
    src.ecog[t+1:]+=900
    src.flex[t+1:]+=900
    sample_after,new_y=phase_arrays(src,1,0,0,np.array([t]))
    np.testing.assert_equal(sample_before,sample_after)
    np.testing.assert_equal(new_y,y+900)
    assert boot_draws(23).shape == (5000,23)
    np.testing.assert_equal((np.diff(boot_draws(23)[:,:3],axis=1)%23),1)
    # Fitted means derive from fit rows, and checkpoint reload preserves predictions.
    m=ridge_fit(part.aligned,part.target,'motion_cue')
    np.testing.assert_allclose(m['mean'],part.aligned[...,:65].reshape(204,-1).mean(axis=0))
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'weights.npz'
        np.savez_compressed(path,**m)
        pred=ridge_predict(part.aligned,'motion_cue',m)
        np.testing.assert_equal(pred,ridge_predict(part.aligned,'motion_cue',load_checkpoint(path)))
    print('Pass: source-free invented clock, units, band order, common reference, causal footprint, eligible trial boundaries, earlier matched donors, paired block sampler, fit-only means, checkpoint reload.')


if __name__=='__main__':
    main()
