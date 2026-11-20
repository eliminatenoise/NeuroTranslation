"""Check the published inputs and folds. Put the row-bearing output in private storage."""
import argparse
import json
from pathlib import Path

import numpy as np

from scalp_inputs import NATIVE, SITES, fit_normalizers, load_inputs, require, typed_digest


def count(inp, keep):
    people = inp.keys["person"][keep]
    pairs = zip(people, inp.keys["session"][keep], strict=True)
    return {"events": int(keep.sum()), "participants": len(np.unique(people)),
            "participant_sessions": len(set(pairs))}


def support_table(inp, keep, d):
    result = {"all": count(inp, keep)}
    for kind, names in SITES.items():
        ok = inp.mask[kind]
        result[kind] = {
            "any_site": count(inp, keep & ok.any(1)),
            "observed": {name: count(inp, keep & ok[:, slot]) for slot, name in enumerate(names[d])},
            "patterns": {"".join(map(str, bits.astype(int))):
                         count(inp, keep & np.all(ok == bits, axis=1))
                         for bits in np.unique(ok[keep], axis=0)},
        }
    donor = inp.donor >= 0
    result["wrong"] = count(inp, keep & donor)
    result["unmatched"] = count(inp, keep & ~donor)
    result["common_support_with_prior_central"] = {
        k: count(inp, keep & donor & inp.mask[k].any(1)) for k in SITES}
    return result


def numerical_evidence(inp, fold):
    keys = inp.keys
    n = len(fold)
    require(np.array_equal(np.unique(fold), [0, 1, 2]), "expected three folds")
    expected = np.full(n, -1, dtype=int)
    for d in [0, 1]:
        for rank, person in enumerate(np.unique(keys["person"][keys["domain"] == d])):
            expected[(keys["domain"] == d) & (keys["person"] == person)] = rank % 3
    require(np.array_equal(fold, expected), "fold differs from published participant split")
    paired = np.flatnonzero(inp.donor >= 0)
    donor = inp.donor[paired]
    require(len(np.unique(donor)) == len(donor), "reused donor")
    require(np.all(keys["event"][paired] != keys["event"][donor]), "donor same event")
    for array in [*(keys[k] for k in ("person", "domain", "session", "direction", "block")),
                  inp.source_session, fold, inp.mask["central"]]:
        require(np.array_equal(array[paired], array[donor]), "wrong stratum or masks")
    require(np.all(inp.envelope_end[donor] < inp.envelope_start[paired]), "overlapping envelopes")
    report = {}
    for d, study in enumerate(NATIVE):
        domain = keys["domain"] == d
        rows = paired[domain[paired]]
        gap = inp.envelope_start[rows] - inp.envelope_end[inp.donor[rows]]
        require(np.all(gap > 0), "negative gap")
        rate = (256, 500)[d]
        conditions = {}
        for session, direction in sorted(set(zip(keys["session"][domain], keys["direction"][domain]))):
            take = domain & (keys["session"] == session) & (keys["direction"] == direction)
            conditions[f"series_or_posture={session},direction={direction}"] = support_table(inp, take, d)
        report[study] = {
            "total": support_table(inp, domain, d),
            "source_conditions": conditions,
            "by_fold": {str(f): support_table(inp, domain & (fold == f), d) for f in range(3)},
            "donor_envelope_clock_hz": rate,
            "envelope_ticks_inclusive_relative_to_series_or_session_cutoff": (
                [-314, 64] if d else [-198, 71]),
            "earlier_end_to_later_start_ticks_min_median_max":
                [int(gap.min()), float(np.median(gap)), int(gap.max())],
            "earlier_end_to_later_start_seconds_min": float(gap.min() / rate),
            "same_site_masks_for_every_pair": True, "max_uses_of_one_donor": 1,
        }
    return report


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("cohort", "scalp", "splits", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    inp = load_inputs(args.cohort, args.scalp)
    n = len(inp.donor)
    with np.load(args.splits, allow_pickle=False) as z:
        require(np.array_equal(z["row"], np.arange(n)), "split row identity")
        fold = z["fold"]
    results = numerical_evidence(inp, fold)
    args.out.mkdir(exist_ok=True, parents=True)
    arrays = dict(row=np.arange(n, dtype=np.int64), fold=fold, donor=inp.donor,
                  envelope_start=inp.envelope_start, envelope_end=inp.envelope_end,
                  **{f"{k}_mask": v for k, v in inp.mask.items()})
    np.savez_compressed(args.out / "support.npz", **arrays)
    scales = {str(f): fit_normalizers(inp, np.flatnonzero(fold != f)) for f in range(3)}
    write_json(args.out / "fold-scales.json", scales)
    write_json(args.out / "support-counts.json", results)
    print(json.dumps({"rows": n, "support_typed_sha256": typed_digest(arrays),
                      "matched": {study: results[study]["total"]["wrong"] for study in NATIVE}}))


if __name__ == "__main__":
    main()
