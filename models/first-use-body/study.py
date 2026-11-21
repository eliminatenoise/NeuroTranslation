"""Train, freeze predictions, then score a manifest of independent optical recordings."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from forecaster import GEOMETRY, HISTORY, METHODS, PROTOCOL, forecast, mix, norms, observe, read_weights

HERE = Path(__file__).resolve().parent
STRESS = ("observed", "20pct_hidden")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def code_hashes():
    return {name: digest(HERE / name) for name in ("protocol.json", "forecaster.py", "study.py")}


def records(manifest, split, alternate=None):
    full = json.loads(manifest.read_text())["records"]
    if alternate:
        plan = json.loads(alternate.read_text())
        train, test = set(plan["mixed_train"]), set(plan["common_test"])
        if train & test:
            raise ValueError("A mixed comparison group crosses the split")
        full = [dict(r, split="train" if r["group"] in train else "test") for r in full
                if r["group"] in train | test]
    groups = defaultdict(set)
    ids = set()
    for row in full:
        if row["id"] in ids:
            raise ValueError("Duplicate track name")
        ids.add(row["id"])
        groups[row["group"]].add(row["split"])
    if any(len(splits) > 1 for splits in groups.values()):
        raise ValueError("Recording group crosses a split")
    rows = []
    for row in full:
        if row["split"] != split:
            continue
        path = manifest.parent / row["path"]
        if path.is_absolute() and not path.resolve().is_relative_to(manifest.parent.resolve()):
            raise ValueError("Track file lies outside manifest tree")
        if "/" in row["id"] or row["id"] in (".", ".."):
            raise ValueError("Unsafe track ID")
        rows.append(dict(row, file=path))
    if not rows:
        raise ValueError(f"No {split} records")
    return sorted(rows, key=lambda r: r["id"])


def load(row):
    source_hash = row.get("sha256") or row.get("npz_sha256")
    if source_hash and digest(row["file"]) != source_hash:
        raise ValueError("Recording SHA256 mismatch: " + row["id"])
    with np.load(row["file"], allow_pickle=False) as data:
        xy, t = data["xy"].astype(float), data["seconds"].astype(float)
    if xy.ndim != 3 or xy.shape[-1] != 2 or t.shape != xy.shape[:1] or len(t) < HISTORY+1:
        raise ValueError("Invalid record dimensions")
    if not np.isfinite(t).all() or not (np.diff(t) > 0).all():
        raise ValueError("Invalid timestamps")
    return xy, t


def windows(xy, t, maximum):
    gaps = np.diff(t)
    nominal = PROTOCOL["low_rate_horizon_s"] if np.median(gaps) > .12 else PROTOCOL["horizon_s"]
    valid = np.isfinite(xy).all(2)
    counts = np.concatenate([np.zeros((1, xy.shape[1]), int), valid.cumsum(0)])
    origins = np.arange(HISTORY-1, len(t)-1)
    enough = counts[origins+1] - counts[origins+1-HISTORY] >= PROTOCOL["minimum_observations_per_point_including_origin"]
    gaps_ok = np.lib.stride_tricks.sliding_window_view(gaps, HISTORY-1).max(1)[:-1]
    eligible = (enough & valid[origins]).any(1) & (gaps_ok <= PROTOCOL["maximum_interframe_gap_s"])
    eligible &= t[origins]-t[origins-HISTORY+1] <= PROTOCOL["maximum_history_span_s"]
    origins = origins[eligible]
    i = np.searchsorted(t, t[origins] + nominal)
    hi = np.minimum(i, len(t)-1)
    lo = np.maximum(hi-1, origins+1)
    desired = t[origins] + nominal
    target = np.where(abs(t[hi]-desired) < abs(t[lo]-desired), hi, lo)
    within = (target > origins) & (abs(t[target] - desired) <= PROTOCOL["horizon_tolerance_s"] + 1e-10)
    candidates, prior_time = [], -np.inf
    for o, e in zip(origins[within], target[within]):
        if t[o] >= prior_time + PROTOCOL["origin_stride_s"] - 1e-10:
            candidates.append((int(o), int(e)))
            prior_time = t[o]
    if len(candidates) > maximum:
        candidates = [candidates[i] for i in np.linspace(0, len(candidates)-1, maximum).astype(int)]
    return nominal, candidates


def training_rows(rows):
    parts, track_groups = [], {}
    for row in rows:
        xy, t = load(row)
        _, eligible = windows(xy, t, PROTOCOL["max_train_origins_per_track"])
        group, track = row["group"], row["id"]
        chunks = []
        for o, e in eligible:
            selected = slice(o-HISTORY+1, o+1)
            obs = observe(xy[selected], t[selected], t[e]-t[o])
            radius, selected_points = obs["radius"], obs["valid"]
            target = (xy[e, selected_points] - xy[o, selected_points])
            measured = np.isfinite(target).all(1)
            if radius <= 0 or not measured.any():
                continue
            chunks.append((obs["features"][measured], obs["proposals"][measured]/radius,
                           target[measured]/radius))
        if not chunks:
            continue
        track_groups[track] = group
        for features, proposals, target in chunks:
            n = len(features)
            parts.append((features, proposals, target, np.full(n, 1/(len(chunks)*n)),
                          np.full(n, track), np.full(n, group)))
    if not parts:
        raise ValueError("No measured training endpoints")
    x, p, y, w, ids, groups = (np.concatenate(column) for column in zip(*parts))
    tracks_per_group = {g: sum(gg == g for gg in track_groups.values()) for g in set(groups)}
    for g, n in tracks_per_group.items():
        w[groups == g] /= n
    return x, p, y, w, ids, groups


def balance_phyla(weights, groups, mapping):
    for phylum in set(mapping[g] for g in set(groups)):
        same = np.array([mapping[g] == phylum for g in groups])
        weights[same] /= len(set(groups[same]))
    return weights


def train(arrays, selected, use_shape, threads, mapping):
    import torch
    from torch import nn

    torch.set_num_threads(threads)
    torch.manual_seed(PROTOCOL["seed"])
    x, p, y, weights = [a[selected] for a in arrays[:4]]
    weights = balance_phyla(weights.copy(), arrays[5][selected], mapping)
    x = x.copy()
    if not use_shape:
        x[:, -GEOMETRY:] = 0.
    x, p, y = [torch.from_numpy(a.astype(np.float32)) for a in (x, p, y)]
    model = nn.Sequential(nn.Linear(x.shape[1], PROTOCOL["hidden"]), nn.Tanh(),
                          nn.Linear(PROTOCOL["hidden"], p.shape[1]))
    optimizer = torch.optim.Adam(model.parameters(), lr=PROTOCOL["adam_lr"])
    rng = np.random.default_rng(PROTOCOL["seed"])
    losses = []
    for _ in range(PROTOCOL["adam_steps"]):
        i = rng.choice(len(x), size=PROTOCOL["batch_size"], p=weights/weights.sum())
        gates = torch.softmax(model(x[i]), 1)
        d = (gates.unsqueeze(-1) * p[i]).sum(1) - y[i]
        loss = (.01 * (torch.sqrt(1 + (d*d).sum(1)/.01) - 1)).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    w1, b1, w2, b2 = [v.detach().numpy().astype(float) for v in model.parameters()]
    result = dict(w1=w1.T, b1=b1, w2=w2.T, b2=b2)
    return result, {"first_16_batch_loss": float(np.mean(losses[:16])),
                    "last_16_batch_loss": float(np.mean(losses[-16:]))}


def fit(args):
    import torch
    torch.set_num_interop_threads(1)
    start = time.perf_counter()
    rows = records(args.manifest, "train", args.mixed)
    mapping = {r["group"]: r["phylum"] for r in rows}
    arrays = training_rows(rows)
    x,p,y,w,ids,groups = arrays
    if len(set(groups)) < 2:
        raise ValueError("Two independent training groups required")
    timing = {"prepare_s": time.perf_counter()-start}
    all_weights, logs = {}, {}
    radii = {}
    for label in ("shape", "no_shape"):
        flag = label == "shape"
        before = time.perf_counter()
        model, details = train(arrays, np.ones(len(x), bool), flag, args.threads, mapping)
        all_weights[label] = {k: a.tolist() for k,a in model.items()}
        errors, probabilities = [], []
        for g in np.unique(groups):
            held = groups == g
            cv, _ = train(arrays, ~held, flag, args.threads, mapping)
            errors.extend(norms(mix(x[held], p[held], cv, flag) - y[held]))
            probabilities.extend(w[held]/w[held].sum()/len(set(groups)))
        order = np.argsort(errors, kind="stable")
        cdf = np.cumsum(np.array(probabilities)[order])
        radii[label] = float(np.array(errors)[order][np.searchsorted(cdf,.9)])
        logs[label] = details
        timing[label+"_fit_and_train_group_holdouts_s"] = time.perf_counter()-before
    args.out.mkdir(parents=True, exist_ok=True)
    save(args.out/"weights.json", {"version":1,"models":all_weights})
    save(args.out/"freeze.json", {"utc":datetime.now(timezone.utc).isoformat(),"code":code_hashes(),
         "weights_sha256":digest(args.out/"weights.json"),"manifest":digest(args.manifest),
         "train_hashes":{r["id"]:digest(r["file"]) for r in rows},"groups":sorted(set(groups)),
         "points":len(x),"tracks":len(set(ids)),"radii_q90":radii,"logs":logs,"timing":timing,
         "phylum_by_group": mapping, "mixed_plan": digest(args.mixed) if args.mixed else None,
         "seed":PROTOCOL["seed"],"cpu_threads":torch.get_num_threads(),"interop":torch.get_num_interop_threads(),
         "torch":torch.__version__,"numpy":np.__version__})
    print("Fitted",len(x),"point examples;",len(set(groups)),"groups;",digest(args.out/"freeze.json"))


def check_freeze(args):
    frozen = json.loads((args.fit/"freeze.json").read_text())
    if frozen["code"] != code_hashes() or frozen["weights_sha256"] != digest(args.fit / "weights.json"):
        raise ValueError("Frozen code/weights changed")
    return frozen


def predict(args):
    frozen = check_freeze(args)
    rows = records(args.manifest, "test", args.mixed)
    if frozen["mixed_plan"] != (digest(args.mixed) if args.mixed else None):
        raise ValueError("Prediction allocation differs from training")
    if set(frozen["groups"]) & {r["group"] for r in rows}:
        raise ValueError("A held recording occurred in fit")
    train_hashes = set(frozen["train_hashes"].values())
    weights = read_weights(args.fit / "weights.json")
    args.out.mkdir(parents=True, exist_ok=True)
    index = []
    tick = time.perf_counter()
    inference_times = []
    for row in rows:
        record_hash = digest(row["file"])
        if record_hash in train_hashes:
            raise ValueError("Held recording file repeats training data")
        xy, t = load(row)
        nominal, pairs = windows(xy,t,PROTOCOL["max_test_origins_per_track"])
        pred = np.full((len(pairs),len(STRESS),len(METHODS),xy.shape[1],2),np.nan)
        radii = np.full((len(pairs),len(STRESS)),np.nan)
        history = np.array([t[o]-t[o-HISTORY+1] for o,_ in pairs])
        for j,(o,e) in enumerate(pairs):
            sel = slice(o-HISTORY+1,o+1)
            for s,condition in enumerate(STRESS):
                prefix = xy[sel].copy()
                if s:
                    token = f"{PROTOCOL['seed']}|{row['id']}|{o}".encode()
                    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(token).digest()[:8],"big"))
                    prefix[rng.random(prefix.shape[:2]) < .2] = np.nan
                before = time.perf_counter_ns()
                estimated = forecast(prefix,t[sel],t[e]-t[o],weights,all_methods=True)
                inference_times.append((time.perf_counter_ns()-before)/1e6)
                pred[j,s] = np.stack([estimated[m] for m in METHODS])
                ok = np.isfinite(estimated["shape"]).all(1)
                if ok.any():
                    points = prefix[-1,ok]
                    radii[j,s] = np.sqrt(np.mean(norms(points-points.mean(0))**2))
        name = row["id"]+".npz"
        coordinates = np.asarray(pairs, dtype=int).reshape((-1,2))
        np.savez_compressed(args.out/name, pairs=coordinates, history_s=history,
                            first_wait_s=np.array([t[o]-t[0] for o,_ in pairs[:1]]),
                            horizon_s=t[coordinates[:,1]]-t[coordinates[:,0]], radius=radii, pred=pred)
        index.append({"id":row["id"],"group":row["group"],"species":row["species"],
                      "phylum":row["phylum"],"units":row["units"],"nominal_s":nominal,
                      "source_sha256":record_hash,"file":name,"sha256":digest(args.out/name)})
    save(args.out/"predictions.json",{"utc":datetime.now(timezone.utc).isoformat(),
         "freeze":digest(args.fit/"freeze.json"),"manifest":digest(args.manifest),"methods":METHODS,
         "conditions":STRESS,"tracks":index,"elapsed_s":time.perf_counter()-tick,
         "all_six_model_cpu_ms_p50_p95":np.percentile(inference_times,[50,95]).tolist()})
    print("Frozen",len(index),"tracks;",digest(args.out/"predictions.json"))


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(required=True)
    f=sub.add_parser("fit"); f.set_defaults(func=fit)
    f.add_argument("manifest",type=Path); f.add_argument("out",type=Path)
    f.add_argument("--threads",type=int,default=1)
    p=sub.add_parser("predict"); p.set_defaults(func=predict)
    for name in ("manifest","fit","out"):
        p.add_argument(name,type=Path)
    for command in (f,p):
        command.add_argument("--mixed",type=Path)
    opts=ap.parse_args()
    opts.func(opts)
