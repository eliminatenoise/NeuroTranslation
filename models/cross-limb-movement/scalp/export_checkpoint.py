"""Export one of the 45 released person-fold models to portable inference JSON."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fusion_model import KINDS, create, export

HERE=Path(__file__).resolve().parent


def checkpoint(seed,fold,kind):
    stats=json.loads((HERE/'fold-scales.json').read_text())[str(fold)]
    prefix=f's{seed}-f{fold}-{kind}/'
    model=create(seed)
    with np.load(HERE/'checkpoints.npz', allow_pickle=False) as archive:
        state={k.removeprefix(prefix):torch.from_numpy(archive[k]) for k in archive.files if k.startswith(prefix)}
    model.load_state_dict(state,strict=True)
    return export(model.eval(),kind,stats['scales'],stats['scalp_scales'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('seed',type=int,choices=(1641,2718,3917))
    p.add_argument('fold',type=int,choices=(0,1,2))
    p.add_argument('kind',choices=KINDS)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(checkpoint(args.seed,args.fold,args.kind),separators=(',',':'),allow_nan=False)+'\n')
