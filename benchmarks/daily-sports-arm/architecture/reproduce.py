"""Evaluate the supplied checkpoint and optionally reproduce the three new ridge heads."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

# Set before importing any numerical runtime. Thread settings apply only to this process.
for key in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import numpy as np
import torch
from chronos import chronos_bolt
from bolt_runner import digest, load_bolt, quantiles
from scoring import HORIZONS, direct, fit_new, groups, interval, live_timing, read_windows, recursive, repeat, summarize_forecast

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "sources.json").read_text())


def check(path, expected):
    if digest(path) != expected:
        raise ValueError(f"Unexpected file digest for {path.name}")


def load_reference(folder):
    for name, expected in SPEC["arm_reference"]["files"].items():
        check(folder / name, expected)
    modspec = importlib.util.spec_from_file_location("arm_reference", folder / "forecast.py")
    mod = importlib.util.module_from_spec(modspec)
    modspec.loader.exec_module(mod)
    model, state = mod.load(folder / "model.pt")
    if state["implementation"] != SPEC["arm_reference"]["files"]["forecast.py"]:
        raise ValueError("Earlier checkpoint carries different implementation")
    return mod, model, state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New JSON file for this run")
    parser.add_argument("--arm-study", type=Path, default=HERE.parent, help="Existing daily-sports-arm folder")
    parser.add_argument("--refit-ridge", action="store_true", help="Fit the new 1/6/12-row heads once on p1–p4")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output file")
    check(args.archive, SPEC["source"]["sha256"])
    check(HERE / "protocol.json", SPEC["protocol_sha256"])
    check(HERE / "ridge.npz", SPEC["ridge_npz_sha256"])
    check(Path(chronos_bolt.__file__), SPEC["chronos"]["bolt_module_sha256"])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    mod, old, state = load_reference(args.arm_study)
    bolt = load_bolt()
    with np.load(HERE / "ridge.npz", allow_pickle=False) as fitted:
        params = {k: fitted[k] for k in fitted.files}
    report = {"horizons_samples": HORIZONS, "refit_horizons": [], "counts": {}}
    if args.refit_ridge:
        train_ids, x_train, y_train = read_windows(args.archive, "TRAIN")
        updated = fit_new(mod, state, x_train, y_train)
        for key in updated:
            np.testing.assert_allclose(updated[key], params[key], rtol=1e-10, atol=1e-11)
        params = updated
        report["refit_horizons"] = [1, 6, 12]
        report["counts"]["train"] = len(train_ids)
    for key, ref in (("center", state["center"]), ("scale", state["scale"])):
        np.testing.assert_array_equal(params[key], ref.numpy())
    np.testing.assert_array_equal(params["coef"][:, 3:6], state["ridge"].numpy())
    np.testing.assert_array_equal(params["intercept"][3:6], state["intercept"].numpy())
    ids, x, y = read_windows(args.archive, "DEV")
    digests = [hashlib.sha256(a.tobytes(order="C")).hexdigest() for a in (ids, y)]
    if digests != [SPEC["dev_identity"]["ordered_numpy_unicode_id_sha256"],
                   SPEC["dev_identity"]["float64_native_targets_sha256"]]:
        raise ValueError("Participant, row ordering or measured targets differ")
    funcs = {"direct": lambda v: direct(v, params), "recursive": lambda v: recursive(v, params),
             "persistence": repeat, "bolt_quantiles": lambda v: quantiles(bolt, v)}
    predictions, durations = {}, {}
    for key, fn in funcs.items():
        begin = time.perf_counter()
        predictions[key] = np.concatenate([fn(x[i:i+32]) for i in range(0, len(x), 32)])
        durations[key] = time.perf_counter() - begin
    q = predictions.pop("bolt_quantiles")
    predictions["bolt_median"] = q[..., 4]
    np.testing.assert_allclose(predictions["direct"][:, 0], predictions["recursive"][:, 0], atol=1e-11, rtol=0)
    old_h3 = mod.network_predictions(old, (x - params["center"]) / params["scale"]) * params["scale"] + params["center"]
    metrics = {}
    for name, mask in groups(ids).items():
        metrics[name] = {"windows": int(mask.sum()), **{
            k: summarize_forecast(v[mask], y[mask]) for k, v in predictions.items()},
            "bolt_interval": interval(q[mask], y[mask]),
            "old_transformer_h3_mae": float(abs(old_h3[mask] - y[mask, 1]).mean())}
    report["counts"]["development"] = len(ids)
    report.update(metrics=metrics, batch_seconds=durations, local_warm_timings=live_timing(funcs, x[:1]))
    with args.output.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
