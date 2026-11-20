"""Fit linear benchmarks and walking-to-standing transfer, then score sealed models."""
import argparse
import json
from pathlib import Path
import numpy as np
from forecast import BASELINES,FITS,observations,design,predict

METHODS=(*BASELINES,*FITS)
WRONG=("wrong_muscle","wrong_muscle_keep_baseline")


def dump(p,j):p.write_text(json.dumps(j,indent=2,allow_nan=False)+"\n")
def take(d,mask):return {k:v[mask] for k,v in d.items()}


def counts(d):
    return {"people":len(np.unique(d["person"])),"sessions":len(set(zip(d["person"],d["posture"]))),
            "events":len(d["person"])}


def weights(d):
    w=np.zeros(len(d["person"]))
    people=np.unique(d["person"])
    for person in people:
        own=d["person"]==person
        postures=np.unique(d["posture"][own])
        for posture in postures:
            session=own&(d["posture"]==posture)
            directions=np.unique(d["direction"][session])
            for direction in directions:
                rows=session&(d["direction"]==direction)
                w[rows]=1/(len(people)*len(postures)*len(directions)*np.count_nonzero(rows))
    return w


def supported(d):
    paired=np.zeros(len(d["person"]),bool)
    valid=np.zeros_like(paired)
    for person in np.unique(d["person"]):
        own=d["person"]==person
        contexts=[p for p in (0,1) if set(d["direction"][own&(d["posture"]==p)])=={-1,1}]
        if len(contexts)==2:paired[own]=True
        valid |= own & np.isin(d["posture"],contexts)
    return paired,valid


def target(d):return np.column_stack((d["future_rms_uv"],d["future_path_mm"].reshape(len(d["person"]),-1)))


def ridge(x,y,w,prior=None):
    mean=w@x;sd=np.sqrt(w@((x-mean)**2));sd=np.where(sd<1e-8,1.,sd)
    z=(x-mean)/sd;center=w@y
    gram=z.T@(w[:,None]*z)+.1*np.eye(z.shape[1])
    rhs=z.T@(w[:,None]*(y-center))
    if prior is not None:
        # Transfer slopes in native feature units. This fit recalibrates the intercept.
        rhs+=.1*(np.asarray(prior["coef"])/np.asarray(prior["sd"])[:,None])*sd[:,None]
    coef=np.linalg.solve(gram,rhs)
    return dict(mean=mean.tolist(),sd=sd.tolist(),bias=center.tolist(),coef=coef.tolist())


def fit(d):
    v=observations(d);y=target(d);state={"format":1,"fits":{},"mean_target":{},"training":{}}
    for posture in (0,1):
        for direction in (-1,1):
            rows=(d["posture"]==posture)&(d["direction"]==direction)
            state["mean_target"][f"{posture}/{direction}"]=(weights(take(d,rows))@y[rows]).tolist()
    for method in FITS:
        keep=np.ones(len(y),bool)
        if method=="walk_only":keep=d["posture"]==1
        if method in ("stand_only","stand_limited","adapted_walk"):keep=d["posture"]==0
        if method in ("stand_limited","adapted_walk"):keep &= d["block"]==0
        subset=take(d,keep);prior=state["fits"]["walk_only"] if method=="adapted_walk" else None
        state["training"][method]=counts(subset)
        state["fits"][method]=ridge(design(method,d,v)[keep],(y-v["recent"])[keep],weights(subset),prior)
    return state


def donors(d):
    groups={}
    for i,key in enumerate(zip(d["person"],d["posture"],d["direction"],d["block"])):
        groups.setdefault(key,[]).append(i)
    out=np.full(len(d["person"]),-1,int)
    for rows in groups.values():
        if len(rows)<2:continue
        ordered=np.array(sorted(rows,key=lambda i:(d["cutoff"][i],d["event"][i])))
        partner=np.roll(ordered,-1);ok=abs(d["cutoff"][ordered]-d["cutoff"][partner])>207
        out[ordered[ok]]=partner[ok]
    return out


def estimates(d,state):
    v=observations(d)
    values={};clips={}
    for m in METHODS:values[m],clips[m]=predict(m,d,v,state)
    donor=donors(d);other=observations(d,donor=np.maximum(donor,0))
    for m in WRONG:
        out,clip=predict("pooled",d,other,state,keep_rms=v["rms"] if m==WRONG[1] else None)
        out[donor<0]=np.nan;clip[donor<0]=0
        values[m]=out;clips[m]=clip
    return values,clips


def comparison(first,second):
    delta=first-second
    idx=np.random.default_rng(1419).integers(0,len(delta),size=(5000,len(delta)))
    means=delta[idx].mean(axis=1)
    bound=np.quantile(means,.975,axis=0)
    return {"mean_difference":delta.mean(axis=0).tolist(),"ci95":np.quantile(means,[.025,.975],axis=0).T.tolist(),
            "upper_97_5":bound.tolist(),"people_better":(delta<0).sum(axis=0).tolist(),
            "both_primary_upper_negative":bool(np.all(bound[:2]<0))}


def scope(d,values,clips,mask,names):
    if not mask.any():return {"people":0,"sessions":0,"events":0,"methods":{}},{}
    small=take(d,mask);true=target(small);w=weights(small);people=np.unique(small["person"]);by={}
    report={**counts(small),"methods":{}}
    for m in names:
        diff=values[m][mask]-true
        if not np.isfinite(diff).all():raise ValueError(f"Unsupported rows passed to score {m}")
        emg=abs(diff[:,:8]);paths=diff[:,8:].reshape(-1,32,3)
        dist=np.linalg.norm(paths,axis=2)
        scalars=np.column_stack((emg.mean(axis=1),dist.mean(axis=1),dist[:,-1]))
        per=np.stack([np.average(scalars[small["person"]==p],axis=0,weights=w[small["person"]==p]) for p in people])
        by[m]=per;avg=per.mean(axis=0)
        report["methods"][m]={"emg_mae_uv":float(avg[0]),"path_error_mm":float(avg[1]),"endpoint_error_mm":float(avg[2]),
            "per_muscle_mae_uv":(w@emg).tolist(),"per_muscle_bias_uv":(w@diff[:,:8]).tolist(),
            "endpoint_bias_mm":(w@paths[:,-1]).tolist(),"negative_rms_values_before_bound":int(clips[m][mask].sum())}
    return report,by


def score(d,values,clips):
    pair,valid=supported(d)
    report={"measure_order":["eight-muscle RMS MAE (µV)","mean 3D path error (mm)","3D endpoint error (mm)"],
            "primary":scope(d,values,clips,pair,METHODS)[0],"postures":{},"unpaired":{},"wrong_history":{}}
    for p,label in ((0,"standing"),(1,"walking")):
        keep=pair&(d["posture"]==p)
        group,by=scope(d,values,clips,keep,METHODS)
        group["directions"]={str(c):scope(d,values,clips,keep&(d["direction"]==c),METHODS)[0] for c in (-1,1)}
        if p==0 and by:
            group["adapted_minus_comparator"]={m:comparison(by["adapted_walk"],by[m]) for m in ("stand_limited","stand_only","walk_only")}
        report["postures"][label]=group
        report["unpaired"][label]=scope(d,values,clips,valid & ~pair & (d["posture"]==p),METHODS)[0]
    present=pair & np.isfinite(values[WRONG[0]][:,0])
    if present.any():
        good,_=supported(take(d,present));present[np.flatnonzero(present)[~good]]=False
    group,by=scope(d,values,clips,present,("pooled",*WRONG))
    if by:group["correct_minus_wrong"]={m:comparison(by["pooled"],by[m]) for m in WRONG}
    report["wrong_history"]=group
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("fit","assess"))
    for k in ("source","model","out"):parser.add_argument(k,type=Path)
    parser.add_argument("--private",type=Path)
    args=parser.parse_args()
    with np.load(args.source,allow_pickle=False) as f:
        d={k:(f[k].astype(float) if k in ("sacrum_mm","leg_uv","future_rms_uv","future_path_mm") else f[k])
           for k in ("person","posture","direction","cutoff","event","block","sacrum_mm","leg_uv","future_rms_uv","future_path_mm")}
    if args.private:args.private.mkdir(parents=True,exist_ok=True)
    pair,valid=supported(d)
    if args.stage=="fit":
        paired=take(d,pair);people=sorted(set(paired["person"]));nfold=min(5,len(people))
        if nfold<2:raise ValueError("Need at least two paired development people.")
        values={};clips={}
        def insert(rows,fitstate):
            scored,neg=estimates(take(d,rows),fitstate)
            for name,pred in scored.items():
                values.setdefault(name,np.full((len(pair),104),np.nan))[rows]=pred
                clips.setdefault(name,np.zeros(len(pair),int))[rows]=neg[name]
        for fold in range(nfold):
            test=np.isin(d["person"],people[fold::nfold])
            state=fit(take(d,pair & ~test));insert(test,state)
            if args.private:dump(args.private/f"fold-{fold}.json",state)
        state=fit(paired);dump(args.model,state)
        if np.any(valid&~pair):insert(valid&~pair,state)
    else:values,clips=estimates(d,json.loads(args.model.read_bytes()))
    dump(args.out,score(d,values,clips))
    if args.private:
        ids={k:d[k] for k in ("person","posture","event","cutoff","direction")}
        np.savez_compressed(args.private/(args.out.stem+"-rows.npz"),**ids,**values)
if __name__=="__main__":main()
