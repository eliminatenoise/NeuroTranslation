"""Run the published original and specialist comparison on a rebuilt development cache."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from scalp_inputs import typed_digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='Public cross-limb-movement source directory')
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    expected=json.loads(Path(__file__).with_name('comparison-identities.json').read_text())
    src=args.source.resolve()
    for name, wanted in expected['published_prior_code'].items():
        if hashlib.sha256((src/name).read_bytes()).hexdigest()!=wanted:
            raise ValueError(f'Unexpected published prior implementation at {name}')
    sys.path.insert(0,str(src))
    import fit as prior
    if Path(prior.__file__).resolve()!=src/'fit.py':
        raise ValueError('The prior implementation was not imported')
    with np.load(args.base,allow_pickle=False) as z:
        data={k:z[k] for k in (*prior.INPUT_KEYS,'person','future_rms','future_path_mm')}
    if typed_digest(data)!=expected['typed_development_inputs_and_labels']:
        raise ValueError('Wrong development cohort or signal arrays')
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    args.out.mkdir(exist_ok=True,parents=True)
    (args.out/'fits').mkdir(exist_ok=True)
    folds=prior.folds_of(data)
    prior.prepare(data,folds,args.out)
    config=SimpleNamespace(output=args.out,device='cpu')
    for seed in prior.SEEDS:
        for fold in range(3):
            prior.fit_fold(data,folds,config,seed,fold)
    del data['future_rms'], data['future_path_mm']
    for seed in prior.SEEDS:
        prior.predict_seed(data,folds,config,seed)


if __name__=='__main__':
    main()
