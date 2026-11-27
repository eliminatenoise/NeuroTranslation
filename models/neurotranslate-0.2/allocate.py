#!/usr/bin/env python3
"""Allocation for the NeuroTranslate 0.2 pooled-encoder protocol.

Computes, from identifiers and archive metadata only, every group that can be
fixed before any data value is read:

  - the inner folds of the training individuals of each dataset;
  - the nested people subsets of the quantity-versus-diversity "P" arms;
  - the hash order used to draw the sources of the "D" arms;
  - the fresh evaluation groups E1 (Gait120 S001-S010), E2 (AJILE12
    participants 03-12, calibration and scoring sessions), E3 (MC_Maze full
    and Large training files) and the lab order used for E4 (IBL, conditional);
  - the optional secondary groups B1 and the seen-dataset arm.

Only the Python standard library is used. No recording is opened.

Usage:
  python3 allocate.py                         # print ALLOCATION.json to stdout
  python3 allocate.py --out ALLOCATION.json
  python3 allocate.py --check ALLOCATION.json  # exit 1 unless byte-identical
  python3 allocate.py --gait120-tail TAIL --gait120-tail-offset 1451874994 ...
      adds the E1 member list parsed from the ZIP central directory of
      figshare file 53167640. TAIL is the last 262,144 bytes of that archive
      (one public HTTP range request: bytes=-262144). Only central-directory
      records are parsed; any member bytes in the tail are never inflated.

Without --gait120-tail, --check takes the E1 member list from the file being
checked and compares everything else; with it, the member list is compared too.
"""
import argparse
import hashlib
import json
import struct
import sys

SALT = "pooled-encoder-0.2"


def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rank(units, key):
    """Units sorted by ascending sha256 of key(unit)."""
    return sorted(units, key=lambda u: (h(key(u)), u))


# ---------------------------------------------------------------------------
# Training individuals, copied from the frozen rosters of earlier studies.
# Each list holds only units whose recorded role is fit / train / development
# (or the engineering person of a fitting role). Consumed evaluation groups and
# reserves are absent by construction.
# ---------------------------------------------------------------------------
TRAINING_UNITS = {
    "gait120": {
        "kind": "person",
        "roster_rule": "Gait120 chair-rise roster, role 'development' (salt neurotranslation-gait120-frozen-chair-rise-20261122)",
        "units": ["S011", "S014", "S016", "S018", "S019", "S020", "S022", "S023", "S026", "S027", "S028",
                  "S030", "S031", "S033", "S035", "S036", "S038", "S039", "S041", "S042", "S043", "S045",
                  "S046", "S050", "S052", "S053", "S054", "S055", "S057", "S059", "S061", "S062", "S063",
                  "S064", "S066", "S070", "S071", "S073", "S074", "S076", "S077", "S080", "S085", "S086",
                  "S087", "S088", "S089", "S090", "S091", "S092", "S093", "S095", "S096", "S098", "S102",
                  "S104", "S106", "S107", "S108", "S110", "S111", "S112", "S113", "S115", "S116", "S119"],
    },
    "schreiber_moissenet": {
        "kind": "person",
        "roster_rule": "split-three rule, partition 'train' (ordinals 1-30)",
        "units": ["2014001", "2014002", "2014003", "2014004", "2014005", "2014006", "2014007", "2014008",
                  "2014009", "2014011", "2014013", "2014014", "2014015", "2014016", "2014019", "2014022",
                  "2014024", "2014025", "2014029", "2014030", "2014031", "2014033", "2014034", "2014040",
                  "2014046", "2014048", "2014049", "2014050", "2014051", "2014052"],
    },
    "moreira": {
        "kind": "person",
        "roster_rule": "source split, role 'development'",
        "units": ["1", "6", "8", "10", "11", "12", "13", "14"],
    },
    "izmir": {
        "kind": "person",
        "roster_rule": "roster roles 'fit' and 'engineering'",
        "units": ["S01", "S04", "S07", "S08", "S12", "S15", "S17", "S19", "S20", "S21", "S22", "S23", "S24",
                  "S26", "S28", "S29", "S30"],
    },
    "van_criekinge": {
        "kind": "person",
        "roster_rule": "prospective roster, role 'fit'",
        "units": ["SUBJ024", "SUBJ038", "SUBJ039", "SUBJ040", "SUBJ043", "SUBJ044", "SUBJ061", "SUBJ062",
                  "SUBJ082", "SUBJ096", "SUBJ110", "SUBJ112"],
    },
    "katmah": {
        "kind": "person",
        "roster_rule": "knee-motion fit identifiers 1-40, 0.5 m/s only",
        "units": ["S%d" % i for i in range(1, 41)],
    },
    "ds003739": {
        "kind": "person",
        "roster_rule": "visual-balance stage 'development'",
        "units": ["sub-001", "sub-003", "sub-006", "sub-009", "sub-010", "sub-011", "sub-012", "sub-013",
                  "sub-016", "sub-017", "sub-018", "sub-020", "sub-022", "sub-023", "sub-026", "sub-027",
                  "sub-028", "sub-029"],
    },
    "ofner": {
        "kind": "person",
        "roster_rule": "arm-transfer fitting people S1-S7",
        "units": ["S1", "S2", "S3", "S4", "S5", "S6", "S7"],
    },
    "hyser": {
        "kind": "person",
        "roster_rule": "source manifest role 'TRAIN' (split hyser-random-index-20261119-v1)",
        "units": ["S01", "S05", "S06", "S09", "S10", "S11", "S13", "S15", "S16", "S17", "S19", "S20"],
    },
    "hygrip": {
        "kind": "person",
        "roster_rule": "train manifest, frozen role TRAIN and eligible (group /N withheld by its timing gate)",
        "units": ["/B", "/C", "/D", "/E", "/H", "/I", "/K"],
    },
    "cemhsey": {
        "kind": "person",
        "roster_rule": "pinch source stage 'TRAIN' (S1-S3)",
        "units": ["S1", "S2", "S3"],
    },
    "wtrack": {
        "kind": "animal",
        "roster_rule": "population protocol 'Train' rats plus JS14 data recorded before the start of trip 79",
        "units": ["ER1", "JS14", "JS15", "JS17"],
    },
    "sabes": {
        "kind": "time_block",
        "roster_rule": "cortical-source-mix training files indy_20170131_02 and loco_20170215_02",
        "units": ["indy_20170131_02", "loco_20170215_02"],
    },
}

CONDITIONAL_TRAINING = {
    "area2": {
        "kind": "time_block",
        "condition": "role audit at step P2: only the 290 Han 2017-12-07 trials with fitting or configuration roles in the area2 separate-day study; the 74 assessed trials and every Dryad session stay out",
        "units": ["Han_20171207"],
    },
    "falcon_m1": {
        "kind": "recording",
        "condition": "role audit at step P2: only FALCON M1 'held-in-calib' days that no earlier evaluation used; folds by day computed at P2 with the same rule",
        "units": [],
    },
    "ibl_train": {
        "kind": "animal",
        "condition": "IBL audit and owner confirmation before the freeze: never-referenced mice of labs not drawn for E4; folds computed at P2 with the same rule",
        "units": [],
    },
}

Q_ANCHORS = ["gait120", "ds003739", "ofner", "wtrack"]  # wtrack is replaced by ibl_train if IBL is admitted
P_ARM_DATASETS = ["gait120", "ds003739"]

# ---------------------------------------------------------------------------
# Fresh evaluation groups (identifiers and archive metadata only).
# ---------------------------------------------------------------------------
E1 = {
    "dataset": "gait120",
    "people": ["S%03d" % i for i in range(1, 11)],
    "archive": {"figshare_file_id": 53167640, "name": "Gait120_001_to_010.zip", "bytes": 1452137138,
                "md5": "9f73435302c9cc2c1b9bcef875085985"},
    "central_directory": {"offset": 1451983325, "bytes": 153791, "entries": 1208},
    "emg_scaling_trial": "LevelWalking Trial01 of each person (used only to scale that person's EMG; never scored)",
}

# AJILE12 (DANDI 000055, version 0.220127.0436): every session of participants 03-12.
AJILE12_SESSIONS = {
    "sub-03": [3, 4, 5, 6], "sub-04": [3, 4, 5, 6, 7], "sub-05": [3, 4, 7], "sub-06": [3, 4, 5, 6, 7],
    "sub-07": [3, 4, 5, 6, 7], "sub-08": [3, 4, 5, 6, 7], "sub-09": [3, 4, 5, 6, 7], "sub-10": [3, 4, 5, 6, 7],
    "sub-11": [3, 4, 5, 6, 7], "sub-12": [3, 4, 5, 6, 7],
}
AJILE12_ASSETS = {
    ("sub-03", 3): ("5122cc42-981c-4fa3-92f4-5f9ccfb8c092", 12993721651, "cb47e04883272a5d8152530bdf3655d2a79119ab032d4cf8d437a3d569c6fcd2"),
    ("sub-03", 4): ("263d8a0a-167b-4a35-83b6-f924a455178f", 13013447892, "e7f8fee54bb5368d3718e622513c3792670d11bc4eaee0fc5bfc175dd58d4d46"),
    ("sub-04", 3): ("554a74cc-824b-4a02-8b23-63aa51ac2369", 8423945777, "a982a9ce4718c1d86aff4943306c6a4e936a64b44bcc899ac10d9c8c71da646e"),
    ("sub-04", 4): ("d914679e-dd71-4c7e-86be-92eaebfff0cd", 13233736922, "f7c997d11f687c7f3634dd62f1bab03ecaba25d95f9cda1e4c4fab5f10353ade"),
    ("sub-05", 3): ("c4674f3f-fd0d-471c-a9a4-a0d0eeaed105", 17155594911, "056ee3ce118a30b1db7f9486d7fe1d7bb15107c0d974d94524b3cea8e47196c6"),
    ("sub-05", 4): ("9c88256e-3088-4bbb-b6c5-b4f0e25e4129", 17170906865, "d2a1c4708dbc29a1db21afcd959583bbacc1898e168ea67fef993b9db3a30f61"),
    ("sub-06", 3): ("87c2f790-8f6c-4e73-a54f-f275af6a2680", 8620317009, "8940fed2ac6239b7f5667547b5ace7828d662fe687dc1a1a2f05e75826bf17e4"),
    ("sub-06", 4): ("eea59c28-3e69-4fb6-a6c0-fbd57dd303cc", 12885238804, "2f688c4850e5cc633cce2b4847e8cf5d5d6d910b0219739817f7524a6198fd0b"),
    ("sub-07", 3): ("5791a9f3-5c0c-484b-b690-b5ce9fea589e", 10021863235, "a80285a4fd829aaba58c8b36fd670c6594d3d98708aa32282e962f5a07d6728c"),
    ("sub-07", 4): ("dbf11bb5-e73c-43aa-8f9e-d87807e09971", 10395219939, "2e6bc139cf5cfe913283a17d451474ea3b2563cc0beda41edbd19b0cd4fc0be3"),
    ("sub-08", 3): ("7de9b149-2994-455e-a8c6-5e5893245baf", 14919492016, "95ab8bb566dc23f7153946f0a67fd2c6641bc70662ee6e7fd2ba0b9483e41de6"),
    ("sub-08", 4): ("07fe6ecc-1a51-4655-a925-dcc3ecb6183f", 14898053963, "04029121342ab4f56dc5b8b487e166bfd49ff752012ccf4fd535e083b8e611cc"),
    ("sub-09", 3): ("b5b123ea-557f-4b69-ad11-8b3ff6bc9bd5", 19794037714, "2635ebb93567752019ed69e1d2951e53c2d137a1e038edaf7df2c127f3ba4778"),
    ("sub-09", 4): ("4d960b31-6a46-4578-a620-2dfdad46bf55", 19741644394, "0d220f2c055dc20f28620f9510433de67c343abebad5d24185db818de8d332d4"),
    ("sub-10", 3): ("e22abf61-170a-4d52-89f5-27e394e04afa", 19715930499, "6ae08347daed71deebe677798cab7db69e04be728b18ba07a645c6add2942486"),
    ("sub-10", 4): ("0d4e2bea-fd00-405f-923c-86141269c39a", 19723279309, "6ae359fd31373e825b456605426135040859c566b04030bbd25ba40501b0f308"),
    ("sub-11", 3): ("0b4aac2b-e080-4854-b792-4ea4359e2044", 17160159566, "42ce126cdf84ae9224235dffc4442fd9793f07b94526c7f88ce80f5971424a22"),
    ("sub-11", 4): ("1fc40baf-4007-4d96-9d6a-61213b14aecd", 16985717017, "f3f145c11adeae27ca7e3110f94dffca073b9737954a9de4d93441f2aafe0ec4"),
    ("sub-12", 3): ("3db4e507-c2de-4ab3-a052-88d9800f36d0", 19928317351, "e0f2fe25556c77867793c1bdf95c232b33b338b4d5c4bfcc320803e04f087616"),
    ("sub-12", 4): ("257cec4c-84ba-4047-815c-a790d4f51d7e", 19946639193, "7f1767df98a99a78022f8c5c3b988102356af81232ffbc5d81fb971e0906bb52"),
}
AJILE12_OWNER_OPTION_KEEP_BACK = ["sub-08", "sub-09", "sub-10", "sub-11", "sub-12"]

E3_FILES = [
    {"dandiset": "000128", "version": "0.220113.0400", "session": "full", "recorded": "2009-09-25",
     "asset_id": "26e85f09-39b7-480f-b337-278a8f034007",
     "path": "sub-Jenkins/sub-Jenkins_ses-full_desc-train_behavior+ecephys.nwb", "bytes": 690612247,
     "sha256": "a27f84f9c31f077011062fd99a6ced199fdf19e656151f056c3c6244a408a3c4"},
    {"dandiset": "000138", "version": "0.220113.0407", "session": "large", "recorded": "2009-10-06",
     "asset_id": "e67b57b2-e9ad-4d95-b9e3-1262997360dc",
     "path": "sub-Jenkins/sub-Jenkins_ses-large_desc-train_behavior+ecephys.nwb", "bytes": 148590536,
     "sha256": "1188ddf5b822dd9ac49afb8916f4b42a85867613cf7f169d0b04a1d1aeecd700"},
]

IBL_LABS = ["angelakilab", "churchlandlab", "churchlandlab_ucla", "cortexlab", "danlab", "hausserlab",
            "hoferlab", "mainenlab", "mrsicflogellab", "steinmetzlab", "wittenlab", "zadorlab"]

GAIT120_VALIDATION = ["S015", "S017", "S021", "S029", "S034", "S037", "S044", "S048", "S056", "S060", "S065",
                      "S067", "S075", "S079", "S082", "S084", "S094", "S097", "S103", "S105", "S114", "S118"]
GAIT120_CONFIRMATION = ["S012", "S013", "S024", "S025", "S032", "S040", "S047", "S049", "S051", "S058", "S068",
                        "S069", "S072", "S078", "S081", "S083", "S099", "S100", "S101", "S109", "S117", "S120"]



def round_half_up(x):
    return int(x + 0.5)


def inner_folds(name, spec):
    units = spec["units"]
    out = {"kind": spec["kind"], "n_units": len(units)}
    if spec["kind"] in ("person", "animal", "recording") and len(units) >= 3:
        ordered = rank(units, lambda u: "%s|fold|%s|%s" % (SALT, name, u))
        rows = []
        for r, u in enumerate(ordered):
            rows.append({"unit": u, "sha256": h("%s|fold|%s|%s" % (SALT, name, u)), "rank": r, "fold": r % 5})
        out["rule"] = "rank units by ascending sha256('%s|fold|' + dataset + '|' + unit); fold = rank mod 5; fold 0 is the inner-validation fold" % SALT
        out["rows"] = rows
        out["inner_validation"] = [x["unit"] for x in rows if x["fold"] == 0]
        out["inner_training"] = sorted(x["unit"] for x in rows if x["fold"] != 0)
    else:
        out["rule"] = ("fewer than 3 independent individuals or recordings: each recording is cut into 5 blocks of equal duration in time order; "
                       "block b is fold b; fold 4 (the latest block) is the inner-validation fold; a 1 s gap is dropped at each block boundary")
        out["recordings"] = units
    return out


def p_subsets(name, inner_training):
    ordered = rank(inner_training, lambda u: "%s|P|%s|%s" % (SALT, name, u))
    n = len(ordered)
    levels = sorted({max(2, round_half_up(n / 16.0)), round_half_up(n / 4.0), n})
    return {"rule": "rank inner-training people by ascending sha256('%s|P|' + dataset + '|' + unit); level L takes the first L (nested); levels = max(2, round(n/16)), round(n/4) and n, rounding halves up" % SALT,
            "order": ordered, "levels": {str(L): ordered[:L] for L in levels}}


def d_orders(candidates):
    out = {}
    for k in (2, 4, 8):
        for draw in (0, 1, 2):
            key = "k%d|draw%d" % (k, draw)
            out[key] = rank(candidates, lambda d: "%s|D|%s|%s" % (SALT, key, d))
    return {"rule": "for k in {2,4,8} and draw in {0,1,2}: order candidate sources by ascending sha256('%s|D|k' + k + '|draw' + draw + '|' + dataset); the arm uses the first k sources in that order that are eligible (at least W_max/8 inner-training windows, counted at P2)" % SALT,
            "orders": out}


def e2():
    rows = []
    for s in sorted(AJILE12_SESSIONS):
        ses = sorted(AJILE12_SESSIONS[s])
        cal, score = ses[0], ses[1]
        a_cal, a_score = AJILE12_ASSETS[(s, cal)], AJILE12_ASSETS[(s, score)]
        rows.append({"participant": s,
                     "calibration": {"session": cal, "asset_id": a_cal[0], "bytes": a_cal[1], "sha256": a_cal[2],
                                     "path": "%s/%s_ses-%d_behavior+ecephys.nwb" % (s, s, cal)},
                     "scoring": {"session": score, "asset_id": a_score[0], "bytes": a_score[1], "sha256": a_score[2],
                                 "path": "%s/%s_ses-%d_behavior+ecephys.nwb" % (s, s, score)},
                     "other_sessions_never_opened": ses[2:]})
    return {"dataset": "AJILE12, DANDI 000055 version 0.220127.0436",
            "rule": "participants 03-12; calibration = lowest-numbered session; scoring = next-numbered session",
            "rows": rows,
            "owner_option": {"keep_back": AJILE12_OWNER_OPTION_KEEP_BACK,
                             "then_scored": [r["participant"] for r in rows if r["participant"] not in AJILE12_OWNER_OPTION_KEEP_BACK]},
            "window_rule": "for k = 0, 1, 2, ...: candidate issue frame = int(sha256('%s|ajile12|' + participant + '|ses-' + session + '|' + k), 16) mod n_frames; accept if eligible (protocol section 7.2) and at least 2 s from every accepted issue time; stop at 600 accepted or k = 200000" % SALT}


def e4_lab_order():
    ordered = rank(IBL_LABS, lambda l: "%s|ibl-bwm-2023_12|lab|%s" % (SALT, l))
    return {"rule": "rank labs by ascending sha256('%s|ibl-bwm-2023_12|lab|' + lab); after the IBL audit, the first 3 labs in this order with at least 4 never-referenced mice are evaluation labs; never-referenced mice of every other lab may enter training" % SALT,
            "roster": "2023_12_bwm_release.csv at int-brain-lab/paper-brain-wide-map commit 118fc36cb3602934466ad2c6087c2b3b441f9f1f, sha256 db9edfc6f5d92a4df81d488bfb1068f43526a13717bb8fc7da2aecdd28876ac4",
            "order": [{"lab": l, "sha256": h("%s|ibl-bwm-2023_12|lab|%s" % (SALT, l))} for l in ordered]}


def adapter_folds_gait120():
    units = TRAINING_UNITS["gait120"]["units"]
    ordered = rank(units, lambda u: "%s|adapter-fold|gait120|%s" % (SALT, u))
    return {"rule": "E1 adapter penalty folds: rank the 66 Gait120 development people by ascending sha256('%s|adapter-fold|gait120|' + unit); fold = rank mod 5" % SALT,
            "folds": {str(f): [u for r, u in enumerate(ordered) if r % 5 == f] for f in range(5)}}


def parse_tail(path, offset):
    b = open(path, "rb").read()
    i = b.rfind(b"PK\x05\x06")
    j = b.rfind(b"PK\x06\x06")
    cd_size, = struct.unpack("<I", b[i + 12:i + 16])
    cd_off, = struct.unpack("<I", b[i + 16:i + 20])
    if j >= 0:
        cd_size, = struct.unpack("<Q", b[j + 40:j + 48])
        cd_off, = struct.unpack("<Q", b[j + 48:j + 56])
    p = cd_off - offset
    ents = []
    while b[p:p + 4] == b"PK\x01\x02":
        fields = struct.unpack("<IHHHHHHIIIHHHHHII", b[p:p + 46])
        crc, csize, usize, nl, el, cl, off = fields[7], fields[8], fields[9], fields[10], fields[11], fields[12], fields[16]
        name = b[p + 46:p + 46 + nl].decode("utf-8")
        extra = b[p + 46 + nl:p + 46 + nl + el]
        q = 0
        while q + 4 <= len(extra):
            hid, hl = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:
                vals = extra[q + 4:q + 4 + hl]
                k = 0
                if usize == 0xFFFFFFFF:
                    usize, = struct.unpack("<Q", vals[k:k + 8]); k += 8
                if csize == 0xFFFFFFFF:
                    csize, = struct.unpack("<Q", vals[k:k + 8]); k += 8
                if off == 0xFFFFFFFF:
                    off, = struct.unpack("<Q", vals[k:k + 8]); k += 8
            q += 4 + hl
        ents.append((name, "%08x" % crc, csize, usize, off))
        p += 46 + nl + el + cl
    return cd_off, cd_size, ents


def e1_members(path, offset):
    cd_off, cd_size, ents = parse_tail(path, offset)
    keep = []
    for name, crc, csize, usize, off in sorted(ents, key=lambda e: e[0]):
        if name.endswith("/"):
            continue
        parts = name.split("/")
        if parts[1] == "EMG" and parts[-1] != "RawData.mat":
            continue  # ProcessedData.mat is not used
        keep.append([name, crc, csize, usize, off])
    listing = "\n".join("%s %s %d %d" % (m[0], m[1], m[2], m[3]) for m in keep)
    summary = {}
    for m in keep:
        parts = m[0].split("/")
        person, kind = parts[0], parts[1]
        task = parts[2] if kind in ("MotionCapture", "JointAngle") else "-"
        key = "%s|%s|%s" % (person, kind, task)
        s = summary.setdefault(key, [0, 0])
        s[0] += 1
        s[1] += m[2]
    return {"central_directory": {"offset": cd_off, "bytes": cd_size},
            "member_list_sha256": hashlib.sha256(listing.encode("utf-8")).hexdigest(),
            "member_list_format": "one line per member, sorted by name: name crc32 compressed_bytes bytes, joined by newlines",
            "members_used": len(keep),
            "compressed_bytes_used": sum(m[2] for m in keep),
            "per_person_kind_task": {k: {"members": v[0], "compressed_bytes": v[1]} for k, v in sorted(summary.items())},
            "member_columns": ["name", "crc32", "compressed_bytes", "bytes", "local_header_offset"],
            "members": ["%s %s %d %d %d" % tuple(m) for m in keep]}


def build(args):
    alloc = {
        "schema": "neurotranslate-0.2-pooled-encoder-allocation",
        "version": 1,
        "salt": SALT,
        "reads_data_values": False,
        "inner_folds": {name: inner_folds(name, spec) for name, spec in TRAINING_UNITS.items()},
        "conditional_training": CONDITIONAL_TRAINING,
        "leave_one_dataset_out": {"rule": "each wave-1 dataset in turn is left out of training; its adapter is fitted on its inner-training units and scored on its inner-validation units",
                                  "datasets": sorted(TRAINING_UNITS)},
    }
    alloc["roster_rules"] = {name: spec["roster_rule"] for name, spec in TRAINING_UNITS.items()}
    p = {}
    for name in P_ARM_DATASETS:
        p[name] = p_subsets(name, alloc["inner_folds"][name]["inner_training"])
    alloc["quantity_diversity"] = {
        "q_anchors": Q_ANCHORS,
        "q_anchor_substitution": "if IBL training mice are admitted before the freeze, ibl_train replaces wtrack as the fourth anchor",
        "q_window_rule": "within an anchor's inner-training units, order its non-overlapping 1.2 s windows by ascending sha256('%s|Q|' + dataset + '|' + window_id) and take the first W (nested levels W_max/16, W_max/4, W_max)" % SALT,
        "w_max_rule": "W_max = the smallest number of unique inner-training windows in any Q anchor, rounded down to a power of 2 (computed at P2 from MIXTURE-MANIFEST.json)",
        "p_arms": p,
        "p_window_rule": "W_P = the largest power of 2 not above min(W_max/4, windows of the smallest P level of that dataset); each P arm draws W_P windows, equal shares per person as far as available, in the q_window_rule order",
        "d_arms": d_orders(sorted(TRAINING_UNITS)),
        "d_candidate_note": "conditional sources (area2, falcon_m1, ibl_train) join the candidate list only if admitted before the freeze; the orders are then recomputed with the same rule and recorded in MIXTURE-MANIFEST.json",
    }
    e1 = dict(E1)
    if args.gait120_tail:
        e1["members"] = e1_members(args.gait120_tail, args.gait120_tail_offset)
    alloc["evaluation"] = {
        "E1": e1,
        "E2": e2(),
        "E3": {"dataset": "MC_Maze (Neural Latents Benchmark), Jenkins", "files": E3_FILES,
               "rule": "adapt on the NLB 'train' trials and score on the NLB 'val' trials of each training file; the desc-test files are never opened"},
        "E4_conditional": e4_lab_order(),
    }
    alloc["secondary"] = {
        "B1": {"dataset": "gait120", "people_validation": GAIT120_VALIDATION, "people_confirmation": GAIT120_CONFIRMATION,
               "tasks": ["LevelWalking", "SlopeAscent", "SlopeDescent", "StairAscent", "StairDescent"],
               "label": "people already used in another study's evaluation, new tasks"},
        "seen_dataset_arm": {"dataset": "AJILE12", "participant": "sub-01", "session": 3,
                             "scored_on": "E2 only"},
        "A4": {"dataset": "Camargo et al. lower-limb biomechanics", "status": "needs protocol version 2 after a person-overlap check against 10.35090/gatech/70296 and a licence check"},
    }
    alloc["adapter_folds"] = {"E1": adapter_folds_gait120()}
    return alloc


def dumps(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check")
    ap.add_argument("--gait120-tail")
    ap.add_argument("--gait120-tail-offset", type=int, default=1451874994)
    args = ap.parse_args()
    alloc = build(args)
    if args.check:
        with open(args.check, "r", encoding="utf-8") as f:
            ref = json.load(f)
        if not args.gait120_tail:
            alloc["evaluation"]["E1"]["members"] = ref["evaluation"]["E1"].get("members")
        same = dumps(alloc) == dumps(ref)
        print("identical" if same else "DIFFERENT")
        sys.exit(0 if same else 1)
    text = dumps(alloc)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
