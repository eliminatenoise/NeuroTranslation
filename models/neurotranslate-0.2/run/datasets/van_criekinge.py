"""Van Criekinge et al. healthy adult gait (figshare 24192480 v1, CC0): the 12 fit people (36 walks).

The fit members were fetched earlier by ranged reads and are local; each file's sha256 is checked
against the earlier transport record before it is read. Validation, test, never-assigned and stroke
people are never opened. One C3D per walk: Plug-in-Gait markers at 100 Hz, plates and EMG at 1 kHz.
Model outputs stored as points (virtual markers, angles, powers, forces, moments) are not used; the
three unnamed analog channels and the foot switches are not used.
"""
import json
from pathlib import Path

import numpy as np

import common
from datasets import c3d_common

DATASET = "van_criekinge"
MARKERS = ["LFHD", "RFHD", "LBHD", "RBHD", "C7", "T10", "CLAV", "STRN", "LSHO", "LELB", "LWRA", "LWRB", "LFIN", "RSHO",
           "RELB", "RWRA", "RWRB", "RFIN", "LASI", "RASI", "SACR", "LTHI", "LKNE", "LTIB", "LANK", "LHEE", "LTOE", "RTHI",
           "RKNE", "RTIB", "RANK", "RHEE", "RTOE", "LPSI", "RPSI", "RBAK", "LUPA", "RUPA", "LFRM", "RFRM"]
EMG_LABELS = {"Voltage.RERS": ("R", "erector spinae"), "Voltage.LERS": ("L", "erector spinae"),
              "Voltage.RRF": ("R", "rectus femoris"), "Voltage.LRF": ("L", "rectus femoris"),
              "Voltage.RVL": ("R", "vastus lateralis"), "Voltage.LVL": ("L", "vastus lateralis"),
              "Voltage.RTA": ("R", "tibialis anterior"), "Voltage.LTA": ("L", "tibialis anterior"),
              "Voltage.RGAS": ("R", None), "Voltage.LGAS": ("L", None),
              "Voltage.RST": ("R", "semitendinosus"), "Voltage.LST": ("L", "semitendinosus"),
              "Voltage.RBF": ("R", "biceps femoris"), "Voltage.LBF": ("L", "biceps femoris")}
N_PLATES = 4
ANCHOR = {"kind": "pelvis", "markers": ["LASI", "RASI", "SACR", "LPSI", "RPSI"]}
AXIS_NOTE = {"rotation": np.eye(3).tolist(), "note": "laboratory Z is vertical in the source; identity map, re-checked per file"}
META = {
    "name": "Van Criekinge et al. healthy adult gait (138_HealthyPiG)", "doi": "10.6084/m9.figshare.24192480.v1",
    "species": "human", "sites": 1, "derived": False, "paired": True,
    "events_definition": "author gait events in each C3D file (foot strikes and foot offs)",
    "context": {"dataset": DATASET, "species": "human", "task": "overground walking at self-selected speed",
                "body_plan": "human biped", "value_flag": "measured"},
    "streams": [
        {"group": "kin", "kind": "marker", "channels": "Plug-in-Gait markers x 3 axes", "rate_hz": 100, "units": "mm",
         "value_type": "measured", "filtering": "author-processed (most samples flagged modelled)"},
        {"group": "emg", "kind": "surface_emg", "channels": "up to 14 named channels", "rate_hz": 1000,
         "units": "V (source); log RMS per step", "value_type": "measured"},
        {"group": "force", "kind": "plate_force", "channels": "4 plates x 3 axes", "rate_hz": 1000, "units": "N",
         "value_type": "measured", "frame": "laboratory, ground reaction"},
    ],
    "notes": ["Gastrocnemius channels (GAS) do not name the head, so they get dataset rows.",
              "Plug-in-Gait model outputs stored in the C3D point section are not used."],
}


def _src(paths):
    return Path(paths["van_criekinge_source"])


def roster(paths):
    f = _src(paths) / "ROSTER.json"
    r = json.loads(f.read_bytes())
    unit_roles = {}
    for role, rows in r["roles"].items():
        for row in rows:
            unit_roles[row["subject_code"]] = role
    units = sorted(u for u, role in unit_roles.items() if role == "fit")
    excluded = {k: sorted(row["subject_code"] for row in rows) for k, rows in r["roles"].items() if k != "fit"}
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["fit"], "rule": r["selection_rule"],
            "excluded": excluded,
            "roster_files": [{"file": "van-criekinge prospective ROSTER.json (earlier study)", "sha256": common.sha256_file(f)}]}


def channels(paths):
    from p2 import ChannelSet
    ch = ChannelSet()
    c3d_common.add_marker_channels(ch, MARKERS, "pig", DATASET)
    items = []
    for lab, (side, mus) in EMG_LABELS.items():
        items.append((lab, side, mus))
    c3d_common.add_emg_channels(ch, items, DATASET, 1000)
    c3d_common.add_plate_channels(ch, N_PLATES)
    return ch


def jobs(paths, units):
    r = json.loads((_src(paths) / "ROSTER.json").read_bytes())
    res = json.loads((_src(paths) / "fit-transport" / "RESULT.json").read_bytes())
    by_member = {v["archive_member"]: v for v in res["records"].values()}
    out = []
    for row in r["roles"]["fit"]:
        mem = []
        for m in row["members"]:
            t = by_member[m["path"]]
            mem.append((m["path"], t["path"], t["decoded_sha256"], m["zip_crc32"], m["author_trial_index"]))
        out.append((row["subject_code"], mem))
    return [j for j in out if j[0] in units]


def process_unit(paths, unit, members, chans):
    root = _src(paths) / "fit-transport"
    spec = {"marker_idx": {n: [chans.idx("kin", "%s_%s" % (n, a)) for a in "xyz"] for n in MARKERS},
            "R": np.eye(3), "top": ["LASI", "RASI", "SACR"], "bottom": ["LHEE", "RHEE", "LTOE", "RTOE"],
            "emg": {lab: chans.idx("emg", lab) for lab in EMG_LABELS},
            "plates": {p: [chans.idx("force", "plate%d_%s" % (p + 1, a)) for a in "xyz"] for p in range(N_PLATES)}}
    recs, metas, checks = [], [], {}
    for member, local, digest, crc, trial in members:
        b = (root / local).read_bytes()
        if common.sha256_bytes(b) != digest:
            raise ValueError("local file differs from transport record: " + member)
        tag = "%s_trial%d" % (unit, trial)
        meta = {"source_member": member, "member_crc32": crc, "member_bytes": len(b), "member_sha256": digest,
                "task": "walk", "condition": None, "session": 1, "author_trial_index": trial}
        rec, meta, ck = c3d_common.tokenise(b, chans, tag, unit, spec, meta)
        recs.append(rec)
        metas.append(meta)
        checks[tag] = ck
    return recs, metas, checks


def file_audit(paths, results):
    n = sum(len(r["recordings"]) for r in results)
    return {"pass": n == 36, "walks": n, "expected_from_protocol": 36,
            "local_files_match_transport_sha256": True}


def source_file_summary(results):
    rows = sorted((m["source_member"], m["member_sha256"]) for r in results for m in r["recordings"])
    return {"files": len(rows), "member_list_sha256": common.sha256_text(json.dumps(rows)),
            "archive": "138_HealthyPiG.zip, 463,159,769 B, md5 85235c73455d4df8434810d61517efbb"}


def gates(paths, results, summary):
    allck = [c for r in results for c in r["checks"].values()]
    clock_ok = all(c.get("analog_samples_equal_frames_x_per_frame") in (True, None) and
                   c.get("analog_rate_equals_point_rate_x_per_frame", True) for c in allck)
    vert = [c.get("vertical_axis_from_landmarks", {}).get("agrees_with_dataset_map") for c in allck]
    return {
        "Q3_access": {"pass": True, "how": "local fit members fetched earlier by per-member ranged reads; sha256 checked "
                      "against the transport record before reading"},
        "Q4_clock": {"pass": clock_ok, "how": "markers, EMG and plates share one C3D clock (analog 1 kHz = 10 x 100 Hz); "
                     "checked on every file", "files_checked": len(allck),
                     "vertical_axis_rechecks_disagreeing": sum(1 for v in vert if v is False)},
        "Q5_labels": {"pass": True, "how": "units and modality per channel; all measured; EMG labelled surface EMG of muscles"},
        "Q6_causality": {"pass": True, "author_filtering": "trajectories author-processed (residual 0 on most samples)",
                         "our_features": "causal"},
    }
