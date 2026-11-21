"""Compare estimated changes in the OpenSim muscle–tendon path lengths by workspace."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from model import infer_direct,infer_path

KEYS=("block","workspace","original","ordinal","k")
ARMS=("full","pose","wrong","frozen","ridge_full","ridge_pose","stationary","velocity","measured_path","direct")
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def resamples(blocks,moving=True):
    rng=np.random.default_rng(20261125);out=[]
    for b in np.unique(blocks):
        group=np.flatnonzero(blocks==b);n=len(group)
        if moving and n<8:return None
        if moving:
            start=rng.integers(n-7,size=(5000,(n+7)//8))
            pick=(start[:,:,None]+np.arange(8)).reshape(5000,-1)[:,:n]
        else:pick=rng.integers(n,size=(5000,n))
        out.append(group[pick])
    return np.column_stack(out)
def group(values,positions,size):
    vals=np.zeros((size,values.shape[1]));count=np.bincount(positions,minlength=size)
    np.add.at(vals,positions,values)
    return np.divide(vals,count[:,None],where=count[:,None]>0,out=np.full_like(vals,np.nan))
def interval(table,indices):
    if indices is None:return None
    mask=np.isfinite(table);sample=table[indices];n=mask[indices].sum(1)
    if np.any(n==0):return None
    return np.quantile(np.nansum(sample,axis=1)/n,[.025,.975]).tolist()
def metrics(error,moving):
    ma=np.abs(error)*1000
    return dict(endpoint_mae=ma[:,:,-1].mean(-1),trajectory_mae=ma.mean((2,3)),
                moving_endpoint_mae=ma[:,:,-1,moving].mean(-1),
                endpoint_by_path=ma[:,:,-1].mean(0),trajectory_by_path=ma.mean((0,2)))
def run(args):
    with np.load(args.weights) as q:weights=dict(q)
    blocks=[];targets=[];poses=[];moves=[];cues=[]
    for source,label in zip(args.sources,args.lengths,strict=True):
        with np.load(source) as s,np.load(label) as y:
            for k in KEYS:np.testing.assert_array_equal(s[k],y[k])
            np.testing.assert_array_equal(weights["names"],y["names"])
            blocks.append(np.column_stack([s[k] for k in KEYS]))
            targets.append(y["delta_m"]);poses.append(s["pose"]);moves.append(s["movement"]);cues.append(s["cue"])
    keys=np.concatenate(blocks);y=np.concatenate(targets);pose=np.concatenate(poses);movement=np.concatenate(moves);cue=np.concatenate(cues)
    with np.load(args.motor) as z:
        np.testing.assert_array_equal(keys,np.column_stack([z[k] for k in KEYS]))
        forecasts={arm:z["seeds_"+arm] for arm in ("full","pose","wrong","frozen")}
        forecasts.update({arm:z[arm][None,...] for arm in ("ridge_full","ridge_pose","stationary","velocity")})
        donor=z["donor"];mask=(donor>=0)
    assert np.all(donor[mask]<np.flatnonzero(mask)) and np.all(keys[donor[mask],0]==keys[mask,0]) and np.all(keys[donor[mask],1]==keys[mask,1])
    assert np.all(keys[donor[mask],2]!=keys[mask,2]) and np.all(keys[donor[mask],3]==keys[mask,3])
    forecasts["measured_path"]=movement[None,...]
    predictions={a:np.stack([infer_path(pose,one,weights) for one in pred]) for a,pred in forecasts.items()}
    predictions["direct"]=infer_direct(pose,cue,weights)[None,...]
    losses={a:metrics(pred-y[None,...],weights["moving_subset"]) for a,pred in predictions.items()}
    meta=json.loads(args.roster.read_bytes())
    report={"scores":{},"paths":weights["names"].tolist(),"moving_paths":weights["names"][weights["moving_subset"]].tolist(),
            "units":"millimetres of change in the source model's musculotendon length, relative to k-1","metrics":"Mean absolute error; each seed scored separately, original windows averaged then equal-original mean; range [k,k+9] vs last k-1","seed_order":[17,41,73],"positive_claim":True,
            "checksums":{p.name:sha(p) for p in [args.weights,args.motor,*args.sources,*args.lengths,args.roster]}}
    for ws in (1,2):
        ordered=sorted((r for r in meta if r["workspace"]==ws),key=lambda r:(r["block"],r["start"]))
        pos={(r["block"],r["original"]):j for j,r in enumerate(ordered)}
        in_ws=keys[:,1]==ws
        positions=np.array([pos.get((b,o),-1) for b,_,o,_,_ in keys])
        assert np.all(positions[in_ws]>=0) and len(pos)==len(ordered)
        rb=np.array([r["block"] for r in ordered]);draw=resamples(rb);iid=resamples(rb,False)
        good=np.isfinite(y).all((1,2))&in_ws
        matched=good&mask
        for a in ("full","pose","wrong"):matched &= np.isfinite(predictions[a]).all((0,2,3))
        stats={"roster":len(ordered),"candidate_windows":int(in_ws.sum()),"finite_reference_windows":int(good.sum()),"matched_windows":int(matched.sum()),"matched_originals":len(np.unique(positions[matched])),"arms":{},"paired":{}}
        for a in ARMS:
            ok=good&np.isfinite(predictions[a]).all((0,2,3))
            views={}
            for lab,take in [("available",ok),("matched",matched & ok)]:
                v={"originals":len(np.unique(positions[take])),"windows":int(take.sum())}
                for name,arr in losses[a].items():
                    val=arr if "by_path" in name else arr.mean(0)[:,None]
                    ref=group(val[take],positions[take],len(ordered))
                    v[name]=np.nanmean(ref,axis=0).tolist() if take.any() else [None]*val.shape[1]
                views[lab]=v
            stats["arms"][a]=views
        for other in ("pose","wrong","frozen"):
            diff=(losses["full"]["endpoint_mae"]-losses[other]["endpoint_mae"]).mean(0)
            g=group(diff[matched,None],positions[matched],len(ordered))[:,0]
            ci=interval(g,draw)
            stats["paired"]["full_minus_"+other]={"difference":float(np.nanmean(g)) if matched.any() else None,"block_95":ci,"iid_95":interval(g,iid)}
            if other in ("pose","wrong") and (ci is None or ci[1]>=0):report["positive_claim"]=False
        report["scores"][str(ws)]=stats
    args.out.mkdir(exist_ok=True,parents=True)
    # These example trajectories are an arithmetic mean of fitted seeds for replay only.
    np.savez_compressed(args.out/"predictions.npz",**{a:p.mean(0) for a,p in predictions.items()},reference=y,names=weights["names"],keys=keys)
    (args.out/"summary.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("weights","motor","roster","out"):p.add_argument("--"+k,type=Path,required=True)
    for k in ("sources","lengths"):p.add_argument("--"+k,type=Path,nargs="+",required=True)
    run(p.parse_args())
