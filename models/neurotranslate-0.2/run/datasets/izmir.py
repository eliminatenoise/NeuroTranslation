"""Izmir walking motion capture (Aperta 286866, CC BY 4.0): 16 fit people and engineering person S01.

Only the 3 walking-cycle C3D members per person listed in the frozen roster are inflated from the local
MoCap.zip (51 files); development and final people (consumed) are never opened. The protocol admits the
markers only, so the plate and the four unlabelled EMG sensors in these files are not tokenised.
"""
import json
import zipfile
from pathlib import Path

import numpy as np

import common
from datasets import c3d_common

DATASET = "izmir"
MARKERS = ["L_HEAD", "R_HEAD", "SGL", "CV7", "L_SIA", "R_SIA", "TV10", "L_SAE", "L_HUM", "L_HLE", "L_RSP", "L_USP", "L_HM2",
           "R_SAE", "R_HUM", "R_HLE", "R_RSP", "R_USP", "R_HM2", "L_IAS", "L_IPS", "R_IPS", "R_IAS", "L_TH1", "L_TH2",
           "L_TH3", "L_TH4", "L_SK1", "L_SK2", "L_SK3", "L_SK4", "L_FCC", "L_FM1", "L_FM2", "L_FM5", "R_TH1", "R_TH2",
           "R_TH3", "R_TH4", "R_SK1", "R_SK2", "R_SK3", "R_SK4", "R_FCC", "R_FM1", "R_FM2", "R_FM5"]
ANCHOR = {"kind": "pelvis", "markers": ["L_IAS", "R_IAS", "L_IPS", "R_IPS"]}
AXIS_NOTE = {"rotation": np.eye(3).tolist(), "note": "laboratory Z is vertical in the source; identity map, re-checked per file"}
META = {
    "name": "Izmir walking motion capture (Aperta)", "doi": "10.48623/aperta.286865 (record 286866)",
    "species": "human", "sites": 1, "derived": False, "paired": False,
    "events_definition": "author cycle start and end events in each C3D file",
    "context": {"dataset": DATASET, "species": "human", "task": "overground walking, one gait cycle per file",
                "body_plan": "human biped", "value_flag": "measured"},
    "streams": [{"group": "kin", "kind": "marker", "channels": "47 markers x 3 axes", "rate_hz": 100, "units": "mm",
                 "value_type": "measured", "filtering": "not documented in the deposit README"}],
    "notes": ["Each file holds one gait cycle of about 1.1-1.6 s, so most files give one counted 1.2 s window.",
              "The C3D files also hold a force plate and four unlabelled EMG sensors; the protocol admits markers only."],
}


def _src(paths):
    return Path(paths["izmir_source"])


def roster(paths):
    f = _src(paths) / "ROSTER.json"
    r = json.loads(f.read_bytes())
    unit_roles = {}
    for role, ids in r["roles"].items():
        for i in ids:
            unit_roles[i] = role
    units = sorted(u for u, role in unit_roles.items() if role in ("fit", "engineering"))
    assert len(units) == 17
    excluded = {k: sorted(v) for k, v in r["roles"].items() if k not in ("fit", "engineering")}
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["fit", "engineering"],
            "rule": r.get("state"), "excluded": excluded,
            "roster_files": [{"file": "izmir ROSTER.json (earlier walking study)", "sha256": common.sha256_file(f)}]}


def channels(paths):
    from p2 import ChannelSet
    ch = ChannelSet()
    c3d_common.add_marker_channels(ch, MARKERS, "isb", DATASET)
    return ch


def jobs(paths, units):
    r = json.loads((_src(paths) / "ROSTER.json").read_bytes())
    return [(u, [(k, v["name"], v["crc32"]) for k, v in sorted(r["members"][u].items())]) for u in units]


def process_unit(paths, unit, members, chans):
    z = zipfile.ZipFile(_src(paths) / "private" / "MoCap.zip")
    spec = {"marker_idx": {n: [chans.idx("kin", "%s_%s" % (n, a)) for a in "xyz"] for n in MARKERS},
            "R": np.eye(3), "top": ANCHOR["markers"], "bottom": ["L_FCC", "R_FCC", "L_FM2", "R_FM2"],
            "emg": None, "plates": None}
    recs, metas, checks = [], [], {}
    for k, name, crc in members:
        info = z.getinfo(name)
        assert "%08x" % info.CRC == crc and name.split("/")[-1].startswith(unit)
        b = z.read(name)
        tag = name.split("/")[-1][:-4]
        meta = {"source_member": name, "member_crc32": crc, "member_bytes": len(b), "member_sha256": common.sha256_bytes(b),
                "task": "walk", "condition": None, "session": 1, "cycle": int(k)}
        rec, meta, ck = c3d_common.tokenise(b, chans, tag, unit, spec, meta)
        recs.append(rec)
        metas.append(meta)
        checks[tag] = ck
    return recs, metas, checks


def file_audit(paths, results):
    n = sum(len(r["recordings"]) for r in results)
    bad = [m["source_member"] for r in results for m in r["recordings"] if not m["source_member"].split("/")[-1].startswith(r["unit"])]
    return {"pass": n == 51 and not bad, "files": n, "expected_from_protocol": 51, "members_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((m["source_member"], m["member_sha256"]) for r in results for m in r["recordings"])
    return {"files": len(rows), "member_list_sha256": common.sha256_text(json.dumps(rows)),
            "archive": "MoCap.zip, 25,457,104 B, sha256 ea6fefd5a80b1b46497ba8e6bd95da028b2c6cbf9bd3a77557997c9ef15bbcaf"}


def gates(paths, results, summary):
    allck = [c for r in results for c in r["checks"].values()]
    vert = [c.get("vertical_axis_from_landmarks", {}).get("agrees_with_dataset_map") for c in allck]
    return {
        "Q3_access": {"pass": True, "how": "local archive; the 51 roster members inflated by name, CRC-32 checked",
                      "archive_sha256": common.sha256_file(_src(paths) / "private" / "MoCap.zip")},
        "Q4_clock": {"pass": True, "how": "markers only, one file per cycle (no pairing needed)", "files_checked": len(allck),
                     "vertical_axis_rechecks_disagreeing": sum(1 for v in vert if v is False)},
        "Q5_labels": {"pass": True, "how": "markers in mm, measured; cluster markers kept as dataset-specific rows"},
        "Q6_causality": {"pass": True, "author_filtering": "not documented in the deposit README; flagged unknown",
                         "our_features": "causal (last sample and change per step)"},
    }
