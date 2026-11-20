"""Repeat the frozen experiment with regenerated, numerically authenticated inputs.

Example: python -B replay.py --base movement.npz --scalp paired.npz --prior previous-fit --out repeated-fit
"""
import argparse
from pathlib import Path

import numpy as np
import torch

import training as fit
from scalp_inputs import load_inputs, typed_digest

EXPECTED = fit.load(Path(__file__).with_name('comparison-identities.json'))


def confirm(expected, observed, label):
    if expected != observed:
        raise ValueError(f'Scientific identity mismatch for {label}')


def check_prior(prior):
    """Authenticate numerical arrays. Runtime metadata and ZIP packaging may differ."""
    files = {}
    with np.load(prior/'splits-and-orders.npz', allow_pickle=False) as z:
        confirm(EXPECTED['typed_splits'],typed_digest({k:z[k] for k in z.files}),'prior splits and full draws')
    for seed in fit.SEEDS:
        name=f'oof-seed-{seed}.npz'
        with np.load(prior/name,allow_pickle=False) as z:
            keys=['row','fold',*(k+'_'+field for k in fit.REUSED for field in ('rms','path'))]
            confirm(EXPECTED['typed_forecasts'][str(seed)],typed_digest({k:z[k] for k in keys}),name)
        files[name]=fit.digest(prior/name)
        for fold in range(3):
            rec=f'fits/seed-{seed}-fold-{fold}.json'
            files[rec]=fit.digest(prior/rec)
    for name,expected in EXPECTED['typed_checkpoints'].items():
        file=prior/'fits'/name
        with np.load(file,allow_pickle=False) as z:
            confirm(expected,typed_digest({k:z[k] for k in z.files}),name)
        files['fits/'+name]=fit.digest(file)
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('base','scalp','prior','out'):
        parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args()
    args.device='cpu'
    args.threads=3
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    args.out.mkdir(exist_ok=True,parents=True)
    (args.out/'checkpoints').mkdir(exist_ok=True)
    inputs=load_inputs(args.base,args.scalp)
    with np.load(args.base,allow_pickle=False) as z:
        data={k:z[k] for k in (*fit.INPUT_KEYS,'person',*fit.LABELS)}
    confirm(EXPECTED['typed_development_inputs_and_labels'],typed_digest(data),'development inputs and labels')
    archive_manifest=check_prior(args.prior)
    prior_design=fit.load(args.prior/'design.json')
    folds=np.full(len(data['domain']),-1,dtype=np.int64)
    for d in (0,1):
        for i,person in enumerate(np.unique(data['person'][data['domain']==d])):
            folds[(data['domain']==d)&(data['person']==person)]=i%3
    assert (folds>=0).all()
    fit.design(data,inputs,folds,args,prior_design)
    plan=fit.load(args.out/'design.json')
    with np.load(args.out/'splits.npz',allow_pickle=False) as splits:
        for seed in fit.SEEDS:
            for fold in range(3):
                fit.run_fit(data,inputs,folds,plan,splits,seed,fold,args)
    # Future labels are discarded before predicting any held row.
    for key in fit.LABELS:
        del data[key]
    for seed in fit.SEEDS:
        fit.predict_seed(data,inputs,folds,plan,seed,args,archive_manifest)
    print(f'Completed three seeds and three person folds in {args.out}')


if __name__=='__main__':
    main()
