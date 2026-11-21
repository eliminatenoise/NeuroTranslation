"""Produce aligned forecast arrays. Each non-training split requires its release."""
import argparse
import json
import numpy as np

from count_model import ARMS, SEEDS, predict, simple_rates
from study_io import BASE, HERE, IDENTITY, arm_input, dump, load_inputs, npz, require_stage, sha


def evaluate(split):
    require_stage(split)
    out = HERE / (split + "-predictions.npz")
    meta = HERE / (split + "-predictions.json")
    if meta.exists():
        prev = json.loads(meta.read_text())
        if prev["predictions_sha256"] == sha(out):
            return prev
        raise RuntimeError("Existing predictions differ from their receipt")
    data = load_inputs(split)
    n = len(data["original"])
    guide = data["unit_guide"]
    donor = data["donor"]
    match = donor >= 0
    output = {key:data[key] for key in (*IDENTITY, "source_row", "unit_guide", "donor")}
    output["seeds"] = np.array(SEEDS)
    output["donor_source_row"] = np.full(n, -1, int)
    output["donor_source_row"][match] = output["source_row"][donor[match]]
    weights = HERE / "weights"

    def forecast(path, motion):
        with np.load(path) as z:
            np.testing.assert_array_equal(guide, z["unit_guide"])
            inputs = arm_input(data, str(z["arm"]), motion)
            rates = predict(z, **inputs)
            if rates.shape != (n,10,23) or not np.isfinite(rates).all() or (rates <= 0).any():
                raise ValueError("Invalid forecast count rates")
            if str(z["arm"]) != "full":
                return rates, None
            paired = np.full_like(rates, np.nan)
            if np.any(match):
                wrong = {name:x[match] for name, x in inputs.items()}
                wrong["movement"] = motion[donor[match]]
                paired[match] = predict(z, **wrong)
                if not np.isfinite(paired[match]).all() or (paired[match] <= 0).any():
                    raise ValueError("Invalid wrong-movement rates")
            return rates, paired

    for arm in ARMS:
        y, wrong = forecast(weights / f"glm-{arm}.npz", data["ridge"])
        output["glm_" + arm] = y
        ensemble, wrong_ensemble = [], []
        if wrong is not None:
            output["glm_wrong"] = wrong
        for j, seed in enumerate(SEEDS):
            y, wrong = forecast(weights / f"transformer-{arm}-{seed}.npz", data["forecast"][j])
            ensemble.append(y)
            if wrong is not None:
                wrong_ensemble.append(wrong)
        output[arm] = np.stack(ensemble)
        if wrong_ensemble:
            output["wrong"] = np.stack(wrong_ensemble)
    with np.load(weights / "rates.npz") as controls:
        np.testing.assert_array_equal(controls["unit_guide"], guide)
        output.update(simple_rates(controls, data["spikes"], data["ordinal"]))
        fallback = int(np.count_nonzero(~np.isin(data["ordinal"], controls["ordinals"])))
    npz(out,output)
    meta_data = {"split":split, "windows":n,"originals":len(np.unique(data["original"])),
                 "matched_windows":int(match.sum()),"matched_originals":len(np.unique(data["original"][match])),
                 "unsupported_windows":int((~match).sum()),"unseen_ordinal_fallback_windows":fallback,
                 "count_heads":"Fitted on original-balanced non-warmup train rows. Train rows are a fit diagnostic; later splits are frozen forward evaluations.",
                 "motion_features":("Chronological OOF full motor and OOF ridge_full." if split=="train" else
                                    "All-training motor refits evaluated on this released split, full and ridge_full."),
                 "model_families":"Transformer (full motor forecast matched by seed); glm_* (ridge_full motor forecast).",
                 "wrong":"Same full model; source history unchanged. Latest strictly earlier distinct supported original in same split/block/go ordinal supplies forecast, indexed by donor in this file, or donor_source_row in source split; -1 and NaN when unavailable.",
                 "privileged":"Only privileged and glm_privileged receive the measured intervening displacement. All outcomes are 10-by-23 expected sorted-unit spike counts.",
                 "predictions_sha256":sha(out), "source_sha256":sha(BASE/"source"/(split+".npz")),
                 "motion_sha256":sha(BASE/"motor"/("oof.npz" if split=="train" else split+"-predictions.npz"))}
    dump(meta, meta_data)
    return meta_data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("split", choices=["train","validation","within","transfer"])
    print(json.dumps(evaluate(ap.parse_args().split), indent=2))
