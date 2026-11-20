"""Fit a cross-person arm forecast, then assess sealed weights on the reserved test people."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import cued_arm as arm
import group_arm as group
import predict
from ofner_transfer import Run

PARENT="ab3db00e8c048953bdc12d8c978e3cabdf1f2fae7dcfe2f6f53fe8aed724ddfd"
PROTOCOL="450e97e75a7560eacf1daaf3c970ecc997ca5db66d3296a374600128317ccdd1"
OFFSET_PROTOCOL="34bf6a1e27ac77bd645b8f3770aec23595b6dfdc6e0b845f07a20af44a23aac8"
FITTING=tuple(range(1,8))
ASSESSMENT=tuple(range(8,13))
SENSORS=(93,94,68)
ROUTE="shared_cue_motion"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,data):
    Path(p).write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")


def rows(cache,people):
    histories,targets,labels=[],[],[]
    excluded=Counter()
    sensor_runs=np.zeros(3,dtype=int)
    sensor_trials=np.zeros(3,dtype=int)
    candidates=0
    for person in people:
        for number in (1,2,3):
            with Run(cache,person,number) as run:
                raw=np.column_stack([run.window(ch,0,run.records*64) for ch in SENSORS])
                varied=[]
                for v in raw.T:
                    good=v[np.isfinite(v)]
                    varied.append(bool(len(good) and good.min()<good.max()))
                varied=np.asarray(varied)
                sensor_runs+=varied
                cues=[(t,c) for t,c in run.events if 0x600<=c<=0x606]
                candidates+=len(cues)
                for j,(t,c) in enumerate(cues):
                    cutoff=t+128
                    boundary=cues[j+1][0] if j+1<len(cues) else run.records*512
                    ends=[et for et,ec in run.events if t<et<=boundary and ec==c+0x8000]
                    if len(ends)!=1 or ends[0]<t+896:
                        excluded["missing_or_short_event"]+=1
                        continue
                    last=cutoff//8;tail=(cutoff+np.array([256,512,768]))//8
                    if last<31 or tail[-1]>=len(raw):
                        excluded["record_bounds"]+=1
                        continue
                    b=raw[last-31:last+1].reshape(4,8,3)
                    future=raw[tail[:,None]+np.arange(-7,1)]
                    observed=varied & np.isfinite(b).all(axis=(0,1)) & np.isfinite(future).all(axis=(0,1))
                    sensor_trials+=observed
                    if not observed.all():
                        excluded["constant_or_unavailable_run_channel" if not varied.all() else "missing_required_samples"]+=1
                        continue
                    levels=np.median(b,axis=1)
                    histories.append(np.column_stack((levels,np.median(b[:,4:],axis=1)-np.median(b[:,:4],axis=1))))
                    targets.append(np.median(future,axis=1)-levels[-1])
                    labels.append((person,number,c-0x600))
    g=np.asarray(labels,dtype=int).reshape(-1,3)
    coverage={"candidate_people":len(people),"candidate_runs":len(people)*3,"marked_cues":candidates,
              "eligible_people":len(np.unique(g[:,0])),"eligible_runs":len(np.unique(g[:,:2],axis=0)),
              "eligible_trials":len(g),"excluded_trials":dict(excluded),"observed_runs_by_sensor":sensor_runs.tolist(),
              "observed_trials_by_sensor":sensor_trials.tolist()}
    return np.asarray(histories).reshape(-1,4,6),np.asarray(targets).reshape(-1,3,3),g,coverage


def balance(g):
    """Assign equal weight to people, runs, tasks and finally trials in each task."""
    if not len(g):
        raise ValueError("No eligible trials on common support.")
    prc,row,counts=np.unique(g,axis=0,return_inverse=True,return_counts=True)
    pr=np.unique(prc[:,:2],axis=0)
    people=np.unique(pr[:,0])
    weights=[]
    for (person,run,_),n in zip(prc,counts):
        nruns=(pr[:,0]==person).sum()
        ntasks=((prc[:,0]==person)&(prc[:,1]==run)).sum()
        weights.append(1/(len(people)*nruns*ntasks*n))
    return np.asarray(weights)[row]


def stats(x,ww,*,floor=True):
    mean=np.average(x,axis=0,weights=ww)
    sd=np.sqrt(np.average((x-mean)**2,axis=0,weights=ww))
    return mean,np.where(sd<1e-8,1.,sd) if floor else sd


def cue_medians(y,g):
    table=[]
    for task in range(7):
        mask=g[:,2]==task
        if not mask.any():
            raise ValueError("Missing a fitting task for the cue median.")
        by_person=[]
        for person in np.unique(g[mask,0]):
            own=mask&(g[:,0]==person)
            by_person.append(np.median([np.median(y[own&(g[:,1]==r)],axis=0) for r in np.unique(g[own,1])],axis=0))
        table.append(np.median(by_person,axis=0))
    return np.stack(table)


def fit(cache,parent,checkpoint,receipt):
    if sha(parent)!=PARENT:raise ValueError("Different parent checkpoint.")
    x,y,g,coverage=rows(cache,FITTING)
    ww=balance(g);cfg,w=predict.read_checkpoint(parent)
    tokens,_=arm.tokens_and_anchor(x)
    w["cued_arm.token.mean"],w["cued_arm.token.sd"]=stats(tokens.reshape(-1,6),np.repeat(ww/4,4))
    flat=y.reshape(-1,9)
    for mode in (*arm.MODES[1:],*group.OFFSET):
        a=arm.design(group.OFFSET.get(mode,mode),g[:,2],x,cfg,w,predict.linear,predict.encode)
        if mode in group.OFFSET:
            # The covariates are cue indicators, four flattened tokens, three cutoff levels, then optional encoder.
            first_level=len(arm.CUES)+x.shape[1]*x.shape[2]
            a[:,first_level:first_level+3]=0.
        stem="cued_arm."+mode+"."
        mu,sd=stats(a,ww);z=(a-mu)/sd
        bias=np.average(flat,axis=0,weights=ww)
        w[stem+"mean"],w[stem+"sd"],w[stem+"bias"]=mu,sd,bias
        w[stem+"coef"]=np.linalg.solve(z.T@(ww[:,None]*z)+.2*np.eye(z.shape[1]),z.T@(ww[:,None]*(flat-bias)))
    with np.load(parent,allow_pickle=False) as parent_data:
        arrays={k:parent_data[k] for k in parent_data.files}
    for k,v in w.items():
        if k.startswith("cued_arm."):
            arrays["group_arm."+k[len("cued_arm."):]]=v
    arrays["group_arm.cue_median"]=cue_medians(y,g)
    _,target_sd=stats(y,ww,floor=False)
    arrays["group_arm.target_sd"]=target_sd
    signature=hashlib.sha256((PARENT+PROTOCOL).encode())
    for key in sorted(k for k in arrays if k.startswith("group_arm.")):
        value=np.ascontiguousarray(arrays[key],dtype="<f8")
        signature.update(key.encode()+b"\0"+str(value.shape).encode()+b"\0"+value.tobytes())
    cfg["group_arm"]={"format":1,"calibration_id":signature.hexdigest(),"study":PROTOCOL,"offset_study":OFFSET_PROTOCOL,"parent":PARENT,"training_people":coverage["eligible_people"],
                      "training_trials":len(g),"modes":list(group.MODES),"source":"10.5281/zenodo.834976"}
    arrays["configuration"]=np.array(json.dumps(cfg))
    np.savez_compressed(checkpoint,**arrays)
    save(receipt,{"checkpoint_sha256":sha(checkpoint),"parent_sha256":PARENT,"protocol_sha256":PROTOCOL,
                  "coverage":coverage,"target_sd_native":target_sd.tolist(),"assessment_opened_by_fit":False})


def coverage(g):
    return {"people":len(np.unique(g[:,0])),"runs":len(np.unique(g[:,:2],axis=0)),"trials":len(g)}


def summarize(errors,g,sd):
    if not len(g):return {"coverage":coverage(g),"models":{}}
    weights=balance(g);status=bool(np.all(sd>=1e-8))
    out={"coverage":coverage(g),"models":{},"standardized_targets_available":status}
    for name,err in errors.items():
        rec={"native_mae":np.average(err,weights=weights,axis=0).tolist()}
        if status:
            loss=(err/sd).mean(axis=(1,2))
            person=[]
            for pid in np.unique(g[:,0]):
                keep=g[:,0]==pid;person.append(float(balance(g[keep])@loss[keep]))
            rec["standardized_mae"]=float(weights@loss)
            rec["person_scores"]=person  # removed from the public summary after paired comparisons
            rec["per_cue"]={}
            for i,c in enumerate(arm.CUES):
                keep=g[:,2]==i
                rec["per_cue"][c]=float(balance(g[keep])@loss[keep]) if keep.any() else None
        out["models"][name]=rec
    return out


def compare(report,method,comparator):
    if not report.get("standardized_targets_available") or report["coverage"]["people"]<4:
        return {"sufficient_support":False,"pass":False}
    a=np.asarray(report["models"][method]["person_scores"])
    b=np.asarray(report["models"][comparator]["person_scores"])
    diff=a-b;n=len(a)
    draws=np.random.default_rng(88402).integers(n,size=(10000,n))
    ci=np.quantile(diff[draws].mean(axis=1),[.025,.975])
    relative=float(diff.mean()/b.mean()) if b.mean()>0 else None
    return {"sufficient_support":True,"paired_mean_difference":float(diff.mean()),"interval95":ci.tolist(),
            "sorted_person_differences":np.sort(diff).tolist(),"fraction_change":relative,"people_improved":int((diff<0).sum()),"people":n,
            "pass":bool(relative is not None and relative<=-.05 and ci[1]<0 and (diff<0).sum()>n/2)}


def assessment(cache,checkpoint,receipt,outfile):
    seal=json.loads(receipt.read_bytes())
    if sha(checkpoint)!=seal["checkpoint_sha256"] or seal["protocol_sha256"]!=PROTOCOL or seal["parent_sha256"]!=PARENT:
        raise ValueError("Fit seal does not match the checkpoint, protocol and parent.")
    cfg,w=predict.read_checkpoint(checkpoint)
    if cfg.get("group_arm",{}).get("study")!=PROTOCOL:
        raise ValueError("Unrecognized group fit.")
    x,y,g,qa=rows(cache,ASSESSMENT)
    if not len(g):
        save(outfile,{"coverage":qa,"claim":"No eligible assessment rows."});return
    ids=g[:,2];sd=w["group_arm.target_sd"]
    def pooled(m,labels=ids):
        return group.batch(m,labels,x,cfg,w,predict.linear,predict.encode)
    predictions={m:pooled(m) for m in group.MODES if m!="calibrated_shared"}
    for m in ("cue",ROUTE):
        predictions["s1_"+m]=arm.batch(m,ids,x,cfg,w,predict.linear,predict.encode)
    errors={m:np.abs(v-y) for m,v in predictions.items()}
    errors["wrong_cue"]=np.mean([np.abs(pooled(ROUTE,(ids+k)%7)-y) for k in range(1,7)],axis=0)
    primary=summarize(errors,g,sd)
    primary["comparisons"]={c:compare(primary,ROUTE,c) for c in ("s1_"+ROUTE,"shared_motion","wrong_cue","cue_motion","shuffled_cue_motion","cue_median")}
    primary["offset_comparisons"]={m:compare(primary,m,control) for m,control in group.OFFSET.items()}
    pairs=primary["comparisons"]
    primary["passes"]={"pooled_vs_s1":pairs["s1_"+ROUTE]["pass"],"cue":all(pairs[c]["pass"] for c in ("shared_motion","wrong_cue")),
                       "encoder":all(pairs[c]["pass"] for c in ("cue_motion","shuffled_cue_motion","cue_median"))}
    chosen=[];corrected=[];personal=[]
    for person in np.unique(g[:,0]):
        first=(g[:,0]==person)&(g[:,1]==1)
        later=np.flatnonzero((g[:,0]==person)&(g[:,1]>1))
        if not first.any() or not len(later):continue
        summary=group.summarize(y[first]-predictions[ROUTE][first],ids[first])
        prev=w["group_arm.cue_median"].copy()
        for i in np.unique(ids[first]):
            prev[i]=np.median(y[first&(ids==i)],axis=0)
        chosen.extend(later)
        corrected.extend([predictions[ROUTE][j]+group.calibration_matrix(summary[arm.CUES[ids[j]]]) for j in later])
        personal.extend(prev[ids[later]])
    chosen=np.array(chosen,dtype=int)
    err={m:e[chosen] for m,e in errors.items() if m in (ROUTE,"cue_median")}
    if len(chosen):
        err.update(calibrated_shared=np.abs(np.asarray(corrected)-y[chosen]),personal_median=np.abs(np.asarray(personal)-y[chosen]))
    calibration=summarize(err,g[chosen],sd)
    calibration["comparisons"]={c:compare(calibration,"calibrated_shared",c) for c in (ROUTE,"cue_median","personal_median")}
    calibration["passes"]=all(r["pass"] for r in calibration["comparisons"].values())
    for report in (primary,calibration):
        for score in report["models"].values():
            scores=score.pop("person_scores",[])
            if scores:score["people_error_quartiles"]=np.quantile(scores,[.25,.5,.75]).tolist()
    save(outfile,{"protocol_sha256":PROTOCOL,"checkpoint_sha256":sha(checkpoint),"training":seal["coverage"],
                  "assessment":qa,"horizons_after_cutoff_s":list(arm.DELAYS),"sensors":list(arm.CHANNELS),
                  "unseen_person":primary,"after_first_run":calibration})


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation",choices=("fit","assess"))
    for arg in ("cache","first","second","output"):parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    if sha(HERE/"PROTOCOL.md")!=PROTOCOL or sha(HERE/"OFFSET-CHECK.md")!=OFFSET_PROTOCOL:parser.error("Protocol fingerprint changed.")
    if len({p.resolve() for p in (args.first,args.second,args.output)})!=3:parser.error("Use distinct input and output paths.")
    (fit if args.operation=="fit" else assessment)(args.cache,args.first,args.second,args.output)
