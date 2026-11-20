"""Rebuild fixed walking forecast fits, scores, fixtures and private review receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

# Restrict nested CPU pools before importing numerical libraries.
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
import numpy as np
import torch
from model import KINDS, Forecast, fitted, load_rows, normalizer, phase_profile, predict, predictions, subset
from score import evaluate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False) + "\n")


def read(path):
    return json.loads(Path(path).read_text())


def fit_all(d, device):
    norm = normalizer(d)
    bundle = {"schema": "walking-instruction-transformer-v1", "norm": norm, "models": {},
              "cue_phase_profile": phase_profile(d)}
    proofs = {}
    for kind in KINDS:
        bundle["models"][kind], proofs[kind] = fitted(d, norm, kind, device)
    return bundle, proofs


def synthetic():
    t = np.arange(-20, 1, dtype=np.float64) / 100
    pelvis = np.column_stack((1350*t, 15*np.sin(np.pi*t/.2), 18*(np.cos(8*t)-1)))
    heel = np.column_stack((1350*t+100*np.sin(14*t)-80, 4*np.sin(12*t)-85, -830+65*(1-np.cos(10*t))))
    return np.stack((pelvis, heel), axis=1)


def fixture(bundle):
    history = synthetic()[None, ...]
    oracle = {}
    for instruction, key, kind in ((4, "4", "cue"), (5, "5", "cue"), (4, "null", "withheld"), (4, "permuted_4", "permuted")):
        oracle[key] = predict(bundle, history, [20], [instruction], kind)[0].tolist()
    return {"source": "invented coordinate histories in millimetres", "input": {
        "history_mm": history[0].tolist(), "offset": 20, "instruction": 4}, "pytorch_future_delta_mm": oracle}


def record(out, label, d, preds, provenance):
    aggregate, personal = evaluate(d, preds)
    aggregate["provenance"] = provenance
    dump(out / (label + "-summary.json"), aggregate)
    dump(out / "private" / (label + "-people.json"), personal)
    np.savez_compressed(out / "private" / (label + "-predictions.npz"), **{k: d[k] for k in ("person", "condition", "repeat", "offset", "cutoff")},
                        **preds, future_delta_mm=d["future_delta_mm"])


def train(args, d):
    out = args.output
    (out / "private").mkdir(parents=True, exist_ok=True)
    if (out / "weights.json").exists():
        raise FileExistsError("Use an empty destination for a rebuild")
    people = sorted(set(d["person"]))
    if len(people) < 3:
        raise ValueError("Three participant groups are required")
    fold_predictions = {}
    proof = {"source_file_sha256": sha(args.data), "folds": []}
    for i in range(3):
        held = people[i::3]
        mask = np.isin(d["person"], held)
        tr, val = subset(d, ~mask), subset(d, mask)
        if set(tr["person"]) & set(val["person"]):
            raise AssertionError("Participant leak")
        model, gradients = fit_all(tr, args.device)
        dump(out / "private" / ("fold-" + str(i) + "-weights.json"), model)
        preds = predictions(model, val)
        for name, y in preds.items():
            if name not in fold_predictions:
                fold_predictions[name] = np.full(d["future_delta_mm"].shape, np.nan, dtype=np.float64)
            fold_predictions[name][mask] = y
        proof["folds"].append({"excluded_people": held, "train_people": sorted(set(tr["person"])),
                               "training_windows": int((~mask).sum()), "gradient_proofs": gradients})
    record(out, "development", d, fold_predictions, "Three participant-held-out development folds")
    model, proof["final_gradients"] = fit_all(d, args.device)
    proof["fitted_people"] = people
    proof["device"] = args.device
    proof["threads"] = torch.get_num_threads()
    dump(out / "weights.json", model)
    dump(out / "example.json", fixture(model))
    dump(out / "private" / "fit-proof.json", proof)


def assess(args, d):
    proof = read(args.fit_dir / "private" / "fit-proof.json")
    if set(d["person"]) & set(proof["fitted_people"]):
        raise ValueError("Assessment includes fitted people")
    if sha(args.fit_dir / "weights.json") != args.weights_sha256:
        raise ValueError("Sealed weights hash mismatch")
    bundle = read(args.fit_dir / "weights.json")
    record(args.output, "assessment", d, predictions(bundle, d), "Historical participants, after fit and scorer seal")


def bench(args, d):
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("ROCm/CUDA unavailable")
    norm = normalizer(d)
    start = time.perf_counter()
    state, proof = fitted(d, norm, "cue", args.device, 6)
    elapsed = time.perf_counter() - start
    bundle = {"norm": norm, "models":{"cue":state}}
    pred = predict(bundle, d["history_mm"], d["offset"], d["condition"])
    dump(args.output, {"fit_seconds":elapsed, "gradient_proof":proof,
                       "torch":torch.__version__, "numpy":np.__version__, "python":sys.version,
                       "device":torch.cuda.get_device_name(0) if args.device=="cuda" else "CPU",
                       "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,
                       "torch_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(),
                       "rows":len(pred), "predictions":pred.tolist()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["bench", "train", "assess"])
    p.add_argument("data", type=Path, help="Prepared private split NPZ from the source extractor")
    p.add_argument("output", type=Path)
    p.add_argument("--data-sha256", required=True)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--weights-sha256")
    p.add_argument("--fit-dir", type=Path)
    args = p.parse_args()
    if args.action == "assess" and (not args.fit_dir or not args.weights_sha256):
        p.error("assess requires --fit-dir and --weights-sha256")
    if sha(args.data) != args.data_sha256:
        raise ValueError("Prepared split SHA-256 mismatch")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.use_deterministic_algorithms(True)
    d = load_rows(args.data)
    {"train": train, "bench": bench, "assess": assess}[args.action](args, d)


if __name__ == "__main__":
    main()
