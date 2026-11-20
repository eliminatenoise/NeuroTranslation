"""Reference scoring for the 100-ms area 2 handle forecast. Requires NumPy only."""
import argparse
import csv
import hashlib
import json
import gzip
import tempfile
from itertools import zip_longest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
FIELDS = ("trial", "original_trial", "epoch", "offset", "k", "donor", "movement",
          "neural", "cue", "y", "cv", "observed_direction", "unit_guide")
SEEDS = (17, 41, 73)
BRANCHES = {
    "all": ("movement", "cue", "neural"),
    "movement_cue": ("movement", "cue"),
    "neural_cue": ("neural", "cue"),
    "cue_only": ("cue",),
    "movement_only": ("movement",),
    "neural_only": ("neural",),
    "movement_cue_population_rate": ("movement", "cue", "population_rate"),
    "movement_cue_unit_rate": ("movement", "cue", "unit_rate"),
}
TRANSFORMERS = tuple(BRANCHES)[:6] + ("wrong_neural",)
MEASURES = ("euclidean", "x_mae", "y_mae", "x_bias", "y_bias")
EPOCHS = ("bump", "reach")
RIDGE_LAMBDA = 0.01
SHAPES = {"movement": (5, 4), "cue": (5, 7), "neural": (5, 30), "cv": (3, 2),
          "observed_direction": (2,), "y": (2,)}
CI_DRAWS = 5000
BLOCK = 8
BOOT_SEED = 20261121


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def columns(source, keys):
    with np.load(source, allow_pickle=False) as bundle:
        return {key: bundle[key] for key in keys}


def require(value, message):
    if not value:
        raise ValueError(message)


def open_source(path, stage):
    data = columns(path, FIELDS)
    count = {"train": 324, "validation": 108, "test": 108}[stage]
    check_source(data, count)
    expected = json.loads((HERE / "original-ids.json").read_text())[stage]
    require(np.array_equal(data["original_trial"], expected), "wrong original trial partition")
    return data


def check_source(data, expected_originals):
    original = data["original_trial"]
    trial = data["trial"]
    epoch = data["epoch"]
    offset = data["offset"]
    n = len(trial)
    require(original.shape == (expected_originals,) and np.all(np.diff(original) > 0),
            "original trial identity / chronological order")
    for name in ("original_trial", "trial", "epoch", "offset", "k", "donor"):
        require(data[name].dtype.kind in "iu" and data[name].ndim == 1, name)
        if name != "original_trial":
            require(len(data[name]) == n, name)
    require(n > 0 and np.isin(trial, original).all(), "unknown original")
    require(np.isin(epoch, (0, 1)).all() and np.isin(offset, (0, 5, 10, 15)).all(),
            "epoch/offset")
    keys = np.stack((trial, epoch, offset), axis=1)
    require(len(np.unique(keys, axis=0)) == n, "duplicate original, epoch and offset")
    for name, shape in SHAPES.items():
        require(data[name].shape == (n, *shape), name)
        if name != "observed_direction":
            require(np.isfinite(data[name]).all(), f"nonfinite {name}")
    require(data["unit_guide"].shape == (30, 2)
            and np.all(data["unit_guide"][:, 1] > 0), "positive sorted-unit guide")
    require(np.all(data["neural"] >= 0)
            and np.equal(data["neural"], np.floor(data["neural"])).all(), "spike counts")
    donor = data["donor"]
    require(np.all((donor >= -1) & (donor < n)), "donor outside source")
    valid = donor >= 0
    d = donor[valid]
    require(np.all(trial[d] < trial[valid]), "non-earlier original donor")
    for name in ("epoch", "offset", "observed_direction"):
        require(np.array_equal(data[name][d], data[name][valid], equal_nan=True),
                f"donor stratum mismatch {name}")
    require(np.allclose(data["cue"][d, -1], data["cue"][valid, -1], atol=1e-7),
            "donor cutoff cue mismatch")


def weights(trial, epoch):
    """Each original weighs one and equally divides its weight among its epochs."""
    groups, group_index, n_windows = np.unique(
        np.stack((trial, epoch), axis=1), axis=0, return_inverse=True, return_counts=True)
    trials, trial_index, n_epochs = np.unique(
        groups[:, 0], return_inverse=True, return_counts=True)
    return 1.0 / (len(trials) * n_epochs[trial_index[group_index]] * n_windows[group_index])


def design_parts(data, wrong=False):
    m = data["movement"]
    c = data["cue"]
    n = data["neural"]
    if wrong:
        n = n[np.maximum(data["donor"], 0)]
    def flattened(name, a, names):
        return (a.reshape(len(a), -1).astype(np.float64),
                [f"token{i + 1}_{name}_{key}" for i in range(a.shape[1]) for key in names])
    unit_names = [f"electrode_{int(ch)}_sort_{int(unit)}" for ch, unit in data["unit_guide"]]
    return {
        "movement": flattened("movement", m, ("x_cm", "y_cm", "dx_cm", "dy_cm")),
        "cue": flattened("cue", c, ("bump_known", "bump_cos", "bump_sin",
                                     "target_known", "target_cos", "target_sin", "go_known")),
        "neural": flattened("spikes", n, unit_names),
        "population_rate": flattened("rate", n.sum(axis=2, keepdims=True) / 0.04,
                                    ("population_events_per_s",)),
        "unit_rate": (n.sum(axis=1) / 0.20, [s + "_events_per_s" for s in unit_names]),
    }


def design(parts, branch):
    names = BRANCHES[branch]
    return (np.concatenate([parts[key][0] for key in names], axis=1),
            [label for key in names for label in parts[key][1]])


def fit_ridges(data):
    parts = design_parts(data)
    w = weights(data["trial"], data["epoch"])
    y = data["y"].astype(np.float64)
    intercept = w @ y
    fitted = {"unit_guide": data["unit_guide"], "lambda": np.asarray(RIDGE_LAMBDA)}
    for branch in BRANCHES:
        x, names = design(parts, branch)
        center = w @ x
        x -= center
        scale = np.sqrt(w @ np.square(x))
        scale[scale < 1e-10] = 1.0
        x /= scale
        weighted = w[:, None] * x
        gram = weighted.T @ x
        gram.flat[::len(gram) + 1] += RIDGE_LAMBDA
        fitted[branch + "_coef"] = np.linalg.solve(gram, weighted.T @ (y - intercept))
        for key, value in (("center", center), ("scale", scale), ("intercept", intercept),
                           ("features", np.asarray(names))):
            fitted[branch + "_" + key] = value
    return fitted


def ridge_control_predictions(data, fitted):
    parts = design_parts(data)
    require(np.array_equal(data["unit_guide"], fitted["unit_guide"]), "neural unit order")
    def predict(branch, inputs):
        x, names = design(inputs, branch)
        require(np.array_equal(fitted[branch + "_features"], names), "feature order")
        scaled = (x - fitted[branch + "_center"]) / fitted[branch + "_scale"]
        return (scaled @ fitted[branch + "_coef"] + fitted[branch + "_intercept"])[None]
    predicted = {"ridge_" + branch: predict(branch, parts) for branch in BRANCHES}
    wrong = predict("all", design_parts(data, wrong=True))
    wrong[:, data["donor"] < 0] = np.nan
    predicted["ridge_wrong_neural"] = wrong
    predicted["stationary"] = np.zeros((1, len(data["trial"]), 2))
    for index, ms in enumerate((40, 100, 200)):
        predicted[f"constant_velocity_{ms}ms"] = data["cv"][None, :, index]
    return predicted


def transformers(path, data, source_digest):
    keys = (*TRANSFORMERS, "trial", "epoch", "offset", "k", "donor", "source_sha256", "seeds")
    models = columns(path, keys)
    require(str(models["source_sha256"].item()) == source_digest, "prediction source digest")
    require(np.array_equal(models["seeds"], SEEDS), "unexpected seed order")
    for key in ("trial", "epoch", "offset", "k", "donor"):
        require(np.array_equal(models[key], data[key]), f"prediction identity {key}")
    out = {}
    for name in TRANSFORMERS:
        pred = models[name].astype(np.float64)
        require(pred.shape == (3, len(data["trial"]), 2), f"prediction shape {name}")
        if name == "wrong_neural":
            require(np.isfinite(pred[:, data["donor"] >= 0]).all(), "missing donor forecast")
            require(np.isnan(pred[:, data["donor"] < 0]).all(), "unmatched donor forecast")
        else:
            require(np.isfinite(pred).all(), f"nonfinite prediction {name}")
        out["transformer_" + name] = pred
    return out


def metrics(forecast, y):
    residual = forecast - y
    return np.concatenate((np.linalg.norm(residual, axis=-1, keepdims=True),
                           np.abs(residual), residual), axis=-1)


def bootstrap_counts(n):
    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    start = rng.integers(n, size=(CI_DRAWS, (n + BLOCK - 1) // BLOCK))
    drawn = ((start[:, :, None] + np.arange(BLOCK)) % n).reshape(CI_DRAWS, -1)[:, :n]
    counts = np.zeros((CI_DRAWS, n), dtype=np.float64)
    np.add.at(counts, (np.arange(CI_DRAWS)[:, None], drawn), 1)
    return counts


def summarize(trial, epoch, original, measures):
    """Calculate trial-epoch and trial means for S×N×5 per-window losses."""
    groups, idx, windows = np.unique(np.stack((trial, epoch), axis=1), axis=0,
                                     return_inverse=True, return_counts=True)
    n_seed, _, n_metric = measures.shape
    by_epoch = np.zeros((len(groups), n_seed, n_metric))
    np.add.at(by_epoch, idx, measures.transpose(1, 0, 2))
    by_epoch /= windows[:, None, None]
    group_trial = np.searchsorted(original, groups[:, 0])
    present = np.bincount(group_trial, minlength=len(original))
    by_trial = np.zeros((len(original), n_seed, n_metric))
    np.add.at(by_trial, group_trial, by_epoch)
    by_trial /= np.maximum(present, 1)[:, None, None]
    return groups, windows, by_epoch, present > 0, by_trial


def labels_for(model):
    return SEEDS if model.startswith("transformer_") else ("fixed",)


def per_seed(estimates, labels):
    return dict(zip(map(str, labels), estimates.tolist(), strict=True))


def contrasts(names):
    return (
        [(name + "_minus_joint", name, "transformer_all") for name in names
         if name != "transformer_all"]
        + [("ridge_" + c + "_minus_ridge_joint", "ridge_" + c, "ridge_all")
           for c in ("movement_cue", "wrong_neural")]
    )


def summarize_subset(data, chosen, losses, counts, include_ci, writer=None):
    original = data["original_trial"]
    t, e = data["trial"][chosen], data["epoch"][chosen]
    summary = {"n_trials": int(len(np.unique(t))), "n_windows": int(len(t)),
               "n_trial_epochs": int(len(set(zip(t.tolist(), e.tolist())))),
               "models": {}, "contrasts_cm": {}}
    if not chosen.any():
        return summary
    model_trials = {}
    for name, loss in losses.items():
        groups, windows, by_epoch, represented, by_trial = summarize(
            t, e, original, loss[:, chosen])
        seed_metrics = by_trial[represented].mean(axis=0)
        labels = labels_for(name)
        summary["models"][name] = {
            "mean": dict(zip(MEASURES, seed_metrics.mean(axis=0).tolist(), strict=True)),
            "by_seed": {label: dict(zip(MEASURES, values, strict=True))
                        for label, values in per_seed(seed_metrics, labels).items()},
        }
        if writer is not None:
            for i, (trial, epoch) in enumerate(groups):
                for s, seed in enumerate(labels):
                    writer.writerow([trial, EPOCHS[epoch], windows[i], name, seed,
                                     *by_epoch[i, s].tolist()])
        model_trials[name] = by_trial[:, :, 0]
    boot = counts[:, represented] if include_ci else None
    total = boot.sum(axis=1) if include_ci else None
    for key, left, right in contrasts(losses):
        if left not in losses or right not in losses:
            continue
        pair = (model_trials[left] - model_trials[right])[represented]
        by_seed = pair.mean(axis=0)
        result = {"mean": float(by_seed.mean()),
                  "by_seed": per_seed(by_seed, SEEDS if pair.shape[1] == 3 else ("fixed",)),
                  "seed_min_max": [float(by_seed.min()), float(by_seed.max())]}
        if include_ci:
            valid = total > 0
            draws = (boot[valid] @ pair.mean(axis=1)) / total[valid]
            result["ci95"] = np.quantile(draws, (0.025, 0.975)).tolist()
            result["bootstrap_nonempty"] = int(valid.sum())
        summary["contrasts_cm"][key] = result
    return summary


def classify(interval):
    if interval[0] > 0:
        return "improvement"
    if interval[1] < 0:
        return "worsening"
    return "unresolved"


def evaluate(data, predicted, destination):
    trial, epoch = data["trial"], data["epoch"]
    matched = data["donor"] >= 0
    require(matched.any(), "no eligible matched recipient")
    losses = {name: metrics(values, data["y"]) for name, values in predicted.items()}
    counts = bootstrap_counts(len(data["original_trial"]))
    has_both = np.intersect1d(trial[matched & (epoch == 0)], trial[matched & (epoch == 1)])
    subsets = {"matched": (matched, True),
               "matched_both_epochs": (matched & np.isin(trial, has_both), True)}
    coverage = {}
    for code, label in enumerate(EPOCHS):
        phase = epoch == code
        subsets["matched_" + label] = (matched & phase, True)
        seen = data["observed_direction"][:, code]
        dirs = np.unique(seen[phase & np.isfinite(seen)])
        for value in dirs:
            subsets[f"matched_{label}_{value:g}deg"] = (matched & phase & (seen == value), False)
        subsets[f"matched_{label}_direction_unavailable"] = (matched & phase & np.isnan(seen), False)
        coverage[label] = {
            "source_trials": int(len(np.unique(trial[phase]))), "source_windows": int(phase.sum()),
            "matched_trials": int(len(np.unique(trial[matched & phase]))),
            "matched_windows": int((matched & phase).sum()),
            "no_earlier_exact_donor_windows": int((~matched & phase).sum()),
        }
    reports = {}
    with (destination / "matched-trial-epochs.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("original_trial", "epoch", "n_windows", "model", "seed", *MEASURES))
        for label, (chosen, interval) in subsets.items():
            reports[label] = summarize_subset(data, chosen, losses, counts, interval,
                                             writer=writer if label == "matched" else None)
    main = {k: losses[k] for k in ("transformer_all", "transformer_movement_cue")}
    reports["all_eligible_no_donor_required"] = summarize_subset(
        data, np.ones(len(trial), dtype=bool), main, counts, True)
    selections = {"incremental": "transformer_movement_cue_minus_joint",
                  "wrong_trial_control": "transformer_wrong_neural_minus_joint"}
    decisions = {k: classify(reports["matched"]["contrasts_cm"][v]["ci95"])
                 for k, v in selections.items()}
    return {"n_originals_in_block": len(data["original_trial"]), "n_eligible_windows": len(trial),
            "n_originals_with_eligible_window": len(np.unique(trial)), "support": coverage,
            "decision": decisions, "subsets": reports}


def render(report):
    lines = ["# " + report["stage"].capitalize() + " scores", "",
             "The endpoint is the recorded change in handle position over the next 100 ms. "
             "Errors are in cm. Positive paired differences favor the correctly paired joint Transformer.",
             "", "| Subset | Originals | Windows | Joint error | Added spikes, difference [95% interval] | "
             "Wrong-trial minus correct [95% interval] |", "|---|---:|---:|---:|---:|---:|"]
    for key in ("matched", "matched_bump", "matched_reach", "matched_both_epochs"):
        s = report["subsets"][key]
        if not s["n_windows"]:
            continue
        models, effects = s["models"], s["contrasts_cm"]
        def effect(name):
            entry = effects[name]
            lo, hi = entry["ci95"]
            return f"{entry['mean']:.4f} [{lo:.4f}, {hi:.4f}]"
        lines.append(f"| {key.replace('_',' ')} | {s['n_trials']} | {s['n_windows']} | "
                     f"{models['transformer_all']['mean']['euclidean']:.4f} | "
                     f"{effect('transformer_movement_cue_minus_joint')} | "
                     f"{effect('transformer_wrong_neural_minus_joint')} |")
    lines += ["", "| Model on matched recipients | Euclidean | x MAE | y MAE | x bias | y bias |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, stats in report["subsets"]["matched"]["models"].items():
        row = " | ".join(f"{stats['mean'][k]:.4f}" for k in MEASURES)
        lines.append(f"| {name} | {row} |")
    lines += ["", "Each original receives equal weight. Within an original, available epochs receive "
              "equal weight. Seeds, windows and paired epochs belong to a single recording from one animal. "
              "Intervals resample blocks of eight chronological originals and condition on the fitted "
              "models and fixed donor mapping. Bias is predicted minus recorded displacement.",
              "", "scores.json includes directions available at cutoff, seed-specific results, both-epoch "
              "sensitivity, matched sizes and the separate donor-free comparison. matched-trial-epochs.csv "
              "contains the original-level epoch means used to reconstruct the estimates.", ""]
    return "\n".join(lines)


TOLERANCE = 1e-10


def verify_tree(actual, expected, label):
    """Compare numbers within an absolute tolerance and all identities exactly."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and expected.keys() == actual.keys(), label)
        return sum(verify_tree(actual[k], v, f"{label}.{k}") for k, v in expected.items())
    if isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label)
        return sum(verify_tree(a, e, f"{label}[{i}]")
                   for i, (a, e) in enumerate(zip(actual, expected, strict=True)))
    if isinstance(expected, float):
        require(isinstance(actual, (int, float)) and abs(actual - expected) <= TOLERANCE, label)
    else:
        require(type(actual) is type(expected) and actual == expected, label)
    return 1


def verify_rows(actual_path, expected_path):
    count = 0
    with actual_path.open(newline="") as actual, gzip.open(expected_path, "rt", newline="") as expected:
        r, e = csv.reader(actual), csv.reader(expected)
        require(next(r) == next(e), "trial/epoch table columns")
        for a, b in zip_longest(r, e):
            require(a is not None and b is not None and a[:5] == b[:5], "trial/epoch identity")
            require(len(a) == len(b) == 10, "trial/epoch row width")
            for i, name in enumerate(MEASURES, start=5):
                require(abs(float(a[i]) - float(b[i])) <= TOLERANCE, f"trial/epoch {a[:5]} {name}")
            count += 1
    return count


def verify_ridges(fitted):
    largest = 0.0
    with np.load(HERE / "train" / "ridge-weights.npz", allow_pickle=False) as expected:
        require(set(fitted) == set(expected), "ridge arrays")
        for key in expected:
            a, b = fitted[key], expected[key]
            require(a.shape == b.shape, key)
            if b.dtype.kind in "fi":
                gap = float(np.max(np.abs(a - b)))
                require(gap <= TOLERANCE, f"ridge {key} larger than tolerance")
                largest = max(largest, gap)
            else:
                require(np.array_equal(a, b), f"ridge identities {key}")
    return largest


def run(args, output):
    if args.refit:
        require(args.weights is None, "choose --refit or --weights")
        fitted = fit_ridges(open_source(args.source / "train.npz", "train"))
        np.savez_compressed(output / "ridge-weights.npz", **fitted)
    else:
        weightfile = args.weights or HERE / "train" / "ridge-weights.npz"
        with np.load(weightfile, allow_pickle=False) as archive:
            fitted = {k: archive[k] for k in archive}
    largest = verify_ridges(fitted)
    checks = {"ridge_source": "fresh training-only fit" if args.refit else "supplied coefficients",
              "ridge_models": list(BRANCHES), "ridge_max_absolute_difference": largest,
              "absolute_tolerance": TOLERANCE, "stages": {}}
    for stage in ("validation", "test"):
        src = args.source / (stage + ".npz")
        data = open_source(src, stage)
        preds = args.predictions / (stage + "-predictions.npz")
        model = transformers(preds, data, digest(src))
        controls = ridge_control_predictions(data, fitted)
        out = output / stage
        out.mkdir()
        summary = {"stage": stage, "seed_order": list(SEEDS),
                   "interval": {"method": "circular moving block percentile",
                                "length_originals": BLOCK, "draws": CI_DRAWS, "seed": BOOT_SEED},
                   **evaluate(data, model | controls, out)}
        write_json(out / "scores.json", summary)
        (out / "RESULTS.md").write_text(render(summary))
        expected = HERE / stage
        values = verify_tree(summary, json.loads((expected / "scores.json").read_text()), stage)
        groups = verify_rows(out / "matched-trial-epochs.csv", expected / "matched-trial-epochs.csv.gz")
        require(render(summary) == (expected / "RESULTS.md").read_text(), stage + " rounded table")
        checks["stages"][stage] = {"checked_score_fields": values, "checked_trial_epoch_rows": groups,
                                   "methods": len(model) + len(controls), "decisions": summary["decision"],
                                   "source_npz_sha256": digest(src), "prediction_npz_sha256": digest(preds)}
    write_json(output / "comparison.json", checks)
    print(json.dumps(checks, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Reproduce the published 100-ms area 2 handle forecast scores.")
    parser.add_argument("--source", type=Path, default=HERE.parent / "source",
                        help="directory containing regenerated study NPZ files")
    parser.add_argument("--predictions", type=Path, default=HERE / "predictions",
                        help="directory containing validation-predictions.npz and test-predictions.npz")
    parser.add_argument("--weights", type=Path, help="eight fitted ridge models in one NPZ")
    parser.add_argument("--refit", action="store_true", help="fit all eight ridges from train.npz")
    parser.add_argument("--output", type=Path, required=True, help="new directory for reproduced scores")
    args = parser.parse_args()
    dest = args.output.resolve()
    require(not dest.exists(), "output directory already exists; choose a new name")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
        output = Path(temp) / "scores"
        output.mkdir()
        run(args, output)
        output.rename(dest)


if __name__ == "__main__":
    main()
