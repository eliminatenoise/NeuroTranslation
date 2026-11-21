"""Score a completed prediction archive. No fitting or model selection."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from forecaster import METHODS, norms
from study import STRESS, digest, load, records, save


def summarize(summary):
    n, raw, scaled, cover, count, possible, interval_n = summary
    return {"matched_points":int(n), "scored_forecasts":int(count),"available_target_points":int(possible),
            "mean_raw": (raw/n).tolist() if n else None,
            "mean_normalized":(scaled/n).tolist() if n else None,
            "interval_points":int(interval_n),
            "trained_90pct_radius_coverage":(cover/interval_n).tolist() if interval_n else None}


def accumulator():
    return [0,np.zeros(len(METHODS)),np.zeros(len(METHODS)),np.zeros(2),0,0,0]


def add(total, partial):
    for i, value in enumerate(partial):
        total[i] += value


def score(args):
    archive = json.loads((args.pred/"predictions.json").read_text())
    frozen = json.loads((args.fit/"freeze.json").read_text())
    if digest(args.fit/"freeze.json") != archive["freeze"] or archive["manifest"] != digest(args.manifest):
        raise ValueError("Prediction archive no longer matches source or fit")
    rows = {r["id"]:r for r in records(args.manifest,"test",args.mixed)}
    if {r["id"] for r in archive["tracks"]} != set(rows):
        raise ValueError("Archive track inventory incomplete")
    radii = np.asarray([frozen["radii_q90"][m] for m in METHODS[:2]])
    totals = defaultdict(accumulator)
    metadata, timing = {}, defaultdict(list)
    for info in archive["tracks"]:
        row = rows[info["id"]]
        if digest(row["file"]) != info["source_sha256"] or digest(args.pred/info["file"]) != info["sha256"]:
            raise ValueError("Changed source or saved forecast")
        xy,t = load(row)
        name = info["group"]
        metadata[name] = {"taxon":info["phylum"],"species":info["species"],"units":info["units"],
                          "horizon_s":info["nominal_s"]}
        with np.load(args.pred/info["file"],allow_pickle=False) as data:
            pairs,pred,all_scale = data["pairs"],data["pred"],data["radius"]
            scale = all_scale[:,0]
            timing[name].append({"track":info["id"],"K":xy.shape[1],"origins":len(pairs),
                 "first_wait_s": data["first_wait_s"].tolist(),
                 "first_span_s": data["history_s"][:1].tolist(),
                 "horizon_range_s":[float(a(data["horizon_s"])) for a in (min,max)] if len(pairs) else None,
                 "history_range_s":[float(a(data["history_s"])) for a in (min,max)] if len(pairs) else None})
            for n, (_,e) in enumerate(pairs):
                endpoint = xy[e]
                target_exists = np.isfinite(endpoint).all(1)
                for s, condition in enumerate(STRESS):
                    err = norms(pred[n,s]-endpoint[None,:,:])
                    ok = np.isfinite(err).all(0) & np.isfinite(scale[n]) & (scale[n] > 0.)
                    d = err[:,ok]
                    norm = d/scale[n] if ok.any() else d
                    interval_ok = np.isfinite(all_scale[n,s]) and all_scale[n,s] > 0.
                    covered = (d[:2]<=radii[:,None]*all_scale[n,s]).sum(1) if interval_ok else np.zeros(2)
                    part = [len(d.T),d.sum(1),norm.sum(1),covered,int(ok.any()),int(target_exists.sum()),
                            int(ok.sum()) if interval_ok else 0]
                    for phase in ("all", "first" if n == 0 else "later"):
                        add(totals[(name,condition,phase)],part)
    out = []
    for (g,cond,phase),total in sorted(totals.items()):
        out.append(dict(group=g,condition=cond,phase=phase,**metadata[g],**summarize(total)))
    aggregates = []
    for horizon in sorted({m["horizon_s"] for m in metadata.values()}):
        for condition in STRESS:
            for phase in ("all","first","later"):
                included = [r for r in out if r["horizon_s"]==horizon and r["condition"]==condition
                            and r["phase"]==phase and r["matched_points"]]
                if not included:
                    continue
                groups = np.asarray([r["mean_normalized"] for r in included])
                pooled = np.average(groups,axis=0,weights=[r["matched_points"] for r in included])
                by_taxon = {taxon:np.mean([r["mean_normalized"] for r in included if r["taxon"]==taxon],axis=0).tolist()
                            for taxon in sorted({r["taxon"] for r in included})}
                aggregates.append({"horizon_s":horizon,"condition":condition,"phase":phase,
                    "n_groups":len(groups),"n_points":sum(r["matched_points"] for r in included),
                    "group_mean":groups.mean(0).tolist(),"pooled":pooled.tolist(),
                    "worst_group_each_method":groups.max(0).tolist(),"by_phylum":by_taxon,
                    "phylum_mean":np.mean(list(by_taxon.values()),axis=0).tolist()})
    save(args.out,{"methods":METHODS,"coverage_methods":METHODS[:2],"groups":out,"summary":aggregates,
                   "timing_by_group":timing,"prediction_archive_sha256":digest(args.pred/"predictions.json")})


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("manifest","fit","pred","out"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--mixed",type=Path)
    score(parser.parse_args())
