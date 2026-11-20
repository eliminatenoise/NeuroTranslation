"""Reproduce participant-held-out development fits, every control and optional assessment tables."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

# These small full-batch matrices used one native math thread in the reference fit.
for pool in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[pool] = "1"

import numpy as np
import torch
from records import MUSCLES, donors, sha, stats, subset, weights, write
from network import EPOCHS, decode_state, encode_state, predict, train
from controls import RIDGES, combine, fit_ridge, fit_simple, ridge_predict, simple_predict
from report import errors, summarize

HERE = Path(__file__).resolve().parent
KINDS = ("joint", "heel", "force", "marker")


def scoring(pred, d, norm, desired):
    err = errors(d, pred)
    w = weights(d)
    mm = (w @ err[:, 0]) / np.linalg.norm(norm["ys"][:3])
    force = (w @ err[:, 1]) / norm["ys"][3]
    return float(mm if desired == "heel" else force if desired == "force" else (mm+force)/2)


def candidates(fit, val, device):
    norm = stats(fit)
    scores, choices = {}, {}
    for k in KINDS:
        states, _ = train(fit, norm, k, device)
        vals = {ep:scoring(predict(st, val, norm, k, device), val, norm, k) for ep,st in states.items()}
        scores[k], choices[k] = vals, min(vals, key=vals.get)
    for k in RIDGES:
        vals = {"heel":{}, "force":{}}
        for a, params in fit_ridge(fit, norm, k).items():
            pred = ridge_predict(val, norm, k, params)
            for target in vals:
                vals[target][a] = scoring(pred, val, norm, target)
        for target, outcomes in vals.items():
            key = k + "_" + target
            scores[key], choices[key] = outcomes, min(outcomes, key=outcomes.get)
    return scores, choices


def refit(fit, choices, device, val=None):
    norm = stats(fit)
    models, scores, proof = {}, {}, {}
    for k in KINDS:
        epochs = EPOCHS if val is not None else (choices[k],)
        states, grad = train(fit, norm, k, device, epochs, k == "joint" and val is None)
        models[k] = {"schema":"gait-pair-temporal-v1", "kind":k, "epoch":choices[k],"norm":norm,
                     "state":encode_state(states[choices[k]], k),"supported_offsets":sorted(set(map(int, fit["offset"]))),
                     "marker_order":["R_FCC","R_FM2"], "emg_order":MUSCLES,"axes":["lab_X","lab_Y","lab_Z_up"]}
        if grad:
            proof = grad
        if val is not None:
            scores[k] = {ep:scoring(predict(st, val, norm, k, device), val, norm, k) for ep,st in states.items()}
    extras = {"norm":norm,"simple":fit_simple(fit,norm),"ridges":{}}
    for k in RIDGES:
        params = fit_ridge(fit,norm,k)
        extras["ridges"][k] = combine(params[choices[k+"_heel"]], params[choices[k+"_force"]])
        if val is not None:
            for target in ("heel","force"):
                scores[k+"_"+target] = {a:scoring(ridge_predict(val,norm,k,r), val,norm,target)
                                         for a,r in params.items()}
    return models, extras, scores, proof


def predict_all(d, models, extras):
    norm = extras["norm"]
    out = simple_predict(d, norm, extras["simple"])
    for k, param in extras["ridges"].items():
        out[k] = ridge_predict(d,norm,k,param)
    for k, model in models.items():
        out[k] = predict(decode_state(model),d,model["norm"],k)
    take, donor = donors(d)
    wrong = np.full((len(d["person"]),4), np.nan)
    if len(take):
        sample = subset(d, take)
        sample["emg_uv"] = d["emg_uv"][donor]
        wrong[take] = predict(decode_state(models["joint"]),sample,norm,"joint")
    out["wrong_emg"] = wrong
    return out



def read_arrays(path, expected_hash):
    if sha(path) != expected_hash:
        raise ValueError("The supplied arrays differ from the qualified source partition")
    with np.load(path, allow_pickle=False) as file:
        return {k: file[k] for k in ("person", "repeat", "offset", "cutoff", "marker_mm", "emg_uv",
                                          "heel_delta_mm", "force_n", "privileged_force_n")}


def develop(d, ordinals):
    folds = (ordinals - 1) % 3
    nested = {}
    validation_counts = []
    candidate_scores = []
    for fold in range(3):
        training = folds != fold
        outer, val = subset(d, training), subset(d, ~training)
        train_ordinals = ordinals[training]
        people = sorted(set(train_ordinals))
        inner_val = np.isin(train_ordinals, people[::3])
        inner_fit, inner_dev = subset(outer, ~inner_val), subset(outer, inner_val)
        if len(set(inner_fit["person"])) < 2 or not len(inner_dev["person"]) or not len(val["person"]):
            raise ValueError("Not enough participants in a prespecified development split")
        _, choices = candidates(inner_fit, inner_dev, "cpu")
        models, extras, scores, _ = refit(outer, choices, "cpu", val)
        for key, predictions in predict_all(val, models, extras).items():
            nested.setdefault(key, np.full((len(folds), 4), np.nan))[~training] = predictions
        validation_counts.append(len(set(val["person"])))
        candidate_scores.append(scores)
    choices = {}
    for key, options in candidate_scores[0].items():
        choices[key] = min(options, key=lambda opt: sum(n * row[key][opt] for n, row in zip(validation_counts, candidate_scores)))
    models, extras, _, proof = refit(d, choices, "cpu")
    return summarize(d, nested), models, extras, choices, proof


def run(args):
    if args.output.exists() or not args.output.parent.is_dir():
        raise ValueError("Choose an unused output directory inside an existing folder")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    seal = json.loads((HERE / "PRETEST-SHA256.json").read_bytes())
    reference = json.loads((HERE / "aggregate.json").read_bytes())
    d = read_arrays(args.development_npz, seal["development_npz_sha256"])
    receipt = json.loads(args.development_receipt.read_bytes())
    if receipt["partition"] != "train" or receipt["arrays_sha256"] != seal["development_npz_sha256"]:
        raise ValueError("The receipt must identify the development arrays")
    trials = receipt["trials"]
    ids = sorted({trial["person"] for trial in trials})
    ordinal_by_person = {person: i for i, person in enumerate(ids, 1)}
    ordinal_bytes = json.dumps(ids, separators=(",", ":")).encode()
    import hashlib
    if hashlib.sha256(ordinal_bytes).hexdigest() != seal["development_roster_order_sha256"]:
        raise ValueError("The receipt must contain the original complete 30-person development roster")
    if any(ordinal_by_person[t["person"]] != t["source_member"]["ordinal"] for t in trials):
        raise ValueError("Unexpected participant ordinal in the development receipt")
    ordinals = np.array([ordinal_by_person[person] for person in d["person"]])
    tables = {}
    tables["development"], models, extras, choices, gradient = develop(d, ordinals)
    for path, partition in ((args.assessment, "historical-primary"), (args.later_repeats, "historical-supplement")):
        if path is not None:
            rows = read_arrays(path, seal["qualified_assessment_npz_sha256"][partition])
            tables[partition] = summarize(rows, predict_all(rows, models, extras))
    with tempfile.TemporaryDirectory(dir=args.output.parent) as folder:
        staged = Path(folder) / "results"
        staged.mkdir()
        digests = {}
        for kind, model in models.items():
            filename = kind + "-model.json"
            write(staged / filename, model)
            digests[filename] = sha(staged / filename)
        write(staged / "aggregate.json", tables)
        write(staged / "gradient.json", gradient)
        check = {"exact_weight_bytes": digests == seal["task_trained_weights"], "weights": digests,
                 "reference_aggregate_match": {key: val == reference[key] for key, val in tables.items()},
                 "selected_configurations": choices}
        write(staged / "reproduction.json", check)
        staged.rename(args.output)
    return check


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development_npz", type=Path)
    parser.add_argument("development_receipt", type=Path)
    parser.add_argument("output", type=Path, help="New directory for aggregates and final weights")
    parser.add_argument("--assessment", type=Path, help="Original historical assessment NPZ")
    parser.add_argument("--later-repeats", type=Path, help="Additional walks in the historical roster")
    checks = run(parser.parse_args())
    print(json.dumps(checks, indent=2))
    sys.exit(0 if checks["exact_weight_bytes"] and all(checks["reference_aggregate_match"].values()) else 1)
