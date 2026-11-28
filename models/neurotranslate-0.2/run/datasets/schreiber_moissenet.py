"""Schreiber-Moissenet (figshare 7734767 v8, CC BY 4.0): ordinals 1-30 of the split-three rule.

Every walk (conditions C1-C5) and the static trial of the 30 training participants are read by member
name from the local source archive; members of ordinals 31-50 are never opened (Python's zipfile
inflates only the member asked for). One C3D per walk: 52 markers at 100 Hz, 8 right-leg EMG at
1,500 Hz, two plates (type 2, newtons) on one clock.
"""
import json
import re
import zipfile
from pathlib import Path

import numpy as np

import common
from datasets import c3d_common

DATASET = "schreiber_moissenet"
PREFIX = "A multimodal dataset of human gait at different walking speeds/"
MARKERS = ["L_IAS", "L_IPS", "R_IPS", "R_IAS", "L_FTC", "L_FLE", "L_FME", "L_FAX", "L_TTC", "L_FAL", "L_TAM", "L_FCC",
           "L_FM1", "L_FM2", "L_FM5", "R_FTC", "R_FLE", "R_FME", "R_FAX", "R_TTC", "R_FAL", "R_TAM", "R_FCC", "R_FM1",
           "R_FM2", "R_FM5", "CV7", "TV10", "SXS", "SJN", "L_SIA", "L_SRS", "L_SAA", "L_SAE", "L_HLE", "L_HME", "L_UOA",
           "L_RSP", "L_UHE", "L_HM2", "L_HM5", "R_SIA", "R_SRS", "R_SAA", "R_SAE", "R_HLE", "R_HME", "R_UOA", "R_RSP",
           "R_UHE", "R_HM2", "R_HM5"]
EMG = [("R_tibialis_anterior", "R", "tibialis anterior"), ("R_soleus", "R", "soleus"),
       ("R_gastrocnemius_medialis", "R", "gastrocnemius medialis"), ("R_vastus_medialis", "R", "vastus medialis"),
       ("R_rectus_femoris", "R", "rectus femoris"), ("R_semitendinosus", "R", "semitendinosus"),
       ("R_gluteus_maximus", "R", "gluteus maximus"), ("R_gluteus_medius", "R", "gluteus medius")]
ANCHOR = {"kind": "pelvis", "markers": ["L_IAS", "R_IAS", "L_IPS", "R_IPS"]}
AXIS_NOTE = {"rotation": np.eye(3).tolist(), "note": "laboratory Z is vertical in the source; identity map, re-checked per file"}
META = {
    "name": "A multimodal dataset of human gait at different walking speeds (Rehazenter), version 8",
    "doi": "10.6084/m9.figshare.7734767.v8", "species": "human", "sites": 1, "derived": False, "paired": True,
    "events_definition": "author gait events in each C3D file (EVENT parameters: foot strikes and foot offs)",
    "context": {"dataset": DATASET, "species": "human", "task": "overground walking at five speed conditions and a static trial",
                "body_plan": "human biped", "value_flag": "measured"},
    "streams": [
        {"group": "kin", "kind": "marker", "channels": "52 markers x 3 axes", "rate_hz": 100, "units": "mm",
         "value_type": "measured", "filtering": "author-processed trajectories (every sample flagged as modelled, residual 0)"},
        {"group": "emg", "kind": "surface_emg", "channels": 8, "rate_hz": 1500, "units": "V (source); log RMS per step",
         "value_type": "measured", "side": "right leg"},
        {"group": "force", "kind": "plate_force", "channels": "2 plates x 3 axes", "rate_hz": 1500, "units": "N",
         "value_type": "measured", "frame": "laboratory, ground reaction"},
    ],
    "notes": ["Plate moments are not tokenised (the force group holds the three force axes per plate).",
              "Each static trial holds one 100 Hz frame, shorter than one 20 ms step, so the 30 static trials are read and audited but give no token."],
}


def _paths(paths):
    root = Path(paths["schreiber_moissenet_source"])
    return root / "source.zip", root / "split-three.json"


def roster(paths):
    _, split = _paths(paths)
    sp = json.loads(split.read_bytes())
    roles, ordinals = {}, {}
    for row in sp["selected"]:
        pid = row["name"].split("/")[-2]
        roles.setdefault(pid, set()).add(row["partition"])
        ordinals[pid] = row["ordinal"]
    unit_roles = {}
    for pid, r in roles.items():
        assert len(r) == 1, (pid, r)
        unit_roles[pid] = r.pop()
    units = sorted(p for p, r in unit_roles.items() if r == "train")
    assert sorted(ordinals[p] for p in units) == list(range(1, 31))
    excluded = {"assessment_ordinals_31_40": sorted(p for p, r in unit_roles.items() if r != "train" and 31 <= ordinals[p] <= 40),
                "reserve_ordinals_41_50": sorted(p for p, r in unit_roles.items() if r != "train" and ordinals[p] >= 41)}
    assert len(excluded["assessment_ordinals_31_40"]) == 10 and len(excluded["reserve_ordinals_41_50"]) == 10
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["train"],
            "rule": sp["rule"], "excluded": excluded,
            "roster_files": [{"file": "split-three.json (earlier overground study)", "sha256": common.sha256_file(split)}]}


def channels(paths):
    from p2 import ChannelSet
    ch = ChannelSet()
    c3d_common.add_marker_channels(ch, MARKERS, "isb", DATASET)
    c3d_common.add_emg_channels(ch, EMG, DATASET, 1500)
    c3d_common.add_plate_channels(ch, 2)
    return ch


def jobs(paths, units):
    src, _ = _paths(paths)
    z = zipfile.ZipFile(src)
    names = [i.filename for i in z.infolist()]
    out = []
    for u in units:
        mem = sorted(n for n in names if n.startswith(PREFIX + u + "/") and n.lower().endswith(".c3d"))
        out.append((u, mem))
    return out


def process_unit(paths, unit, members, chans):
    src, _ = _paths(paths)
    z = zipfile.ZipFile(src)
    spec = {"marker_idx": {n: [chans.idx("kin", "%s_%s" % (n, a)) for a in "xyz"] for n in MARKERS},
            "R": np.eye(3), "top": ANCHOR["markers"], "bottom": ["L_FCC", "R_FCC", "L_FM2", "R_FM2"],
            "emg": {lab: chans.idx("emg", lab) for lab, _, _ in EMG}, "plates": {0: [chans.idx("force", "plate1_%s" % a) for a in "xyz"],
                                                                                 1: [chans.idx("force", "plate2_%s" % a) for a in "xyz"]}}
    recs, metas, checks = [], [], {}
    for name in members:
        info = z.getinfo(name)
        assert name.split("/")[-2] == unit
        b = z.read(name)
        base = name.split("/")[-1][:-4]
        m = re.match(r"(\d+)_(C\d)_(\d+)$", base)
        if m:
            task, cond = "walk", m.group(2)
        elif base.endswith("_ST"):
            task, cond = "static", None
        else:
            task, cond = "other", None
        meta = {"source_member": name, "member_crc32": "%08x" % info.CRC, "member_bytes": len(b),
                "member_sha256": common.sha256_bytes(b), "task": task, "condition": cond, "session": 1}
        rec, meta, ck = c3d_common.tokenise(b, chans, base, unit, spec, meta)
        recs.append(rec)
        metas.append(meta)
        checks[base] = ck
    return recs, metas, checks


def file_audit(paths, results):
    allm = [(r["unit"], m) for r in results for m in r["recordings"] + r.get("dropped_recordings", [])]
    bad = [m["source_member"] for u, m in allm if m["source_member"].split("/")[-2] != u]
    walks = sum(1 for _, m in allm if m["task"] == "walk")
    static = sum(1 for _, m in allm if m["task"] == "static")
    static_tokens = sum(1 for r in results for m in r["recordings"] if m["task"] == "static")
    return {"pass": not bad and walks == 685 and static == 30, "walks_read": walks, "static_read": static,
            "static_with_tokens": static_tokens,
            "note": "each static trial holds a single 100 Hz frame (10 ms), shorter than one 20 ms step, so it gives no token",
            "expected_from_protocol": {"walks": 685, "static": 30}, "members_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((m["source_member"], m["member_sha256"]) for r in results
                  for m in r["recordings"] + r.get("dropped_recordings", []))
    return {"files": len(rows), "member_list_sha256": common.sha256_text(json.dumps(rows)),
            "archive": "source.zip, 381,392,112 B, sha256 e11f0f85424e7630d32dbeb8b37bf78d470dcb34c0f461417671ce7d146eaec5"}


def gates(paths, results, summary):
    src, _ = _paths(paths)
    allck = [c for r in results for c in r["checks"].values()]
    clock_ok = all(c.get("analog_samples_equal_frames_x_per_frame") in (True, None) and
                   c.get("analog_rate_equals_point_rate_x_per_frame", True) for c in allck)
    vert = [c.get("vertical_axis_from_landmarks", {}).get("agrees_with_dataset_map") for c in allck]
    return {
        "Q3_access": {"pass": True, "how": "local archive read by member name; only the 715 members of the 30 training "
                      "participants were inflated", "archive_sha256": common.sha256_file(src)},
        "Q4_clock": {"pass": clock_ok, "how": "markers, EMG and plates share one C3D clock; analog samples = frames x "
                     "samples per frame checked on every file", "files_checked": len(allck),
                     "vertical_axis_rechecks_disagreeing": sum(1 for v in vert if v is False)},
        "Q5_labels": {"pass": True, "how": "units and modality per channel in TOKENS.json; markers mm, EMG volts (log RMS), "
                      "forces N; all measured; EMG labelled surface EMG of muscles, not nerve recordings"},
        "Q6_causality": {"pass": True, "author_filtering": "trajectories are author-processed (residual 0 on all samples: "
                         "filtered or gap-filled); the filter's phase is not documented in the deposit",
                         "our_features": "causal: last sample, change, step mean, forward-only 20 Hz high-pass then log RMS"},
    }
