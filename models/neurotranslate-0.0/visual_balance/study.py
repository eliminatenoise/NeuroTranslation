"""Rebuild the fitted output layers, controls and participant-weighted evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from predict import DEFAULT_CHECKPOINT,read_checkpoint
from forecast import (BASELINES,LEARNED,movement,observations,standardized,nuisance_predictors,
                      materialize,design,predict)
PARENT="6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864"
SEEDS=(None,258,1173)
PRIMARY="shared_full"


def put(p,x):
    p.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")


def take(d,mask):
    return {k:v[mask] for k,v in d.items()}


def weights(people):
    _,inverse,count=np.unique(people,return_inverse=True,return_counts=True)
    return 1./(len(count)*count[inverse])


def scale(x,w):
    m=w@x
    sd=np.sqrt(w@((x-m)**2))
    return m,np.where(sd<1e-8,1,sd)


def obs_stats(values,good,w):
    obs=w[:,None]*good
    total=obs.sum(axis=0)
    mean=np.divide(np.sum(obs*values.mean(axis=1),axis=0),total,out=np.zeros_like(total),where=total>0)
    variance=np.divide(np.sum(obs*((values-mean)**2).mean(axis=1),axis=0),total,out=np.zeros_like(total),where=total>0)
    sd=np.sqrt(variance)
    return {"mean":mean.tolist(),"sd":np.where(sd<1e-8,1.,sd).tolist()}


def ridge(x,y,w):
    mean,sd=scale(x,w)
    z=(x-mean)/sd
    bias=w@y
    gram=z.T@(w[:,None]*z)+.1*np.eye(z.shape[1])
    coef=np.linalg.solve(gram,z.T@(w[:,None]*(y-bias)))
    return {"mean":mean.tolist(),"sd":sd.tolist(),"bias":bias.tolist(),"coef":coef.tolist()}


def nuisance_fit(x, eeg, observed, w):
    # Separate only where spatial group masks actually differ.
    coefs=np.zeros((x.shape[2],eeg.shape[2]))
    intercepts=np.zeros(eeg.shape[2])
    masks={}
    for group in range(observed.shape[1]):
        masks.setdefault(observed[:,group].tobytes(),[]).append(group)
    for group in masks.values():
        keep=observed[:,group[0]]
        if not keep.any():continue
        a=x[keep].reshape(-1,x.shape[2])
        b=eeg[keep][:,:,group].reshape(-1,len(group))
        wt=np.repeat(w[keep]/w[keep].sum()/8,8)
        f=ridge(a,b,wt)
        coef=np.asarray(f["coef"])/np.asarray(f["sd"])[:,None]
        coefs[:,group]=coef
        intercepts[group]=np.asarray(f["bias"])-np.asarray(f["mean"])@coef
    return {"coef":coefs.tolist(),"bias":intercepts.tolist()}


def fit(d,encoders):
    w=weights(d["person"])
    y=d["future_delta_mm"].reshape(-1,6)
    scalp,sg,frac,nuisance,ng,mask=observations(d)
    es=obs_stats(scalp,sg,w);ns=obs_stats(nuisance,ng,w)
    recent,_,tokens=movement(d["motion_mm"])
    tm,ts=scale(tokens.reshape(-1,6),np.repeat(w/4,4))
    mean={}
    for direction in (-1,1):
        rows=d["direction"]==direction
        mean[str(direction)]=(weights(d["person"][rows])@y[rows]).tolist()
    state={"version":1,"parent_sha256":PARENT,"scalp_stats":es,"nuisance_stats":ns,
           "token_mean":tm.tolist(),"token_sd":ts.tolist(),"cue_mean":mean,"fits":{}}
    v=materialize(d,state)
    state["nuisance_regression"]=nuisance_fit(nuisance_predictors(v["nuisance"],mask),v["scalp"],sg,w)
    for mode in LEARNED:
        x=design(mode,v,state,encoders)
        target=y if mode in ("scalp_only","masks_only") else y-recent
        state["fits"][mode]=ridge(x,target,w)
    return state


def donor_maps(d):
    strata={}
    for i,key in enumerate(zip(d["person"],d["direction"],d["block"])):
        strata.setdefault(key,[]).append(i)
    maps={}
    for seed in SEEDS:
        rng=np.random.default_rng(seed) if seed is not None else None
        out=np.full(len(d["person"]),-1,int)
        for key,idx in sorted(strata.items()):
            if len(idx)<2:continue
            order=np.array(sorted(idx,key=lambda i:(d["cutoff"][i],d["event"][i])))
            if rng is not None:order=rng.permutation(order)
            partners=np.roll(order,-1)
            use=np.abs(d["cutoff"][order]-d["cutoff"][partners])>207
            out[order[use]]=partners[use]
        maps["cycle" if seed is None else str(seed)]=out
    return maps


def predictions(d,state,encoders,donors):
    v=materialize(d,state)
    out={m:predict(m,v,d,state,encoders) for m in (*BASELINES,*LEARNED)}
    for key,indices in donors.items():
        keep=indices>=0
        paired=materialize(d,state,donor=np.maximum(indices,0))
        for m in ("shared_full","shared_residual","linear_full"):
            values=predict(m,paired,d,state,encoders)
            values[~keep]=np.nan
            out[m+"_wrong_"+key]=values
    return out


def group_stats(d,pred,mask,methods):
    if not mask.any():
        return {"people":0,"events":0,"methods":{}},{}
    people=d["person"][mask];true=d["future_delta_mm"][mask]
    w=weights(people);roster=np.unique(people);by={}
    samples=np.random.default_rng(2701).integers(0,len(roster),(5000,len(roster)))
    result={"people":len(roster),"events":int(mask.sum()),"methods":{}}
    for m in methods:
        diff=pred[m][mask]-true
        loss=np.linalg.norm(diff,axis=2)
        per=np.stack([loss[people==p].mean(axis=0) for p in roster])
        by[m]=per
        result["methods"][m]={"endpoint_mm":per.mean(axis=0).tolist(),
            "ci95_mm":np.quantile(per[samples].mean(axis=1),[.025,.975],axis=0).T.tolist(),
            "bias_ml_si_ap_mm":np.einsum("n,nma->ma",w,diff).tolist()}
    return result,by


def difference(per):
    idx=np.random.default_rng(2701).integers(0,len(per),(5000,len(per)))
    sample=per[idx].mean(axis=1)
    return {"mean_mm":per.mean(axis=0).tolist(),"ci95_mm":np.quantile(sample,[.025,.975],axis=0).T.tolist(),
            "adjusted_upper_98_75_mm":np.quantile(sample,.9875,axis=0).tolist(),
            "people_improved":(per<0).sum(axis=0).tolist()}


def contrast(by,full,no,wrong):
    if not by:return {"people":0,"passes_sacrum_head":[None,None],"all_four_pass":None}
    control=difference(by[full]-by[no]);falsification=difference(by[full]-by[wrong])
    passed=(np.array(control["adjusted_upper_98_75_mm"])<0)&(np.array(falsification["adjusted_upper_98_75_mm"])<0)
    return {"people":len(by[full]),"correct_minus_no_scalp":control,"correct_minus_wrong":falsification,
            "passes_sacrum_head":passed.tolist(),"all_four_pass":bool(passed.all())}


def report(d,pred):
    main=(*BASELINES,*LEARNED)
    all_rows=np.ones(len(d["person"]),bool)
    result,by=group_stats(d,pred,all_rows,main)
    out={"all":result,"conditions":{},"donors":{},"all_correct_minus_nuisance":difference(by[PRIMARY]-by["shared_nuisance"])}
    for cue in (-1,1):
        out["conditions"][str(cue)]=group_stats(d,pred,d["direction"]==cue,main)[0]
    for key in ("cycle","258","1173"):
        extras=tuple(m+"_wrong_"+key for m in (PRIMARY,"shared_residual","linear_full"))
        mask=np.isfinite(pred[extras[0]][:,0,0])
        both=[p for p in np.unique(d["person"][mask]) if set(d["direction"][mask & (d["person"]==p)])=={-1,1}]
        mask &= np.isin(d["person"],both)
        view,matched=group_stats(d,pred,mask,(*main,*extras))
        view["scalp_tests"]={m:contrast(matched,m,no,m+"_wrong_"+key) for m,no in [
            (PRIMARY,"shared_nuisance"),("shared_residual","shared_nuisance"),("linear_full","linear_nuisance")]}
        out["donors"][key]=view
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=["fit","score"])
    for k in ("source","model","summary"):parser.add_argument(k,type=Path)
    parser.add_argument("--private",type=Path)
    args=parser.parse_args()
    if hashlib.sha256(DEFAULT_CHECKPOINT.read_bytes()).hexdigest()!=PARENT:
        raise ValueError("Expected the original movement encoder.")
    encoders=read_checkpoint(DEFAULT_CHECKPOINT)
    with np.load(args.source,allow_pickle=False) as f:
        d={k:np.asarray(f[k],dtype=float) if k.endswith(("_uv","_mm")) else f[k] for k in f.files}
    roster=[p for p in np.unique(d["person"]) if set(d["direction"][d["person"]==p])=={-1,1}]
    if not roster:raise ValueError("No person with rows for both cue directions.")
    d=take(d,np.isin(d["person"],roster));donors=donor_maps(d)
    if args.private:args.private.mkdir(parents=True,exist_ok=True)
    if args.stage=="fit":
        pred={}
        for fold in range(min(5,len(roster))):
            test=np.isin(d["person"],roster[fold::min(5,len(roster))])
            state=fit(take(d,~test),encoders)
            if args.private:put(args.private/f"fold-{fold}.json",state)
            back=np.full(len(test),-1,int);back[test]=np.arange(test.sum())
            local={k:np.where(a[test]<0,-1,back[np.maximum(a[test],0)]) for k,a in donors.items()}
            for mode,arr in predictions(take(d,test),state,encoders,local).items():
                pred.setdefault(mode,np.full(d["future_delta_mm"].shape,np.nan))[test]=arr
        put(args.model,fit(d,encoders))
    else:pred=predictions(d,json.loads(args.model.read_bytes()),encoders,donors)
    put(args.summary,report(d,pred))
    if args.private:
        ids={k:d[k] for k in ("person","event","direction","cutoff")}
        np.savez_compressed(args.private/(args.summary.stem+"-rows.npz"),**ids,**pred)


if __name__=="__main__":main()
