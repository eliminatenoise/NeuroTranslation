"""Reproduce the five-placement TRAIN study from the UCI archive."""
import argparse
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import resource
import statistics
import time
from zipfile import ZipFile

import numpy as np
import torch

from aligned_forecast import validate_aligned_forecast
from broader_learner import configure_cpu_runtime, masked_nll
from model import (BATCH, HERE, MOTION, PARTS, PLAN, PROTOCOL, TASK_SPEC, Events, digest,
                   direction, estimate, load_checkpoint, make_model, observation, source, targets)

O = PLAN["optimizer"]
CUTOFFS = np.array(PLAN["cutoffs_zero_based"])
PEOPLE = tuple(PLAN["train_people"])
ACTIVITIES = tuple(PLAN["activities"])
PARENT_NAMES = tuple(PLAN["member_template"].format(person=p, activity=a, segment=s)
                     for a in ACTIVITIES for p in PEOPLE for s in range(1, 61))
PARENTS = frozenset(PARENT_NAMES)
SOURCES = ("model.py", "aligned_forecast.py", "broader_learner.py")
DIRECT_HASH = "96018afd0b6f5e38f6af721a540a1b6bca55b0f4c7c4a321c535b3d2722d873b"


def save(path, obj):
    with path.open("x") as out:
        json.dump(obj, out, indent=2, allow_nan=False)
        out.write("\n")


@dataclass
class Data:
    part: str
    members: np.ndarray
    cutoffs: np.ndarray
    histories: np.ndarray
    events: Events

    def batch(self, indices):
        members = tuple(self.members[indices].tolist())
        obs, query = observation(self.part, members, self.cutoffs[indices], self.histories[indices], "TRAIN")
        ev = self.events
        labels = targets(Events(ev.part, tuple(ev.members[i] for i in indices),
                                ev.rows[indices], ev.values[indices]))
        if not set(members) <= PARENTS:
            raise ValueError("Unadmitted TRAIN participant or segment")
        validate_aligned_forecast(TASK_SPEC, obs, query, labels, {MOTION: source(self.part)})
        return obs, query, labels


def collect(records):
    histories = {part: [] for part in PARTS}
    measured = {part: [] for part in PARTS}
    members, cutoffs, actual_rows, event_members = [], [], [], []
    for member, raw in records:
        if member not in PARENTS or raw.shape != (125, 15) or not np.isfinite(raw).all():
            raise ValueError("Unexpected member, selected sensor shape or values")
        events = list(enumerate(raw))
        for cutoff in CUTOFFS:
            row, label = events[cutoff + PLAN["lead_rows"]]
            members.append(member)
            cutoffs.append(cutoff)
            event_members.append(member)
            actual_rows.append(row)
            for i, part in enumerate(PARTS):
                xyz = slice(3*i, 3*i + 3)
                histories[part].append(raw[cutoff - 15:cutoff + 1, xyz])
                measured[part].append(label[xyz])
    return {part: Data(part, np.array(members), np.array(cutoffs), np.stack(histories[part]),
                       Events(part, tuple(event_members), np.array(actual_rows), np.stack(measured[part])))
            for part in PARTS}


def read_archive(path):
    if digest(path) != PLAN["source"]["archive_sha256"]:
        raise ValueError("Different UCI source archive")
    columns = [c for triple in PLAN["channels_zero_based"].values() for c in triple]
    if tuple(PEOPLE) != ("p1", "p2", "p3", "p4") or len(set(PARENT_NAMES)) != 480:
        raise ValueError("TRAIN source manifest differs from the study")
    with ZipFile(path) as archive:
        for member in PARENT_NAMES:
            with archive.open(member) as stream:
                raw = np.loadtxt(stream, delimiter=",", usecols=columns)
            yield member, raw


def moments(data):
    result = {}
    for part, ds in data.items():
        center = ds.histories.mean(axis=(0, 1))
        scale = ds.histories.std(axis=(0, 1))
        if (scale <= 0).any() or not np.isfinite([center, scale]).all():
            raise ValueError(f"Unusable TRAIN input scale for {part}")
        result[part] = {"center": center.tolist(), "scale": scale.tolist()}
    return result


def optimizer_for(model):
    return torch.optim.AdamW(model.parameters(), lr=O["learning_rate"], betas=tuple(O["adam_betas"]),
                             eps=O["adam_epsilon"], weight_decay=O["weight_decay"])


def update(model, optimizer, part, batch):
    obs, query, labels = batch
    if obs.modalities[MOTION].source_id != source(part):
        raise ValueError("Input sensor differs from selected body part")
    optimizer.zero_grad(set_to_none=True)
    predicted = model.forecast(obs, query.grid, direction(part))
    loss, _, _ = masked_nll(model, predicted, {MOTION: labels[MOTION].record},
                            query.grid.valid_steps, {MOTION: 1}, obs)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), O["max_gradient_norm"], error_if_nonfinite=True)
    optimizer.step()
    return loss.item()


def predict_all(model, ds):
    means, variances = [], []
    for i in range(0, len(ds.cutoffs), BATCH):
        ids = np.arange(i, min(i+BATCH, len(ds.cutoffs)))
        obs, query, _ = ds.batch(ids)
        m, v = estimate(model, ds.part, obs, query)
        means.append(m)
        variances.append(v)
    return np.concatenate(means), np.concatenate(variances)


def direct_reference():
    base = HERE.parent / "daily-sports-arm"
    if digest(base / "model.pt") != DIRECT_HASH:
        raise ValueError("Frozen external right-arm model changed")
    spec = importlib.util.spec_from_file_location("direct_arm_reference", base / "forecast.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    model, state = mod.load(base / "model.pt")
    if state["implementation"] != digest(base / "forecast.py"):
        raise ValueError("Frozen right-arm reference code changed")
    return mod, model, state


def baselines(ds, stats, direct):
    part = ds.part
    x, y = ds.histories, ds.events.values
    center, scale = np.array(stats["center"]), np.array(stats["scale"])
    xn, yn = (x - center) / scale, (y - center) / scale
    mod, prior, state = direct
    result = {"persistence": x[:, -1]}
    if part == "right_arm":
        np.testing.assert_allclose(center, state["center"].numpy(), rtol=0, atol=1e-12)
        np.testing.assert_allclose(scale, state["scale"].numpy(), rtol=0, atol=1e-12)
        original = mod.predict_all(prior, state, x)
        result["ridge"] = original["ridge"]
        result["direct_right_arm"] = original["transformer"]
        coef, intercept = state["ridge"].numpy(), state["intercept"].numpy()
    else:
        coef, intercept = mod.fit_ridge(xn, yn)
        residual = xn.reshape(len(xn), -1) @ coef + intercept
        result["ridge"] = (xn[:, -1] + residual) * scale + center
    return result, {"coef": torch.from_numpy(coef), "intercept": torch.from_numpy(intercept)}


def summarize(ds, predictions, variance):
    target = ds.events.values
    errors = {name: abs(values - target) for name, values in predictions.items()}
    parts = [s.split("/") for s in ds.members]
    people = np.array([m[2] for m in parts])
    acts = np.array([m[1] for m in parts])
    masks = {"all": np.ones(len(target), dtype=bool), **{p: people == p for p in PEOPLE},
             **{a: acts == a for a in ACTIVITIES},
             **{f"{p}/{a}": (people == p) & (acts == a) for p in PEOPLE for a in ACTIVITIES}}
    half = 1.959963984540054 * np.sqrt(variance)
    scores = {}
    for key, mask in masks.items():
        scores[key] = {"windows": int(mask.sum()), "mae": {n: float(e[mask].mean()) for n,e in errors.items()},
                       "mae_xyz": {n: e[mask].mean(0).tolist() for n,e in errors.items()},
                       "interval_coverage_xyz": (errors["shared"][mask] <= half[mask]).mean(0).tolist(),
                       "mean_interval_width_xyz": (2*half[mask]).mean(0).tolist()}
    wins = all(scores[p]["mae"]["shared"] < scores[p]["mae"][m]
               for p in PEOPLE for m in errors if m != "shared")
    return {"strict_train_superiority": wins, "scores": scores}


def synthetic(threads):
    started = time.perf_counter()
    rng = np.random.default_rng(41092)
    data = collect((m, rng.normal(size=(125, 15))) for m in PARENT_NAMES[:10])
    stats = moments(data)
    model = make_model(stats, PARENT_NAMES[:10]).train()
    opt = optimizer_for(model)
    times, losses = [], []
    for i in range(25):
        part = PARTS[i % len(PARTS)]
        ids = np.arange(BATCH)
        t = time.perf_counter()
        losses.append(update(model, opt, part, data[part].batch(ids)))
        times.append(time.perf_counter()-t)
    return {"threads": threads, "median_last_20": statistics.median(times[5:]), "losses": losses,
            "elapsed_body_s": time.perf_counter()-started, "affinity": sorted(os.sched_getaffinity(0)),
            "torch": str(torch.__version__), "numpy": np.__version__}


def fit(archive, out):
    start = time.perf_counter()
    out.mkdir(parents=True, exist_ok=True)
    save(out/"intent.json", {"protocol_sha256": digest(PROTOCOL), "study": PLAN["edition"]})
    data = collect(read_archive(archive))
    for ds in data.values():
        if tuple(ds.members[::7]) != PARENT_NAMES or len(ds.cutoffs) != 3360:
            raise ValueError("Source membership changed")
    stats = moments(data)
    direct = direct_reference()
    prior, ridge = {}, {}
    for part in PARTS:
        prior[part], ridge[part] = baselines(data[part], stats[part], direct)
    model = make_model(stats, PARENT_NAMES).train()
    opt = optimizer_for(model)
    rng = np.random.default_rng(O["seed"])
    loss_by_epoch = []
    for epoch in range(O["epochs"]):
        order = {p: rng.permutation(len(data[p].cutoffs)) for p in PARTS}
        losses = []
        for n in range(0, len(order[PARTS[0]]), BATCH):
            for part in rng.permutation(PARTS):
                idx = order[part][n:n+BATCH]
                losses.append(update(model, opt, part, data[part].batch(idx)))
        loss_by_epoch.append(float(np.mean(losses)))
    model.eval()
    path = out/"model.pt"
    torch.save({"weights": model.state_dict(), "parts": list(PARTS), "stats": stats, "ridge": ridge,
                "parents": list(PARENT_NAMES), "protocol_sha256": digest(PROTOCOL),
                "model_sources": {n: digest(HERE/n) for n in SOURCES}}, path)
    restored, _ = load_checkpoint(path)
    report = {}
    recorded = {}
    for part, ds in data.items():
        mu, var = predict_all(model, ds)
        mu2, var2 = predict_all(restored, ds)
        np.testing.assert_array_equal(mu, mu2)
        np.testing.assert_array_equal(var, var2)
        predictions = {**prior[part], "shared": mu}
        report[part] = summarize(ds, predictions, var)
        recorded.update({f"{part}_{n}": v for n,v in {**predictions,"target": ds.events.values, "variance": var}.items()})
    np.savez_compressed(out/"train-arrays.npz", members=data[PARTS[0]].members, cutoffs=data[PARTS[0]].cutoffs, **recorded)
    save(out/"results.json", {"edition":PLAN["edition"], "protocol_sha256":digest(PROTOCOL),
         "archive_sha256":PLAN["source"]["archive_sha256"],"checkpoint_sha256":digest(path),
         "training_implementation_sha256":digest(HERE/"train.py"),"parameters":sum(p.numel() for p in model.parameters()),
         "people":list(PEOPLE),"activities":list(ACTIVITIES),"members":480,"windows_per_placement":3360,
         "updates":len(losses)*len(loss_by_epoch), "epoch_nll_batch_means":loss_by_epoch,
         "restored_max_abs_difference":0,"scope":"TRAIN development only; p5-p8 excluded", "regions":report})
    save(out/"runtime.json", {"whole_fit_s":time.perf_counter()-start,"max_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "threads":torch.get_num_threads(),"interop":torch.get_num_interop_threads(),"device":"cpu","affinity":sorted(os.sched_getaffinity(0)),
        "torch":str(torch.__version__),"numpy":np.__version__,"evidence_sha256":digest(out/"train-arrays.npz")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["synthetic","fit"])
    parser.add_argument("--threads", required=True, type=int, choices=[1,2])
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    configure_cpu_runtime(args.threads, 1, True)
    if args.action == "synthetic":
        print(json.dumps(synthetic(args.threads), allow_nan=False))
    elif args.archive is None or args.out is None:
        parser.error("fit requires --archive and a fresh --out")
    else:
        fit(args.archive, args.out)
