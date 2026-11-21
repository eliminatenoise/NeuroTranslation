"""Score all four frozen models across the two Delhaye development participants."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import gammaln

from predict import MODELS, predict_all


def evaluate(data, predictions):
    y = data["y"]
    factorial = gammaln(y + 1)
    record_trial = np.char.add(np.char.add(data["recording"].astype(str), ":"), data["trial"].astype(str))
    metrics = {}
    for name, pred in predictions.items():
        if pred.shape != y.shape or not np.isfinite(pred).all() or (pred <= 0).any():
            raise ValueError("Incomplete predictions")
        metrics[name] = (pred, pred - y * np.log(pred) + factorial, np.abs(pred - y), np.square(pred - y))

    def summarize(group, which):
        obs = int(y[which].sum())
        scores = {}
        for name, (pred, nll, ae, se) in metrics.items():
            s = float(pred[which].sum())
            scores[name] = {"poisson_nll_per_bin": float(nll[which].mean()),
                            "mae_spikes_per_bin": float(ae[which].mean()),
                            "rmse_spikes_per_bin": float(np.sqrt(se[which].mean())),
                            "predicted_total": s, "predicted_minus_observed_total": s - obs,
                            "bins_predicted_above_20": int((pred[which] > 20).sum())}
        ll = {n: s["poisson_nll_per_bin"] for n, s in scores.items()}
        return {"group": group, "bins": int(which.sum()), "trials": len(np.unique(record_trial[which])),
                "observed_spikes": obs, "scores": scores, "true_minus_history_nll": ll[MODELS[2]] - ll[MODELS[1]],
                "true_minus_substitution_nll": ll[MODELS[2]] - ll[MODELS[3]]}

    groups = {"all": [summarize({}, np.ones(len(y), dtype=bool))]}
    for dimensions in (("group",), ("receptor_class",), ("material",),
                       ("group", "receptor_class"), ("group", "unit", "receptor_class", "field_vs_contact"),
                       ("group", "unit", "receptor_class", "material"),
                       ("group", "unit", "receptor_class", "material", "direction")):
        name = "_".join("person" if d == "group" else d for d in dimensions)
        keys = np.column_stack([data[d] for d in dimensions])
        levels, inverse = np.unique(keys, return_inverse=True, axis=0)
        groups[name] = [summarize(dict(zip(("person" if d == "group" else d for d in dimensions), level.tolist())),
                                  inverse.reshape(-1) == i) for i, level in enumerate(levels)]
    macro = {name: float(np.mean([p["scores"][name]["poisson_nll_per_bin"] for p in groups["person"]])) for name in MODELS}
    by_person = {}
    for p in groups["person"]:
        total_error = p["scores"][MODELS[2]]["predicted_minus_observed_total"]
        by_person[p["group"]["person"]] = {
            "true_better_than_history": p["true_minus_history_nll"] < 0,
            "true_better_than_substitution": p["true_minus_substitution_nll"] < 0,
            "true_force_total_calibration": "overpredicted" if total_error > 0 else "underpredicted" if total_error < 0 else "exact"}
    return {"equal_person_mean_nll_per_bin": macro, "person_readout": by_person, "groups": groups}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("development_npz", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_bytes())
    with np.load(args.development_npz, allow_pickle=False) as src:
        if set(np.unique(src["group"]).tolist()) != {"U105", "U111"}:
            raise ValueError("Expected both preregistered development participants")
        pred = predict_all(src["X"], src["previous_repeat_force"], bundle)
        data = {k: src[k] for k in ("group", "trial", "recording", "unit", "receptor_class",
                                     "material", "direction", "field_vs_contact")}
        y = src["y"]
    if y.shape != (len(y), 1) or not np.isin(y, np.arange(21)).all():
        raise ValueError("Expected a count of 0–20 spikes per future 20 ms window")
    data["y"] = y[:, 0].astype(np.float64)
    result = evaluate(data, pred)
    with args.output_json.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
