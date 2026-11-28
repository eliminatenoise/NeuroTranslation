"""OpenNeuro ds003739 1.0.3 (perturbed beam walking, CC0): the 18 people of the visual-balance stage
'development', all four sessions each (pull-stand, pull-walk, rotate-stand, rotate-walk).

Roster: the visual-balance roster rule (pilot sub-001, then the other 29 participants ordered by
sha256('balance-stance-20261121:' + id); development = pilot + first 17, assessment = next 6 (consumed),
reserve = next 6 (never fetched)), recomputed here from the 30 BIDS participants of the pinned catalogue
and compared with the earlier development receipt. Session 4 of every development person is the earlier
local copy (sha256 checked against that receipt); sessions 1-3 were downloaded at P1 (MD5 and size checked
against the git-annex keys, sha256 recorded). Sidecar text files are read from the pinned git catalogue
and their git blob hashes are checked. The 6 assessment people's local files are never opened.

One EEGLAB .set/.fdt per session holds every channel on one 256 Hz clock: 128 EEG (Biosemi A1-D32;
author-preprocessed: 1 Hz high-pass, line-noise removal, common median reference), 3 EOG, 10 EMG (neck,
and four leg muscles per side), 6 motion-capture coordinates (sacrum and head, mm) and 2 load cells (N).
Tokens: field = 128 EEG + 3 EOG; emg = 10; kin = 6 mocap coordinates. The load cells are not tokenised:
the protocol lists EEG, EMG, EOG and motion capture for this dataset.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

import common
import neural_common as nc

DATASET = "ds003739"
KIND = "person"
FS = 256.0
SESSIONS = {"ses-01": "pullstand", "ses-02": "pullwalk", "ses-03": "rotatestand", "ses-04": "rotatewalk"}
EMG_MUSCLES = {
    "L_neck_emg": ("L", None, "neck"), "R_neck_emg": ("R", None, "neck"),
    "L_leg_emg_tibialis_anterior": ("L", "tibialis anterior", None), "L_leg_emg_soleus": ("L", "soleus", None),
    "L_leg_emg_medial_gastrocnemius": ("L", "gastrocnemius medialis", None),
    "L_leg_emg_peroneus_longus": ("L", "peroneus longus", None),
    "R_leg_emg_tibialis_anterior": ("R", "tibialis anterior", None), "R_leg_emg_soleus": ("R", "soleus", None),
    "R_leg_emg_medial_gastrocnemius": ("R", "gastrocnemius medialis", None),
    "R_leg_emg_peroneus_longus": ("R", "peroneus longus", None),
}
EOG = ["R_horizontal_eog", "L_horizontal_eog", "L_vertical_eog"]
MOCAP = {"Mocap_sacrum_mediolateral": ("sacrum", "x"), "Mocap_sacrum_anteriorposterior": ("sacrum", "y"),
         "Mocap_sacrum_superiorinferior": ("sacrum", "z"), "Mocap_head_mediolateral": ("head", "x"),
         "Mocap_head_anteriorposterior": ("head", "y"), "Mocap_head_superiorinferior": ("head", "z")}
NOT_TOKENISED = ["L_load_cell", "R_load_cell"]
ANCHOR = {"kind": "pelvis", "markers": ["sacrum"], "note": "the sacrum is the only pelvis marker; the head marker is kept as recorded"}
AXIS_NOTE = {"rotation": np.eye(3).tolist(), "note": "x mediolateral, y anterior-posterior, z superior-inferior as named "
             "by the authors' channel labels; the sign conventions are not documented"}
META = {
    "name": "Perturbed beam-walking task (OpenNeuro ds003739)", "doi": "10.18112/openneuro.ds003739.v1.0.3",
    "species": "human", "sites": 1, "derived": True, "paired": True,
    "events_definition": "author-annotated perturbation onsets (events.tsv rows with trial_type 'stimulus': pull_left, "
                         "pull_right, rotate_cw, rotate_ccw)",
    "context": {"dataset": DATASET, "species": "human", "task": "standing and beam walking with pull or visual-rotation perturbations",
                "body_plan": "human biped", "value_flag": "derived (author-preprocessed EEG) and measured"},
    "streams": [
        {"group": "field", "kind": "eeg", "channels": 128, "rate_hz": 256, "units": "microV (source); log band power and low-pass value per step",
         "value_type": "derived (author-preprocessed: 1 Hz high-pass, line-noise removal, common median reference)",
         "rows": "learned per recording (Biosemi A1-D32 labels are not 10-10 names); digitised positions kept"},
        {"group": "field", "kind": "eog", "channels": 3, "rate_hz": 256, "units": "microV", "value_type": "measured (in the author-preprocessed file)"},
        {"group": "emg", "kind": "surface_emg", "channels": 10, "rate_hz": 256, "units": "microV (source); log RMS per step",
         "value_type": "measured (in the author-preprocessed file, 256 Hz)"},
        {"group": "kin", "kind": "marker", "channels": 6, "rate_hz": 256, "units": "mm",
         "value_type": "measured (sacrum and head positions on the EEG clock)"},
    ],
    "notes": ["The two load cells (N) in the same files are not tokenised; the protocol lists EEG, EMG, EOG and motion "
              "capture for this dataset.",
              "EMG at 256 Hz: the causal 20 Hz high-pass and the log RMS per step use about 5 samples per step.",
              "The 70-150 Hz band is masked (sampling below 400 Hz).",
              "Motion-capture coordinates have session means within a few mm of zero; they may be high-pass filtered "
              "by the authors (not documented), so they carry movement about a moving mean, not absolute position."],
}


def _cache(paths):
    return Path(paths["ds003739_cache"])


def _catalogue_tree(paths):
    from fetch_neural import ds_tree
    return ds_tree(paths)


def roster(paths):
    from fetch_neural import ds_roster
    cat, tree = _catalogue_tree(paths)
    people = sorted({n.split("/")[0] for n in tree if n.startswith("sub-") and "/" in n})
    ros = ds_roster(people)
    rec = _cache(paths) / "development-files.json"
    receipt = json.loads(rec.read_text())
    assert sorted(receipt["selected"]) == sorted(ros["development"]) and receipt["stage"] == "development"
    integ = Path(paths["run_worktree"]) / "models" / "visual-balance" / "source" / "integrity.json"
    integrity = json.loads(integ.read_text())
    assert integrity["stages"]["development"]["totals"]["catalogue_selected"] == 18
    unit_roles = {p: "development" for p in ros["development"]}
    unit_roles.update({p: "assessment" for p in ros["assessment"]})
    unit_roles.update({p: "reserve" for p in ros["reserve"]})
    return {"units": sorted(ros["development"]), "unit_roles": unit_roles, "training_roles": ["development"],
            "rule": "visual-balance roster: pilot sub-001 plus the first 17 of the other participants by sha256('balance-stance-20261121:' + id)",
            "excluded": {"assessment_consumed": sorted(ros["assessment"]), "reserve": sorted(ros["reserve"])},
            "roster_files": [{"file": "ds003739 development receipt (development-files.json, earlier study)",
                              "sha256": common.sha256_file(rec)},
                             {"file": "models/visual-balance/source/integrity.json (repository)", "sha256": common.sha256_file(integ)},
                             {"file": "ds003739 1.0.3 git catalogue", "commit": "f15449b6aecb83044b49a1798955e8a212a68fc1"}]}


def _channels_tsv_names(paths):
    p = _cache(paths) / "raw" / "sub-001" / "ses-04" / "eeg" / "sub-001_ses-04_task-rotatewalk_channels.tsv"
    rows = [l.split("\t") for l in p.read_text().splitlines()[1:] if l.strip()]
    return [(r[0], r[1], r[2]) for r in rows]


def channels(paths):
    from vocab import muscle_key
    rows = _channels_tsv_names(paths)
    eeg = [n for n, t, u in rows if t == "EEG"]
    assert len(eeg) == 128
    field = [dict(name=n, kind="eeg", units="log microV^2 (band power) / microV (low-pass)", source_units="microV",
                  rate_hz=256, value_type="derived", modality="scalp EEG (field potential)", vocab=None,
                  row="per-recording", label_system="Biosemi ABCD 128", positions="digitised per session (recording metadata)")
             for n in eeg]
    field += [dict(name=n, kind="eog", units="log microV^2 / microV", source_units="microV", rate_hz=256,
                   value_type="measured", modality="electrooculogram (field potential)", vocab="eog:" + n, row="shared")
              for n in EOG]
    emg = []
    for n, (side, muscle, other) in EMG_MUSCLES.items():
        emg.append(dict(name=n, kind="surface_emg", units="log microV (log RMS per 20 ms step)", source_units="microV",
                        rate_hz=256, value_type="measured", modality="surface EMG (muscle electrical activity, not a nerve recording)",
                        muscle=muscle or other, side=side, vocab=muscle_key(side, muscle) if muscle else None,
                        row="shared" if muscle else "per-dataset"))
    kin = [dict(name="%s_%s" % (lm, ax), kind="marker", units="mm", value_type="measured", source_channel=n,
                landmark=lm, axis=ax, vocab="landmark:%s:%s" % (lm, ax), row="shared",
                filtering="on the 256 Hz EEG clock; means within a few mm of zero in every session, so the recording's "
                "stated 1 Hz high-pass may have been applied (not documented)")
           for n, (lm, ax) in MOCAP.items()]
    return {"field": field, "emg": emg, "kin": kin}


def _git_blob_ok(path, blob):
    b = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest() == blob


def jobs(paths, units):
    cat, tree = _catalogue_tree(paths)
    receipt = json.loads((_cache(paths) / "development-files.json").read_text())
    fetched = json.loads((Path(paths["raw"]) / "ds003739" / "FETCH-RESULT.json").read_text())
    plan = {p["path"]: p for p in fetched["plan"]}
    out = []
    for u in units:
        items = []
        for ses, task in SESSIONS.items():
            stem = "%s/%s/eeg/%s_%s_task-%s" % (u, ses, u, ses, task)
            item = {"session": ses, "task": task, "stem": stem}
            if ses == "ses-04":
                base = _cache(paths) / "raw"
                item["set"], item["fdt"] = str(base / (stem + "_eeg.set")), str(base / (stem + "_eeg.fdt"))
                item["expect"] = {k: receipt["files"][stem + "_eeg." + k]["sha256"] for k in ("set", "fdt")}
                item["sidecar_root"] = str(base)
                item["sidecar_expect"] = {s: ("sha256", receipt["files"][stem + "_" + s]["sha256"])
                                          for s in ("channels.tsv", "events.tsv")}
            else:
                base = Path(paths["raw"]) / "ds003739"
                item["set"], item["fdt"] = str(base / (stem + "_eeg.set")), str(base / (stem + "_eeg.fdt"))
                item["expect_md5"] = {k: plan[stem + "_eeg." + k]["md5"] for k in ("set", "fdt")}
                item["sidecar_root"] = str(cat)
                item["sidecar_expect"] = {s: ("git_blob", tree[stem + "_" + s][1]) for s in ("channels.tsv", "events.tsv")}
            items.append(item)
        out.append((u, items))
    return out


def _digest(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def read_set(set_path, fdt_path):
    import scipy.io as sio
    m = sio.loadmat(set_path, squeeze_me=True, struct_as_record=False)
    E = m["EEG"]
    nb, pnts, srate = int(E.nbchan), int(E.pnts), float(E.srate)
    labels = [c.labels for c in E.chanlocs]
    raw = np.fromfile(fdt_path, dtype="<f4")
    assert raw.size == nb * pnts, (raw.size, nb, pnts)
    x = raw.reshape(pnts, nb)  # EEGLAB writes channel-fastest
    return x, srate, labels, float(E.xmin)


def process_unit(paths, unit, items, shared):
    recs, metas, checks = [], [], {}
    field_names = [c["name"] for c in shared["field"]]
    emg_names = [c["name"] for c in shared["emg"]]
    kin_src = [c["source_channel"] for c in shared["kin"]]
    for it in items:
        files = {}
        for k in ("set", "fdt"):
            if "expect" in it:
                d = common.sha256_file(it[k])
                if d != it["expect"][k]:
                    raise ValueError("sha256 mismatch " + it[k])
                files[Path(it[k]).name] = d
            else:
                if _digest(it[k], "md5") != it["expect_md5"][k]:
                    raise ValueError("MD5 mismatch " + it[k])
                files[Path(it[k]).name] = common.sha256_file(it[k])
        side = {}
        for s, (kind, want) in it["sidecar_expect"].items():
            p = Path(it["sidecar_root"]) / (it["stem"] + "_" + s)
            ok = common.sha256_file(p) == want if kind == "sha256" else _git_blob_ok(p, want)
            if not ok:
                raise ValueError("sidecar check failed " + str(p))
            side[s] = p.read_text()
            files[p.name] = common.sha256_file(p)
        tsv = [l.split("\t") for l in side["channels.tsv"].splitlines()[1:] if l.strip()]
        x, srate, labels, xmin = read_set(it["set"], it["fdt"])
        assert srate == FS and xmin == 0.0 and labels == [r[0] for r in tsv], "channel table differs"
        units_by_name = {r[0]: r[2] for r in tsv}
        col = {n: i for i, n in enumerate(labels)}
        n = x.shape[0]
        dur = n / FS
        S = common.n_steps_for(dur)
        rid = "%s_%s_%s" % (unit, it["session"], it["task"])
        rec = nc.Rec(rid, unit, S)
        xf = x[:, [col[c] for c in field_names]].astype(np.float64)
        v, m = nc.field_features(xf, FS, 0.0, S)
        rec.put("field", v, m)
        lo, hi = common.step_bounds(n, FS, 0.0, S)
        xe = x[:, [col[c] for c in emg_names]].astype(np.float64)
        v, m = common.emg_features(xe, FS, lo, hi)
        rec.put("emg", v, m)
        xk = x[:, [col[c] for c in kin_src]].astype(np.float64)
        v, m = common.kin_features(xk, lo, hi)
        rec.put("kin", v, m)
        ev = [l.split("\t") for l in side["events.tsv"].splitlines()[1:] if l.strip()]
        stim = [e for e in ev if e[3] == "stimulus" and 0 <= float(e[0]) < dur]
        recs.append(rec)
        metas.append({"source_files": files, "task": it["task"], "session": it["session"],
                      "condition": it["task"].replace("stand", "-stand").replace("walk", "-walk"),
                      "events": len(stim), "event_types": sorted({e[6] for e in stim}), "duration_s": round(dur, 4)})
        checks[rid] = {"samples": int(n), "channels_in_file": len(labels), "nonfinite_samples": int((~np.isfinite(x)).sum()),
                       "units": {k: sorted({units_by_name[c] for c in v}) for k, v in
                                 (("field", field_names), ("emg", emg_names), ("kin", kin_src))},
                       "not_tokenised_channels": [c for c in NOT_TOKENISED if c in col]}
    return recs, metas, checks, {}


def file_audit(paths, results):
    bad = []
    for r in results:
        for m in r["recordings"]:
            bad += [f for f in m["source_files"] if not f.startswith(r["unit"] + "_")]
    n = sum(len(r["recordings"]) for r in results)
    return {"pass": not bad and n == 72, "recordings": n, "expected_from_protocol": 72, "files_outside_unit": bad}


def source_file_summary(results):
    rows = sorted((f, d) for r in results for m in r["recordings"] for f, d in m["source_files"].items())
    return {"files": len(rows), "file_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    ck = [c for r in results for c in r["checks"].values()]
    units_ok = all(c["units"]["field"] == ["microV"] and c["units"]["emg"] == ["microV"] and c["units"]["kin"] == ["mm"]
                   for c in ck)
    return {
        "Q3_access": {"pass": True, "how": "session 4 local (sha256 against the earlier receipt); sessions 1-3 downloaded "
                      "whole at P1 (annex MD5 and size); sidecars from the pinned git catalogue (blob hashes)"},
        "Q4_clock": {"pass": all(c["channels_in_file"] == 149 for c in ck), "how": "one EEGLAB file per session; every "
                     "channel (EEG, EOG, EMG, motion capture) shares the file's 256 Hz sample grid",
                     "recordings_checked": len(ck)},
        "Q5_labels": {"pass": units_ok, "how": "units from channels.tsv: EEG, EOG, EMG microV; motion capture mm; EEG "
                      "labelled derived (author-preprocessed), EOG/EMG/motion capture measured; EMG is muscle activity, "
                      "not a nerve recording", "nonfinite_samples": sum(c["nonfinite_samples"] for c in ck)},
        "Q6_causality": {"pass": True, "author_filtering": "EEG: 1 Hz high-pass, line-noise removal (cleanline) and "
                         "common median reference by the authors (phase of the high-pass not documented; treated as "
                         "possibly non-causal); motion capture on the EEG clock with session means within a few mm of "
                         "zero, so it may carry the same high-pass (not documented; flagged)",
                         "our_features": "causal (forward-only filters; trailing windows end at each step end)"},
    }


def extra_outputs(paths, results):
    """Digitised EEG electrode positions per session (for the coordinate network of per-recording rows): read from
    each session's electrodes.tsv in the pinned git catalogue (blob hash checked) and written to the private
    shards/ds003739/ELECTRODES.json. Coordinates as stored (the catalogue's coordsystem file names the CTF frame)."""
    cat, tree = _catalogue_tree(paths)
    out = {"source": "electrodes.tsv of each session in the ds003739 1.0.3 git catalogue", "frame": "as stored (CTF)",
           "recordings": {}}
    for r in results:
        for m in r["recordings"]:
            stem = "%s/%s/eeg/%s_%s_task-%s" % (r["unit"], m["session"], r["unit"], m["session"], m["task"])
            name = stem + "_electrodes.tsv"
            p = Path(cat) / name
            if not _git_blob_ok(p, tree[name][1]):
                raise ValueError("electrodes.tsv blob check failed " + name)
            rows = [l.split("\t") for l in p.read_text().splitlines()[1:] if l.strip()]
            out["recordings"][m["rec_id"]] = {"file_sha256": common.sha256_file(p),
                                             "positions": {x[0]: [None if v == "n/a" else float(v) for v in x[1:4]]
                                                           for x in rows}}
    f = Path(paths["shards"]) / DATASET / "ELECTRODES.json"
    common.atomic_write_json(f, out)
    return {"electrode_positions": {"file": f.name, "sha256": common.sha256_file(f), "recordings": len(out["recordings"])}}
