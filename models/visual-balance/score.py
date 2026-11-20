"""Participant-level endpoint errors, direction and donor sensitivities."""
import numpy as np

SEEDS = (None, 258, 1173)


def donor_indices(d, seed=None):
    n = len(d["person"])
    out = np.full(n, -1, int)
    rng = np.random.default_rng(seed) if seed is not None else None
    stats = {"rows": n, "singleton_rows": 0, "overlapping_pairs": 0, "separation_200_to_207": 0}
    strata = sorted(set(zip(d["person"], d["direction"], d["block"])))
    for p, direction, part in strata:
        rows = np.flatnonzero((d["person"] == p) & (d["direction"] == direction) & (d["block"] == part))
        if len(rows) < 2:
            stats["singleton_rows"] += len(rows)
            continue
        rows = rows[np.lexsort((d["event"][rows], d["cutoff"][rows]))]
        if rng is not None:
            rows = rng.permutation(rows)
        donor = np.roll(rows, -1)
        distance = np.abs(d["cutoff"][rows].astype(np.int64) - d["cutoff"][donor])
        good = distance > 207
        out[rows[good]] = donor[good]
        stats["overlapping_pairs"] += int((~good).sum())
        stats["separation_200_to_207"] += int(((distance >= 200) & (distance <= 207)).sum())
    stats["supported_rows"] = int((out >= 0).sum())
    return out, stats


def marker_err(delta):
    return np.linalg.norm(delta, axis=-1)


def paired_report(d, preds, support, *, both_directions=True):
    directions = d["direction"]
    valid_people = sorted(set(d["person"][support]))
    if both_directions:
        valid_people = [p for p in valid_people if len(set(directions[support & (d["person"] == p)])) == 2]
    support = support & np.isin(d["person"], valid_people)
    n = len(valid_people)
    rows = int(support.sum())
    if not rows:
        return {"rows": 0, "people": 0, "methods": {}, "comparisons": {}, "joint_pass": False,
                "marker_pass": [False, False]}
    groups = [np.flatnonzero(support & (d["person"] == p)) for p in valid_people]
    base = {"rows": rows, "people": n, "training_people_in_score": 0,
            "direction_rows": {str(q): int(np.sum(support & (directions == q))) for q in (-1, 1)},
            "methods": {}, "comparisons": {}}
    errors = {}
    for mode, prediction in preds.items():
        delta = prediction - d["future_delta_mm"]
        err = marker_err(delta)
        if not np.isfinite(err[support]).all():
            raise ArithmeticError("Missing prediction on matched support")
        per_person = np.stack([err[ix].mean(0) for ix in groups])
        errors[mode] = per_person
        by_direction = {}
        for q in (-1, 1):
            parts = [ix[directions[ix] == q] for ix in groups]
            arr = [err[ix].mean(0) for ix in parts if len(ix)]
            by_direction[str(q)] = {"people": len(arr), "marker_error_mm":
                                    np.mean(arr, 0).tolist() if arr else None}
        base["methods"][mode] = {"marker_error_mm": per_person.mean(0).tolist(),
                                 "bias_xyz_mm": np.mean([delta[ix].mean(0) for ix in groups], 0).tolist(),
                                 "by_direction": by_direction}
    rng = np.random.default_rng(2701)
    boot = rng.integers(n, size=(5000, n))
    for mode in sorted(set(errors) - {"full"}):
        diff = errors["full"] - errors[mode]
        draw = diff[boot].mean(1)
        base["comparisons"][mode] = {"mean_mm": diff.mean(0).tolist(),
            "ci95_mm": np.percentile(draw, [2.5, 97.5], axis=0).T.tolist() if n >= 2 else None,
            "upper_9875_mm": np.percentile(draw, 98.75, axis=0).tolist() if n >= 2 else None,
            "people_full_better": (diff < 0).sum(0).astype(int).tolist()}
    passed = np.zeros(2, bool)
    if n >= 2 and {"wrong", "no_scalp"} <= errors.keys():
        passed = np.all([np.asarray(base["comparisons"][m]["upper_9875_mm"]) < 0
                         for m in ("no_scalp", "wrong")], axis=0)
    base["marker_pass"] = passed.tolist()
    base["joint_pass"] = bool(passed.all())
    return base


def report(d, predictions, donors):
    n = len(d["person"])
    base = {m: predictions[m] for m in ("full", "no_scalp")}
    result = {"marker_order": ["sacrum", "head"], "axis_order": ["ML", "SI", "AP"],
              "units": "mm", "input_rows": n, "input_people": len(set(d["person"])),
              "difference": "full minus comparator; negative favors full",
              "all_rows": paired_report(d, base, np.ones(n, bool), both_directions=False),
              "alternate_donors": {}}
    for seed in SEEDS:
        label = "primary" if seed is None else str(seed)
        ids, counts = donors[label]
        methods = {**base, "wrong": predictions["wrong_" + label]}
        supported = ids >= 0
        sub = paired_report(d, methods, supported)
        sub["donors"] = counts
        if seed is None:
            result["primary"] = sub
            adjacency = d.get("adjacent_to_excluded")
            if adjacency is not None:
                result["tracking_sensitivity"] = {
                    k: paired_report(d, methods, supported & flag, both_directions=False)
                    for k, flag in (("adjacent", adjacency), ("other", ~adjacency))}
            else:
                result["tracking_sensitivity"] = {"available": False}
        else:
            result["alternate_donors"][label] = sub
    return result
