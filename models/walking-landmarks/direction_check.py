"""Exploratory correction for the direction of walking; see direction-protocol.json."""
import argparse
import json
from pathlib import Path

import numpy as np
from assess import controls, describe, comparison, finite_json, sha
from predict import run_tokens, load_weights


def weight(data):
    out=np.empty(len(data["person"]))
    for who in np.unique(data["person"]):
        p=data["person"]==who
        reps=np.unique(data["repeat"][p])
        for r in reps:
            rows=p&(data["repeat"]==r)
            out[rows]=1/(len(set(data["person"]))*len(reps)*sum(rows))
    return out


def mean(x, w):
    wt=w.reshape((-1,)+(1,)*(x.ndim-1))*np.isfinite(x)
    denom=wt.sum(axis=0)
    return np.divide((np.nan_to_num(x)*wt).sum(axis=0),denom,out=np.full(x.shape[1:],np.nan),where=denom>0)


def aligned(data):
    movement=data["x"][:,:,24:48].reshape(-1,8,8,3)
    progress=np.nansum(movement[:,:,6:,0],axis=(1,2))
    direction=np.where(progress<0,-1,1)
    x=data["x"].copy()
    for start in (0,24):
        piece=x[:,:,start:start+24].reshape(-1,8,8,3)
        piece[:,:,:,:2]*=direction[:,None,None,None]
    y=data["y"].copy()
    y[:,:,:2]*=direction[:,None,None]
    return {**data,"x":x,"y":y},direction,int((progress==0).sum())


def phase_table(data,w):
    y=data["y"].reshape(-1,18)
    p,b=data["phase"],data["phase_bin"]
    table={"global":mean(y,w)}
    for phase in np.unique(p):
        mask=p==phase
        base=mean(y[mask],w[mask])
        table[phase]=np.where(np.isfinite(base),base,table["global"])
        for t in np.unique(b[mask]):
            ix=mask&(b==t)
            v=mean(y[ix],w[ix])
            table[f"{phase}.{t}"]=np.where(np.isfinite(v),v,table[phase])
    return table


def compare(train,test,weights):
    tr,_,train_zero=aligned(train)
    held,direction,test_zero=aligned(test)
    wt=weight(tr)
    features=tr["x"][:,:,:64].reshape(-1,64)
    mean_train=np.nan_to_num(mean(features,np.repeat(wt/8,8)))
    sd=np.sqrt(mean((features-mean_train)**2,np.repeat(wt/8,8)))
    normalized={**weights,"markers.mean":mean_train,"markers.sd":np.where(sd>1e-6,sd,1)}
    table=phase_table(tr,wt)
    pred,later=controls(held,normalized,table)
    for name in ("phase","personal"):
        pred[name][:,:,:2]*=direction[:,None,None]
    predicted=run_tokens(test["x"],weights,"transformer_combined")
    ref=np.linalg.norm(predicted-test["y"],axis=-1)
    errors={k:np.linalg.norm(pred[k]-test["y"],axis=-1) for k in ("phase","personal")}
    counts={"match":0,"reverse":0}
    trial_counts={"match":0,"reverse":0}
    for who in np.unique(held["person"]):
        repeats=np.unique(held["repeat"][held["person"]==who])
        for a,b in zip(repeats[:-1],repeats[1:]):
            old=(held["person"]==who)&(held["repeat"]==a)
            new=(held["person"]==who)&(held["repeat"]==b)
            key="match" if np.sign(direction[old].sum())==np.sign(direction[new].sum()) else "reverse"
            counts[key]+=int(new.sum())
            trial_counts[key]+=1
    return {"status":"Exploratory follow-up after primary scores",
            "train_heading_ties":train_zero,"test_heading_ties":test_zero,
            "later_repeat_trials_by_heading":trial_counts,"later_repeat_cutoffs_by_heading":counts,
            "all_anchor_phase":describe(errors["phase"],test),
            "later_repeat_personal":describe(errors["personal"],test),
            "transformer_minus_phase":comparison(ref,errors["phase"],test),
            "transformer_minus_personal":comparison(ref,errors["personal"],test)}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("train","assessment","model_dir","out"):
        parser.add_argument(name,type=Path)
    a=parser.parse_args()
    seal=json.loads((a.model_dir/"fit-seal.json").read_bytes())
    if sha(a.train)!=seal["train_data_sha256"] or sha(a.model_dir/"weights.npz")!=seal["weights_sha256"]:
        raise ValueError("Training set or fitted weights changed.")
    with np.load(a.train,allow_pickle=False) as tr, np.load(a.assessment,allow_pickle=False) as te:
        result=compare(dict(tr),dict(te),load_weights(a.model_dir/"weights.npz"))
    a.out.write_text(json.dumps(finite_json(result),indent=2,allow_nan=False)+"\n")
    print({k:v["mean_mm"] for k,v in result.items() if isinstance(v,dict) and "mean_mm" in v})
