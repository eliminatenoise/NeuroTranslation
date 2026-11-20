"""Measure causal forecasts against unseen motion, by recording and source group."""
import argparse
import json
from pathlib import Path

import numpy as np

from forecast import STEPS, load_weights, residual_prediction
from prepare import COHORT


def retrieval(training, x):
    train_x = training["x"].reshape(len(training["id"]), -1)
    ids = training["id"]
    groups = [np.flatnonzero(ids == c) for c in np.unique(ids)]
    result = []
    for query in x:
        distance = np.sqrt(np.mean((train_x - query.ravel())**2, axis=-1))
        per_clip = [indices[np.argmin(distance[indices])] for indices in groups]
        winners = np.array(sorted(per_clip, key=lambda i: distance[i])[:3])
        weight = 1 / np.maximum(distance[winners], .01)
        result.append(np.average(training["y"][winners], axis=0, weights=weight))
    return np.asarray(result)


def errors(pred, target):
    delta = (pred - target) * 100.
    body = delta[..., :54].reshape(len(pred), 12, 18, 3)
    body -= body[:, :, 2:4].mean(axis=2, keepdims=True)
    return np.stack((np.linalg.norm(body, axis=-1).mean(axis=-1), np.linalg.norm(delta[..., 54:], axis=-1)), axis=-1)


def summarize(curves):
    return {"bodyMeanMm": float(curves[:, 0].mean()), "pelvisMeanMm": float(curves[:, 1].mean()), "body250Mm": float(curves[4, 0]), "body600Mm": float(curves[-1, 0]), "pelvis250Mm": float(curves[4, 1]), "pelvis600Mm": float(curves[-1, 1]), "bodyCurveMm": curves[:, 0].tolist(), "pelvisCurveMm": curves[:, 1].tolist()}


def predictions(local, data):
    x, tokens = data["x"], data["token"]
    _, w = load_weights(local / "conditional.json")
    _, h = load_weights(local / "history-only.json")
    tagged = []
    swapped = []
    only = []
    collapsed = []
    for hist, token in zip(x, tokens):
        tagged.append(residual_prediction(hist, token, w))
        swapped.append(residual_prediction(hist, 1 - token, w))
        only.append(residual_prediction(hist, 0, h))
        collapsed.append(residual_prediction(np.repeat(hist[-1:], 11, axis=0), token, w))
    # All results share the real-history residual convention. For a stationary
    # input the nominal root velocity was zero, so remove the true-history prior.
    root_prior = (-x[:, -5, 54:] * 250 / .20)[:, None, :] * STEPS[None, :, None] / 100
    static = np.asarray(collapsed)
    static[..., 54:] -= root_prior
    persist = np.zeros_like(tagged)
    persist[..., 54:] -= root_prior
    cv = persist + ((x[:, -1] - x[:, -3]) * 250 / .10)[:, None, :] * STEPS[None, :, None] / 100
    ridge = np.load(local / "ridge.npz")
    linear = (x.reshape(len(x), -1) @ ridge["coef"] + ridge["bias"]).reshape(-1, 12, 57)
    train = dict(np.load(local / "train.npz"))
    return {"conditional": np.asarray(tagged), "history-only": np.asarray(only), "swapped": np.asarray(swapped), "stationary-history": static, "persistence": persist, "constant-velocity": cv, "ridge": linear, "retrieval": retrieval(train, x)}


def evaluate(local, split):
    data = dict(np.load(local / (split + ".npz")))
    ids, subjects = data["id"], data["subject"]
    named = sorted({r["subject"] for r in COHORT if r["split"] == split}, key=int)
    report = {"cohort": split, "eligibleWindows": len(ids), "sourceGroupNumbers": named, "eligibleGroups": sorted(set(subjects)), "models": {}}
    if len(ids):
        for name, prediction in predictions(local, data).items():
            error = errors(prediction, data["y"])
            trials = {c: error[ids == c].mean(axis=0) for c in np.unique(ids)}
            groups = {s: np.mean([trials[c] for c in np.unique(ids[subjects == s])], axis=0) for s in np.unique(subjects)}
            report["models"][name] = {"overall": summarize(np.mean(list(groups.values()), axis=0)), "byGroup": {s: summarize(v) for s, v in groups.items()}, "byTrial": {c: summarize(v) for c, v in trials.items()}}
        primary = report["models"]["conditional"]["overall"]["bodyMeanMm"]
        report["primaryStrictWin"] = all(primary < report["models"][m]["overall"]["bodyMeanMm"] for m in ["history-only", "persistence", "constant-velocity", "ridge", "retrieval"])
    (local / (split + "-results.json")).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(split, {k: round(v["overall"]["bodyMeanMm"], 2) for k, v in report["models"].items()})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("local", type=Path)
    p.add_argument("split", choices=["previous", "fresh"])
    a = p.parse_args()
    from seal import check
    check(a.local)
    evaluate(a.local, a.split)
