"""Fit all fixed alternatives using only training people."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

from predict import MODES, fields, normalize, squared, transformer

class HistoryTransformer(nn.Module):
    def __init__(self,features):
        super().__init__()
        self.embed=nn.Linear(features,24)
        self.pos=nn.Parameter(torch.zeros(8,24))
        nn.init.normal_(self.pos,std=.02)
        self.n1,self.n2,self.n3=(nn.LayerNorm(24) for _ in range(3))
        self.qkv=nn.Linear(24,72)
        self.out=nn.Linear(24,24)
        self.ff1,self.ff2=nn.Linear(24,48),nn.Linear(48,24)
        self.head=nn.Linear(24,1)

    def forward(self,x):
        h=self.embed(x)+self.pos
        q,k,v=self.qkv(self.n1(h)).chunk(3,dim=-1)
        def heads(a):
            return a.reshape(len(x),8,3,8).transpose(1,2)
        q,k,v=map(heads,(q,k,v))
        mix=((q@k.transpose(-1,-2))/(8**.5)).softmax(-1)@v
        h=h+self.out(mix.transpose(1,2).reshape(len(x),8,24))
        h=h+self.ff2(self.ff1(self.n2(h)).relu())
        return self.head(self.n3(h[:,-1]))[:,0]


def weights_for(person,repeat):
    out=np.zeros(len(person))
    for p in np.unique(person):
        repeats=np.unique(repeat[person==p])
        for r in repeats:
            mask=(person==p)&(repeat==r)
            out[mask]=1/(len(np.unique(person))*len(repeats)*mask.sum())
    return out/out.sum()


def scaling(x,w):
    xf,ok=fields(x)
    weight=w[:,None,None]/8
    valid_weight=(weight*ok).sum(axis=(0,1))
    center=(weight*np.where(ok,xf,0)).sum(axis=(0,1))/np.maximum(valid_weight,1e-15)
    var=(weight*np.where(ok,(xf-center)**2,0)).sum(axis=(0,1))/np.maximum(valid_weight,1e-15)
    scale=np.sqrt(var)
    scale[scale<1e-7]=1
    for sl in (slice(18,24),slice(32,40)):
        center[sl]=0
        scale[sl]=1
    return {"center":center.astype("f4"),"scale":scale.astype("f4")}


def linear_system(x,y,w,lam):
    mean=w@x
    ymean=w@y
    u=x-mean
    matrix=(u*w[:,None]).T@u+lam*np.eye(x.shape[1])
    coef=np.linalg.solve(matrix,(u*w[:,None]).T@(y-ymean))
    return {"coef":coef,"bias":np.asarray(ymean-mean@coef)}


def fit_models(data,out,internal,steps=400,only=None):
    internal.mkdir(parents=True,exist_ok=True)
    out.mkdir(parents=True,exist_ok=True)
    x,y=data["x"],data["y"]/500
    if not (data["person"].min()>=1 and data["person"].max()<=30):
        raise ValueError("fit required training partitions")
    w=weights_for(data["person"],data["repeat"])
    params=scaling(x,w)
    z=normalize(x,params)
    y_train=torch.from_numpy(y.astype("f4"))
    records={}
    for mode,sl in MODES.items():
        if only and mode!=only:
            continue
        started=time.perf_counter()
        torch.manual_seed(7693)
        rng=np.random.default_rng(7693)
        z_t=torch.from_numpy(np.ascontiguousarray(z[:,:,sl]))
        model=HistoryTransformer(z_t.shape[-1])
        optimizer=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.01)
        model.train()
        for _ in range(steps):
            ind=rng.choice(len(z),size=128,p=w)
            optimizer.zero_grad(set_to_none=True)
            loss=(model(z_t[ind])-y_train[ind]).square().mean()
            loss.backward()
            optimizer.step()
        model.eval()
        state={k:v.detach().numpy() for k,v in model.state_dict().items()}
        ww={**params,**state}
        np.savez_compressed(out/f"transformer-{mode}.npz",**ww)
        probe=np.arange(min(len(z_t),64))
        with torch.no_grad():
            expected=(500*model(z_t[probe])).clip(min=0).numpy()
        parity=float(np.max(np.abs(expected-transformer(x[probe],ww,mode))))
        assert parity<.002
        flat=z[:,:,sl].reshape(len(z),-1).astype("f8")
        np.savez_compressed(out/f"ridge-{mode}.npz",**params,**linear_system(flat,y,w,.01))
        records[mode]={"updates":steps,"parameters":sum(p.numel() for p in model.parameters()),
                       "portable_max_abs_difference_N":parity,"elapsed_s":time.perf_counter()-started}
    if only:
        return records
    flat=z[:,:,MODES["markers"]].reshape(len(z),-1).astype("f8")
    inds=np.random.default_rng(7694).choice(len(z),size=256,replace=True,p=w)
    centres=flat[inds]
    distances=squared(centres,centres)
    bw=np.median(distances[distances>0])
    kernel=np.exp(-squared(flat,centres)/bw)
    np.savez_compressed(internal/"marker-kernel.npz",**params,centres=centres,bandwidth=bw,
                        **linear_system(kernel,y,w,.0001))
    records["training_mean_N"]=float(w@data["y"])
    return records


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("train",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("private_fit",type=Path,help="private only; kernel stores measured training landmarks")
    p.add_argument("--threads",type=int,default=1)
    p.add_argument("--timing-only",action="store_true",help="fixed synthetic 8-step route check only")
    a=p.parse_args()
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    if a.timing_only:
        rng=np.random.default_rng(7)
        sx=rng.normal(size=(600,8,40)).astype("f4")
        sx[:,:,18:24]=1
        sx[:,:,32:40]=1
        fake={"x":sx,"y":rng.uniform(0,1000,600).astype("f4"),"person":np.repeat([1,2],300),"repeat":np.tile(np.repeat([1,2],150),2)}
        print(json.dumps(fit_models(fake,a.out,a.private_fit,steps=8,only="combined")))
        return
    if (a.private_fit/"fit-seal.json").exists():
        raise ValueError("locked fit exists; use a clean output directory for independent reproduction")
    start=time.perf_counter()
    with np.load(a.train,allow_pickle=False) as train:
        rec=fit_models(train,a.out,a.private_fit)
        people=np.unique(train["person"])
        rec.update({"training_people":len(people),"trial_count":len(set(zip(train["person"],train["repeat"]))),"training_anchors":len(train["y"])})
    paths=[*sorted(a.out.glob("*.npz")),a.private_fit/"marker-kernel.npz"]
    rec.update({"torch":str(torch.__version__),"numpy":str(np.__version__),"device":"cpu",
                "intra_threads":torch.get_num_threads(),"interop_threads":torch.get_num_interop_threads(),
                "elapsed_s":time.perf_counter()-start,
                "weight_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in paths},
                "train_sha256":hashlib.sha256(a.train.read_bytes()).hexdigest(),
                "frozen_files_sha256":{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()
                                      for n in ("protocol.json","qualification.json","extract.py","predict.py","fit.py","assess.py")}})
    (a.private_fit/"fit-seal.json").write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps(rec,indent=2))

if __name__=="__main__":
    main()
