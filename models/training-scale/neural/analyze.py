"""Freeze a scale-up prediction and compare it with subsequent larger fits."""
import argparse
import gzip
import itertools
import json
from pathlib import Path

import numpy as np

from study import HELD, SEEDS, SIZES, model_key, ref
from prepare import HERE

CASES = [(arm,kind) for arm in ('rat','mixed') for kind in ('linear5','hinge13')]


def read(path):
    return json.loads(path.read_bytes())


def mean_losses(scores,n):
    return {f:{f'{arm}-{kind}':float(np.mean([scores[f][model_key(n,arm,s,kind)]['equal_trial']['log_loss']
            for s in SEEDS])) for arm,kind in CASES} for f in HELD}


def forecast(out):
    small = {n:read(out/f'scores-{n}.json') for n in SIZES[:-1]}
    means = {n:mean_losses(scores,n) for n,scores in small.items()}
    factor = float(np.log2(SIZES[-1]/SIZES[-2])/np.log2(SIZES[-2]/SIZES[-3]))
    pred = {f:{method:{} for method in ('plateau','log_slope','tiny_only')} for f in HELD}
    for f in HELD:
        for case, y in means[SIZES[-2]][f].items():
            pred[f]['plateau'][case] = y
            pred[f]['log_slope'][case] = y+factor*(y-means[SIZES[-3]][f][case])
            pred[f]['tiny_only'][case] = means[SIZES[0]][f][case]
    return dict(forecast_n=SIZES[-1],smaller_mean_log_losses=means,predictions=pred,
                slope_multiplier=factor,small_scores_sha256={n:ref.digest(out/f'scores-{n}.json') for n in small},
                protocol_sha256=ref.digest(HERE/'protocol.json'))


def resample_delta(a,b,draw):
    diff=np.asarray(a)-np.asarray(b)
    return dict(delta=float(diff.mean()),paired_trial_bootstrap95=np.percentile(diff[draw].mean(axis=1),[2.5,97.5]).tolist())


def combine(out, cache, public):
    sealed=read(out/'prediction-seal.json'); pred=read(out/'prediction.json')
    if ref.digest(out/'prediction.json')!=sealed['prediction_sha256'] or pred!=json.loads(json.dumps(forecast(out))):
        raise ValueError('Changed prediction or small-score files')
    scores={n:read(out/f'scores-{n}.json') for n in SIZES}
    inv=read(cache/'groups.json'); results={}
    for f in HELD:
        rows=[r for r in inv['rows'] if r['family']==f]; rg=[r for r in rows if r['qc']['resolved_targets']]
        draw=np.random.default_rng(20261121).integers(len(rg),size=(5000,len(rg)))
        trial_vectors={}; curves={}
        for n, data in scores.items():
            curves[n]={}; trial_vectors[n]={}
            for a,k in CASES:
                group=[data[f][model_key(n,a,s,k)] for s in SEEDS]; label=f'{a}-{k}'
                per_seed=np.array([v['equal_trial']['log_loss'] for v in group]); per_trial=np.array([[t['log_loss'] for t in v['by_trial']] for v in group]); trial_vectors[n][label]=per_trial.mean(axis=0)
                curves[n][label]=dict(equal_trial_log_loss=float(per_seed.mean()),seed_log_losses=per_seed.tolist(),
                       equal_trial_top1=float(np.mean([v['equal_trial']['top1'] for v in group])),
                       pooled={m:float(np.mean([v['pooled'][m] for v in group])) for m in group[0]['pooled']})
        actual={k:v['equal_trial_log_loss'] for k,v in curves[SIZES[-1]].items()}
        ranking={}; small_to_large={}
        for method,values in pred['predictions'][f].items():
            anticipated=sorted(values,key=values.get); observed=sorted(actual,key=actual.get)
            correct=sum((values[i]<values[j])==(actual[i]<actual[j]) for i,j in itertools.combinations(actual,2))
            residual={case:actual[case]-values[case] for case in actual}
            ranking[method]=dict(anticipated_order=anticipated,observed_order=observed,correct_pairs_of_six=correct,
                  winner_matched=anticipated[0]==observed[0],actual_minus_predicted=residual,
                  mean_abs_error=float(np.mean(np.abs(list(residual.values())))))
        for n in SIZES[:-1]:
            small_to_large[n]={case:resample_delta(trial_vectors[SIZES[-1]][case],trial_vectors[n][case],draw) for case in actual}
        contrasts={}; control_comparisons={}
        for n in SIZES:
            vec=trial_vectors[n]; contrasts[n]={}; control_comparisons[n]={}
            for a,b in itertools.combinations(vec,2):
                contrasts[n][f'{a} minus {b}']=resample_delta(vec[a],vec[b],draw)
            for case,values in vec.items():
                control_comparisons[n][case]={k:resample_delta(values,[t['log_loss'] for t in scores[n][f][k]['by_trial']],draw)
                                              for k in ('uniform','rate','recency')}
        results[f]=dict(held_trials=len(rg),unique_scored_rows=inv['counts'][f],candidate_units=len(rows[0]['units']),
               target_units=int((np.asarray([r['targets_per_unit'] for r in rows]).sum(axis=0)>0).sum()),
               curves=curves,controls={k:scores[SIZES[-1]][f][k]['equal_trial'] for k in ('uniform','rate','recency')},
               forecast_check=ranking,largest_minus_smaller=small_to_large,paired_contrasts=contrasts,
               model_minus_control_log_loss=control_comparisons)
    public.mkdir(parents=True,exist_ok=True); ref.dump(public/'results.json',results)
    complete={str(n):s for n,s in scores.items()}; raw=json.dumps(complete,separators=(',',':'),allow_nan=False).encode()
    (public/'by-trial-scores.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    allfits={}; samples={}
    for path in sorted(out.glob('fit-*.json')):
        fit=read(path); fit.pop('fit_seconds'); membership=fit.pop('groups'); key=path.stem.removeprefix('fit-')
        group_key=key.rsplit('-',1)[0]
        if group_key in samples and samples[group_key]!=membership:
            raise ValueError('Candidate models fitted different transitions')
        samples[group_key]=membership; allfits[key]=fit
    ref.dump(public/'models.json',dict(features='Ordered in study.design',fits=allfits,
             shared_final_rat_weights='Rat-only N=54578 weights from seed 11 also apply to seeds 23 and 47.'))
    (public/'training-membership.json.gz').write_bytes(gzip.compress(json.dumps(samples,separators=(',',':')).encode(),mtime=0))
    (public/'source-groups.json.gz').write_bytes(gzip.compress(json.dumps(inv,separators=(',',':')).encode(),mtime=0))
    (public/'prediction.json').write_bytes((out/'prediction.json').read_bytes());ref.dump(public/'prediction-seal.json',sealed)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('forecast','report'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path);p.add_argument('--public',type=Path)
    a=p.parse_args()
    if a.stage=='forecast':
        if list(a.out.glob('fit-54578-*')) or (a.out/'scores-54578.json').exists():
            raise ValueError('Largest runs already exist; use the existing seal or a clean directory')
        ref.dump(a.out/'prediction.json',forecast(a.out))
        ref.dump(a.out/'prediction-seal.json',dict(prediction_sha256=ref.digest(a.out/'prediction.json')))
    else:
        combine(a.out,a.cache,a.public)


if __name__=='__main__':
    main()
