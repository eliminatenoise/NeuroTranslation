"""Reproduce the three-run development study under its fixed protocol."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import cued_arm as arm
import predict
from ofner_source import Run

PROTOCOL = "ed4a6e0f8b6f927683a7445449a6a6213249ea409869a41b58abc85ed3281e02"
PARENT = "eac2b0e49ab68ce6d6a2ff2f09a804f2d41fa3af96d632b7bbbb02f73871bed0"
SENSORS = (93,94,68)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rows(cache):
    inputs, targets, groups = [], [], []
    reasons = Counter()
    for n in (1,2,3):
        with Run(cache,n) as run:
            cues = [(t,code) for t,code in run.events if 0x600 <= code <= 0x606]
            for j,(t,code) in enumerate(cues):
                limit = cues[j+1][0] if j+1 < len(cues) else 512*run.records
                end = [et for et,ec in run.events if t < et <= limit and ec == code+0x8000]
                if len(end)!=1 or end[0] < t+896:
                    reasons["missing_or_short_event"] += 1
                    continue
                cutoff=t+128
                last=cutoff//8
                if last<31 or (cutoff+768)//8>=run.records*64:
                    reasons["record_bounds"] += 1
                    continue
                b=np.column_stack([run.window(i,last-31,last+1) for i in SENSORS]).reshape(4,8,3)
                median=np.median(b,axis=1)
                history=np.column_stack((median,np.median(b[:,4:],axis=1)-np.median(b[:,:4],axis=1)))
                endpoints=[]
                for ticks in (256,512,768):
                    e=(cutoff+ticks)//8
                    endpoints.append([np.median(run.window(i,e-7,e+1)) for i in SENSORS])
                y=np.asarray(endpoints)-median[-1]
                if not np.isfinite(b).all() or not np.isfinite(y).all():
                    reasons["nonfinite_input_or_target"]+=1
                    continue
                inputs.append(history);targets.append(y);groups.append((n,code-0x600))
    return np.stack(inputs),np.stack(targets),np.asarray(groups),dict(reasons)


def balance(groups):
    weights=np.zeros(len(groups))
    runs=np.unique(groups[:,0])
    for r in runs:
        tasks=np.unique(groups[groups[:,0]==r,1])
        for task in tasks:
            mask=(groups[:,0]==r)&(groups[:,1]==task)
            weights[mask]=1/(len(runs)*len(tasks)*mask.sum())
    return weights


def scale(x,weights, *, floor=True):
    mean=np.average(x,weights=weights,axis=0)
    sd=np.sqrt(np.average((x-mean)**2,weights=weights,axis=0))
    return mean,np.where(sd<1e-8,1.,sd) if floor else sd


def fit(x,y,groups,cfg,base):
    w=dict(base);ww=balance(groups)
    tokens,_=arm.tokens_and_anchor(x)
    w["cued_arm.token.mean"],w["cued_arm.token.sd"]=scale(tokens.reshape(-1,6),np.repeat(ww/4,4))
    flat=y.reshape(-1,9)
    for mode in arm.MODES[1:]:
        a=arm.design(mode,groups[:,1],x,cfg,w,predict.linear,predict.encode)
        pre="cued_arm."+mode+"."
        mean,sd=scale(a,ww)
        w[pre+"mean"],w[pre+"sd"]=mean,sd
        design=(a-mean)/sd
        bias=np.average(flat,weights=ww,axis=0)
        w[pre+"bias"]=bias
        w[pre+"coef"]=np.linalg.solve(design.T@(ww[:,None]*design)+.2*np.eye(a.shape[1]),
                                      design.T@(ww[:,None]*(flat-bias)))
    return w


def contrasts(folds,control):
    shared=np.array([f["balanced_standardized_mae"]["shared_cue_motion"] for f in folds])
    other=np.array([f["balanced_standardized_mae"][control] for f in folds])
    if np.isclose(other.mean(),0.,rtol=0.,atol=1e-12):
        return {"defined":False,"pass":False}
    relative=float(np.mean(shared-other)/other.mean())
    return {"defined":True,"shared_minus_other":float((shared-other).mean()),"fraction_change":relative,
            "runs_with_lower_error":int((shared<other).sum()),
            "pass":bool(relative<=-.05 and np.all(shared<other))}


def score(x,y,g,cfg,base):
    modes=(*arm.MODES,"wrong_cue")
    folds=[]
    by_task={c:{m:[] for m in modes} for c in arm.CUES}
    for r in (1,2,3):
        train=g[:,0]!=r;test=~train
        w=fit(x[train],y[train],g[train],cfg,base)
        _,sd=scale(y[train],balance(g[train]),floor=False)
        if np.any(sd<1e-8):
            raise ValueError("At least one fitting coordinate is constant: withhold the pooled comparison.")
        ids=g[test,1];freq=balance(g[test])
        losses={}
        for m in arm.MODES:
            prediction=arm.batch(m,ids,x[test],cfg,w,predict.linear,predict.encode)
            losses[m]=np.abs(prediction-y[test])
        swapped=[arm.batch("shared_cue_motion",(ids+k)%7,x[test],cfg,w,predict.linear,predict.encode)
                 for k in range(1,7)]
        losses["wrong_cue"]=np.mean([np.abs(pred-y[test]) for pred in swapped],axis=0)
        f={"run":r,"fitting_trials":int(train.sum()),"test_trials":int(test.sum()),
           "test_trials_by_cue":dict(zip(arm.CUES,np.bincount(ids,minlength=7).tolist())),
           "balanced_standardized_mae":{},"native_mae_by_horizon_and_sensor":{}}
        for m,err in losses.items():
            values=(err/sd).mean(axis=(1,2))
            f["balanced_standardized_mae"][m]=float(freq@values)
            f["native_mae_by_horizon_and_sensor"][m]=np.average(err,weights=freq,axis=0).tolist()
            for j,label in enumerate(arm.CUES):
                if (ids==j).any():
                    by_task[label][m].append(float(values[ids==j].mean()))
        folds.append(f)
    means={m:float(np.mean([f["balanced_standardized_mae"][m] for f in folds])) for m in modes}
    native={m:np.mean([f["native_mae_by_horizon_and_sensor"][m] for f in folds],axis=0).tolist() for m in modes}
    paired={c:contrasts(folds,c) for c in ("shared_motion","wrong_cue","cue_motion","shuffled_cue_motion")}
    return {"held_runs":folds,"balanced_standardized_mae":means,"native_mae_by_horizon_and_sensor":native,
            "task_balanced_standardized_mae":{c:{m:float(np.mean(v)) if v else None for m,v in by_task[c].items()} for c in arm.CUES},
            "contrasts":paired,"consistent_cue_advantage":all(paired[c]["pass"] for c in ("shared_motion","wrong_cue")),
            "pretrained_encoder_advantage":all(paired[c]["pass"] for c in ("cue_motion","shuffled_cue_motion"))}


def study(cache,parent,package,report):
    if sha(parent)!=PARENT or sha(HERE/"PROTOCOL.md")!=PROTOCOL:
        raise ValueError("Use the exact original parent and fixed protocol.")
    if len({p.resolve() for p in (parent,package,report)})!=3:
        raise ValueError("Use distinct parent, checkpoint and score paths.")
    x,y,g,excluded=rows(cache)
    cfg,base=predict.read_checkpoint(parent)
    result=score(x,y,g,cfg,base)
    fitted=fit(x,y,g,cfg,base)
    cfg["cued_arm"]={"format":1,"source":"10.5281/zenodo.834976","protocol":PROTOCOL,"modes":list(arm.MODES),
                     "cues":list(arm.CUES),"sensors":list(arm.CHANNELS),"horizon_after_cutoff_s":list(arm.DELAYS),
                     "fit_people":1,"fit_runs":3,"fit_trials":len(g)}
    with np.load(parent,allow_pickle=False) as z:
        arrays={k:z[k] for k in z.files}
    arrays.update({k:v for k,v in fitted.items() if k.startswith("cued_arm.")})
    arrays["configuration"]=np.array(json.dumps(cfg))
    np.savez_compressed(package,**arrays)
    result.update({"checkpoint_sha256":sha(package),"parent_checkpoint_sha256":PARENT,"method_sha256":PROTOCOL,
                   "eligible_trials":len(g),"excluded":excluded,"people":1,"horizon_after_cutoff_s":list(arm.DELAYS),
                   "channels":list(arm.CHANNELS),"cues":list(arm.CUES)})
    report.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ("eligible_trials","excluded","balanced_standardized_mae","consistent_cue_advantage","pretrained_encoder_advantage","checkpoint_sha256")},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("cache","parent","checkpoint","report"):parser.add_argument(key,type=Path)
    a=parser.parse_args()
    study(a.cache,a.parent,a.checkpoint,a.report)
