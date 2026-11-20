"""Build two invented public examples; export recorded reference pairs only when requested locally."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from predict import forecast

HERE = Path(__file__).resolve().parent
DATA = HERE.parent/'shared-motion-data'
sys.path.insert(0,str(DATA))
from features import history_tokens


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path, default=HERE/'shared-weights.npz')
    p.add_argument('--out', type=Path, default=HERE/'reference-examples.json')
    p.add_argument('--local-recorded', type=Path, help="Local-only audit output. Requires reconstructed source packet.")
    args=p.parse_args()
    domain=['wrist','rat']
    positions=[[[0,0,0],[1,.2,.4],[2,.7,1.1],[3,.9,1.4],[3.5,1.1,1.6]],
               [[0,0],[1.8,0],[3.2,0],[4.8,.2],[6.0,.7]]]
    times=[[0,.245,.486,.738,.990],[-.008,.232,.489,.744,.991]]
    x=np.stack([history_tokens(pos,tm,1.) for pos,tm in zip(positions,times)])
    predicted=forecast(x,domain,args.checkpoint).tolist()
    result=dict(provenance="Both histories are invented for software verification. No observed target.",
                domain=domain, positions_cm=positions, history_native_s=times, cutoff_s=[1.,1.],
                x=x.tolist(), expected_cm=predicted)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    if args.local_recorded:
        from methods import load_data
        a=load_data(DATA/'train.npz','train')
        rows=[int(np.flatnonzero(a['domain']==d)[0]) for d in domain]
        pred=forecast(a['x'][rows],domain,args.checkpoint).tolist()
        local=dict(purpose="First row of each TRAIN domain. Private local verification only.",index=rows,domain=domain,
                   recording=a['recording'][rows].tolist(), cutoff_s=a['cutoff_s'][rows].tolist(),
                   x=a['x'][rows].tolist(), expected_cm=pred, measured_cm=a['y'][rows].tolist())
        args.local_recorded.write_text(json.dumps(local,indent=2)+'\n')


if __name__=='__main__':
    main()
