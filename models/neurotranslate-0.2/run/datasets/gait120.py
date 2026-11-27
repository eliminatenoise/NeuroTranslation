"""Gait120 (figshare 27677016 v1, CC BY 4.0): the 66 development people of the chair-rise roster.

Per person: the local raw.mat (12 right-leg EMG channels at 2 kHz per trial, MATLAB table objects read
with mat-io), the local SitToStand marker and plate files, and the members fetched at P1 (marker TRC
for the other tasks and the static trial, OpenSim joint-angle MOT except SitToStand, plate MOT for
LevelWalking and StandToSit). One recording per trial on the trial's frame clock: frame f is at
(f - 1) / 100 s; the trial's EMG covers frames TotalFrame[0]..TotalFrame[1] (20 samples per frame) and
is the recording origin; the author step segments (TargetFrame, consecutive and sharing one boundary
frame) are placed on that clock, so overlapping step files are never counted twice. Plate MOT samples
lie on the EMG's 2 kHz grid. The static trial is a markers-only recording.
Pairing check on every training trial (the chair-rise study's rule): TRC frame numbers equal the step's
TargetFrame range and times equal (f - 1) / 100; joint-angle times equal the TRC times; plate times start
at the step's first TRC time on a 2 kHz grid; EMG length equals (TotalFrame[1] - TotalFrame[0] + 1) x 20.
S001-S010 (evaluation set E1) and the validation and confirmation people are never opened.
"""
import json
from pathlib import Path

import numpy as np

import common
import c3d_reader

DATASET = "gait120"
TASKS = ["LevelWalking", "StairAscent", "StairDescent", "SlopeAscent", "SlopeDescent", "SitToStand", "StandToSit"]
MARKERS = ["LFHD", "RFHD", "LBHD", "RBHD", "C7", "T10", "CLAV", "STRN", "RBAK", "LSHO", "LUPA", "LELB", "LFRM", "LWRA",
           "LWRB", "LFIN", "RSHO", "RUPA", "RELB", "RFRM", "RWRA", "RWRB", "RFIN", "LASI", "RASI", "LPSI", "RPSI", "LTHI",
           "LKNE", "LTIB", "LANK", "LHEE", "LTOE", "RTHI", "RKNE", "RTIB", "RANK", "RHEE", "RTOE"]
EMG = ["Vastus Lateralis", "Rectus Femoris", "Vastus Medialis", "Tibialis Anterior", "Biceps Femoris", "Semitendinosus",
       "Gastrocnemuis Medialis", "Gastrocnemius Lateralis", "Soleus Medialis", "Soleus Lateralis", "Peroneus Longus",
       "Peroneus Brevis"]
R_MAP = c3d_reader.rotation_for(1, 1.0)  # OpenSim-style Y-up files: (x, y, z) -> (x, -z, y); re-checked per file
ANCHOR = {"kind": "pelvis", "markers": ["LASI", "RASI", "LPSI", "RPSI"]}
AXIS_NOTE = {"rotation": R_MAP.tolist(), "note": "TRC and plate MOT use +Y vertical; rotated so that +Z is vertical; "
             "re-checked on every trial from pelvis and foot markers. Joint-angle coordinates are kept as recorded."}
META = {
    "name": "Comprehensive Human Locomotion and Electromyography Dataset: Gait120", "doi": "10.6084/m9.figshare.27677016.v1",
    "species": "human", "sites": 1, "derived": True, "paired": True,
    "events_definition": "author step segments (TargetFrame ranges in raw.mat), one per marker step file",
    "context": {"dataset": DATASET, "species": "human", "task": "7 daily locomotion tasks and a static trial",
                "body_plan": "human biped", "value_flag": "measured (markers, EMG, plates) and derived (joint angles)"},
    "streams": [
        {"group": "kin", "kind": "marker", "channels": "39 Plug-in-Gait markers x 3 axes", "rate_hz": 100, "units": "mm",
         "value_type": "measured", "filtering": "author-filtered (file paths name 'Filtered_trc')"},
        {"group": "kin", "kind": "joint_angle", "channels": "OpenSim coordinates", "rate_hz": 100,
         "units": "degrees (rotations), m (pelvis translations)", "value_type": "derived (OpenSim inverse kinematics)"},
        {"group": "emg", "kind": "surface_emg", "channels": 12, "rate_hz": 2000, "units": "source units; log RMS per step",
         "value_type": "measured", "side": "right leg"},
        {"group": "force", "kind": "plate_force", "channels": "2 plates x 3 axes", "rate_hz": 2000, "units": "N",
         "value_type": "measured", "tasks": "LevelWalking, SitToStand, StandToSit"},
    ],
    "notes": ["Joint angles of SitToStand were not part of the P1 member list, so SitToStand trials carry markers, "
              "EMG and plates only.",
              "EMG spans each trial's TotalFrame range, which starts before and ends after the marker steps; steps "
              "with EMG only are kept (marker and plate channels masked there)."],
}


def _g(paths):
    return Path(paths["gait120_intake"])


def roster(paths):
    f = _g(paths) / "ROSTER.json"
    r = json.loads(f.read_bytes())
    unit_roles = {}
    for role, ids in r["roles"].items():
        for i in ids:
            unit_roles[i] = role
    units = sorted(r["roles"]["development"])
    excluded = {k: sorted(v) for k, v in r["roles"].items() if k != "development"}
    excluded["E1_S001_S010"] = ["S%03d" % i for i in range(1, 11)]
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["development"], "rule": r["salt"],
            "excluded": excluded,
            "roster_files": [{"file": "Gait120 chair-rise ROSTER.json (earlier study)", "sha256": common.sha256_file(f)}]}


def _ja_columns(paths):
    root = Path(paths["raw"]) / "gait120" / "members"
    for p in sorted(root.glob("S*/JointAngle/LevelWalking/Trial01/step01.mot")):
        return _read_mot(p)[0]
    raise FileNotFoundError("no joint-angle member found")


def channels(paths):
    from p2 import ChannelSet
    from datasets import c3d_common
    ch = ChannelSet()
    c3d_common.add_marker_channels(ch, MARKERS, "pig", DATASET)
    for c in _ja_columns(paths)[1:]:
        trans = c in ("pelvis_tx", "pelvis_ty", "pelvis_tz")
        ch.add("kin", "ja:" + c, kind="joint_angle", units="m" if trans else "degrees", value_type="derived",
               rate_hz=100, vocab="joint:opensim:" + c, convention="OpenSim model coordinates (author inverse kinematics)")
    c3d_common.add_emg_channels(ch, [(m, "R", m) for m in EMG], DATASET, 2000)
    c3d_common.add_plate_channels(ch, 2)
    return ch


def _read_trc(path):
    lines = Path(path).read_text().splitlines()
    names = [n for n in lines[3].split("\t")[2:] if n.strip()]
    rows = [l.split("\t") for l in lines[5:] if l.strip()]
    a = np.array([[float(v) if v.strip() else np.nan for v in r[:2 + 3 * len(names)]] for r in rows])
    return names, a


def _read_mot(path):
    lines = Path(path).read_text().splitlines()
    k = next(i for i, l in enumerate(lines) if l.strip().lower() == "endheader")
    head = [h for h in lines[k + 1].split("\t") if h.strip()]
    if len(head) == 1:
        head = lines[k + 1].split()
    rows = [l.split() for l in lines[k + 2:] if l.strip()]
    a = np.array(rows, dtype=np.float64)
    return head, a


def jobs(paths, units):
    return [(u, None) for u in units]


def process_unit(paths, unit, _, chans):
    import matio
    g = _g(paths)
    loc = g / "archives" / "development" / unit
    members = json.loads((loc / "MEMBERS.json").read_bytes())["members"]
    raw_digest = common.sha256_file(loc / "raw.mat")
    if raw_digest != members["raw.mat"]["sha256"]:
        raise ValueError("raw.mat differs from its transfer record for " + unit)
    mroot = Path(paths["raw"]) / "gait120" / "members" / unit
    mat = matio.load_from_mat(str(loc / "raw.mat"))
    assert int(np.ravel(mat["EMGs_info"].flat[0]["fs"])[0]) == 2000
    assert int(np.ravel(mat["Markers_info"].flat[0]["fs"])[0]) == 100
    nK = chans.n("kin")
    mk_idx = {n: [chans.idx("kin", "%s_%s" % (n, a)) for a in "xyz"] for n in MARKERS}
    emg_idx = [chans.idx("emg", m) for m in EMG]
    pl_idx = [chans.idx("force", "plate%d_%s" % (p, a)) for p in (1, 2) for a in "xyz"]
    recs, metas, checks = [], [], {}
    files_read = {"raw.mat": raw_digest}
    n_steps_total = 0

    def put_markers(rec, names, xyz_frames, lo, hi):
        for j, n in enumerate(names):
            if n in mk_idx:
                v, m = common.kin_features(xyz_frames[:, j, :], lo, hi)
                rec.put("kin", mk_idx[n], v, m, nK)

    for task in TASKS:
        ts = mat[task].flat[0]
        for tn in [n for n in ts.dtype.names if n.startswith("Trial")]:
            cell = ts[tn]
            if not getattr(cell, "size", 0):
                continue
            tr = cell.flat[0]
            if not hasattr(tr, "dtype") or tr.dtype.names is None or "EMGs_raw" not in tr.dtype.names:
                continue
            k = int(tn[5:])
            start, end = [int(v) for v in np.ravel(tr["TotalFrame"])]
            emg_df = tr["EMGs_raw"]
            assert list(emg_df.columns) == EMG, list(emg_df.columns)
            emg = emg_df.to_numpy(dtype=np.float64)
            nF = end - start + 1
            ck = {"total_frames": [start, end], "emg_samples": int(emg.shape[0]),
                  "emg_length_equals_frames_x_20": emg.shape[0] == nF * 20}
            steps = [(s, [int(v) for v in np.ravel(tr[s].flat[0]["TargetFrame"])]) for s in tr.dtype.names if s.startswith("Step")]
            S = common.n_steps_for(nF / 100.0)
            rid = "%s_%s_T%02d" % (unit, task, k)
            rec = common.Recording(rid, unit, S, {})
            xyz = np.full((nF, len(MARKERS), 3), np.nan)
            ja = None
            frc = np.full((nF * 20, 6), np.nan)
            step_rows, vert = [], []
            for sname, (a, b) in steps:
                si = int(sname[4:])
                row = {"step": si, "target_frames": [a, b]}
                if task == "SitToStand":
                    key = "trial%02d" % k
                    trc_p = loc / (key + ".trc") if (key + ".trc") in members else None
                    mot_p = loc / (key + ".mot") if (key + ".mot") in members else None
                    ja_p = None
                    if trc_p is not None:
                        assert members[key + ".trc"]["source_name"] == "%s/MotionCapture/SitToStand/TRC/Trial%02d/Step%02d.trc" % (unit, k, si)
                        d = common.sha256_file(trc_p)
                        assert d == members[key + ".trc"]["sha256"]
                        files_read[members[key + ".trc"]["source_name"]] = d
                    if mot_p is not None:
                        d = common.sha256_file(mot_p)
                        assert d == members[key + ".mot"]["sha256"]
                        files_read[members[key + ".mot"]["source_name"]] = d
                else:
                    trc_p = mroot / "MotionCapture" / task / "TRC" / ("Trial%02d" % k) / ("Step%02d.trc" % si)
                    ja_p = mroot / "JointAngle" / task / ("Trial%02d" % k) / ("step%02d.mot" % si)
                    mot_p = mroot / "MotionCapture" / task / "MOT" / ("Trial%02d" % k) / ("Step%02d.mot" % si)
                    for p in (trc_p, ja_p, mot_p):
                        if p.exists():
                            files_read[str(p.relative_to(mroot.parent))] = common.sha256_file(p)
                    trc_p = trc_p if trc_p.exists() else None
                    ja_p = ja_p if ja_p.exists() else None
                    mot_p = mot_p if mot_p.exists() else None
                if trc_p is None:
                    row["trc"] = "missing"
                    step_rows.append(row)
                    continue
                names, arr = _read_trc(trc_p)
                fr = arr[:, 0].astype(int)
                tt = arr[:, 1]
                row["trc_frames_equal_target"] = bool(fr[0] == a and fr[-1] == b and np.array_equal(fr, np.arange(a, b + 1)))
                row["trc_time_equals_frame_clock"] = bool(np.allclose(tt, (fr - 1) / 100.0, atol=1e-6))
                row["trc_inside_total_frames"] = bool(a >= start and b <= end)
                pts = arr[:, 2:2 + 3 * len(names)].reshape(len(fr), len(names), 3)
                am = c3d_reader.axis_map_from_points(names, pts, ANCHOR["markers"], ["LHEE", "RHEE", "LTOE", "RTOE"])
                if am is not None:
                    vert.append(bool(np.allclose(am[0], R_MAP)))
                pts = pts @ R_MAP.T
                ii = fr - start
                ok = (ii >= 0) & (ii < nF)
                order = [MARKERS.index(n) if n in MARKERS else -1 for n in names]
                for j, o in enumerate(order):
                    if o >= 0:
                        prev = xyz[ii[ok], o, :]
                        new = pts[ok, j, :]
                        both = np.isfinite(prev).all(axis=1) & np.isfinite(new).all(axis=1)
                        if both.any():
                            row.setdefault("shared_frame_max_diff_mm", 0.0)
                            row["shared_frame_max_diff_mm"] = max(row["shared_frame_max_diff_mm"],
                                                                  float(np.abs(prev[both] - new[both]).max()))
                        xyz[ii[ok], o, :] = np.where(np.isfinite(prev), prev, new)
                if ja_p is not None:
                    head, ja_a = _read_mot(ja_p)
                    row["ja_time_equals_trc_time"] = bool(ja_a.shape[0] == len(tt) and np.allclose(ja_a[:, 0], tt, atol=1e-6))
                    if ja is None:
                        ja = np.full((nF, len(head) - 1), np.nan)
                        ja_head = head
                    assert head == ja_head
                    jf = np.rint(ja_a[:, 0] * 100).astype(int) + 1 - start
                    okj = (jf >= 0) & (jf < nF)
                    ja[jf[okj]] = np.where(np.isfinite(ja[jf[okj]]), ja[jf[okj]], ja_a[okj, 1:])
                if mot_p is not None:
                    head, fa = _read_mot(mot_p)
                    plates_here = [p for p in (1, 2) if "ground_force%d_vx" % p in head]
                    row["plates_in_file"] = plates_here
                    ft = fa[:, 0]
                    row["plate_starts_at_trc_time"] = bool(abs(ft[0] - tt[0]) < 1e-6)
                    row["plate_on_2khz_grid"] = bool(np.allclose(np.diff(ft), 0.0005, atol=1e-6))
                    kk = np.rint((ft - (start - 1) / 100.0) * 2000).astype(int)
                    okf = (kk >= 0) & (kk < nF * 20)
                    for p in plates_here:
                        cols = [head.index("ground_force%d_v%s" % (p, ax)) for ax in "xyz"]
                        F, nbad = common.mask_implausible_force(fa[:, cols] @ R_MAP.T)
                        if nbad:
                            # a plate file with any sample above 10 kN is corrupt throughout (zeros and
                            # values up to 1e36 in the published files): the whole plate of that file is masked
                            row.setdefault("plate_samples_above_10kN_masked", {})[str(p)] = nbad
                            F[:] = np.nan
                        sl = slice((p - 1) * 3, p * 3)
                        cur = frc[kk[okf], sl]
                        frc[kk[okf], sl] = np.where(np.isfinite(cur), cur, F[okf])
                step_rows.append(row)
            n_steps_total += len(steps)
            # tokens
            lo, hi = common.step_bounds(nF, 100.0, 0.0, S)
            put_markers(rec, MARKERS, xyz, lo, hi)
            if ja is not None:
                idx = [chans.idx("kin", "ja:" + c) for c in ja_head[1:]]
                v, m = common.kin_features(ja, lo, hi)
                rec.put("kin", idx, v, m, nK)
            elo, ehi = common.step_bounds(emg.shape[0], 2000.0, 0.0, S)
            v, m = common.emg_features(emg, 2000.0, elo, ehi)
            rec.put("emg", emg_idx, v, m, chans.n("emg"))
            if np.isfinite(frc).any():
                for p in range(2):
                    z = frc[:, p * 3 + 2]
                    loaded = np.abs(z) > 50
                    if loaded.sum() > 10 and np.nanmedian(z[loaded]) < 0:
                        frc[:, p * 3:(p + 1) * 3] *= -1
                        ck.setdefault("plate_sign_flipped", []).append(p + 1)
                v, m = common.force_features(frc, elo, ehi)
                rec.put("force", pl_idx, v, m, chans.n("force"))
            ck["steps"] = step_rows
            ck["vertical_axis_rechecks"] = vert
            recs.append(rec)
            metas.append({"task": task, "trial": k, "condition": None, "session": 1, "events": len(steps),
                          "duration_s": round(nF / 100.0, 3), "total_frames": [start, end],
                          "joint_angles": ja is not None, "plates": bool(np.isfinite(frc).any())})
            checks[rid] = ck
    # static trial (markers only)
    st = [p for p in (mroot / "MotionCapture" / "Static" / "TRC").glob("*.trc")] if (mroot / "MotionCapture" / "Static" / "TRC").is_dir() else []
    assert len(st) <= 1, st  # the archive names it Trial01.trc or trial01.trc
    st = st[0] if st else None
    if st is not None:
        files_read[str(st.relative_to(mroot.parent))] = common.sha256_file(st)
        names, arr = _read_trc(st)
        fr = arr[:, 0].astype(int)
        pts = arr[:, 2:2 + 3 * len(names)].reshape(len(fr), len(names), 3) @ R_MAP.T
        nF = len(fr)
        S = common.n_steps_for(nF / 100.0)
        rec = common.Recording("%s_Static" % unit, unit, S, {})
        lo, hi = common.step_bounds(nF, 100.0, 0.0, S)
        put_markers(rec, names, pts, lo, hi)
        recs.append(rec)
        metas.append({"task": "Static", "trial": 1, "condition": None, "session": 1, "events": 0,
                      "duration_s": round(nF / 100.0, 3)})
        checks["%s_Static" % unit] = {"frames": nF, "contiguous": bool(np.array_equal(fr, np.arange(fr[0], fr[0] + nF)))}
    metas[0]["files_read"] = files_read
    return recs, metas, checks


def file_audit(paths, results):
    bad, n_trc = [], 0
    for r in results:
        files = r["recordings"][0].get("files_read", {}) if r["recordings"] else {}
        for f in files:
            if f != "raw.mat" and not f.startswith(r["unit"] + "/"):
                bad.append(f)
            if f.endswith(".trc") and "/Static/" not in f:
                n_trc += 1
    return {"pass": not bad, "dynamic_trc_files_read": n_trc, "protocol_count_marker_trial_steps": 3761,
            "files_outside_unit": bad}


def source_file_summary(results):
    rows = []
    for r in results:
        if r["recordings"]:
            for f, d in r["recordings"][0].get("files_read", {}).items():
                rows.append((r["unit"] + "/raw.mat" if f == "raw.mat" else f, d))
    rows.sort()
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    steps = [s for r in results for c in r["checks"].values() for s in c.get("steps", [])]
    trials = [c for r in results for c in r["checks"].values() if "emg_samples" in c]

    def allok(key):
        vals = [s[key] for s in steps if key in s]
        return all(vals), len(vals)
    a1, n1 = allok("trc_frames_equal_target")
    a2, n2 = allok("trc_time_equals_frame_clock")
    a3, n3 = allok("ja_time_equals_trc_time")
    a4, n4 = allok("plate_starts_at_trc_time")
    a5, n5 = allok("plate_on_2khz_grid")
    a6, n6 = allok("trc_inside_total_frames")
    e_ok = all(c["emg_length_equals_frames_x_20"] for c in trials)
    vert = [v for c in trials for v in c.get("vertical_axis_rechecks", [])]
    missing = sum(1 for s in steps if s.get("trc") == "missing")
    implaus = {}
    for r in results:
        for rid, c in r["checks"].items():
            for s in c.get("steps", []):
                for p, n in (s.get("plate_samples_above_10kN_masked") or {}).items():
                    implaus["%s step %d plate %s" % (rid, s["step"], p)] = n
    return {
        "Q3_access": {"pass": True, "how": "raw.mat and SitToStand members local (sha256 checked against their transfer "
                      "records); other members fetched at P1 by ranged reads covering only development people's wanted "
                      "members, each CRC-32 checked"},
        "Q4_clock": {"pass": a1 and a2 and a3 and a4 and a5 and a6 and e_ok,
                     "how": "trial timestamp and frame-identifier match of the chair-rise study, on every training trial",
                     "trc_frames_equal_target": [a1, n1], "trc_time_equals_frame_clock": [a2, n2],
                     "joint_angle_time_equals_trc": [a3, n3], "plate_starts_at_trc_time": [a4, n4],
                     "plate_on_2khz_grid": [a5, n5], "steps_inside_emg_span": [a6, n6],
                     "emg_length_equals_frames_x_20": [e_ok, len(trials)], "step_files_missing": missing,
                     "vertical_axis_rechecks_disagreeing": sum(1 for v in vert if not v)},
        "Q5_labels": {"pass": True, "how": "markers mm (measured), OpenSim coordinates degrees or m (derived), EMG measured "
                      "surface EMG of right-leg muscles (not a nerve recording), plate forces N (measured)",
                      "plate_files_masked_whole_for_samples_above_10kN": implaus},
        "Q6_causality": {"pass": True, "author_filtering": "marker files are the authors' filtered TRC exports; joint angles "
                         "come from the authors' inverse kinematics on them; filter phase not documented in the deposit",
                         "our_features": "causal"},
    }
