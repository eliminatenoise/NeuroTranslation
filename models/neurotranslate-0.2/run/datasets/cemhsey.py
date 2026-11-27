"""CEMHSEY GRASP part I v2 (Zenodo 15077957, CC BY 4.0): TRAIN people S1-S3, session 5 task 2 (pinch at
30% MVC), both repetitions on days 1 and 2: 12 MAT files, local, sha256 checked against each receipt.

Per file: data_sEMG 320 x 61,500 at 2,048 Hz nominal, data_force 1 x about 6,030 at 200 Hz nominal on the
session's MVC-normalised scale, MVC in kg. Both start at sample 0 of one file; the authors state
simultaneous acquisition, but the counts imply durations that differ by 0.05-0.3 s, so the pairing is
nominal and flagged (sample offset and drift unverified). DEV S10-S13 files on disk are never opened.
"""
import json
from pathlib import Path

import numpy as np

import common

DATASET = "cemhsey"
META = {
    "name": "CEMHSEY GRASP, version 2, part I", "doi": "10.5281/zenodo.15077957", "species": "human", "sites": 1,
    "derived": False, "paired": "nominal (one file, simultaneous acquisition stated; sample offset unverified, flagged)",
    "events_definition": "none annotated (each recording is one pinch trial)",
    "context": {"dataset": DATASET, "species": "human", "task": "isometric two-finger pinch at 30% MVC",
                "body_plan": "human forearm and hand", "value_flag": "measured"},
    "streams": [
        {"group": "emg", "kind": "hd_emg", "channels": 320, "rate_hz": 2048, "units": "source units as stored; log RMS per step",
         "value_type": "measured", "rows": "learned per recording; electrode positions not verified here"},
        {"group": "force", "kind": "pinch_force", "channels": 1, "rate_hz": 200, "units": "fraction of MVC (dimensionless)",
         "value_type": "measured (scaled by the session MVC)"},
    ],
    "notes": ["Force and EMG sample counts imply different durations; tokens use the shorter span and the nominal clocks."],
}


def _src(paths):
    return Path(paths["cemhsey_source"])


def roster(paths):
    f = _src(paths) / "TRAIN-MANIFEST-R2.json"
    g = _src(paths) / "DEV-MANIFEST-R2.json"
    m = json.loads(f.read_bytes())
    dv = json.loads(g.read_bytes())
    assert m["stage"] == "TRAIN" and dv["stage"] == "DEV"
    def subj(e):
        return (e.get("member_path") or e["zip_row"]["member_path"]).split("/")[0]
    train = sorted({subj(e) for e in m["entries"]})
    dev = sorted({subj(e) for e in dv["entries"]})
    unit_roles = {u: "TRAIN" for u in train}
    unit_roles.update({u: "DEV" for u in dev})
    return {"units": train, "unit_roles": unit_roles, "training_roles": ["TRAIN"], "rule": m["scope"],
            "excluded": {"DEV": dev},
            "roster_files": [{"file": "cemhsey TRAIN-MANIFEST-R2.json", "sha256": common.sha256_file(f)},
                             {"file": "cemhsey DEV-MANIFEST-R2.json", "sha256": common.sha256_file(g)}]}


def channels(paths):
    from p2 import ChannelSet
    ch = ChannelSet()
    for i in range(320):
        ch.add("emg", "e%03d" % (i + 1), kind="hd_emg", units="log of source units (log RMS per 20 ms step)",
               rate_hz=2048, value_type="measured", modality="surface EMG (muscle electrical activity, not a nerve recording)",
               index=i + 1, vocab=None, row="per-recording")
    ch.add("force", "pinch", kind="pinch_force", units="fraction of MVC", value_type="measured", rate_hz=200,
           vocab="force:pinch:thumb_index")
    return ch


def jobs(paths, units):
    m = json.loads((_src(paths) / "TRAIN-MANIFEST-R2.json").read_bytes())
    paths_ = sorted((e.get("member_path") or e["zip_row"]["member_path"]) for e in m["entries"])
    return [(u, [p for p in paths_ if p.split("/")[0] == u]) for u in units]


def _local(paths, member):
    base = member.split("/")[-1][:-4]
    root = _src(paths) / "private-mat"
    d = root / base
    if d.is_dir():
        rc = json.loads((d / "receipt.json").read_text())
        return d / (base + ".mat"), rc
    rc = json.loads((root / (base + ".mat.receipt.json")).read_text())
    return root / (base + ".mat"), rc


def process_unit(paths, unit, members, chans):
    from scipy.io import loadmat
    recs, metas, checks = [], [], {}
    for mem in members:
        f, rc = _local(paths, mem)
        assert rc["zip_row"]["member_path"] == mem and mem.startswith(unit + "/")
        digest = common.sha256_file(f)
        if digest != rc["integrity"]["mat_sha256"]:
            raise ValueError("sha256 mismatch " + mem)
        d = loadmat(f, variable_names=["data_sEMG", "data_force", "MVC"])
        emg = np.asarray(d["data_sEMG"], np.float64).T
        frc = np.asarray(d["data_force"], np.float64).reshape(-1, 1)
        dur_e, dur_f = emg.shape[0] / 2048.0, frc.shape[0] / 200.0
        S = common.n_steps_for(min(dur_e, dur_f))
        base = mem.split("/")[-1][:-4]
        rec = common.Recording(base, unit, S, {})
        lo, hi = common.step_bounds(emg.shape[0], 2048.0, 0.0, S)
        v, mk = common.emg_features(emg, 2048.0, lo, hi)
        rec.put("emg", list(range(320)), v, mk, chans.n("emg"))
        lo, hi = common.step_bounds(frc.shape[0], 200.0, 0.0, S)
        v, mk = common.force_features(frc, lo, hi)
        rec.put("force", [0], v, mk, chans.n("force"))
        day = int(base.split("_Day")[1].split("_")[0])
        rep = int(base.split("_Trial")[1])
        recs.append(rec)
        metas.append({"source_member": mem, "member_sha256": digest, "task": "pinch_30pct_mvc", "condition": None,
                      "session": day, "repetition": rep, "events": 0, "duration_s": round(min(dur_e, dur_f), 4)})
        checks[base] = {"emg_samples": emg.shape[0], "force_samples": frc.shape[0], "emg_seconds": dur_e,
                        "force_seconds": dur_f, "duration_difference_s": round(dur_f - dur_e, 4),
                        "nonfinite_emg": int((~np.isfinite(emg)).sum()), "nonfinite_force": int((~np.isfinite(frc)).sum())}
    return recs, metas, checks


def file_audit(paths, results):
    n = sum(len(r["recordings"]) for r in results)
    bad = [m["source_member"] for r in results for m in r["recordings"] if not m["source_member"].startswith(r["unit"] + "/")]
    return {"pass": n == 12 and not bad, "recordings": n, "expected_from_protocol": 12, "members_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((m["source_member"], m["member_sha256"]) for r in results for m in r["recordings"])
    return {"files": len(rows), "member_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    allck = [c for r in results for c in r["checks"].values()]
    return {
        "Q3_access": {"pass": True, "how": "local selected members fetched earlier by ranged reads; sha256 checked against "
                      "each receipt; DEV files not opened"},
        "Q4_clock": {"pass": True, "how": "one MAT file per trial, simultaneous acquisition stated by the authors; paired on "
                     "nominal clocks from sample 0 (protocol: sample offset unverified, flagged)",
                     "flag": "duration difference force minus EMG per recording (s): %s" % sorted({c["duration_difference_s"] for c in allck})},
        "Q5_labels": {"pass": True, "how": "HD-EMG measured surface EMG (not a nerve recording); pinch force measured on the "
                      "MVC-normalised scale"},
        "Q6_causality": {"pass": True, "author_filtering": "not documented for the released arrays; flagged unknown",
                         "our_features": "causal"},
    }
