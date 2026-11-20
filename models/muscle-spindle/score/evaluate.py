"""Read held predictions, build hierarchical score tables, test frozen descriptive gates."""

import argparse
import csv
import gzip
import io
from pathlib import Path

import numpy as np
from poisson import (
    KEYS,
    MODES,
    balanced_weights,
    dump,
    earlier_indices,
    group_ids,
    sha,
    subset,
)
from scipy.special import xlogy

FLOOR = 1e-8
SEEDS = (1641, 2718, 3917)
METRICS = ("deviance", "mae", "observed", "forecast", "bias", "observed_over_forecast")


def loss(y, pred):
    if not np.isfinite(pred).all() or (pred < 0).any():
        raise ValueError("Expected finite nonnegative count predictions")
    mu = np.maximum(pred, FLOOR)
    return 2 * (xlogy(y, y) - xlogy(y, mu) - y + mu), np.abs(y - pred)


def levels(meta):
    total = len(meta["trial"])
    output = []
    for i, level in enumerate(("macro", "prefix", "member", "trial")):
        cols = KEYS[:i]
        idx = group_ids(*(meta[c] for c in cols)) if i else np.zeros(total, dtype=int)
        _, starts = np.unique(idx, return_index=True)
        labels = ["/".join(str(meta[c][j]) for c in cols) or "all" for j in starts]
        output.append((level, idx, labels, np.bincount(idx).tolist()))
    return output


def load_npz(path):
    with np.load(path, allow_pickle=False) as source:
        return {name: source[name] for name in source.files}


def require_metadata(meta, other, y):
    for key in KEYS:
        if not np.array_equal(other[key], meta[key]):
            raise ValueError(f"OOF input row order mismatch: {key}")
    if not np.array_equal(y, other["y_count"]):
        raise ValueError("OOF label mismatch")


def summarize(rates, meta, y, support, support_label):
    sm = subset(meta, support)
    all_levels = levels(sm)
    balance = balanced_weights(sm)
    truth = y[support].astype(float)
    result, calibration = {}, []
    identifiers = {
        level: list(zip(labels, counts)) for level, _, labels, counts in all_levels
    }
    for name, raw in rates.items():
        predictions = raw[support]
        if predictions.ndim == 1:
            predictions = predictions[:, None]
        nseeds = predictions.shape[1]
        methods = []
        for j, p in enumerate(predictions.T):
            dev, mae = loss(truth, p)
            metrics = [dev, mae, truth, p, p - truth]
            seed = str(SEEDS[j]) if nseeds > 1 else "fixed"
            methods.append((seed, metrics))
        if nseeds > 1:
            merged = [
                np.mean([metrics[k] for _, metrics in methods], axis=0)
                for k in range(5)
            ]
            methods.append(("mean", merged))
        for seed, metrics in methods:
            table = {}
            for level, ids, keys, _ in all_levels:
                denom = np.bincount(ids, weights=balance)
                means = np.stack(
                    [np.bincount(ids, weights=balance * v) / denom for v in metrics],
                    axis=1,
                )
                table[level] = {key: as_dict(row) for key, row in zip(keys, means)}
            result[name, seed] = table
        for j, p in enumerate(predictions.T):
            seed = str(SEEDS[j]) if nseeds > 1 else "fixed"
            bounds = np.array([0, 0.5, 1, 2, 4, np.inf])
            bucket = np.searchsorted(bounds, p, side="right") - 1
            calibration_groups = [("macro", "all", np.ones(len(p), dtype=bool))]
            calibration_groups.extend(
                ("prefix", str(int(g)), sm["prefix"] == g)
                for g in np.unique(sm["prefix"])
            )
            calibration_groups.extend(
                ("member", str(a), sm["afferent"] == a)
                for a in np.unique(sm["afferent"])
            )
            for level, group, mask in calibration_groups:
                for b in range(5):
                    chosen = mask & (bucket == b)
                    n = int(chosen.sum())
                    weights = balance[chosen]
                    group_mass = float(weights.sum())
                    calibration.append(
                        dict(
                            support=support_label,
                            model=name,
                            seed=seed,
                            prefix=group
                            if level != "member"
                            else str(sm["prefix"][mask][0]),
                            level=level,
                            group=group,
                            left=float(bounds[b]),
                            right="inf" if b == 4 else float(bounds[b + 1]),
                            n_windows=n,
                            weight_fraction=group_mass / balance[mask].sum(),
                            forecast=float(np.average(p[chosen], weights=weights))
                            if n
                            else None,
                            observed=float(np.average(truth[chosen], weights=weights))
                            if n
                            else None,
                        )
                    )
    return result, identifiers, calibration


def as_dict(row):
    return dict(
        zip(METRICS, [*map(float, row), (float(row[2] / row[3]) if row[3] else None)])
    )


def write_csv(path, rows):
    """Stable gzip metadata makes repeated output byte-identical."""
    with (
        path.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as zipped,
    ):
        with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def evaluate_frozen(results, held_level="prefix"):
    primary = results["full"]
    stale = results["common_lag"]
    gates, deltas = {}, []

    def compare(label, a, b, table, support):
        primary_seed = "mean" if (a, "mean") in table else "fixed"
        seed_keys = (
            (primary_seed, *map(str, SEEDS)) if primary_seed == "mean" else ("fixed",)
        )
        passed = {}
        for seed in seed_keys:
            other = seed if (b, seed) in table else "fixed"
            delta = {}
            for level in ("macro", "prefix", "member", "trial"):
                for group, a_scores in table[a, seed][level].items():
                    b_scores = table[b, other][level][group]
                    d = {m: a_scores[m] - b_scores[m] for m in ("mae", "deviance")}
                    deltas.append(
                        dict(
                            comparison=label,
                            support=support,
                            model=a,
                            comparator=b,
                            seed=seed,
                            level=level,
                            group=group,
                            **d,
                        )
                    )
                    if level in ("macro", held_level):
                        delta[group] = d
            passed[seed] = delta
        return passed

    def ok_held(ds):
        return all(v["deviance"] < 0 for k, v in ds.items() if k != "all")

    for family in ("glm", "transformer"):
        all_model = f"{family}_all"
        central = "mean" if family == "transformer" else "fixed"
        individual = list(map(str, SEEDS)) if central == "mean" else ["fixed"]
        conditions = {}
        pairs = {}
        for mode in (
            "history",
            "mechanics",
            "force",
            "position",
            "constant",
            "recent_smoothed",
            "recent_five",
            "recent_one",
        ):
            other = f"{family}_{mode}" if mode in MODES else mode
            pairs[mode] = compare(
                f"{family}_combined_vs_{mode}", all_model, other, primary, "full"
            )
            if mode in ("history", "mechanics"):
                c = pairs[mode][central]
                conditions[f"all_{held_level}_deviance_vs_{mode}"] = ok_held(c)
                conditions[f"macro_mae_vs_{mode}"] = c["all"]["mae"] < 0
                conditions[f"all_seed_macro_deviance_vs_{mode}"] = all(
                    pairs[mode][s]["all"]["deviance"] < 0 for s in individual
                )
            if mode in ("constant", "recent_smoothed"):
                conditions[f"macro_deviance_and_mae_vs_{mode}"] = all(
                    v < 0 for v in pairs[mode][central]["all"].values()
                )
        gates[family + "_conditional"] = dict(
            pass_all=all(conditions.values()), conditions=conditions, paired=pairs
        )
        c = compare(
            f"{family}_current_vs_stale_mechanics",
            all_model,
            family + "_stale",
            stale,
            "common_lag",
        )
        cond = {
            f"all_{held_level}_deviance": ok_held(c[central]),
            "macro_mae": c[central]["all"]["mae"] < 0,
            "all_seed_macro_deviance": all(
                c[s]["all"]["deviance"] < 0 for s in individual
            ),
        }
        gates[family + "_timing"] = dict(
            pass_all=all(cond.values()), conditions=cond, paired=c
        )
    c = compare(
        "transformer_vs_glm_joint", "transformer_all", "glm_all", primary, "full"
    )
    cond = {
        f"all_{held_level}_deviance": ok_held(c["mean"]),
        "macro_mae": c["mean"]["all"]["mae"] < 0,
        "all_seed_macro_deviance": all(c[str(s)]["all"]["deviance"] < 0 for s in SEEDS),
    }
    gates["transformer_over_primary_glm"] = dict(
        pass_all=all(cond.values()), conditions=cond, paired=c
    )
    for candidate in ("glm_afferent", "glm_sampled"):
        compare(
            "transformer_vs_" + candidate, "transformer_all", candidate, primary, "full"
        )
        compare(candidate + "_vs_primary_glm", candidate, "glm_all", primary, "full")
    return gates, deltas


def read_predictions(glm_path, transformer_path, aux_path):
    g, t, aux = (load_npz(path) for path in (glm_path, transformer_path, aux_path))
    meta = {k: g[k] for k in KEYS}
    y = g["y_count"]
    population = str(g["population"].item())
    if population != str(aux["population"].item()):
        raise ValueError("Primary and auxiliary GLMs use different populations")
    require_metadata(meta, t, y)
    require_metadata(meta, aux, y)
    if tuple(t["seeds"]) != SEEDS or tuple(aux["seeds"]) != SEEDS:
        raise ValueError("Unexpected seed order")
    modes = t["modes"].tolist()
    if set(modes) != set(MODES) or len(modes) != len(MODES):
        raise ValueError("Unexpected Transformer inputs")
    all_rates = {
        k: g[k] for k in ("constant", "recent_one", "recent_five", "recent_smoothed")
    }
    for k in MODES:
        all_rates["glm_" + k] = g[k]
        all_rates["transformer_" + k] = t["rate"][:, modes.index(k), :]
    all_rates.update(glm_afferent=aux["afferent_weighted"], glm_sampled=aux["sampled"])
    allowed = earlier_indices(meta) >= 0
    if not np.array_equal(np.isfinite(g["stale"]), allowed) or not np.array_equal(
        np.isfinite(t["wrong_mechanics"]),
        np.broadcast_to(allowed[:, None], t["wrong_mechanics"].shape),
    ):
        raise ValueError("Shifted histories lack matched common support")
    lagged = {
        "glm_all": g["all"],
        "glm_stale": g["stale"],
        "transformer_all": all_rates["transformer_all"],
        "transformer_stale": t["wrong_mechanics"],
    }
    return meta, y, population, all_rates, lagged, allowed


def run(glm_path, transformer_path, aux_path, out):
    meta, y, population, all_rates, lagged, allowed = read_predictions(
        glm_path, transformer_path, aux_path
    )
    held_level = "member" if population == "strict-afferent" else "prefix"
    results, sizes, summaries, tables, calibrations = {}, {}, {}, [], []
    for name, rates, support in (
        ("full", all_rates, np.ones(len(y), bool)),
        ("common_lag", lagged, allowed),
    ):
        results[name], ids, cal = summarize(rates, meta, y, support, name)
        sizes[name] = {level: dict(entries) for level, entries in ids.items()}
        calibrations.extend(cal)
        public = {}
        for (model, seed), table in results[name].items():
            for level, groups in table.items():
                for group, values in groups.items():
                    tables.append(
                        dict(
                            support=name,
                            model=model,
                            seed=seed,
                            level=level,
                            group=group,
                            n_windows=sizes[name][level][group],
                            **values,
                        )
                    )
            public.setdefault(model, {})[seed] = {
                level: table[level] for level in ("macro", "prefix", "member")
            }
        summaries[name] = public
    ranges = {}
    for support_name, matrix in summaries.items():
        ranges[support_name] = {}
        for model, by_seed in matrix.items():
            central = by_seed.get("mean", by_seed.get("fixed"))
            individual = [table for seed, table in by_seed.items() if seed != "mean"]
            ranges[support_name][model] = {}
            for metric in METRICS:
                prefixes = [
                    metrics[metric]
                    for metrics in central[held_level].values()
                    if metrics[metric] is not None
                ]
                seeds = [
                    table["macro"]["all"][metric]
                    for table in individual
                    if table["macro"]["all"][metric] is not None
                ]
                ranges[support_name][model][metric] = {
                    f"held_{held_level}_min_max": [min(prefixes), max(prefixes)]
                    if prefixes
                    else None,
                    "macro_seed_min_max": [min(seeds), max(seeds)] if seeds else None,
                }
    gates, paired = evaluate_frozen(results, held_level)
    for row in tables + paired + calibrations:
        row["population"] = population
    write_csv(out / "group-scores.csv.gz", tables)
    write_csv(out / "paired-differences.csv.gz", paired)
    write_csv(
        out / "calibration-bins.csv.gz",
        [r for r in calibrations if r["level"] != "member"],
    )
    write_csv(
        out / "member-calibration-bins.csv.gz",
        [r for r in calibrations if r["level"] == "member"],
    )
    dump(
        out / "summary.json",
        {
            "population": population,
            "interpretation": {
                "strict-afferent": "Exploratory held-afferent forecasts in three original two-clock members, all from filename prefix 0. The registered three-prefix evaluation was unevaluable in both populations.",
                "strict": "independent archived mechanical and electrical time arrays",
                "mixed-clock": "conditional sensitivity including records with only one deposited time axis",
            }.get(population, population),
            "metric_unit": "count in the next 20 ms",
            "primary_metric": "Poisson deviance",
            "difference_sign": "model minus comparator; negative favors model for MAE and deviance",
            "balanced_order": "windows → trials → members → prefixes",
            "group_sizes_windows": sizes,
            "seed_semantics": "mean is arithmetic mean of separately scored seed losses; no rate ensemble",
            "groups_are_not_confirmed_animals": True,
            "outcome": f"descriptive held-{held_level} development evaluation",
            "held_unit": held_level,
            "original_three_prefix_gates_evaluable": population != "strict-afferent",
            "inputs_sha256": {
                p.name: sha(p) for p in (glm_path, transformer_path, aux_path)
            },
            "models": summaries,
            "descriptive_ranges": ranges,
            "gates": gates,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("glm", "transformer", "auxiliary", "out"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.glm, args.transformer, args.auxiliary, args.out)
