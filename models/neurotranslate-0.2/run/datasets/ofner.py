"""Ofner et al. 2017 (Zenodo 834976, CC BY 4.0): S1-S7, motor-execution runs 1-10.

Roster: the arm-transfer protocol (repository models/arm-transfer/PROTOCOL.md): S1-S7 fitting, S8-S12
assessment (consumed, including their unopened runs 5-10), S13-S15 reserve. Runs 1-3 are the earlier local
copies (sha256 checked against the earlier fitting receipt); runs 4-10 were downloaded at P1 (publisher MD5
and size checked). No file of S8-S15 and no motor-imagery run is opened.

One GDF 2.10 file per run: 96 channels in 1 s records, little-endian float64 with identity scaling and blank
physical units: 61 EEG and 3 EOG at 512 Hz, 32 glove, exoskeleton and arm channels at 64 Hz, plus an event
table (cue codes 0x600-0x606). Header layout checks follow the earlier reviewed reader. Tokens: field = 61 EEG
(10-5 site names from the authors' channel table, shared vocabulary) + 3 EOG; kin = the 27 mechanical channels
with a meaning in the authors' table (15 glove sensors, hand and elbow positions, 6 arm angles), in their native
uncalibrated units. The five channels the table marks '-' (wrist_bend, roll, pitch, gesture, GripPressure) are
not tokenised.

Clock: each 1 s record holds 512 samples of the fast channels and 64 of the slow ones, so every 64 Hz reading
spans 8 ticks of the 512 Hz clock, and where inside those ticks it was acquired is not documented: reading j of
a run lies between j / 64 s and (8j + 7) / 512 s, up to 13.7 ms after the time the file gives it. The arm and
glove stream is therefore tokenised on the file's times (reading j at j / 64 s) and then delayed by one whole
20 ms step (KIN_DELAY_STEPS): the token of step k holds the last reading whose file time lies in step k - 1, so
that reading was acquired before step k ends even in the latest case. The first step of a run holds no arm or
glove value. A whole step was used because the tokens of the first tokenisation could be corrected from the
stored shards this way without a second download (delay_ofner_kin.py); a fresh run of this reader gives the
same tokens.
"""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

import common
import neural_common as nc

DATASET = "ofner"
KIND = "person"
PEOPLE = ["S%d" % i for i in range(1, 8)]
RUNS = list(range(1, 11))
EEG_SITES = tuple("""
F3 F1 Fz F2 F4 FFC5h FFC3h FFC1h FFC2h FFC4h FFC6h FC5 FC3 FC1 FCz FC2 FC4 FC6
FTT7h FCC5h FCC3h FCC1h FCC2h FCC4h FCC6h FTT8h C5 C3 C1 Cz C2 C4 C6 TTP7h CCP5h
CCP3h CCP1h CCP2h CCP4h CCP6h TTP8h CP5 CP3 CP1 CPz CP2 CP4 CP6 CPP5h CPP3h CPP1h
CPP2h CPP4h CPP6h P3 P1 Pz P2 P4 PPO1h PPO2h
""".split())
MECH_LABELS = tuple("""
thumb_near thumb_far thumb_index index_near index_far index_middle middle_near middle_far middle_ring ring_near
ring_far ring_little litte_near litte_far thumb_palm wrist_bend roll pitch gesture handPosX handPosY handPosZ
elbowPosX elbowPosY elbowPosZ ShoulderAdductio ShoulderFlexionE ShoulderRotation Elbow ProSupination Wrist GripPressure
""".split())
MECH_MEANING = ("thumb near", "thumb far", "thumb index", "index near", "index far", "index middle", "middle near",
                "middle far", "middle ring", "ring near", "ring far", "ring little", "little near", "little far",
                "thumb palm", "-", "-", "-", "-", "hand X", "hand Y", "hand Z", "elbow X", "elbow Y", "elbow Z",
                "shoulder adduction", "shoulder flexion/extension", "shoulder rotation", "elbow", "pro/supination",
                "wrist flexion/extension", "-")
RATES = (512,) * 64 + (64,) * 32
KIN_DELAY_STEPS = 1  # whole 20 ms steps by which the 64 Hz arm and glove tokens are delayed (see the module text)
STREAM_DELAYS = {"kin": {"steps": KIN_DELAY_STEPS, "seconds": KIN_DELAY_STEPS * common.STEP_S,
                         "why": "a 64 Hz reading may have been acquired up to 7 ticks of the 512 Hz clock (13.7 ms) "
                                "after the time its file position gives it"}}
HEADER_BYTES = 256 * 97
CUES = range(0x600, 0x607)
ANCHOR = {"kind": "single tracker", "note": "hand and elbow positions are anchored to themselves; glove and angle "
          "channels are not positions"}
AXIS_NOTE = {"note": "exoskeleton X, Y, Z as stored; no documented vertical axis or physical unit"}
META = {
    "name": "Upper limb movements can be decoded from the time-domain of low-frequency EEG", "doi": "10.5281/zenodo.834976",
    "species": "human", "sites": 1, "derived": False, "paired": True,
    "events_definition": "movement and rest cues (event codes 0x600-0x606 in each run's GDF event table)",
    "context": {"dataset": DATASET, "species": "human", "task": "cued sustained right-arm and hand movements (motor execution)",
                "body_plan": "human arm and hand", "value_flag": "measured"},
    "streams": [
        {"group": "field", "kind": "eeg", "channels": 61, "rate_hz": 512, "units": "stored values (header physical unit blank)",
         "value_type": "measured", "rows": "shared 10-5 site vocabulary"},
        {"group": "field", "kind": "eog", "channels": 3, "rate_hz": 512, "units": "stored values", "value_type": "measured"},
        {"group": "kin", "kind": "glove_and_exoskeleton", "channels": 27, "rate_hz": 64,
         "units": "native, uncalibrated (header physical unit blank)", "value_type": "measured"},
    ],
    "notes": ["The GDF headers give identity digital-to-physical scaling and blank units, so field band power is in "
              "log(stored unit^2) and the arm channels are in native units.",
              "Five mechanical channels marked '-' in the authors' table are not tokenised.",
              "Some mechanical channels are constant within a run (for example thumb_palm, elbowPosX and shoulder "
              "adduction in S2 run 5); they are kept and carry no variation there."],
}


def _proto_file(paths):
    return Path(paths["run_worktree"]) / "models" / "arm-transfer" / "PROTOCOL.md"


def roster(paths):
    f = _proto_file(paths)
    text = f.read_text()
    assert "The seven fitting participants are S1–S7" in text and "S13–S15 remain in reserve" in text
    roles = {p: "fitting" for p in PEOPLE}
    roles.update({"S%d" % i: "assessment" for i in range(8, 13)})
    roles.update({"S%d" % i: "reserve" for i in range(13, 16)})
    return {"units": PEOPLE, "unit_roles": roles, "training_roles": ["fitting"],
            "rule": "arm-transfer protocol: S1-S7 fitting, S8-S12 assessment, S13-S15 reserve (published file order)",
            "excluded": {"assessment_consumed": ["S%d" % i for i in range(8, 13)],
                         "reserve": ["S%d" % i for i in range(13, 16)]},
            "roster_files": [{"file": "models/arm-transfer/PROTOCOL.md (repository)", "sha256": common.sha256_file(f)},
                             {"file": "transfer-arm-source fitting-receipt.json (earlier source custody)",
                              "sha256": common.sha256_file(Path(paths["ofner_source_record"]) / "fitting-receipt.json")}]}


def channels(paths):
    field = [dict(name="eeg:" + s, kind="eeg", units="log(stored unit^2) / stored unit", source_units="stored (blank)",
                  rate_hz=512, value_type="measured", modality="scalp EEG (field potential)", vocab="eeg1010:" + s,
                  row="shared", site=s) for s in EEG_SITES]
    field += [dict(name="eog:" + n, kind="eog", units="log(stored unit^2) / stored unit", source_units="stored (blank)",
                   rate_hz=512, value_type="measured", modality="electrooculogram (field potential)", vocab=None,
                   row="per-dataset", position=n) for n in ("left", "middle", "right")]
    kin = []
    for i, (lab, meaning) in enumerate(zip(MECH_LABELS, MECH_MEANING)):
        if meaning == "-":
            continue
        kind = "glove_sensor" if i < 15 else ("exoskeleton_position" if "Pos" in lab else "arm_angle")
        kin.append(dict(name="mech:" + lab, kind=kind, units="native (uncalibrated)", value_type="measured", rate_hz=64,
                        meaning=meaning, vocab=None, row="per-dataset"))
    return {"field": field, "kin": kin}


def _local_receipt(paths):
    return json.loads((Path(paths["ofner_source_record"]) / "fitting-receipt.json").read_text())


def _receipt_sha(rec, name):
    def walk(o):
        if isinstance(o, dict):
            if o.get("file") == name or o.get("name") == name or o.get("filename") == name:
                for k in ("sha256", "SHA256"):
                    if k in o:
                        return o[k]
            for k, v in o.items():
                if k == name and isinstance(v, dict) and "sha256" in v:
                    return v["sha256"]
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r:
                    return r
        return None
    return walk(rec)


def jobs(paths, units):
    from fetch_neural import ofner_plan
    record = json.loads((Path(paths["raw"]) / "ofner" / "record.json").read_text())  # the record the P1 fetch used
    plan = {p["key"]: p for p in ofner_plan(record)}
    rec = _local_receipt(paths)
    out = []
    for u in units:
        items = []
        for r in RUNS:
            name = "motorexecution_subject%d_run%d.gdf" % (int(u[1:]), r)
            if r <= 3:
                sha = _receipt_sha(rec, name)
                assert sha, "no earlier sha256 for " + name
                items.append({"run": r, "path": str(Path(paths["ofner_local"]) / name), "sha256": sha})
            else:
                p = plan[name]
                items.append({"run": r, "path": str(Path(paths["raw"]) / "ofner" / name), "md5": p["md5"], "bytes": p["bytes"]})
        out.append((u, items))
    return out


def read_gdf(path):
    b = Path(path).read_bytes()
    assert b[:8] == b"GDF 2.10", "not GDF 2.10"
    hb = struct.unpack_from("<H", b, 184)[0] * 256
    records, num, den, count = struct.unpack_from("<qIIH", b, 236)
    assert count == 96 and hb == HEADER_BYTES and num == den != 0, "unexpected GDF layout"

    def column(off, kind):
        return struct.unpack_from("<%d%s" % (count, kind), b, 256 + count * off)

    labels = tuple(b[256 + 16 * i:272 + 16 * i].decode("ascii").strip() for i in range(count))
    assert labels[:61] in (("eeg",) * 61, EEG_SITES), "scalp order differs from the authors' table"
    assert labels[61:64] in (("eog-r", "eog-m", "eog-l"), ("eog-l", "eog-m", "eog-r")), "unexpected EOG layout"
    assert labels[64:] == MECH_LABELS, "mechanical channel order differs"
    assert column(216, "i") == RATES and column(220, "i") == (17,) * count, "expected 512/64 Hz float64"
    assert column(104, "d") == column(120, "d") == (-250000.,) * count and column(112, "d") == column(128, "d") == (250000.,) * count
    per = sum(RATES)
    data = np.frombuffer(b, "<f8", count=records * per, offset=hb).reshape(records, per)
    fast = data[:, :64 * 512].reshape(records, 64, 512).transpose(0, 2, 1).reshape(-1, 64)
    slow = data[:, 64 * 512:].reshape(records, 32, 64).transpose(0, 2, 1).reshape(-1, 32)
    ev = b[hb + records * per * 8:]
    n_ev = int.from_bytes(ev[1:4], "little")
    assert ev[0] == 1 and struct.unpack_from("<f", ev, 4)[0] == 512.0 and len(ev) == 8 + 6 * n_ev
    pos = np.array(struct.unpack_from("<%dI" % n_ev, ev, 8), np.int64) - 1
    codes = np.array(struct.unpack_from("<%dH" % n_ev, ev, 8 + 4 * n_ev), np.int64)
    eog_order = labels[61:64]
    return fast, slow, pos, codes, eog_order, records


def kin_tokens(xk, n_steps):
    """Arm and glove tokens of one run: [last reading in the step, change from the previous step's last] on the
    file's times (reading j at j / 64 s), delayed by KIN_DELAY_STEPS whole steps (see the module text)."""
    lo, hi = common.step_bounds(len(xk), 64.0, 0.0, n_steps)
    v, m = common.kin_features(xk, lo, hi)
    return common.delay_steps(v, m, KIN_DELAY_STEPS)


def process_unit(paths, unit, items, shared):
    recs, metas, checks = [], [], {}
    keep_mech = [i for i, m in enumerate(MECH_MEANING) if m != "-"]
    for it in items:
        if "sha256" in it:
            d = common.sha256_file(it["path"])
            if d != it["sha256"]:
                raise ValueError("sha256 mismatch " + it["path"])
        else:
            h = hashlib.md5()
            with open(it["path"], "rb") as f:
                for blk in iter(lambda: f.read(1 << 22), b""):
                    h.update(blk)
            if h.hexdigest() != it["md5"] or Path(it["path"]).stat().st_size != it["bytes"]:
                raise ValueError("MD5 or size mismatch " + it["path"])
            d = common.sha256_file(it["path"])
        fast, slow, pos, codes, eog_order, records = read_gdf(it["path"])
        eog = {"eog-l": "left", "eog-m": "middle", "eog-r": "right"}
        order = [eog[e] for e in eog_order]
        eog_cols = [61 + order.index(n) for n in ("left", "middle", "right")]
        xf = np.concatenate([fast[:, :61], fast[:, eog_cols]], axis=1).astype(np.float64)
        dur = float(records)
        S = common.n_steps_for(dur)
        rid = "%s_run%02d" % (unit, it["run"])
        rec = nc.Rec(rid, unit, S)
        v, m = nc.field_features(xf, 512.0, 0.0, S)
        rec.put("field", v, m)
        v, m = kin_tokens(slow[:, keep_mech].astype(np.float64), S)
        rec.put("kin", v, m)
        cue = np.isin(codes, list(CUES)) & (pos >= 0) & (pos < records * 512)
        recs.append(rec)
        metas.append({"source_files": {Path(it["path"]).name: d}, "task": "motor_execution", "condition": None,
                      "session": 1, "run": it["run"], "events": int(cue.sum()), "duration_s": dur,
                      "eog_header_order": list(eog_order)})
        checks[rid] = {"records_s": int(records), "nonfinite_fast": int((~np.isfinite(fast)).sum()),
                       "nonfinite_slow": int((~np.isfinite(slow)).sum()), "cues": int(cue.sum()),
                       "event_codes": sorted({int(c) for c in codes})}
    return recs, metas, checks, {}


def file_audit(paths, results):
    bad = []
    for r in results:
        num = "subject%d_" % int(r["unit"][1:])
        for m in r["recordings"]:
            bad += [f for f in m["source_files"] if num not in f or not f.startswith("motorexecution_")]
    n = sum(len(r["recordings"]) for r in results)
    return {"pass": not bad and n == 70, "recordings": n, "expected_from_protocol": 70, "files_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((f, d) for r in results for m in r["recordings"] for f, d in m["source_files"].items())
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    ck = [c for r in results for c in r["checks"].values()]
    return {
        "Q3_access": {"pass": True, "how": "runs 1-3 local (sha256 against the earlier receipt); runs 4-10 downloaded whole "
                      "at P1 (publisher MD5 and size)"},
        "Q4_clock": {"pass": True, "how": "one GDF file per run; the 512 Hz and 64 Hz channels share its 1 s records. "
                     "Each 64 Hz reading spans 8 ticks of the 512 Hz clock with an undocumented acquisition time inside "
                     "them (up to 13.7 ms after the time its file position gives), so the arm and glove tokens are "
                     "delayed by one whole 20 ms step: the token of step k holds the last reading whose file time lies "
                     "in step k - 1, which was acquired before step k ends in every case",
                     "kin_delay_steps": KIN_DELAY_STEPS, "kin_delay_s": KIN_DELAY_STEPS * common.STEP_S,
                     "recordings_checked": len(ck)},
        "Q5_labels": {"pass": True, "how": "EEG and EOG as stored (identity scaling, blank unit field), arm channels in "
                      "native uncalibrated units; all measured; site names from the authors' table",
                      "nonfinite_samples": sum(c["nonfinite_fast"] + c["nonfinite_slow"] for c in ck)},
        "Q6_causality": {"pass": True, "author_filtering": "amplifier and glove filtering not re-verified; stored samples "
                         "used as recorded", "our_features": "causal"},
    }
