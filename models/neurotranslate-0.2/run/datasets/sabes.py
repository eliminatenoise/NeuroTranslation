"""O'Doherty/Sabes nonhuman primate reaching (Zenodo 3854034 v2, CC BY 4.0): the training files
indy_20170131_02 and loco_20170215_02 of the cortical-source-mix study (two macaques, Indy and Loco).

Roster: the cortical-source-mix protocol lists exactly these two original files (author MD5s) for
training; indy_20161212_02 (kept for future intake) and the August held days stay out. Each local copy's
sha256 (protocol pins) and MD5 (author checksum) are checked before it is opened.

Each MATLAB v7.3 file holds one clock t (seconds, 4 ms period), the fingertip position finger_pos
(rows z, -x, -y in cm from the hand tracker) and per electrode five spike-time lists (one unsorted and up
to four sorted partitions). Tokens (protocol): spikes = events per electrode per step, the five partitions
summed; kin = the planar fingertip coordinates -x and -y converted to x and y in mm (multiplied by -10, as
the cortical-source-mix study did). The cursor and target arrays are not tokenised; target changes are
counted as events.

Inner folds (protocol section 6, fewer than three individuals): each recording's time span is cut into 5
equal blocks in time order, a 1 s gap is dropped at each internal boundary, and block b is fold b (fold 4,
the latest, is inner validation). Each block is tokenised as its own recording with its own 20 ms grid
starting at the block start.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

import common
import neural_common as nc

DATASET = "sabes"
KIND = "time_block"
FILES = {
    "indy_20170131_02": {"path_key": "sabes_indy", "bytes": 208792806, "md5": "2790b1c869564afaa7772dbf9e42d784",
                         "sha256": "a55c9703ec61af9fe6757e285972b10839232482e046e7618e06bcc846ab0c24", "animal": "Indy"},
    "loco_20170215_02": {"path_key": "sabes_loco", "bytes": 779509843, "md5": "739b70762d838f3a1f358733c426bb02",
                         "sha256": "6cdaa3c9f6845bd3f0c31c45136f09ecc259049d1ea51fc327599c7e194a133c", "animal": "Loco"},
}
ANCHOR = {"kind": "single tracker", "note": "the fingertip is anchored to itself"}
AXIS_NOTE = {"note": "planar x and y of the reaching workspace (from the tracker's -x and -y columns, cm x -10 = mm); no vertical axis"}
META = {
    "name": "Nonhuman primate reaching with multichannel sensorimotor cortex electrophysiology", "doi": "10.5281/zenodo.3854034",
    "species": "macaque", "sites": 1, "derived": False, "paired": True,
    "events_definition": "target changes (rows where the stored target position changes)",
    "context": {"dataset": DATASET, "species": "macaque", "task": "self-paced reaching to successive targets on a grid",
                "body_plan": "macaque arm", "value_flag": "measured"},
    "streams": [
        {"group": "spikes", "kind": "electrode_events", "channels": "96 (Indy, M1) and 192 (Loco, M1 and S1)",
         "units": "events per 20 ms step (sorted and unsorted partitions summed per electrode)", "value_type": "measured",
         "rows": "learned per recording"},
        {"group": "kin", "kind": "fingertip", "channels": 2, "rate_hz": 250, "units": "mm", "value_type": "measured"},
    ],
    "notes": ["Per-electrode observation intervals are not documented, so a zero count means no exported event, not "
              "verified silence.", "The 1 s around each internal block boundary is not tokenised (fold rule)."],
}


def roster(paths):
    src = Path(paths["sabes_roster"])
    pr = json.loads(src.read_text())
    tr = pr["training"]
    assert "2790b1c869564afaa7772dbf9e42d784" in tr["indy"] and "739b70762d838f3a1f358733c426bb02" in tr["loco"]
    units = sorted(FILES)
    return {"units": units, "unit_roles": {u: "training" for u in units}, "training_roles": ["training"],
            "rule": "cortical-source-mix training files (author MD5s in its protocol)",
            "excluded": {"reserved_future_intake": ["indy_20161212_02"], "august_held_days_consumed": []},
            "extra": {"august_held_days": "not named in the roster; no August file is opened"},
            "roster_files": [{"file": "cortical-source-mix PROTOCOL.json (earlier study)", "sha256": common.sha256_file(src)}]}


def channels(paths):
    kin = [dict(name="fingertip_%s" % ax, kind="fingertip", units="mm", value_type="measured", rate_hz=250, axis=ax,
                source="finger_pos row %d (cm) x -10" % (1 if ax == "x" else 2), vocab=None, row="per-dataset")
           for ax in ("x", "y")]
    return {"kin": kin}


def jobs(paths, units):
    return [(u, FILES[u]) for u in units]


def _check_file(path, spec):
    md5, sha = hashlib.md5(), hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            md5.update(b)
            sha.update(b)
            n += len(b)
    return n == spec["bytes"] and md5.hexdigest() == spec["md5"] and sha.hexdigest() == spec["sha256"]


def _times(f, ref):
    d = f[ref]
    if d.attrs.get("MATLAB_empty"):
        return np.zeros(0)
    return np.asarray(d[()], np.float64).ravel()


def process_unit(paths, unit, spec, shared):
    import h5py
    path = paths[spec["path_key"]]
    if not _check_file(path, spec):
        raise ValueError("size, MD5 or sha256 mismatch for " + unit)
    with h5py.File(path, "r") as f:
        t = f["t"][0].astype(np.float64)
        fp = f["finger_pos"][()].astype(np.float64)
        tp = f["target_pos"][()].astype(np.float64)
        names = ["".join(chr(c) for c in f[r][()].ravel()) for r in f["chan_names"][0]]
        sp = f["spikes"]
        per_el = []
        n_part = sp.shape[0]
        for c in range(sp.shape[1]):
            per_el.append(np.sort(np.concatenate([_times(f, sp[i, c]) for i in range(n_part)])))
    dt = np.diff(t)
    assert np.allclose(dt, 0.004, atol=1e-9), "clock is not a uniform 4 ms grid"
    xy = -10.0 * fp[1:3].T  # (-x, -y) cm -> (x, y) mm
    T0, T1 = t[0], t[-1] + 0.004
    unit_ch = {"spikes": [dict(name="%s:%s" % (unit, n), kind="electrode_events", units="count per step",
                               value_type="measured", array=n.split()[0], electrode=n, row="per-recording",
                               partitions_summed=n_part) for n in names]}
    recs, metas = [], []
    spikes_outside = 0
    for fold, a, e in nc.time_blocks(T0, T1):
        S = common.n_steps_for(e - a)
        rid = "%s_block%d" % (unit, fold)
        rec = nc.Rec(rid, unit, S)
        v, m = nc.spike_counts(per_el, S, a)
        rec.put("spikes", v, m)
        i0 = int(np.ceil((a - T0) / 0.004 - 1e-6))
        i1 = int(np.ceil((a + S * 0.02 - T0) / 0.004 - 1e-6))
        seg = xy[i0:i1]
        lo, hi = common.step_bounds(len(seg), 250.0, (T0 + i0 * 0.004) - a, S)
        v, m = common.kin_features(seg, lo, hi)
        rec.put("kin", v, m)
        tps = tp[:, i0:i1]
        ch = np.any(np.diff(tps, axis=1) != 0, axis=0) & np.all(np.isfinite(tps[:, 1:]), axis=0)
        recs.append(rec)
        metas.append({"source_files": {Path(path).name + " (" + unit + ")": spec["sha256"]}, "task": "random_target_reaching",
                      "condition": None, "session": unit, "inner_fold": fold, "events": int(ch.sum()),
                      "block_start_s": round(a - T0, 4), "block_stop_s": round(e - T0, 4), "duration_s": round(S * 0.02, 4),
                      "animal": spec["animal"]})
    allsp = np.concatenate(per_el) if per_el else np.zeros(0)
    spikes_outside = int(((allsp < T0) | (allsp >= T1)).sum())
    checks = {"electrodes": len(names), "partitions": n_part, "clock_s": [float(T0), float(T1)],
              "spike_events_total": int(len(allsp)), "spike_events_outside_clock": spikes_outside,
              "finger_nonfinite_rows": int((~np.isfinite(xy).all(axis=1)).sum())}
    return recs, metas, checks, unit_ch


def file_audit(paths, results):
    return {"pass": sorted(r["unit"] for r in results) == sorted(FILES), "files": sorted(r["unit"] for r in results)}


def source_file_summary(results):
    rows = sorted({(f, d) for r in results for m in r["recordings"] for f, d in m["source_files"].items()})
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    return {
        "Q3_access": {"pass": True, "how": "local copies of the two original files; size, author MD5 and sha256 checked"},
        "Q4_clock": {"pass": True, "how": "one file per session; spike times and the fingertip trace share the file's clock t "
                     "(uniform 4 ms grid checked)", "spike_events_outside_clock": {r["unit"]: r["checks"]["spike_events_outside_clock"]
                                                                                 for r in results}},
        "Q5_labels": {"pass": True, "how": "spikes as event counts per electrode (measured, sorted and unsorted partitions "
                      "summed); fingertip position in mm (measured, converted from cm)"},
        "Q6_causality": {"pass": True, "author_filtering": "tracker processing of the fingertip trace not documented",
                         "our_features": "causal (counts and last samples inside each step)"},
    }
