"""Predict from four consecutive 50-ms observations in the source recording frame."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from data import CONTACTS, norm
from experiment import DRAWS, load_weights, native_samples


def input_array(packet, key, shape):
    if packet.get(key) is None:
        return np.zeros((1,*shape),dtype=np.float32),False
    out=np.asarray(packet[key],dtype=np.float64)
    if out.shape!=shape or not np.isfinite(out).all():
        raise ValueError(f"{key} must contain {shape} finite values")
    if key=="counts" and ((out<0)|(out!=np.floor(out))).any():
        raise ValueError("counts must be nonnegative integers")
    return out[None],True


@torch.inference_mode()
def forecast(packet, directory, task, arch, seed):
    sensor=packet["sensor"]
    if sensor not in ("hand","handle"):
        raise ValueError("sensor must be hand or handle")
    dim=3 if sensor=="hand" else 2
    p,visible_pose=input_array(packet,"pose",(4,2*dim))
    c,visible_counts=input_array(packet,"counts",(4,len(CONTACTS)))
    if not (visible_pose or visible_counts):
        raise ValueError("provide pose, counts or both")
    if visible_counts and packet.get("contacts")!=CONTACTS:
        raise ValueError("counts require the ordered acquisition contacts from protocol.json")
    weights=directory/sensor
    with np.load(weights/"scales.npz",allow_pickle=False) as f:
        sc={k:f[k] for k in f.files}
    model=load_weights(weights/f"{task}-{arch}-{seed}.npz",dim if task=="movement" else len(CONTACTS),arch,"cpu",2*dim)
    mask=torch.tensor([[visible_pose,visible_counts]],dtype=torch.float32)
    memory=model.encode(torch.from_numpy(norm(p,"pose",sc)),torch.from_numpy(norm(c,"counts",sc)),mask)
    rng=np.random.default_rng(110000+seed*37)
    z=torch.from_numpy(rng.standard_normal((DRAWS,2,model.output),dtype=np.float32))
    samples=native_samples(model.generate(memory.repeat_interleave(DRAWS,0),z).numpy(),task,sc)
    lo,hi=np.quantile(samples,[.1,.9],axis=0)
    out=dict(sensor=sensor,target=task,architecture=arch,training_seed=seed,draws=DRAWS,
             horizons=["+50 ms","+100 ms"] if task=="movement" else ["first 50 ms","next 50 ms"],
             units="displacement in centimetres from last observation" if task=="movement" else "spikes per contact in 50 ms",
             axes=list("xyz"[:dim]) if task=="movement" else CONTACTS,
             sample_mean=samples.mean(axis=0).tolist(),lower_decile=lo.tolist(),upper_decile=hi.tolist())
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("packet",type=Path)
    p.add_argument("--weights",type=Path,default=Path(__file__).with_name("weights"))
    p.add_argument("--task",choices=["movement","neural"],required=True)
    p.add_argument("--architecture",choices=["ar","diffusion","hybrid"],required=True)
    p.add_argument("--seed",type=int,choices=[17,41,73],default=17)
    args=p.parse_args()
    torch.set_num_threads(1)
    torch.backends.mha.set_fastpath_enabled(False)
    print(json.dumps(forecast(json.loads(args.packet.read_text()),args.weights,args.task,args.architecture,args.seed),indent=2,allow_nan=False))
