"""Regenerate all learned parameters from a previously extracted development split."""
import argparse
import hashlib
import json
import os
import resource
import time
from pathlib import Path

from network import (Forecast, calibration, configure, export, inputs, np, predictions,
                     prepare, read_events, restore, sha256, torch, write_json)
from scoring import summarize, extract_errors


def groups(data, ids):
    weights = np.zeros(len(ids), dtype=float)
    people, poses, directions = [data[k][ids] for k in ("person", "posture", "direction")]
    for person in np.unique(people):
        p = people == person
        for pose in np.unique(poses[p]):
            cell = p & (poses == pose)
            for direction in np.unique(directions[cell]):
                group = cell & (directions == direction)
                weights[group] = 1 / (sum(group) * len(np.unique(directions[cell])) * len(np.unique(poses[p])))
    return weights / weights.sum()


def parameter_norm(grads):
    return float(torch.stack([g.detach().square().sum() for g in grads]).sum().sqrt().cpu())


def train(task, data, ids, prepared, scale, steps, device, initial=None, heads_only=False):
    started = time.monotonic()
    torch.manual_seed(9227)
    model = (Forecast(task) if initial is None else restore(initial, task)).to(device).train()
    if heads_only:
        for name, p in model.named_parameters():
            p.requires_grad_(name.startswith(("muscle.", "path.")))
    trunk = [p for n, p in model.named_parameters() if not n.startswith(("muscle.", "path."))]
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                  lr=.002, weight_decay=.005, foreach=False, fused=False)
    targets = [torch.tensor(data[k], device=device, dtype=torch.float32) for k in ("future_rms_uv", "future_path_mm")]
    batches = np.random.default_rng(8134).choice(ids, size=(steps, 96), replace=True, p=groups(data, ids))
    batches_device = torch.tensor(batches, device=device)
    gradients = {}
    for step, batch in enumerate(batches_device):
        y, path = model(*(f[batch] for f in prepared), scale)
        terms = []
        if y is not None:
            terms.append((y - targets[0][batch]).abs().mean() / scale["rms_scale"])
        if path is not None:
            terms.append(torch.linalg.vector_norm(path - targets[1][batch], dim=-1).mean() / scale["path_scale"])
        if task == "joint" and not heads_only and step in (0, steps-1):
            gradients[str(step + 1)] = dict(zip(["muscle_l2", "path_l2"], [
                parameter_norm(torch.autograd.grad(loss, trunk, retain_graph=True)) for loss in terms]))
        optimizer.zero_grad(set_to_none=True)
        (sum(terms) / len(terms)).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2., error_if_nonfinite=True)
        optimizer.step()
    if device == "cuda":
        torch.cuda.synchronize()
    log = dict(seconds=time.monotonic()-started, updates=steps, examples=steps*96, events=len(ids),
               people=len(set(data["person"][ids])), parameters=sum(p.numel() for p in model.parameters()),
               trainable=sum(p.numel() for p in model.parameters() if p.requires_grad),
               trunk_parameters=sum(p.numel() for p in trunk), independent_trunk_gradient_norms=gradients,
               batch_indices_sha256=hashlib.sha256(batches.astype("<i8").tobytes()).hexdigest())
    return model.eval(), log


def fold_assignments(people):
    ordered = sorted(np.unique(people), key=lambda label: hashlib.sha256(
        ("paired-emg-motion-fold-1/" + str(label)).encode()).hexdigest())
    return {person: i % 3 for i, person in enumerate(ordered)}


def fit(args):
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    data = read_events(args.development)
    features = inputs(data)
    all_ids = np.flatnonzero(data["paired"])
    folds = fold_assignments(data["person"][all_ids])
    scale = calibration(features, data, all_ids)
    cfg = prepare(features, scale, args.device)
    if args.benchmark:
        m, log = train("joint", data, all_ids, cfg, scale, 16, args.device)
        test = predictions(m, [t[all_ids[:96]] for t in cfg], scale)
        write_json(dest/"prefix-weights.json", export(m))
        np.savez(dest/"prefix-predictions.npz", rms=test[0], path=test[1])
        log.update(threads=torch.get_num_threads(), interop=torch.get_num_interop_threads(), device=args.device,
                   torch=torch.__version__, numpy=np.__version__, hip=torch.version.hip,
                   device_name=torch.cuda.get_device_name(0) if args.device == "cuda" else "cpu",
                   gpu_peak_bytes=torch.cuda.max_memory_allocated() if args.device == "cuda" else None,
                   maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, affinity=sorted(os.sched_getaffinity(0)),
                   psi={name:Path("/proc/pressure",name).read_text() for name in ("cpu","memory","io")})
        write_json(dest/"benchmark.json", log)
        return
    logs, validation, final_weights = {}, {}, {}
    for fold in [0, 1, 2, "all"]:
        if fold == "all":
            ids, held, sc, prepared = all_ids, None, scale, cfg
        else:
            ids = all_ids[[folds[p] != fold for p in data["person"][all_ids]]]
            held = all_ids[[folds[p] == fold for p in data["person"][all_ids]]]
            sc = calibration(features, data, ids)
            prepared = prepare(features, sc, args.device)
        per_model = {}
        for task in ("joint", "muscle", "path"):
            m, log = train(task, data, ids, prepared, sc, 640, args.device)
            logs[f"{fold}/{task}"] = log
            if held is None:
                final_weights[task] = export(m)
            else:
                per_model[task] = predictions(m, [a[held] for a in prepared], sc)
        if held is not None:
            if args.private_evidence:
                args.private_evidence.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(args.private_evidence/f"fold-{fold}.npz", indices=held, joint_rms=per_model["joint"][0], joint_path=per_model["joint"][1], specialist_rms=per_model["muscle"][0], specialist_path=per_model["path"][1])
            both = {"joint":per_model["joint"], "specialists":(per_model["muscle"][0],per_model["path"][1])}
            for name,(yr,yp) in both.items():
                validation.setdefault(name,[]).append((held,extract_errors(data, held, yr, yp)))
        print("Completed primary models", fold, flush=True)
    write_json(dest/"weights.json", dict(schema_version=1, scale=scale, models=final_weights))
    internal = {}
    for name, parts in validation.items():
        internal[name] = summarize(data, np.concatenate([ids for ids,_ in parts]),np.concatenate([err for _,err in parts]))[0]
    walk, stand = (all_ids[data["posture"][all_ids] == pose] for pose in (1,0))
    transfer_scale = calibration(features,data,walk)
    transfer_data = prepare(features,transfer_scale,args.device)
    tw = {}
    for name,ids,origin,head_only in [
            ("walk",walk,None,False), ("adapt_heads",stand,"walk",True),
            ("adapt_full",stand,"walk",False), ("stand_640",stand,None,False),
            ("stand_1280",stand,"stand_640",False)]:
        m, log = train("joint",data,ids,transfer_data,transfer_scale,640,args.device,
                       initial=tw.get(origin),heads_only=head_only)
        logs[f"transfer/{name}"] = {**log, "inherited_weights":origin}
        tw[name] = export(m)
        print("Completed transfer model",name,flush=True)
    write_json(dest/"transfer-weights.json",dict(schema_version=1,scale=transfer_scale,models=tw))
    write_json(dest/"development-summary.json",dict(folds=3,people=len(folds),events=len(all_ids),
               out_of_fold=internal, fits=logs, total_updates=sum(v["updates"] for v in logs.values()),
               torch=torch.__version__,numpy=np.__version__,threads=torch.get_num_threads(),device=args.device))
    print("Development array digest",sha256(args.development),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--private-evidence",type=Path)
    parser.add_argument("--benchmark",action="store_true")
    parser.add_argument("--threads",type=int,default=1)
    parser.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    a=parser.parse_args()
    configure(a.threads)
    fit(a)
