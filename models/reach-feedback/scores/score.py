#!/usr/bin/env python3
"""Score frozen reach predictions. The two test workspaces share one release."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from metrics import (BOOT_SEED, BLOCK_LENGTH, N_BOOT, PARTS, RATE_FLOOR, SEEDS, balanced,
                     bootstrap_draws, count_errors, difference, donors, motion_errors, need,
                     ordinal_controls, positions, reduce_seeds)

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
import sys
sys.path.insert(0, str(BASE))
ROW_KEYS = ("block", "original", "ordinal", "k", "fold")
MOTOR = ("full", "pose_cue", "spike_cue", "spikes_only", "cue_only")
COUNT = ("direct", "full", "predicted_only", "spikes_only", "cue_only", "pose_cue", "privileged", "wrong")
CONTROL = ("train_mean", "ordinal_mean", "persistence")
POPULATIONS = ("all", "matched", "ordinal_2", "ordinal_3", "ordinal_4", "early", "late")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read_npz(path):
    with np.load(path, allow_pickle=False) as src:
        return {k: src[k] for k in src.files}


def read_json(path):
    return json.loads(path.read_text())


def check_source(d, split):
    n = len(d["original"])
    b = len(d["roster_original"])
    need(all(d[k].shape == (n,) for k in (*ROW_KEYS, "donor", "workspace")), "row key mismatch")
    need(all(d[k].shape == (b,) for k in ("roster_block", "roster_start", "roster_end", "roster_fold")), "roster shape")
    roster = list(zip(d["roster_block"].tolist(), d["roster_original"].tolist()))
    pos = positions(d, roster)
    need(np.all(np.diff(pos) >= 0) and np.all(np.diff(d["k"])[np.diff(d["block"]) == 0] > 0), "nonchronological windows")
    for block in np.unique(d["roster_block"]):
        need(np.all(np.diff(d["roster_start"][d["roster_block"] == block]) > 0), "nonchronological roster")
    need(np.isin(d["ordinal"], (2, 3, 4)).all(), "unexpected go ordinal")
    expected_ws = 2 if split == "transfer" else 1
    need((d["workspace"] == expected_ws).all(), "wrong workspace")
    need(np.array_equal(d["fold"], d["roster_fold"][pos]), "fold != original's fold")
    if split == "train":
        need(np.isin(d["roster_fold"], np.arange(5)).all(), "unknown train fold")
    else:
        need((d["fold"] == -1).all(), "held fold mismatch")
    need(d["unit_guide"].shape == (23, 2) and (d["unit_guide"][:, 1] > 0).all() and
         len(set(map(tuple, d["unit_guide"]))) == 23, "invalid sorted unit identities")
    for name, shape in {"pose": (20, 8), "movement": (10, 8), "cue": (20, 3),
                        "delayed": (10, 23), "spikes": (20, 23), "concurrent": (10, 23)}.items():
        need(d[name].shape == (n, *shape) and np.isfinite(d[name]).all(), "invalid " + name)
        if name in ("delayed", "spikes", "concurrent"):
            need((d[name] >= 0).all() and (d[name] == np.floor(d[name])).all(), "invalid counts " + name)
    for name, offsets in {"history_rows": np.arange(-20, 0), "movement_rows": np.arange(10),
                          "delayed_rows": np.arange(10, 20)}.items():
        need(np.array_equal(d[name], d["k"][:, None] + offsets), "native timing " + name)
    need(np.array_equal(donors(d["block"], pos, d["ordinal"]), d["donor"]), "source donor mismatch")
    return pos


def check_ids(p, d, mask, guide=False):
    for key in ROW_KEYS:
        need(np.array_equal(p[key], d[key][mask]), "prediction row mismatch " + key)
    need(np.array_equal(p["seeds"], SEEDS), "seed identity/order mismatch")
    if guide:
        need(np.array_equal(p["unit_guide"], d["unit_guide"]), "sorted-unit order mismatch")


def check_oof(oof, d):
    check_ids(oof, d, slice(None))
    supported = d["fold"] > 0
    need(np.array_equal(supported, oof["supported"]), "warmup support mismatch")
    n = len(supported)
    for key, exp_shape in (("full", (3, n, 10, 8)), ("ridge_full", (n, 10, 8))):
        value = oof[key]
        need(value.shape == exp_shape, "OOF dimensions")
        v = value[None] if key == "ridge_full" else value
        need(np.isnan(v[:, ~supported]).all() and np.isfinite(v[:, supported]).all(),
             "OOF warmup/forecast support differs")
    return supported


def subgroups(ordinals, pos, n_original, matched):
    return {"all": np.ones(len(pos), bool), "matched": matched, "early": pos < (n_original + 1) // 2,
            "late": pos >= (n_original + 1) // 2, **{"ordinal_" + str(o): ordinals == o for o in (2, 3, 4)}}


def count_coverage(d, selected):
    y = d["delayed"][selected]
    sums = y.sum(axis=1)
    return {"windows": len(y), "bin_unit_observations": y.size, "zero_bin_unit_observations": int((y == 0).sum()),
            "zero_window_unit_totals": int((sums == 0).sum()), "sorted_unit_total_counts": sums.sum(axis=0).tolist(),
            "zero_window_totals_by_unit": (sums == 0).sum(axis=0).tolist(),
            "positive_windows_by_unit": (sums > 0).sum(axis=0).tolist(),
            "variance_of_window_totals_by_unit_unweighted": sums.var(axis=0).tolist() if len(y) else None,
            "concurrent_counts_by_unit_descriptive": d["concurrent"][selected].sum(axis=(0, 1)).tolist()}


def clean_qc(qc):
    keys = ("roster","candidates","eligible","metadata_eligible_originals","numeric_eligible_originals",
            "ordinal_before_qc","ordinal_after_qc","qc_reasons_may_overlap")
    return {k: qc[k] for k in keys}


def zero_rates(y, forecast):
    # Raw counts of zero forecasts, independent of the scoring floor.
    z = forecast == 0
    observed = y > 0
    zt = forecast.sum(axis=1) == 0
    return {"zero_forecasts": int(z.sum()), "positive_observations_at_zero_forecast": int((observed & z).sum()),
            "zero_total_forecasts": int(zt.sum()),
            "positive_totals_at_zero_total_forecast": int(((y.sum(axis=1) > 0) & zt).sum()),
            "positive_at_zero_forecast_by_unit": (observed & z).sum(axis=(0, 1)).tolist()}


def motion_section(source, train, motor, pos, train_pos, groups):
    actual = source["movement"]
    n = len(actual)
    _, ordinal_mean = ordinal_controls(train["movement"], train_pos, train["ordinal"], source["ordinal"])
    last_vel = source["pose"][:, -1] - source["pose"][:, -2]
    predictions = {m: motor[m] for m in MOTOR}
    predictions.update({"ridge_" + m: motor["ridge_" + m][None] for m in MOTOR})
    predictions.update({"stationary": np.zeros_like(actual)[None],
                        "backward_velocity": (last_vel[:, None] * np.arange(1, 11)[None, :, None])[None],
                        "ordinal_mean": ordinal_mean[None]})
    stats = {g: {} for g in groups}
    primary_losses = {}
    for name, forecasts in predictions.items():
        multi = name in MOTOR
        labels = SEEDS if multi else ("fixed",)
        need(forecasts.shape == (len(labels), n, 10, 8), "motor dimensions " + name)
        metrics = [motion_errors(actual, f) for f in forecasts]
        primary_losses[name] = {part: np.stack([m[part]["endpoint"] for m in metrics]) for part in PARTS}
        for g, mask in groups.items():
            stats[g][name] = reduce_seeds(metrics, pos, mask, labels)
    return stats, primary_losses


def count_section(s, c, train, pos, train_pos, eligible, groups):
    # Train-only controls exclude the entire warmup, matching all count heads.
    trained = train["fold"] > 0
    glob, cond = ordinal_controls(train["delayed"][trained], train_pos[trained], train["ordinal"][trained], s["ordinal"][eligible])
    past = s["spikes"][eligible, -10:].mean(axis=1)
    naive = {"train_mean": glob, "ordinal_mean": cond, "persistence": np.broadcast_to(past[:, None], glob.shape)}
    for name, expect in naive.items():
        need(np.allclose(c[name], expect, atol=1e-6, rtol=1e-6), "training or persistence control mismatch: " + name)
    y = s["delayed"][eligible]
    stats = {g: {} for g in groups}
    losses, by_unit = {}, {}
    for name in (*COUNT, *("glm_" + a for a in COUNT), *CONTROL):
        multi = name in COUNT
        labels = SEEDS if multi else ("fixed",)
        forecast = c[name] if multi else c[name][None]
        need(forecast.shape == (len(labels), *y.shape), "count dimensions " + name)
        valid = groups["matched"] if name in ("wrong", "glm_wrong") else groups["all"]
        need(np.isnan(forecast[:, ~valid]).all(), "wrong forecast outside donor support")
        forecast = forecast[:, valid].astype(np.float64, copy=False)
        if name not in CONTROL:
            need((forecast > 0).all(), "trained expected counts must be positive")
        metrics = [count_errors(y[valid], f) for f in forecast]
        unit_losses = np.full((len(labels), len(y)), np.nan)
        unit_losses[:, valid] = [m["total_deviance"] for m in metrics]
        losses[name] = unit_losses
        if name in ("full", "direct", "wrong"):
            units = np.full((len(labels), len(y), 23), np.nan)
            units[:, valid] = [m["total_deviance_by_unit"] for m in metrics]
            by_unit[name] = units
        for group, mask in groups.items():
            active = mask[valid]
            stats[group][name] = reduce_seeds(metrics, pos[valid], active, labels)
            if name in CONTROL:
                stats[group][name]["raw_zero_predictions"] = zero_rates(y[valid][active], forecast[0, active])
    return stats, losses, by_unit


def paired_results(motor, count, unit_losses, mpos, cpos, blocks, mg, cg):
    weights = {"moving_block_95": bootstrap_draws(blocks, True), "iid_95": bootstrap_draws(blocks, False)}

    def paired(a, b, positions_, mask):
        labels = SEEDS if max(a.shape[0], b.shape[0]) > 1 else ("fixed",)
        return difference(a[:, mask], b[:, mask], positions_[mask], blocks, weights, labels)

    motions = {part: paired(motor["full"][part], motor["pose_cue"][part], mpos, mg["all"]) for part in PARTS}
    counts = {f"full_minus_{op}": paired(count["full"], count[op], cpos, cg["matched"]) for op in ("direct", "wrong")}
    by_group = {}
    for group in POPULATIONS:
        m, common = mg[group], cg[group] & cg["matched"]
        by_group[group] = {
            "motor_full_minus_pose_cue": {p: paired(motor["full"][p], motor["pose_cue"][p], mpos, m) for p in PARTS},
            "count_common": {"full_minus_" + op: paired(count["full"], count[op], cpos, common) for op in ("direct","wrong")},
        }
    rivals = {}
    for op, baseline in count.items():
        mask = cg["matched"] if op.endswith("wrong") else cg["all"]
        if op not in ("full", "privileged", "glm_privileged"):
            rivals["full_minus_" + op] = paired(count["full"], baseline, cpos, mask)
    return motions, counts, by_group, {
        "genuine_full_against_other_heads_or_controls": rivals,
        "matched_unit_contrasts_native_guide_order": {
            "full_minus_" + op: [paired(unit_losses["full"][:, :, unit], unit_losses[op][:, :, unit], cpos, cg["matched"]) for unit in range(23)]
            for op in ("direct", "wrong")},
        "privileged_minus_direct_descriptive": paired(count["privileged"], count["direct"], cpos, cg["all"]),
        "glm_privileged_minus_direct_descriptive": paired(count["glm_privileged"], count["glm_direct"], cpos, cg["all"]),
        "glm_full_minus_direct_matched": paired(count["glm_full"], count["glm_direct"], cpos, cg["matched"]),
        "glm_full_minus_wrong_matched": paired(count["glm_full"], count["glm_wrong"], cpos, cg["matched"]),
    }


def gate(relevant, comparisons):
    if not relevant:
        return {"status": "not_applicable"}
    ci = [d["mean"]["moving_block_95"] for d in comparisons]
    if any(x is None for x in ci):
        return {"status": "insufficient_support", "pass": False}
    return {"status": "evaluated", "pass": all(x[1] < 0 for x in ci)}


def analyze(split, src, train, m, c, oof, qc):
    pos = check_source(src, split)
    tpos = check_source(train, "train")
    check_ids(m, src, slice(None))
    trained = check_oof(oof, train)
    support = trained if split == "train" else np.ones(len(pos), bool)
    check_ids(c, src, support, guide=True)
    need(np.array_equal(src["unit_guide"], train["unit_guide"]), "unit mapping changed")
    need(qc["eligible"] == len(pos) and qc["roster"] == len(src["roster_block"]), "source QC denominator mismatch")
    cp = pos[support]
    blocks = src["roster_block"]
    donor = donors(src["block"][support], cp, src["ordinal"][support])
    need(np.array_equal(donor, c["donor"]), "count head donor index mismatch")
    cg = subgroups(src["ordinal"][support], cp, len(blocks), donor >= 0)
    mg = subgroups(src["ordinal"], pos, len(blocks), src["donor"] >= 0)
    mstats, mloss = motion_section(src, train, m, pos, tpos, mg)
    if split == "train":
        mstats["forward_oof"] = {}
        for arm, values in (("full", oof["full"]), ("ridge_full", oof["ridge_full"][None])):
            labels = SEEDS if arm == "full" else ("fixed",)
            ms = [motion_errors(src["movement"][trained], pred[trained]) for pred in values]
            mstats["forward_oof"][arm] = reduce_seeds(ms, tpos[trained], np.ones(int(trained.sum()), bool), labels)
    cstats, closs, unit_losses = count_section(src, c, train, cp, tpos, support, cg)
    mot, cnt, bygroup, other = paired_results(mloss, closs, unit_losses, pos, cp, blocks, mg, cg)
    actual_motion = motion_errors(src["movement"], np.zeros_like(src["movement"]))
    observed = {g: reduce_seeds([actual_motion], pos, select, ["fixed"])["mean"] for g, select in mg.items()}
    # Here endpoint-distance is displacement magnitude. Explicit signs of observed displacement:
    for val in observed.values():
        for part, obj in val.items():
            key = "signed_endpoint_xy" if part == "handle" else "signed_endpoint_xyz"
            if obj[key] is not None:
                obj[key] = (-np.asarray(obj[key])).tolist()
    qc_data = {"source": clean_qc(qc), "count_roster_originals": len(blocks), "count_supported_windows": int(support.sum()),
               "count_supported_originals": len(np.unique(cp)), "count_matched_windows": int((donor >= 0).sum()),
               "count_matched_originals": len(np.unique(cp[donor >= 0])), "donor_unavailable_windows": int((donor < 0).sum()),
               "count_warmup_windows_excluded": int((~support).sum()), "unit_guide": src["unit_guide"].tolist(),
               "tracking": "Finite released coordinates required throughout all windows. Original camera visibility and interpolation masks are unavailable.",
               "unseen_train_ordinal_fallback_motor": int((~np.isin(src["ordinal"], train["ordinal"])).sum()),
               "unseen_train_ordinal_fallback_counts": int((~np.isin(src["ordinal"][support], train["ordinal"][trained])).sum()),
               "observed_movement": observed, "counts": {}}
    idx = np.flatnonzero(support)
    for g, mask in cg.items():
        qc_data["counts"][g] = count_coverage(src, idx[mask])
    return {"schema": 1, "split": split, "coverage": qc_data, "motor": mstats, "counts": cstats,
            "primary": {"motor": mot, "count": cnt,
                        "motor_gate": gate(split == "transfer", [mot["hand"], mot["elbow"]]),
                        "count_gate": gate(split in ("within", "transfer"), list(cnt.values()))},
            "subgroup_contrasts": bygroup, "secondary": other,
            "units": {"hand":"mm","elbow":"mm","handle":"cm","total_deviance":"Poisson deviance per sorted unit per 100 ms",
                      "bin_deviance":"Poisson deviance per sorted unit per 10 ms", "axes":"source XYZ for optical markers; source XY for encoder",
                      "mean":"original-balanced after window losses, then equal-seed mean of losses"},
            "bootstrap": {"draws":N_BOOT, "seed":BOOT_SEED, "primary_non_circular_length":BLOCK_LENGTH,
                          "quantiles":[.025,.975], "iid":"sensitivity; equal whole original resampling",
                          "empty_roster_positions":"sampled and contribute no paired loss","expected_count_floor":RATE_FLOOR},
            "forecast_scope": {"privileged":"measured future motion is descriptive only", "train":"motor all-train refit; count fit diagnostics from forward OOF motor features",
                               "other":"fixed train-only refit; direct and augmented heads on identical warmup-excluded originals"}}


def run(stage, output):
    from freeze import verify_stage
    verify_stage(BASE, stage)
    source, motor, cortex = (BASE / n for n in ("source", "motor", "cortex"))
    splits = [stage] if stage != "test" else ["within", "transfer"]
    train_path, oof_path = source / "train.npz", motor / "oof.npz"
    train, oof = read_npz(train_path), read_npz(oof_path)
    all_results = {}
    for split in splits:
        paths = (source / (split + ".npz"), motor / (split + "-predictions.npz"), cortex / (split + "-predictions.npz"))
        qc_path = source / (split + "-qc.json")
        d = train if split == "train" else read_npz(paths[0])
        qc = read_json(qc_path)
        need(qc["npz_sha256"] == sha(paths[0]), "source QC fingerprint mismatch")
        result = analyze(split, d, train, read_npz(paths[1]), read_npz(paths[2]), oof, qc)
        all_results[split] = result
    if stage == "test":
        both = all(x["primary"]["count_gate"]["pass"] for x in all_results.values())
        for result in all_results.values():
            result["primary"]["both_test_count_gates_pass"] = both
    for split, result in all_results.items():
        folder = output / split
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / "summary.json.tmp"
        tmp.write_text(json.dumps(result, allow_nan=False, separators=(",", ":")) + "\n")
        tmp.replace(folder / "summary.json")
        print(split, json.dumps({k:v for k,v in result["primary"].items() if "gate" in k}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("train", "validation", "test"))
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    run(args.stage, args.output)
