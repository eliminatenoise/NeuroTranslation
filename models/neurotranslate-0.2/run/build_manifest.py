"""Merge per-dataset manifest parts into MIXTURE-MANIFEST.json (counts, flags, licences and file hashes;
no recording values), then compute the mixture totals and, once every quantity-versus-diversity anchor is
present, W_max and the sources eligible for the D arms (PROTOCOL.json quantity_diversity).

Entries of datasets that have no part in the parts folder (for example datasets written by the neural
part of P2 directly) are kept as they are. The write happens under a lock and re-reads the file first.
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


def qd(datasets, proto):
    anchors = proto["quantity_diversity"].get("Q_anchors") if isinstance(proto["quantity_diversity"], dict) else None
    anchors = ["gait120", "ds003739", "ofner", "wtrack"]
    have = {a: datasets[a]["counts"]["windows_inner_training"] for a in anchors
            if a in datasets and datasets[a].get("qualified") and "windows_inner_training" in datasets[a].get("counts", {})}
    if len(have) < len(anchors):
        return {"status": "pending: anchors not yet counted", "anchors_counted": have,
                "anchors_missing": [a for a in anchors if a not in have]}
    m = min(have.values())
    w = 1
    while w * 2 <= m:
        w *= 2
    elig = sorted(k for k, d in datasets.items() if d.get("qualified") and
                  d.get("counts", {}).get("windows_inner_training", 0) >= w / 8)
    return {"status": "computed", "anchors_inner_training_windows": have, "W_max": w,
            "D_arm_eligible_sources": elig, "rule": "W_max = smallest anchor inner-training window count rounded down "
            "to a power of 2; D-arm sources need at least W_max/8 inner-training windows"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--out", help="defaults to the run worktree's models/neurotranslate-0.2/MIXTURE-MANIFEST.json")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    out = Path(a.out) if a.out else Path(paths["run_worktree"]) / "models" / "neurotranslate-0.2" / "MIXTURE-MANIFEST.json"
    proto, _ = common.protocol_files(paths)
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
        obj["quantity_diversity"] = qd(ds, proto)
        obj["updated_at"] = common.now_iso()
        obj["no_recording_values"] = True
        return obj

    res = common.locked_update(out, upd, dict, lock_path=Path(paths["private"]) / "MIXTURE-MANIFEST.json.lock")
    s = json.dumps(res)
    assert not any(x in s for x in FORBIDDEN)
    print(json.dumps({"datasets": sorted(res["datasets"]), "totals": res["totals"], "qd": res["quantity_diversity"]["status"]}))


if __name__ == "__main__":
    main()
