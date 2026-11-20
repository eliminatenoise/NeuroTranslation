"""Uncertainty over people paired on the same eligible walks."""
import numpy as np
from model import subset, weights


def interval(samples):
    return np.quantile(samples, [.025, .975], axis=0).T.tolist()


def evaluate(d, predictions):
    people = sorted(set(d["person"]))
    paired = [p for p in people if set(d["condition"][d["person"] == p]) == {4, 5}]
    if not paired:
        raise ValueError("No people with both contexts")
    public = {"windows": len(d["person"]), "trials": len(set(zip(d["person"],d["condition"],d["repeat"]))),
              "people": len(people), "paired_people": len(paired), "single_context_people": len(people)-len(paired),
              "primary_windows": int(np.isin(d["person"], paired).sum()), "results": {}}
    personal = {"single_context_people": sorted(set(people)-set(paired)), "results": {}}
    for name, arr in predictions.items():
        if np.shape(arr) != d["future_delta_mm"].shape or not np.isfinite(arr).all():
            raise ValueError("Invalid predictions: " + name)
    for context in ("both", "4", "5"):
        by_person = {}
        eligible = np.isin(d["person"], paired)
        if context != "both":
            eligible &= d["condition"] == int(context)
        for person in paired:
            mask = eligible & (d["person"] == person)
            w = weights(subset(d, mask))
            by_person[person] = {}
            for name, pred in predictions.items():
                error = pred[mask] - d["future_delta_mm"][mask]
                by_person[person][name] = {
                    "endpoint_mm": (w @ np.linalg.norm(error, axis=2)).tolist(),
                    "bias_mm": np.einsum("n,nmc->mc", w, error).tolist()}
        personal["results"][context] = by_person
        record = {"people": len(paired), "windows": int(eligible.sum()), "models": {}, "cue_minus": {}}
        draws = np.random.default_rng(1207).integers(0, len(paired), (5000, len(paired)))
        per_method = {}
        for name in predictions:
            endpoint = np.array([by_person[p][name]["endpoint_mm"] for p in paired])
            bias = np.array([by_person[p][name]["bias_mm"] for p in paired])
            per_method[name] = endpoint
            record["models"][name] = {"endpoint_mm": endpoint.mean(axis=0).tolist(),
                                      "endpoint_ci95_mm": interval(endpoint[draws].mean(axis=1)),
                                      "bias_forward_left_up_mm": bias.mean(axis=0).tolist()}
        for name, v in per_method.items():
            if name == "cue":
                continue
            delta = per_method["cue"] - v
            record["cue_minus"][name] = {"mean_mm": delta.mean(axis=0).tolist(),
                                         "ci95_mm": interval(delta[draws].mean(axis=1))}
        public["results"][context] = record
    deltas = public["results"]["both"]["cue_minus"]
    public["passes_both_context_controls_pelvis_heel"] = [
        all(deltas[k]["ci95_mm"][j][1] < 0 and deltas[k]["mean_mm"][j] < 0
            for k in ("withheld", "swapped")) for j in range(2)]
    return public, personal
