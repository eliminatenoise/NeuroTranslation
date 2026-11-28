"""Hyser 2.0.0 random finger task (PhysioNet hd-semg, ODC-By 1.0): the 12 TRAIN people.

Only subjectNN_session{1,2} folders of TRAIN people are read (DEV folders on disk are never opened;
the final 4 were never fetched). Each file's sha256 is checked against the source manifest before it
is read. Per trial: 256-channel HD-EMG (four 8 x 8 grids) at 2,048 Hz and five finger force
transducers at 100 Hz, 25 s each, started by one trigger (nominal clocks k/2048 s and j/100 s).
"""
import json
from pathlib import Path

import numpy as np

import common

DATASET = "hyser"
GRIDS = {"ED": "extensor distal", "EP": "extensor proximal", "FD": "flexor distal", "FP": "flexor proximal"}
FINGERS = ["thumb", "index", "middle", "ring", "little"]
META = {
    "name": "Hyser high-density surface EMG, random finger task, version 2.0.0", "doi": "10.13026/hxan-pe94",
    "species": "human", "sites": 1, "derived": False, "paired": True,
    "events_definition": "none annotated (each recording is one 25 s trial)",
    "context": {"dataset": DATASET, "species": "human", "task": "isometric finger contractions, random combinations",
                "body_plan": "human forearm and hand", "value_flag": "measured"},
    "streams": [
        {"group": "emg", "kind": "hd_emg", "channels": 256, "rate_hz": 2048, "units": "V (source); log RMS per step",
         "value_type": "measured", "rows": "learned per recording, grid position recorded (grid, row, column)"},
        {"group": "force", "kind": "finger_force", "channels": 5, "rate_hz": 100,
         "units": "V (transducer output, no verified conversion to newtons)", "value_type": "measured"},
    ],
    "notes": ["Finger force is uncalibrated transducer voltage; its filtering history in the release is unresolved."],
}


def _src(paths):
    return Path(paths["hyser_source"])


def _manifest(paths):
    return json.loads((_src(paths) / "SOURCE-MANIFEST.json").read_bytes())


def roster(paths):
    m = _manifest(paths)
    unit_roles = {}
    for role, ids in m["role_participants"].items():
        for i in ids:
            unit_roles[i] = role
    units = sorted(m["role_participants"]["TRAIN"])
    excluded = {k: sorted(v) for k, v in m["role_participants"].items() if k != "TRAIN"}
    excluded["FINAL_never_fetched"] = []
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["TRAIN"], "rule": m["split_algorithm"],
            "excluded": excluded,
            "roster_files": [{"file": "hyser SOURCE-MANIFEST.json (earlier source custody)",
                              "sha256": common.sha256_file(_src(paths) / "SOURCE-MANIFEST.json")}]}


def channels(paths):
    from p2 import ChannelSet
    m = _manifest(paths)
    ch = ChannelSet()
    for name in m["raw_channel_order"]:
        g, r, c = name.split("-")
        ch.add("emg", name, kind="hd_emg", units="log V (log RMS per 20 ms step)", source_units="V", rate_hz=2048,
               value_type="measured", modality="surface EMG (muscle electrical activity, not a nerve recording)",
               grid=g, grid_name=GRIDS[g], grid_row=int(r), grid_col=int(c), vocab=None, row="per-recording")
    for f in FINGERS:
        ch.add("force", "finger_" + f, kind="finger_force", units="V (uncalibrated transducer)", value_type="measured",
               rate_hz=100, vocab="force:finger:" + f)
    return ch


def read_wfdb(stem):
    hea = Path(str(stem) + ".hea").read_text().strip().splitlines()
    name, nsig, fs, n = hea[0].split()[:4]
    nsig, fs, n = int(nsig), float(fs), int(n)
    gains, base, labels = [], [], []
    for line in hea[1:1 + nsig]:
        p = line.split()
        assert p[1] == "16"
        g = p[2].split("/")[0]
        gains.append(float(g.split("(")[0]))
        base.append(int(g.split("(")[1].rstrip(")")) if "(" in g else 0)
        labels.append(p[-1])
    raw = np.fromfile(str(stem) + ".dat", dtype="<i2")
    assert raw.size == nsig * n
    raw = raw.reshape(n, nsig)
    x = (raw.astype(np.float64) - np.array(base)) / np.array(gains)
    x[raw == -32768] = np.nan
    return x, fs, labels


def jobs(paths, units):
    out = []
    for u in units:
        num = int(u[1:])
        out.append((u, [(s, k, "random_dataset/subject%02d_session%d/random_%%s_sample%d" % (num, s, k))
                        for s in (1, 2) for k in range(1, 6)]))
    return out


def process_unit(paths, unit, items, chans):
    m = _manifest(paths)
    root = _src(paths) / "private-cache"
    recs, metas, checks = [], [], {}
    emg_idx = list(range(chans.n("emg")))
    f_idx = [chans.idx("force", "finger_" + f) for f in FINGERS]
    for s, k, pat in items:
        files = {}
        for kind in ("raw", "force"):
            for ext in (".hea", ".dat"):
                rel = pat % kind + ext
                d = common.sha256_file(root / rel)
                if d != m["files"][rel]["sha256"]:
                    raise ValueError("sha256 mismatch " + rel)
                files[rel] = d
        emg, fe, el = read_wfdb(root / (pat % "raw"))
        frc, ff, fl = read_wfdb(root / (pat % "force"))
        assert el == m["raw_channel_order"] and fl == FINGERS
        dur_e, dur_f = emg.shape[0] / fe, frc.shape[0] / ff
        S = common.n_steps_for(min(dur_e, dur_f))
        rid = "%s_s%d_t%d" % (unit, s, k)
        rec = common.Recording(rid, unit, S, {})
        lo, hi = common.step_bounds(emg.shape[0], fe, 0.0, S)
        v, mk = common.emg_features(emg, fe, lo, hi)
        rec.put("emg", emg_idx, v, mk, chans.n("emg"))
        lo, hi = common.step_bounds(frc.shape[0], ff, 0.0, S)
        v, mk = common.force_features(frc, lo, hi)
        rec.put("force", f_idx, v, mk, chans.n("force"))
        recs.append(rec)
        metas.append({"source_files": files, "task": "random_finger", "condition": None, "session": s, "trial": k,
                      "events": 0, "duration_s": round(min(dur_e, dur_f), 4)})
        checks[rid] = {"emg_seconds": dur_e, "force_seconds": dur_f, "durations_equal": abs(dur_e - dur_f) < 1e-9,
                       "emg_missing_samples": int(np.isnan(emg).sum()), "force_missing_samples": int(np.isnan(frc).sum())}
    return recs, metas, checks


def file_audit(paths, results):
    bad = []
    for r in results:
        num = "subject%02d_" % int(r["unit"][1:])
        for mta in r["recordings"]:
            bad += [f for f in mta["source_files"] if num not in f]
    n = sum(len(r["recordings"]) for r in results)
    return {"pass": not bad and n == 120, "recordings": n, "expected_from_protocol": 120, "files_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((f, d) for r in results for m in r["recordings"] for f, d in m["source_files"].items())
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    allck = [c for r in results for c in r["checks"].values()]
    return {
        "Q3_access": {"pass": True, "how": "local TRAIN files; sha256 of every file checked against the source manifest"},
        "Q4_clock": {"pass": all(c["durations_equal"] for c in allck),
                     "how": "one trigger at task onset starts both systems (authors); nominal clocks k/2048 s and j/100 s; "
                     "both streams last exactly 25 s in every training recording", "recordings_checked": len(allck),
                     "flag": "sample-level trigger skew and drift are not independently established"},
        "Q5_labels": {"pass": True, "how": "HD-EMG in volts (log RMS), measured, surface EMG of forearm muscles (not a nerve "
                      "recording); finger force as uncalibrated transducer volts, measured"},
        "Q6_causality": {"pass": True, "author_filtering": "force filtering history of the release unresolved (authors "
                         "describe zero-phase 10 Hz low-pass for their benchmark, applied after loading); flagged",
                         "our_features": "causal"},
    }
