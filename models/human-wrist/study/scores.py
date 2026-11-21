"""Absolute and paired camera-pixel errors on matching events and time strata."""

from itertools import product
import numpy as np

SEEDS = (17, 37, 73)
SIDES = ("right", "left")
HORIZONS = (8, 15)
TREATMENTS = ("direct", "bounded_zero", "anchored")


def dist(forecast, target):
    return np.linalg.norm(forecast - target, axis=-1)


def average(a):
    return float(np.mean(a)) if len(a) else None


def pairs(diff, valid, group):
    hours = {}
    leave = {}
    for s in range(6):
        inside = valid & (group == s)
        outside = valid & (group != s)
        hours[str(s)] = {"n": int(inside.sum()), "mean_delta_px": average(diff[inside])}
        leave[str(s)] = {"n": int(outside.sum()), "mean_delta_px": average(diff[outside])}
    x = diff[valid]
    occupied = [v["mean_delta_px"] for v in hours.values() if v["n"]]
    return {
        "n": len(x),
        "mean_delta_px": average(x),
        "equal_occupied_stratum_delta_px": average(occupied),
        "wins": int((x < -1e-9).sum()),
        "ties": int((abs(x) <= 1e-9).sum()),
        "losses": int((x > 1e-9).sum()),
        "four_hour_strata": hours,
        "omit_one_stratum": leave,
    }


def tiered(a, b, group, common=None):
    d = a - b
    finite = np.isfinite(d)
    if common is not None:
        finite &= common
    return {
        side: {str(h): pairs(d[:, j, k], finite[:, j, k], group) for j, h in enumerate(HORIZONS)}
        for k, side in enumerate(SIDES)
    }


def stats(e, resid, mask):
    vals = e[mask]
    vec = resid[mask]
    return {
        "n": len(vals),
        "mean_px": average(vals),
        "median_px": float(np.median(vals)) if len(vals) else None,
        "axis_rmse_px": np.sqrt(np.mean(vec**2, 0)).tolist() if len(vals) else [None, None],
    }


def mean_rows(e, resid, mask):
    return {
        side: {
            str(h): stats(e[:, j, k], resid[:, j, k], mask[:, j, k]) for j, h in enumerate(HORIZONS)
        }
        for k, side in enumerate(SIDES)
    }


def report(data, target, group):
    errs = {k: dist(v, target) for k, v in data.items()}
    absolute = {}
    for name, x in data.items():
        e = errs[name]
        ok = np.isfinite(e)
        absolute[name] = mean_rows(e, x - target, ok)
    comparisons = {}
    primary = {}
    sensitivity = {}
    four_heads = {}

    def compare(arm, control, mask=None):
        return tiered(errs[arm], errs[control], group, mask)

    def new_pair(arm, control):
        comparisons[arm + "__minus__" + control] = compare(arm, control)

    for t, seed in product(TREATMENTS, SEEDS):
        a = f"transformer_{t}_full_s{seed}"
        p = f"transformer_{t}_pose_s{seed}"
        w = a + "_wrong"
        shared = np.isfinite(errs[a]) & np.isfinite(errs[p]) & np.isfinite(errs[w])
        for arm in (a, p):
            for ref in (
                "velocity",
                "geo_velocity",
                "zero",
                "fitted_velocity",
                f"ridge_{t}_" + ("full" if arm == a else "pose"),
            ):
                new_pair(arm, ref)
        for ref in (p, w):
            new_pair(a, ref)
            if t == "anchored":
                primary[a + "__minus__" + ref] = compare(a, ref, shared)
                both = np.repeat(shared.all(axis=2)[:, :, None], 2, axis=2)
                sensitivity[a + "__minus__" + ref] = compare(a, ref, both)
                complete = shared.all(axis=(1, 2))[:, None, None]
                four_heads[a + "__minus__" + ref] = compare(
                    a, ref, np.broadcast_to(complete, shared.shape)
                )
        if t != "direct":
            for mod in ("full", "pose"):
                new_pair(f"transformer_{t}_{mod}_s{seed}", f"transformer_direct_{mod}_s{seed}")
        if t == "anchored":
            new_pair(a, f"transformer_bounded_zero_full_s{seed}")
        for mod in ("full", "pose"):
            v = f"transformer_{t}_{mod}_s{seed}"
            new_pair(v, "small16_" + v)
            if t == "direct":
                old = f"legacy_{'combined' if mod == 'full' else 'pose'}_direct_{seed}"
                new_pair(v, old)
                new_pair("small16_" + v, old)
    for t in TREATMENTS:
        a = f"ridge_{t}_full"
        p = f"ridge_{t}_pose"
        for ref in (p, a + "_wrong", "velocity", "fitted_velocity"):
            new_pair(a, ref)
    for ref in ("geo_velocity", "geo_whole_shared", "geo_segments_by_side", "geo_zero"):
        new_pair("geo_segments_shared", ref)
    for ref in ("velocity", "fitted_velocity", "ridge_anchored_full", "geo_segments_shared"):
        for seed in SEEDS:
            new_pair(f"transformer_anchored_full_s{seed}", ref)
    # Complete paired support for the three new principal arms.
    principal = {}
    for side in SIDES:
        entries = [v[side][str(h)] for v in primary.values() for h in HORIZONS]
        defined = all(x["n"] > 0 for x in entries)
        principal[side] = {
            "defined": defined,
            "lower_against_both_controls_all_seeds_and_horizons": all(
                x["mean_delta_px"] < 0 for x in entries
            )
            if defined
            else None,
        }
    geo = {}
    for side in SIDES:
        values = [
            comparisons["geo_segments_shared__minus__" + r][side][str(h)]["mean_delta_px"]
            for h in HORIZONS
            for r in ("geo_velocity", "geo_whole_shared")
        ]
        geo[side] = all(v < 0 for v in values) if all(v is not None for v in values) else None
    return {
        "absolute": absolute,
        "pairs": comparisons,
        "primary_common": primary,
        "all_bilateral_common": sensitivity,
        "all_four_heads_common": four_heads,
        "primary": principal,
        "geometric_secondary": geo,
    }
