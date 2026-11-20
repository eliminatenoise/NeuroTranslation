"""Rebuild the 26 shared-contact forecast inputs from two original Chowdhury MAT sessions."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import groupby
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from encode import COMPASS, OFFSETS, Ineligible, bump_anchors, sample_window, zero_columns


HERE = Path(__file__).resolve().parent
PHASES = ("bump_before_target_and_go", "go_after_bump_before_target", "go_without_bump")
EVENT = {"bump": "idx_bumpTime", "target": "idx_tgtOnTime", "go": "idx_goCueTime"}
STAGES = ("train", "validation", "test")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(name):
    return json.loads((HERE / name).read_bytes())


def write_json(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")


def selected_originals(td, stage, identity):
    ids = np.asarray(td.trialID, dtype=np.int64)
    starts, ends = td.idx_startTime, td.idx_endTime
    require(np.all(np.diff(ids) > 0) and np.all(starts[1:] > ends[:-1]), "Original ordering")
    if stage == "test":
        lo, hi = identity["held_original_range_inclusive"]
        require(ids.tolist() == list(range(1, hi + 1)), "Changed reserved original IDs")
        chosen = list(range(lo, hi + 1))
    else:
        block = read("first-day-split.json")["fit" if stage == "train" else "validation"]
        chosen = [r["trial"] for r in block]
        i = np.searchsorted(ids, chosen)
        require(ids[i].tolist() == chosen, "First-day memberships were not found")
        require([(int(a), int(b)) for a, b in zip(starts[i], ends[i], strict=True)] ==
                [(r["start"], r["end"]) for r in block], "First-day interval mismatch")
        require(all(td.result[j] == "R" for j in i), "Unexpected first-day trial result")
    streams = {name: np.asarray(getattr(td, field)).reshape(-1) for name, field in EVENT.items()}
    for stream in streams.values():
        require(np.all(np.diff(stream.astype(np.int64)) >= 0), "Sparse event timestamps out of order")
    originals = {}
    for t, i in zip(chosen, np.searchsorted(ids, chosen), strict=True):
        start, end = int(starts[i]), int(ends[i])
        ev = {name: v[np.searchsorted(v, start):np.searchsorted(v, end, side="right")].astype(int).tolist()
              for name, v in streams.items()}
        originals[t] = dict(trial=t, start=start, end=end, result=td.result[i], events=ev,
                            flag=int(td.ctrHoldBump[i]), bump_direction=float(td.bumpDir[i]),
                            target_direction=float(td.tgtDir[i]))
    return originals


def candidate_rows(stage, originals, lock):
    if stage == "test":
        rows = [(t, PHASES.index(name), k, off, int(axis)) for t, name, k, off, axis in lock["rows"]]
        require(dict(Counter(PHASES[p] for t,p,k,off,d in rows)) == lock["windows_before_signal_QC"],
                "Locked phase totals changed")
        for t, p, k, off, axis in rows:
            tr = originals[t]
            b, tgt, go = (tr["events"][name] for name in ("bump", "target", "go"))
            require(tr["result"] == "R" and off in OFFSETS and tr["start"] <= k-20 and k+10 <= tr["end"],
                    "Locked original failed basic event/time eligibility")
            if p == 0:
                require((off, k) in bump_anchors(tr) and axis == tr["bump_direction"], "Bump key mismatch")
            else:
                require(tgt and go == [k-off] and len(tgt) == 1 and tgt[0] <= go[0] and axis == tr["target_direction"],
                        "Go key mismatch")
                if p == 1:
                    require(tr["flag"] == 1 and len(b) == 1 and b[0] < tgt[0] and tr["bump_direction"] in COMPASS,
                            "Post-bump cue mismatch")
                else:
                    require(tr["flag"] == 0 and not b, "Unbumped cue mismatch")
        return rows, []
    rows, missing = [], []
    for t, tr in originals.items():
        try:
            allowed = dict(bump_anchors(tr))
            reason = "outside_bounds_or_pre_target_horizon"
        except Ineligible as e:
            allowed, reason = {}, str(e)
        for off in OFFSETS:
            if off in allowed:
                rows.append((t, 0, allowed[off], off, int(tr["bump_direction"])))
            else:
                missing.append([t, 0, off, reason])
    return rows, missing


def closest_donors(keys, cue_rows):
    """Match the five complete cue state/direction vectors. Update after each original."""
    prior = {}
    donors = np.full(len(keys), -1, dtype=np.int32)
    trials = [row[0] for row in keys]
    require(all(a <= b for a,b in zip(trials, trials[1:])), "Rows must be in original order")
    for trial, group in groupby(range(len(keys)), key=lambda i: trials[i]):
        pending = {}
        for i in group:
            _, phase, k, off, axis = keys[i]
            key = phase, off, axis, tuple(cue_rows[i].ravel())
            require(key not in pending, "Ambiguous phase/direction/offset/cues within an original")
            donors[i] = prior.get(key, -1)
            pending[key] = i
        prior.update(pending)
    return donors


def verify_donors(keys, cue_rows, donors):
    # Independent lookup by descending chronological candidate trials within each coarse stratum.
    seen = defaultdict(list)
    for i, (trial, phase, k, off, axis) in enumerate(keys):
        previous = seen[phase, axis, off]
        expected = next((j for j in reversed(previous) if keys[j][0]<trial and
                         np.array_equal(cue_rows[i], cue_rows[j])), -1)
        require(donors[i] == expected, "Earlier different-original full cue-history donor mismatch")
        previous.append(i)


def sample_for_reader(data, date):
    """Preselected first eligible and first matched original per phase. Show every eligible offset."""
    examples = []
    for p, name in enumerate(PHASES):
        mask = data["phase"] == p
        choices = {}
        for label, selected in (("first eligible", mask), ("first matched", mask & (data["donor"] >= 0))):
            indices = np.flatnonzero(selected)
            if len(indices):
                choices.setdefault(int(data["trial"][indices[0]]), []).append(label)
        for trial, labels in choices.items():
            windows = []
            for i in np.flatnonzero(mask & (data["trial"] == trial)):
                ex = {f:data[f][i].tolist() for f in ("k","offset","direction","position_history_cm",
                      "movement_tokens_cm","count_tokens_40ms","cues","cue_elapsed_s","prior_count_100ms",
                      "target_count_100ms")}
                j = int(data["donor"][i])
                ex["donor_trial"] = int(data["trial"][j]) if j >= 0 else None
                ex["donor_movement_tokens_cm"] = data["movement_tokens_cm"][j].tolist() if j >= 0 else None
                ex["row_index"] = int(i)
                windows.append(ex)
            examples.append(dict(phase=name, trial=trial, selection=labels, windows=windows))
    return dict(date=date, contact_id=data["contact_id"].tolist(), samples=examples)


def extract(stage, mat, dest, release=False):
    require(stage in STAGES, "Unknown stage")
    require(stage != "test" or release, "Explicit release of the next-day windows is required")
    date = "2017-09-13" if stage == "test" else "2017-09-12"
    id_ = read("identities.json")
    spec = id_["sources"][date]
    require(mat.name == spec["file"], "Expected the original MAT filename for this stage")
    for filename, expected in id_["portable_identity_sha256"].items():
        require(digest(HERE / filename) == expected, "Portable identity changed: " + filename)
    require(mat.stat().st_size == spec["bytes"] and digest(mat) == spec["sha256"], "MAT identity mismatch")
    lock = read("held-day-membership.json")
    td = loadmat(mat, variable_names=["trial_data"], struct_as_record=False, squeeze_me=True)["trial_data"]
    require(td.monkey == "C" and td.task == "COactpas" and td.bin_size == 0.01 and
            td.date_time.split()[0] == ("2017/9/13" if stage == "test" else "2017/9/12"), "Session identity mismatch")
    guide = td.S1_unit_guide
    guide_hash = hashlib.sha256(guide.astype("<u2").tobytes(order="C")).hexdigest()
    require(guide_hash == spec["guide_sha256"], "Guide mismatch")
    contacts = id_["contacts"]
    require(contacts == lock["contacts"] and len(contacts) == 26, "Contact order mismatch")
    cols = zero_columns(guide, contacts)
    day = "9_13" if stage == "test" else "9_12"
    require(cols.tolist() == lock["source_guide_columns_zero_based"][day], "Source guide column mismatch")
    require(td.pos.shape == (len(td.S1_spikes), 2) and td.S1_spikes.shape[1] == len(guide), "Signal shape mismatch")
    originals = selected_originals(td, stage, id_)
    candidates, metadata_excluded = candidate_rows(stage, originals, lock)
    require(len(set((t,p,k) for t,p,k,off,d in candidates)) == len(candidates), "Duplicate trial, phase, anchor")
    kept, qc = [], []
    out = defaultdict(list)
    for row in candidates:
        t, p, k, off, direction = row
        tr = originals[t]
        try:
            arr = sample_window(td.S1_spikes, td.pos, cols, tr, k)
        except Ineligible as e:
            qc.append([*row, str(e)])
            continue
        for name, value in arr.items():
            out[name].append(value)
        out["bump_direction_deg"].append(int(tr["bump_direction"]) if tr["bump_direction"] in COMPASS else -1)
        kept.append(row)
    arrays = {key: np.asarray(value) for key, value in out.items()}
    trial, phase, k, off, direction = np.asarray(kept, dtype=np.int32).T
    arrays.update(trial=trial, k=k, offset=off, original_ids=np.array(list(originals), dtype=np.int32),
                  contact_id=np.array(contacts, dtype=np.uint16), matlab_column=(cols+1).astype(np.int32))
    if stage == "train":
        require(set(arrays) == set(id_["training_fields"]), "Accepted training fields mismatch")
        for key, v in arrays.items():
            identity = dict(shape=list(v.shape), dtype=v.dtype.str, sha256_C_order=hashlib.sha256(v.tobytes(order="C")).hexdigest())
            require(identity == id_["training_fields"][key], "Training array differs: " + key)
    donors = closest_donors(kept, arrays["cues"])
    verify_donors(kept, arrays["cues"], donors)
    arrays.update(phase=phase.astype(np.int8), direction=direction, donor=donors)
    dest.mkdir(exist_ok=True, parents=True)
    np.savez_compressed(dest / (stage + ".npz"), **arrays)
    eligible_ids = {name:sorted({t for t,p,k,off,d in candidates if p == index})
                    for index,name in enumerate(PHASES)}
    coverage = {}
    for index, name in enumerate(PHASES):
        which = phase == index
        matched = which & (donors >= 0)
        coverage[name] = dict(eligible_windows=sum(row[1] == index for row in candidates),
                              retained_windows=int(which.sum()), retained_originals=len(set(trial[which].tolist())),
                              matched_windows=int(matched.sum()), matched_originals=len(set(trial[matched].tolist())),
                              unmatched_windows=int((which & (donors < 0)).sum()))
    audit = dict(stage=stage, date=date, source_mat_sha256=spec["sha256"], guide_sha256=guide_hash,
                 contact_id=contacts, source_matlab_columns=(cols+1).tolist(), dates_are_separate=True,
                 assigned_originals=list(originals), metadata_excluded=metadata_excluded,
                 phase_eligible_original_ids=eligible_ids, pre_qc_rows=candidates, numerical_exclusions=qc,
                 phases=coverage, full_cue_donor_check=True, windows=len(kept), numerical_exclusion_count=len(qc),
                 training_field_identity_verified=(stage == "train"))
    write_json(dest / (stage+"-qc.json"), audit)
    write_json(dest / (stage+"-samples.json"), sample_for_reader(arrays, date))
    print(json.dumps({"stage":stage,"assigned_originals":len(originals),"windows":len(kept),
                      "numerical_exclusions":len(qc),"phases":coverage}))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("stage", choices=STAGES)
    cli.add_argument("member", type=Path)
    cli.add_argument("output", type=Path)
    cli.add_argument("--release-test", action="store_true", help="Reproduce the released September 13 study")
    args = cli.parse_args()
    extract(args.stage, args.member, args.output, args.release_test)
