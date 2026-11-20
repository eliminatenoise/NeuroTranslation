"""Exploratory leave-one-recording-out fallback. Source filename prefixes retain their original values."""
import argparse
from pathlib import Path
import time

import numpy as np
import torch

from train import (BATCH, CHANNELS, MODES, SEEDS, STEPS, draw_plan, earlier_rows, export,
                   fit_one, normalizer, predict, save_json, sha256)


def source_windows(path):
    with np.load(path, allow_pickle=False) as src:
        x = src["X"].astype(np.float64, copy=True)
        x[:, :, :2] = src["mech_mean"]
        info = {name: src[name] for name in ("afferent","trial","bin_index","prefix","y_count")}
    n = len(x)
    assert x.shape == (n,5,5) and np.isfinite(x).all()
    assert (x[:,:,4] >= 0).all() and np.equal(x[:,:,4], np.floor(x[:,:,4])).all()
    assert all(v.shape == (n,) for v in info.values())
    assert np.issubdtype(info["y_count"].dtype, np.integer) and (info["y_count"] >= 0).all()
    assert np.unique(info["afferent"]).size >= 3 and "aff015" in info["afferent"]
    return x, info


def group_trials(info, held_afferent):
    groups = []
    for aff in np.unique(info["afferent"]):
        if aff == held_afferent:
            continue
        rows = np.flatnonzero(info["afferent"] == aff)
        assert np.unique(info["prefix"][rows]).size == 1
        groups.append([rows[info["trial"][rows] == t] for t in np.unique(info["trial"][rows])])
    return groups


def run(args):
    start = time.monotonic()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested GPU unavailable")
    args.out.mkdir(parents=True, exist_ok=True)
    x, info = source_windows(args.data)
    afferents = np.unique(info["afferent"]).tolist()
    earlier = earlier_rows(info)
    full = args.task == "fit"
    folds = afferents if full else ["aff015"]
    seeds = SEEDS if full else [1641]
    modes = list(MODES)
    branches = modes if full else ["all"]
    steps = 24 if args.task == "bench" else STEPS
    y = torch.as_tensor(info["y_count"], dtype=torch.float32, device=args.device)
    rates = np.full((len(x),len(modes),len(SEEDS)), np.nan, np.float32)
    wrong = np.full((len(x),len(SEEDS)), np.nan, np.float32)
    details = []
    plans = {}
    for held in folds:
        groups = group_trials(info, held)
        rows = np.flatnonzero(info["afferent"] == held)
        shifted = rows[earlier[rows] >= 0]
        mean, sd = normalizer(x, groups)
        inputs = torch.as_tensor(np.clip((x-mean)/sd,-10,10), dtype=torch.float32, device=args.device)
        for seed in seeds:
            plan = draw_plan(groups, seed, afferents.index(held))
            assert np.all(info["afferent"][plan] != held)
            plans[f"{held}-seed{seed}"] = plan
            batches = torch.as_tensor(plan, device=args.device)
            for mode in branches:
                before = time.monotonic()
                model, mask = fit_one(inputs, y, batches, seed, mode, steps, args.device)
                elapsed = time.monotonic()-before
                details.append({"held_afferent":held,"mode":mode,"seed":seed,"seconds":elapsed})
                if args.task == "bench":
                    probe = np.unique(plan[:4].ravel())
                    save_json(args.out/f"bench-{args.device}-{args.threads}.json",{
                      "seconds_fit":elapsed,"seconds_total":time.monotonic()-start,
                      "threads":torch.get_num_threads(),"interop":torch.get_num_interop_threads(),"device":args.device,
                      "backend": torch.cuda.get_device_name(0) if args.device=="cuda" else "cpu",
                      "torch":torch.__version__,"hip":torch.version.hip,"numpy":np.__version__,
                      "probe":predict(model,inputs,probe,mask).tolist()})
                    return
                ck = export(model,(mean,sd),None,seed,mode)
                del ck["held_prefix"]
                ck.update(held_afferent=held,split_unit="individual afferent recording",
                          population="strict two-clock exploratory leave-one-afferent-out",
                          training_afferents=[a for a in afferents if a!=held])
                name = f"{held}-seed{seed}-{mode}.json"
                if args.task == "refit":
                    save_json(args.out/name, ck)
                    np.save(args.out/"refit.npy", predict(model,inputs,rows,mask))
                    return
                dest = args.out/"checkpoints"
                dest.mkdir(exist_ok=True)
                save_json(dest/name, ck)
                si = SEEDS.index(seed)
                rates[rows,modes.index(mode),si] = predict(model,inputs,rows,mask)
                if mode == "all":
                    wrong[shifted,si] = predict(model,inputs,shifted,mask,earlier)
    ok = earlier >= 0
    assert np.isfinite(rates).all() and (rates>0).all()
    assert np.isfinite(wrong[ok]).all() and (wrong[ok]>0).all() and np.isnan(wrong[~ok]).all()
    np.savez_compressed(args.out/"oof.npz",**info, modes=np.array(modes), seeds=SEEDS, rate=rates,
                        wrong_mechanics=wrong, earlier_row=earlier, available_wrong=ok)
    np.savez_compressed(args.out/"train-row-samples.npz",**plans)
    save_json(args.out/"fit-run.json",{"seconds":time.monotonic()-start,"fits":details,"data_sha256":sha256(args.data),
                "params_per_fit":sum(p.numel() for p in model.parameters()),"device":args.device,"threads":args.threads,
                "interop":torch.get_num_interop_threads(),"torch":torch.__version__,"numpy":np.__version__,
                "grouping":"leave one strict afferent out","held_afferents":afferents,"original_prefixes":np.unique(info["prefix"]).tolist()})


if __name__=="__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("task",choices=("fit","refit","bench"))
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--threads",type=int,default=1)
    p.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    run(p.parse_args())
