"""Aggregate historical participant-level errors and backtest scale forecasts."""
import argparse
from itertools import combinations
import json
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

PLAN = json.loads(Path(__file__).with_name('protocol.json').read_text())
PEOPLE = PLAN['donor_counts']
ORDERS = PLAN['order_seeds']
PRIMARY = [f'{n}_w{w}' for n in ('paired','early') for w in (8,16,32)]
DRAW = np.random.default_rng(431).integers(0,6,(10000,6))


def ranks(scores, reference):
    here = sorted(PRIMARY, key=scores.get)
    there = sorted(PRIMARY, key=reference.get)
    flipped, same, ties = [], [], []
    for a,b in combinations(PRIMARY,2):
        sign = np.sign(scores[a]-scores[b])*np.sign(reference[a]-reference[b])
        (flipped if sign < 0 else same if sign > 0 else ties).append([a,b])
    return dict(small=here, largest=there, same_top=here[0]==there[0], inversions=len(flipped),
                reversed_pairs=flipped, tied_pairs=ties, kendall_tau_a=(len(same)-len(flipped))/15)


def paired_contrast(x,y):
    diff = x-y
    ci = np.quantile(diff[DRAW].mean(1),[.025,.975],axis=0)
    return dict(difference=diff.mean(0).tolist(), ci95_low=ci[0].tolist(), ci95_high=ci[1].tolist(),
                left_lower_people=(diff < 0).sum(0).tolist(), per_person=diff.tolist())


def analyze(data):
    metrics = data['metrics']
    per_fit = data['fits']
    sets = data['training_sets']
    models = list(data['variants'])
    # Dataset x model x person x outcome, aggregating errors over training seeds.
    mean = {k:{p:{m:np.mean([v[m][p] for v in seeds.values()],axis=0) for m in models}
               for p in ('both','standing','walking')} for k,seeds in per_fit.items()}
    def keys(n,limit,order=None):
        suffix = f'{n}-{limit}'
        if n == 18:
            return [f'common-{suffix}']
        return [f'{s}-{suffix}' for s in (ORDERS if order is None else [order])]
    def dataset_rows(n,limit,model,order=None,posture='both'):
        return np.mean([mean[k][posture][model] for k in keys(n,limit,order)],axis=0)
    def outcome(n,limit,j,order=None):
        return {m:dataset_rows(n,limit,m,order).mean(0)[j] for m in PRIMARY}
    regimes = [('all',n,'all') for n in PEOPLE] + [('matched432',n,'432') for n in PEOPLE]
    regimes += [('fixed18',18,size) for size in ('432','864','1728','3456','all')]
    levels, contrasts = {}, {}
    for regime,n,limit in regimes:
        label = f'{regime}-{n}-{limit}'
        dataset_keys = keys(n,limit)
        pooled = {m:dataset_rows(n,limit,m) for m in models}
        summary = {}
        for m,people in pooled.items():
            per_order = np.array([mean[k]['both'][m].mean(0) for k in dataset_keys])
            per_seed = np.stack([np.mean([per_fit[k][str(s)][m]['both'] for k in dataset_keys],axis=(0,1))
                                 for s in PLAN['train_seeds']])
            ci = np.quantile(people[DRAW].mean(1),[.025,.975],axis=0)
            summary[m] = dict(mean=people.mean(0).tolist(),ci95_low=ci[0].tolist(),ci95_high=ci[1].tolist(),
                              mean_by_order=per_order.tolist(),mean_by_training_seed=per_seed.tolist(),
                              per_person=people.tolist(),posture={p:dataset_rows(n,limit,m,posture=p).mean(0).tolist()
                                                                   for p in ('standing','walking')})
        levels[label] = dict(n=n,windows=[sets[k]['windows'] for k in dataset_keys],models=summary)
        pairs = [(f'paired_w{w}',f'early_w{w}') for w in (8,16,32)]
        pairs += [(f'{m}_w32',f'{m}_w8') for m in ('paired','early')]
        pairs += [('paired_w16',f'without_{source}_w16') for source in ('scalp','electrical','mechanics')]
        comp = {f'{a}_minus_{b}':paired_contrast(pooled[a],pooled[b]) for a,b in pairs}
        comp['paired_w16_minus_velocity32'] = paired_contrast(pooled['paired_w16'],np.array(data['baselines']['velocity32']['both']))
        contrasts[label] = comp
    scale_contrasts = {}
    for r,l in [('all','all'),('matched432','432')]:
        for small in (3,6,12):
            scale_contrasts[f'{r}-18_minus_{small}'] = {m:paired_contrast(dataset_rows(18,l,m),dataset_rows(small,l,m)) for m in models}
    scale_contrasts['same18-all_minus_432'] = {m:paired_contrast(dataset_rows(18,'all',m),dataset_rows(18,'432',m)) for m in models}
    rank_results = {}
    for l in ('all','432'):
        rank_results[l] = {}
        for j,metric in enumerate(metrics[:2]):
            ref = outcome(18,l,j)
            rank_results[l][metric] = {str(n):dict(averaged=ranks(outcome(n,l,j),ref),
                by_order={str(o):ranks(outcome(n,l,j,o),ref) for o in ORDERS}) for n in PEOPLE[:-1]}
    forecasts = {}
    train_n = np.array(PEOPLE[:-1])
    basis = np.column_stack((np.ones(3),1/np.sqrt(train_n)))
    for j,metric in enumerate(metrics[:2]):
        estimates = {}
        for m in PRIMARY:
            observed = np.array([dataset_rows(n,'all',m).mean(0)[j] for n in PEOPLE])
            floor,amplitude = nnls(basis,observed[:-1])[0]
            pred = floor+amplitude/np.sqrt(18)
            estimates[m] = dict(observed_3_6_12_18=observed.tolist(),flat_18=observed[-2],
                                inverse_root_18=pred,fitted_intercept=floor,fitted_amplitude=amplitude,
                                flat_signed_error=observed[-2]-observed[-1], inverse_root_signed_error=pred-observed[-1])
        forecasts[metric] = dict(models=estimates,
            mean_absolute_prediction_error={method:float(np.mean([abs(v[method+'_signed_error']) for v in estimates.values()]))
                                            for method in ('flat','inverse_root')})
    base = {k:{p:np.mean(rows,axis=0).tolist() for p,rows in v.items()} for k,v in data['baselines'].items()}
    return dict(metrics=metrics, historical_people=6, assessment_events=data['assessment_events'],parameters=data['variants'],
                levels=levels,rank_against_largest=rank_results,numeric_backtest=forecasts,baselines=base,
                model_contrasts=contrasts,training_size_contrasts=scale_contrasts,
                interval='Exploratory 95% participant bootstrap intervals conditional on trained models, same six historical participants in all comparisons.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('people',type=Path)
    p.add_argument('result',type=Path)
    args=p.parse_args()
    args.result.write_text(json.dumps(analyze(json.loads(args.people.read_text())),indent=2,allow_nan=False)+'\n')
