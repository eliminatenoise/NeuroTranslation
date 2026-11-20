"""Frozen targets, estimators and scoring used in development and external evaluation."""
import hashlib
import json
import math
import numpy as np
from forward import features, fit_transform, predict, tokens, undo

N = 80
SHIFT = 37
RIDGE_PENALTY = 32.0


def recording(baseline, early, late):
    x = tokens(baseline, early)
    late = np.asarray(late, dtype=np.float64)
    if x.shape[0] != N or late.shape != (N, 20, 5) or not np.isfinite(late[:, :, 1]).all():
        raise ValueError("Expected 80 events with 20 late samples in the five-channel source layout.")
    # No late channel other than the target enters a statistic or predictor.
    base = np.asarray(baseline, dtype=np.float64)[:, :, 1].mean(axis=1)
    future = late[:, :, 1].mean(axis=1)
    return x, base, future - base


def derange(raw, person):
    x = raw.copy()
    for group in np.unique(person):
        rows = np.where(person == group)[0]
        if len(rows) != N:
            raise ValueError("The pairing control requires exactly 80 ordered events per person.")
        x[rows, 10:, 0] = np.roll(raw[rows, 10:, 0], SHIFT, axis=0)
    return x


def ridge_inputs(x, variant):
    order = x[:, 0, 5:6]
    if variant == "time":
        return order
    first = x[:, :10, 1:5] if variant == "pre" else x[:, :, :5]
    return np.column_stack((first.reshape(len(x), -1), order))


def ridge_fit(x, y):
    xm, ym = x.mean(0), float(y.mean())
    centered = x - xm
    diagonal = RIDGE_PENALTY * np.eye(x.shape[1])
    coef = np.linalg.solve(centered.T @ centered + diagonal, centered.T @ (y - ym))
    return {"coef": coef.tolist(), "intercept": float(ym - xm @ coef)}


def fit_controls(x, baseline_sc6, target, order, people):
    transform = fit_transform(x, target)
    y = (target - transform["target_mean"]) / transform["target_sd"]
    reg = {}
    inputs = {}
    for key in ("noneng", "eng", "deranged"):
        raw = derange(x, people) if key == "deranged" else x
        inputs[key] = features(raw, order, transform, key != "noneng")
    for key, variant in (("time", "time"), ("pre", "pre"), ("noneng", "all"), ("eng", "all"), ("deranged", "all")):
        model_key = key if key in inputs else "noneng"
        reg[key] = ridge_fit(ridge_inputs(inputs[model_key], variant), y)
    controls = {"ridge": reg, "mean_late_SC6": float(np.mean(target + baseline_sc6))}
    return inputs, y, transform, controls


def simple_predictions(raw, baseline, order, people, transform, controls):
    outputs = {"event_mean": np.full(len(raw), transform["target_mean"]),
               "baseline_subtraction": controls["mean_late_SC6"] - baseline}
    for key, reg in controls["ridge"].items():
        data = derange(raw, people) if key == "deranged" else raw
        x = features(data, order, transform, key in ("eng", "deranged"))
        variant = key if key in ("time", "pre") else "all"
        scaled = ridge_inputs(x, variant) @ np.asarray(reg["coef"]) + reg["intercept"]
        outputs["ridge_" + key] = undo(scaled, transform)
    return outputs


def sealed_predictions(raw, baseline, order, people, export, controls):
    outputs = simple_predictions(raw, baseline, order, people, export["transform"], controls)
    models = dict(export["models"], deranged=controls["deranged_transformer"])
    for key in models:
        data = derange(raw, people) if key == "deranged" else raw
        outputs["transformer_" + key] = predict(data, order, dict(export, models=models), key)
    return outputs


def errors(target, predictions):
    result = {}
    for name, pred in predictions.items():
        residual = np.asarray(pred, dtype=np.float64) - target
        if not np.isfinite(residual).all():
            raise ValueError("Model produced a nonfinite error")
        result[name] = {"mae_uV": float(np.abs(residual).mean()),
                        "rmse_uV": float(np.sqrt(np.square(residual).mean()))}
    return result


def summarize(folds):
    names = list(folds[0])
    mean = {name: {metric: float(np.mean([fold[name][metric] for fold in folds]))
                   for metric in ("mae_uV", "rmse_uV")} for name in names}
    def paired(control):
        gain = [fold[control]["mae_uV"] - fold["transformer_eng"]["mae_uV"] for fold in folds]
        return {"comparator": control, "per_person_gain_uV": gain, "mean_gain_uV": float(np.mean(gain)),
                "range_uV": [min(gain), max(gain)], "people_improved": sum(x > 0 for x in gain)}
    comparisons = {key: paired(key) for key in names if key != "transformer_eng"}
    primary = comparisons["transformer_noneng"]["per_person_gain_uV"]
    deranged = comparisons["transformer_deranged"]["per_person_gain_uV"]
    nonzero = [p for p in primary if p != 0]
    s = min(sum(p > 0 for p in nonzero), sum(p < 0 for p in nonzero))
    p = min(1.0, 2 * sum(math.comb(len(nonzero), k) for k in range(s + 1)) / 2**len(nonzero))
    both = sum(a > 0 and b > 0 for a, b in zip(primary, deranged))
    return {"people": len(folds), "events_per_person": N, "macro": mean,
            "person_folds": folds, "paired_gain_comparator_minus_full": comparisons,
            "primary_exact_two_sided_sign_p": p, "people_improved_on_both": both,
            "predeclared_development_criterion_met": bool(np.mean(primary) > 0 and np.mean(deranged) > 0 and both >= 3)}


def load_npz(path, receipt_path):
    receipt = json.loads(receipt_path.read_text())
    from forward import CHANNELS
    channels = receipt["channels"]
    if ([c["name"] for c in channels] != CHANNELS
            or any(c["units"] != "microV" for c in channels)):
        raise ValueError("Unexpected source channel order or voltage units.")
    if (receipt["header"]["srate"] != 10000
            or receipt["intervals_samples_half_open"] != {"baseline": [-150, -100], "early": [50, 80], "late": [120, 140]}
            or receipt["selected_rows_zero_based"] != list(range(N))
            or receipt["snapshot"] != "ab5f0cb559249cb6d82b6f763767c6fe99292886"
            or "_task-median_run-" not in receipt["stem"]):
        raise ValueError("The recording differs from the frozen source contract.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["output_sha256"]:
        raise ValueError("Recording hash differs from source receipt.")
    with np.load(path, allow_pickle=False) as f:
        if set(f.files) != {"baseline", "early", "late", "event_samples"}:
            raise ValueError("Unexpected data members.")
        sample = np.asarray(f["event_samples"])
        if (sample.shape != (N,) or not np.issubdtype(sample.dtype, np.integer)
                or not (np.diff(sample) > 0).all() or sample.tolist() != receipt["event_samples"]):
            raise ValueError("Source and recording chronological event samples differ.")
        return recording(f["baseline"], f["early"], f["late"])
