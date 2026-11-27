"""P2 runner of the neural part: role audit, tokens, the six-check gate and the manifest part of one dataset.

  python p2_neural.py --paths PATHS.json DATASET [--workers 8]

A dataset module (datasets/<name>.py) provides:
  DATASET, META, KIND        identifiers and descriptions; KIND is "person", "animal" or "time_block"
  roster(paths)              {"units", "unit_roles", "training_roles", "excluded", "roster_files", "rule"}
  channels(paths)            {group: [channel dicts]} shared by every unit (groups with fixed channel lists)
  jobs(paths, units)         [(unit, payload)]
  process_unit(paths, unit, payload, shared)
                             -> (recs, metas, checks, unit_channels) where unit_channels is
                                {group: [channel dicts]} for groups whose channels are specific to the unit
                                (spike units, electrodes) and recs are neural_common.Rec objects
  gates(paths, results, summary)  Q3-Q6 evidence (Q1 from licences.py, Q2 from the role audit)
  file_audit(paths, results)      optional: every source read belongs to a training unit
For time-block datasets every recording's metadata carries "inner_fold" (the latest block is fold 4).
Outputs (private): shards/<dataset>/<unit>.npz, shards/<dataset>/TOKENS.json, audits/<dataset>-AUDIT.json,
manifest-parts/<dataset>.json. No recording value leaves the private folder.
"""
import argparse
import importlib
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import common  # noqa: E402
import neural_common as nc  # noqa: E402

_STATE = {}


def _init(dsname, paths, shared):
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    _STATE["mod"] = importlib.import_module("datasets." + dsname)
    _STATE["paths"] = paths
    _STATE["shared"] = shared


def _work(job):
    unit, payload = job
    mod, paths, shared = _STATE["mod"], _STATE["paths"], _STATE["shared"]
    t0 = time.time()
    recs, metas, checks, unit_ch = mod.process_unit(paths, unit, payload, shared)
    dropped = [dict(m, rec_id=r.rec_id, reason="shorter than one 20 ms step") for r, m in zip(recs, metas)
               if r.n_steps == 0]
    keep = [i for i, r in enumerate(recs) if r.n_steps > 0]
    recs, metas = [recs[i] for i in keep], [metas[i] for i in keep]
    chans = dict(shared)
    chans.update(unit_ch or {})
    kinds = {g: nc.kinds_of(c) for g, c in chans.items()}
    for r, m in zip(recs, metas):
        m.update(nc.count_rec(r, kinds))
        m["rec_id"] = r.rec_id
    shard = Path(paths["shards"]) / mod.DATASET / (unit.replace("/", "_") + ".npz")
    if recs:
        digest, size, quant = nc.write_shard(shard, unit, recs, {g: len(c) for g, c in chans.items()},
                                             dtypes=getattr(mod, "GROUP_DTYPES", None))
    else:
        digest, size, quant = None, 0, {}
    return {"unit": unit, "recordings": metas, "dropped_recordings": dropped, "checks": checks, "float16_error": quant,
            "unit_channels": unit_ch or {}, "shard": shard.name if recs else None,
            "shard_sha256": digest, "shard_bytes": size, "seconds": round(time.time() - t0, 2)}


def summarise(results, inner_val_units, kind):
    tot = {"recordings": 0, "steps": 0, "steps_with_data": 0, "windows": 0, "windows_all_steps_with_data": 0,
           "windows_inner_training": 0, "windows_inner_validation": 0, "events": 0, "spikes": 0}
    chs, tasks, conds, sessions = {}, {}, {}, set()
    for res in results:
        for m in res["recordings"]:
            tot["recordings"] += 1
            for k in ("steps", "steps_with_data", "windows", "windows_all_steps_with_data", "spikes"):
                tot[k] += m[k]
            if kind == "time_block":
                val = m.get("inner_fold") == 4
            else:
                val = res["unit"] in inner_val_units
            tot["windows_inner_validation" if val else "windows_inner_training"] += m["windows"]
            tot["events"] += int(m.get("events", 0) or 0)
            for k, v in m["channel_seconds"].items():
                chs[k] = chs.get(k, 0.0) + v
            tasks[m.get("task", "")] = tasks.get(m.get("task", ""), 0) + 1
            if m.get("condition") is not None:
                conds[str(m["condition"])] = conds.get(str(m["condition"]), 0) + 1
            if m.get("session") is not None:
                sessions.add((res["unit"], str(m["session"])))
    tot["channel_seconds"] = {k: round(v, 2) for k, v in sorted(chs.items())}
    tot["tasks"] = dict(sorted(tasks.items()))
    tot["conditions"] = dict(sorted(conds.items()))
    tot["sessions"] = len(sessions)
    return tot


def float16_summary(results):
    out = {}
    for r in results:
        for g, v in (r.get("float16_error") or {}).items():
            cur = out.setdefault(g, [0.0] * len(v))
            out[g] = [max(a, b) for a, b in zip(cur, v)]
    return {g: dict(zip(nc.GROUP_FEATURES[g], [float("%.3g" % x) for x in v])) for g, v in out.items()}


def role_audit(mod, paths, alloc, head):
    ds = mod.DATASET
    ros = mod.roster(paths)
    units = ros["units"]
    if mod.KIND == "time_block":
        alloc_ds = alloc["inner_folds"].get(ds) or alloc.get("conditional_training", {}).get(ds)
        alloc_units = alloc_ds.get("recordings") or alloc_ds.get("units")
        fold_ok, folds = True, {u: "time blocks" for u in units}
        inner_val = []
    elif ds in alloc["inner_folds"]:
        alloc_ds = alloc["inner_folds"][ds]
        alloc_units = [r["unit"] for r in alloc_ds["rows"]]
        fold_ok, folds = common.fold_rule_check(ds, units, alloc)
        inner_val = alloc_ds["inner_validation"]
    else:  # conditional member whose folds are computed at P2 by the published rule
        alloc_ds = alloc["conditional_training"][ds]
        alloc_units = units
        ranked = sorted(units, key=lambda u: (common.sha256_text("%s|fold|%s|%s" % (common.SALT, ds, u)), u))
        folds = {u: i % 5 for i, u in enumerate(ranked)}
        fold_ok = True
        inner_val = [u for u in units if folds[u] == 0]
    rows = []
    for u in units:
        role = ros["unit_roles"].get(u)
        hits = [k for k, v in ros["excluded"].items() if u in v]
        rows.append({"unit": u, "roster_role": role, "inner_fold": folds.get(u), "in_allocation": u in alloc_units,
                     "in_excluded_groups": hits,
                     "pass": bool(role) and role in ros["training_roles"] and not hits and u in alloc_units})
    same = sorted(alloc_units) == sorted(units)
    audit = {"dataset": ds, "protocol_head": head, "roster_files": ros["roster_files"],
             "training_roles": ros["training_roles"], "rule": ros.get("rule"),
             "excluded_groups_checked": {k: len(v) for k, v in ros["excluded"].items()},
             "excluded_groups": ros["excluded"], "units": rows, "allocation_units_equal_roster_units": same,
             "inner_fold_rule_recomputed_equal": fold_ok, "extra": ros.get("extra"),
             "all_units_pass": all(r["pass"] for r in rows) and same and fold_ok}
    return audit, ros, inner_val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("dataset")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--units", nargs="*", help="debug: restrict to these units (no manifest part written)")
    ap.add_argument("--extra-only", action="store_true",
                    help="rerun only the dataset's extra_outputs hook on the existing TOKENS.json and record it in the part")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    mod = importlib.import_module("datasets." + a.dataset)
    ds = mod.DATASET
    head = common.protocol_head(paths)
    proto, alloc = common.protocol_files(paths)
    t0 = time.time()

    if a.extra_only:
        tok = json.loads((Path(paths["shards"]) / ds / "TOKENS.json").read_text())
        by_unit = {}
        for m in tok["recordings"]:
            by_unit.setdefault(m["unit"], []).append(m)
        extra = mod.extra_outputs(paths, [{"unit": u, "recordings": ms} for u, ms in sorted(by_unit.items())])
        pf = Path(paths["manifest_parts"]) / (ds + ".json")
        part = json.loads(pf.read_text())
        part.setdefault("tokens", {}).update(extra)
        common.atomic_write_json(pf, part)
        print(json.dumps(extra))
        return

    audit, ros, inner_val = role_audit(mod, paths, alloc, head)
    if not audit["all_units_pass"]:
        common.atomic_write_json(Path(paths["audits"]) / (ds + "-AUDIT.json"), audit)
        sys.exit("role audit failed for %s" % ds)
    units = ros["units"]

    shared = mod.channels(paths)
    jobs = mod.jobs(paths, units)
    if a.units:
        jobs = [j for j in jobs if j[0] in a.units]
    assert {j[0] for j in jobs} <= set(units)
    (Path(paths["shards"]) / ds).mkdir(parents=True, exist_ok=True)
    workers = max(1, min(a.workers, 8, len(jobs)))
    if workers == 1:
        _init(a.dataset, paths, shared)
        results = [_work(j) for j in jobs]
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_init, initargs=(a.dataset, paths, shared)) as pool:
            results = pool.map(_work, jobs, chunksize=1)
    results.sort(key=lambda r: r["unit"])
    summary = summarise(results, set(inner_val), mod.KIND)
    if a.units:
        print(json.dumps({"debug_units": a.units, "results": [{k: v for k, v in r.items() if k not in ("recordings",)}
                                                               for r in results]}, indent=1, default=str)[:6000])
        print(json.dumps(summary, indent=1))
        return

    file_audit = mod.file_audit(paths, results) if hasattr(mod, "file_audit") else None
    lic = json.loads((Path(paths["licences"]) / (ds + ".json")).read_text())
    gates = mod.gates(paths, results, summary)
    gates["Q1_licence"] = {"pass": bool(lic["allowed_by_Q1"]), "declared": lic["declared_licence"],
                           "deposit_endpoint": lic["deposit_endpoint"], "response_sha256": lic["response_sha256"],
                           "licence_object_sha256": lic.get("licence_object_sha256"),
                           "licence_text": lic.get("licence_text"), "checked_at": lic["checked_at"]}
    gates["Q2_role"] = {"pass": audit["all_units_pass"] and (file_audit is None or file_audit["pass"]),
                        "units_checked": len(audit["units"]), "roster_files": ros["roster_files"],
                        "file_audit": file_audit}
    order = ["Q1_licence", "Q2_role", "Q3_access", "Q4_clock", "Q5_labels", "Q6_causality"]
    gates = {k: gates[k] for k in order}
    qualified = all(g["pass"] for g in gates.values())

    shard_list = [{"unit": r["unit"], "file": r["shard"], "sha256": r["shard_sha256"], "bytes": r["shard_bytes"]}
                  for r in results if r["shard"]]
    tokens = {"dataset": ds, "protocol_head": head, "features": nc.GROUP_FEATURES,
              "dtypes": {g: np.dtype((getattr(mod, "GROUP_DTYPES", None) or nc.GROUP_DTYPES).get(g, np.float32)).name
                         for g in nc.GROUP_ORDER},
              "step_s": common.STEP_S, "window_steps": common.WINDOW_STEPS,
              "field_definition": {"bands_hz": [[b[1], b[2]] for b in nc.BANDS], "windows_s": nc.FIELD_WINDOWS_S,
                                   "warmup_s": nc.WARMUP_S, "high_band_min_fs": nc.HIGH_BAND_MIN_FS},
              "channels": shared, "unit_channels": {r["unit"]: r["unit_channels"] for r in results if r["unit_channels"]},
              "axis_map": getattr(mod, "AXIS_NOTE", None), "anchor": getattr(mod, "ANCHOR", None),
              "context": mod.META.get("context"), "kind": mod.KIND, "shards": shard_list,
              "recordings": [dict(m, unit=r["unit"]) for r in results for m in r["recordings"]]}
    common.atomic_write_json(Path(paths["shards"]) / ds / "TOKENS.json", nc.json_safe(tokens))
    audit["unit_checks"] = {r["unit"]: r["checks"] for r in results}
    common.atomic_write_json(Path(paths["audits"]) / (ds + "-AUDIT.json"), nc.json_safe(audit))

    n_ind = len({r["unit"] for r in results if r["recordings"]})
    human = mod.META["species"] == "human"
    individuals = mod.META.get("individuals_override") or n_ind
    chan_counts = {}
    for g, c in shared.items():
        chan_counts[g] = len(c)
    for r in results:
        for g, c in r["unit_channels"].items():
            chan_counts[g] = chan_counts.get(g, 0) + len(c)
    part = {
        "dataset": ds, "part": "neural", "wave": mod.META.get("wave", 1), "name": mod.META["name"],
        "doi": mod.META["doi"], "licence": lic["declared_licence"], "species": mod.META["species"],
        "sites": mod.META["sites"], "protocol_head": head, "built_at": common.now_iso(), "qualified": qualified,
        "counts": {
            "individuals": individuals,
            "individuals_in_roster": mod.META.get("individuals_in_roster", len(units)),
            "animals": 0 if human else individuals,
            "people": individuals if human else 0,
            "sites": mod.META["sites"],
            "sessions": summary["sessions"],
            "recordings": summary["recordings"],
            "tasks": summary["tasks"], "conditions": summary["conditions"],
            "unique_steps_20ms": summary["steps"], "steps_with_any_channel": summary["steps_with_data"],
            "windows_1200ms": summary["windows"],
            "windows_1200ms_every_step_with_data": summary["windows_all_steps_with_data"],
            "windows_inner_training": summary["windows_inner_training"],
            "windows_inner_validation": summary["windows_inner_validation"],
            "channel_seconds": summary["channel_seconds"],
            "spikes": summary["spikes"],
            "events": {"count": summary["events"], "definition": mod.META.get("events_definition")},
            "sources_read_without_a_full_step": sum(len(r.get("dropped_recordings", [])) for r in results),
        },
        "unit_kind": mod.KIND,
        "inner_validation_units": inner_val if mod.KIND != "time_block" else "latest time block (fold 4) of each recording",
        "streams": mod.META["streams"],
        "flags": {"derived_values_present": mod.META.get("derived", False), "simulated_values_present": False,
                  "paired_streams": mod.META.get("paired")},
        "qualification": gates,
        "role_audit": {"pass": audit["all_units_pass"], "units": len(audit["units"]),
                       "roster_files": ros["roster_files"], "excluded_groups_checked": audit["excluded_groups_checked"],
                       "inner_fold_rule_recomputed_equal": audit["inner_fold_rule_recomputed_equal"],
                       "roles_seen": sorted({str(r["roster_role"]) for r in audit["units"]})},
        "tokens": {"shards": len(shard_list), "bytes": sum(s["bytes"] for s in shard_list),
                   "shard_list_sha256": common.sha256_text(json.dumps(shard_list, sort_keys=True)),
                   "channels": chan_counts,
                   "shared_vocabulary_channels": {g: sum(1 for c in cs if c.get("vocab")) for g, cs in shared.items()},
                   "field_storage": np.dtype((getattr(mod, "GROUP_DTYPES", None) or nc.GROUP_DTYPES).get("field", np.float32)).name,
                   "float16_rms_error_over_channel_sd_max": float16_summary(results)},
        "source_files": mod.source_file_summary(results) if hasattr(mod, "source_file_summary") else None,
        "notes": mod.META.get("notes", []),
        "seconds": round(time.time() - t0, 1),
    }
    if hasattr(mod, "extra_outputs"):
        part["tokens"].update(mod.extra_outputs(paths, results))
    common.atomic_write_json(Path(paths["manifest_parts"]) / (ds + ".json"), nc.json_safe(part))
    print(json.dumps({"dataset": ds, "qualified": qualified, "counts": {k: part["counts"][k] for k in (
        "individuals", "recordings", "unique_steps_20ms", "windows_1200ms", "windows_inner_training", "spikes")},
        "gates": {k: v["pass"] for k, v in gates.items()}, "seconds": part["seconds"]}))


if __name__ == "__main__":
    main()
