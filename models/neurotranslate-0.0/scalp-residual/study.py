"""Fit a robust correction on the designated development people; assess the sealed model on fresh runs."""
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
import predict
import scalp_residual as signal
from ofner_early import Run

PROTOCOL="0476e81b91d6a6a447bc504379460bc02d46703a5a672a7e2e77d64e979e1f93"
PARENT="901922e1db489a06cc3252212232b7df65784128695f86f84a751726b9f0521c"
ELECTRODES=(13,17,28,32,43,47,62,63,64)
SENSORS=(93,94,68)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,data):p.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")


def load(cache, stage):
    roster=[(p,r) for p in range(1,8) for r in (1,2,3)] if stage=="fit" else [(p,4) for p in range(8,13)]
    x=[];s=[];e=[];y=[];g=[];qc=[];omissions=Counter();marked=0
    for person,num in roster:
        with Run(cache,person,num) as run:
            motion=np.column_stack([run.window(k,0,run.records*64) for k in SENSORS])
            varied=True
            for channel in motion.T:
                finite=channel[np.isfinite(channel)]
                if len(finite)<2 or finite.max()==finite.min():varied=False
            cues=[(t,c) for t,c in run.events if 0x600<=c<=0x606]
            marked+=len(cues)
            for i,(t,c) in enumerate(cues):
                if not varied:omissions["unavailable_motion_channel"]+=1;continue
                cutoff=t+128;last=cutoff//8
                stop=cues[i+1][0] if i+1<len(cues) else run.records*512
                end=[et for et,ec in run.events if t<et<=stop and ec==c+0x8000]
                if len(end)!=1 or end[0]<t+896:omissions["missing_or_short_event"]+=1;continue
                endpoints=(cutoff+np.array([256,512,768]))//8
                if t-128<0 or last<31 or endpoints[-1]>=len(motion):omissions["clock_boundary"]+=1;continue
                volts=np.column_stack([run.window(k,t-128,cutoff+1) for k in ELECTRODES])
                bins=motion[last-31:last+1].reshape(4,8,3)
                future=motion[endpoints[:,None]+np.arange(-7,1)]
                if not (np.isfinite(volts).all() and np.isfinite(bins).all() and np.isfinite(future).all()):
                    omissions["incomplete_required_window"]+=1;continue
                means=volts[1:].reshape(4,64,9).mean(axis=1)
                levels=np.median(bins,axis=1)
                x.append(np.column_stack((levels,np.median(bins[:,4:],axis=1)-np.median(bins[:,:4],axis=1))))
                s.append(means[:,:6]);e.append(means[:,6:]);y.append(np.median(future,axis=1)-levels[-1])
                qc.append(np.std(volts[:128],axis=0));g.append((person,num,c-0x600))
    labels=np.array(g,dtype=int).reshape(-1,3)
    quality={"candidate_people":len(set(p for p,_ in roster)),"files":len(roster),"marked":marked,
             "trials":len(g),"people":len(np.unique(labels[:,0])),"runs":len(np.unique(labels[:,:2],axis=0)),"omissions":dict(omissions)}
    return (np.array(x).reshape(-1,4,6),np.array(s).reshape(-1,4,6),np.array(e).reshape(-1,4,3),
            np.array(y).reshape(-1,3,3),labels,np.array(qc).reshape(-1,9),quality)


def balance(g):
    if not len(g):raise ValueError("No eligible trials on this support.")
    out=np.zeros(len(g));people=np.unique(g[:,0])
    for p in people:
        own=g[:,0]==p;runs=np.unique(g[own,1])
        for r in runs:
            run=own&(g[:,1]==r);cues=np.unique(g[run,2])
            for c in cues:
                use=run&(g[:,2]==c);out[use]=1/(len(people)*len(runs)*len(cues)*use.sum())
    return out


def scales(x,wt):
    mean=np.average(x,axis=0,weights=wt)
    sd=np.sqrt(np.average((x-mean)**2,axis=0,weights=wt))
    return mean,np.where(sd<1e-8,1.,sd)


def huber(z,y,wt):
    coef=np.zeros((z.shape[1],y.shape[1]));iterations=[];changes=[]
    penalty=.05*np.eye(z.shape[1])
    for j in range(y.shape[1]):
        old=coef[:,j]
        for i in range(100):
            abs_error=np.abs(y[:,j]-z@old)
            rw=wt*np.minimum(1.,.25/np.maximum(abs_error,np.finfo(float).tiny))
            new=np.linalg.solve(z.T@(rw[:,None]*z)+penalty,z.T@(rw*y[:,j]))
            change=float(np.max(np.abs(new-old)));old=new
            if change<1e-10:break
        coef[:,j]=old;iterations.append(i+1);changes.append(change)
    return coef,{"iterations":iterations,"final_max_coef_change":changes}


def fit(cache,parent,output,receipt):
    if sha(parent)!=PARENT:raise ValueError("Use the registered group arm checkpoint.")
    x,s,e,y,g,qc,quality=load(cache,"fit");wt=balance(g)
    cfg,w=predict.read_checkpoint(parent)
    s,e=signal.centered(s),signal.centered(e)
    key="scalp_residual.ocular."
    for name,v in (("scalp",s),("eye",e)):
        w[key+name+"_mean"],w[key+name+"_sd"]=scales(v.reshape(-1,v.shape[-1]),np.repeat(wt/4,4))
    ez=((e-w[key+"eye_mean"])/w[key+"eye_sd"]).reshape(-1,3)
    sz=((s-w[key+"scalp_mean"])/w[key+"scalp_sd"]).reshape(-1,6)
    bwt=np.repeat(wt/4,4)
    w[key+"coef"]=np.linalg.solve(ez.T@(bwt[:,None]*ez)+.10*np.eye(3),ez.T@(bwt[:,None]*sz))
    sd=w["group_arm.target_sd"]
    if np.any(sd<1e-8):raise ValueError("Original fitting target SD is too small for pooled scoring.")
    targets=((y-w["group_arm.cue_median"][g[:,2]])/sd).reshape(-1,9)
    movement=signal.motion_features(x,cfg,w,predict.linear,predict.encode)
    convergence={}
    for mode in signal.FIT_MODES:
        mat=signal.features(mode,movement,s,e,w);k="scalp_residual."+mode+"."
        w[k+"mean"],w[k+"sd"]=scales(mat,wt)
        z=(mat-w[k+"mean"])/w[k+"sd"]
        w[k+"coef"],convergence[mode]=huber(z,targets,wt)
    w["scalp_residual.precue_sd99"]=np.quantile(qc,.99,axis=0)
    cfg["scalp_residual"]={"format":1,"protocol":PROTOCOL,"parent":PARENT,"fit_people":quality["people"],"fit_trials":len(x),"modes":list(signal.MODES)}
    with np.load(parent,allow_pickle=False) as original:arrays={k:original[k] for k in original.files}
    arrays.update({k:v for k,v in w.items() if k.startswith("scalp_residual.")})
    arrays["configuration"]=np.array(json.dumps(cfg))
    np.savez_compressed(output,**arrays)
    write(receipt,{"checkpoint_sha256":sha(output),"parent_sha256":PARENT,"protocol_sha256":PROTOCOL,
                   "quality":quality,"solver":convergence,"assessed":False})


def next_repeat(g):
    donor=np.full(len(g),-1,dtype=int)
    for row in np.unique(g,axis=0):
        group=np.flatnonzero((g==row).all(axis=1))
        if len(group)>1:donor[group]=np.roll(group,-1)
    return donor


def summarize(losses,g,sd):
    if not len(g):return {"people":0,"trials":0,"models":{}},{}
    ww=balance(g);people=np.unique(g[:,0]);by_person={};results={}
    for m,loss in losses.items():
        standardized=(loss/sd).mean(axis=(1,2));per=[]
        for p in people:
            mask=g[:,0]==p;per.append(float(balance(g[mask])@standardized[mask]))
        by_person[m]=np.array(per)
        results[m]={"scaled_mae":float(ww@standardized),"native_mae":np.average(loss,weights=ww,axis=0).tolist(),
                    "by_cue":{name:float(balance(g[g[:,2]==i])@standardized[g[:,2]==i]) if np.any(g[:,2]==i) else None for i,name in enumerate(arm.CUES)}}
    return {"people":len(people),"runs":len(np.unique(g[:,:2],axis=0)),"trials":len(g),"models":results},by_person


def compare(per,candidate,other):
    if candidate not in per or len(per[candidate])<4:return {"available":False,"pass":False}
    delta=per[candidate]-per[other];n=len(delta);reference=per[other].mean()
    draws=np.random.default_rng(66381).integers(n,size=(10000,n))
    ci=np.quantile(delta[draws].mean(axis=1),[.025,.975])
    frac=float(delta.mean()/reference) if reference>0 else None
    return {"available":True,"mean_difference":float(delta.mean()),"relative_change":frac,"interval95":ci.tolist(),
            "improved":int((delta<0).sum()),"people":n,"sorted_paired_differences":np.sort(delta).tolist(),
            "pass":bool(frac is not None and frac<=-.05 and ci[1]<0 and (delta<0).sum()>n/2)}


def assess(cache,checkpoint,receipt,output):
    fit_seal=json.loads(receipt.read_bytes())
    if sha(checkpoint)!=fit_seal["checkpoint_sha256"] or fit_seal["parent_sha256"]!=PARENT or fit_seal["protocol_sha256"]!=PROTOCOL:
        raise ValueError("Verify the registered fit seal before opening the assessment.")
    cfg,w=predict.read_checkpoint(checkpoint)
    if cfg.get("scalp_residual",{}).get("protocol")!=PROTOCOL:raise ValueError("Wrong model or study.")
    x,s,e,y,g,qc,q=load(cache,"assess")
    if not len(g):write(output,{"quality":q,"reason":"No complete trial."});return
    sd=w["group_arm.target_sd"];ids=g[:,2];donor=next_repeat(g);paired=donor>=0
    clean=(qc<=w["scalp_residual.precue_sd99"]).all(axis=1)
    ages={}
    errors={}
    for mode in signal.MODES:
        pred=signal.batch(mode,ids,x,s,e,cfg,w,predict.linear,predict.encode)
        errors[mode]=np.abs(pred-y)
    for mode in ("scalp","joint"):
        pred=signal.batch(mode,ids,x,s,e,cfg,w,predict.linear,predict.encode,donor=np.maximum(donor,0))
        errors[mode+"_shifted"]=np.abs(pred-y)
    for name,mask in (("all",np.ones(len(g),dtype=bool)),("paired",paired),("screened",clean),("screened_pairs",paired&clean&clean[np.maximum(donor,0)])):
        models=errors if name in ("paired","screened_pairs") else {m:errors[m] for m in signal.MODES}
        report,per=summarize({k:v[mask] for k,v in models.items()},g[mask],sd)
        report["comparisons"]={}
        for cand,controls in (("scalp",("mechanics","cue_median","scalp_shifted")),
                              ("joint",("eye","cue_median","joint_shifted"))):
            for c in controls:
                if c in models:report["comparisons"][cand+"_vs_"+c]=compare(per,cand,c)
        ages[name]=report
    gates={}
    for mode,control in (("scalp","mechanics"),("joint","eye")):
        gates[mode]=all(v.get("pass",False) for v in [ages["all"]["comparisons"][mode+"_vs_"+control],ages["all"]["comparisons"][mode+"_vs_cue_median"],ages["paired"]["comparisons"][mode+"_vs_"+mode+"_shifted"]])
    write(output,{"protocol_sha256":PROTOCOL,"checkpoint_sha256":sha(checkpoint),"assessment":q,"fit":fit_seal["quality"],
                  "horizons_after_cutoff_s":list(arm.DELAYS),"output_channels":list(arm.CHANNELS),"groups":ages,"primary_tests":gates})
    print(q,{m:round(v["scaled_mae"],5) for m,v in ages["paired"]["models"].items()},gates)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("fit","assess"))
    for key in ("cache","first","second","output"):parser.add_argument(key,type=Path)
    a=parser.parse_args()
    if sha(HERE/"PROTOCOL.md")!=PROTOCOL:parser.error("Protocol fingerprint differs.")
    if len({p.resolve() for p in (a.first,a.second,a.output)})!=3:parser.error("Specify distinct checkpoint, report and receipt files.")
    (fit if a.action=="fit" else assess)(a.cache,a.first,a.second,a.output)
