"""Recompute the D-arm orders from the published rule and compare them with D-ARM-ORDERS.json.

  python check_d_arm_orders.py [--dir FOLDER] [--out RESULT.json]

FOLDER (default: the folder above this one) holds ALLOCATION.json, MIXTURE-MANIFEST.json and D-ARM-ORDERS.json.
This check shares no code with build_manifest.py: it uses the standard library only and reads the rule's
inputs itself. It checks that

  1. ALLOCATION.json has the digest that D-ARM-ORDERS.json records;
  2. the candidates are the wave-1 sources of ALLOCATION.json plus the conditional sources that the manifest
     lists as qualified, and nothing else;
  3. each of the nine orders is the candidates sorted by ascending sha256 of
     'pooled-encoder-0.2|D|k<k>|draw<draw>|<dataset>';
  4. each order, with the conditional sources taken out, is the order ALLOCATION.json publishes;
  5. W_max is the smallest inner-training window count of the Q anchors rounded down to a power of 2, and the
     eligible sources are the qualified ones with at least W_max/8 inner-training windows (counts from the
     manifest's dataset entries);
  6. each arm lists the first k eligible sources of its order, and D_all lists every eligible source;
  7. the manifest's own copy of the orders and arms equals the file.

Prints one line of JSON and exits non-zero if any check fails. No recording value is read.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SALT = "pooled-encoder-0.2"
CONDITIONAL = ("area2", "falcon_m1")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pow2_floor(x):
    p = 1
    while p * 2 <= x:
        p *= 2
    return p if x >= 1 else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out")
    a = ap.parse_args()
    d = Path(a.dir)
    alloc = json.loads((d / "ALLOCATION.json").read_text())
    man = json.loads((d / "MIXTURE-MANIFEST.json").read_text())
    rec = json.loads((d / "D-ARM-ORDERS.json").read_text())
    pub = alloc["quantity_diversity"]
    published = pub["d_arms"]["orders"]
    wave1 = sorted(next(iter(published.values())))
    qualified = {k: v for k, v in man["datasets"].items() if v.get("qualified")}
    admitted = [c for c in CONDITIONAL if c in qualified]
    cands = sorted(set(wave1) | set(admitted))
    wit = {k: v["counts"]["windows_inner_training"] for k, v in qualified.items()}
    w_max = _pow2_floor(min(wit[x] for x in pub["q_anchors"]))
    eligible = sorted(c for c in cands if wit.get(c, 0) >= w_max / 8)

    checks = {
        "allocation_digest": _sha(d / "ALLOCATION.json") == rec["protocol"]["ALLOCATION.json_sha256"],
        "rule_text": rec["rule"] == pub["d_arms"]["rule"] and rec["candidate_note"] == pub["d_candidate_note"],
        "candidates": rec["candidates"] == cands and rec["conditional_sources_admitted"] == admitted,
        "nine_orders": sorted(rec["orders"]) == sorted("k%d|draw%d" % (k, r) for k in (2, 4, 8) for r in (0, 1, 2)),
        "W_max": rec["eligibility"]["W_max"] == w_max == man["quantity_diversity"]["W_max"],
        "eligible": rec["eligibility"]["eligible"] == eligible,
        "window_counts": rec["eligibility"]["inner_training_windows_by_source"] == {c: wit.get(c, 0) for c in cands},
        "D_all": rec["D_all"]["sources"] == eligible,
        "manifest_copy": man["quantity_diversity"]["D_arm_orders"] == rec["orders"]
        and man["quantity_diversity"]["D_arms"] == rec["arms"],
    }
    orders_ok, published_ok, arms_ok, digests_distinct = True, True, True, True
    for k in (2, 4, 8):
        for draw in (0, 1, 2):
            key = "k%d|draw%d" % (k, draw)
            dig = {c: hashlib.sha256(("%s|D|k%d|draw%d|%s" % (SALT, k, draw, c)).encode("utf-8")).hexdigest()
                   for c in cands}
            digests_distinct &= len(set(dig.values())) == len(dig)
            order = sorted(cands, key=lambda c: dig[c])
            orders_ok &= rec["orders"].get(key) == order
            published_ok &= [c for c in order if c in wave1] == published[key]
            first = [c for c in order if c in eligible][:k]
            arm = rec["arms"].get(key, {})
            arms_ok &= arm.get("sources") == first and arm.get("windows_per_source") == w_max // k
            arms_ok &= arm.get("sources_with_fewer_unique_inner_training_windows_than_their_share") == \
                {c: wit[c] for c in first if wit[c] < w_max // k}
    checks.update({"orders_by_the_rule": orders_ok, "digests_distinct": digests_distinct,
                   "wave_1_orders_equal_ALLOCATION_json": published_ok
                   and rec["orders_restricted_to_wave_1_equal_ALLOCATION_json"] is True,
                   "arms_first_k_eligible": arms_ok})
    out = {"check": "d-arm-orders", "candidates": len(cands), "conditional_sources_admitted": admitted,
           "W_max": w_max, "eligible_sources": len(eligible), "checks": checks, "pass": all(checks.values())}
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out))
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
