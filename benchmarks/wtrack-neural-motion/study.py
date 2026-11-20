"""Fit from TRAIN only, seal all parameters, then evaluate the registered role once."""
from __future__ import annotations
import argparse
import json
import platform
import time
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_info
import attention
from wtrack import (HERE, UNITS, PROTOCOL, read_partition, choose_penalty, fit_ridge,
                    predict_ridge, trial_weights, surrogate, distance_summary, digest, write_json)

MODES = ("motion", "combined", "spikes")
CHECKS = ["persistence","velocity","ridge_motion","attention_motion","ridge_wrong"]
SOURCES = ["study.py","wtrack.py","attention.py","shared_decoder.py","predict.py","protocol.json"]


def load_fit(path):
    with np.load(path,allow_pickle=False) as z:
        return dict(z)


def supported_inputs(source, support, role):
    manifest = json.loads((source.parent/"manifest.json").read_text())
    if any(manifest[k] != v for k,v in {
        "asset_id":PROTOCOL["source"]["asset"],"version":"000978/versions/" + PROTOCOL["source"]["version"],
        "archive_sha256":PROTOCOL["source"]["sha256_archive_reported"]}.items()):
        raise ValueError("Source release or asset mismatch")
    entries = {str(e["trial_id"]):e["sha256"] for e in manifest["arrays"] if e["split"] == role}
    if entries != {k:v["sha256"] for k,v in support.items()}:
        raise ValueError("Registry and packet hashes differ")


def identities():
    return {filename:digest(HERE/filename) for filename in SOURCES}


def fit_all(args):
    start = time.perf_counter()
    out = args.output
    if (out/"fit-seal.json").exists():
        raise FileExistsError("A sealed fit already exists. Use a new output directory.")
    out.mkdir(parents=True,exist_ok=True)
    d,_,support = read_partition(args.pairs,"train")
    supported_inputs(args.pairs,support,"train")
    folds, curves, fits = {}, {}, {}
    for mode in MODES:
        best, record = choose_penalty(d,mode)
        folds[mode] = dict(selected=best,rolling_cv=record)
        fits["ridge_"+mode] = fit_ridge(d,mode,best)
    for mode in MODES[:2]:
        fits["attention_"+mode],curves[mode] = attention.fit(d,mode)
    for mode, params in fits.items():
        np.savez_compressed(out/(mode+".npz"),**params)
    prior = np.average(d.y,axis=0,weights=trial_weights(d.trial))
    ex = dict(subject=PROTOCOL["source"]["rat"], session="01", epoch_id=5,
              unit_ids=UNITS.tolist(), trial_id=int(d.trial[0]), cutoff_s=float(d.cutoff[0]),
              history_frame_s=d.prior_s[0].tolist(), motion=d.motion[0].tolist(),
              log_elapsed=d.clocks[0].tolist(), spike_counts=d.spike[0].tolist(),
              source_camera_rows=d.prior_frame[0].tolist())
    write_json(out/"example.json",ex)
    seal = dict(source_manifest=digest(args.pairs.parent/"manifest.json"), train=support,
                code=identities(), weights={key:digest(out/(key+".npz")) for key in fits},
                example_sha256=digest(out/"example.json"), centroid=prior.tolist(),
                n_trial=len(np.unique(d.trial)), n_windows=len(d.y), ridge_cv=folds, attention_loss=curves,
                dtype=dict(ridge="float64",attention="float32, denormalized to float64"),
                numpy=np.__version__,torch=str(torch.__version__),python=platform.python_version(),
                effective=dict(torch_threads=torch.get_num_threads(),interop=torch.get_num_interop_threads(),
                               numerical_pools=threadpool_info()),
                elapsed_s=time.perf_counter()-start, completed_utc=time.strftime("%FT%TZ",time.gmtime()))
    write_json(out/"fit-seal.json", seal)
    print(json.dumps(dict(trials=seal["n_trial"],windows=seal["n_windows"],seconds=seal["elapsed_s"],
                          weights=seal["weights"],seal=digest(out/"fit-seal.json"))))


def bootstrap(trial_ids, error):
    """Contiguous circular four-trip blocks. Same indices for every comparison."""
    if not np.all(np.diff(trial_ids)==1):
        return {}, False, "Gaps in contributing test trials prevent contiguous-block inference"
    n = len(trial_ids)
    rng = np.random.default_rng(1445)
    block_starts = rng.integers(0,n,(10000,(n+3)//4))
    boot = ((block_starts[:,:,None]+np.arange(4))%n).reshape(10000,-1)[:,:n]
    candidates = [(k,"ridge_combined") for k in CHECKS] + [
        ("ridge_order","ridge_combined"),
        ("attention_motion","attention_combined"),("attention_wrong","attention_combined"),
        ("attention_order","attention_combined"),("train_centroid","ridge_spikes")]
    result = {}
    for control, model in candidates:
        delta = np.array([error[control][i]-error[model][i] for i in trial_ids])
        draws = delta[boot].mean(axis=1)
        row = dict(mean_cm=float(delta.mean()),percentile95_cm=np.quantile(draws,[.025,.975]).tolist(),
                   positive_trips=int((delta>0).sum()))
        if model=="ridge_combined" and control in CHECKS:
            row["simultaneous_lower_cm"] = float(np.quantile(draws,.05/len(CHECKS)))
        result[control+"_minus_"+model] = row
    passes = len(trial_ids)>=8 and all(result[k+"_minus_ridge_combined"]["simultaneous_lower_cm"]>0
                                        for k in CHECKS)
    return result, passes, "Eligible paired descriptive block-bootstrap decision"


def score(args):
    out = args.output
    if (out/"score-intent.json").exists():
        raise FileExistsError("This fit already has an evaluation intent. Inspect its recorded outcome.")
    seal = json.loads((out/"fit-seal.json").read_text())
    if seal["code"] != identities() or seal["source_manifest"] != digest(args.pairs.parent/"manifest.json"):
        raise ValueError("Fit code or source registry has changed")
    fits = {}
    for key,value in seal["weights"].items():
        path = out/(key+".npz")
        if digest(path) != value: raise ValueError("Fitted weight hash changed")
        fits[key] = load_fit(path)
    # This is persisted before touching test array contents.
    write_json(out/"score-intent.json",dict(fit_sha256=digest(out/"fit-seal.json"), code=identities(),
               utc=time.strftime("%FT%TZ",time.gmtime()), eligible=PROTOCOL["split"]["paired_test"]))
    d, trials, support = read_partition(args.pairs,"test")
    supported_inputs(args.pairs,support,"test")
    d = d.select(np.isin(d.trial,PROTOCOL["split"]["paired_test"]))
    wrong, order, donor, donor_s = surrogate(d,trials)
    pred = dict(train_centroid=np.tile(seal["centroid"],(len(d.y),1)),persistence=d.anchor,
                velocity=d.anchor+d.motion[:,-1,2:4]*(.25+d.motion[:,-1,4,None]))
    for mode in MODES:
        pred["ridge_"+mode] = predict_ridge(fits["ridge_"+mode],d.motion,d.clocks,d.spike)
    for mode in MODES[:2]:
        pred["attention_"+mode] = attention.predict(fits["attention_"+mode],d.motion,d.clocks,d.spike)
    for name,spike in [("wrong",wrong),("order",order)]:
        pred["ridge_"+name] = predict_ridge(fits["ridge_combined"],d.motion,d.clocks,spike)
        pred["attention_"+name] = attention.predict(fits["attention_combined"],d.motion,d.clocks,spike)
    if any(p.shape!=d.y.shape or not np.isfinite(p).all() for p in pred.values()):
        raise ValueError("Invalid forecast array")
    trial_ids=np.unique(d.trial).tolist()
    errors={k:distance_summary(d,v) for k,v in pred.items()}
    comparisons,passed,state = bootstrap(trial_ids,errors)
    outputs = {key:dict(mean_trip_error_cm=float(np.mean(list(by_trip.values()))),
                        mean_window_error_cm=float(np.linalg.norm(pred[key]-d.y,axis=1).mean()),
                        by_trial_cm=by_trip) for key,by_trip in errors.items()}
    elapsed=d.label_s-d.cutoff
    np.savez_compressed(out/"predictions.npz",trial=d.trial,cutoff_s=d.cutoff,history_frame_s=d.prior_s,
                        history_frame_row=d.prior_frame,label_s=d.label_s,label_frame=d.label_frame,
                        measured_xy_cm=d.y,donor_trial=donor,donor_cutoff_s=donor_s,
                        **{"pred_"+k:v for k,v in pred.items()})
    result=dict(fit_sha256=digest(out/"fit-seal.json"),intent_sha256=digest(out/"score-intent.json"),
                predictions_sha256=digest(out/"predictions.npz"),
                primary_pass=passed,primary_decision=state,test_support=support,
                paired_trials=trial_ids,n_paired_trials=len(trial_ids),n_paired_windows=len(d.y),
                recorded_target_lead_s=dict(min=float(elapsed.min()),mean=float(elapsed.mean()),max=float(elapsed.max())),
                metrics=outputs,comparisons=comparisons,reserve=PROTOCOL["split"]["reserve"],
                completed_utc=time.strftime("%FT%TZ",time.gmtime()))
    write_json(out/"scores.json",result)
    print(json.dumps({"pass":passed,"trials":trial_ids,"windows":len(d.y),
                      "scores":{k:v["mean_trip_error_cm"] for k,v in outputs.items()}}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=["fit","score"])
    parser.add_argument("--pairs",type=Path,required=True,help="Path to the source packet’s pairs directory")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--threads",type=int,choices=[1,2],default=1)
    args=parser.parse_args()
    attention.set_threads(args.threads)
    (fit_all if args.stage=="fit" else score)(args)


if __name__=="__main__":
    main()
