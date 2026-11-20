"""Fit and evaluate the frozen development study. Requires Python 3 and NumPy."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from forecast import CHANNELS, FITTED, INPUTS, as_features, center, with_anchor


def robust_scale(a):
    mid = np.median(a, axis=0)
    scale = 1.4826 * np.median(np.abs(a - mid), axis=0)
    return mid, np.maximum(scale, 1e-6)


def huber(x, y):
    mid, scale = robust_scale(x)
    y0, ys = robust_scale(y)
    design = np.column_stack([np.ones(len(x)), np.clip((x - mid) / scale, -8, 8)])
    target = (y - y0) / ys
    regularizer = np.eye(design.shape[1]) * (len(x) * 0.08)
    regularizer[0, 0] = 0.0
    coef = np.zeros(design.shape[1])
    for _ in range(30):
        error = np.abs(target - design @ coef)
        weights = np.minimum(1.0, 1.345 / np.maximum(1e-12, error))
        weighted = design.T * weights
        coef = np.linalg.solve(weighted @ design + regularizer, weighted @ target)
    return dict(center=mid.tolist(), scale=scale.tolist(), target_center=float(y0),
                target_scale=float(ys), bias=float(coef[0]), coef=coef[1:].tolist())


def fit(bins, y):
    anchor = bins[:, -1, 1]
    return {"format": 1, "channels": list(CHANNELS), "event_median": float(np.median(y)),
            "median_innovation": float(np.median(y - anchor)),
            "fits": {m: huber(as_features(m, bins), y - anchor) for m in FITTED}}


def metrics(y, pred):
    d = pred - y
    return {"mae_uV": float(np.abs(d).mean()), "rmse_uV": float(np.sqrt(np.mean(d * d)))}


def load(path, receipt=None):
    source_file = receipt if receipt is not None else path.with_name(path.stem.removeprefix("development-") + "-receipt.json")
    source = json.loads(source_file.read_bytes())
    if source["output_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("Voltage file checksum differs from the acquisition receipt")
    with np.load(path, allow_pickle=False) as f:
        b, e, later = [np.asarray(f[k], dtype=np.float64) for k in ("baseline", "early", "late")]
        if (b.shape, e.shape, later.shape) != ((80, 50, 5), (80, 30, 5), (80, 20, 5)):
            raise ValueError(f"Unexpected electrode array at {path.name}")
        names = tuple(c["name"] for c in source["channels"])
        if names != CHANNELS or not all(np.isfinite(a).all() for a in (b, e, later)):
            raise ValueError("Nonfinite voltage or inconsistent channel order")
        if len(np.unique(f["event_samples"])) != 80 or np.any(np.diff(f["event_samples"]) <= 0):
            raise ValueError("Expected 80 distinct chronological events")
        bins = np.concatenate((b.reshape(80, 5, 10, 5).mean(2), e.reshape(80, 3, 10, 5).mean(2)), axis=1)
        z = center(bins)
        y = later[:, :, 1].mean(1) - b[:, :, 1].mean(1)
        innovation = later[:, :, 1].mean(1) - e[:, -10:, 1].mean(1)
        if not np.allclose(y - z[:, -1, 1], innovation, rtol=0, atol=1e-10):
            raise ValueError("Common baseline failed to cancel")
        return z, y


def run(data, out):
    ids = [f"sub-{n:03d}" for n in range(1, 5)]
    paths = [data / f"development-{sid}.npz" for sid in ids]
    inputs = [load(p) for p in paths]
    folds = []
    for i, (z, y) in enumerate(inputs):
        train = [row for ix, row in enumerate(inputs) if ix != i]
        model = fit(*[np.concatenate(column) for column in zip(*train)])
        preds = {m: with_anchor(m, model, z, z[:, -1, 1]) for m in INPUTS}
        wrong = z.copy()
        wrong[:, :, 0] = np.roll(z[:, :, 0], -37, axis=0)
        preds["wrong_event"] = with_anchor("with_axilla", model, wrong, z[:, -1, 1])
        folds.append({"person": ids[i], "events": len(y), "target_sd_uV": float(np.std(y, ddof=1)),
                      "scores": {m: metrics(y, p) for m, p in preds.items()}})
    modes = list(folds[0]["scores"])
    avg = {m: {k: float(np.mean([f["scores"][m][k] for f in folds])) for k in ("mae_uV", "rmse_uV")} for m in modes}
    gains = {m: [f["scores"][m]["mae_uV"] - f["scores"]["with_axilla"]["mae_uV"] for f in folds]
             for m in ("other_sites", "wrong_event")}
    passes = all(avg["with_axilla"]["mae_uV"] <= .95 * avg[m]["mae_uV"] and min(gains[m]) > 0 for m in gains)
    results = {"evaluation": "four leave-one-person-out development fits", "participants": 4, "events": 320,
               "macro": avg, "folds": folds, "paired_gain_uV": gains, "practical_development_gate": bool(passes)}
    model = fit(*[np.concatenate(column) for column in zip(*inputs)])
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in [("model.json", model), ("results.json", results)]:
        (out / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return {"development_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, "macro": avg, "gate": bool(passes)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.out), indent=2))
