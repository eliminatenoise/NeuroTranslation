"""Fit and score the frozen HoloAssist protocol. Results stay spatially aggregated."""

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from learn import STRUCTURES, find_donors, fit, predictions
from windows import HERE, coverage, load_role, sha

CORE = ["windows.py", "learn.py", "run.py", "protocol.json", "protocol-addendum.json"]
SRC = ["preceding-words-source/COHORT.json", "preceding-words-source/events.jsonl"]


def write(path, obj):
    with path.open("x") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")


def binding(root):
    return {f: sha(HERE / f) for f in CORE} | {f: sha(root / f) for f in SRC}


def as_np(x):
    return {k: np.asarray(v) for k, v in x.items()}


def model_example(train, spec, weights):
    # Selection occurs before inspecting model predictions or comparing errors.
    row = min(train, key=lambda r: (r["record"], r["cutoff"], r["id"]))
    pred, matched = predictions([row], spec, weights, train)
    donor = find_donors([row], train, spec)[0] if spec else None
    retained = set(spec["vocabulary"]) if spec else set()
    return {
        "role": "train_illustration",
        "recording": row["record"],
        "group": row["group"],
        "task": row["task"],
        "event_id": row["id"],
        "speech_start_s": row["cutoff"] - row["lead"][0] - row["duration"],
        "speech_end_s": row["cutoff"] - row["lead"][0],
        "cutoff_s": row["cutoff"],
        "forecast_horizon_s": 1.0,
        "requested_endpoint_s": row["cutoff"] + 1.0,
        "actual_endpoint_grid_s": row["cutoff"] + row["lead"][1],
        "observed_cm": row["y"],
        "motion": row["motion"].tolist(),
        "context": row["context"].tolist(),
        "confidence_status": row["confidence"],
        "retained_tokens": sorted(set(row["tokens"]) & retained),
        "donor_tokens": sorted(set(train[donor]["tokens"]) & retained)
        if donor is not None
        else None,
        "donor_matched": bool(matched[0]),
        "predictions_cm": {
            k: float(v[0])
            for k, v in pred.items()
            if not k.endswith("substituted") or matched[0]
        },
    }


def fit_stage(root, out):
    out.mkdir(exist_ok=True, parents=True)
    if any(
        (out / f).exists()
        for f in ["fit.json", "weights.json", "example.json", "model.json"]
    ):
        raise FileExistsError("Choose an empty reproduction output directory")
    train, counts = load_role(root, "train")
    groups = len({r["group"] for r in train})
    admitted = len(train) >= 40 and groups >= 4
    spec, weights = fit(train) if admitted else ({}, {})
    write(out / "model.json", spec)
    write(out / "weights.json", {k: v.tolist() for k, v in weights.items()})
    if train:
        write(out / "example.json", model_example(train, spec, weights))
    write(
        out / "fit.json",
        {
            "inputs": binding(root),
            "coverage": coverage(train, counts),
            "ridge_admitted": admitted,
            "attention_admitted": bool(spec.get("attention_admitted")),
            "vocabulary_size": len(spec.get("vocabulary", [])),
            "model_sha256": sha(out / "model.json"),
            "weights_sha256": sha(out / "weights.json"),
            "structures": STRUCTURES,
        },
    )
    print(
        json.dumps(
            {
                "train_rows": len(train),
                "groups": groups,
                "ridge": admitted,
                "attention": spec.get("attention_admitted", False),
            }
        )
    )


def group_errors(rows, losses):
    groups = {}
    for group in sorted({r["group"] for r in rows}):
        rec_errors = []
        for rec in sorted({r["record"] for r in rows if r["group"] == group}):
            ix = [i for i, r in enumerate(rows) if r["record"] == rec]
            rec_errors.append(float(losses[ix].mean()))
        groups[group] = float(np.mean(rec_errors))
    return groups


def results(rows, predictions_by_model, take, include_donor):
    ix = np.flatnonzero(take)
    subset = [rows[i] for i in ix]
    models = {
        k: v
        for k, v in predictions_by_model.items()
        if include_donor or not k.endswith("substituted")
    }
    truth = np.array([r["y"] for r in subset])
    by_group = {
        k: group_errors(subset, np.abs(v[ix] - truth)) for k, v in models.items()
    }
    means = (
        {k: float(np.mean(list(d.values()))) for k, d in by_group.items()}
        if len(ix)
        else {}
    )
    comparisons = {}
    for actual in ["motion_context_words", "attention_actual"]:
        if actual not in means:
            continue
        for cmp in means:
            if cmp == actual:
                continue
            diff = [by_group[cmp][g] - by_group[actual][g] for g in by_group[actual]]
            arr = np.asarray(diff)
            rng = np.random.default_rng(917)
            boot = arr[rng.integers(len(diff), size=(2000, len(diff)))].mean(axis=1)
            comparisons[f"{cmp}_minus_{actual}"] = {
                "gain_cm": float(np.mean(arr)),
                "interval_cm": np.quantile(boot, [0.025, 0.975]).tolist(),
                "groups_favoring_actual": int(np.sum(arr > 0)),
                "groups": len(arr),
            }
    return {
        "scored_examples": len(ix),
        "recordings": len({r["record"] for r in subset}),
        "groups": len({r["group"] for r in subset}),
        "group_balanced_mae_cm": means,
        "by_group_mae_cm": by_group,
        "paired_differences": comparisons,
    }


def assess_stage(root, out):
    if (out / "assessment.json").exists():
        raise FileExistsError("Assessment already exists")
    prev = json.loads((out / "fit.json").read_text())
    if (
        binding(root) != prev["inputs"]
        or sha(out / "model.json") != prev["model_sha256"]
        or sha(out / "weights.json") != prev["weights_sha256"]
    ):
        raise ValueError("Inputs, methods or learned parameters changed after fit")
    spec = json.loads((out / "model.json").read_text())
    weights = as_np(json.loads((out / "weights.json").read_text()))
    train, _ = load_role(
        root, "train"
    )  # previously admitted donor inputs; no re-fitting
    rows, counts = load_role(root, "assessment")
    summary = coverage(rows, counts)
    if rows:
        pred, matched = predictions(rows, spec, weights, train)
        all_scored = results(rows, pred, np.ones(len(rows), dtype=bool), False)
        paired = results(rows, pred, matched, True)
    else:
        all_scored = paired = results([], {}, [], False)
        matched = np.zeros(0, dtype=bool)
    grade = "insufficient_training" if not spec else "descriptive_only"
    if spec and paired["groups"] >= 4 and paired["scored_examples"] >= 20:
        cmp = paired["paired_differences"]
        required = [
            "constant_velocity",
            "persistence",
            "prior_net",
            "context",
            "context_words",
            "motion",
            "motion_context",
            "ridge_removed",
            "ridge_substituted",
        ]
        better = all(
            cmp[f"{k}_minus_motion_context_words"]["gain_cm"] > 0 for k in required
        )
        stable = all(
            cmp[f"{k}_minus_motion_context_words"]["interval_cm"][0] > 0
            for k in ["motion_context", "ridge_removed", "ridge_substituted"]
        )
        grade = (
            "exploratory_increment_supported"
            if better and stable
            else "language_increment_not_demonstrated"
        )
    retained = set(spec.get("vocabulary", []))
    write(
        out / "assessment.json",
        {
            "inputs": binding(root),
            "fit_sha256": sha(out / "fit.json"),
            "coverage": summary,
            "all_scorable": all_scored,
            "same_task_donor_matched": paired,
            "missing_donor": int(len(rows) - matched.sum()),
            "rows_with_retained_words": sum(
                bool(retained & set(r["tokens"])) for r in rows
            ),
            "confidence_status_counts": dict(Counter(r["confidence"] for r in rows)),
            "conclusion": grade,
        },
    )
    print(
        json.dumps(
            {"scorable": len(rows), "matched": int(matched.sum()), "grade": grade}
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["fit", "assess"])
    p.add_argument("--workspace", type=Path, default=HERE.parent)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    (fit_stage if a.stage == "fit" else assess_stage)(a.workspace, a.output)
