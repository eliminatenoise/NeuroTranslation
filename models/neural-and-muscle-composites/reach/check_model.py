"""Check model masks, source clocks, transformations and sampled trajectory ordering."""
import argparse
from pathlib import Path

import numpy as np
import torch
from data import CONTACTS, earlier_donors, read_archive
from experiment import load_weights
from models import STEPS


def check_source(directory, sensor):
    for split in ("train","block1","block2"):
        d=read_archive(directory, split, sensor)
        with np.load(directory/(split+".npz"),allow_pickle=False) as raw:
            # For the archived data all selected cases have finite readings.
            np.testing.assert_array_equal(raw["k"],d["k"])
            cols = np.arange(3) if sensor=="hand" else np.arange(6,8)
            scale = 100 if sensor=="hand" else 1
            expected = raw["movement"][:, (4,9)][:,:,cols]*scale
            np.testing.assert_array_equal(expected,d["movement"])
            for j,contact in enumerate(CONTACTS):
                matching = np.flatnonzero(raw["all_guide"][:,0]==contact)
                for part,(start,end) in enumerate([(0,5),(5,10)]):
                    expected = raw["all_concurrent"][:,start:end][:,:,matching].sum(axis=(1,2))
                    np.testing.assert_array_equal(expected,d["neural"][:,part,j])
            assert not np.any(raw["history_rows"][:,-1]>=raw["movement_rows"][:,0])
            donors=earlier_donors(d)
            matched=donors>=0
            assert np.all(d["original"][donors[matched]]!=d["original"][matched])
            np.testing.assert_array_equal(d["workspace"][donors[matched]],d["workspace"][matched])
            np.testing.assert_array_equal(d["ordinal"][donors[matched]],d["ordinal"][matched])


@torch.inference_mode()
def check_weights(weights,sensor):
    torch.manual_seed(123)
    n=12
    dim=6 if sensor=="hand" else 4
    p=torch.randn(n,4,dim)
    count=torch.randn(n,4,37)
    both=torch.ones(n,2)
    for task,out in [("neural",37),("movement",dim//2)]:
        for arch in ("ar","diffusion","hybrid"):
            model=load_weights(weights/(task+"-"+arch+"-17.npz"),out,arch,"cpu",dim)
            memory=model.encode(p,count,both)
            only_pose=both.clone()
            only_pose[:,1]=0
            torch.testing.assert_close(model.encode(p,count,only_pose),model.encode(p,count.flip(0),only_pose),atol=0,rtol=0)
            assert model.signal[0]==1 and model.signal[-1]==0 and model.noise[0]==0 and model.noise[-1]==1
            z=torch.randn(n,2,out)
            switch=z.clone()
            switch[:,1]+=3
            sampled=model.generate(memory,z)
            alt=model.generate(memory,switch)
            assert torch.isfinite(sampled).all()
            if arch in ("ar","hybrid"):
                torch.testing.assert_close(sampled[:,0],alt[:,0],atol=0,rtol=0)
                assert (sampled[:,1]-alt[:,1]).abs().max()>1e-4
            if arch=="ar":
                baseline=model.autoregress(memory,z)
                changed=model.autoregress(memory,switch)
                torch.testing.assert_close(baseline[:,0],changed[:,0],atol=0,rtol=0)
            if arch=="hybrid":
                ts=torch.full((n,),STEPS,dtype=torch.long)
                left=model.denoise(memory,z[:,1:],ts,z[:,:1],torch.zeros(n,dtype=torch.long))
                right=model.denoise(memory,z[:,1:],ts,z[:,:1]+2,torch.zeros(n,dtype=torch.long))
                torch.testing.assert_close(left,right,atol=0,rtol=0)
                first=model.denoise(memory,z[:,1:],ts,z[:,:1],torch.ones(n,dtype=torch.long))
                second=model.denoise(memory,z[:,1:],ts,z[:,:1]+2,torch.ones(n,dtype=torch.long))
                assert (first-second).abs().max()>1e-4


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--weights",type=Path,required=True)
    parser.add_argument("--sensor",choices=["handle","hand"],default="handle")
    args=parser.parse_args()
    torch.set_num_threads(1)
    torch.backends.mha.set_fastpath_enabled(False)
    check_source(args.data,args.sensor)
    check_weights(args.weights,args.sensor)
    print("Source, unit, mask and generation checks passed.")
