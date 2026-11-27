"""P2 runner: role audit, tokens, the six-check gate and the manifest part of one dataset.

  python p2.py --paths PATHS.json DATASET [--workers 8]

A dataset module (datasets/<name>.py) provides:
  DATASET, META           identifiers, DOI, species, sites, streams
  roster(paths)           frozen roster evidence: {"units": [...], "roster_files": [...], "unit_roles": {...},
                          "excluded": {...}}  (never lists or opens an excluded unit's data)
  channels(paths)         ChannelSet with the dataset's fixed channel order per group
  jobs(paths, units)      [(unit, payload)] work items, one per individual
  process_unit(paths, unit, payload, chans)
                          -> (recordings, per-recording metadata, per-unit checks)
  gates(paths, summary)   dataset-specific Q2-Q6 evidence; Q1 comes from licences.py
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
import common  # noqa: E402


class ChannelSet:
    def __init__(self):
        self.groups = {"emg": [], "kin": [], "force": []}
        self._idx = {g: {} for g in self.groups}

    def add(self, group, name, **meta):
        if name in self._idx[group]:
            return self._idx[group][name]
        self._idx[group][name] = len(self.groups[group])
        self.groups[group].append(dict(name=name, **meta))
        return self._idx[group][name]

    def idx(self, group, name):
        return self._idx[group][name]

    def names(self, group):
        return [c["name"] for c in self.groups[group]]

    def kinds(self):
        out = {}
        for g, chans in self.groups.items():
            d = {}
            for i, c in enumerate(chans):
                d.setdefault(c.get("kind", g), []).append(i)
            out[g] = d
        return out

    def n(self, group):
        return len(self.groups[group])

    def to_json(self):
        return {g: chans for g, chans in self.groups.items() if chans}


_STATE = {}


def _init(dsname, paths, chans):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    _STATE["mod"] = importlib.import_module("datasets." + dsname)
    _STATE["paths"] = paths
    _STATE["chans"] = chans


def _work(job):
    unit, payload = job
    mod, paths, chans = _STATE["mod"], _STATE["paths"], _STATE["chans"]
    t0 = time.time()
    recs, metas, checks = mod.process_unit(paths, unit, payload, chans)
    # a source shorter than one 20 ms step (for example a one-frame static trial) gives no token
    dropped = [dict(m, rec_id=r.rec_id, reason="shorter than one 20 ms step") for r, m in zip(recs, metas) if r.n_steps == 0]
    keep = [i for i, r in enumerate(recs) if r.n_steps > 0]
    recs, metas = [recs[i] for i in keep], [metas[i] for i in keep]
    kinds = chans.kinds()
    counts = []
    for r, m in zip(recs, metas):
        c = common.count_recording(r, kinds)
        m.update(c)
        m["rec_id"] = r.rec_id
        counts.append(c)
    shard = Path(paths["shards"]) / mod.DATASET / (unit.replace("/", "_") + ".npz")
    if recs:
        digest, size = common.write_unit_shard(shard, unit, recs, chans.groups)
    else:
        digest, size = None, 0
    return {"unit": unit, "recordings": metas, "dropped_recordings": dropped, "checks": checks,
            "shard": shard.name if recs else None,
            "shard_sha256": digest, "shard_bytes": size, "seconds": round(time.time() - t0, 2)}


def summarise(results, alloc_ds):
    inner_val = set(alloc_ds["inner_validation"])
    tot = {"recordings": 0, "steps": 0, "steps_with_data": 0, "windows": 0, "windows_all_steps_with_data": 0,
           "windows_inner_training": 0, "windows_inner_validation": 0, "events": 0}
    chs, tasks, conds, sessions = {}, {}, {}, set()
    for res in results:
        for m in res["recordings"]:
            tot["recordings"] += 1
            for k in ("steps", "steps_with_data", "windows", "windows_all_steps_with_data"):
                tot[k] += m[k]
            tot["windows_inner_validation" if res["unit"] in inner_val else "windows_inner_training"] += m["windows"]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("dataset")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--units", nargs="*", help="debug: restrict to these units (no manifest part written)")
    ap.add_argument("--audit-only", action="store_true",
                    help="redo only the role audit and rewrite it into the existing AUDIT and manifest part (tokens unchanged)")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    mod = importlib.import_module("datasets." + a.dataset)
    ds = mod.DATASET
    head = common.protocol_head(paths)
    proto, alloc = common.protocol_files(paths)
    t0 = time.time()

    # --- Q2 role audit against the frozen roster(s) -------------------------------------------
    ros = mod.roster(paths)
    units = ros["units"]
    alloc_ds = alloc["inner_folds"][ds]
    alloc_units = [r["unit"] for r in alloc_ds["rows"]]
    fold_ok, folds = common.fold_rule_check(ds, units, alloc)
    unit_rows = []
    for u in units:
        role = ros["unit_roles"].get(u)
        excl_hits = [k for k, v in ros["excluded"].items() if u in v]
        unit_rows.append({"unit": u, "roster_role": role, "inner_fold": folds.get(u),
                          "in_allocation": u in alloc_units, "in_excluded_groups": excl_hits,
                          "pass": bool(role) and role in ros["training_roles"] and not excl_hits and u in alloc_units})
    audit = {"dataset": ds, "protocol_head": head, "roster_files": ros["roster_files"],
             "training_roles": ros["training_roles"], "rule": ros.get("rule"),
             "excluded_groups_checked": {k: len(v) for k, v in ros["excluded"].items()},
             "units": unit_rows, "allocation_units_equal_roster_units": sorted(alloc_units) == sorted(units),
             "inner_fold_rule_recomputed_equal": fold_ok,
             "all_units_pass": all(r["pass"] for r in unit_rows) and sorted(alloc_units) == sorted(units) and fold_ok}
    if not audit["all_units_pass"]:
        common.atomic_write_json(Path(paths["audits"]) / (ds + "-AUDIT.json"), audit)
        sys.exit("role audit failed for %s" % ds)
    if a.audit_only:
        old_audit = json.loads((Path(paths["audits"]) / (ds + "-AUDIT.json")).read_text())
        audit["unit_checks"] = old_audit.get("unit_checks")
        audit["tokens_from_run_with_protocol_head"] = old_audit.get("protocol_head")
        common.atomic_write_json(Path(paths["audits"]) / (ds + "-AUDIT.json"), audit)
        pf = Path(paths["manifest_parts"]) / (ds + ".json")
        part = json.loads(pf.read_text())
        part["role_audit"] = {"pass": audit["all_units_pass"], "units": len(unit_rows),
                              "roster_files": ros["roster_files"], "excluded_groups_checked": audit["excluded_groups_checked"],
                              "inner_fold_rule_recomputed_equal": fold_ok, "redone_at": common.now_iso(),
                              "roles_seen": sorted({r["roster_role"] for r in unit_rows})}
        part["qualification"]["Q2_role"]["roster_files"] = ros["roster_files"]
        part["qualification"]["Q2_role"]["pass"] = audit["all_units_pass"] and part["qualification"]["Q2_role"]["file_audit"]["pass"]
        part["qualified"] = all(g["pass"] for g in part["qualification"].values())
        common.atomic_write_json(pf, part)
        print(json.dumps({"dataset": ds, "role_audit": part["role_audit"]["pass"], "roles": part["role_audit"]["roles_seen"]}))
        return

    # --- tokens ------------------------------------------------------------------------------
    chans = mod.channels(paths)
    jobs = mod.jobs(paths, units)
    if a.units:
        jobs = [j for j in jobs if j[0] in a.units]
    assert {j[0] for j in jobs} <= set(units)
    (Path(paths["shards"]) / ds).mkdir(parents=True, exist_ok=True)
    workers = max(1, min(a.workers, 8, len(jobs)))
    if workers == 1:
        _init(a.dataset, paths, chans)
        results = [_work(j) for j in jobs]
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_init, initargs=(a.dataset, paths, chans)) as pool:
            results = pool.map(_work, jobs, chunksize=1)
    results.sort(key=lambda r: r["unit"])
    if a.units:
        print(json.dumps({"debug_units": a.units, "results": [{k: v for k, v in r.items() if k != "recordings"}
                                                               for r in results]}, indent=1)[:4000])
        print(json.dumps(summarise(results, alloc_ds), indent=1))
        return

    summary = summarise(results, alloc_ds)
    # every recording maps to a training unit and every source file read belongs to it
    file_audit = mod.file_audit(paths, results) if hasattr(mod, "file_audit") else None
    lic = json.loads((Path(paths["licences"]) / (ds + ".json")).read_text())
    gates = mod.gates(paths, results, summary)
    gates["Q1_licence"] = {"pass": bool(lic["allowed_by_Q1"]), "declared": lic["declared_licence"],
                           "deposit_endpoint": lic["deposit_endpoint"], "response_sha256": lic["response_sha256"],
                           "licence_object_sha256": lic.get("licence_object_sha256"),
                           "licence_text": lic.get("licence_text"), "checked_at": lic["checked_at"]}
    gates["Q2_role"] = {"pass": audit["all_units_pass"] and (file_audit is None or file_audit["pass"]),
                        "units_checked": len(unit_rows), "roster_files": ros["roster_files"],
                        "file_audit": file_audit}
    order = ["Q1_licence", "Q2_role", "Q3_access", "Q4_clock", "Q5_labels", "Q6_causality"]
    gates = {k: gates[k] for k in order}
    qualified = all(g["pass"] for g in gates.values())

    shard_list = [{"unit": r["unit"], "file": r["shard"], "sha256": r["shard_sha256"], "bytes": r["shard_bytes"]}
                  for r in results if r["shard"]]
    tokens = {"dataset": ds, "protocol_head": head, "features": common.GROUP_FEATURES,
              "step_s": common.STEP_S, "window_steps": common.WINDOW_STEPS,
              "channels": chans.to_json(), "axis_map": getattr(mod, "AXIS_NOTE", None),
              "anchor": getattr(mod, "ANCHOR", None), "context": mod.META.get("context"),
              "shards": shard_list,
              "recordings": [dict(m, unit=r["unit"]) for r in results for m in r["recordings"]]}
    common.atomic_write_json(Path(paths["shards"]) / ds / "TOKENS.json", tokens)
    audit["unit_checks"] = {r["unit"]: r["checks"] for r in results}
    common.atomic_write_json(Path(paths["audits"]) / (ds + "-AUDIT.json"), audit)

    inner_val = alloc_ds["inner_validation"]
    part = {
        "dataset": ds, "part": "motion-and-emg", "wave": 1, "name": mod.META["name"], "doi": mod.META["doi"],
        "licence": lic["declared_licence"], "species": mod.META["species"], "sites": mod.META["sites"],
        "protocol_head": head, "built_at": common.now_iso(), "qualified": qualified,
        "counts": {
            "individuals": len({r["unit"] for r in results if r["recordings"]}),
            "individuals_in_roster": len(units),
            "animals": 0 if mod.META["species"] == "human" else len(units),
            "people": len({r["unit"] for r in results if r["recordings"]}) if mod.META["species"] == "human" else 0,
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
            "spikes": 0,
            "events": {"count": summary["events"], "definition": mod.META.get("events_definition")},
            "sources_read_without_a_full_step": sum(len(r.get("dropped_recordings", [])) for r in results),
        },
        "inner_validation_units": inner_val,
        "streams": mod.META["streams"],
        "flags": {"derived_values_present": mod.META.get("derived", False), "simulated_values_present": False,
                  "paired_streams": mod.META.get("paired")},
        "qualification": gates,
        "role_audit": {"pass": audit["all_units_pass"], "units": len(unit_rows),
                       "roster_files": ros["roster_files"], "excluded_groups_checked": audit["excluded_groups_checked"],
                       "inner_fold_rule_recomputed_equal": fold_ok,
                       "roles_seen": sorted({r["roster_role"] for r in unit_rows})},
        "tokens": {"shards": len(shard_list), "bytes": sum(s["bytes"] for s in shard_list),
                   "shard_list_sha256": common.sha256_text(json.dumps(shard_list, sort_keys=True)),
                   "channels": {g: len(c) for g, c in chans.groups.items()},
                   "shared_vocabulary_channels": {g: sum(1 for c in cs if c.get("vocab")) for g, cs in chans.groups.items()}},
        "source_files": mod.source_file_summary(results) if hasattr(mod, "source_file_summary") else None,
        "notes": mod.META.get("notes", []),
        "seconds": round(time.time() - t0, 1),
    }
    common.atomic_write_json(Path(paths["manifest_parts"]) / (ds + ".json"), part)
    print(json.dumps({"dataset": ds, "qualified": qualified, "counts": {k: part["counts"][k] for k in (
        "individuals", "recordings", "unique_steps_20ms", "windows_1200ms", "windows_inner_training")},
        "gates": {k: v["pass"] for k, v in gates.items()}, "seconds": part["seconds"]}))


if __name__ == "__main__":
    main()
