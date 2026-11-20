# SPDX-License-Identifier: CC0-1.0
"""One predeclared inner comparison. Writes aggregate statistics and parameters only."""
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
from model import (BRAIN, FEATURES, TOKEN_LAGS, WINDOW, band_features, cue_basis, encoder_fit,
                   encoder_predict, load_checkpoint, ridge_fit, ridge_predict)

FINGERS = ('thumb', 'index', 'middle', 'ring', 'little')
SAMPLE_SHA256 = '57ea209841127b6cc04f2c03f8f6146f01b3e0235d169365d009cf3f9c643e9c'
PLAN_SHA = '43a77b57971aa05c072c40c656c317db7f501333e329f549992516c4837dbda9'
SPLITS = {'train':(0,236000), 'development_evaluation':(244000,362000)}
TICKS = np.arange(9,43)*40
PHASE_N = len(TICKS)
TRIAL_N = 2*PHASE_N


@dataclass
class Partition:
    aligned: np.ndarray
    earlier: np.ndarray
    target: np.ndarray
    digits: list
    counts: dict


def grid(start, stop):
    cut = (start+39)//40*40 + TICKS
    if cut[0]+TOKEN_LAGS[0]-WINDOW+1 < start or cut[-1]+120 >= stop:
        return None
    return cut


def phase_arrays(source, digit, phase, start, cutoff):
    ends = cutoff[:,None]+TOKEN_LAGS
    unique, inverse = np.unique(ends, return_inverse=True)
    windows = source.ecog[unique[:,None] + np.arange(-159,1)]
    neural = band_features(windows)[inverse.reshape(ends.shape)]
    tokens = np.concatenate([source.flex[ends], cue_basis(digit, phase, (ends-start)/1000), neural], axis=-1)
    return tokens, source.flex[cutoff+120].astype(np.float64)


def make_partition(source, bounds):
    latest = {}
    aligned, earlier, target, digits = [], [], [], []
    eligible, short, donors = Counter(), Counter(), Counter()
    lo, hi = bounds
    for digit, onset, offset, end in source.complete_trials():
        if not (lo <= onset < offset < end <= hi):
            continue
        cue_ticks, rest_ticks = grid(onset, offset), grid(offset, end)
        if cue_ticks is None or rest_ticks is None:
            short[digit] += 1
            continue
        eligible[digit] += 1
        p0, y0 = phase_arrays(source, digit, 0, onset, cue_ticks)
        p1, y1 = phase_arrays(source, digit, 1, offset, rest_ticks)
        tokens = np.concatenate([p0,p1])
        if digit in latest:
            donor_end, donor_signals = latest[digit]
            assert donor_end <= onset
            mismatch = tokens.copy()
            mismatch[...,BRAIN] = donor_signals
            aligned.append(tokens)
            earlier.append(mismatch)
            target.append(np.concatenate([y0,y1]))
            digits.append(digit)
        else:
            donors[digit] += 1
        latest[digit] = end, tokens[...,BRAIN].copy()
    def named(count):
        return {name:int(count[d+1]) for d,name in enumerate(FINGERS)}
    counts = dict(eligible_by_cue=named(eligible), first_donor_only_by_cue=named(donors),
                  short_trial_excluded_by_cue=named(short), recipients_by_cue=named(Counter(digits)),
                  scored_trials=len(digits), ticks=len(digits)*TRIAL_N, ticks_per_trial=TRIAL_N)
    return Partition(np.concatenate(aligned), np.concatenate(earlier), np.concatenate(target), digits, counts)


def boot_draws(n):
    rng = np.random.default_rng(48019)
    start = rng.integers(0, n, (5000, (n+2)//3))
    return ((start[...,None] + np.arange(3))%n).reshape(5000,-1)[:,:n]


def convert(obj):
    if isinstance(obj,(np.ndarray,np.generic)):
        return obj.tolist()
    raise TypeError(type(obj))


def write_json(path, value):
    path.write_text(json.dumps(value, default=convert, indent=2, allow_nan=False) + '\n')


def compare(errors, a, b, scale, draws):
    d = errors[a].mean(axis=1) - errors[b].mean(axis=1)
    samples = d[draws].mean(axis=1)
    normed = (d/scale).mean(axis=1)
    interval = np.quantile(normed[draws].mean(axis=1), [0.025,0.975])
    return dict(baseline=a, candidate=b, per_digit_gain_glove_units=d.mean(axis=0),
                per_digit_interval=np.quantile(samples, [0.025,0.975], axis=0).T,
                macro_normalized_gain=normed.mean(), macro_interval=interval,
                evaluated_trials_positive_macro_gain=int(np.count_nonzero(normed>0)),
                phase_normalized_gain=((errors[a]-errors[b])/scale).reshape(-1,2,PHASE_N,5).mean(axis=(0,2,3)))


def summarize(pred, train, dev):
    scale = train.target.std(axis=0)
    if np.any(scale <= 0):
        raise ValueError('Undefined normalization for constant training target')
    errors = {key:np.abs(value-dev.target).reshape(-1,TRIAL_N,5) for key,value in pred.items()}
    scores = {key:dict(per_digit_mae_glove_units=arr.mean(axis=(0,1)), macro_normalized_mae=(arr/scale).mean(),
                       phase_normalized_mae=(arr/scale).reshape(-1,2,PHASE_N,5).mean(axis=(0,2,3))) for key,arr in errors.items()}
    pairs = [('motion_cue','aligned'),('earlier_substitute','aligned'),('earlier_fit','aligned'),('persistence','motion_cue'),
             ('motion','motion_cue'),('cue','motion_cue')]
    if 'encoder_aligned' in pred:
        pairs += [('encoder_motion_cue','encoder_aligned'),('encoder_earlier_substitute','encoder_aligned'),('aligned','encoder_aligned')]
    draws = boot_draws(len(dev.digits))
    contrasts = [compare(errors,a,b,scale,draws) for a,b in pairs]
    return dict(schema=1, question='120-ms future recorded glove, within one development prefix and one participant',
                freeze_sha256=PLAN_SHA, source_sha256=SAMPLE_SHA256, digits=FINGERS, intervals='within-record paired, 5000 circular moving-block bootstrap samples of consecutive trial triplets',
                train=train.counts, development_evaluation=dev.counts, count_people=1,
                cross_digit_training_target_correlations=np.corrcoef(train.target.T),
                phase_order=['display','following blank'], scores=scores, contrasts=contrasts,
                provisional_ridge_advantage=all(c['macro_interval'][0]>0 for c in contrasts[:2]))


def run(out, mode, reuse, threads, load_training):
    out.mkdir(parents=True, exist_ok=True)
    params = out/'weights'
    params.mkdir(exist_ok=True)
    data = load_training()
    train, dev = [make_partition(data, b) for b in SPLITS.values()]
    del data
    pred = {'persistence':dev.aligned[:,-1,:5]}
    def get_weights(name, fit):
        path = params/(name+'.npz')
        if reuse and path.exists():
            return load_checkpoint(path)
        vals = fit()
        np.savez_compressed(path, **vals)
        return vals
    for name in FEATURES:
        x = train.earlier if name=='earlier_fit' else train.aligned
        d = dev.earlier if name=='earlier_fit' else dev.aligned
        w = get_weights(name, lambda:ridge_fit(x,train.target,name))
        pred[name] = ridge_predict(d,name,w)
        if name=='aligned':
            pred['earlier_substitute'] = ridge_predict(dev.earlier,name,w)
    write_json(out/'ridge-results.json', summarize(pred,train,dev))
    if mode=='all':
        import torch
        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        for aligned in [False,True]:
            name = 'encoder_'+('aligned' if aligned else 'motion_cue')
            w = get_weights(name, lambda:encoder_fit(train.aligned, train.target, aligned))
            pred[name] = encoder_predict(dev.aligned,aligned,w)
            if aligned:
                pred['encoder_earlier_substitute'] = encoder_predict(dev.earlier,True,w)
        write_json(out/'results.json', summarize(pred,train,dev))
    print(f'{len(train.digits)} fit trials, {len(dev.digits)} development evaluation trials; {mode} complete')
