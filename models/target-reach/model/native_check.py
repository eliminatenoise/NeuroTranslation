"""Compare every portable Transformer forecast with native CPU PyTorch at the 3D positions used."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fit import Net
from kernel import features,tokens,MODES,SEEDS

def check(data,weights,out):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    with np.load(data,allow_pickle=False) as a:
        raw=tokens(a['xyz'],a['time'],a['hand'],a['target'])
    with np.load(out/'forecasts.npz') as preds:
        arrays={};errors={}
        for mode in MODES:
            pool=[]
            for seed in SEEDS:
                w=json.loads((weights/f'{mode}-{seed}.json').read_bytes())
                network=Net();network.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in w['parameters'].items()})
                network.eval()
                with torch.no_grad():
                    result=network(torch.tensor(features(raw,w),dtype=torch.float32)).numpy()*w['target_scale']
                pool.append(result)
            arr=np.stack(pool)
            delta=float(np.max(abs(arr-preds['transformer_'+mode])))
            assert delta<2e-5,(mode,delta)
            arrays[mode]=arr;errors[mode]=delta
    np.savez_compressed(out/'native-transformer.npz',**arrays)
    (out/'native-check.json').write_text(json.dumps(errors,indent=2)+'\n')
if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__)
    for k in ('data','weights','out'):c.add_argument(k,type=Path)
    a=c.parse_args();check(a.data,a.weights,a.out)
