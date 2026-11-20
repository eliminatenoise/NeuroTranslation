"""Fit pooled, independent and cross-study calibrated linear temporal controls."""
import argparse
import json
from pathlib import Path
import numpy as np
from forecast import BASELINES,FITS,estimate,prepared,context_key
DOMAINS=("balance","grasp_lift")
WRONG=("wrong_muscle","wrong_keep_hold")


def write(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")
def take(d,mask):return {k:v[mask] for k,v in d.items()}


def weights(d):
    w=np.zeros(len(d["domain"]));domains=np.unique(d["domain"])
    for dom in domains:
        use=d["domain"]==dom;people=np.unique(d["person"][use])
        for p in people:
            own=use&(d["person"]==p)
            sessions=np.unique(d["session"][own])
            for s in sessions:
                sess=own&(d["session"]==s);cues=np.unique(d["direction"][sess])
                for c in cues:
                    rows=sess&(d["direction"]==c)
                    w[rows]=1/(len(domains)*len(people)*len(sessions)*len(cues)*np.count_nonzero(rows))
    return w


def supported(d):
    valid=np.zeros(len(d["domain"]),bool)
    for person in np.unique(d["person"]):
        own=d["person"]==person
        if (d["domain"][own]==1).all() or set(zip(d["session"][own],d["direction"][own]))=={(0,-1),(0,1),(1,-1),(1,1)}:valid|=own
    return valid


def count(d):
    return dict(people=len(np.unique(d["person"])),sessions=len(set(zip(d["person"],d["session"]))),events=len(d["domain"]))


def ridge(x,y,w,prior):
    g=x.T@(w[:,None]*x)+.05*np.eye(x.shape[1])
    rhs=x.T@(w[:,None]*y)
    if prior is not None:rhs+=.05*np.asarray(prior).reshape(rhs.shape)
    return np.linalg.solve(g,rhs)


def fit_one(d,prior):
    v=prepared(d);w=weights(d);ok=v["active"];n=ok.sum(1)
    mw=np.broadcast_to((w/np.maximum(n,1))[:,None],ok.shape)[ok];mw=mw/mw.sum()
    my=((d["future_rms"]-v["hold"])[ok]/v["scale"][ok])[:,None]
    mc=ridge(v["muscle_x"][ok],my,mw,prior["muscle_coef"] if prior else None)[:,0]
    moving=v["moving"];x=v["path_x"][moving].reshape(-1,15)
    y=((d["future_path_mm"][moving]-d["repeat_path_mm"][moving])/v["path_scale"][moving,None,None]).transpose(0,2,1).reshape(-1,32)
    pw=np.repeat(w[moving]/w[moving].sum()/3,3)
    pc=ridge(x,y,pw,prior["path_coef"] if prior else None)
    return {"muscle_coef":mc.tolist(),"path_coef":pc.tolist(),"training":count(d),
            "silent_available_channel_events":int((d["muscle_mask"]&~ok).sum()),"zero_motion_scale_events":int((~moving).sum())}


def fit(d):
    state={"version":1,"fits":{},"means":{}}
    contexts=np.array([context_key(*t) for t in zip(d["domain"],d["session"],d["direction"])])
    for c in np.unique(contexts):
        group=take(d,contexts==c);w=weights(group)
        mean=[]
        for ch in range(13):
            mask=group["muscle_mask"][:,ch]
            mean.append(float(weights(take(group,mask))@group["future_rms"][mask,ch]) if mask.any() else 0.)
        state["means"][c]={"rms":mean,"path":np.einsum("n,nti->ti",w,group["future_path_mm"]).tolist()}
    state["fits"]["pooled"]=fit_one(d,None)
    for dom,name in enumerate(("leg","arm")):state["fits"][name]=fit_one(take(d,d["domain"]==dom),None)
    for dom,name,foreign in ((0,"leg","arm"),(1,"arm","leg")):
        limited=take(d,(d["domain"]==dom)&(d["block"]==0))
        if not len(limited["person"]):raise ValueError("Missing early target calibration rows for "+name)
        state["fits"][name+"_limited"]=fit_one(limited,None)
        state["fits"][foreign+"_to_"+name]=fit_one(limited,state["fits"][foreign])
    return state


def donors(d):
    out=np.full(len(d["domain"]),-1,int);groups={}
    for i,(dom,p,s,cu,bl) in enumerate(zip(d["domain"],d["person"],d["session"],d["direction"],d["block"])):
        key=(dom,p,s,cu,bl if dom==0 else -1)
        groups.setdefault(key,[]).append(i)
    for key,ii in groups.items():
        if len(ii)<2:continue
        ordered=np.array(sorted(ii,key=lambda i:int(d["event"][i])));partner=np.roll(ordered,-1)
        ok=np.ones(len(ii),bool) if key[0]==1 else (abs(d["cutoff"][ordered]-d["cutoff"][partner])>207)
        out[ordered[ok]]=partner[ok]
    return out


def predicts(d,state):
    v=prepared(d);res={};n=len(d["person"])
    def pack(mode,d,v,override=None):
        a,p,clip=estimate(mode,d,v,state,hold_override=override)
        return np.column_stack((a,p.reshape(len(a),-1))),clip
    for m in (*BASELINES,*FITS):res[m]=pack(m,d,v)
    donor=donors(d);idx=np.maximum(0,donor)
    mask=d["muscle_mask"]&d["muscle_mask"][idx]
    valid=(donor>=0)&(mask.sum(axis=1)>=np.where(d["domain"]==1,3,8))
    match=np.flatnonzero(valid);true=take(d,match);true["muscle_mask"]=mask[match]
    swapped={**true,"patch_rms":d["patch_rms"][idx[match]]}
    a,b=prepared(true),prepared(swapped)
    for m,dd,vv,h in [("correct_on_donor_mask",true,a,None),("wrong_muscle",swapped,b,None),("wrong_keep_hold",swapped,b,a["hold"])]:
        out=np.full((n,109),np.nan);clips=np.zeros(n,int)
        if len(match):out[match],clips[match]=pack("pooled",dd,vv,h)
        res[m]=out,clips
    return res,mask


def difference(per):
    rng=np.random.default_rng(1641);n=len(per)
    draw=per[rng.integers(0,n,(5000,n))].mean(1)
    return {"mean":per.mean(0).tolist(),"ci95":np.quantile(draw,[.025,.975],axis=0).T.tolist(),
            "upper_98_75":np.quantile(draw,.9875,axis=0).tolist(),"people_improved":(per<0).sum(0).tolist()}


def scope(d,estimates,m,channels,methods):
    info=count(take(d,m));info["methods"]={};individual={}
    if not m.any():return info,individual
    small=take(d,m);w=weights(small);people=np.unique(small["person"]);mask=channels[m];nc=mask.sum(axis=1)
    info["per_channel_events"]=mask.sum(axis=0).tolist();info["per_channel_people"]=[len(np.unique(small["person"][v])) for v in mask.T]
    for name in methods:
        y=estimates[name][0][m];z=y[:,:13]-small["future_rms"]
        path=y[:,13:].reshape(-1,32,3)-small["future_path_mm"];dist=np.linalg.norm(path,axis=2)
        val=np.column_stack(((np.abs(z)*mask).sum(1)/nc,dist.mean(1),dist[:,-1]))
        per=np.stack([np.average(val[small["person"]==p],weights=w[small["person"]==p],axis=0) for p in people])
        individual[name]=per;score=per.mean(0);channel_mae=[];channel_bias=[]
        for j in range(13):
            rows=mask[:,j]
            if rows.any():
                wc=weights(take(small,rows));channel_mae.append(float(wc@abs(z[rows,j])));channel_bias.append(float(wc@z[rows,j]))
            else:channel_mae.append(None);channel_bias.append(None)
        info["methods"][name]={"emg_mae_native":float(score[0]),"mean_path_mm":float(score[1]),"endpoint_mm":float(score[2]),
            "channel_mae_native":channel_mae,"channel_bias_native":channel_bias,
            "endpoint_bias_mm":(w@path[:,-1]).tolist(),"pre_bound_negative":int(estimates[name][1][m].sum())}
    return info,individual


def report(d,res,common):
    available=d["muscle_mask"];out={};main=(*BASELINES,*FITS);passes=[]
    for dom,label,native,foreign in [(0,"balance","leg","arm"),(1,"grasp_lift","arm","leg")]:
        rows=d["domain"]==dom
        summary,per=scope(d,res,rows,available,main);summary["unit"]="µV" if dom==0 else "WAY native amplitude"
        if not per:out[label]=summary;passes.append(False);continue
        summary["strict_complete"]=scope(d,res,rows&d["complete"].astype(bool),available,main)[0]
        if dom==0:
            summary["posture"]={str(s):scope(d,res,rows&(d["session"]==s),available,main)[0] for s in (0,1)}
        target=foreign+"_to_"+native
        summary["paired_differences"]={a+"_minus_"+b:difference(per[a]-per[b]) for a,b in [
            ("pooled",native),(foreign,native),(target,native+"_limited"),(target,native),(target,foreign),("pooled","hold_repeat"),("pooled","hold_velocity")]}
        test=summary["paired_differences"][target+"_minus_"+native+"_limited"]
        summary["calibrated_pass_amplitude_path"]=(np.array(test["upper_98_75"][:2])<0).tolist()
        passes.append(all(summary["calibrated_pass_amplitude_path"]))
        match=rows&np.isfinite(res["correct_on_donor_mask"][0][:,0]);q,by=scope(d,res,match,common,("correct_on_donor_mask",*WRONG))
        if by:q["paired_differences"]={k:difference(by['correct_on_donor_mask']-by[k]) for k in WRONG}
        summary["masked_donor_comparison"]=q;out[label]=summary
    return {"domains":out,"all_four_calibrated_transfer_bounds_below_zero":all(passes),"measure_order":["available muscle MAE in each native study scale","mean 3-D path mm","final 3-D endpoint mm"]}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("stage",choices=("fit","assess"))
    for k in ("source","model","summary"):p.add_argument(k,type=Path)
    p.add_argument("--private",type=Path);a=p.parse_args()
    if a.private:a.private.mkdir(exist_ok=True,parents=True)
    with np.load(a.source,allow_pickle=False) as f:
        names=("domain","person","session","direction","event","cutoff","block","complete","patch_rms","muscle_mask","patch_xyz_mm","age_s","past_rms","repeat_path_mm","future_rms","future_path_mm")
        d={k:(f[k].astype(np.float64) if k in names[8:] and k!="muscle_mask" else f[k]) for k in names}
    d["muscle_mask"]=d["muscle_mask"].astype(bool);d=take(d,supported(d))
    if a.stage=="fit":
        folds=np.zeros(len(d["domain"]),int)
        for dom in (0,1):
            for i,person in enumerate(sorted(set(d["person"][d["domain"]==dom]))):folds[(d["person"]==person)&(d["domain"]==dom)]=i%3
        common=np.zeros_like(d["muscle_mask"]);res={}
        for f in range(3):
            held=folds==f;state=fit(take(d,~held));pred,mask=predicts(take(d,held),state);common[held]=mask
            for name,(x,c) in pred.items():
                out,clip=res.setdefault(name,(np.full((len(folds),109),np.nan),np.zeros(len(folds),int)));out[held]=x;clip[held]=c
            if a.private:write(a.private/f"fold-{f}.json",state)
        write(a.model,fit(d))
    else:res,common=predicts(d,json.loads(a.model.read_bytes()))
    write(a.summary,report(d,res,common))
    if a.private:
        ids={k:d[k] for k in names[:8]};np.savez_compressed(a.private/(a.summary.stem+"-rows.npz"),**ids,**{k:v[0] for k,v in res.items()},donor_mask=common)
if __name__=="__main__":main()
