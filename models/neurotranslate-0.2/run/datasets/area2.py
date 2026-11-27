"""Area2_Bump (DANDI 000127 0.220113.0359, CC BY 4.0), conditional member: the 290 Han 2017-12-07 trials that
the area2 separate-day study used for fitting (218) and configuration (72).

Role audit (step P2): the earlier area2 force-forecast study split the NLB 'train' and 'val' trials of this file
(364 whole trials ordered by start time) into the first floor(0.6 N) = 218 for fitting, the next floor(0.2 N) = 72
for configuration and the remaining 74 held (assessed in the original comparison, consumed); the separate-day
study reused the 290 fitting and configuration trials. The rule is recomputed here from the trial table and must
give exactly the trial lists of that study's input record. The 74 held trials, the 462 trials outside the NLB
splits, the Dryad deposit and the NLB test file stay out.

Reading: only data up to the end of the last configuration trial (1809.676 s; the first held trial starts at
1815.644 s) are read: rows of the 1 kHz behaviour arrays before that time, and per unit the spike times before it.
Each unit's boundary is located by a binary search reading single values; values the search touches at or after
the cut are compared with it and discarded (their number is recorded).

Tokens: spikes = events of the 65 sorted area 2 units per step, masked outside each unit's observation intervals;
kin = hand position x, y (cm in the file, converted to mm); force = handle forces x, y, z (N). The moments,
velocities, joint angles and muscle lengths (model outputs) are not tokenised. Recordings are trial pieces: each of
the 290 trials, cut by the protocol's five equal time blocks over the span of the 290 trials (1 s gap dropped at
each internal boundary); block b is fold b and fold 4 is inner validation.
"""
import json
from pathlib import Path

import numpy as np

import common
import neural_common as nc

DATASET = "area2"
KIND = "time_block"
UNIT = "Han_20171207"
SHA256 = "639b1a03ab813f96fec76681110a1634942476badc0fd4c93d406c24701f5db2"
BYTES = 1822876234
FS = 1000.0
ANCHOR = {"kind": "single tracker", "note": "the hand position is anchored to itself"}
AXIS_NOTE = {"note": "planar x and y of the manipulandum workspace (cm in the file, mm in the tokens); forces x, y, z in "
             "the manipulandum frame"}
META = {
    "name": "Area2_Bump (Neural Latents Benchmark)", "doi": "10.48324/dandi.000127/0.220113.0359", "species": "macaque",
    "sites": 1, "derived": False, "paired": True, "wave": "1 (conditional, admitted by the P2 role audit)",
    "events_definition": "trials (one per tokenised trial; trial pieces cut by a block boundary count once)",
    "context": {"dataset": DATASET, "species": "macaque", "task": "centre-out reaching with occasional handle bumps",
                "body_plan": "macaque arm", "value_flag": "measured"},
    "streams": [
        {"group": "spikes", "kind": "sorted_unit", "channels": 65, "units": "events per 20 ms step",
         "value_type": "measured", "rows": "learned per recording", "masking": "outside each unit's observation intervals"},
        {"group": "kin", "kind": "hand_position", "channels": 2, "rate_hz": 1000, "units": "mm (file: cm)",
         "value_type": "measured (low-pass filtered at 100 Hz by the authors)"},
        {"group": "force", "kind": "handle_force", "channels": 3, "rate_hz": 1000, "units": "N", "value_type": "measured"},
    ],
    "notes": ["Only the 290 fitting and configuration trials are tokenised; inter-trial time and other trials are not.",
              "Hand position was low-pass filtered at 100 Hz by the authors (phase not documented)."],
}


def _inputs_record(paths):
    return Path(paths["area2_roles"])


def _split_rule(trials):
    ids, split, st = trials["id"], trials["split"], trials["start"]
    el = np.flatnonzero(np.isin(split, ["train", "val"]))
    order = el[np.argsort(st[el], kind="stable")]
    n = len(order)
    nf, ncf = int(np.floor(0.6 * n)), int(np.floor(0.2 * n))
    return (sorted(ids[order[:nf]].tolist()), sorted(ids[order[nf:nf + ncf]].tolist()),
            sorted(ids[order[nf + ncf:]].tolist()), n)


def _trials(path):
    import h5py
    with h5py.File(path, "r") as f:
        t = f["intervals/trials"]
        out = {"id": t["id"][:].astype(np.int64), "start": t["start_time"][:], "stop": t["stop_time"][:],
               "split": np.array([s.decode() if isinstance(s, bytes) else str(s) for s in t["split"][:]]),
               "bump": t["ctr_hold_bump"][:].astype(bool)}
    return out


def roster(paths):
    rec = json.loads(_inputs_record(paths).read_text())
    fit, cfg = rec["packets"]["fit"]["allocated_trial_ids"], rec["packets"]["config"]["allocated_trial_ids"]
    held = rec["packets"]["held"]["allocated_trial_ids"]
    tr = _trials(paths["area2_file"])
    rf, rc, rh, n = _split_rule(tr)
    ok = rf == sorted(fit) and rc == sorted(cfg) and rh == sorted(held) and n == 364 and len(fit) == 218 and len(cfg) == 72
    return {"units": [UNIT], "unit_roles": {UNIT: "fitting and configuration trials" if ok else None},
            "training_roles": ["fitting and configuration trials"],
            "rule": "NLB train and val trials ordered by start time: first floor(0.6 N) fit, next floor(0.2 N) configuration, "
                    "rest held (N = 364)",
            "excluded": {"held_74_assessed": ["trial %d" % i for i in held], "dryad_deposit": ["doi 10.5061/dryad.nk98sf7q7"],
                         "nlb_test_file": ["sub-Han_desc-test"]},
            "extra": {"rule_recomputed_equal": ok, "fit": 218, "configuration": 72, "held": len(held),
                      "trials_outside_nlb_splits": int((~np.isin(tr["split"], ["train", "val"])).sum())},
            "roster_files": [{"file": "area2 force-forecast INPUTS.json (earlier study; fit and configuration trial lists)",
                              "sha256": common.sha256_file(_inputs_record(paths))},
                             {"file": "area2 force-forecast PROTOCOL.json (split rule)",
                              "sha256": common.sha256_file(_inputs_record(paths).parent / "PROTOCOL.json")}]}


def channels(paths):
    kin = [dict(name="hand_%s" % ax, kind="hand_position", units="mm", source_units="cm", value_type="measured",
                rate_hz=1000, axis=ax, vocab=None, row="per-dataset", filtering="author low-pass 100 Hz")
           for ax in ("x", "y")]
    force = [dict(name="handle_F%s" % ax, kind="handle_force", units="N", value_type="measured", rate_hz=1000,
                  axis=ax, vocab=None, row="per-dataset") for ax in ("x", "y", "z")]
    return {"kin": kin, "force": force}


def jobs(paths, units):
    return [(UNIT, None)]


def _count_before(ds, lo, hi, cut, probes):
    """First index in [lo, hi) of a sorted dataset with value >= cut, reading single values (binary search)."""
    a, b = lo, hi
    while a < b:
        m = (a + b) // 2
        v = float(ds[m])
        if v >= cut:
            probes[0] += 1
            b = m
        else:
            a = m + 1
    return a


def process_unit(paths, unit, payload, shared):
    import h5py
    path = paths["area2_file"]
    if Path(path).stat().st_size != BYTES or common.sha256_file(path) != SHA256:
        raise ValueError("area2 file differs from the pinned asset")
    tr = _trials(path)
    rf, rc, rh, n = _split_rule(tr)
    keep = sorted(rf + rc)
    first_held = float(tr["start"][rh].min())
    t_lo = float(tr["start"][keep].min())
    t_hi = float(tr["stop"][keep].max())
    assert t_hi < first_held
    probes = [0]
    with h5py.File(path, "r") as f:
        beh = f["processing/behavior"]
        for k in ("hand_pos", "force"):
            assert float(beh[k]["starting_time"][()]) == 0.0 and float(beh[k]["starting_time"].attrs["rate"]) == FS
        conv = float(beh["hand_pos/data"].attrs["conversion"])
        assert abs(conv - 0.01) < 1e-12  # stored in cm
        r1 = int(np.ceil(t_hi * FS)) + 1
        hand_cm = beh["hand_pos/data"][:r1].astype(np.float64)
        force = beh["force/data"][:r1, :3].astype(np.float64)
        u = f["units"]
        index = u["spike_times_index"][:].astype(np.int64)
        st = u["spike_times"]
        starts = np.r_[0, index[:-1]]
        per_unit = []
        for a, b in zip(starts, index):
            e = _count_before(st, int(a), int(b), t_hi, probes)
            per_unit.append(st[int(a):e].astype(np.float64))
        oi = u["obs_intervals"][:].astype(np.float64)
        oix = u["obs_intervals_index"][:].astype(np.int64)
        obs = [oi[x:y] for x, y in zip(np.r_[0, oix[:-1]], oix)]
        uid = u["id"][:].astype(np.int64)
    hand_mm = hand_cm * 10.0
    unit_ch = {"spikes": [dict(name="%s:u%d" % (UNIT, i), kind="sorted_unit", units="count per step", value_type="measured",
                               region="area 2", row="per-recording") for i in uid]}
    blocks = nc.time_blocks(t_lo, t_hi)
    recs, metas = [], []
    for tid in keep:
        a0, b0 = float(tr["start"][tid]), float(tr["stop"][tid])
        for fold, ba, be in blocks:
            a, b = max(a0, ba), min(b0, be)
            if b - a < common.STEP_S:
                continue
            S = common.n_steps_for(b - a)
            rid = "trial%03d_block%d" % (tid, fold)
            rec = nc.Rec(rid, UNIT, S)
            v, m = nc.spike_counts(per_unit, S, a)
            # observation intervals: a count is present only if its whole step lies inside one interval of the unit
            k0 = a + np.arange(S) * common.STEP_S
            for ui, iv in enumerate(obs):
                ok = np.zeros(S, bool)
                for s_, e_ in iv:
                    ok |= (k0 >= s_) & (k0 + common.STEP_S <= e_)
                m[:, ui, 0] = ok
                v[~ok, ui, 0] = 0
            rec.put("spikes", v, m)
            i0 = int(np.ceil(a * FS - 1e-6))
            i1 = int(np.ceil((a + S * common.STEP_S) * FS - 1e-6))
            lo, hi = common.step_bounds(i1 - i0, FS, i0 / FS - a, S)
            vv, mm = common.kin_features(hand_mm[i0:i1], lo, hi)
            rec.put("kin", vv, mm)
            vv, mm = common.force_features(force[i0:i1], lo, hi)
            rec.put("force", vv, mm)
            recs.append(rec)
            metas.append({"source_files": {"area2_bump_training.nwb (DANDI 000127)": SHA256}, "task": "centre_out_bump",
                          "condition": "bump" if tr["bump"][tid] else "active", "session": "2017-12-07",
                          "inner_fold": fold, "trial": int(tid), "role": "fit" if tid in rf else "configuration",
                          "events": 1 if a == a0 else 0, "duration_s": round(S * common.STEP_S, 4)})
    checks = {"trials_tokenised": len(keep), "trial_pieces": len(recs), "read_until_s": t_hi, "first_held_trial_s": first_held,
              "behaviour_rows_read": r1, "binary_search_probes_at_or_after_cut": probes[0],
              "spikes_read": int(sum(len(x) for x in per_unit)), "units": len(per_unit),
              "nonfinite_rows": {"hand": int((~np.isfinite(hand_cm)).any(axis=1).sum()),
                                 "force": int((~np.isfinite(force)).any(axis=1).sum())}}
    return recs, metas, checks, unit_ch


def file_audit(paths, results):
    r = results[0]
    trials = sorted({m["trial"] for m in r["recordings"]})
    rf, rc, rh, n = _split_rule(_trials(paths["area2_file"]))
    return {"pass": trials == sorted(rf + rc) and not set(trials) & set(rh) and r["checks"]["read_until_s"] < r["checks"]["first_held_trial_s"],
            "trials": len(trials), "held_trials_tokenised": len(set(trials) & set(rh)),
            "read_until_s": r["checks"]["read_until_s"], "first_held_trial_s": r["checks"]["first_held_trial_s"],
            "binary_search_probes_at_or_after_cut": r["checks"]["binary_search_probes_at_or_after_cut"]}


def source_file_summary(results):
    return {"files": 1, "file_sha256": SHA256}


def gates(paths, results, summary):
    c = results[0]["checks"]
    return {
        "Q3_access": {"pass": True, "how": "local training file (size and sha256 against the DANDI asset); only rows and spike "
                      "times before the end of the last configuration trial are read"},
        "Q4_clock": {"pass": True, "how": "one NWB file; spike times and the 1 kHz behaviour series share its clock (starting "
                     "time 0, rate 1000 Hz checked)"},
        "Q5_labels": {"pass": True, "how": "spikes as event counts per sorted unit (masked outside observation intervals); hand "
                      "position in mm (file cm, conversion 0.01 to m checked); handle force in N; all measured",
                      "nonfinite_rows": c["nonfinite_rows"]},
        "Q6_causality": {"pass": True, "author_filtering": "hand position low-pass filtered at 100 Hz by the authors (phase not "
                         "documented)", "our_features": "causal"},
    }
