"""Aggregate the held-day scores, respecting original trial and recording block."""
import argparse
import json
from pathlib import Path

import numpy as np

ARCH = ["ar","diffusion","hybrid"]
SEEDS = [17,41,73]
METRICS = ["primary","crps","coverage","width"]


def combine(directory):
    store = []
    for block in ("block1","block2"):
        with np.load(directory/(block+"-scores.npz"), allow_pickle=False) as f:
            store.append({k:f[k] for k in f.files})
    assert store[0].keys() == store[1].keys()
    return {k:np.concatenate([s[k] for s in store]) for k in store[0]}


def by_original(values, ids, n):
    counts = np.bincount(ids, minlength=n)
    ans = np.stack([np.bincount(ids,weights=values[:,i],minlength=n)/np.maximum(counts,1)
                    for i in range(values.shape[-1])],axis=1)
    return ans[counts>0],counts>0


def flatten_scores(x):
    return {"mean":float(x.mean()),"by_horizon":x.mean(0).tolist()}


def summarize(data):
    group, ids = np.unique(np.column_stack([data["block"],data["workspace"],data["original"]]), axis=0,return_inverse=True)
    strata = {"all":np.ones(len(group),dtype=bool)}
    for b,ws in np.unique(group[:,:2],axis=0):
        strata[f"block{b}-workspace{ws}"] = (group[:,0]==b) & (group[:,1]==ws)
    output = {"held_day":"2017-09-14","counts":{k:{"originals":int(v.sum()),"windows":int(v[ids].sum())} for k,v in strata.items()},"tasks":{}}
    def stat(loss):
        valid = np.isfinite(loss).all(axis=1)
        grouped, keep = by_original(loss[valid],ids[valid],len(group))
        return {key:flatten_scores(grouped[mask[keep]]) for key,mask in strata.items()}

    def contrast(a,b):
        delta = a-b
        valid = np.isfinite(delta).all(axis=1)
        grouped,keep = by_original(delta[valid],ids[valid],len(group))
        loss = grouped.mean(axis=1)
        held_groups = group[keep]
        rng = np.random.default_rng(371081)
        sums = np.zeros(2000)
        for block,ws in np.unique(held_groups[:,:2],axis=0):
            subset = loss[(held_groups[:,0]==block)&(held_groups[:,1]==ws)]
            draws = rng.integers(len(subset),size=(len(sums),len(subset)))
            sums += subset[draws].sum(axis=1)
        interval = np.quantile(sums/len(loss),[.025,.975])
        return dict(delta=float(loss.mean()),ci95_conditional=interval.tolist(),matched_windows=int(valid.sum()),matched_originals=int(len(loss)))

    winners = set(ARCH)
    for task in ("movement","neural"):
        base = ["mean","persistence","ridge"] + (["velocity"] if task=="movement" else [])
        results = {"systems":{},"full_by_seed":{},"contrasts":{}}
        primary = {}
        for name in base:
            primary[name] = data[f"{task}/{name}/primary"]
            results["systems"][name] = {"primary":stat(primary[name])}
        for arch in ARCH:
            results["full_by_seed"][arch] = {str(s):stat(data[f"{task}/{arch}/{s}/both/primary"])["all"]["mean"] for s in SEEDS}
            for cond in ("both","pose","spikes","wrong"):
                name = arch if cond=="both" else arch+"-"+cond
                result = {}
                for metric in METRICS:
                    rows = np.stack([data[f"{task}/{arch}/{s}/{cond}/{metric}"] for s in SEEDS]).mean(axis=0)
                    if metric=="primary":
                        primary[name] = rows
                    result[metric] = stat(rows)
                results["systems"][name] = result
        for arch in ARCH:
            for other in [a for a in ARCH if a!=arch]+base+[arch+"-"+c for c in ("pose","spikes","wrong")]:
                result = contrast(primary[arch],primary[other])
                results["contrasts"][arch+" minus "+other] = result
                if other in ARCH+base and result["ci95_conditional"][1]>=0:
                    winners.discard(arch)
        if task=="neural":
            for system in results["systems"].values():
                system["rmse_counts"] = {scope:float(np.sqrt(row["mean"])) for scope,row in system["primary"].items()}
        output["tasks"][task] = results
    output["unique_bidirectional_winner"] = sorted(winners)
    return output


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scores",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=summarize(combine(args.scores))
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
