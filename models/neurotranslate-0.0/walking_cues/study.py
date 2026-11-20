"""Fit development models or score the fixed walking-instruction comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from forecast import OFFSETS, BASELINES, FITS, summaries, features, predict_batch, load_encoders
from predict import DEFAULT_CHECKPOINT

PARENT = "6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864"
FAMILY = "encoder_cue"
METHODS = (*BASELINES, *FITS, "swapped_encoder", "swapped_linear")


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def take(d, mask):
    return {k:v[mask] for k,v in d.items()}


def paired_only(d):
    people = [p for p in np.unique(d["person"]) if set(d["condition"][d["person"] == p]) == {4,5}]
    if not people:
        raise ValueError("No participant supplied qualifying rows in both conditions.")
    return take(d, np.isin(d["person"], people))


def weights(d):
    out = np.zeros(len(d["person"]))
    people = np.unique(d["person"])
    for person in people:
        own = d["person"] == person
        conditions = np.unique(d["condition"][own])
        for code in conditions:
            pac = own & (d["condition"] == code)
            trials = np.unique(d["repeat"][pac])
            for trial in trials:
                use = pac & (d["repeat"] == trial)
                out[use] = 1 / (len(people) * len(conditions) * len(trials) * sum(use))
    return out


def center_scale(x, w):
    m = w @ x
    sd = np.sqrt(w @ ((x - m)**2))
    return m, np.where(sd < 1e-8, 1., sd)


def fit(d, encoders):
    w = weights(d)
    hist = d["history_mm"]
    y = d["future_delta_mm"].reshape(-1, 6)
    prior = (hist[:, -1] - hist[:, -11]).reshape(-1, 6)
    t, _ = summaries(hist)
    mc, sd = center_scale(t.reshape(-1, 6), np.repeat(w/4, 4))
    means = {}
    for c in (4, 5):
        for o in OFFSETS:
            rows = (d["condition"] == c) & (d["offset"] == o)
            if not rows.any():
                rows = d["condition"] == c
            if not rows.any():
                rows = np.ones(len(w),dtype=bool)
            cell_weight = weights(take(d, rows))
            means[f"{c}/{o}"] = (cell_weight @ y[rows]).reshape(2,3).tolist()
    state = {"version":1,"parent_sha256":PARENT,"cell_means":means,"token_mean":mc.tolist(),
             "token_sd":sd.tolist(),"fits":{}}
    for method in FITS:
        x = features(method, d, state, encoders)
        center, scale = center_scale(x, w)
        z = (x-center)/scale
        target = y if method == "cue_only" else y-prior
        bias = w @ target
        gram = z.T @ (w[:,None]*z) + .05*np.eye(z.shape[1])
        coef = np.linalg.solve(gram, z.T @ (w[:,None]*(target-bias)))
        state["fits"][method] = {"mean":center.tolist(),"sd":scale.tolist(),"coef":coef.tolist(),
                                 "bias":bias.tolist()}
    return state


def predict_all(d, state, encoders):
    result = {k:predict_batch(k,d,state,encoders) for k in (*BASELINES,*FITS)}
    swapped = {**d, "condition": 9-d["condition"]}
    result["swapped_encoder"] = predict_batch(FAMILY, swapped, state, encoders)
    result["swapped_linear"] = predict_batch("linear_cue", swapped, state, encoders)
    return result


def summarize(d, pred):
    people = np.unique(d["person"])
    w = weights(d)
    true = d["future_delta_mm"]
    rng = np.random.default_rng(1207)
    sampled = rng.integers(0,len(people),size=(5000,len(people)))
    result = {"people":len(people),"recordings":len(set(zip(d["person"],d["condition"],d["repeat"]))),
              "windows":len(w),"conditions":{},"methods":{},"paired":{},"cue_test":{}}
    person_loss = {}
    for m,prediction in pred.items():
        error = prediction-true
        distance = np.linalg.norm(error,axis=2)
        by_person = np.stack([np.average(distance[d["person"]==p],axis=0,weights=w[d["person"]==p]) for p in people])
        person_loss[m] = by_person
        result["methods"][m] = {"endpoint_mm":np.average(distance,axis=0,weights=w).tolist(),
                                "bias_forward_left_up_mm":np.average(error,axis=0,weights=w).tolist(),
                                "mean_ci95_mm":np.quantile(by_person[sampled].mean(axis=1),[.025,.975],axis=0).T.tolist()}
    for code in (4,5):
        mask = d["condition"] == code
        wc = weights(take(d,mask))
        result["conditions"][str(code)] = {
            "people":len(set(d["person"][mask])),"windows":int(mask.sum()),
            "recordings":len(set(zip(d["person"][mask],d["repeat"][mask]))),
            "endpoint_mm":{m:np.average(np.linalg.norm((p-true)[mask],axis=2),axis=0,weights=wc).tolist() for m,p in pred.items()}}
    for family, no, swapped in [(FAMILY,"encoder_motion","swapped_encoder"),("linear_cue","linear_motion","swapped_linear")]:
        summaries_by_method = {}
        for comp in (no,swapped,"pace_phase","velocity_50ms","repeat_100ms","condition_phase_mean","hold"):
            paired = person_loss[family]-person_loss[comp]
            summaries_by_method[comp] = {"mean_mm":paired.mean(axis=0).tolist(),
                "ci95_mm":np.quantile(paired[sampled].mean(axis=1),[.025,.975],axis=0).T.tolist(),
                "people_improved":(paired<0).sum(axis=0).tolist()}
        result["paired"][family] = summaries_by_method
        a,b=[np.asarray(summaries_by_method[m]["ci95_mm"])[:,1] for m in (no,swapped)]
        result["cue_test"][family] = {"passes_pelvis_heel":((a<0)&(b<0)).tolist(),
            "beats_all_simple_means_pelvis_heel":np.all([np.asarray(summaries_by_method[c]["mean_mm"])<0
                for c in ("pace_phase","velocity_50ms","repeat_100ms","condition_phase_mean","hold")],axis=0).tolist()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("fit","score"))
    for key in ("data","model","report"):
        parser.add_argument(key,type=Path)
    parser.add_argument("--private",type=Path)
    args = parser.parse_args()
    if hashlib.sha256(DEFAULT_CHECKPOINT.read_bytes()).hexdigest()!=PARENT:
        raise ValueError("Original movement encoder identity has changed.")
    encoders = load_encoders(DEFAULT_CHECKPOINT,None)
    required=("person","condition","repeat","offset","history_mm","future_delta_mm")
    with np.load(args.data,allow_pickle=False) as source:
        d=paired_only({k:source[k] for k in required})
    if args.private:
        args.private.mkdir(parents=True,exist_ok=True)
    if args.stage=="fit":
        pred={}
        roster=sorted(set(d["person"]))
        for fold in range(min(5,len(roster))):
            test=np.isin(d["person"],roster[fold::min(5,len(roster))])
            state=fit(take(d,~test),encoders)
            if args.private:dump(args.private/f"fold-{fold}.json",state)
            for key,values in predict_all(take(d,test),state,encoders).items():
                pred.setdefault(key,np.full_like(d["future_delta_mm"],np.nan))[test]=values
        dump(args.model,fit(d,encoders))
    else:
        pred=predict_all(d,json.loads(args.model.read_bytes()),encoders)
    dump(args.report,summarize(d,pred))
    if args.private:np.savez_compressed(args.private/(args.report.stem+"-rows.npz"),**pred)


if __name__=="__main__":
    main()
