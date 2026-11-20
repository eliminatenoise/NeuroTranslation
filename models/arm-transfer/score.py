"""Evaluate a fixed model. Forecast errors are paired on identical eligible trials."""

import numpy as np
from predict import CUE_METHODS, CUES, METHODS, batch

PRIMARY = ("still", "cue", "ridge", "mlp", "transformer_no_cue", "transformer_wrong")
DOMAINS = {
    "cue_contribution": ("transformer_no_cue", "transformer_wrong"),
    "attention_architecture": ("ridge", "mlp"),
    "net_benefit": ("cue", "still"),
}


def average(values):
    return np.mean(values, axis=0)


def person_results(model, x, y, g):
    errors = {m: np.abs(batch(model, x, g[:, 2], m) - y) for m in METHODS}
    for m in CUE_METHODS:
        errors[m + "_wrong"] = average(
            [np.abs(batch(model, x, (g[:, 2] + i) % 7, m) - y) for i in range(1, 7)]
        )
    s = model["scales"]
    target_sd = np.asarray(s["target_sd"]).reshape(3, 3)
    pooled = not any(s["constant_targets"])
    outside = np.any((x < s["raw_min"]) | (x > s["raw_max"]), axis=(1, 2))
    out = []
    for person in np.unique(g[:, 0]):
        mask = g[:, 0] == person
        runs = np.unique(g[mask, 1])
        result = {
            "person": int(person),
            "runs": runs.tolist(),
            "n": int(mask.sum()),
            "outside_fit_range": int(outside[mask].sum()),
            "methods": {},
        }
        result["counts_by_run_and_cue"] = {
            str(run): np.bincount(g[mask & (g[:, 1] == run), 2], minlength=7).tolist()
            for run in runs
        }
        result["complete_cue_and_run_support"] = list(runs) == [1, 2, 3] and all(
            min(counts) > 0 for counts in result["counts_by_run_and_cue"].values()
        )
        for m, err in errors.items():
            cube = {
                (int(run), i): average(err[r])
                for run in runs
                for i in range(7)
                if np.any(r := mask & (g[:, 1] == run) & (g[:, 2] == i))
            }
            native = average(
                [average([v for (r, c), v in cube.items() if r == run]) for run in runs]
            )

            def measures(val):
                return {
                    "score": float((val / target_sd).mean()) if pooled else None,
                    "native_mae": val.tolist(),
                }

            d = measures(native)
            by_cue = {}
            for i, cue in enumerate(CUES):
                vals = [v for (r, c), v in cube.items() if c == i]
                if vals:
                    by_cue[cue] = {
                        **measures(average(vals)),
                        "n": int((mask & (g[:, 2] == i)).sum()),
                    }
            d["by_cue"] = by_cue
            result["methods"][m] = d
        out.append(result)
    return out


def summary(people, expected):
    methods = list(people[0]["methods"])
    complete = sorted(p["person"] for p in people) == list(expected) and all(
        p["complete_cue_and_run_support"] for p in people
    )
    out = {"complete_people_cues_runs": complete, "methods": {}, "contrasts": {}}
    eligible_scores = all(
        p["methods"]["transformer"]["score"] is not None for p in people
    )
    for m in methods:
        vals = [p["methods"][m] for p in people]
        score = float(average([v["score"] for v in vals])) if eligible_scores else None
        out["methods"][m] = {
            "score": score,
            "native_mae": average([v["native_mae"] for v in vals]).tolist(),
        }
    n = len(people)
    draws = np.random.default_rng(71293).integers(n, size=(10000, n))
    pairs = [("transformer", m) for m in PRIMARY]
    pairs.extend(
        [
            (m, baseline)
            for m in CUE_METHODS
            if m != "transformer"
            for baseline in (
                ("unconditional" if m == "cue" else m + "_no_cue"),
                m + "_wrong",
            )
        ]
    )
    for model, baseline in pairs:
        key = model + "_vs_" + baseline
        if not eligible_scores:
            out["contrasts"][key] = {"defined": False, "pass": False}
            continue
        reference = np.array([p["methods"][baseline]["score"] for p in people])
        delta = np.array([p["methods"][model]["score"] for p in people]) - reference
        relative = (
            float(delta.mean() / reference.mean()) if reference.mean() > 1e-12 else None
        )
        out["contrasts"][key] = {
            "defined": True,
            "mean_difference": float(delta.mean()),
            "differences_in_people_order": delta.tolist(),
            "relative_change": relative,
            "paired_percentile_95": np.percentile(
                delta[draws].mean(axis=1), [2.5, 97.5]
            ).tolist(),
            "people_with_lower_error": int((delta < 0).sum()),
            "pass": bool(
                complete
                and relative is not None
                and relative <= -0.05
                and np.all(delta < 0)
            ),
        }
    out["criteria"] = {
        k: all(out["contrasts"]["transformer_vs_" + v]["pass"] for v in vv)
        for k, vv in DOMAINS.items()
    }
    out["overall_advantage"] = all(out["criteria"].values())
    return out
