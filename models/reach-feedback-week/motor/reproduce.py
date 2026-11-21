"""Reproduce the September 7 movement readout and September 14 paired scores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from replay import (SEEDS, CONTACTS, WEIGHTS, body_features, body_forecast, design,
                    load_arrays, load_model, pooled_history, residual)
from scoring import REGIONS, errors, score

def weights(block,original):
    _,inv,n=np.unique(np.stack((block,original),axis=1),return_inverse=True,return_counts=True,axis=0)
    return 1./(len(n)*n[inv])

def fit_design(d,idx,w):
    body=body_features(d["pose"][idx],d["cue"][idx])
    cnt=np.log1p(d["pooled"][idx].reshape(len(idx),148))
    rng=np.random.default_rng(20261127)
    cfg={"contacts":CONTACTS}
    for name,x in (("body",body),("count",cnt)):
        mean=w@x
        sd=np.sqrt(w@(x-mean)**2)
        cfg[name+"_mean"]=mean
        cfg[name+"_scale"]=np.where(sd<1e-8,1.,sd)
        cfg[name+"_projection"]=rng.normal(size=(x.shape[1],48))/np.sqrt(x.shape[1])
    return cfg

def torch_setup(threads):
    import torch
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    return torch

def fit_adapter(x,y,w,seed,device,steps):
    import torch
    from torch import nn
    torch.manual_seed(seed)
    net=nn.Sequential(nn.Linear(48,24),nn.Tanh(),nn.Linear(24,80))
    with torch.no_grad():
        net[-1].weight.zero_()
        net[-1].bias.zero_()
    net.to(device)
    opt=torch.optim.AdamW(net.parameters(),lr=.003,weight_decay=.01,foreach=False,fused=False)
    xx,yy,ww=[torch.as_tensor(a,dtype=torch.float32,device=device) for a in (x,y,w)]
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        loss=((net(xx)-yy).square().mean(1)*ww).sum()
        loss.backward()
        opt.step()
    with torch.no_grad():
        native=net(xx).cpu().numpy()
    p={name:par.detach().cpu().numpy() for name,par in zip(("in_weight","in_bias","out_weight","out_bias"),net.parameters())}
    mean_x,mean_y=w@x,w@y
    xc=x-mean_x
    p["ridge_weight"]=np.linalg.solve(xc.T@(w[:,None]*xc)+.05*np.eye(x.shape[1]),xc.T@(w[:,None]*(y-mean_y)))
    p["ridge_bias"]=mean_y-mean_x@p["ridge_weight"]
    native_ridge=(torch.from_numpy(x)@torch.from_numpy(p["ridge_weight"])+torch.from_numpy(p["ridge_bias"])).numpy()
    parity=float(np.max(np.abs(native-residual(x,p,"mlp"))))
    ridge_parity=float(np.max(np.abs(native_ridge-residual(x,p,"ridge"))))
    if not np.isfinite([parity,ridge_parity]).all() or max(parity,ridge_parity)>=.0005:
        raise ValueError("Native/portable mismatch")
    return p,{"steps":steps,"parameters":sum(t.numel() for t in net.parameters()),
              "max_normalized_port_error":parity,"ridge_max_normalized_port_error":ridge_parity,
              "design_rank":int(np.linalg.matrix_rank(x))},native

def donors(d):
    n=len(d["k"])
    out=np.full(n,-1,dtype=int)
    latest={}
    for i in np.lexsort((d["k"],d["block"])):
        key=tuple(d[k][i] for k in ("block","workspace","ordinal"))
        old=latest.get(key)
        if old is not None:
            if d["original"][old]==d["original"][i] or d["k"][old]>=d["k"][i]:
                raise ValueError("Ambiguous same-ordinal donor or overlapping chronology")
            out[i]=old
        latest[key]=i
    return out

def forecast_all(d,folder):
    donor=donors(d)
    pool=d["pooled"]
    wrong=np.full_like(pool,np.nan)
    ok=donor>=0
    wrong[ok]=pool[donor[ok]]
    cfg=load_arrays(folder/"features.npz")
    p,c=d["pose"],d["cue"]
    seeds={m:[] for m in ("full","pose","wrong","ridge_full","ridge_pose","ridge_wrong","frozen")}
    for seed in SEEDS:
        base=load_model(folder/f"pose_cue-{seed}.npz")
        body=body_forecast(p,c,base)
        seeds["frozen"].append(body)
        for arm in ("full","pose","wrong"):
            w_arm="full" if arm=="wrong" else arm
            weights_=load_arrays(folder/f"adapter-{w_arm}-{seed}.npz")
            x=design(p,c,wrong if arm=="wrong" else pool,cfg,w_arm)
            for family,prefix in (("mlp",""),("ridge","ridge_")):
                delta=residual(x,weights_,family).reshape(-1,10,8)*base["y_scale"]
                seeds[prefix+arm].append(body+delta)
    predictions={m:np.mean(arr,axis=0) for m,arr in seeds.items()}
    predictions.update({"seeds_"+m:np.stack(arr) for m,arr in seeds.items()})
    # Position persistence still needs a finite last observed coordinate on its native region.
    predictions["stationary"]=np.broadcast_to((p[:,-1:]*0),(len(p),10,8)).copy()
    predictions["velocity"]=(p[:,-1:]-p[:,-5:-4])/4*np.arange(1,11)[None,:,None]
    predictions["donor"]=donor
    for region in REGIONS:
        predictions["matched_"+region]=np.logical_and.reduce(
            [np.isfinite(errors(predictions[m],d["movement"],region)).all(axis=1) for m in ("full","pose","wrong")])
    return predictions


def read_block(path):
    with np.load(path,allow_pickle=False) as z:
        data={k:z[k] for k in ("block","workspace","original","ordinal","k","movement","pose","cue")}
        data["pooled"]=pooled_history(z["all_history"],z["all_guide"])
    return data


def refit(train, destination, bases):
    import shutil
    identity=hashlib.sha256()
    for key in ("block","workspace","original","ordinal","k","pose","cue","pooled","movement"):
        identity.update(key.encode())
        identity.update(train[key].astype("<f8").tobytes(order="C"))
    if identity.hexdigest()!="5afe805a90d0921194408d7531d44d7e41925e2a3858706d5e0e71750d2ff378":
        raise ValueError("Refit requires the registered September 7 training keys and values")
    if destination.exists():
        raise ValueError("Choose a new output directory")
    destination.mkdir(parents=True)
    torch_setup(1)
    w=weights(train["block"],train["original"])
    cfg=fit_design(train,np.arange(len(w)),w)
    np.savez_compressed(destination/"features.npz",**cfg)
    for seed in SEEDS:
        filename=f"pose_cue-{seed}.npz"
        shutil.copyfile(bases/filename,destination/filename)
        base=load_model(destination/filename)
        body=body_forecast(train["pose"],train["cue"],base)
        targets=((train["movement"]-body)/base["y_scale"]).reshape(-1,80)
        for arm in ("full","pose"):
            x=design(train["pose"],train["cue"],train["pooled"],cfg,arm)
            fitted,info,_=fit_adapter(x,targets,w,seed,"cpu",120)
            np.savez_compressed(destination/f"adapter-{arm}-{seed}.npz",**fitted)
            print(seed,arm,info)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    subs=cli.add_subparsers(dest="operation",required=True)
    f=subs.add_parser("refit")
    f.add_argument("train",type=Path)
    f.add_argument("destination",type=Path)
    f.add_argument("--bases", type=Path, default=WEIGHTS)
    e=subs.add_parser("score")
    e.add_argument("block1",type=Path)
    e.add_argument("block2",type=Path)
    e.add_argument("output",type=Path)
    e.add_argument("--weights",type=Path,default=WEIGHTS)
    args=cli.parse_args()
    if args.operation=="refit":
        refit(read_block(args.train),args.destination,args.bases)
    else:
        blocks=[read_block(path) for path in (args.block1,args.block2)]
        data={k:np.concatenate([b[k] for b in blocks]) for k in blocks[0]}
        expected=json.loads((Path(__file__).with_name("held-population.json")).read_text())
        if not all(np.array_equal(data[k],[r[i] for r in expected["windows"]])
                   for i,k in enumerate(("block","workspace","original","ordinal","k"))):
            raise ValueError("Held row keys differ from the fixed study population")
        pred=forecast_all(data,args.weights)
        result=score(data,pred,expected["roster"])
        upper=[reg["contrasts"]["full_minus_"+ctl]["moving"]["interval"]
               for ws in result["workspaces"].values()
               for name,reg in ws["regions"].items() if name in ("hand_mm","elbow_mm")
               for ctl in ("pose","wrong")]
        result["all_required_primary_intervals_below_zero"]=(
            all(ci[0][1]<0 for ci in upper) if all(ci is not None for ci in upper) else None)
        args.output.mkdir(parents=True,exist_ok=False)
        (args.output/"scores.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        roster=expected["roster"]
        ids={k:data[k] for k in ("block","workspace","original","ordinal","k")}
        ro={"roster_block":np.array([z["block"] for z in roster]),"roster_original":np.array([z["original"] for z in roster]),
            "roster_workspace":np.array([z["workspace"] or -1 for z in roster]),"roster_start":np.array([z["start"] for z in roster])}
        qc={"finite_pose_history":np.isfinite(data["pose"]).all(axis=(1,2)),"finite_cue_history":np.isfinite(data["cue"]).all(axis=(1,2)),
            "valid_count_history":np.isfinite(data["pooled"]).all(axis=(1,2))}
        for region,(a,b,_) in REGIONS.items():
            qc["valid_target_"+region]=np.isfinite(data["movement"][:,:,a:b]).all(axis=(1,2))
        np.savez_compressed(args.output/"predictions.npz",**ids,**ro,**qc,**pred,movement=data["movement"],seeds=np.array(SEEDS))


if __name__=="__main__":
    main()
