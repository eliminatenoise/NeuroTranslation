"""Fit a contact-specific update on one known day's training windows."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ARMS=("measured_update","stale_position","earlier","movement_only")
RIDGE=0.05
def pool(spikes,guide,contact):
    match=(guide[:,0]==contact)&(guide[:,1]>0)
    if not match.any():
        raise ValueError("No positive-sort column for this contact")
    return spikes[:,:,match].sum(axis=2)

def features(src,contact,arm,donors=None):
    guide=src["unit_guide"]
    pose=src["pose"]
    motion=src["movement"] if donors is None else src["movement"][donors]
    known=[pose[:,-1],pose[:,-1]-pose[:,9],src["cue"][:,-1]]
    if arm!="movement_only":
        history=pool(src["spikes"],guide,contact).reshape(-1,4,5).sum(2)
        known.append(np.log1p(history))
        if arm!="earlier":
            recent=pool(src["concurrent"],guide,contact).reshape(-1,2,5).sum(2)
            known.append(np.log1p(recent))
    if arm in ("movement_only","measured_update"):
        known.extend((motion[:,4],motion[:,9]))
    return np.column_stack(known)

def loss(params,x,y,w):
    eta=params[0]+x@params[1:]
    rates=np.exp(eta)
    residual=w*(rates-y)
    obj=w@(rates-y*eta)+0.5*RIDGE*(params[1:]@params[1:])
    gradient=np.r_[residual.sum(),x.T@residual+RIDGE*params[1:]]
    return obj,gradient

def fit_one(x,y,w):
    mean=w@x
    scale=np.maximum(np.sqrt(w@((x-mean)**2)),1e-8)
    z=np.clip((x-mean)/scale,-8,8)
    start=np.zeros(1+x.shape[1]);start[0]=np.log(max(w@y,1e-6))
    opt=minimize(loss,start,args=(z,y,w),jac=True,method="L-BFGS-B",
                 options={"ftol":1e-14,"gtol":1e-8,"maxiter":500,"maxls":50})
    grad=float(np.max(np.abs(opt.jac)))
    if not opt.success or grad>1e-5:
        raise ValueError((opt.message,grad))
    return {"mean":mean.tolist(),"scale":scale.tolist(),"coefficients":opt.x.tolist(),
            "mean_count":float(w@y),"iterations":int(opt.nit),"max_gradient":grad}

def predict(x,model):
    z=np.clip((x-np.array(model["mean"]))/np.array(model["scale"]),-8,8)
    b=np.array(model["coefficients"])
    return np.exp(b[0]+z@b[1:])

def train(path,mode):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!="40bb17cd64e61bfb4ef52b5ee943d27d50e1c82bbf487d58c623c4ed2d6666ab":
        raise ValueError("Expected the immutable September 7 training shard")
    with np.load(path,allow_pickle=False) as d:
        rows={k:d[k] for k in ("original","unit_guide","spikes","pose","movement","concurrent","cue","delayed")}
    unique,index,n=np.unique(rows["original"],return_inverse=True,return_counts=True)
    w=1/(len(unique)*n[index])
    guide=rows["unit_guide"];contacts=np.unique(guide[guide[:,1]>0,0])
    assert len(unique)==198 and len(index)==519 and len(contacts)==22
    out={"source_sha256":digest,"row_count":len(index),"originals":len(unique),"arms":{}}
    if mode=="qualify":
        contacts=contacts[:3]
    for arm in ARMS:
        models={}
        for c in contacts:
            x=features(rows,c,arm);y=pool(rows["delayed"],guide,c).sum(1)
            m=fit_one(x,y,w)
            m["positive_sort_count"]=int(np.count_nonzero((guide[:,0]==c)&(guide[:,1]>0)))
            if not np.all(np.isfinite(predict(x,m))):
                raise ValueError(c)
            models[str(c)]=m
        out["arms"][arm]=models
    return out

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source",type=Path);cli.add_argument("output",type=Path)
    cli.add_argument("--qualify",action="store_true")
    args=cli.parse_args()
    result=train(args.source,"qualify" if args.qualify else "fit")
    with args.output.open("x") as stream:
        stream.write(json.dumps(result,allow_nan=False,separators=(",",":"))+"\n")
