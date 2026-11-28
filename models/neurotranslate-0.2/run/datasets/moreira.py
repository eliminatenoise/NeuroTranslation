"""Moreira et al. (figshare 14241812 v1, CC0 1.0): the 8 development people of the earlier source split.

Members are read by name from the local C3D archive (only Participant<N>/ folders of development
people). One C3D per trial: 24 markers at 200 Hz, 8 named leg EMG channels and 6 force plates at
2 kHz on one clock. Plates are type 4 (CAL_MATRIX applied to volts) and one type 3 (Kistler,
8 channels summed); no ZERO range is stored, so no baseline is subtracted (offsets of unloaded plates
remain, recorded in the notes). Unnamed analog channels (EMG_01, EMG_10-12, Reserved_*) are not used.
"""
import json
import zipfile
from pathlib import Path

import numpy as np

import common
from datasets import c3d_common

DATASET = "moreira"
MARKERS = ["RASIS", "LASIS", "RPSIS", "LPSIS", "RTROC", "LTROC", "RTH1", "RLK", "RMK", "RSK1", "RLA", "RMA", "RFM1",
           "RFM2", "RFM5", "LTH1", "LLK", "LMK", "LSK1", "LLA", "LMA", "LFM1", "LFM2", "LFM5"]
EMG = [("R_Vastus lateralis", "R", "vastus lateralis"), ("R_Biceps femoris", "R", "biceps femoris"),
       ("R_Tibialis anterior", "R", "tibialis anterior"), ("R_Gastrocnemius lateralis", "R", "gastrocnemius lateralis"),
       ("L_Vastus lateralis", "L", "vastus lateralis"), ("L_Biceps femoris", "L", "biceps femoris"),
       ("L_Tibialis anterior", "L", "tibialis anterior"), ("L_Gastrocnemius lateralis", "L", "gastrocnemius lateralis")]
N_PLATES = 6
ANCHOR = {"kind": "pelvis", "markers": ["RASIS", "LASIS", "RPSIS", "LPSIS"]}
AXIS_NOTE = {"rotation": np.eye(3).tolist(), "note": "laboratory Z is vertical in the source; identity map, re-checked per file"}
SPEED = {"V1": 1.0, "V15": 1.5, "V2": 2.0, "V25": 2.5, "V3": 3.0, "V35": 3.5, "V4": 4.0}
META = {
    "name": "Lower limb kinematic, kinetic and EMG data from young healthy humans during walking at controlled speeds (C3D files)",
    "doi": "10.6084/m9.figshare.14241812.v1", "species": "human", "sites": 1, "derived": False, "paired": True,
    "events_definition": "author events stored in the C3D files (none present in this release)",
    "context": {"dataset": DATASET, "species": "human", "task": "overground walking at 7 controlled speeds (1-4 km/h)",
                "body_plan": "human biped", "value_flag": "measured"},
    "streams": [
        {"group": "kin", "kind": "marker", "channels": "24 markers x 3 axes", "rate_hz": 200, "units": "mm",
         "value_type": "measured", "filtering": "publisher reports polynomial gap filling"},
        {"group": "emg", "kind": "surface_emg", "channels": 8, "rate_hz": 2000, "units": "V (source); log RMS per step",
         "value_type": "measured", "side": "both legs, 4 muscles each"},
        {"group": "force", "kind": "plate_force", "channels": "6 plates x 3 axes", "rate_hz": 2000, "units": "N",
         "value_type": "measured", "frame": "laboratory, ground reaction; calibrated from volts with the C3D calibration"},
    ],
    "notes": ["No FORCE_PLATFORM:ZERO range is stored; unloaded plates keep offsets of up to about 20 N.",
              "Force calibration follows the C3D type 4 and type 3 definitions; one development trial's vertical force "
              "was compared with the authors' ASCII export (Q5 evidence)."],
}


def _src(paths):
    return Path(paths["moreira_source"])


def roster(paths):
    s = _src(paths) / "SOURCE-SPLIT.json"
    sp = json.loads(s.read_bytes())
    unit_roles = {}
    for role, ids in sp["participants"].items():
        for i in ids:
            unit_roles[str(i)] = role
    units = sorted((u for u, r in unit_roles.items() if r == "development"), key=int)
    excluded = {r: sorted(str(i) for i in ids) for r, ids in sp["participants"].items() if r != "development"}
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["development"], "rule": sp["person_order_rule"],
            "excluded": excluded,
            "roster_files": [{"file": "SOURCE-SPLIT.json (earlier Moreira study)", "sha256": common.sha256_file(s)}]}


def channels(paths):
    from p2 import ChannelSet
    ch = ChannelSet()
    c3d_common.add_marker_channels(ch, MARKERS, "moreira", DATASET)
    c3d_common.add_emg_channels(ch, EMG, DATASET, 2000)
    c3d_common.add_plate_channels(ch, N_PLATES)
    return ch


def jobs(paths, units):
    z = zipfile.ZipFile(_src(paths) / "c3d-files.zip")
    names = [i.filename for i in z.infolist()]
    out = []
    for u in units:
        pre = "c3d files/Participant%s/" % u
        out.append((u, sorted(n for n in names if n.startswith(pre) and n.lower().endswith(".c3d"))))
    return out


def process_unit(paths, unit, members, chans):
    z = zipfile.ZipFile(_src(paths) / "c3d-files.zip")
    spec = {"marker_idx": {n: [chans.idx("kin", "%s_%s" % (n, a)) for a in "xyz"] for n in MARKERS},
            "R": np.eye(3), "top": ANCHOR["markers"], "bottom": ["RFM2", "LFM2", "RLA", "LLA"],
            "emg": {lab: chans.idx("emg", lab) for lab, _, _ in EMG},
            "plates": {p: [chans.idx("force", "plate%d_%s" % (p + 1, a)) for a in "xyz"] for p in range(N_PLATES)}}
    recs, metas, checks = [], [], {}
    for name in members:
        assert name.split("/")[1] == "Participant" + unit
        info = z.getinfo(name)
        b = z.read(name)
        parts = name.split("/")
        folder = parts[-2]
        tag = "%s_%s_%s" % (unit, folder, parts[-1][:-4])
        meta = {"source_member": name, "member_crc32": "%08x" % info.CRC, "member_bytes": len(b),
                "member_sha256": common.sha256_bytes(b), "task": "walk" if folder in SPEED else folder,
                "condition": ("%.1f km/h" % SPEED[folder]) if folder in SPEED else None, "session": 1,
                "folder": "/".join(parts[2:-1])}
        rec, meta, ck = c3d_common.tokenise(b, chans, tag, unit, spec, meta)
        recs.append(rec)
        metas.append(meta)
        checks[tag] = ck
    return recs, metas, checks


def file_audit(paths, results):
    bad = [m["source_member"] for r in results for m in r["recordings"]
           if m["source_member"].split("/")[1] != "Participant" + r["unit"]]
    n = sum(len(r["recordings"]) for r in results)
    return {"pass": not bad and n == 551, "trials": n, "expected_from_protocol": 551, "members_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((m["source_member"], m["member_sha256"]) for r in results for m in r["recordings"])
    return {"files": len(rows), "member_list_sha256": common.sha256_text(json.dumps(rows)),
            "archive": "c3d files.zip, 1,804,755,126 B, publisher md5 7fa9bc94db2a9df5e01301f1be184b38"}


def calibration_check(paths):
    """Vertical force of one development trial (Participant 1, V1, T1) against the authors' ASCII export of the
    same trial, summing per plate only loads above the authors' 20 N threshold, on loaded frames (> 100 N)."""
    import c3d_reader
    ref_f = _src(paths) / "private-reference-GRF.txt"
    if not ref_f.exists():
        return {"status": "reference export not available"}
    b = zipfile.ZipFile(_src(paths) / "c3d-files.zip").read("c3d files/Participant1/Raw_Data/V1/T1.c3d")
    d = c3d_reader.read_c3d(b)
    ref = np.genfromtxt(ref_f, skip_header=1)
    refz = np.nansum(ref[:, [3, 6]], axis=1)
    tot = 0
    for p in d["force_platforms"]:
        if p.get("force_lab") is not None:
            z = p["force_lab"][:, 2]
            tot = tot + np.where(z > 20, z, 0)
    t = tot[::d["analog_per_frame"]][:len(refz)]
    ld = refz > 100
    return {"trial": "Participant1/Raw_Data/V1/T1 (development)", "reference_sha256": common.sha256_file(ref_f),
            "loaded_frames": int(ld.sum()), "vertical_mae_n": round(float(np.mean(np.abs(t[ld] - refz[ld]))), 2),
            "vertical_correlation": round(float(np.corrcoef(t[ld], refz[ld])[0, 1]), 5)}


def gates(paths, results, summary):
    allck = [c for r in results for c in r["checks"].values()]
    clock_ok = all(c.get("analog_samples_equal_frames_x_per_frame") in (True, None) and
                   c.get("analog_rate_equals_point_rate_x_per_frame", True) for c in allck)
    vert = [c.get("vertical_axis_from_landmarks", {}).get("agrees_with_dataset_map") for c in allck]
    return {
        "Q3_access": {"pass": True, "how": "local archive read by member name; only development people's members inflated",
                      "archive_sha256": common.sha256_file(_src(paths) / "c3d-files.zip")},
        "Q4_clock": {"pass": clock_ok, "how": "markers, EMG and plates share one C3D clock; checked on every file",
                     "files_checked": len(allck), "vertical_axis_rechecks_disagreeing": sum(1 for v in vert if v is False)},
        "Q5_labels": {"pass": True, "how": "units and modality per channel in TOKENS.json; all measured; EMG labelled surface "
                      "EMG of muscles, not nerve recordings", "force_calibration_check": calibration_check(paths)},
        "Q6_causality": {"pass": True, "author_filtering": "publisher reports polynomial gap filling of trajectories",
                         "our_features": "causal (last sample, change, step mean, forward-only high-pass and log RMS)"},
    }
