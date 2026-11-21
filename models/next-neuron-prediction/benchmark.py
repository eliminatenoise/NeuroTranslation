"""Forecast the next observed sorted unit on a frozen 1-ms replay clock. CC0."""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from time import perf_counter_ns

import numpy as np

HERE = Path(__file__).resolve().parent
TAUS_MS = np.array([10.0, 100.0, 1000.0])
BANDS = {"1–10": (1, 10), "11–100": (11, 100), "101+": (101, np.inf)}
PROTOCOL_SHA256 = "c0c04287d26d8b1ab7996053adaee26b858ce4b2a0f0110d88726a4c4a06bc08"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


class History:
    """Trial-local state at the end of a complete occupied bin."""
    def __init__(self, units):
        self.last_tick = None
        self.count = np.zeros(units, dtype=np.int64)
        self.trace = np.zeros((units, 3), dtype=np.float64)

    def observe(self, tick, counts):
        if self.last_tick is not None:
            if tick <= self.last_tick:
                raise ValueError("Replayed an old or unordered bin")
            self.trace *= np.exp(-(tick - self.last_tick) / TAUS_MS)
        self.count += counts
        self.trace += counts[:, None]
        self.last_tick = tick
        return np.column_stack((np.log1p(self.count), np.log1p(self.trace), counts > 0))


@dataclass
class Trial:
    number: int
    units: np.ndarray
    features: np.ndarray
    targets: np.ndarray
    source_ordinals: np.ndarray
    marginal_counts: np.ndarray
    qc: dict


def millisecond_edges(seconds):
    """Floor and ceiling on the nominal millisecond clock, including exact float edges."""
    seconds = np.asarray(seconds, dtype=np.float64)
    nearest = np.rint(seconds * 1000).astype(np.int64)
    # Compare in the recording's seconds representation. Multiplying an exact
    # edge such as 2.007 s by 1000 can round just above the correct bin number.
    nominal = nearest / 1000.0
    return nearest - (seconds < nominal), nearest + (seconds > nominal)


def read_trial(path, trial_number):
    with np.load(path, allow_pickle=False) as z:
        if z["trial_id"].item() != trial_number:
            raise ValueError("Wrong trial")
        ids, ends, times = (z[f] for f in ("unit_id", "spike_end", "spike_time_s"))
        start, stop = (float(z[f]) for f in ("start_s", "stop_s"))
    if (ids.ndim != 1 or len(ids) < 2 or len(set(ids.tolist())) != len(ids)
            or ends.shape != ids.shape or ends.dtype.kind not in "iu" or times.ndim != 1
            or ends[-1] != len(times) or not np.isfinite([start, stop]).all() or start >= stop):
        raise ValueError("Malformed trial or candidate roster")
    sizes = np.diff(np.r_[0, ends.astype(np.int64)])
    if (np.any(sizes < 0) or not np.isfinite(times).all() or np.any(times <= start)
            or np.any(times >= stop) or any(np.any(np.diff(t) < 0) for t in np.split(times, ends[:-1].astype(int)))):
        raise ValueError("Missing, unordered or out-of-bounds unit timestamps")
    _, end_tick = millisecond_edges(times)
    ticks = end_tick - 1
    _, first = millisecond_edges(start)
    after, _ = millisecond_edges(stop)
    first, after = int(first), int(after)
    keep = (ticks >= first) & (ticks < after)
    labels = np.repeat(np.arange(len(ids)), sizes)[keep]
    bins, groups = np.unique(ticks[keep], return_inverse=True)
    counts = np.zeros((len(bins), len(ids)), dtype=np.int64)
    np.add.at(counts, (groups, labels), 1)
    # All probabilities can be issued as soon as the closing boundary arrives.
    # The next-bin identity and elapsed time are absent from History.observe.
    state = History(len(ids))
    features = np.empty((len(bins), len(ids), 5), dtype=np.float64)
    for j, (tick, local_counts) in enumerate(zip(bins, counts, strict=True)):
        features[j] = state.observe(tick, local_counts)
    future_counts = counts[1:]
    resolved = future_counts.sum(axis=1) == 1
    y = np.argmax(future_counts[resolved], axis=1)
    ordinal = np.arange(1, len(bins))[resolved]
    qc = dict(total_spikes=len(times), incomplete_edge_spikes=int((~keep).sum()),
              complete_bins=max(0, after - first), occupied_bins=len(bins),
              complete_bin_spikes=len(labels), first_occupied_bin_without_forecast=int(bool(len(bins))),
              unresolved_multi_spike_targets=int((~resolved).sum()),
              multi_unit_targets=int(((future_counts > 0).sum(axis=1) > 1).sum()),
              right_censored_forecasts=int(bool(len(bins))), resolved_targets=len(y),
              units_with_events=int((state.count > 0).sum()))
    return Trial(trial_number, ids, features[:-1][resolved], y, ordinal, state.count, qc)


def load_trials(directory, numbers, primary):
    filename = "primary-packets.json" if primary else "external-packets.json"
    packet_hashes = json.loads((HERE / filename).read_text())
    trials = []
    for number in numbers:
        packet = directory / f"trial-{number:03d}.npz"
        if digest(packet) != packet_hashes[str(number)]:
            raise ValueError(f"Unexpected original trial packet {number}")
        trial = read_trial(packet, number)
        if trials and not np.array_equal(trial.units, trials[0].units):
            raise ValueError("Candidate roster changed within a recording")
        trials.append(trial)
    return trials


def logprobs(scores):
    shifted = scores - np.max(scores, axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))


def fit(trials):
    from scipy.optimize import minimize
    total = sum(len(t.targets) for t in trials)
    if total == 0:
        raise ValueError("No resolved training transitions")

    def objective(w):
        loss, grad = 0.0, np.zeros_like(w)
        for trial in trials:
            x, y = trial.features, trial.targets
            lp = logprobs(x @ w)
            rows = np.arange(len(y))
            loss -= lp[rows, y].sum()
            residual = np.exp(lp)
            residual[rows, y] -= 1
            grad += np.einsum("ij,ijk->k", residual, x)
        return loss / total + 0.00005 * np.dot(w, w), grad / total + 0.0001 * w

    result = minimize(objective, np.zeros(5), jac=True, method="L-BFGS-B",
                      options=dict(maxiter=100, ftol=1e-10, gtol=1e-7))
    if not result.success:
        raise RuntimeError(f"Frozen optimizer failed: {result.message}")
    counts = sum((t.marginal_counts for t in trials), np.zeros(len(trials[0].units), dtype=np.int64))
    return dict(protocol_sha256=PROTOCOL_SHA256, code_sha256=digest(Path(__file__)),
                weights=result.x.tolist(), feature_names=["log_count", "trace_10ms",
                    "trace_100ms", "trace_1000ms", "last_bin_fired"],
                training_recording="JDS-SingleDay-JS14/01", unit_ids=trials[0].units.tolist(),
                training_counts=counts.tolist(), training_resolved=total,
                iterations=int(result.nit), training_objective=float(result.fun),
                training_qc=[dict(trial=t.number, **t.qc) for t in trials])


def row_scores(logits, y):
    log_p = logprobs(logits)
    truth = logits[np.arange(len(y)), y]
    greater = (logits > truth[:, None]).sum(axis=1)
    equal = (logits == truth[:, None]).sum(axis=1)
    return np.column_stack((-log_p[np.arange(len(y)), y], (greater == 0) / equal,
                            1 + greater + (equal - 1) / 2))


def metrics(values, targets):
    if not len(targets):
        return dict(rows=0)
    per_unit = np.stack([values[targets == u].mean(axis=0) for u in np.unique(targets)])
    return dict(rows=len(targets), target_units=len(per_unit),
                **dict(zip(("log_loss", "top1", "mean_rank"), values.mean(axis=0).tolist(), strict=True)),
                balanced_log_loss=float(per_unit[:, 0].mean()), balanced_top1=float(per_unit[:, 1].mean()))


def evaluate(trials, model, same_recording):
    k = len(trials[0].units)
    if same_recording and model["unit_ids"] != trials[0].units.tolist():
        raise ValueError("Unit order differs from the fitted recording")
    weights = np.array(model["weights"])
    outputs = {}
    for t in trials:
        x, y = t.features, t.targets
        logits = {"uniform": np.zeros(x.shape[:2]), "online_rate": x[:, :, 0],
                  "recency": x[:, :, 0] + x[:, :, 2], "shared_model": x @ weights}
        if same_recording:
            logits["training_marginal"] = np.broadcast_to(np.log1p(model["training_counts"]), x.shape[:2])
        for key, score in logits.items():
            outputs.setdefault(key, []).append(row_scores(score, y))
    all_y = np.concatenate([t.targets for t in trials])
    ordinals = np.concatenate([t.source_ordinals for t in trials])
    results = {}
    for key, per_trial_values in outputs.items():
        values = np.concatenate(per_trial_values)
        per_trial = [dict(trial=t.number, **metrics(s, t.targets)) for t, s in zip(trials, per_trial_values, strict=True)]
        valid = [m for m in per_trial if m["rows"]]
        results[key] = dict(pooled=metrics(values, all_y),
                            equal_trial={name:float(np.mean([m[name] for m in valid])) for name in
                                        ("log_loss","top1","mean_rank","balanced_log_loss","balanced_top1")} if valid else {},
                            by_trial=per_trial, by_occupied_source_bin={})
        for label, (lo, hi) in BANDS.items():
            include = (ordinals >= lo) & (ordinals <= hi)
            results[key]["by_occupied_source_bin"][label] = metrics(values[include], all_y[include])
    valid_indices = np.flatnonzero([len(t.targets) > 0 for t in trials])
    differences = {}
    if len(valid_indices):
        draws = np.random.default_rng(20261121).integers(len(valid_indices), size=(5000, len(valid_indices)))
        for key, table in outputs.items():
            if key != "shared_model":
                deltas = np.array([outputs["shared_model"][i][:,0].mean() - table[i][:,0].mean()
                                   for i in valid_indices])
                differences[key] = {"delta": float(deltas.mean()), "trial_bootstrap_95pct": 
                                   np.percentile(deltas[draws].mean(axis=1), [2.5, 97.5]).tolist()}
    return dict(candidate_units=k, units_with_complete_bin_events=int((sum(t.marginal_counts for t in trials) > 0).sum()),
                units_with_scored_target=len(np.unique(all_y)), source_observation_intervals="unavailable",
                qc_by_trial=[dict(trial=t.number, **t.qc) for t in trials], methods=results,
                paired_equal_trial_log_loss_model_minus_comparator=differences,
                training_marginal_applicable=same_recording)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["train","js14","er1","example","timing"])
    parser.add_argument("--packets", type=Path)
    parser.add_argument("--model", type=Path, default=HERE/"weights.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if digest(HERE/"protocol.json") != PROTOCOL_SHA256:
        raise ValueError("Frozen protocol changed")
    if args.stage in ("train", "js14", "er1") and args.packets is None:
        parser.error("--packets is required for biological data")
    if args.stage == "train":
        result = fit(load_trials(args.packets, range(55,79), True))
    else:
        model = json.loads(args.model.read_text())
        if model["protocol_sha256"] != PROTOCOL_SHA256 or model["code_sha256"] != digest(Path(__file__)):
            raise ValueError("Model/code/protocol mismatch")
        if args.stage in ("example","timing"):
            result = example(model) if args.stage == "example" else timing(model)
        else:
            same = args.stage == "js14"
            trials = load_trials(args.packets, range(80,90) if same else range(10), same)
            result = evaluate(trials, model, same)
    if args.output:
        dump(args.output, result)
    else:
        print(json.dumps(result, indent=2, allow_nan=False))


def example(model):
    """Authored fiction. The three local IDs do not correspond to recorded neurons."""
    names = ["Amber", "Birch", "Cedar"]
    s = History(len(names))
    steps = []
    weights = np.asarray(model["weights"])
    for tick, observed in [(0,[0,1,0]), (4,[1,0,0]), (8,[0,1,1])]:
        features = s.observe(tick, np.asarray(observed))
        p = np.exp(logprobs(features @ weights))
        steps.append(dict(forecast_time_ms=tick+1, observed_counts=observed,
                          next_unit_probabilities=dict(zip(names,p.tolist(),strict=True))))
    return dict(origin="Authored fictional event stream for illustrating inference", local_units=names,
                note="At 5 ms a forecast exists. The next occupied bin contains two spikes, so that forecast is unresolved. At 9 ms both observations update history.", steps=steps)


def timing(model):
    rng = np.random.default_rng(20261121)
    weights = np.asarray(model["weights"])
    cases = {}
    for k in (3,72):
        counts = np.eye(k,dtype=int)[rng.integers(k,size=2100)]
        s = History(k)
        timings = []
        for j, row in enumerate(counts):
            start = perf_counter_ns()
            np.exp(logprobs(s.observe(4*j, row) @ weights))
            timings.append((perf_counter_ns()-start)/1000)
        cases[str(k)] = dict(fixed_fictional_updates=2000, warmup_updates=100,
                            median_us=float(np.median(timings[100:])), p95_us=float(np.percentile(timings[100:],95)))
    return cases


if __name__ == "__main__":
    main()
