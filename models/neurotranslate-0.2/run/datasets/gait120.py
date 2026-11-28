"""Gait120 (figshare 27677016 v1, CC BY 4.0): the 66 development people of the chair-rise roster.

Per person: the local raw.mat (12 right-leg EMG channels at 2 kHz per trial, MATLAB table objects read
with mat-io), the local SitToStand marker and plate files, and the members fetched at P1 (marker TRC
for the other tasks and the static trial, OpenSim joint-angle MOT except SitToStand, plate MOT for
LevelWalking and StandToSit).

Recordings: one per author step segment, the contiguous unit of the protocol (sections 5.2 and 13 and
step P5). A step segment is the TargetFrame range [a, b] of one step file in raw.mat; its recording runs
on the segment's own clock, frame f at (f - a) / 100 s, holds N = b - a + 1 frames and so
floor(N / 2) steps of 20 ms. Markers, joint angles and plates come from that step's own files; EMG is the
trial's EMG over the same frames (20 samples per frame from TotalFrame[0]). The 20 Hz high-pass runs forward
over the trial's whole EMG from its first sample, so it uses only samples before each step end and leaves no
filter start-up inside a segment. EMG outside every step segment of a trial is not tokenised.
Consecutive segments of a trial share one boundary frame (the authors' segmentation); where a segment has an
even number of frames, its last step holds that frame, which the next segment's first step also holds. These
boundaries are counted in the audit. The static trial is a markers-only recording.
Pairing check on every training step (the chair-rise study's rule): TRC frame numbers equal the step's
TargetFrame range and times equal (f - 1) / 100; joint-angle times equal the TRC times; plate times start
at the step's first TRC time on a 2 kHz grid; EMG length equals (TotalFrame[1] - TotalFrame[0] + 1) x 20.
Plate sign: loaded vertical force is checked to be positive; no data-dependent sign change is made.
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
    "events_definition": "author step segments (TargetFrame ranges in raw.mat): one per recording; the static trials have none",
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
              "One recording per author step segment (the TargetFrame range of one step file), the unit that "
              "protocol sections 5.2 and 13 and step P5 use for Gait120; the static trial is one recording. EMG "
              "outside every step segment of a trial is not tokenised.",
              "The 20 Hz EMG high-pass runs forward over the whole trial from its first sample, so a segment's "
              "EMG features use only samples before each step end, including samples before the segment start.",
              "Consecutive step segments share one boundary frame (the authors' segmentation). Where a segment has "
              "an even number of frames, its last 20 ms step holds that frame, which the next segment's first step "
              "also holds; the number of such boundaries is in the Q4 record."],
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
            steps = sorted((int(s[4:]), [int(v) for v in np.ravel(tr[s].flat[0]["TargetFrame"])])
                           for s in tr.dtype.names if s.startswith("Step"))
            # forward-only 20 Hz high-pass over the trial's whole EMG from its first sample; each segment's
            # log RMS then uses only samples before its step ends (no filter start-up inside a segment)
            emg_hp = common.causal_highpass(emg, 2000.0)
            tid = "%s_%s_T%02d" % (unit, task, k)
            step_rows, vert = [], []
            prev = None  # (last target frame, marker array at that frame) of the previous segment
            for si, (a, b) in steps:
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
                # one recording per author step segment: frames a..b on the segment's own clock,
                # frame f at (f - a) / 100 s; markers, joint angles and plates from this step's own files
                N = b - a + 1
                S = common.n_steps_for(N / 100.0)
                rid = "%s_S%02d" % (tid, si)
                rec = common.Recording(rid, unit, S, {})
                lo, hi = common.step_bounds(N, 100.0, 0.0, S)
                names, arr = _read_trc(trc_p)
                fr = arr[:, 0].astype(int)
                tt = arr[:, 1]
                row["recording"] = rid
                row["trc_frames_equal_target"] = bool(fr[0] == a and fr[-1] == b and np.array_equal(fr, np.arange(a, b + 1)))
                row["trc_time_equals_frame_clock"] = bool(np.allclose(tt, (fr - 1) / 100.0, atol=1e-6))
                row["trc_inside_total_frames"] = bool(a >= start and b <= end)
                pts = arr[:, 2:2 + 3 * len(names)].reshape(len(fr), len(names), 3)
                am = c3d_reader.axis_map_from_points(names, pts, ANCHOR["markers"], ["LHEE", "RHEE", "LTOE", "RTOE"])
                if am is not None:
                    vert.append(bool(np.allclose(am[0], R_MAP)))
                pts = pts @ R_MAP.T
                xyz = np.full((N, len(MARKERS), 3), np.nan)
                ii = fr - a
                ok = (ii >= 0) & (ii < N)
                for j, n in enumerate(names):
                    if n in MARKERS:
                        xyz[ii[ok], MARKERS.index(n), :] = pts[ok, j, :]
                if prev is not None and prev[0] == a:
                    both = np.isfinite(prev[1]).all(axis=1) & np.isfinite(xyz[0]).all(axis=1)
                    if both.any():
                        row["shared_frame_max_diff_mm"] = float(np.abs(prev[1][both] - xyz[0][both]).max())
                prev = (b, xyz[-1].copy())
                put_markers(rec, MARKERS, xyz, lo, hi)
                if ja_p is not None:
                    head, ja_a = _read_mot(ja_p)
                    row["ja_time_equals_trc_time"] = bool(ja_a.shape[0] == len(tt) and np.allclose(ja_a[:, 0], tt, atol=1e-6))
                    ja = np.full((N, len(head) - 1), np.nan)
                    jf = np.rint(ja_a[:, 0] * 100).astype(int) + 1 - a
                    okj = (jf >= 0) & (jf < N)
                    ja[jf[okj]] = ja_a[okj, 1:]
                    idx = [chans.idx("kin", "ja:" + c) for c in head[1:]]
                    v, m = common.kin_features(ja, lo, hi)
                    rec.put("kin", idx, v, m, nK)
                elo, ehi = common.step_bounds(N * 20, 2000.0, 0.0, S)
                e0, e1 = (a - start) * 20, (b - start + 1) * 20
                row["emg_samples_inside_trial"] = bool(e0 >= 0 and e1 <= emg.shape[0])
                v, m = common.emg_features(emg_hp[max(e0, 0):e1], 2000.0, elo, ehi, already_filtered=True)
                rec.put("emg", emg_idx, v, m, chans.n("emg"))
                plates = False
                if mot_p is not None:
                    head, fa = _read_mot(mot_p)
                    plates_here = [p for p in (1, 2) if "ground_force%d_vx" % p in head]
                    row["plates_in_file"] = plates_here
                    ft = fa[:, 0]
                    row["plate_starts_at_trc_time"] = bool(abs(ft[0] - tt[0]) < 1e-6)
                    row["plate_on_2khz_grid"] = bool(np.allclose(np.diff(ft), 0.0005, atol=1e-6))
                    kk = np.rint((ft - (a - 1) / 100.0) * 2000).astype(int)
                    okf = (kk >= 0) & (kk < N * 20)
                    frc = np.full((N * 20, 6), np.nan)
                    for p in plates_here:
                        cols = [head.index("ground_force%d_v%s" % (p, ax)) for ax in "xyz"]
                        F, nbad = common.mask_implausible_force(fa[:, cols] @ R_MAP.T)
                        if nbad:
                            # a plate file with any sample above 10 kN is corrupt throughout (zeros and
                            # values up to 1e36 in the published files): the whole plate of that file is masked
                            row.setdefault("plate_samples_above_10kN_masked", {})[str(p)] = nbad
                            F[:] = np.nan
                        frc[kk[okf], (p - 1) * 3:p * 3] = F[okf]
                        # sign convention check only (no data-dependent flip): loaded vertical force must be positive
                        z = F[okf, 2]
                        loaded = np.isfinite(z) & (np.abs(z) > 50)
                        if loaded.sum() > 10 and np.median(z[loaded]) < 0:
                            row.setdefault("plate_vertical_median_negative", []).append(p)
                    if np.isfinite(frc).any():
                        plates = True
                        v, m = common.force_features(frc, elo, ehi)
                        rec.put("force", pl_idx, v, m, chans.n("force"))
                row["last_step_holds_last_frame"] = bool(2 * S == N)
                recs.append(rec)
                metas.append({"task": task, "trial": k, "step": si, "condition": None, "session": 1, "events": 1,
                              "duration_s": round(N / 100.0, 3), "target_frames": [a, b],
                              "joint_angles": ja_p is not None, "plates": plates})
                step_rows.append(row)
            # consecutive author segments share one boundary frame; count where both recordings hold it
            shared = 0
            for r0, r1 in zip(step_rows, step_rows[1:]):
                if r0["target_frames"][1] == r1["target_frames"][0] and r0.get("last_step_holds_last_frame"):
                    shared += 1
            ck["steps"] = step_rows
            ck["boundary_frames_in_two_recordings"] = shared
            ck["vertical_axis_rechecks"] = vert
            checks[tid] = ck
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
    a7, n7 = allok("emg_samples_inside_trial")
    e_ok = all(c["emg_length_equals_frames_x_20"] for c in trials)
    neg = sorted("%s step %d plate %s" % (r, s["step"], p) for res in results for r, c in res["checks"].items()
                 for s in c.get("steps", []) for p in s.get("plate_vertical_median_negative", []))
    shared = sum(c.get("boundary_frames_in_two_recordings", 0) for c in trials)
    seg_rec = sum(1 for s in steps if "recording" in s)
    frames = sorted(s["target_frames"][1] - s["target_frames"][0] + 1 for s in steps if "recording" in s)
    durations = {"segments": len(frames), "min_s": frames[0] / 100.0 if frames else None,
                 "median_s": float(np.median(frames)) / 100.0 if frames else None,
                 "max_s": frames[-1] / 100.0 if frames else None,
                 "shorter_than_one_1200ms_window": sum(1 for n in frames if n // 2 < common.WINDOW_STEPS),
                 "note": "N frames give floor(N / 2) steps; a segment of fewer than 120 frames holds no counted window"}
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
        "Q4_clock": {"pass": a1 and a2 and a3 and a4 and a5 and a6 and a7 and e_ok,
                     "how": "trial timestamp and frame-identifier match of the chair-rise study, on every training step "
                            "segment; one recording per author step segment",
                     "step_segment_recordings": seg_rec, "segment_emg_inside_trial_emg": [a7, n7],
                     "step_segment_durations": durations,
                     "boundary_frames_in_two_recordings": shared,
                     "trc_frames_equal_target": [a1, n1], "trc_time_equals_frame_clock": [a2, n2],
                     "joint_angle_time_equals_trc": [a3, n3], "plate_starts_at_trc_time": [a4, n4],
                     "plate_on_2khz_grid": [a5, n5], "segment_frames_inside_trial_frames": [a6, n6],
                     "emg_length_equals_frames_x_20": [e_ok, len(trials)], "step_files_missing": missing,
                     "vertical_axis_rechecks_disagreeing": sum(1 for v in vert if not v)},
        "Q5_labels": {"pass": not neg, "how": "markers mm (measured), OpenSim coordinates degrees or m (derived), EMG measured "
                      "surface EMG of right-leg muscles (not a nerve recording), plate forces N (measured; loaded vertical "
                      "force positive in every plate file, checked; no sign change made)",
                      "plate_files_with_negative_loaded_vertical_median": neg,
                      "plate_files_masked_whole_for_samples_above_10kN": implaus},
        "Q6_causality": {"pass": True, "author_filtering": "marker files are the authors' filtered TRC exports; joint angles "
                         "come from the authors' inverse kinematics on them; filter phase not documented in the deposit",
                         "our_features": "causal"},
    }
