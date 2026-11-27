"""Merge per-dataset manifest parts into MIXTURE-MANIFEST.json (counts, flags, licences and file hashes;
no recording values), then compute the mixture totals and, once every quantity-versus-diversity anchor is
present, W_max and the sources eligible for the D arms (PROTOCOL.json quantity_diversity).

Entries of datasets that have no part in the parts folder (for example datasets written by the neural
part of P2 directly) are kept as they are. The write happens under a lock and re-reads the file first.

Once W_max is computed, the D-arm source orders (recomputed over the wave-1 sources and every conditional
source admitted before the freeze, as ALLOCATION.json d_candidate_note requires) are also written to
D-ARM-ORDERS.json beside the manifest; ALLOCATION.json is never edited. check_d_arm_orders.py recomputes that
file from the published rule without using this module.
"""
import argparse
import json
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


def qd(paths, datasets, alloc):
    """PROTOCOL.json quantity_diversity, counted at P2: W_max, the Q levels and budget, the D-arm orders
    recomputed with every admitted conditional source (ALLOCATION.json d_candidate_note), D-arm eligibility
    (at least W_max/8 inner-training windows), the sources of each D arm and D_all, and W_P of the P arms."""
    q = alloc["quantity_diversity"]
    anchors = q["q_anchors"]
    have = {a: datasets[a]["counts"]["windows_inner_training"] for a in anchors
            if a in datasets and datasets[a].get("qualified") and "windows_inner_training" in datasets[a].get("counts", {})}
    if len(have) < len(anchors):
        return {"status": "pending: anchors not yet counted", "anchors_counted": have,
                "anchors_missing": [a for a in anchors if a not in have]}
    w = _pow2_floor(min(have.values()))
    wit = {k: d.get("counts", {}).get("windows_inner_training", 0) for k, d in datasets.items() if d.get("qualified")}
    elig = sorted(k for k, n in wit.items() if n >= w / 8)
    published = q["d_arms"]["orders"]
    base = sorted(next(iter(published.values())))
    admitted = [c for c in CONDITIONAL_SOURCES if datasets.get(c, {}).get("qualified")]
    not_admitted = {c: datasets.get(c, {}).get("not_qualified_because", "not qualified")
                    for c in CONDITIONAL_SOURCES if c not in admitted}
    cands = sorted(set(base) | set(admitted))
    orders, arms, published_equal = {}, {}, True
    for k in (2, 4, 8):
        for draw in (0, 1, 2):
            key = "k%d|draw%d" % (k, draw)
            order = sorted(cands, key=lambda d: (common.sha256_text("%s|D|%s|%s" % (common.SALT, key, d)), d))
            published_equal &= [d for d in order if d in base] == published[key]
            orders[key] = order
            chosen = [d for d in order if d in elig][:k]
            arms[key] = {"sources": chosen, "windows_per_source": w // k,
                         "sources_with_fewer_unique_inner_training_windows_than_their_share":
                             {d: wit[d] for d in chosen if wit[d] < w // k}}
    d_all = {"sources": elig, "windows_per_source": w // len(elig) if elig else 0,
             "sources_with_fewer_unique_inner_training_windows_than_their_share":
                 {d: wit[d] for d in elig if wit[d] < (w // len(elig) if elig else 0)}}
    p_arms = {}
    for ds, spec in q["p_arms"].items():
        lv = spec["levels"]
        smallest = min(lv, key=int)
        n_small = _unit_windows(paths, ds, lv[smallest])
        p_arms[ds] = {"levels_people": sorted((int(x) for x in lv)),
                      "windows_of_smallest_level": {"people": int(smallest), "windows": n_small},
                      "W_P": _pow2_floor(min(w // 4, n_small)),
                      "windows_per_level": {x: _unit_windows(paths, ds, lv[x]) for x in sorted(lv, key=int)}}
    return {"status": "computed", "anchors_inner_training_windows": have, "W_max": w,
            "q_levels": [w // 16, w // 4, w], "updates_per_arm_U": 40 * w // 128,
            "D_arm_eligible_sources": elig, "D_arm_eligibility_threshold_windows": w / 8,
            "inner_training_windows_by_source": dict(sorted(wit.items())),
            "D_arm_candidates": {"wave_1": base, "conditional_admitted": admitted,
                                 "conditional_not_admitted": not_admitted},
            "D_arm_orders": orders,
            "D_arm_orders_restricted_to_wave_1_equal_ALLOCATION_json": bool(published_equal),
            "D_arms": arms, "D_all": d_all, "P_arms": p_arms,
            "rule": "W_max = smallest anchor inner-training window count rounded down to a power of 2; D-arm sources "
                    "need at least W_max/8 inner-training windows; D-arm orders by ascending sha256('" + common.SALT +
                    "|D|k' + k + '|draw' + draw + '|' + dataset) over the wave-1 sources and the admitted conditional "
                    "sources, each arm taking the first k eligible sources; W_P = the largest power of 2 not above "
                    "min(W_max/4, windows of the smallest P level)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--out", help="defaults to the run worktree's models/neurotranslate-0.2/MIXTURE-MANIFEST.json")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    out = Path(a.out) if a.out else Path(paths["run_worktree"]) / "models" / "neurotranslate-0.2" / "MIXTURE-MANIFEST.json"
    proto, alloc = common.protocol_files(paths)
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
        obj["protocol"] = {"file": "PROTOCOL.json", "revision": proto.get("revision", proto.get("protocol_version")),
                           "head": common.protocol_head(paths)["branch_head"]}
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
        obj["quantity_diversity"] = qd(paths, ds, alloc)
        prov = Path(paths["private"]) / "P1-PROTOCOL-HEADS.json"
        if prov.exists():
            obj["protocol_heads_at_p1"] = json.loads(prov.read_text())
        obj["updated_at"] = common.now_iso()
        obj["no_recording_values"] = True
        return obj

    res = common.locked_update(out, upd, dict, lock_path=Path(paths["private"]) / "MIXTURE-MANIFEST.json.lock")
    s = json.dumps(res)
    assert not any(x in s for x in FORBIDDEN)
    orders = d_arm_orders(res, alloc, common.protocol_head(paths))
    if orders:
        assert not any(x in json.dumps(orders) for x in FORBIDDEN)
        common.atomic_write_json(out.with_name(D_ARM_FILE), orders)
    print(json.dumps({"datasets": sorted(res["datasets"]), "totals": res["totals"], "qd": res["quantity_diversity"]["status"],
                      "d_arm_orders_file": D_ARM_FILE if orders else None}))


D_ARM_FILE = "D-ARM-ORDERS.json"


def d_arm_orders(manifest, alloc, head):
    """The D-arm orders as their own file beside the manifest. ALLOCATION.json publishes the orders of the wave-1
    sources and says (d_candidate_note) that they are recomputed, by the same rule, once a conditional source is
    admitted; the published file is not edited. Returns None until the anchors are counted."""
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
                "d_candidate_note requires. ALLOCATION.json itself is unchanged and lists the wave-1 sources only; "
                "restricted to those sources, every order here equals the published one.",
        "protocol": {"head": head["branch_head"], "ALLOCATION.json_sha256": head["ALLOCATION.json"],
                     "PROTOCOL.json_sha256": head["PROTOCOL.json"]},
        "rule": pub["d_arms"]["rule"],
        "candidate_note": pub["d_candidate_note"],
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
                        "not_eligible": {c: wit.get(c, 0) for c in cands if wit.get(c, 0) < thr}},
        "arms": q["D_arms"],
        "D_all": q["D_all"],
        "arms_with_a_source_below_its_share": {
            key: arm["sources_with_fewer_unique_inner_training_windows_than_their_share"]
            for key, arm in q["D_arms"].items() if arm["sources_with_fewer_unique_inner_training_windows_than_their_share"]},
        "counts_from": "MIXTURE-MANIFEST.json of " + manifest["updated_at"],
        "no_recording_values": True}


if __name__ == "__main__":
    main()
