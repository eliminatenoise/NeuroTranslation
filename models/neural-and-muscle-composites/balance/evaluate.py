"""Evaluate frozen weights on the historical comparison group, publishing aggregates only."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter_ns

import numpy as np
import torch

from model import BASES, Fusion, PROTOCOL, decode, load, mapped

METRICS = ("muscle_mae_uV", "path_error_mm", "endpoint_error_mm")
PARTS = {"both":(0,1),"standing":(0,),"walking":(1,)}
SEEDS = PROTOCOL["fit"]["seeds"]


def earlier_donors(a):
    last = {}
    out = np.full(len(a["event"]),-1,dtype=int)
    for i in np.argsort(a["cutoff"], kind="stable"):
        key = (a["person"][i], int(a["posture"][i]), int(a["direction"][i]), int(a["block"][i]),
               tuple(a["present"][i]))
        group = last.setdefault(key, [])
        for j in reversed(group):
            if a["cutoff"][j]+71 < a["cutoff"][i]-198:
                out[i] = j
                break
        group.append(i)
    return out


def errors(a, emg, path):
    err = np.linalg.norm(path-a["y_path"],axis=2)
    return np.column_stack((abs(emg-a["y_leg"]).mean(axis=1),err.mean(axis=1),err[:,-1]))


def people_means(a, loss, mask, postures):
    rows = []
    for person in np.unique(a["person"]):
        cells = []
        for posture in postures:
            for direction in (-1,1):
                keep = mask & (a["person"]==person) & (a["posture"]==posture) & (a["direction"]==direction)
                if not keep.any():
                    raise ValueError("empty required person and condition cell")
                cells.append(loss[keep].mean(axis=0))
        rows.append(np.mean(cells,axis=0))
    return np.stack(rows)


def native_metrics(x):
    return dict(zip(METRICS, x.tolist(), strict=True))


def support(a, mask):
    return {"people":int(len(np.unique(a["person"][mask]))), "events":int(mask.sum()),
            "standing":int((mask & (a["posture"] == 0)).sum()),
            "walking":int((mask & (a["posture"] == 1)).sum())}


def comparison(a, loss, other, mask):
    left = people_means(a,loss,mask,(0,1))
    right = people_means(a,other,mask,(0,1))
    delta = left-right
    rng = np.random.default_rng(431)
    ix = rng.integers(0,len(delta),size=(10000,len(delta)))
    boot = delta[ix].mean(axis=1)
    return {"support":support(a,mask),"aligned_paired":native_metrics(left.mean(axis=0)),
            "comparator":native_metrics(right.mean(axis=0)), "paired_minus_comparator":native_metrics(delta.mean(axis=0)),
            "ci95_low":native_metrics(np.quantile(boot,.025,axis=0)),
            "ci95_high":native_metrics(np.quantile(boot,.975,axis=0)),
            "upper_98_75":native_metrics(np.quantile(boot,.9875,axis=0)),
            "people_lower_with_paired":native_metrics((delta<0).sum(axis=0))}


def timing(net, xs, n=150):
    result={}
    for size in (1,128):
        batch=[x[:size] for x in xs]
        for _ in range(12):
            net(batch)
        elapsed=[]
        for _ in range(n):
            start=perf_counter_ns()
            net(batch)
            elapsed.append((perf_counter_ns()-start)/1e6)
        result[str(size)]={"median_ms":float(np.median(elapsed)),"p95_ms":float(np.quantile(elapsed,.95)),
                           "iterations":n}
    return result


def evaluate(a, weights):
    if len(set(a["person"])) != 6:
        raise ValueError("expected historical comparison cohort")
    xs=mapped(a,weights,"cpu")
    donors=earlier_donors(a)
    good=donors>=0
    used=np.where(good,donors,np.arange(len(donors)))
    mismatch={"wrong_electrical":(0,1),"wrong_mechanics":(2,3),"wrong_scalp":(0,)}
    all_rows=np.ones(len(good),dtype=bool)
    all_loss={}
    speed={}
    for name in BASES:
        model=Fusion(name).eval()
        for seed in SEEDS:
            prefix=f"{name}_{seed}/"
            model.load_state_dict({k[len(prefix):]:torch.from_numpy(v) for k,v in weights.items() if k.startswith(prefix)})
            with torch.inference_mode():
                pred=model(xs).numpy()
                all_loss.setdefault(name,[]).append(errors(a,*decode(pred,weights)))
                if name=="paired":
                    for control, streams in mismatch.items():
                        swapped=[x[used] if i in streams else x for i,x in enumerate(xs)]
                        pred=model(swapped).numpy()
                        all_loss.setdefault(control,[]).append(errors(a,*decode(pred,weights)))
                if seed==SEEDS[0] and name in ("paired","early","crossed"):
                    speed[name]=timing(model,xs)
    constant_velocity=a["physics"][:,2:3] * np.arange(1,33)[None,:,None]/32
    for name, path in (("stationary",np.zeros_like(a["y_path"])),("velocity32",constant_velocity)):
        all_loss[name]=[errors(a,a["previous_rms"],path)]
    averages={k:np.mean(loss,axis=0) for k,loss in all_loss.items()}
    strata={"all":support(a,all_rows),"valid_donor":support(a,good)}
    def means(loss,mask,h):
        return native_metrics(people_means(a,loss,mask,h).mean(axis=0))
    modes={}
    for name,loss in averages.items():
        mask=good if name in mismatch else all_rows
        modes[name]={"support":support(a,mask), **{part:means(loss,mask,h) for part,h in PARTS.items()}}
        if name in ("paired","early","crossed"):
            modes[name]["per_seed_both"]={str(seed):means(err,mask,(0,1))
                                         for seed,err in zip(SEEDS,all_loss[name],strict=True)}
    contrasts={name:comparison(a,averages["paired"],loss,good if name in mismatch else all_rows)
               for name,loss in averages.items() if name!="paired"}
    passed=all(contrasts[other]["paired_minus_comparator"][m] < 0 and contrasts[other]["upper_98_75"][m] < 0
               for other in ("early","crossed") for m in METRICS[:2])
    return {"source":"OpenNeuro ds003739 1.0.3, historical whole-person comparison",
            "scalp_sites_present_events":dict(zip(("D19","A1","B22"),a["present"].sum(axis=0).tolist())),
            "outcomes":list(METRICS),"seeds":SEEDS,"coverage":strata,"scores":modes,
            "comparisons":contrasts,"paired_superiority_passed":bool(passed)}, speed


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("assessment",type=Path)
    p.add_argument("weights",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("timings",type=Path)
    args=p.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    result, timing_rows=evaluate(load(args.assessment),load(args.weights))
    for obj,dest in [(result,args.output),(timing_rows,args.timings)]:
        dest.write_text(json.dumps(obj,allow_nan=False,indent=2)+"\n")
