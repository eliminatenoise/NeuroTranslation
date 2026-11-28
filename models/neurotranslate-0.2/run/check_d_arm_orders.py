"""Recompute the D-arm orders and the D arms from the published rules and compare them with D-ARM-ORDERS.json.

  python check_d_arm_orders.py [--dir FOLDER] [--out RESULT.json]

FOLDER (default: the folder above this one) holds ALLOCATION.json, PROTOCOL.json, MIXTURE-MANIFEST.json and
D-ARM-ORDERS.json. This check shares no code with build_manifest.py: it uses the standard library only and
reads the rules' inputs itself. It checks that

  1. ALLOCATION.json and PROTOCOL.json have the digests that D-ARM-ORDERS.json records, and the revision is
     the one PROTOCOL.json states;
  2. the candidates are the wave-1 sources of ALLOCATION.json plus the conditional sources that the manifest
     lists as qualified, and nothing else;
  3. each of the nine orders is the candidates sorted by ascending sha256 of
     'pooled-encoder-0.2|D|k<k>|draw<draw>|<dataset>';
  4. each order, with the conditional sources taken out, is the order ALLOCATION.json publishes;
  5. W_max is the smallest inner-training window count of the Q anchors rounded down to a power of 2, and the
     eligible sources are the qualified ones with at least W_max/8 inner-training windows (counts from the
     manifest's dataset entries);
  6. the arm rule recorded in the file is the text of PROTOCOL.json quantity_diversity.D_arm_rule (protocol
     revision 3): a source enters a k-source arm only if it has at least W_max/k unique inner-training windows;
  7. each arm is what that rule gives: the order is walked from the top, sources below W_max/8 (not eligible)
     and below W_max/k (short for this k) are skipped and recorded with their reason, and the first k that
     remain are the arm; every arm is complete, every source in it has its whole share of W_max/k windows, and
     the arm's unique windows add up to W_max;
  8. D_all lists every eligible source at floor(W_max / n) windows each, with the total and the windows short
     of W_max recorded;
  9. the lists of sources with a whole share at each k, and the arms that differ from the revision 2 rule
     (the first k eligible sources), are as recorded;
 10. the manifest's own copy of the orders, arms and D_all equals the file, and the arms and D_all that
     PROTOCOL.json states as computed values equal the file.

Prints one line of JSON and exits non-zero if any check fails. No recording value is read.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SALT = "pooled-encoder-0.2"
CONDITIONAL = ("area2", "falcon_m1")
KS = (2, 4, 8)
DRAWS = (0, 1, 2)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pow2_floor(x):
    p = 1
    while p * 2 <= x:
        p *= 2
    return p if x >= 1 else 0


def _walk(order, counts, w_max, k):
    """The revision 3 arm rule, written out here from the protocol text (whole-number comparisons)."""
    arm, passed_over = [], []
    for name in order:
        if len(arm) == k:
            break
        n = counts.get(name, 0)
        if 8 * n < w_max:
            passed_over.append((name, n, "not eligible"))
        elif k * n < w_max:
            passed_over.append((name, n, "short for this k"))
        else:
            arm.append(name)
    return arm, passed_over


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out")
    a = ap.parse_args()
    d = Path(a.dir)
    alloc = json.loads((d / "ALLOCATION.json").read_text())
    proto = json.loads((d / "PROTOCOL.json").read_text())
    man = json.loads((d / "MIXTURE-MANIFEST.json").read_text())
    rec = json.loads((d / "D-ARM-ORDERS.json").read_text())
    pub = alloc["quantity_diversity"]
    pq = proto["quantity_diversity"]
    mq = man["quantity_diversity"]
    published = pub["d_arms"]["orders"]
    wave1 = sorted(next(iter(published.values())))
    qualified = {k: v for k, v in man["datasets"].items() if v.get("qualified")}
    admitted = [c for c in CONDITIONAL if c in qualified]
    cands = sorted(set(wave1) | set(admitted))
    wit = {k: v["counts"]["windows_inner_training"] for k, v in qualified.items()}
    w_max = _pow2_floor(min(wit[x] for x in pub["q_anchors"]))
    eligible = sorted(c for c in cands if 8 * wit.get(c, 0) >= w_max)
    keys = ["k%d|draw%d" % (k, r) for k in KS for r in DRAWS]
    n_all = len(eligible)
    share_all = w_max // n_all if n_all else 0

    checks = {
        "allocation_digest": _sha(d / "ALLOCATION.json") == rec["protocol"]["ALLOCATION.json_sha256"],
        "protocol_digest": _sha(d / "PROTOCOL.json") == rec["protocol"]["PROTOCOL.json_sha256"]
        and rec["protocol"]["revision"] == proto["revision"] == man["protocol"]["revision"]
        and man["protocol"]["PROTOCOL.json_sha256"] == rec["protocol"]["PROTOCOL.json_sha256"],
        "rule_text": rec["rule"] == pub["d_arms"]["rule"] and rec["candidate_note"] == pub["d_candidate_note"],
        "arm_rule_text": rec["arm_rule"] == pq["D_arm_rule"] == mq["D_arm_rule"],
        "candidates": rec["candidates"] == cands and rec["conditional_sources_admitted"] == admitted,
        "nine_orders": sorted(rec["orders"]) == sorted(keys) and sorted(rec["arms"]) == sorted(keys),
        "W_max": rec["eligibility"]["W_max"] == w_max == mq["W_max"],
        "eligible": rec["eligibility"]["eligible"] == eligible
        and rec["eligibility"]["threshold_inner_training_windows"] * 8 == w_max,
        "window_counts": rec["eligibility"]["inner_training_windows_by_source"] == {c: wit.get(c, 0) for c in cands},
        "whole_share_lists": rec["eligibility"]["windows_per_source_by_k"] == {str(k): w_max // k for k in KS}
        and rec["eligibility"]["sources_with_a_whole_share_by_k"]
        == {str(k): sorted(c for c in cands if k * wit.get(c, 0) >= w_max) for k in KS},
        "D_all": rec["D_all"]["sources"] == eligible and rec["D_all"]["windows_per_source"] == share_all
        and rec["D_all"]["unique_windows"] == share_all * n_all
        and rec["D_all"]["windows_short_of_W_max"] == w_max - share_all * n_all
        and all(wit[c] >= share_all for c in eligible)
        and rec["D_all"]["sources_with_fewer_unique_inner_training_windows_than_their_share"] == {},
        "manifest_copy": mq["D_arm_orders"] == rec["orders"] and mq["D_arms"] == rec["arms"]
        and mq["D_all"] == rec["D_all"],
    }
    orders_ok, published_ok, arms_ok, shares_ok, skipped_ok, digests_distinct = True, True, True, True, True, True
    arms, changed = {}, {}
    for k in KS:
        for draw in DRAWS:
            key = "k%d|draw%d" % (k, draw)
            dig = {c: hashlib.sha256(("%s|D|k%d|draw%d|%s" % (SALT, k, draw, c)).encode("utf-8")).hexdigest()
                   for c in cands}
            digests_distinct &= len(set(dig.values())) == len(dig)
            order = sorted(cands, key=lambda c: dig[c])
            orders_ok &= rec["orders"].get(key) == order
            published_ok &= [c for c in order if c in wave1] == published[key]
            want, passed_over = _walk(order, wit, w_max, k)
            arms[key] = want
            arm = rec["arms"].get(key, {})
            arms_ok &= arm.get("sources") == want and len(want) == k and arm.get("complete") is True
            shares_ok &= arm.get("windows_per_source") == w_max // k and arm.get("unique_windows") == w_max
            shares_ok &= all(wit[c] >= w_max // k for c in want) and len(set(want)) == len(want)
            shares_ok &= arm.get("sources_with_fewer_unique_inner_training_windows_than_their_share") == {}
            got = arm.get("skipped_in_the_order", [])
            skipped_ok &= [(s["source"], s["inner_training_windows"]) for s in got] == [(n, c) for n, c, _ in passed_over]
            skipped_ok &= all(s["why"].startswith(why) for s, (_, _, why) in zip(got, passed_over))
            old = [c for c in order if c in eligible][:k]
            if old != want:
                changed[key] = {"revision_2_rule": old, "revision_3_rule": want}
    stated = pq.get("computed_at_P2", {})
    checks.update({
        "orders_by_the_rule": orders_ok, "digests_distinct": digests_distinct,
        "wave_1_orders_equal_ALLOCATION_json": published_ok
        and rec["orders_restricted_to_wave_1_equal_ALLOCATION_json"] is True,
        "arms_by_the_revision_3_rule": arms_ok,
        "every_arm_has_W_max_unique_windows": shares_ok,
        "skipped_sources_recorded": skipped_ok,
        "no_arm_source_below_its_share": rec["arms_with_a_source_below_its_share"] == {},
        "arms_changed_from_the_revision_2_rule": rec["arms_changed_from_the_revision_2_rule"] == changed
        == mq["D_arms_changed_from_the_revision_2_rule"],
        "protocol_states_the_same_arms": stated.get("D_arms") == arms
        and stated.get("D_all", {}).get("sources") == eligible
        and stated.get("D_all", {}).get("windows_per_source") == share_all
        and stated.get("D_all", {}).get("unique_windows") == share_all * n_all
        and stated.get("W_max") == w_max,
    })
    out = {"check": "d-arm-orders", "protocol_revision": proto["revision"], "candidates": len(cands),
           "conditional_sources_admitted": admitted, "W_max": w_max, "eligible_sources": n_all,
           "arms": arms, "D_all": {"sources": eligible, "windows_per_source": share_all,
                                   "unique_windows": share_all * n_all,
                                   "windows_short_of_W_max": w_max - share_all * n_all},
           "arms_changed_from_the_revision_2_rule": sorted(changed),
           "checks": checks, "pass": all(checks.values())}
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out))
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
