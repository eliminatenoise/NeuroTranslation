"""Fit or evaluate the single-marker rule using the fixed walking roster."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zlib

import ezc3d
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import point_motion as pm
import predict

PARENT = "a52af3c0875a43d3ce8ae70ae7eaa8cf83a9bcd4f75422f1cc84bea6fd8379ee"
PROTOCOL = "a133714951379dc5e14b6ea17c430bcc62e75ea509ce01d5e6b9be6afe697fd3"
SITES = list(json.loads((HERE / "landmarks.json").read_text()))
FIT = {side + "_" + site for side in ("L", "R") for site in ("FAL", "FLE", "RSP")}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(directory, partition):
    paths = sorted(directory.glob("*.c3d"))
    roster = [[p.name, p.stat().st_size, f"{zlib.crc32(p.read_bytes()):08x}"] for p in paths]
    digest = hashlib.sha256(json.dumps(roster, separators=(",", ":")).encode()).hexdigest()
    pin = json.loads((HERE / "source-checks.json").read_bytes())[partition]["roster_and_source_crc_sha256"]
    if digest != pin:
        raise ValueError("Walking files do not match the study roster.")
    people = sorted({p.name.split("_")[0] for p in paths})
    sites = [s for s in SITES if s in FIT or partition == "assessment"]
    x, target, keys = [], [], []
    for trial, path in enumerate(paths):
        c = ezc3d.c3d(str(path))
        point = c["parameters"]["POINT"]
        if point["RATE"]["value"][0] != 100 or point["UNITS"]["value"] != ["mm"]:
            raise ValueError("Expected 100 Hz and millimetres.")
        labels = [s.strip() for s in point["LABELS"]["value"]]
        if len(labels) != len(set(labels)):
            raise ValueError("Ambiguous marker labels.")
        xyz = c["data"]["points"][:3].transpose(2,1,0)
        residual = c["data"]["meta_points"]["residuals"][0].T
        cutoff = np.arange(40,len(xyz)-20,10)
        sample = cutoff[:,None]+np.arange(-40,1,5)
        who = people.index(path.name.split("_")[0])
        for site in sites:
            if site not in labels:
                continue
            index = labels.index(site)
            p = xyz[:,index]
            valid = np.isfinite(p).all(axis=1) & np.any(p != 0,axis=1) & (residual[:,index]>=0)
            keep = valid[sample].all(axis=1) & valid[cutoff+20]
            if not keep.any():
                continue
            t = cutoff[keep]
            x.append(p[sample[keep]])
            target.append(p[t+20]-p[t])
            keys.extend((who, SITES.index(site), trial) for _ in t)
    return np.concatenate(x), np.concatenate(target), np.asarray(keys)


def balance(keys):
    # Equal windows within trial, trials within site, sites within person, people overall.
    people = np.unique(keys[:,0])
    person_site = np.unique(keys[:,:2],axis=0)
    groups, row, windows = np.unique(keys,axis=0,return_inverse=True,return_counts=True)
    weights = np.ones(len(groups))
    for i,(p,s,_) in enumerate(groups):
        n_sites = np.count_nonzero(person_site[:,0]==p)
        n_trials = np.count_nonzero((groups[:,0]==p) & (groups[:,1]==s))
        weights[i] /= len(people)*n_sites*n_trials*windows[i]
    return weights[row]


def scales(x, sample_weight):
    mu = np.average(x,axis=0,weights=sample_weight)
    sd = np.sqrt(np.average((x-mu)**2,axis=0,weights=sample_weight))
    return mu, np.where(sd < 1e-6,1,sd)


def fit(directory, parent, output):
    if sha(parent)!=PARENT:
        raise ValueError("Wrong parent checkpoint.")
    x,y,keys = load(directory,"train")
    ww = balance(keys)
    with np.load(parent,allow_pickle=False) as z:
        stored = {k:z[k] for k in z.files}
    cfg,w = predict.read_checkpoint(parent)
    tokens,heading = pm.coordinates(x)
    residual = pm.transform(y-pm.batch("velocity",x,cfg,w,predict.linear,predict.encode),heading)
    raw = tokens.reshape(-1,24)
    w["point_motion.raw.mean"],w["point_motion.raw.scale"] = scales(raw,ww)
    w["point_motion.token.mean"],w["point_motion.token.scale"] = scales(tokens.reshape(-1,6),np.repeat(ww/4,4))
    choice = np.random.default_rng(3692).choice(len(x),64,replace=False,p=ww/ww.sum())
    centers = pm.normalize(raw,w,"point_motion.raw")[choice]
    dist = np.sum((centers[:,None]-centers[None,:])**2,axis=2)
    w["point_motion.centres"] = centers
    w["point_motion.bandwidth2"] = np.median(dist[dist>0])
    for mode in pm.LEARNED:
        design = pm.features(mode,tokens,cfg,w,predict.linear,predict.encode)
        stem = "point_motion."+mode
        w[stem+".mean"],w[stem+".scale"] = scales(design,ww)
        A=pm.normalize(design,w,stem)
        bias=np.average(residual,axis=0,weights=ww)
        w[stem+".coef"] = np.linalg.solve(A.T@(ww[:,None]*A)+.01*np.eye(A.shape[1]), A.T@(ww[:,None]*(residual-bias)))
        w[stem+".bias"] = bias
    cfg["point_motion"]={"format":1,"sites_fitted":sorted(FIT),"training_people":len(np.unique(keys[:,0])),
                         "training_walks":len(np.unique(keys[:,2])),"training_marker_windows":len(x),
                         "modes":list(pm.MODES),"lead_ms":200,"source_protocol":PROTOCOL}
    stored["configuration"] = np.array(json.dumps(cfg))
    stored.update({k:v for k,v in w.items() if k.startswith("point_motion.")})
    np.savez_compressed(output,**stored)
    print(json.dumps({"fit":cfg["point_motion"],"checkpoint":sha(output)},indent=2))


def predict_rows(mode,x,cfg,w):
    return np.concatenate([pm.batch(mode,chunk,cfg,w,predict.linear,predict.encode)
                           for chunk in np.array_split(x,max(1,(len(x)+511)//512))])


def metrics(errors,keys):
    weights = balance(keys)
    return {"endpoint_error_mm":float(weights@np.linalg.norm(errors,axis=1)),
            "signed_lab_xyz_mm":(weights@errors).tolist()}


def coverage(keys):
    return {"people":len(np.unique(keys[:,0])),"trials":len(np.unique(keys[:,2])),
            "sites":len(np.unique(keys[:,1])),"marker_windows":len(keys)}


def assess(directory,checkpoint,output):
    fit_seal=json.loads((HERE/"fit.json").read_bytes())
    if sha(checkpoint)!=fit_seal["checkpoint"] or fit_seal["fit"]["source_protocol"]!=PROTOCOL:
        raise ValueError("Verify the original full fit before assessing. Use one BLAS thread for reproduction.")
    cfg,w=predict.read_checkpoint(checkpoint)
    if cfg.get("point_motion",{}).get("source_protocol")!=PROTOCOL:
        raise ValueError("Checkpoint was not fitted under the registered protocol.")
    x,y,keys=load(directory,"assessment")
    errors={mode:predict_rows(mode,x,cfg,w)-y for mode in pm.MODES}
    report={"checkpoint_sha256":sha(checkpoint),"protocol_sha256":PROTOCOL,"training":cfg["point_motion"],
            "training_sites":sorted(FIT),"assessment_sites":SITES,"horizon_ms":200,"groups":{}}
    trained=np.isin(keys[:,1],[SITES.index(s) for s in FIT])
    for name,mask in (("other_46",~trained),("fit_6",trained)):
        sub=keys[mask]
        entry={"coverage":coverage(sub),"modes":{},"per_site":{},"per_person":{},"contrasts":{}}
        scores={}
        for mode,all_err in errors.items():
            err=all_err[mask]
            entry["modes"][mode]=metrics(err,sub)
            scores[mode]=[]
            for p in sorted(set(sub[:,0])):
                sel=sub[:,0]==p; pid=f"assessment-{p+1:02d}"
                row=entry["per_person"].setdefault(pid,{"coverage":coverage(sub[sel])})
                value=metrics(err[sel],sub[sel])["endpoint_error_mm"]
                row[mode]=value;scores[mode].append(value)
            for site in np.unique(sub[:,1]):
                sel=sub[:,1]==site
                row=entry["per_site"].setdefault(SITES[site],{"coverage":coverage(sub[sel])})
                row[mode]=metrics(err[sel],sub[sel])["endpoint_error_mm"]
        size=len(scores["shared"])
        indices=np.random.default_rng(3693).integers(size,size=(10000,size))
        gate=size>=8
        for control in ("velocity","previous","linear","radial","shuffled"):
            delta=np.asarray(scores["shared"])-scores[control]
            interval=np.quantile(delta[indices].mean(axis=1),[.025,.975])
            change=float(delta.mean()/np.mean(scores[control]))
            entry["contrasts"][control]={"shared_minus_control_mm":float(delta.mean()),"relative_change":change,
                                          "interval95_mm":interval.tolist(),"walkers_improved":int((delta<0).sum())}
            gate=gate and change<=-.05 and interval[1]<0
        entry["walker_error_quartiles_mm"]={mode:np.quantile(values,[.25,.5,.75]).tolist() for mode,values in scores.items()}
        del entry["per_person"]
        entry["advantage_gate"]=bool(gate)
        report["groups"][name]=entry
        print(name,entry["coverage"],{m:round(r["endpoint_error_mm"],2) for m,r in entry["modes"].items()},bool(gate))
    report["overall_advantage_gate"]=all(v["advantage_gate"] for v in report["groups"].values())
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["fit","assess"])
    for key in ("source_dir","checkpoint","output"):
        parser.add_argument(key,type=Path)
    args=parser.parse_args()
    if sha(HERE/"PROTOCOL.md")!=PROTOCOL or args.checkpoint.resolve()==args.output.resolve():
        parser.error("Use the registered protocol and a separate output path.")
    (fit if args.action=="fit" else assess)(args.source_dir,args.checkpoint,args.output)
