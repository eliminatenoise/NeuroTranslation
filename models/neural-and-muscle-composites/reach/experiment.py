"""Fit or replay the frozen, two-direction, real-recording experiment."""
import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

try:
    import resource
except ImportError:  # Unavailable on Windows.
    resource = None
from data import PROTOCOL, earlier_donors, make_scales, norm, read_archive
from models import Forecaster, HORIZONS, STEPS

ARCHITECTURES = ["ar", "diffusion", "hybrid"]
SEEDS = PROTOCOL["optimizer"]["seeds"]
DRAWS = PROTOCOL["generative"]["draws"]
CONDITIONS = ["both", "pose", "spikes", "wrong"]
TASKS = ["movement", "neural"]


def json_save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def tensor(x, device):
    return torch.as_tensor(x, device=device)


def training_tensors(a, scales, task, device):
    return [tensor(norm(a[k], k, scales), device) for k in ("pose", "counts", task)]


def fit(data, seed, architecture, steps, device):
    p, c, y = data
    torch.manual_seed(seed)
    model = Forecaster(y.shape[-1], architecture, p.shape[-1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=.002, weight_decay=.01, foreach=False)
    rng = np.random.default_rng(seed+100)
    start = time.perf_counter()
    losses = []
    for _ in range(steps):
        row = rng.integers(0, len(y), size=48)
        m = rng.random(48)
        mask = np.column_stack(((m < .8), (m < .6) | (m >= .8))).astype(np.float32)
        ts = tensor(rng.integers(1, STEPS+1, size=48), device)
        index = tensor(rng.integers(HORIZONS, size=48), device)
        eps = tensor(rng.standard_normal((48, HORIZONS, y.shape[-1]), dtype=np.float32), device)
        row = tensor(row, device)
        memory = model.encode(p[row], c[row], tensor(mask, device))
        opt.zero_grad()
        loss = model.error(memory, y[row], ts, eps, index)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
        opt.step()
        losses.append(float(loss.detach()))
    model.eval()
    if architecture == "ar":
        with torch.no_grad():
            memory = model.encode(p, c, torch.ones(len(y), 2, device=device))
            shifted = torch.cat((torch.zeros_like(y[:, :1]), y[:, :-1]), dim=1)
            model.residual_scale.copy_((model.autoregress(memory, shifted)-y).square().mean(0, keepdim=True).sqrt())
    synchronize(device)
    return model, dict(train_seconds=time.perf_counter()-start, parameters=sum(t.numel() for t in model.parameters()),
                       innovation_scales_fitted=(2*y.shape[-1] if architecture=="ar" else 0),
                       initial_loss=losses[0], final_loss=losses[-1], steps=steps)


def synchronize(device):
    if device == "cuda":
        torch.cuda.synchronize()


def save_weights(model, path):
    np.savez_compressed(path, **{k:v.detach().cpu().numpy() for k,v in model.state_dict().items()})


def load_weights(path, target, architecture, device, pose_features=4):
    model = Forecaster(target, architecture, pose_features).to(device)
    with np.load(path, allow_pickle=False) as f:
        model.load_state_dict({k:tensor(f[k], device) for k in f.files}, strict=True)
    return model.eval()


def native_samples(raw, task, scales):
    out = raw*scales[task+"_std"] + scales[task+"_mean"]
    return np.maximum(0, np.rint(out)) if task == "neural" else out


def summarize(draws, truth, task):
    point = draws.mean(axis=1)
    error = point-truth
    primary = np.linalg.norm(error, axis=-1) if task=="movement" else np.mean(error**2, axis=-1)
    k = draws.shape[1]
    # Unbiased ensemble CRPS: empirical absolute error minus half the
    # mean absolute difference over independent, distinct draws.
    weights = (2*np.arange(1,k+1)-k-1).reshape(1,k,1,1)
    sorted_draws = np.sort(draws, axis=1)
    correction = (sorted_draws*weights).sum(axis=1)/(k*(k-1)) if k > 1 else 0
    crps = (np.abs(draws-truth[:, None]).mean(axis=1)-correction).mean(axis=2)
    lo, hi = np.quantile(draws, [.1,.9], axis=1, method="linear")
    covered = ((truth>=lo) & (truth<=hi)).mean(axis=2)
    width = (hi-lo).mean(axis=2)
    return {"primary":primary,"crps":crps,"coverage":covered,"width":width}


@torch.inference_mode()
def generate(model, a, scales, task, seed, condition, device):
    p, c = (norm(a[k], k, scales) for k in ("pose","counts"))
    mask = np.ones((len(p),2), dtype=np.float32)
    valid = np.ones(len(p),dtype=bool)
    if condition == "wrong":
        donor = earlier_donors(a)
        valid = donor >= 0
        safe = np.maximum(donor,0)
        if task=="movement":
            c = c[safe]
        else:
            p = p[safe]
    if condition == "pose":
        mask[:,1] = 0
    if condition == "spikes":
        mask[:,0] = 0
    # Use identical Gaussian innovations for matched conditions/architectures.
    rng = np.random.default_rng(110000+seed*37+int(a["block"][0]))
    z = rng.standard_normal((len(p),DRAWS,2,model.output), dtype=np.float32)
    predictions = []
    synchronize(device)
    start = time.perf_counter()
    for i in range(0,len(p),32):
        idx = slice(i, i+32)
        memory = model.encode(tensor(p[idx],device),tensor(c[idx],device),tensor(mask[idx],device))
        values = model.generate(memory.repeat_interleave(DRAWS, dim=0),tensor(z[idx].reshape(-1,2,model.output),device))
        predictions.append(values.reshape(-1,DRAWS,2,model.output).cpu().numpy())
    synchronize(device)
    seconds = time.perf_counter()-start
    sampled = native_samples(np.concatenate(predictions),task,scales)
    stats = summarize(sampled, a[task], task)
    for value in stats.values():
        value[~valid] = np.nan
    return stats, seconds


def deterministic(train, held, scales, task):
    def design(a):
        return np.concatenate([norm(a[k],k,scales).reshape(len(a[k]),-1) for k in ["pose","counts"]],axis=1).astype(np.float64)
    x, z = design(train), design(held)
    y = train[task].reshape(len(x),-1)
    center = x.mean(0)
    train_x = x-center
    mean = y.mean(0)
    coef = np.linalg.solve(train_x.T@train_x+10*np.eye(x.shape[1]), train_x.T@(y-mean))
    ridge = ((z-center)@coef+mean).reshape(held[task].shape)
    preds = {"mean":np.broadcast_to(train[task].mean(0),held[task].shape),
             "ridge":ridge if task=="movement" else ridge.clip(min=0)}
    if task=="movement":
        preds.update(persistence=np.zeros_like(ridge), velocity=held["velocity"])
    else:
        preds["persistence"] = np.repeat(held["counts"][:, -1:],2,axis=1)
    return {name:summarize(value[:, None],held[task],task)["primary"] for name, value in preds.items()}


def run(args):
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.backends.mha.set_fastpath_enabled(False)
    torch.use_deterministic_algorithms(True)
    if args.device == "cuda":
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_cudnn_sdp(False)
    dest = args.out
    dest.mkdir(exist_ok=True,parents=True)
    start = time.perf_counter()
    train = read_archive(args.data,"train",args.sensor)
    if args.mode in ("fit","probe"):
        scales = make_scales(train)
        np.savez_compressed(dest/"scales.npz", **scales)
        logs = {}
        for task in (TASKS if args.mode=="fit" else ["movement"]):
            data = training_tensors(train,scales,task,args.device)
            for seed in (SEEDS if args.mode=="fit" else [17]):
                for arch in (ARCHITECTURES if args.mode=="fit" else ["hybrid"]):
                    name = f"{task}-{arch}-{seed}"
                    model, logs[name] = fit(data,seed,arch,180 if args.mode=="fit" else 16,args.device)
                    save_weights(model,dest/(name+".npz"))
                    if args.mode=="probe":
                        subset = {k:v[:32] for k,v in train.items()}
                        stats,elapsed = generate(model,subset,scales,task,seed,"both",args.device)
                        np.save(dest/"probe.npy",stats["primary"])
                        logs[name]["inference_seconds"] = elapsed
                    print(name,logs[name]["train_seconds"],flush=True)
        json_save(dest/"training.json",logs)
    else:
        with np.load(args.weights/"scales.npz",allow_pickle=False) as f:
            scales = {k:f[k] for k in f.files}
        logs = {}
        for block in ["block1","block2"]:
            a = read_archive(args.data,block,args.sensor)
            metrics = {key:a[key] for key in ["block","workspace","original","ordinal","k"]}
            for task in TASKS:
                for name, loss in deterministic(train,a,scales,task).items():
                    metrics[task+"/"+name+"/primary"] = loss
                for seed in SEEDS:
                    for arch in ARCHITECTURES:
                        stem = f"{task}-{arch}-{seed}"
                        model = load_weights(args.weights/(stem+".npz"),a[task].shape[-1],arch,args.device,a["pose"].shape[-1])
                        for condition in CONDITIONS:
                            stats, seconds = generate(model,a,scales,task,seed,condition,args.device)
                            key = f"{task}/{arch}/{seed}/{condition}"
                            metrics.update({key+"/"+metric:vals for metric,vals in stats.items()})
                            logs[block+"/"+key] = seconds
                        print(block,stem,flush=True)
            np.savez_compressed(dest/(block+"-scores.npz"),**metrics)
        json_save(dest/"inference.json",logs)
    json_save(dest/"runtime.json",dict(torch=str(torch.__version__),numpy=np.__version__,device=args.device,
             threads=torch.get_num_threads(),interop=torch.get_num_interop_threads(),
             affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
             wall_seconds=time.perf_counter()-start,
             peak_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
             gpu=torch.cuda.get_device_name(0) if args.device=="cuda" else None,
             pressure={k:Path("/proc/pressure",k).read_text() for k in ("cpu","memory","io") if Path("/proc/pressure",k).exists()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["probe","fit","score"])
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--weights",type=Path)
    parser.add_argument("--sensor",choices=["handle","hand"],default="handle")
    parser.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    parser.add_argument("--threads",type=int,default=1)
    opts = parser.parse_args()
    if opts.mode=="score" and not opts.weights:
        parser.error("scoring requires --weights")
    run(opts)
