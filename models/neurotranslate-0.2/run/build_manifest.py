"""Merge per-dataset manifest parts into MIXTURE-MANIFEST.json (counts, flags, licences and file hashes;
no recording values), then compute the mixture totals and, once every quantity-versus-diversity anchor is
present, W_max, the D arms and the P-arm budgets (PROTOCOL.json quantity_diversity).

Entries of datasets that have no part in the parts folder (for example datasets written by the neural
part of P2 directly) are kept as they are. The write happens under a lock and re-reads the file first.

Once W_max is computed, the D-arm source orders (recomputed over the wave-1 sources and every conditional
source admitted before the freeze, as ALLOCATION.json d_candidate_note requires) and the D arms are also
written to D-ARM-ORDERS.json beside the manifest; ALLOCATION.json is never edited. check_d_arm_orders.py
recomputes that file from the published rules without using this module.

D arms from protocol revision 3 (PROTOCOL.json quantity_diversity.D_arm_rule): a source enters a k-source arm
only if it has at least W_max/k unique inner-training windows. The draw's order is walked from the top;
sources with fewer than W_max/8 windows (not eligible) and sources with fewer than W_max/k (short for this k)
are skipped, and the first k that remain form the arm. The nine orders do not depend on this rule.

The protocol is read from the folder above this one (or --protocol-dir): from revision 3 the governing
protocol files sit beside the manifest. The run stops if those files differ from their last commit, unless
--draft is given together with --out (a trial build that is not to be committed).
"""
import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

FORBIDDEN = tuple("/%s/" % d for d in ("home", "tmp", "Users", "mnt"))  # absolute local paths


def totals(datasets):
    t = {"datasets": 0, "qualified_datasets": 0, "individuals": 0, "people": 0, "animals": 0, "sites": 0,
         "recordings": 0, "tasks": 0, "unique_steps_20ms": 0, "windows_1200ms": 0, "windows_inner_training": 0,
         "windows_inner_validation": 0, "spikes": 0, "events": 0, "channel_seconds_by_group": {},
         "species": {}, "not_qualified": {}}
    for name, d in datasets.items():
        c = d.get("counts", {})
        t["datasets"] += 1
        t["qualified_datasets"] += 1 if d.get("qualified") else 0
        if not d.get("qualified"):
            t["not_qualified"][name] = d.get("not_qualified_because", "see its qualification record")
            continue
        t["sites"] += int(c.get("sites", 0) or 0)
        t["tasks"] += len(c.get("tasks") or {})
        sp = d.get("species")
        t["species"][sp] = t["species"].get(sp, 0) + int(c.get("individuals", 0) or 0)
        for k in ("individuals", "people", "animals", "recordings", "unique_steps_20ms", "windows_1200ms",
                  "windows_inner_training", "windows_inner_validation", "spikes"):
            v = c.get(k, 0)
            t[k] += v if isinstance(v, (int, float)) else 0
        ev = c.get("events", {})
        t["events"] += ev.get("count", 0) if isinstance(ev, dict) else (ev or 0)
        for k, v in (c.get("channel_seconds") or {}).items():
            g = k.split(":")[0]
            t["channel_seconds_by_group"][g] = round(t["channel_seconds_by_group"].get(g, 0.0) + v, 2)
    return t


CONTEXTS = (64, 128, 256, 512)


def padded_share(paths, datasets):
    """Padded share at each context length T (PROTOCOL.json time_estimates): every recording is tiled into
    ceil(L / T) rows of T steps; the share is padded positions over all positions. Counted from the step counts
    in each qualified dataset's private TOKENS.json (no recording value is read)."""
    per, tot = {}, {T: [0, 0] for T in CONTEXTS}
    for name, d in sorted(datasets.items()):
        if not d.get("qualified"):
            continue
        tf = Path(paths["shards"]) / name / "TOKENS.json"
        if not tf.exists():
            continue
        steps = [r["steps"] for r in json.loads(tf.read_text())["recordings"]]
        per[name] = {}
        for T in CONTEXTS:
            rows = sum(-(-L // T) for L in steps)
            pad = rows * T - sum(steps)
            per[name][str(T)] = round(pad / (rows * T), 4) if rows else None
            tot[T][0] += pad
            tot[T][1] += rows * T
    return {"rule": "each recording tiled into ceil(L/T) rows of T steps; share = padded positions / all positions",
            "all_qualified_datasets": {str(T): round(a / b, 4) if b else None for T, (a, b) in tot.items()},
            "per_dataset": per}


CONDITIONAL_SOURCES = ("area2", "falcon_m1")  # ALLOCATION.json d_candidate_note


def _pow2_floor(x):
    w = 1
    while w * 2 <= x:
        w *= 2
    return w if x >= 1 else 0


def _unit_windows(paths, dataset, units):
    tf = Path(paths["shards"]) / dataset / "TOKENS.json"
    rows = json.loads(tf.read_text())["recordings"]
    return sum(r["windows"] for r in rows if r["unit"] in set(units))


PROTOCOL_FILES = ("PROTOCOL.json", "PROTOCOL.md", "PROTOCOL-SIMPLE.md", "ALLOCATION.json")


def protocol_here(folder):
    """PROTOCOL.json and ALLOCATION.json of the folder that holds the governing protocol, and what identifies
    them: the last commit that changed a protocol file, the files' sha256 and whether they equal that commit."""
    folder = Path(folder)

    def git(*args):
        return subprocess.run(["git", "-C", str(folder)] + list(args), capture_output=True, text=True,
                              check=True).stdout.strip()

    proto = json.loads((folder / "PROTOCOL.json").read_text())
    alloc = json.loads((folder / "ALLOCATION.json").read_text())
    ident = {"revision": proto.get("revision"),
             "commit": git("log", "-1", "--format=%H", "--", *PROTOCOL_FILES),
             "files_equal_commit": git("status", "--porcelain", "--", *PROTOCOL_FILES) == "",
             "PROTOCOL.json": common.sha256_file(folder / "PROTOCOL.json"),
             "ALLOCATION.json": common.sha256_file(folder / "ALLOCATION.json")}
    return proto, alloc, ident


def d_arm(order, wit, w, k):
    """One D arm under the revision 3 rule. Walks the draw's order; a source needs at least W_max/8 unique
    inner-training windows to be eligible at all and at least W_max/k to enter a k-source arm. Returns the
    first k sources that pass and the sources skipped on the way, with the reason (whole-number comparisons)."""
    chosen, skipped = [], []
    for d in order:
        if len(chosen) == k:
            break
        n = wit.get(d, 0)
        if n * 8 < w:
            skipped.append({"source": d, "inner_training_windows": n, "why": "not eligible: fewer than W_max/8"})
        elif n * k < w:
            skipped.append({"source": d, "inner_training_windows": n,
                            "why": "short for this k: fewer than W_max/%d" % k})
        else:
            chosen.append(d)
    return chosen, skipped


def w_max_basis(paths, alloc, have, w):
    """Where the anchor that sets W_max gets its windows. For Gait120 the step segments and the static trials
    are counted apart (counts and signal kinds from the private TOKENS.json; no recording value is read)."""
    setter = min(sorted(have), key=lambda a: have[a])
    out = {"anchor_with_fewest_inner_training_windows": setter, "its_inner_training_windows": have[setter],
           "W_max": w, "margin_over_W_max_windows": have[setter] - w,
           "rule": "the smallest number of unique inner-training windows in any Q anchor, rounded down to a "
                   "power of 2; every training-role recording of the anchor counts"}
    tf = Path(paths["shards"]) / "gait120" / "TOKENS.json"
    if setter != "gait120" or not tf.exists():
        return out
    rows = json.loads(tf.read_text())["recordings"]
    tr = set(alloc["inner_folds"]["gait120"]["inner_training"])
    seg = [r for r in rows if r.get("task") != "Static"]
    sta = [r for r in rows if r.get("task") == "Static"]
    w_seg = sum(r["windows"] for r in seg if r["unit"] in tr)
    w_sta = sum(r["windows"] for r in sta if r["unit"] in tr)
    assert w_seg + w_sta == have["gait120"], (w_seg, w_sta, have["gait120"])
    kinds = sorted({k for r in sta for k, v in (r.get("channel_seconds") or {}).items() if v > 0})
    dur = [r["duration_s"] for r in seg]
    short = sum(1 for r in seg if r["steps"] < common.WINDOW_STEPS)
    out["gait120"] = {
        "inner_training_windows": have["gait120"],
        "from_step_segments": w_seg,
        "from_static_trials": w_sta,
        "static_trial_recordings_inner_training": sum(1 for r in sta if r["unit"] in tr),
        "signal_kinds_with_values_in_static_trials": kinds,
        "static_trial_windows_hold": "markers only (no EMG, no force)" if kinds == ["kin:marker"] else "see the kinds",
        "why_static_trials_count": "static trials are training-role recordings of the training people and were "
                                   "counted in the first count as well; the rule is applied as written",
        "W_max_from_step_segments_alone": _pow2_floor(w_seg),
        "margin_over_W_max_windows": have["gait120"] - w,
        "Q_arm_at_W_max": {"windows_used": w, "windows_available": have["gait120"]},
        "report_rule": "every Q-arm report gives the number of static-trial windows drawn at each level",
        "step_segments": {
            "count": len(seg), "median_s": round(statistics.median(dur), 2), "min_s": min(dur), "max_s": max(dur),
            "protocol_expected_s": "1.5-1.65",
            "shorter_than_one_1200ms_window": short,
            "note": "a departure recorded in revision 3: a segment shorter than one 1.2 s window gives training "
                    "steps but no counted window"}}
    return out


def qd(paths, datasets, alloc, proto):
    """PROTOCOL.json quantity_diversity, counted at P2: W_max and what it rests on, the Q levels and budget, the
    D-arm orders recomputed with every admitted conditional source (ALLOCATION.json d_candidate_note), the D arms
    under the revision 3 rule (a source needs its whole share of W_max/k windows), D_all, and W_P of the P arms."""
    q = alloc["quantity_diversity"]
    anchors = q["q_anchors"]
    have = {a: datasets[a]["counts"]["windows_inner_training"] for a in anchors
            if a in datasets and datasets[a].get("qualified") and "windows_inner_training" in datasets[a].get("counts", {})}
    if len(have) < len(anchors):
        return {"status": "pending: anchors not yet counted", "anchors_counted": have,
                "anchors_missing": [a for a in anchors if a not in have]}
    arm_rule = proto.get("quantity_diversity", {}).get("D_arm_rule")
    if not arm_rule:
        sys.exit("PROTOCOL.json in the protocol folder has no quantity_diversity.D_arm_rule (revision 3 or later)")
    w = _pow2_floor(min(have.values()))
    wit = {k: d.get("counts", {}).get("windows_inner_training", 0) for k, d in datasets.items() if d.get("qualified")}
    elig = sorted(k for k, n in wit.items() if n * 8 >= w)
    published = q["d_arms"]["orders"]
    base = sorted(next(iter(published.values())))
    admitted = [c for c in CONDITIONAL_SOURCES if datasets.get(c, {}).get("qualified")]
    not_admitted = {c: datasets.get(c, {}).get("not_qualified_because", "not qualified")
                    for c in CONDITIONAL_SOURCES if c not in admitted}
    cands = sorted(set(base) | set(admitted))
    orders, arms, changed, published_equal = {}, {}, {}, True
    whole = {str(k): sorted(d for d in cands if wit.get(d, 0) * k >= w) for k in (2, 4, 8)}
    for k in (2, 4, 8):
        for draw in (0, 1, 2):
            key = "k%d|draw%d" % (k, draw)
            order = sorted(cands, key=lambda d: (common.sha256_text("%s|D|%s|%s" % (common.SALT, key, d)), d))
            published_equal &= [d for d in order if d in base] == published[key]
            orders[key] = order
            chosen, skipped = d_arm(order, wit, w, k)
            arms[key] = {"sources": chosen, "windows_per_source": w // k,
                         "unique_windows": (w // k) * len(chosen), "complete": len(chosen) == k,
                         "skipped_in_the_order": skipped,
                         "sources_with_fewer_unique_inner_training_windows_than_their_share":
                             {d: wit[d] for d in chosen if wit[d] < w // k}}
            before = [d for d in order if d in elig][:k]  # the revision 2 rule: the first k eligible sources
            if before != chosen:
                changed[key] = {"revision_2_rule": before, "revision_3_rule": chosen}
    share_all = w // len(elig) if elig else 0
    d_all = {"sources": elig, "windows_per_source": share_all, "unique_windows": share_all * len(elig),
             "windows_short_of_W_max": w - share_all * len(elig),
             "note": "floor(W_max / number of eligible sources) windows from each; the arm is short of W_max by "
                     "the remainder",
             "sources_with_fewer_unique_inner_training_windows_than_their_share":
                 {d: wit[d] for d in elig if wit[d] < share_all}}
    p_arms = {}
    for ds, spec in q["p_arms"].items():
        lv = spec["levels"]
        smallest = min(lv, key=int)
        n_small = _unit_windows(paths, ds, lv[smallest])
        p_arms[ds] = {"levels_people": sorted((int(x) for x in lv)),
                      "windows_of_smallest_level": {"people": int(smallest), "windows": n_small},
                      "W_P": _pow2_floor(min(w // 4, n_small)),
                      "W_P_set_by": "W_max/4 (%d windows)" % (w // 4) if n_small >= w // 4 else
                                    "the smallest level (%d people, %d windows)" % (int(smallest), n_small),
                      "windows_per_level": {x: _unit_windows(paths, ds, lv[x]) for x in sorted(lv, key=int)}}
        if n_small < w // 4:
            p_arms[ds]["limit"] = ("the %d-person level has %d windows, so each P arm of this dataset has %d windows "
                                   "(W_max/4 would be %d); a limit of the arm, kept as the rule gives it"
                                   % (int(smallest), n_small, p_arms[ds]["W_P"], w // 4))
    return {"status": "computed", "anchors_inner_training_windows": have, "W_max": w,
            "W_max_basis": w_max_basis(paths, alloc, have, w),
            "q_levels": [w // 16, w // 4, w], "updates_per_arm_U": 40 * w // 128,
            "D_arm_eligible_sources": elig,
            "D_arm_eligibility_threshold_windows": w // 8 if w % 8 == 0 else w / 8,
            "inner_training_windows_by_source": dict(sorted(wit.items())),
            "D_arm_candidates": {"wave_1": base, "conditional_admitted": admitted,
                                 "conditional_not_admitted": not_admitted},
            "D_arm_orders": orders,
            "D_arm_orders_restricted_to_wave_1_equal_ALLOCATION_json": bool(published_equal),
            "D_arm_rule": arm_rule,
            "D_arm_windows_per_source": {str(k): w // k for k in (2, 4, 8)},
            "D_arm_sources_with_a_whole_share": whole,
            "D_arms": arms, "D_arms_changed_from_the_revision_2_rule": changed, "D_all": d_all, "P_arms": p_arms,
            "rule": "W_max = smallest anchor inner-training window count rounded down to a power of 2; D-arm orders by "
                    "ascending sha256('" + common.SALT + "|D|k' + k + '|draw' + draw + '|' + dataset) over the wave-1 "
                    "sources and the admitted conditional sources; a source needs at least W_max/8 inner-training "
                    "windows to be eligible and at least W_max/k to enter a k-source arm, and each arm takes the "
                    "first k sources of its order that have W_max/k; D_all takes floor(W_max / n) windows from each "
                    "of the n eligible sources; W_P = the largest power of 2 not above min(W_max/4, windows of the "
                    "smallest P level)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--out", help="defaults to the run worktree's models/neurotranslate-0.2/MIXTURE-MANIFEST.json")
    ap.add_argument("--protocol-dir", default=str(Path(__file__).resolve().parent.parent),
                    help="folder with PROTOCOL.json and ALLOCATION.json (default: the folder above this one)")
    ap.add_argument("--draft", action="store_true",
                    help="allow protocol files that differ from their last commit; needs --out (a trial build)")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    out = Path(a.out) if a.out else Path(paths["run_worktree"]) / "models" / "neurotranslate-0.2" / "MIXTURE-MANIFEST.json"
    proto, alloc, ident = protocol_here(a.protocol_dir)
    if a.draft and not a.out:
        sys.exit("--draft needs --out: a trial build is not written beside the protocol")
    if not ident["files_equal_commit"] and not a.draft:
        sys.exit("the protocol files differ from their last commit; commit them first (or use --draft with --out)")
    parts = {}
    for f in sorted(Path(paths["manifest_parts"]).glob("*.json")):
        p = json.loads(f.read_text())
        s = json.dumps(p)
        bad = [x for x in FORBIDDEN if x in s]
        if bad:
            sys.exit("part %s holds a private string %s" % (f.name, bad))
        parts[p["dataset"]] = p

    def upd(obj):
        ds = obj.setdefault("datasets", {})
        ds.update(parts)
        obj["schema"] = "neurotranslate-0.2-mixture-manifest"
        obj["protocol"] = {"file": "PROTOCOL.json", "revision": ident["revision"], "head": ident["commit"],
                           "head_is": "the last commit that changed PROTOCOL.json, PROTOCOL.md, PROTOCOL-SIMPLE.md or "
                                      "ALLOCATION.json when this file was built",
                           "PROTOCOL.json_sha256": ident["PROTOCOL.json"],
                           "ALLOCATION.json_sha256": ident["ALLOCATION.json"]}
        if a.draft:
            obj["protocol"]["draft"] = "trial build: the protocol files were not committed"
        obj["counting_rules"] = {
            "step": "20 ms; step k covers [20k, 20k + 20) ms of a recording",
            "window": "non-overlapping 1.2 s (60 steps) from the start of each recording; a final partial window is not counted",
            "individuals": "people or animals with at least one tokenised recording",
            "channel_seconds": "per group and kind: channels with a present value x 0.02 s",
            "events": "dataset-specific, defined in each entry",
            "sites": "laboratories per dataset (1 each); no two datasets are known to share a laboratory, so the total "
                     "is the sum",
            "tasks": "distinct task labels per dataset, summed",
            "totals": "qualified datasets only; a dataset that is not qualified is listed with its reason",
            "time_block_datasets": "sabes and area2 (fewer than three individuals) count windows in folds 0-3 as inner "
                                   "training and in fold 4 (the latest block) as inner validation"}
        obj["totals"] = totals(ds)
        obj["padded_share"] = padded_share(paths, ds)
        obj["re_estimate"] = {
            "unique_steps_20ms": obj["totals"]["unique_steps_20ms"],
            "design_range_steps": "8-30 million (PROTOCOL.json time_estimates)",
            "not_part_of_this_step": "the 512-step GPU throughput and 16-thread CPU issuing measurements and the "
                                     "recomputed P3-P9 times are made before model choice, not in the data step"}
        obj["quantity_diversity"] = qd(paths, ds, alloc, proto)
        prov = Path(paths["private"]) / "P1-PROTOCOL-HEADS.json"
        if prov.exists():
            heads = json.loads(prov.read_text())
            if "revision_by_step" in heads:
                obj["protocol_revision_by_step"] = heads.pop("revision_by_step")
            obj["protocol_heads_at_p1"] = heads
        obj["updated_at"] = common.now_iso()
        obj["no_recording_values"] = True
        return obj

    res = common.locked_update(out, upd, dict, lock_path=Path(paths["private"]) / "MIXTURE-MANIFEST.json.lock")
    s = json.dumps(res)
    assert not any(x in s for x in FORBIDDEN)
    orders = d_arm_orders(res, alloc, ident)
    if orders:
        assert not any(x in json.dumps(orders) for x in FORBIDDEN)
        common.atomic_write_json(out.with_name(D_ARM_FILE), orders)
    print(json.dumps({"datasets": sorted(res["datasets"]), "totals": res["totals"], "qd": res["quantity_diversity"]["status"],
                      "d_arm_orders_file": D_ARM_FILE if orders else None}))


D_ARM_FILE = "D-ARM-ORDERS.json"


def d_arm_orders(manifest, alloc, ident):
    """The D-arm orders and arms as their own file beside the manifest. ALLOCATION.json publishes the orders of
    the wave-1 sources and says (d_candidate_note) that they are recomputed, by the same rule, once a conditional
    source is admitted; the published file is not edited. Which sources of an order form an arm is decided by
    the arm rule of PROTOCOL.json (revision 3). Returns None until the anchors are counted."""
    q = manifest["quantity_diversity"]
    if q.get("status") != "computed":
        return None
    pub = alloc["quantity_diversity"]
    wit = q["inner_training_windows_by_source"]
    thr = q["D_arm_eligibility_threshold_windows"]
    cands = sorted(next(iter(q["D_arm_orders"].values())))
    added = q["D_arm_candidates"]["conditional_admitted"]
    return {
        "schema": "neurotranslate-0.2-d-arm-orders",
        "what": "Source orders of the D arms (source diversity at a fixed window budget), recomputed at P2 over the "
                "13 wave-1 sources and the conditional source(s) admitted before the freeze, as ALLOCATION.json "
                "d_candidate_note requires, and the arms those orders give under the arm rule of protocol revision "
                "%s. ALLOCATION.json itself is unchanged and lists the wave-1 sources only; restricted to those "
                "sources, every order here equals the published one." % ident["revision"],
        "protocol": {"revision": ident["revision"], "head": ident["commit"],
                     "ALLOCATION.json_sha256": ident["ALLOCATION.json"],
                     "PROTOCOL.json_sha256": ident["PROTOCOL.json"]},
        "rule": pub["d_arms"]["rule"],
        "candidate_note": pub["d_candidate_note"],
        "arm_rule": q["D_arm_rule"],
        "arm_rule_note": "ALLOCATION.json is not edited. The last part of its rule (an arm uses the first k eligible "
                         "sources of its order) is replaced from protocol revision 3 by the arm rule above; the "
                         "ordering part of the rule and the nine orders are unchanged.",
        "key": "sha256 of the UTF-8 text '" + common.SALT + "|D|k<k>|draw<draw>|<dataset>', ascending by its hex "
               "digest (equal digests, which do not occur, would be ordered by name)",
        "candidates": cands,
        "conditional_sources_admitted": added,
        "conditional_sources_not_admitted": q["D_arm_candidates"]["conditional_not_admitted"],
        "orders": q["D_arm_orders"],
        "orders_restricted_to_wave_1_equal_ALLOCATION_json": q["D_arm_orders_restricted_to_wave_1_equal_ALLOCATION_json"],
        "position_of_admitted_conditional_sources": {c: {key: order.index(c) + 1 for key, order in q["D_arm_orders"].items()}
                                                     for c in added},
        "eligibility": {"W_max": q["W_max"], "threshold_inner_training_windows": thr,
                        "inner_training_windows_by_source": {c: wit.get(c, 0) for c in cands},
                        "eligible": [c for c in cands if wit.get(c, 0) >= thr],
                        "not_eligible": {c: wit.get(c, 0) for c in cands if wit.get(c, 0) < thr},
                        "windows_per_source_by_k": q["D_arm_windows_per_source"],
                        "sources_with_a_whole_share_by_k": q["D_arm_sources_with_a_whole_share"]},
        "arms": q["D_arms"],
        "arms_changed_from_the_revision_2_rule": q["D_arms_changed_from_the_revision_2_rule"],
        "D_all": q["D_all"],
        "arms_with_a_source_below_its_share": {
            key: arm["sources_with_fewer_unique_inner_training_windows_than_their_share"]
            for key, arm in q["D_arms"].items() if arm["sources_with_fewer_unique_inner_training_windows_than_their_share"]},
        "counts_from": "MIXTURE-MANIFEST.json of " + manifest["updated_at"],
        "no_recording_values": True}


if __name__ == "__main__":
    main()
