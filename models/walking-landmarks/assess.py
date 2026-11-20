"""Score the sealed fit. Comparisons use the same finite marker targets for both methods."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from predict import MARKERS, MODELS, load_weights, run_tokens, standardize

HERE = Path(__file__).resolve().parent
SEED = 20261121


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(values, axis=0):
    vals = np.asarray(values)
    good = np.isfinite(vals)
    n = good.sum(axis=axis)
    return np.divide(np.where(good,vals,0).sum(axis=axis),n,out=np.full(np.shape(n),np.nan),where=n>0)


def subject_results(errors, people):
    rows = []
    for person in np.unique(people):
        rows.append(summarize(errors[person==people],axis=0))
    return np.stack(rows)


def interval(vals):
    x = np.asarray(vals)
    x = x[np.isfinite(x)]
    if not len(x):
        return [None,None]
    ix = np.random.default_rng(SEED).integers(0,len(x),size=(10000,len(x)))
    return np.percentile(x[ix].mean(axis=1),[2.5,97.5]).tolist()


def describe(errors, data):
    people, repeats = data["person"], data["repeat"]
    good = np.isfinite(errors)
    by_person = subject_results(errors,people)
    macro = summarize(by_person,axis=1)
    ids = np.unique(people)
    def counts(use):
        return dict(people=len(set(people[use])),trials=len(set(zip(people[use],repeats[use]))),
                    cutoffs=int(use.sum()))
    return {
        "mean_mm":float(summarize(macro)), "ci95_mm":interval(macro),
        "coverage":dict(**counts(good.any(axis=1)),landmark_targets=int(good.sum())),
        "by_landmark":{key:dict(mean_mm=float(summarize(by_person[:,j])),
                                ci95_mm=interval(by_person[:,j]), **counts(good[:,j]))
                       for j,key in enumerate(MARKERS[:6])},
        "by_walker":[{"walker":int(who)-30,"mean_mm":float(macro[i]),"cutoffs":int(good[people==who].any(1).sum()),
                      "by_landmark_mm":by_person[i].tolist(),"landmark_targets":good[people==who].sum(0).tolist()}
                     for i,who in enumerate(ids)]}


def comparison(err_a,err_b, data):
    difference = err_a-err_b
    rep = describe(difference,data)
    x = np.array([v["mean_mm"] for v in rep["by_walker"]])
    x = x[np.isfinite(x)]
    rep["walkers_improved"] = int((x<0).sum())
    rep["walkers_compared"] = len(x)
    rep["passes"] = bool(len(x) and rep["mean_mm"]<0 and rep["ci95_mm"][1]<0 and (x<0).mean()>=.7)
    return rep


def controls(data, w, phase):
    features, y, people, trial, anchor = (data[k] for k in ("x","y","person","repeat","anchor"))
    by_event = [phase.get(f"{p}.{t}",phase.get(p,phase["global"])) for p,t in zip(data["phase"],data["phase_bin"])]
    predicted_phase = np.array(by_event).reshape(-1,6,3)
    personal = np.full_like(y,np.nan)
    wrong = np.full_like(y,np.nan)
    history = standardize(features,w,"markers")[:,-2:].reshape(len(y),-1)
    later = np.zeros(len(y),bool)
    for who in np.unique(people):
        repeats = np.unique(trial[people==who])
        for before,now in zip(repeats[:-1],repeats[1:]):
            src = np.flatnonzero((people==who)&(trial==before))
            ix = np.flatnonzero((people==who)&(trial==now))
            later[ix] = True
            donor = np.abs(anchor[ix,None]-anchor[src][None]).argmin(axis=1)
            swapped = features[ix].copy()
            swapped[:,:,64:] = features[src[donor],:,64:]
            wrong[ix] = run_tokens(swapped,w,"transformer_combined")
            distance = np.sqrt(np.mean((history[ix,None]-history[src][None])**2,axis=-1))
            for j, sample in enumerate(ix):
                top = np.argsort(distance[j],kind="stable")[:3]
                observed = y[src[top]]
                wt = 1/(.01+distance[j,top,None,None])
                finite = np.isfinite(observed).all(axis=-1,keepdims=True)
                total = np.sum(wt*finite,axis=0)
                personal[sample] = np.divide((np.where(finite,observed,0)*wt).sum(axis=0),total,
                                             out=np.full((6,3),np.nan),where=total>0)
    return {"phase":predicted_phase,"wrong_emg":wrong,"personal":personal},later


def distribution(values):
    x = np.ravel(values)
    x = x[np.isfinite(x)]
    if not len(x):
        return {"count":0}
    return dict(count=int(len(x)),mean_mm=float(x.mean()),sd_mm=float(x.std(ddof=1)) if len(x)>1 else None,
                min_mm=float(x.min()),p10_mm=float(np.percentile(x,10)),median_mm=float(np.median(x)),
                p90_mm=float(np.percentile(x,90)),max_mm=float(x.max()))


def assessment(data, w, phase):
    if set(data["person"])!=set(range(31,41)):
        raise ValueError("Expected exactly the ten assessment participants.")
    predictions = {name:run_tokens(data["x"],w,name) for name in MODELS}
    others,later = controls(data,w,phase)
    predictions.update(others)
    magnitude = np.linalg.norm(data["y"],axis=2)
    errors = {name:np.linalg.norm(pred-data["y"],axis=2) for name,pred in predictions.items()}
    all_models = {name:describe(value,data) for name,value in errors.items() if name not in ("wrong_emg","personal")}
    masked = {name:np.where(later[:,None],err,np.nan) for name,err in errors.items()}
    later_models = {name:describe(err,data) for name,err in masked.items()}
    control_names = ("ridge_markers","ridge_combined","persistence","velocity","phase","personal")
    contrasts = {name:comparison(errors["transformer_combined"],errors[name],data)
                 for name in ("transformer_markers","wrong_emg",*control_names)}
    counts = {"planned_people":10,"planned_trials":30,"scored_cutoffs":int(np.isfinite(magnitude).any(1).sum()),
              "possible_cutoffs":len(later),"later_repeat_cutoffs":int(later.sum()),
              "valid_landmark_targets":np.isfinite(magnitude).sum(0).tolist(),
              "emg_valid_tokens_by_channel":np.isfinite(data["x"][:,:,64:72]).sum(axis=(0,1)).tolist(),
              "emg_total_tokens_per_channel":int(len(later)*8),
              "zero_finite_rms_tokens_by_channel":(data["x"][:,:,64:72]==0).sum(axis=(0,1)).tolist(),
              "trials_by_walker":[]}
    for who in np.unique(data["person"]):
        trials = []
        for r in np.unique(data["repeat"][data["person"]==who]):
            ids = np.flatnonzero((data["person"]==who)&(data["repeat"]==r))
            trials.append(dict(repeat=int(r),frames=int(data["record_frames"][ids[0]]),possible_cutoffs=len(ids),
                               valid_landmark_targets=np.isfinite(magnitude[ids]).sum(0).tolist()))
        counts["trials_by_walker"].append({"walker":int(who)-30,"trials":trials})
    return {"clock":"20 stored 100 Hz frames; 200 ms; laboratory XYZ millimetres","landmarks":list(MARKERS[:6]),
            "coverage":counts,"target_displacement_magnitude":{"pooled":distribution(magnitude),
                    "by_landmark":{m:distribution(magnitude[:,i]) for i,m in enumerate(MARKERS[:6])},
                    "by_walker":[{"walker":int(p)-30,**distribution(magnitude[data["person"]==p])} for p in np.unique(data["person"])]},
            "all_anchors":all_models,"later_repeat_anchors":later_models,
            "combined_transformer_minus_comparator":contrasts,
            "gates":{"incremental_emg":all(contrasts[k]["passes"] for k in ("transformer_markers","wrong_emg")),
                     "transformer_advantage":all(contrasts[k]["passes"] for k in control_names)}}


def finite_json(value):
    if isinstance(value,dict):
        return {k:finite_json(v) for k,v in value.items()}
    if isinstance(value,list):
        return [finite_json(x) for x in value]
    if isinstance(value,float) and not np.isfinite(value):
        return None
    return value


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("assessment",type=Path)
    p.add_argument("model_dir",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    seal=json.loads((a.model_dir/"fit-seal.json").read_bytes())
    for name,field in (("weights.npz","weights_sha256"),("phase.json","phase_sha256")):
        if sha(a.model_dir/name)!=seal[field]:
            raise ValueError("Model changed after fitting")
    with np.load(a.assessment,allow_pickle=False) as pack:
        result=assessment(dict(pack),load_weights(a.model_dir/"weights.npz"),json.loads((a.model_dir/"phase.json").read_bytes()))
    a.output.write_text(json.dumps(finite_json(result),indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v["mean_mm"] for k,v in result["all_anchors"].items()},indent=2))
    print(result["gates"])
