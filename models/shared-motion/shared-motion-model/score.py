"""Score the frozen fits on one reused cohort; does not train or select weights."""
import argparse
import json
from pathlib import Path

import numpy as np

from methods import DOMAINS, SEEDS, SOURCE, digest, load_data, ridge_predictions
from predict import forecast, physical_features

HERE = Path(__file__).resolve().parent


def bootstrap(groups, domain):
    rng = np.random.default_rng(7331)
    n = len(groups)
    if domain == 'wrist':
        return rng.integers(n, size=(10000, n))
    starts = rng.integers(n, size=(10000,(n+2)//3))
    return ((starts[:,:,None] + np.arange(3)) % n).reshape(10000,-1)[:, :n]


def summarize_delta(by_group, ix):
    leave_one_out = (by_group.sum()-by_group)/(len(by_group)-1)
    return dict(mean=float(by_group.mean()), percentile_95=np.quantile(
                by_group[ix].mean(axis=1), [.025,.975]).tolist(),
                improved_groups=int((by_group<0).sum()), total_groups=len(by_group),
                leave_one_group_out=[float(leave_one_out.min()), float(leave_one_out.max())])


def evaluate_domain(data, d, fits):
    mask = data['domain']==d
    x,y,groups = (data[k][mask] for k in ('x','y','group'))
    group_names = np.unique(groups)
    ix = bootstrap(group_names,d)
    _, recent = physical_features(x)
    with np.load(fits/f'ridge-{d}.npz',allow_pickle=False) as ridge:
        raw_ridge, log_ridge = ridge_predictions(x,ridge)
    rows = dict(persistence=np.zeros(len(x)), recent=recent, ridge_cm=raw_ridge, ridge_log=log_ridge)
    for seed in SEEDS:
        for label, arm in [('joint','joint'), ('solo32',d+'32'), ('solo64',d+'64')]:
            key = f'{label}_{seed}'
            rows[key] = forecast(x, [d]*len(x), fits/f'{seed}-{arm}.npz')
    mae = {k:np.abs(y-pred) for k,pred in rows.items()}
    group_mae = {k:np.asarray([error[groups==g].mean() for g in group_names])
                 for k,error in mae.items()}
    macro = {k:float(v.mean()) for k,v in group_mae.items()}
    deployed = f'joint_{SEEDS[0]}'
    contrasts = {k:summarize_delta(group_mae[deployed]-group_mae[k],ix)
                 for k in ('persistence','recent','ridge_cm','ridge_log',f'solo32_{SEEDS[0]}',f'solo64_{SEEDS[0]}')}
    seed_contrasts = {str(s):{n:macro[f'joint_{s}']-macro[f'{n}_{s}'] for n in ('solo32','solo64')}
                      for s in SEEDS}
    transfer = (all(contrasts[f'{n}_{SEEDS[0]}']['percentile_95'][1]<0 for n in ('solo32','solo64'))
                and all(v < 0 for comparison in seed_contrasts.values() for v in comparison.values()))
    simple = all(macro[deployed]<macro[k] for k in ('persistence','recent','ridge_cm','ridge_log'))
    return dict(rows=len(x), group_counts={g:int((groups==g).sum()) for g in group_names},
                group_mae_cm={k:dict(zip(group_names,v.tolist())) for k,v in group_mae.items()},
                macro_mae_cm=macro, window_mae_cm={k:float(v.mean()) for k,v in mae.items()},
                paired_joint_minus_comparator_cm=contrasts, seed_contrasts_cm=seed_contrasts,
                three_seed_mean_macro_mae_cm={n:float(np.mean([macro[f'{n}_{s}'] for s in SEEDS]))
                                              for n in ('joint','solo32','solo64')},
                transfer_gate=bool(transfer), beats_all_physical_and_ridge_controls=bool(simple)),rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assessment', type=Path, default=SOURCE/'assessment.npz')
    parser.add_argument('--fits', type=Path, default=HERE/'fits')
    parser.add_argument('--out', type=Path, default=HERE/'results')
    args = parser.parse_args()
    data = load_data(args.assessment,'assessment')
    args.out.mkdir(exist_ok=True,parents=True)
    result = {'assessment_sha256':digest(args.assessment),'checkpoint_sha256':digest(args.fits/'shared-weights.npz'),
              'method_sha256':digest(HERE/'protocol.json'),'domains':{}}
    for d in DOMAINS:
        summary, rows = evaluate_domain(data,d,args.fits)
        result['domains'][d] = summary
        np.savez_compressed(args.out/f'local-{d}-predictions.npz',**rows)
    result['bidirectional_transfer_gate'] = all(m['transfer_gate'] for m in result['domains'].values())
    (args.out/'aggregate.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
