"""Auditable alignment, nonlinear motion features and weighted ridge regression for JS14."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from dataclasses import dataclass
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / "protocol.json").read_text())
UNITS = np.array(PROTOCOL["source"]["unit_id"])
RUN_START = PROTOCOL["source"]["epoch_start_s"]
OFFSETS = np.arange(-4, 1) / 4
LAG = 0.25


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_trial(base, part, trial_id):
    if part not in {"train", "test"} or trial_id not in PROTOCOL["split"][part]:
        raise ValueError("Trial outside the registered role")
    path = Path(base) / part / f"trial-{trial_id:03}.npz"
    with np.load(path, allow_pickle=False) as source:
        trial = {k: source[k] for k in source.files}
    ts, xy = trial["tracking_time_s"], trial["xy_cm"]
    start, stop = float(trial["start_s"]), float(trial["stop_s"])
    events, ends = trial["spike_time_s"], trial["spike_end"]
    if (int(trial["trial_id"]) != trial_id or not np.array_equal(trial["unit_id"], UNITS)
        or ts.shape != trial["camera_row"].shape or xy.shape != (len(ts), 2)
        or np.any(np.diff(ts) <= 0) or np.any(np.diff(trial["camera_row"]) <= 0)
        or not (RUN_START <= start < stop <= PROTOCOL["source"]["epoch_stop_s"])
        or np.any(~np.isfinite(ts)) or np.any((ts <= start) | (ts >= stop))
        or np.any(~np.isfinite(events)) or np.any((events <= start) | (events >= stop))
        or ends.shape != UNITS.shape or ends[-1] != len(events) or np.any(np.diff(ends, prepend=0)<0)):
        raise ValueError(f"Invalid trial, unit, camera or event identity: {path}")
    times = np.split(events, ends[:-1])
    if any(np.any(np.diff(cell)<0) for cell in times):
        raise ValueError("Unordered cell event times")
    return dict(trial=trial_id, start=start, stop=stop, ts=ts, xy=xy,
                frame=trial["camera_row"], spikes=times, sha256=digest(path))


def anchors(start, stop):
    elapsed = np.arange(2.0, stop-start, 2.0)
    return elapsed[(start+elapsed+LAG+.05) <= stop-.25]


def counts(events, cutoff):
    edges = cutoff + OFFSETS
    return np.stack([np.diff(np.searchsorted(cell, edges, side="right"))
                     for cell in events], axis=1)


def history(trial, cutoff):
    """Build only inputs known by the nominal cutoff, independently of labels."""
    ts = trial["ts"]
    queries = cutoff + OFFSETS
    ix = np.searchsorted(ts, queries, side="right") - 1
    if np.any(ix < 0):
        return None, "missing_history"
    if np.any(queries - ts[ix] > .075):
        return None, "stale_history"
    pos, tm = trial["xy"][ix], ts[ix]
    vel = np.diff(pos, axis=0) / np.diff(tm)[:, None]
    motion = np.column_stack([pos[1:], vel, queries[1:]-tm[1:]])
    return dict(motion=motion, spike=counts(trial["spikes"], cutoff),
                clocks=np.log1p([cutoff-trial["start"], cutoff-RUN_START]),
                prior_frame=trial["frame"][ix], prior_s=tm,
                first_ix=ix[0]), None


def measured_target(trial, cutoff, item):
    ts = trial["ts"]
    label = np.searchsorted(ts, cutoff + LAG, side="left")
    if label == len(ts):
        return None, "missing_target"
    if ts[label] - (cutoff+LAG) > .05:
        return None, "late_target"
    if np.any(np.diff(ts[item["first_ix"]:label+1]) > .100):
        return None, "camera_gap"
    xy = trial["xy"][label]
    if not (np.all(np.isfinite(item["motion"])) and np.all(np.isfinite(xy))):
        return None, "nonfinite_xy"
    return dict(y=xy, label_s=ts[label], label_frame=trial["frame"][label]), None


@dataclass
class Samples:
    trial: np.ndarray
    cutoff: np.ndarray
    motion: np.ndarray
    spike: np.ndarray
    clocks: np.ndarray
    prior_s: np.ndarray
    prior_frame: np.ndarray
    label_s: np.ndarray
    label_frame: np.ndarray
    y: np.ndarray

    @property
    def anchor(self):
        return self.motion[:, -1, :2]

    def select(self, mask):
        return Samples(**{k: v[mask] for k, v in vars(self).items()})


def read_partition(base, part):
    items, trials, support = [], {}, {}
    previous_stop = None
    for i in PROTOCOL["split"][part]:
        t = load_trial(base, part, i)
        if previous_stop is not None and t["start"] < previous_stop-1e-8:
            raise ValueError("Trip clock intervals overlap")
        previous_stop = t["stop"]
        trials[i] = t
        counts_by_reason = Counter()
        schedule = anchors(t["start"], t["stop"])
        for elapsed in schedule:
            c = t["start"] + elapsed
            hist, reason = history(t, c)
            if reason is None:
                label, reason = measured_target(t, c, hist)
            if reason is not None:
                counts_by_reason[reason] += 1
                continue
            hist.pop("first_ix")
            items.append(dict(trial=i, cutoff=c, **hist, **label))
            counts_by_reason["retained"] += 1
        support[str(i)] = dict(sha256=t["sha256"], start_s=t["start"], stop_s=t["stop"],
                               planned=len(schedule), disposition=dict(counts_by_reason))
    if not items:
        raise ValueError("No supported paired samples")
    return Samples(**{k: np.stack([row[k] for row in items]) for k in items[0]}), trials, support


def surrogate(data, trials):
    wrong, donor_id, donor_s = [], [], []
    for i, c in zip(data.trial, data.cutoff, strict=True):
        choices = []
        elapsed = c-trials[i]["start"]
        for j, d in trials.items():
            if d["stop"] > trials[i]["start"] or j == i:
                continue
            for other_elapsed in anchors(d["start"], d["stop"]):
                choices.append((abs(other_elapsed-elapsed), -j, other_elapsed))
        if not choices:
            raise ValueError("Scored trial has no completed donor")
        _, neg, other_elapsed = min(choices)
        d = trials[-neg]
        time = d["start"] + other_elapsed
        if time >= c:
            raise ValueError("Donor must predate receiving prediction")
        wrong.append(counts(d["spikes"], time))
        donor_id.append(d["trial"])
        donor_s.append(time)
    roll = np.stack([np.roll(data.spike[:,:,j], 1+int(unit)%3, axis=1)
                     for j, unit in enumerate(UNITS)], axis=2)
    return np.stack(wrong), roll, np.array(donor_id), np.array(donor_s)


def trial_weights(ids):
    _, inv, n = np.unique(ids, return_inverse=True, return_counts=True)
    weights = 1. / n[inv]
    return weights / weights.sum()


def train_grid(anchor):
    bounds = np.percentile(anchor, [5,95], axis=0)
    x, y = np.linspace(*bounds[:,0], 4), np.linspace(*bounds[:,1], 4)
    centers = np.array([[i,j] for i in x for j in y])
    return centers, np.maximum((bounds[1]-bounds[0])/3, 5.)


def ridge_design(motion, clocks, spike, mode, centers, spacing):
    if mode == "spikes":
        return np.sqrt(spike).reshape(len(spike), -1)
    last = motion[:,-1,:]
    dist = (last[:,None,:2] - centers[None,:,:]) / spacing
    rbf = np.exp(-.5*np.square(dist).sum(axis=2))
    design = [motion.reshape(len(motion),-1), clocks, rbf,
              rbf*last[:,2:3], rbf*last[:,3:4]]
    if mode == "combined":
        design.append(np.sqrt(spike).reshape(len(spike), -1))
    return np.column_stack(design)


def fit_ridge(data, mode, penalty):
    centers, spacing = train_grid(data.anchor)
    x = ridge_design(data.motion, data.clocks, data.spike, mode, centers, spacing)
    y = data.y if mode=="spikes" else data.y-data.anchor
    w = trial_weights(data.trial)
    avg = np.average(x, axis=0, weights=w)
    sd = np.sqrt(np.average((x-avg)**2, axis=0, weights=w))
    sd[sd < 1e-8] = 1.
    z = (x-avg)/sd
    yavg = np.average(y, axis=0, weights=w)
    lhs = (z.T*w) @ z + penalty*np.eye(z.shape[1])
    coef = np.linalg.solve(lhs, (z.T*w) @ (y-yavg))
    return dict(centers=centers, spacing=spacing, avg=avg, sd=sd,
                coef=coef, yavg=yavg, mode=np.array(mode), penalty=np.array(penalty))


def predict_ridge(fit, motion, clocks, spike):
    mode = str(fit["mode"])
    x = ridge_design(motion, clocks, spike, mode, fit["centers"], fit["spacing"])
    pred = ((x-fit["avg"])/fit["sd"]) @ fit["coef"] + fit["yavg"]
    return pred if mode=="spikes" else pred+motion[:,-1,:2]


def distance_summary(data, pred):
    error = np.linalg.norm(pred-data.y, axis=1)
    return {int(i):float(error[data.trial==i].mean()) for i in np.unique(data.trial)}


def choose_penalty(data, mode):
    records = []
    for penalty in (0.03,0.3,3.0):
        folds = []
        for last, lo, hi in [(63,64,68),(68,69,73),(73,74,78)]:
            a = data.select(data.trial <= last)
            b = data.select((data.trial >= lo) & (data.trial <= hi))
            fit = fit_ridge(a, mode, penalty)
            pred = predict_ridge(fit, b.motion, b.clocks, b.spike)
            folds.extend(distance_summary(b,pred).values())
        records.append(dict(penalty=penalty, mean_cm=float(np.mean(folds))))
    best = min(records, key=lambda r: (r["mean_cm"], -r["penalty"]))
    return best["penalty"], records
