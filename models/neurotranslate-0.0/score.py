"""Score every sealed wrist adapter on examples from its held person."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from fit import MODES, TABLE_MANIFEST_HASH, digest, read_table, save_json, write_state
from predict import angular_tokens, encode, linear, read_checkpoint

PEOPLE = ["sub-37", "sub-03", "sub-15", "sub-17", "sub-38", "sub-43"]
COMPARATOR_FIT = "3eec2d874ba897a2449ae48ee651be08f59f1bd03e2c1fa8d12bc2e342ca231d"
COMPARATOR_SCORES = "5c65cdcdf451c2d266fe9dca255dbe5e954a743ee5144e9bcd11d4f074c3a7e6"


def held_forecast(fold, config, base, condition, mode, bins, anchor, slots):
    stats = {k.removeprefix("angular.stats."): v for k, v in fold.items() if k.startswith("angular.stats.")}
    x = angular_tokens(bins, anchor, slots, mode, stats)
    prefix = condition + "." + mode + "."
    z = encode(config, base, linear(fold, prefix + "project", x))
    return linear(fold, prefix + "readout", z) * stats["residual_scale"] + stats["residual_center"] + anchor


def matched_comparators(folder, table, person, rows, hashes):
    path = folder / "predictions" / (PEOPLE[person] + ".npz")
    if isinstance(hashes[path.name], str) and digest(path) != hashes[path.name]:
        raise ValueError("Earlier cross-fitted predictions changed")
    with np.load(path, allow_pickle=False) as old:
        for k in ("person", "block", "trial", "slot", "parent", "cue", "target_tick", "target"):
            np.testing.assert_array_equal(old[k], table[k][rows])
        np.testing.assert_array_equal(old["pred_persistence"], table["anchor"][rows])
        if isinstance(hashes[path.name], dict):
            for key, expected in hashes[path.name].items():
                if hashlib.sha256(np.ascontiguousarray(old[key]).tobytes()).hexdigest() != expected:
                    raise ValueError(f"Rebuilt comparator differs numerically on {path.name}, {key}")
        return {"prior_motion_cnn": old["pred_base"], "prior_emg_corrected_cnn": old["pred_corrected_emg"]}


def person_mse(x, person):
    return np.stack([np.mean(x[person == p]**2, axis=0) for p in range(6)])


def rms(x):
    return float(np.sqrt(np.mean(x)))


def metrics(preds, target, groups):
    mses = {k: person_mse(v - target, groups) for k, v in preds.items()}
    scores = {k: {"rmse_deg": rms(m), "axis_rmse_deg": np.sqrt(m.mean(axis=0)).tolist()} for k, m in mses.items()}
    pairs = [("pretrained.full", "pretrained.motion"), ("pretrained.emg", "pretrained.motion"),
             ("pretrained.full", "pretrained.emg")]
    for mode in MODES:
        pairs.append(("pretrained." + mode, "random." + mode))
        for base in ("persistence", "prior_motion_cnn", "prior_emg_corrected_cnn"):
            if base in preds:
                pairs.append(("pretrained." + mode, base))
    sensitivity = {}
    for condition in ("pretrained", "random"):
        for mode in ("emg", "full"):
            name = condition + "." + mode
            switched = name + ".wrong"
            pairs.append((name, switched))
            shift = preds[name] - preds[switched]
            sensitivity[name] = {
                "rms_shift_deg": rms(person_mse(shift, groups)),
                "equal_person_mean_signed_axis_shift_deg": np.mean([shift[groups==g].mean(axis=0) for g in range(6)], axis=0).tolist(),
                "equal_person_mean_absolute_axis_shift_deg": np.mean([abs(shift[groups==g]).mean(axis=0) for g in range(6)], axis=0).tolist()}
    comparisons = {}
    for a, b in pairs:
        ma, mb = mses[a], mses[b]
        leave = [rms(np.delete(ma, g, axis=0)) - rms(np.delete(mb, g, axis=0)) for g in range(6)]
        comparisons[a + " minus " + b] = {"difference_deg": rms(ma) - rms(mb), "people_lower_error": int((ma.mean(1) < mb.mean(1)).sum()),
                                            "omit_one_from_summary_range_deg": [min(leave), max(leave)]}
    return {"scores": scores, "comparisons": comparisons, "signal_swaps": sensitivity}, mses


def run(args):
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    seal = json.loads((args.fits / "seal.json").read_text())
    for k, v in seal["files"].items():
        if digest(args.fits / k) != v:
            raise ValueError(f"Fit changed: {k}")
    table = read_table(args.data, args.manifest)
    config, pretrained = read_checkpoint(args.fits / "movement-weights.npz")
    with np.load(args.fits/"random-core.npz", allow_pickle=False) as f:
        random = {k: f[k].astype(np.float64) for k in f.files}
    hashes = None
    if args.rebuilt_comparators:
        hashes = json.loads(Path(__file__).with_name("comparator-arrays.json").read_text())
    elif args.comparators:
        if digest(args.comparators / "scores.json") != COMPARATOR_SCORES:
            raise ValueError("Historical comparisons require their original accepted scores receipt")
        prior = json.loads((args.comparators / "scores.json").read_text())
        if prior["fit"] != COMPARATOR_FIT:
            raise ValueError("Wrong earlier fit")
        hashes = prior["predictions_sha256"]
    preds = {"persistence": table["anchor"].copy()}
    for p in range(6):
        ix = np.flatnonzero(table["person"] == p)
        donor = table["donor"][ix]
        fold_name = f"held-{p}"
        if p in seal["fits"][fold_name]["fitting_people"]:
            raise ValueError("Held-person contamination")
        with np.load(args.fits / (fold_name+".npz"), allow_pickle=False) as f:
            fold = {k: f[k].astype(np.float64) for k in f.files}
        current = {} if hashes is None else matched_comparators(args.comparators or args.rebuilt_comparators, table, p, ix, hashes)
        for condition, base in (("pretrained", pretrained), ("random", random)):
            for mode, c in MODES.items():
                name = condition + "." + mode
                bins = table["bins"][ix, :, :c].copy()
                def infer(b):
                    return held_forecast(fold, config, base, condition, mode, b, table["anchor"][ix], table["slot"][ix])
                current[name] = infer(bins)
                if mode != "motion":
                    begin = 2 if mode == "emg" else 6
                    bins[:, :, begin:c] = table["bins"][donor, :, begin:c]
                    current[name + ".wrong"] = infer(bins)
        for k, v in current.items():
            if k not in preds:
                preds[k] = np.full(table["target"].shape, np.nan)
            preds[k][ix] = v
    if not all(np.isfinite(a).all() for a in preds.values()):
        raise ValueError("Incomplete held-person predictions")
    summary, mses = metrics(preds, table["target"], table["person"])
    private = {k: table[k] for k in ("person","block","trial","slot","parent","cue","target_tick","target","donor")}
    private.update({"pred." + k: v for k,v in preds.items()})
    private.update({"person_mse." + k: v for k,v in mses.items()})
    write_state(args.out / "private-scores.npz", private)
    save_json(args.out / "summary.json", {"units":"degrees", "people":6, "trials":1879, "rows":11274,
              "axes":["extension","radial_deviation"], "array_manifest_sha256":TABLE_MANIFEST_HASH,
              "fit_seal":digest(args.fits / "seal.json"), "prior_comparator_fit": COMPARATOR_FIT if hashes else None, **summary})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("data", "manifest", "fits", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    controls = parser.add_mutually_exclusive_group()
    controls.add_argument("--comparators", type=Path)
    controls.add_argument("--rebuilt-comparators", type=Path)
    run(parser.parse_args())
