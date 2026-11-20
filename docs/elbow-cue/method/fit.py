"""Refit a prespecified pilot on three Ofner execution files and score whole runs."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from infer import CUES, HERE, MECHANICS, RIDGES, SIGNAL, feature_vector, predict
from ofner_source import Run

PROTOCOL_HASH = "f0e1525bcebf19010f668c36c5d7f308aedccc5c49ff6bc181b4ae2857abd6b7"
CODES = {0x600: "flexion", 0x601: "extension"}
RUNS = (1, 2, 3)
METHODS = ("persistence", "cue_median", *RIDGES, "shifted_c3")
PENALTY = 6.0


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_window(run, channel, end, count):
    data = np.asarray(run.window(channel, end - count + 1, end + 1), dtype=np.float64)
    if data.shape != (count,) or not np.isfinite(data).all():
        raise ValueError(f"Incomplete or nonfinite window on channel {channel}")
    return data


def read_inputs(run, cue, tick):
    cutoff = tick + 128
    def signal_bins(channel):
        return read_window(run, channel, cutoff, 256).reshape(4, 64).mean(axis=1)
    elbow = read_window(run, 93, cutoff // 8, 32).reshape(4, 8)
    eye = [signal_bins(channel) for channel in (62, 63, 64)]
    return {"cue": cue, "elbow_medians": np.median(elbow, axis=1).tolist(),
            "c3_means": signal_bins(28).tolist(),
            "eog_means": np.mean(eye, axis=0).tolist()}


def read_runs(cache):
    rows = []
    for number in RUNS:
        with Run(cache, number) as run:
            events = list(run.events)
            onset = sorted((tick, code) for tick, code in events if code in CODES)
            if Counter(code for _, code in onset) != {0x600: 6, 0x601: 6}:
                raise ValueError(f"Unexpected cue counts in run {number}")
            if len({tick for tick, _ in onset}) != 12:
                raise ValueError(f"Repeated trial onset in run {number}")
            for tick, code in onset:
                if (tick + 1536, code | 0x8000) not in events:
                    raise ValueError(f"Missing three-second cue end in run {number}")
                sample = read_inputs(run, CODES[code], tick)
                endpoint = read_window(run, 93, (tick + 512) // 8, 8)
                target = float(np.median(endpoint) - sample["elbow_medians"][3])
                rows.append({"run": number, "cue": CODES[code], "tick": tick,
                             "sample": sample, "target": target})
    return rows


def fit_models(rows):
    targets = np.asarray([r["target"] for r in rows])
    medians = {c: float(np.median([r["target"] for r in rows if r["cue"] == c]))
               for c in CUES}
    models = {"persistence": {"value": 0.0}, "cue_median": {"by_cue": medians}}
    for name in RIDGES:
        scale = None
        names = MECHANICS.copy()
        if name == "temporal_attention":
            signal = np.asarray([r["sample"]["c3_means"] for r in rows])
            scale = float(np.sqrt(np.mean((signal - signal[:, :1])**2))) or 1.0
            names.append("attention_pool")
        elif name != "cue_mechanics":
            names.extend(SIGNAL)
        features = np.asarray([feature_vector(name, r["sample"], scale) for r in rows])
        means, scales = features.mean(axis=0), features.std(axis=0)
        scales[scales == 0] = 1.0
        x = (features - means) / scales
        intercept = float(targets.mean())
        w = np.linalg.solve(x.T @ x + PENALTY * np.eye(x.shape[1]), x.T @ (targets - intercept))
        model = {"features": names, "means": means.tolist(), "scales": scales.tolist(),
                 "intercept": intercept, "weights": w.tolist()}
        if scale is not None:
            model["token_scale"] = scale
        models[name] = model
    return models


def held_predictions(rows, models):
    predictions = []
    for cue in CUES:
        group = sorted((r for r in rows if r["cue"] == cue), key=lambda r: r["tick"])
        for i, r in enumerate(group):
            sample = r["sample"]
            actual = r["target"]
            estimates = {name: predict(name, model, sample) for name, model in models.items()}
            donor = group[(i + 1) % len(group)]["sample"]
            paired = {**sample, "c3_means": donor["c3_means"]}
            estimates["shifted_c3"] = predict("cue_mechanics_c3", models["cue_mechanics_c3"], paired)
            predictions.append({"run": r["run"], "cue": cue, "target": actual,
                                "opposite": actual * estimates["cue_median"] < 0,
                                "loss": {k: abs(actual-v) for k, v in estimates.items()}})
    return predictions


def summarize(rows):
    return {"n": len(rows), "mae": {m: float(np.mean([r["loss"][m] for r in rows])) for m in METHODS},
            "small_abs_le_0_1": sum(abs(r["target"]) <= 0.1 for r in rows),
            "opposite_training_cue_median": sum(r["opposite"] for r in rows),
            "zero_change": sum(r["target"] == 0.0 for r in rows)}


def evaluate(rows):
    scored = []
    folds = []
    for held_run in RUNS:
        train = [r for r in rows if r["run"] != held_run]
        held = [r for r in rows if r["run"] == held_run]
        folds.append({"fit_runs": [n for n in RUNS if n != held_run], "fit_n": len(train),
                      "held_run": held_run, "held_n": len(held)})
        scored.extend(held_predictions(held, fit_models(train)))
    by_run = {str(i): summarize([r for r in scored if r["run"] == i]) for i in RUNS}
    by_cue = {c: summarize([r for r in scored if r["cue"] == c]) for c in CUES}
    by_cell = {str(i): {c: summarize([r for r in scored if (r["run"], r["cue"]) == (i, c)])
                        for c in CUES} for i in RUNS}
    balanced = {m: float(np.mean([by_cell[str(i)][c]["mae"][m] for i in RUNS for c in CUES]))
                for m in METHODS}
    def beats_mechanics(group):
        return group["mae"]["cue_mechanics_c3"] < group["mae"]["cue_mechanics"]
    controls = ["cue_mechanics", "cue_mechanics_eog", "shifted_c3"]
    improvements = {k: balanced["cue_mechanics_c3"] < balanced[k] for k in controls}
    n_cues = sum(beats_mechanics(g) for g in by_cue.values())
    n_runs = sum(beats_mechanics(g) for g in by_run.values())
    decision = {"balanced_c3_beats": improvements, "cue_groups_c3_beats_mechanics": n_cues,
                "runs_c3_beats_mechanics": n_runs,
                "incremental_c3_gate_passed": all(improvements.values()) and n_cues == 2 and n_runs >= 2}
    return {"protocol_sha256": PROTOCOL_HASH, "units": "native elbow-sensor change",
            "protocol": "Three whole-run rotations within S1 TRAIN development", "folds": folds,
            "pooled": summarize(scored), "balanced_mae": balanced, "by_run": by_run,
            "by_cue": by_cue, "by_run_cue": by_cell, "decision": decision}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="Directory with the verified three GDF files")
    parser.add_argument("--out", type=Path, required=True, help="Directory for aggregate JSON outputs")
    args = parser.parse_args()
    if digest(HERE / "protocol.json") != PROTOCOL_HASH:
        raise ValueError("Protocol hash differs from the frozen specification")
    rows = read_runs(args.cache)
    scores = evaluate(rows)
    bundle = {"schema": 1, "protocol_sha256": PROTOCOL_HASH, "dataset": "doi:10.5281/zenodo.834976",
              "training": {"person": "S1", "execution_runs": list(RUNS), "trials": len(rows)},
              "units": "native elbow-sensor change", "models": fit_models(rows)}
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "scores.json", scores)
    write_json(args.out / "model.json", bundle)


if __name__ == "__main__":
    main()
