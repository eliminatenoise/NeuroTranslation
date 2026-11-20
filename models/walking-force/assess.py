"""Read the locked alternatives on the ten prespecified assessment people."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from predict import MODES, normalize, ridge, transformer


def wholed(values,person,rep,ok):
    """Mean of per-person means of per-repeat means for light and heavy trials alike."""
    people={}
    for p in np.unique(person[ok]):
        m=ok & (person==p)
        groups=np.unique(rep[m])
        people[int(p)]=np.mean([values[m & (rep==r)].mean() for r in groups])
    return people


def metrics(pred,y,person,rep,mask):
    ok=mask & np.isfinite(pred) & np.isfinite(y)
    if not ok.any():
        return {"people":0,"trials":0,"anchors":0}
    err=(pred-y).astype("f8")
    dd={"people":len(np.unique(person[ok])),"trials":len(set(zip(person[ok],rep[ok]))),"anchors":int(ok.sum())}
    for key,values in (("MAE_N",np.abs(err)),("RMSE_N",err**2),("bias_N",err)):
        ps=wholed(values,person,rep,ok)
        value=np.mean(list(ps.values()))
        dd[key]=float(np.sqrt(value) if key=="RMSE_N" else value)
    return dd


def paired(pred,baseline,y,person,rep):
    ok=np.isfinite(pred)&np.isfinite(baseline)
    ps=wholed(np.abs(pred-y).astype("f8"),person,rep,ok)
    bs=wholed(np.abs(baseline-y).astype("f8"),person,rep,ok)
    if not ps:
        return {"people":0,"pass":False}
    a=np.array(list(ps.values()))
    b=np.array(list(bs.values()))
    delta=a-b
    rng=np.random.default_rng(7695)
    boots=delta[rng.integers(0,len(a),(10000,len(a)))].mean(axis=1)
    interval=np.percentile(boots,[2.5,97.5])
    relative=1-a.mean()/b.mean() if b.mean()>0 else None
    return {"people":len(a),"trials":len(set(zip(person[ok],rep[ok]))),"anchors":int(ok.sum()),
            "combined_MAE_N":float(a.mean()),"comparator_MAE_N":float(b.mean()),"difference_N":float(delta.mean()),
            "paired_95pct_bootstrap_N":interval.tolist(),"relative_reduction":float(relative) if relative is not None else None,
            "people_better":int((delta<0).sum()),"pass":bool(len(a)>=8 and relative is not None and relative>=.05 and interval[1]<0)}


def scramble(x,person,rep,anchor,weights):
    z=normalize(x,weights)
    valid=x[:,-1,18:24].repeat(3,axis=1)==1
    copied=x.copy()
    best=np.full(len(x),-1)
    dist=np.full(len(x),np.nan)
    for p in np.unique(person):
        repeats=np.unique(rep[person==p])
        if len(repeats)<2:
            continue
        for ix,r in enumerate(repeats):
            src=np.flatnonzero((person==p)&(rep==repeats[(ix+1)%len(repeats)]))
            for i in np.flatnonzero((person==p)&(rep==r)):
                candidates=src[anchor[src]<=anchor[i]]
                both=valid[candidates]&valid[i]
                keep=both.any(axis=1)
                if not keep.any():
                    continue
                c=candidates[keep]
                mask=both[keep]
                delta=z[c,-1,:18]-z[i,-1,:18]
                mean=((delta*delta)*mask).sum(axis=1)/mask.sum(axis=1)
                j=mean.argmin()
                best[i]=c[j]
                dist[i]=mean[j]
    admit=best>=0
    copied[admit,:,24:40]=x[best[admit],:,24:40]
    return copied,admit,dist


def read_weights(root,name,seal):
    path=root/name
    if hashlib.sha256(path.read_bytes()).hexdigest()!=seal["weight_sha256"][name]:
        raise ValueError("sealed fit changed: "+name)
    with np.load(path,allow_pickle=False) as w:
        return {k:w[k] for k in w.files}


def run_assessment(test,weights,private_fit):
    seal=json.loads((private_fit/"fit-seal.json").read_bytes())
    for n,h in seal["frozen_files_sha256"].items():
        if hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()!=h:
            raise ValueError("assessment requires frozen implementation: "+n)
    p,r,x,y,anc=(test[k] for k in ("person","repeat","x","y","anchor"))
    if not (p.min()>=31 and p.max()<=40):
        raise ValueError("wrong assessment partition")
    preds={"constant-zero":np.zeros(len(y)),"training-mean":np.full(len(y),seal["training_mean_N"]),
           "current-plate-persistence":np.maximum(0,test["previous"])}
    for mode in MODES:
        for family,predictor in (("transformer",transformer),("ridge",ridge)):
            name=f"{family}-{mode}"
            w=read_weights(weights,name+".npz",seal)
            preds[name]=predictor(x,w,mode)
    kernel=read_weights(private_fit,"marker-kernel.npz",seal)
    preds["marker-kernel"]=ridge(x,kernel,"markers",nonlinear=True)
    ww=read_weights(weights,"transformer-combined.npz",seal)
    sw,ok,dist=scramble(x,p,r,anc,ww)
    wrong=np.full(len(y),np.nan)
    if ok.any():
        wrong[ok]=transformer(sw[ok],ww,"combined")
    preds["wrong-repeat-emg"]=wrong
    all_rows=np.ones(len(y),bool)
    comparisons={k:paired(preds["transformer-combined"],preds[k],y,p,r)
                 for k in ("transformer-markers","marker-kernel","wrong-repeat-emg")}
    return {"held_people":len(np.unique(p)),"held_trials":len(set(zip(p,r))),"held_anchors":len(y),
            "metrics":{k:metrics(v,y,p,r,all_rows) for k,v in preds.items()},
            "target_strata":{key:{k:metrics(v,y,p,r,mask) for k,v in preds.items()}
                              for key,mask in (("source-coded-zero",y==0),("nonzero",y!=0))},
            "incremental_EMG_comparisons":comparisons,"incremental_EMG_gate_passed":all(d["pass"] for d in comparisons.values()),
            "wrong_repeat_median_squared_pose_distance_z":float(np.nanmedian(dist)) if ok.any() else None,
            "uncertainty":"10,000 bootstrap draws of paired whole people, equal people with equal trials within each person; all prespecified intervals shown."}


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("assessment",type=Path)
    a.add_argument("weights",type=Path)
    a.add_argument("private_fit",type=Path)
    a.add_argument("out",type=Path)
    opt=a.parse_args()
    with np.load(opt.assessment,allow_pickle=False) as dat:
        result=run_assessment(dat,opt.weights,opt.private_fit)
    opt.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(result["held_people"],result["held_trials"],result["held_anchors"],result["incremental_EMG_gate_passed"])

if __name__=="__main__":
    main()
