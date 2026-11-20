"""Run the four prospective development folds, followed by the final frozen fit."""
import time
START = time.monotonic()
import argparse
import csv
import hashlib
import json
import os
try:
    import resource
except ImportError:
    resource = None
import sys
from pathlib import Path

import numpy as np
import torch

from evaluation import N, derange, errors, fit_controls, load_npz, simple_predictions, summarize
from forward import CHANNELS, WINDOWS, features, predict, tokens, undo
from network import UPDATES, train

HERE = Path(__file__).resolve().parent
SOURCE_FILES = [f"development-sub-{person:03d}.npz" for person in range(1, 5)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def state(model):
    return {k: v.detach().cpu().numpy().tolist() for k, v in model.state_dict().items()}


def pytorch_pred(model, x, transform):
    with torch.inference_mode():
        y = model(torch.as_tensor(x, dtype=torch.float32)).double().numpy()
    return undo(y, transform)


def fit_fold(raw, baseline, target, order, people):
    x, y, tfm, controls = fit_controls(raw, baseline, target, order, people)
    models = {name: train(data, y) for name, data in x.items()}
    return tfm, controls, models


def export_parity(out, weights, models):
    rng = np.random.default_rng(32019)
    cases = []
    maximum = 0.0
    for name, scale, index in (("zero", 0., 0), ("small", 1., 27), ("large", 24., 79)):
        base = np.round(rng.normal(0, scale, size=(50, 5)), 5)
        early = np.round(rng.normal(0, scale, size=(30, 5)), 5)
        sample = tokens(base[None], early[None])
        expected = {}
        for key in ("noneng", "eng"):
            x = features(sample, [index], weights["transform"], key == "eng")
            expected[key] = float(pytorch_pred(models[key], x, weights["transform"])[0])
            actual = float(predict(sample, [index], weights, key)[0])
            maximum = max(maximum, abs(actual - expected[key]))
        cases.append({"name": name, "baseline": base.tolist(), "early": early.tolist(),
                      "event_index": index, "expected_uV": expected})
    tolerance = 0.001
    if maximum > tolerance:
        raise ArithmeticError(f"Portable parity error {maximum} µV exceeds {tolerance}.")
    save(out / "parity.json", {"schema_version": 1, "description": "Entirely synthetic input windows.",
         "atol_uV": tolerance, "max_numpy_difference_uV": maximum, "cases": cases})
    return maximum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-dir", type=Path, required=True, help="Folder containing the four development NPZ files.")
    parser.add_argument("--out", type=Path, required=True, help="New or empty reproducibility directory.")
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Choose an empty output directory for the new fit.")
    args.out.mkdir(exist_ok=True, parents=True)
    threads = 2
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    paths = [args.development_dir / name for name in SOURCE_FILES]
    # Explicit allowlist: do not enumerate this supplied directory.
    receipts = [args.development_dir / f"sub-{person:03d}-receipt.json" for person in range(1, 5)]
    for i, (path, receipt, run) in enumerate(zip(paths, receipts, (3, 3, 2, 2)), start=1):
        metadata = json.loads(receipt.read_text())
        sub = f"sub-{i:03d}"
        if metadata["subject"] != sub or metadata["stem"] != f"{sub}/eeg/{sub}_task-median_run-{run:02d}_" or metadata["output"] != path.name:
            raise ValueError("The receipt does not match its authorized participant and catalog-selected run.")
    parts = [load_npz(path, receipt) for path, receipt in zip(paths, receipts)]
    raw, baseline, target = (np.concatenate(column) for column in zip(*parts))
    people = np.repeat(np.arange(4), N)
    order = np.tile(np.arange(N), 4)
    folds, timing = [], []
    with (args.out / "development-predictions.csv").open("w", newline="") as stream:
        writer = None
        for held in range(4):
            stage = time.monotonic()
            selected = people != held
            tfm, controls, models = fit_fold(raw[selected], baseline[selected], target[selected],
                                             order[selected], people[selected])
            test = ~selected
            outputs = simple_predictions(raw[test], baseline[test], order[test], people[test], tfm, controls)
            for name, model in models.items():
                values = derange(raw[test], people[test]) if name == "deranged" else raw[test]
                x = features(values, order[test], tfm, name != "noneng")
                outputs["transformer_" + name] = pytorch_pred(model, x, tfm)
            folds.append(errors(target[test], outputs))
            if writer is None:
                writer = csv.writer(stream)
                writer.writerow(["development_person", "event_index", "observed_uV", *outputs,
                                 *["absolute_error_" + name for name in outputs]])
            for j, obs in enumerate(target[test]):
                preds = [val[j] for val in outputs.values()]
                writer.writerow([int(held) + 1, j, obs, *preds, *[abs(z - obs) for z in preds]])
            timing.append(time.monotonic() - stage)
    stage = time.monotonic()
    tfm, controls, models = fit_fold(raw, baseline, target, order, people)
    timing.append(time.monotonic() - stage)
    weights = {"schema_version": 1, "channels": CHANNELS, "windows_ms": WINDOWS,
               "target_ms": [12, 14], "units": "uV", "rate_hz": 10000, "transform": tfm,
               "models": {name: state(models[name]) for name in ("noneng", "eng")}}
    controls["deranged_transformer"] = state(models["deranged"])
    export = args.out / "export"
    export.mkdir()
    save(export / "weights.json", weights)
    save(export / "controls.json", controls)
    save(export / "metrics.json", summarize(folds))
    max_error = export_parity(export, weights, models)
    # Check parity for every all-development event without publishing those events.
    real_parity = {}
    for name in ("noneng", "eng"):
        data = features(raw, order, tfm, name == "eng")
        a = pytorch_pred(models[name], data, tfm)
        b = predict(raw, order, weights, name)
        real_parity[name] = float(np.max(np.abs(a - b)))
        if real_parity[name] > 0.001:
            raise ArithmeticError("Real-window parity exceeds the 0.001 µV fixed software tolerance.")
    usage = resource.getrusage(resource.RUSAGE_SELF) if resource is not None else None
    save(args.out / "fit-receipt.json", {
        "sources_sha256": {p.name: sha(p) for p in paths + receipts},
        "protocol_sha256": sha(HERE / "PROTOCOL.md"),
        "acquisition_clarification_sha256": sha(HERE / "ACQUISITION-CLARIFICATION.md"),
        "fit_source_sha256": {p: sha(HERE / p) for p in ("fit.py", "forward.py", "network.py", "evaluation.py", "score.py")},
        "numpy": np.__version__, "torch": torch.__version__, "python": sys.version,
        "device": "cpu", "intraop_threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
        "omp": os.environ.get("OMP_NUM_THREADS"), "mkl": os.environ.get("MKL_NUM_THREADS"),
        "openblas": os.environ.get("OPENBLAS_NUM_THREADS"),
        "trainable_parameters_per_model": sum(p.numel() for p in models["eng"].parameters()),
        "gradient_updates": 5 * 3 * UPDATES, "transformer_fits": 15, "ridge_fits": 25,
        "timing_folds_then_final_s": timing, "elapsed_total_s": time.monotonic() - START,
        "cpu_user_s": usage.ru_utime if usage else None, "cpu_system_s": usage.ru_stime if usage else None, "peak_rss_KiB": usage.ru_maxrss if usage else None,
        "max_synthetic_parity_uV": max_error, "max_real_parity_uV": real_parity,
        "prediction_source": "out-of-person development predictions from PyTorch; final deployment weights trained on all 320",
        "timing_exclusions": "shell startup and writing this receipt; source acquisition, hardware probe, independent reader and outside evaluation separate"})


if __name__ == "__main__":
    main()
