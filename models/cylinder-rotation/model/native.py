"""Verify the distributed forecasts against their native fitted PyTorch state dictionaries."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from portable import MODES,SEEDS,make_tokens,inputs
from train import Encoder

def reconstruct(source,weights,results):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    with np.load(source,allow_pickle=False) as s:
        raw=make_tokens(s['gyro'],s['accel'],s['time'],s['hand'],s['target'])
        donor=s['donor'];valid=donor>=0;wrong=raw[valid].copy();wrong[:,:,6:12]=raw[donor[valid],:,6:12]
    differences={};saved={}
    with np.load(results/'forecasts.npz',allow_pickle=False) as archive, torch.no_grad():
        for arm in (*MODES,'wrong_accel'):
            data=wrong if arm=='wrong_accel' else raw
            if not len(data):continue
            forecasts=[]
            for seed in SEEDS:
                mode='full' if arm=='wrong_accel' else arm
                model=json.loads((weights/f'{mode}-{seed}.json').read_bytes())
                network=Encoder();network.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in model['parameters'].items()});network.eval()
                x=inputs(data,model)
                pred=np.concatenate([network(torch.as_tensor(x[i:i+768],dtype=torch.float32)).detach().numpy() for i in range(0,len(x),768)])
                forecasts.append(pred*np.asarray(model['y_scale'])+np.asarray(model['y_mean']))
            arr=np.array(forecasts);dest=archive['transformer_'+arm];ref=dest[:,valid] if arm=='wrong_accel' else dest
            limit=3 if arm=='gyro_loss' else 6
            err=float(np.max(np.abs(arr[:,:,:limit]-ref[:,:,:limit])));assert err<.0005,(arm,err)
            differences[arm]=err
            # Keep only checked gyro-only output; leave undefined entries missing.
            if arm=='gyro_loss':arr[:,:,3:]=np.nan
            if arm=='wrong_accel':
                complete=np.full(dest.shape,np.nan);complete[:,valid]=arr;arr=complete
            saved[arm]=arr
    np.savez_compressed(results/'native-transformer.npz',**saved)
    (results/'native-check.json').write_text(json.dumps(differences,indent=2)+'\n')
if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__)
    for n in ('source','weights','out'):c.add_argument(n,type=Path)
    a=c.parse_args();reconstruct(a.source,a.weights,a.out)
