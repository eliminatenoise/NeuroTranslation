"""Reproduce grouped development fits or score an independently extracted cohort."""
import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import numpy as np
import torch

from model import (MODES, load_data, normalizer, predict, subset, train_model,
                   write_json)
from score import SEEDS, donor_indices, report


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(device, threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested accelerator is unavailable")


def all_donors(d):
    return {("primary" if seed is None else str(seed)): donor_indices(d, seed) for seed in SEEDS}


def fit(d, device):
    norm = normalizer(d)
    models, proofs = {}, {}
    for mode in MODES:
        models[mode], proofs[mode] = train_model(d, norm, mode, device)
    return models, proofs


def score_rows(d, idx, models, donors, predictions):
    small = subset(d, idx)
    for m in MODES:
        predictions[m][idx] = predict(small, models[m])
    for label, (refs, _) in donors.items():
        ii = idx[refs[idx] >= 0]
        if not len(ii):
            continue
        swapped = subset(d, ii)
        for key in ("eeg_mean_uv", "eeg_rms_uv", "eeg_good"):
            swapped[key] = d[key][refs[ii]]
        predictions["wrong_" + label][ii] = predict(swapped, models["full"])


def empty_predictions(d, donors):
    return {k: np.full((len(d["person"]), 2, 3), np.nan) for k in
            (*MODES, *("wrong_" + label for label in donors))}


def save_score(out, label, d, predictions, donors):
    write_json(out / (label + "-summary.json"), report(d, predictions, donors))
    np.savez_compressed(out / "private" / (label + "-predictions.npz"), **predictions,
                        **{k: d[k] for k in ("person", "event", "cutoff", "direction", "future_delta_mm")})


def grouped_fit(d, roster, out, device):
    donors = all_donors(d)
    predictions = empty_predictions(d, donors)
    ranks = {p: i for i, p in enumerate(roster)}
    folds = np.array([ranks[p] % 3 for p in d["person"]])
    evidence = {"folds": {}}
    for i in range(3):
        train = subset(d, folds != i)
        ix = np.flatnonzero(folds == i)
        if not len(ix) or not len(train["person"]):
            raise ValueError("Empty training or validation fold")
        fit_people = sorted(np.unique(train["person"]).tolist())
        held_people = sorted(np.unique(d["person"][ix]).tolist())
        if set(fit_people) & set(held_people):
            raise ValueError("Person leakage")
        models, check = fit(train, device)
        write_json(out / "private" / f"fold-{i}.json", models, compact=True)
        evidence["folds"][str(i)] = {"fit": fit_people, "held": held_people, "proof": check}
        score_rows(d, ix, models, donors, predictions)
    save_score(out, "development", d, predictions, donors)
    models, check = fit(d, device)
    write_json(out / "weights.json", models, compact=True)
    evidence["final"] = check
    evidence["weights_sha256"] = digest(out / "weights.json")
    write_json(out / "private" / "training-proof.json", evidence)


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fit", "score", "bench"])
    parser.add_argument("data", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--roster", type=Path, help="Optional JSON with ordered fit/assessment lists")
    parser.add_argument("--qc", type=Path, help="Source extractor quality report for adjacency sensitivity")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--weights-sha256")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    if digest(args.data) != args.sha256:
        raise ValueError("Input seal mismatch")
    prepare(args.device, args.threads)
    if args.roster:
        roster = json.loads(args.roster.read_text())
    else:
        from source.acquire import roster as split_roster
        people = [f"sub-{number:03}" for number in range(1, 31)]
        roster = {key: split_roster(stage, people) for key, stage in
                  (("fit", "development"), ("assessment", "assessment"))}
    required = "assessment" if args.action == "score" else "fit"
    allowed = set(roster[required])
    if set(roster["fit"]) & set(roster["assessment"]) or len(allowed) != len(roster[required]):
        raise ValueError("Roster overlap or duplicates")
    d = load_data(args.data)
    if args.action != "bench":
        qc_path = args.qc or args.data.with_name(args.data.stem + "-qc.json")
        qc = json.loads(qc_path.read_text())
        if qc["npz_sha256"] != args.sha256 or qc["stage"] != ("assessment" if required == "assessment" else "development"):
            raise ValueError("Quality report for a different cohort")
        by_person = {p: set(record["admitted_neighbors_of_excluded_ordinals"]) for p, record in qc["per_person"].items()}
        d["adjacent_to_excluded"] = np.array([event in by_person[p] for p, event in zip(d["person"], d["event"])])
    if not set(d["person"]) <= allowed:
        raise ValueError("Participant outside selected cohort")
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(exist_ok=True)
    if args.action == "fit":
        grouped_fit(d, roster["fit"], out, args.device)
    elif args.action == "score":
        if not args.weights or not args.weights_sha256 or digest(args.weights) != args.weights_sha256:
            raise ValueError("Fitted weight seal required")
        models = json.loads(args.weights.read_text())
        donors = all_donors(d)
        predictions = empty_predictions(d, donors)
        score_rows(d, np.arange(len(d["person"])), models, donors, predictions)
        save_score(out, "assessment", d, predictions, donors)
    else:
        begin = time.perf_counter()
        norm = normalizer(d)
        model, proof = train_model(d, norm, "full", args.device, updates=24)
        pred = predict(subset(d, np.arange(min(96, len(d["person"])))), model)
        write_json(out / "private" / "benchmark.json", {
            "training_prediction_seconds": time.perf_counter() - begin, "probe_mm": pred.tolist(),
            "proof": proof, "torch": torch.__version__, "numpy": np.__version__,
            "device": torch.cuda.get_device_name() if args.device == "cuda" else platform.processor(),
            "intra_threads": torch.get_num_threads(), "inter_threads": torch.get_num_interop_threads(),
            "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None})


if __name__ == "__main__":
    run()
