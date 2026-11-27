"""Katmah et al. multimodal treadmill gait (PhysioNet r0ea-7161 v1.0.0, CC BY 4.0): identifiers 1-40 at
0.5 m/s only.

Three separate acquisitions per person, each its own recording and never paired within a window
(the EMG, IMU and treadmill systems have no verified shared clock; the treadmill was started by hand):
  emg  12-muscle mean-absolute-value envelope shipped by the authors (derived), 16.05 Hz. Delsys
       moving-window outputs are stamped at the window centre (documentation); the first stamp, 62.3 ms,
       equals the output interval, implying a 124.6 ms window with 50% overlap, so each value is treated
       as available half a window (62.3 ms) after its stamp. Tokens: log of the value at the step end.
  imu  Xsens MVN joint angles (ZXY, degrees) at 60 Hz, the only IMU member already extracted locally for
       every person (IMU.tar.gz is not extracted further, as the protocol requires); MVN model output,
       labelled derived. All-zero columns are masked.
  fp   treadmill force plates at 1 kHz (downloaded at P1): Fx, Fy, Fz of the left and right belts (N).
Identifiers 41-52 (consumed) and 53-59 (reserved), and other speeds, are never read.
"""
import csv
import json
from pathlib import Path

import numpy as np

import common

DATASET = "katmah"
IDS = list(range(1, 41))
EMG_HALF_WINDOW_S = 0.0623076923
META = {
    "name": "Katmah et al. multimodal treadmill gait", "doi": "10.13026/r0ea-7161", "species": "human", "sites": 1,
    "derived": True, "paired": False,
    "events_definition": "none annotated in the files used",
    "context": {"dataset": DATASET, "species": "human", "task": "treadmill walking at 0.5 m/s",
                "body_plan": "human biped", "value_flag": "measured (force) and derived (EMG envelope, MVN outputs)"},
    "streams": [
        {"group": "emg", "kind": "emg_envelope", "channels": 12, "rate_hz": 16.05, "units": "V (MAV); log per step",
         "value_type": "derived", "recording": "separate acquisition"},
        {"group": "kin", "kind": "imu_joint_angle", "rate_hz": 60, "units": "degrees",
         "value_type": "derived (Xsens MVN model)", "recording": "separate acquisition"},
        {"group": "force", "kind": "treadmill_force", "channels": "2 belts x 3 axes", "rate_hz": 1000, "units": "N",
         "value_type": "measured", "recording": "separate acquisition"},
    ],
    "notes": ["Only Joint_Angles_ZXY is extracted for every person; identifier 1's extra extracted members (segment "
              "positions, free acceleration) are not used, so all people carry the same IMU channels.",
              "Identifier 24 has no IMU folder and identifiers 8 and 24 have no EMG file at 0.5 m/s; each gives the "
              "acquisitions it has.",
              "Identifier 24 has no role in the knee study's roster (it was left out there only for lacking IMU data); "
              "the committed pooled-encoder allocation assigns identifiers 1-40 to training."],
}


def _cache(paths):
    return Path(paths["katmah_cache"])


def roster(paths):
    f = Path(paths["katmah_roster"])
    s = json.loads(f.read_bytes())
    unit_roles = {}
    for m in s["members"]:
        unit_roles["S%d" % m["subject"]] = m["split"]
    units = ["S%d" % i for i in IDS]
    unlisted = "unlisted in the knee roster (no IMU file); training by the committed pooled-encoder allocation"
    for u in units:
        if u not in unit_roles:
            unit_roles[u] = unlisted  # identifier 24: never assigned to any evaluation group
    excluded = {"knee_test_41_52": sorted(u for u, r in unit_roles.items() if r == "test"),
                "reserved_53_59": ["S%d" % i for i in range(53, 60)]}
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["train", unlisted],
            "rule": "knee-motion roster: train S1-40 (S24 unlisted: no IMU file), test S41-52, S53-59 excluded",
            "excluded": excluded,
            "roster_files": [{"file": "models/knee-motion/sources.json (published knee study)", "sha256": common.sha256_file(f)}]}


def _imu_header(paths):
    d = _cache(paths) / "imu-members" / "IMU_S1_0.5"
    cols = {}
    for name in ("Joint_Angles_ZXY",):
        with open(d / (name + ".csv")) as fh:
            cols[name] = next(csv.reader(fh))[1:]
    return cols


EMG_COLS = ["R TIBIALIS ANTERIOR", "L TIBIALIS ANTERIOR", "R VASTUS LATERALIS", "L VASTUS LATERALIS", "R RECTUS FEMORIS",
            "L RECTUS FEMORIS", "R GASTROCNEMIUS MEDIAL HEAD", "L GASTROCNEMIUS MEDIAL HEAD", "R SEMITENDINOSUS",
            "L SEMITENDINOSUS", "R GASTROCNEMIUS LATERAL HEAD", "L GASTROCNEMIUS LATERAL HEAD"]


def channels(paths):
    from p2 import ChannelSet
    import vocab
    ch = ChannelSet()
    for c in EMG_COLS:
        side, mus = c[0], c[2:].lower()
        ch.add("emg", c, kind="emg_envelope", units="log V (log of MAV envelope at step end)", source_units="V (MAV)",
               rate_hz=16.05, value_type="derived", modality="surface EMG envelope (muscle electrical activity, not a nerve recording)",
               muscle=mus, side=side, vocab=vocab.muscle_key(side, mus), row="shared" if vocab.muscle_key(side, mus) else "dataset")
    cols = _imu_header(paths)
    for c in cols["Joint_Angles_ZXY"]:
        ch.add("kin", "ja:" + c, kind="imu_joint_angle", units="degrees", value_type="derived", rate_hz=60,
               vocab="joint:xsens_zxy:" + c, convention="Xsens MVN ZXY Euler (ISB)")
    for belt in ("left", "right"):
        for ax in "xyz":
            ch.add("force", "%s_F%s" % (belt, ax), kind="treadmill_force", units="N", value_type="measured", rate_hz=1000,
                   frame="treadmill belt axes, vertical +Z, ground reaction", vocab="force:belt_%s:%s" % (belt, ax))
    return ch


ANCHOR = {"kind": "none (joint angles only; no positions in this dataset's tokens)"}
AXIS_NOTE = {"rotation": np.eye(3).tolist(), "note": "Xsens global frame is Z-up; treadmill plates report vertical as Fz"}


def jobs(paths, units):
    return [(u, int(u[1:])) for u in units]


FP_HEADER = ["%d:%s" % (b, c) for b in (1, 2) for c in ("Timestamp", "Sync", "Aux", "Fx", "Fy", "Fz", "Mx", "My", "Mz",
                                                         "COPx", "COPy")]


def _read_csv(path, default_header=None):
    """Returns (header, array, header_present). A file whose first row is numeric gets default_header
    (one force file of the release has no header row; its 22 columns match the documented layout)."""
    with open(path) as fh:
        r = csv.reader(fh)
        first = next(r)
        rows = [row for row in r if row]
    try:
        [float(v) for v in first]
        numeric = True
    except ValueError:
        numeric = False
    if numeric:
        if default_header is None or len(first) != len(default_header):
            raise ValueError("headerless file with an unexpected layout: %s" % path)
        rows = [first] + rows
        head = list(default_header)
    else:
        head = first
    return head, (np.array(rows, dtype=np.float64) if rows else np.zeros((0, len(head)))), not numeric


def process_unit(paths, unit, i, chans):
    cache = _cache(paths)
    recs, metas, checks = [], [], {}
    # EMG envelope
    f = cache / "Dataset" / "EMG_Data" / ("EMG_S%d_0.5.csv" % i)
    if f.exists():
        head, a, _ = _read_csv(f)
        t = a[:, 0] + EMG_HALF_WINDOW_S
        cols = [h.split(":")[0].strip() for h in head[1:]]
        assert cols == EMG_COLS, cols
        S = common.n_steps_for(t[-1] + 1e-9)
        lo, hi = common.step_bounds_times(t, S)
        v, mk = common.envelope_features(a[:, 1:], hi)
        rec = common.Recording("%s_0.5_emg" % unit, unit, S, {})
        rec.put("emg", list(range(12)), v, mk, chans.n("emg"))
        dt = np.diff(a[:, 0])
        recs.append(rec)
        metas.append({"acquisition": "emg_envelope", "source_file": "Dataset/EMG_Data/" + f.name,
                      "sha256": common.sha256_file(f), "task": "treadmill_walk", "condition": "0.5 m/s", "session": 1,
                      "events": 0, "duration_s": round(float(t[-1]), 3)})
        checks["emg"] = {"rows": int(a.shape[0]), "interval_s": [float(dt.min()), float(dt.max())],
                         "first_stamp_s": float(a[0, 0])}
    # IMU (already-extracted members only)
    d = cache / "imu-members" / ("IMU_S%d_0.5" % i)
    if d.is_dir():
        parts, frames, shas = [], None, {}
        for name, pre, scale in (("Joint_Angles_ZXY", "ja:", 1.0),):
            p = d / (name + ".csv")
            head, a, _ = _read_csv(p)
            shas[name] = common.sha256_file(p)
            fr = a[:, 0]
            if frames is None:
                frames = fr
            assert np.array_equal(fr, frames) and np.array_equal(fr, np.arange(len(fr)))
            x = a[:, 1:] * scale
            zero_cols = np.all(x == 0, axis=0)
            x[:, zero_cols] = np.nan
            parts.append(([chans.idx("kin", pre + h) for h in head[1:]], x, int(zero_cols.sum())))
        n = len(frames)
        S = common.n_steps_for(n / 60.0)
        lo, hi = common.step_bounds(n, 60.0, 0.0, S)
        rec = common.Recording("%s_0.5_imu" % unit, unit, S, {})
        for idx, x, _ in parts:
            v, mk = common.kin_features(x, lo, hi)
            rec.put("kin", idx, v, mk, chans.n("kin"))
        recs.append(rec)
        metas.append({"acquisition": "imu", "source_files": {k: v for k, v in shas.items()},
                      "task": "treadmill_walk", "condition": "0.5 m/s", "session": 1, "events": 0,
                      "duration_s": round(n / 60.0, 3)})
        checks["imu"] = {"frames": n, "absent_sensor_columns": sum(z for _, _, z in parts)}
    # force plates (P1 download)
    f = Path(paths["raw"]) / "katmah" / ("FP_S%d_0.5.csv" % i)
    if f.exists():
        head, a, hdr = _read_csv(f, FP_HEADER)
        assert head == FP_HEADER, head

        def col(nm):
            return head.index(nm)
        F = np.stack([a[:, col("%d:F%s" % (b, ax))] for b in (1, 2) for ax in "xyz"], axis=1)
        F1, n1 = common.mask_implausible_force(F[:, :3])
        F2, n2 = common.mask_implausible_force(F[:, 3:])
        F = np.concatenate([F1, F2], axis=1)
        sgn = []
        for b in range(2):
            z = F[:, b * 3 + 2]
            loaded = np.abs(np.nan_to_num(z)) > 50
            s = -1.0 if loaded.sum() > 10 and np.median(z[loaded]) < 0 else 1.0
            F[:, b * 3:(b + 1) * 3] *= s
            sgn.append(s)
        n = a.shape[0]
        S = common.n_steps_for(n / 1000.0)
        lo, hi = common.step_bounds(n, 1000.0, 0.0, S)
        v, mk = common.force_features(F, lo, hi)
        rec = common.Recording("%s_0.5_fp" % unit, unit, S, {})
        rec.put("force", [chans.idx("force", "%s_F%s" % (b, ax)) for b in ("left", "right") for ax in "xyz"], v, mk,
                chans.n("force"))
        recs.append(rec)
        metas.append({"acquisition": "force_plates", "source_file": "Dataset/FP_Data/" + f.name, "sha256": common.sha256_file(f),
                      "task": "treadmill_walk", "condition": "0.5 m/s", "session": 1, "events": 0,
                      "duration_s": round(n / 1000.0, 3)})
        checks["fp"] = {"rows": n, "timestamp_column_all_zero": bool(np.all(a[:, col("1:Timestamp")] == 0)),
                        "sign_applied": sgn, "rate_hz_from_documentation": 1000, "header_row_present": hdr,
                        "samples_above_10kN_masked": [n1, n2]}
    return recs, metas, checks


def file_audit(paths, results):
    bad = []
    for r in results:
        tag = "S%d_" % int(r["unit"][1:])
        for m in r["recordings"]:
            if m["acquisition"] != "imu" and tag not in m["source_file"]:
                bad.append(m["source_file"])
            if "_0.5" not in m.get("source_file", "_0.5"):
                bad.append(m.get("source_file"))
    acq = {}
    for r in results:
        for m in r["recordings"]:
            acq[m["acquisition"]] = acq.get(m["acquisition"], 0) + 1
    return {"pass": not bad and acq.get("emg_envelope") == 38 and acq.get("imu") == 39 and acq.get("force_plates") == 40,
            "acquisitions": acq, "expected": {"emg_envelope": 38, "imu": 39, "force_plates": 40}, "files_outside_unit": bad}


def source_file_summary(results):
    rows = []
    for r in results:
        for m in r["recordings"]:
            if "sha256" in m:
                rows.append((m["source_file"], m["sha256"]))
            for k, v in (m.get("source_files") or {}).items():
                rows.append(("IMU_%s_0.5/%s.csv" % (r["unit"], k), v))
    rows.sort()
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    return {
        "Q3_access": {"pass": True, "how": "EMG CSVs and already-extracted IMU members local (IMU.tar.gz not extracted "
                      "further); force CSVs downloaded per file at P1, each matching the publisher SHA256SUMS digest"},
        "Q4_clock": {"pass": True, "how": "EMG, IMU and force plates enter as separate acquisitions (separate recordings), "
                     "never paired within a window, as the protocol requires; no shared-clock claim is made"},
        "Q5_labels": {"pass": True, "how": "EMG envelope labelled derived surface EMG (not a nerve recording); MVN joint angles "
                      "labelled derived; plate forces measured"},
        "Q6_causality": {"pass": True, "author_filtering": "Delsys MAV envelope stamped at window centre: values shifted to the "
                         "window end (+62.3 ms, inferred window 124.6 ms); Xsens MVN outputs at processing quality 'HD' "
                         "(vendor reprocessing, phase not documented; flagged)",
                         "our_features": "causal on the shifted clock"},
    }
