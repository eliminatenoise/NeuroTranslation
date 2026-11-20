"""Fit the frozen development design or score an independently accepted freeze."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from extract import read
from score import people_results, summarize

HERE = Path(__file__).resolve().parent
PROTOCOL_SHA = "0b4f133a5b469c436db52ee3a1fbf502be645e7cd582a6b7b7eb6cbc961008e5"
SOURCE = ("PROTOCOL.md","ofner_early.py","extract.py","predict.py","predict.js","fit.py","score.py","study.py")
PRODUCT = ("model.json","development.json","fit-diagnostics.json","fitting-source.json","example.json")


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,o):
    # Named outputs are immutable; use a fresh directory for another fit.
    with p.open("x",encoding="utf-8") as f:
        json.dump(o,f,allow_nan=False,separators=(",",":"))
        f.write("\n")


def train(cache,out,private,threads):
    import torch
    from fit import fit
    if digest(HERE/"PROTOCOL.md") != PROTOCOL_SHA:
        raise ValueError("The study protocol changed")
    for path in (out,private):
        path.mkdir(parents=True,exist_ok=True)
    if any((out/name).exists() for name in (*PRODUCT,"freeze.json")):
        raise FileExistsError("Use an unused output directory")
    if any((private/f"fold-S{i}.json").exists() for i in range(1,8)):
        raise FileExistsError("Use an unused private fold directory")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    rows,audit = read(cache,"fit")
    people = rows[-1][:,0]
    diagnostics,dev,foldhash = {},[],{}
    for i in range(1,8):
        keep = people!=i
        m,di = fit(tuple(x[keep] for x in rows))
        diag_key = f"fold-S{i}"
        diagnostics[diag_key] = di
        dest = private/(diag_key+".json")
        save(dest,m)
        foldhash[diag_key] = digest(dest)
        dev.extend(people_results(m,tuple(x[~keep] for x in rows)))
        print("Completed leave-one-person-out fold",i,flush=True)
    model,diagnostics["all_seven"] = fit(rows)
    model.update({"protocol_sha256":PROTOCOL_SHA,"source_doi":"10.5281/zenodo.834976",
                  "fitting_people":list(range(1,8)),"fitting_trials":len(people)})
    save(out/"model.json",model)
    save(out/"development.json",summarize(dev,False))
    save(out/"fit-diagnostics.json",diagnostics)
    save(out/"fitting-source.json",audit)
    example = {"cue":"elbow flexion","method":"scalp",
               "history":[[6,2,1,0,0,0],[6,2,1,0,0,0],[6.1,2,1,0.1,0,0],[6.4,2.1,1,0.2,0.1,0]],
               "scalp":[[2,0,1,4,-1,3],[2.2,0,1.4,4,-1,3.1],[3.5,1,2.4,4.2,0,4],[3,1.1,4,3.9,0.3,4]],
               "eye":[[0,1,0],[0,1.1,0],[1.2,2.1,0.2],[1.4,2.4,0.4]]}
    save(out/"example.json",example)
    freeze = {"format":"early-scalp-freeze-v1","source":{n:digest(HERE/n) for n in SOURCE},
              "product":{n:digest(out/n) for n in PRODUCT},"fold_sha256":foldhash,
              "fit_roster":"S1–S7, execution runs 1–3","assessment_roster":"S8–S12, execution run 4",
              "environment":{"numpy":np.__version__,"torch":str(torch.__version__),"device":"cpu",
                             "threads":torch.get_num_threads(),"interop":torch.get_num_interop_threads()}}
    save(out/"freeze.json",freeze)
    print("Frozen model and scoring package SHA-256",digest(out/"freeze.json"),flush=True)


def assess(cache,freeze,expected,out):
    if out.exists():
        raise FileExistsError("Use a fresh assessment report destination")
    if digest(freeze)!=expected:
        raise ValueError("Freeze differs from the independently retained hash")
    f = json.loads(freeze.read_text())
    for base,key,names in ((HERE,"source",SOURCE),(freeze.parent,"product",PRODUCT)):
        if set(f[key])!=set(names) or any(digest(base/n)!=f[key][n] for n in names):
            raise ValueError("Scientific code or products differ from the freeze")
    m = json.loads((freeze.parent/"model.json").read_text())
    rows,audit = read(cache,"assessment")
    report = summarize(people_results(m,rows),True)
    report.update({"freeze_sha256":expected,"model_sha256":f["product"]["model.json"],
                   "source":audit})
    save(out,report)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="which",required=True)
    t = sub.add_parser("train")
    for key in ("cache","output","folds"):
        t.add_argument(key,type=Path)
    t.add_argument("--threads",type=int,default=2)
    a = sub.add_parser("assess")
    a.add_argument("cache",type=Path)
    a.add_argument("freeze",type=Path)
    a.add_argument("expected")
    a.add_argument("output",type=Path)
    opt = p.parse_args()
    if opt.which=="train":
        train(opt.cache,opt.output,opt.folds,opt.threads)
    else:
        assess(opt.cache,opt.freeze,opt.expected,opt.output)
