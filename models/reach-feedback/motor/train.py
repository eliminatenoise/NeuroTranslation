"""Fit each chronological expansion or the final five matched models on TRAIN."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch

from forecast import ARMS, SEEDS, history_tokens, predict, standardized
from model import fit_transformer, native_forecast, ridge, training_scales, weights_by_original

IDENTITIES = ("block", "original", "ordinal", "k", "fold")
TRAIN_SHA = "40bb17cd64e61bfb4ef52b5ee943d27d50e1c82bbf487d58c623c4ed2d6666ab"


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_npz(path, values):
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("xb") as f:
        np.savez_compressed(f, **values)


def write_json(path, obj):
    with path.open("x") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")


def configure(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def load_train(path):
    from array_hash import content_hash
    if (file_hash(path) != TRAIN_SHA and
            content_hash(path) != "f82008a2bc97fdee8475ce56cebb1fa4e9b9bf0fa1fbdc035477d06cedadf700"):
        raise ValueError("Expected the frozen numerical training source")
    with np.load(path, allow_pickle=False) as f:
        d = {k: f[k] for k in (*IDENTITIES, "pose", "spikes", "cue", "movement", "unit_guide")}
    if (len(d["original"]) != 519 or np.unique(d["fold"]).tolist() != list(range(5))
            or d["movement"].shape != (519, 10, 8) or not np.isfinite(d["movement"]).all()):
        raise ValueError("Unexpected TRAIN population or motion support")
    keys = list(zip(d["block"].tolist(), d["original"].tolist()))
    if len(set(keys)) != 198 or len(set(zip(*[d[k].tolist() for k in IDENTITIES[:-1]]))) != 519:
        raise ValueError("Original or window identity discrepancy")
    return d


def run(args):
    tick = time.perf_counter()
    configure(args.threads)
    d = load_train(args.train)
    raw = history_tokens(d["pose"], d["spikes"], d["cue"])
    fold = d["fold"]
    group_ids = np.stack([d["block"], d["original"]], axis=1)
    _, group = np.unique(group_ids, axis=0, return_inverse=True)
    train = np.flatnonzero(fold < args.fold)  # fold 5 uses all TRAIN
    probe = train[:32] if args.qualify else (train if args.fold == 5 else np.flatnonzero(fold == args.fold))
    if not args.qualify and args.fold < 5:
        if np.intersect1d(group[train], group[probe]).size or d["k"][train].max() >= d["k"][probe].min():
            raise ValueError("Source rows violate chronological original-disjoint fitting")
    w = weights_by_original(group[train])
    scales = training_scales(raw[train], d["movement"][train], w)
    y = ((d["movement"][train] - scales["y_mean"]) / scales["y_scale"]).reshape(-1, 80)
    args.out.mkdir(parents=True, exist_ok=True)
    record = dict(train_sha256=TRAIN_SHA, fold=args.fold, qualification=args.qualify,
                  train_originals=np.unique(group_ids[train], axis=0).tolist(),
                  prediction_originals=np.unique(group_ids[probe], axis=0).tolist(),
                  train_rows=len(train), predict_rows=len(probe),
                  train_last_cutoff=int(d["k"][train].max()), predict_first_cutoff=int(d["k"][probe].min()),
                  torch_version=str(torch.__version__), numpy_version=np.__version__,
                  torch_threads=torch.get_num_threads(), interop_threads=torch.get_num_interop_threads(),
                  accelerator=args.device, fits={})
    forecasts = {k: d[k][probe] for k in IDENTITIES}
    forecasts["seeds"] = np.array(SEEDS)
    for arm in (ARMS if args.fold == 5 else ("full",)):
        base = dict(schema="chowdhury-motor-v1", arm=arm, unit_guide=d["unit_guide"], **scales)
        x = standardized(raw[train], base)
        if not args.qualify:
            linear = dict(**base, **ridge(x, y, w))
            name = arm + "-ridge.npz"
            write_npz(args.out / name, linear)
            px = standardized(raw[probe], base).reshape(len(probe), 840)
            native_ridge = (torch.from_numpy(px) @ torch.from_numpy(linear["coef"]) + torch.from_numpy(linear["bias"])).numpy()
            portable_ridge = predict(raw[probe], linear, d["unit_guide"])
            ridge_diff = np.max(np.abs(native_ridge.reshape(-1,10,8) - (portable_ridge - base["y_mean"])/base["y_scale"]))
            if ridge_diff >= .0005:
                raise ValueError("Ridge port mismatch")
            forecasts["ridge_" + arm] = portable_ridge
            record["fits"][name] = dict(sha256=file_hash(args.out / name), max_normalized_port_error=float(ridge_diff))
        runs = []
        for seed in ((17,) if args.qualify else SEEDS):
            net, params, steps = fit_transformer(x, y, w, seed, args.device, 12 if args.qualify else None)
            native = native_forecast(net, raw[probe], base, args.device)
            if args.qualify:
                np.save(args.out / "probe.npy", native, allow_pickle=False)
                record["steps"] = steps
                break
            model = dict(**base, **params)
            portable_output = predict(raw[probe], model, d["unit_guide"])
            difference = float(np.max(np.abs(native - (portable_output - base["y_mean"]) / base["y_scale"])))
            if not np.isfinite(difference) or difference >= .0005:
                raise ValueError(f"Normalized port difference {difference} failed")
            name = f"{arm}-{seed}.npz"
            write_npz(args.out / name, model)
            record["fits"][name] = dict(sha256=file_hash(args.out / name), steps=steps,
                                        max_normalized_port_error=difference,
                                        parameters=sum(p.numel() for p in net.parameters()))
            runs.append(portable_output)
        if not args.qualify:
            forecasts[arm] = np.stack(runs)
    if not args.qualify:
        if not all(np.isfinite(a).all() for a in forecasts.values()):
            raise ValueError("Missing motion prediction")
        write_npz(args.out / "predictions.npz", forecasts)
    record["elapsed_after_import_s"] = time.perf_counter() - tick
    write_json(args.out / "fit.json", record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--fold", required=True, type=int, choices=range(1, 6))
    parser.add_argument("--threads", required=True, type=int)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--qualify", action="store_true")
    run(parser.parse_args())
