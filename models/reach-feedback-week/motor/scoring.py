"""Original-balanced metrics with physical block-specific paired draws."""
import numpy as np

REGIONS = {"hand_mm":(0,3,1000.), "elbow_mm":(3,6,1000.), "handle_cm":(6,8,1.)}
HORIZONS = ["trajectory_mean","endpoint"] + [f"{t}ms" for t in range(10,101,10)]
METHODS = ("full","pose","wrong","ridge_full","ridge_pose","ridge_wrong","frozen","stationary","velocity")


def errors(pred, target, region):
    left,right,scale=REGIONS[region]
    e=np.linalg.norm((pred[:,:,left:right]-target[:,:,left:right])*scale,axis=2)
    return np.column_stack((e.mean(axis=1),e[:,-1],e))


def per_original(values, rows, roster, valid):
    groups={}
    for i,key in enumerate(rows):
        if valid[i]:
            groups.setdefault(key,[]).append(i)
    return np.array([values[groups[key]].mean(axis=0) if key in groups else
                     np.full(values.shape[1],np.nan) for key in roster])


def resamples(roster):
    block=np.array([b for b,o in roster])
    draws={}
    for scheme in ("moving","ordinary"):
        rng=np.random.default_rng(20261125)
        columns=[]
        for b in np.unique(block):
            ix=np.flatnonzero(block==b)
            n=len(ix)
            if scheme=="moving" and n<8:
                break
            if scheme=="ordinary":
                pos=rng.integers(n,size=(5000,n))
            else:
                starts=rng.integers(n-7,size=(5000,(n+7)//8))
                pos=(starts[:,:,None]+np.arange(8)).reshape(5000,-1)[:,:n]
            columns.append(ix[pos])
        else:
            draws[scheme]=np.column_stack(columns)
    return draws


def vector(x):
    return [float(v) if np.isfinite(v) else None for v in x]


def summary(values, draws=None):
    ok=np.isfinite(values).all(axis=1)
    result={"originals":int(ok.sum()),"mean":vector(values[ok].mean(axis=0)) if ok.any() else [None]*values.shape[1]}
    if draws is None:
        return result
    for scheme in ("moving","ordinary"):
        if scheme not in draws:
            result[scheme]={"interval":None,"reason":"fewer than eight originals in a physical block"}
            continue
        ix=draws[scheme]
        denom=ok[ix].sum(axis=1)
        if denom.min()==0:
            result[scheme]={"interval":None,"empty":int((denom==0).sum()),"reason":"empty draws"}
            continue
        safe=np.nan_to_num(values)
        estimates=np.column_stack([safe[:,j][ix].sum(axis=1)/denom for j in range(values.shape[1])])
        result[scheme]={"interval":np.quantile(estimates,[.025,.975],axis=0).T.tolist(),"empty":0}
    return result


def score(data,predictions,roster):
    result={"dimensions":HORIZONS,"workspaces":{}}
    row_keys=list(zip(data["block"].tolist(),data["original"].tolist()))
    for w in sorted(set(r["workspace"] for r in roster if r["workspace"] is not None)):
        ordered=sorted((r for r in roster if r["workspace"]==w),key=lambda r:(r["block"],r["start"]))
        keys=[(r["block"],r["original"]) for r in ordered]
        draws=resamples(keys)
        workspace=data["workspace"]==w
        sections={"roster":len(keys),"windows":int(workspace.sum()),"regions":{}}
        for region in REGIONS:
            e={m:errors(predictions[m],data["movement"],region) for m in METHODS}
            ok={m:np.isfinite(x).all(axis=1)&workspace for m,x in e.items()}
            support=ok["full"] & ok["pose"] & ok["wrong"]
            groups={}
            for m in METHODS:
                nat=per_original(e[m],row_keys,keys,ok[m])
                matched=per_original(e[m],row_keys,keys,support & ok[m])
                groups[m]={"natural":summary(nat),"natural_windows":int(ok[m].sum()),
                           "matched":summary(matched),"matched_windows":int((support&ok[m]).sum())}
            contrasts={}
            for m in ("pose","wrong","ridge_full","frozen","velocity","stationary"):
                valid=support&ok[m]
                contrasts[f"full_minus_{m}"]=summary(per_original(e["full"]-e[m],row_keys,keys,valid),
                                                     draws if m in ("pose","wrong") else None)
            for m in ("ridge_pose","ridge_wrong"):
                contrasts[f"ridge_full_minus_{m}"]=summary(per_original(e["ridge_full"]-e[m],row_keys,keys,support),draws)
            seeds={}
            for arm in ("full","pose","wrong","frozen"):
                arr=[]
                for p in predictions["seeds_"+arm]:
                    tmp=errors(p,data["movement"],region)
                    arr.append(summary(per_original(tmp,row_keys,keys,support))["mean"])
                finite=np.asarray(arr,dtype=float)
                seeds[arm]={"means":arr,"min":vector(np.min(finite,axis=0)),"max":vector(np.max(finite,axis=0))}
            represented={row_keys[i] for i in np.flatnonzero(support)}
            by_block={str(b):{"roster":sum(x[0]==b for x in keys),"matched_originals":sum(x[0]==b for x in represented),
                              "matched_windows":int((support & (data["block"]==b)).sum())} for b in sorted({x[0] for x in keys})}
            sections["regions"][region]={"matched_windows":int(support.sum()),"by_block":by_block,
                                         "methods":groups,"contrasts":contrasts,"seed_range":seeds}
        result["workspaces"][str(w)]=sections
    return result
