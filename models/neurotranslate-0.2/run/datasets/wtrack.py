"""Single Day W-Track Learning (DANDI 000978 0.240511.0307, CC BY 4.0): ER1, JS15 and JS17 (whole recordings)
and JS14 data recorded before the start of trip 79.

Roster: the population study's protocol (repository models/population-motion/protocol.json: train ER1, JS15,
JS17; test JS21, JS34, KL8, consumed; JS14 and both ZT2 assets untouched there) and the JS14 study's frozen
split (repository benchmarks/wtrack-neural-motion: trips 55-78 train, 79 and 90 embargo, 80-89 test (consumed),
91-95 reserved). This protocol gives JS14's data recorded before the start of trip 79 to training.

Source: the arrays fetched at P1 by fetch_wtrack.py (spike times per sorted unit, camera position x and y in
cm with timestamps, epoch and trial tables), one NWB clock per file. Each epoch interval is one recording
with its own 20 ms grid starting at the epoch start; JS14's epoch 5 ends at the start of trip 79 and later
epochs are not part of the fetched data. Tokens: spikes = events per unit per step (per-recording rows,
region CA1 or PFC recorded); kin = position x and y (cm), the last camera sample inside each step and its
change (steps without a camera sample are masked). Trips (trial rows) starting inside a recording are
counted as events.
"""
import json
from pathlib import Path

import numpy as np

import common
import neural_common as nc

DATASET = "wtrack"
KIND = "animal"
RATS = ["ER1", "JS14", "JS15", "JS17"]
ANCHOR = {"kind": "single tracker", "note": "the rat's tracked position is anchored to itself"}
AXIS_NOTE = {"note": "planar x and y in cm relative to the centre well (archive reference frame); no vertical axis"}
META = {
    "name": "Single Day W-Track Learning", "doi": "10.48324/dandi.000978/0.240511.0307", "species": "rat", "sites": 1,
    "derived": False, "paired": True,
    "events_definition": "W-track trips (trial rows of the archive) starting inside a tokenised recording",
    "context": {"dataset": DATASET, "species": "rat", "task": "W-track alternation runs and rest epochs in one day",
                "body_plan": "rat (whole-body position only)", "value_flag": "measured"},
    "streams": [
        {"group": "spikes", "kind": "sorted_unit", "channels": "122 (ER1), 72 (JS14), 81 (JS15), 78 (JS17)",
         "units": "events per 20 ms step", "value_type": "measured (offline spike sorting by the authors)",
         "regions": "hippocampal CA1 and prefrontal cortex", "rows": "learned per recording"},
        {"group": "kin", "kind": "tracked_position", "channels": 2, "rate_hz": "about 30 (camera)", "units": "cm",
         "value_type": "measured (camera tracking estimate; offline processing and latency not documented)"},
    ],
    "notes": ["The archive gives no per-unit observation intervals; a zero count means no archived event.",
              "The stored speed column is not tokenised.",
              "JS14 contributes its epochs before trip 79, and epoch 5 only up to the start of trip 79."],
}


def _raw(paths):
    return Path(paths["raw"]) / "wtrack"


def roster(paths):
    rp = Path(paths["run_worktree"]) / "models" / "population-motion" / "protocol.json"
    pop = json.loads(rp.read_text())
    sp = Path(paths["run_worktree"]) / "benchmarks" / "wtrack-neural-motion" / "recording" / "split.json"
    split = json.loads(sp.read_text())
    assert sorted(pop["train"]) == ["ER1", "JS15", "JS17"] and "JS14" in pop["untouched"]
    assert split["groups"]["test"]["trial_ids"] == list(range(80, 90)) and split["groups"]["reserve"]["trial_ids"] == list(range(91, 96))
    roles = {r: "train" for r in pop["train"]}
    roles.update({r: "test (consumed)" for r in pop["test"]})
    roles["JS14"] = "train (data before trip 79)"
    return {"units": RATS, "unit_roles": roles, "training_roles": ["train", "train (data before trip 79)"],
            "rule": "population study train rats plus JS14 data recorded before the start of trip 79",
            "excluded": {"consumed_test_rats": sorted(pop["test"]), "closed": ["ZT2 (both assets)"]},
            "extra": {"JS14_excluded_time": "from the start of trip 79 on (79 and 90 embargo, 80-89 consumed test, "
                                            "91-95 reserved, later epochs)"},
            "roster_files": [{"file": "models/population-motion/protocol.json (repository)", "sha256": common.sha256_file(rp)},
                             {"file": "benchmarks/wtrack-neural-motion/recording/split.json (repository)", "sha256": common.sha256_file(sp)}]}


def channels(paths):
    return {"kin": [dict(name="position_%s" % ax, kind="tracked_position", units="cm", value_type="measured",
                         rate_hz="camera, about 30", axis=ax, frame="centre well", vocab=None, row="per-dataset")
                    for ax in ("x", "y")]}


def jobs(paths, units):
    return [(u, None) for u in units]


def process_unit(paths, unit, payload, shared):
    rec_p = _raw(paths) / (unit + "-RECEIPT.json")
    receipt = json.loads(rec_p.read_text())
    npz = _raw(paths) / (unit + ".npz")
    if common.sha256_file(npz) != receipt["file_sha256"]:
        raise ValueError("fetched arrays changed for " + unit)
    z = np.load(npz)
    st, ends = z["spike_times"], z["spike_ends"]
    starts = np.r_[0, ends[:-1]]
    per_unit = [st[a:b] for a, b in zip(starts, ends)]
    pt, xy = z["pos_t"], z["pos_xy"]
    tr_start = z["trial_start"]
    cut = receipt.get("cut", {}).get("trip79_start_s")
    unit_ch = {"spikes": [dict(name="%s:u%d" % (unit, uid), kind="sorted_unit", units="count per step",
                               value_type="measured", region=str(reg), electrode_group=str(grp), row="per-recording")
                          for uid, reg, grp in zip(z["unit_id"], z["unit_region"], z["unit_group"])]}
    recs, metas = [], []
    for eid, a, b in zip(z["epoch_id"], z["epoch_start"], z["epoch_stop"]):
        if cut is not None:
            if a >= cut:
                continue
            b = min(b, cut)
        S = common.n_steps_for(b - a)
        rid = "%s_epoch%02d" % (unit, int(eid))
        rec = nc.Rec(rid, unit, S)
        v, m = nc.spike_counts(per_unit, S, a)
        rec.put("spikes", v, m)
        sel = (pt >= a) & (pt < a + S * common.STEP_S)
        tt = pt[sel] - a
        lo, hi = common.step_bounds_times(tt, S)
        v, m = common.kin_features(xy[sel], lo, hi)
        rec.put("kin", v, m)
        n_trips = int(((tr_start >= a) & (tr_start < b)).sum())
        recs.append(rec)
        metas.append({"source_files": {"DANDI 000978 asset " + receipt["asset"]["asset_id"]: receipt["asset"]["sha256"]},
                      "task": "wtrack_run" if n_trips else "rest", "condition": "run" if n_trips else "rest",
                      "session": 1, "epoch": int(eid), "events": n_trips, "duration_s": round(S * common.STEP_S, 4),
                      "epoch_start_s": float(a), "epoch_stop_s": float(b), "camera_rows": int(sel.sum()),
                      "truncated_at_trip79": bool(cut is not None and b == cut)})
    checks = {"units": len(per_unit), "spikes_fetched": int(len(st)), "position_rows_fetched": int(len(pt)),
              "epochs_tokenised": len(recs), "cut_s": cut, "spikes_after_cut": int((st >= cut).sum()) if cut else None,
              "position_rows_after_cut": int((pt >= cut).sum()) if cut else None,
              "requests": receipt["requests"], "network_bytes": receipt["network_bytes"]}
    return recs, metas, checks, unit_ch


def file_audit(paths, results):
    ok = sorted(r["unit"] for r in results) == RATS
    js14 = [r for r in results if r["unit"] == "JS14"][0]["checks"]
    audit_p = _raw(paths) / "JS14-RANGE-AUDIT.json"
    audit = json.loads(audit_p.read_text())
    return {"pass": ok and js14["spikes_after_cut"] == 0 and js14["position_rows_after_cut"] == 0
            and not audit["overlaps_outside_probe"],
            "rats": sorted(r["unit"] for r in results), "js14_spikes_after_cut": js14["spikes_after_cut"],
            "js14_position_rows_after_cut": js14["position_rows_after_cut"],
            "js14_range_audit": {"ranges_checked": audit["js14_ranges_checked"], "held_intervals": audit["held_intervals"],
                                 "overlaps_outside_the_disclosed_probe": len(audit["overlaps_outside_probe"]),
                                 "disclosed_probe_overlap_bytes": sum(h["overlap_bytes"] for h in audit["overlaps"]
                                                                      if h["object"] == "JS14 metadata probe"),
                                 "audit_sha256": common.sha256_file(audit_p)}}


def source_file_summary(results):
    rows = sorted({(f, d) for r in results for m in r["recordings"] for f, d in m["source_files"].items()})
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    return {
        "Q3_access": {"pass": True, "how": "HDF5 byte ranges of the spike-time, position and table arrays only (ETag-pinned "
                      "range requests); JS14 held intervals forbidden before access; per-request log in DOWNLOADS.json",
                      "requests": {r["unit"]: r["checks"]["requests"] for r in results},
                      "network_bytes": {r["unit"]: r["checks"]["network_bytes"] for r in results}},
        "Q4_clock": {"pass": True, "how": "spike and camera tables share each NWB file's seconds (timestamps_reference_time)"},
        "Q5_labels": {"pass": True, "how": "spikes as event counts per sorted unit (measured; region CA1 or PFC per unit); "
                      "position in cm relative to the centre well (measured camera estimate)"},
        "Q6_causality": {"pass": True, "author_filtering": "offline spike sorting and camera tracking; position filtering, "
                         "interpolation and latency not documented", "our_features": "causal (counts and last camera sample "
                         "inside each step)"},
    }
