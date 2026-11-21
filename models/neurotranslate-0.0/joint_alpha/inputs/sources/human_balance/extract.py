"""Extract synchronized muscle voltages and the sacrum path from the pinned recordings."""

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from acquire import COMMIT, STAGES, TASKS, TREE, digest, selection

MUSCLE_NAMES = ("tibialis_anterior", "soleus", "medial_gastrocnemius", "peroneus_longus")
LEGS = [f"{side}_leg_emg_{name}" for side in "LR" for name in MUSCLE_NAMES]
AXES = ("mediolateral", "superiorinferior", "anteriorposterior")
SACRUM = [f"Mocap_sacrum_{axis}" for axis in AXES]
DIRECTIONS = {"rotate_cw": 1, "rotate_ccw": -1}
NUMERIC_DTYPES = dict(event="<i4", posture="i1", direction="i1", block="i1", cutoff="<i8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_set(path):
    fields = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "EEG" in fields:
        record = fields["EEG"]
        return {name: getattr(record, name) for name in record._fieldnames}
    return fields


def constant_mask(values, minimum=32):
    """Mark complete runs including their first and last samples, before windowing."""
    same = (values[:-1] == values[1:]).all(axis=1)
    edges = np.flatnonzero(np.diff(np.r_[False, same, False].astype(np.int8)))
    starts, stops = edges[::2], edges[1::2] + 1
    long = stops - starts >= minimum
    changes = np.zeros(len(values) + 1, dtype=np.int32)
    changes[starts[long]] += 1
    changes[stops[long]] -= 1
    return np.cumsum(changes[:-1]) > 0


def identify_channels(table, eeg):
    names = [row["name"] for row in table]
    require(len(names) == len(set(names)) == eeg["nbchan"], "ambiguous channel identities")
    require([(c.labels, c.type, c.units) for c in np.atleast_1d(eeg["chanlocs"])] ==
            [(r["name"], r["type"], r["units"]) for r in table], "BIDS / EEGLAB channel mismatch")
    indices = np.atleast_1d(eeg["etc"].good_chans).ravel()
    require(np.isfinite(indices).all() and np.equal(indices, np.floor(indices)).all(),
            "nonintegral author good-channel mask")
    good = set(indices.astype(int) - 1)
    require(len(good) == len(indices) and good <= set(range(len(names))), "invalid channel mask")
    for label in LEGS + SACRUM:
        if label in names:
            row = table[names.index(label)]
            require((row["type"], row["units"]) ==
                    (("EMG", "microV") if label in LEGS else ("MISC", "mm")), f"units {label}")
    return names, good


def clock_check(row, source, raw_events, posture, tick, rate):
    code = "M_on_" + ("CW" if row["value"] == "rotate_cw" else "CCW") + ("_WVZ" if posture else "_SVZ")
    set_tick, onset_tick = float(source.latency) - 1, float(row["onset"]) * rate
    original_index = int(source.urevent) - 1
    identity = (source.type == code and 0 <= original_index < len(raw_events) and
                raw_events[original_index].type == code and row["trial_type"] == "stimulus" and
                float(row["duration"]) == 0.5)
    errors = [abs(tick - set_tick), abs(tick - onset_tick)]
    agreed = (all(math.isfinite(x) for x in errors) and max(errors) <= 0.01 and
              math.ceil(tick) == math.ceil(set_tick) == math.ceil(onset_tick))
    return identity and agreed, errors


def session_arrays(person, task, files):
    posture = TASKS.index(task)
    table, events = tsv(files["channels.tsv"]), tsv(files["events.tsv"])
    event_meta = json.loads(files["events.json"].read_bytes())
    require(event_meta["onset"]["Units"] == "second" and
            DIRECTIONS.keys() <= event_meta["value"]["Levels"].keys(), "invalid event sidecar")
    side = json.loads(files["eeg.json"].read_bytes())
    eeg = read_set(files["eeg.set"])
    rate, n, ch = eeg["srate"], int(eeg["pnts"]), int(eeg["nbchan"])
    require(rate == side["SamplingFrequency"] == 256 and eeg["trials"] == 1, "continuous 256 Hz")
    require(math.isclose(side["RecordingDuration"], n/rate, rel_tol=0, abs_tol=1e-8),
            "inconsistent duration")
    require(np.shape(eeg["times"]) == (n,) and np.allclose(eeg["times"], np.arange(n)*1000/rate,
            atol=1e-8, rtol=0), "invalid stored sample clock")
    fdt = files["eeg.fdt"]
    require(eeg["data"] == fdt.name and fdt.stat().st_size == 4*n*ch, "FDT pointer or size")
    names, good = identify_channels(table, eeg)
    data = np.memmap(fdt, mode="r", dtype="<f4", shape=(n, ch))
    legs = [names.index(label) for label in LEGS if label in names]
    xyz = [names.index(label) for label in SACRUM if label in names]
    signals = [i for i in sorted(good) if table[i]["type"] in {"EEG", "EMG", "EOG"}]
    missing = [label for label in LEGS + SACRUM if label not in names]
    rejected = [label for label in LEGS + SACRUM if label in names and names.index(label) not in good]
    legs_ok = len(legs) == 8 and set(legs) <= good
    sacrum_ok = len(xyz) == 3 and set(xyz) <= good
    voltage = np.asarray(data[:, legs])
    position = np.asarray(data[:, xyz], dtype=np.float64)
    legs_flat = np.zeros(n, dtype=bool)
    for column in range(len(legs)):
        legs_flat |= constant_mask(voltage[:, column:column+1])
    if len(xyz) == 3:
        zero = (position == 0).all(axis=1)
        flat = constant_mask(position) & ~zero
        step = np.linalg.norm(np.diff(position, axis=0), axis=1)
    original = [row for row in events if row["value"] in DIRECTIONS]
    source_events = [event for event in np.atleast_1d(eeg["event"])
                     if str(event.type).startswith(("M_on_CW_", "M_on_CCW_"))]
    require(len(source_events) == len(original), "different counts of archived visual rotations")
    raw_events = np.atleast_1d(eeg["urevent"])
    ticks = [float(row["sample"]) for row in original]
    require(all(math.isfinite(x) for x in ticks) and np.all(np.diff(ticks) > 0),
            "unordered rotation clock")
    exclusions, flag_counts, primary = {}, Counter(), Counter()
    directions, accepted_errors = Counter(), []
    out = defaultdict(list)
    for ordinal, (row, source, tick) in enumerate(zip(original, source_events, ticks, strict=True), 1):
        valid_clock, errors = clock_check(row, source, raw_events, posture, tick, rate)
        c = math.ceil(tick) + 32
        f = c + 32
        lo, end = c-167, f+9
        signal_span = slice(c-159, f+1)
        history = slice(c-159, c+1)
        future = slice(c+1, f+1)
        flags = []
        if not valid_clock:
            flags.append("event_clock_or_identity")
        if not legs_ok:
            flags.append("leg_channel_unavailable")
        if not sacrum_ok:
            flags.append("sacrum_channel_unavailable")
        if lo < 0 or end > n:
            flags.append("window_bounds")
        else:
            if not np.isfinite(data[history, signals]).all():
                flags.append("nonfinite_author_good_electrical_history")
            if not np.isfinite(voltage[signal_span]).all():
                flags.append("nonfinite_leg_history_or_target")
            if len(legs) == 8 and np.any(np.all(voltage[signal_span] == 0, axis=1)):
                flags.append("joint_eight_leg_zero")
            if np.any(legs_flat[signal_span]):
                flags.append("constant_leg_run_32")
            if not np.isfinite(position[lo:end]).all():
                flags.append("nonfinite_sacrum")
            if len(xyz) == 3:
                if np.any(zero[lo:end]):
                    flags.append("sacrum_zero_triplet")
                if np.any(step[lo:end-1] > 20):
                    flags.append("sacrum_step_above_20mm")
                if np.any(flat[lo:end]):
                    flags.append("sacrum_nonzero_flat_run_32")
        if flags:
            exclusions[ordinal] = flags
            flag_counts.update(flags)
            primary.update(flags[:1])
            continue
        direction = DIRECTIONS[row["value"]]
        directions[str(direction)] += 1
        accepted_errors.append(errors)
        volts_future = voltage[future].astype(np.float64)
        values = dict(person=person, posture=posture, event=ordinal, direction=direction,
                      block=min(2, 3*(ordinal-1)//len(original)), cutoff=c,
                      sacrum_mm=position[history]-position[c], leg_uv=voltage[history],
                      future_rms_uv=np.sqrt(np.mean(volts_future**2, axis=0)),
                      future_path_mm=position[future]-position[c])
        for key, value in values.items():
            out[key].append(value)
    qc = dict(original_rotations=len(original), original_by_value=dict(Counter(r["value"] for r in original)),
              other_events=dict(Counter(r["value"] for r in events if r["value"] not in DIRECTIONS)),
              retained=sum(directions.values()), retained_by_direction=dict(directions),
              qualified_both_directions=set(directions) == {"1", "-1"}, samples=n, channels=ch,
              author_good_electrical_channels=len(signals), missing=missing, author_bad=rejected,
              excluded_original_ordinals=exclusions, independent_flag_counts=dict(flag_counts),
              primary_exclusion_counts=dict(primary),
              accepted_max_SET_then_onset_error_samples=np.max(accepted_errors, axis=0).tolist()
                  if accepted_errors else None)
    return {k: np.asarray(v, dtype=NUMERIC_DTYPES.get(k)) for k,v in out.items()}, qc


def add_totals(sessions):
    flags, primary, directions = Counter(), Counter(), Counter()
    for q in sessions:
        flags.update(q["independent_flag_counts"])
        primary.update(q["primary_exclusion_counts"])
        directions.update(q["retained_by_direction"])
    return dict(sessions=len(sessions), original_rotations=sum(q["original_rotations"] for q in sessions),
                retained=sum(directions.values()), retained_by_direction=dict(directions),
                qualifying_people=sum(q["qualified_both_directions"] for q in sessions),
                primary_exclusions=dict(primary), independent_flag_counts=dict(flags))


def extract(work, stage, jobs):
    inventory_path = work / f"{stage}-files.json"
    receipt = json.loads(inventory_path.read_bytes())
    records, omissions, selected = selection(work / "catalogue", stage)
    require((receipt["dataset"], receipt["version"], receipt["commit"], receipt["tree"],
             receipt["stage"], receipt["selected"]) ==
            ("ds003739", "1.0.3", COMMIT, TREE, stage, selected), "source inventory mismatch")
    require(receipt["catalogue_omissions"] == omissions and
            set(receipt["files"]) == {r[0] for r in records}, "unexpected source paths")
    files = defaultdict(dict)
    for path, _, blob in records:
        src = work / "raw" / path
        info = receipt["files"][path]
        require(info["git_blob"] == blob and info["bytes"] == src.stat().st_size and
                info["sha256"] == digest(src), f"source bytes differ at {path}")
        if "/" in path:
            task = path.rsplit("_task-", 1)[1].split("_")[0]
            files[(path.split("/")[0], task)][path.rsplit("_",1)[1]] = src
    desc = json.loads((work / "raw" / "dataset_description.json").read_bytes())
    require(desc["License"] == "CC0" and desc["DatasetDOI"].endswith("ds003739.v1.0.3"), "source rights")
    keys = [(p,t) for p in selected for t in TASKS if (p,t) in files]
    per_person = {p: {} for p in selected}
    out = defaultdict(list)

    def decode(key):
        return session_arrays(*key, files[key])

    with ThreadPoolExecutor(jobs) as pool:
        for (person, task), (arrays, qc) in zip(keys, pool.map(decode, keys), strict=True):
            per_person[person][task] = qc
            for name, array in arrays.items():
                out[name].append(array)
    combined = {k: np.concatenate(parts) for k,parts in out.items()}
    require("person" in combined, "no eligible rows")
    qualified = {(p, TASKS.index(t)) for p, item in per_person.items() for t,q in item.items()
                 if q["qualified_both_directions"]}
    paired = [p for p in selected if (p,0) in qualified and (p,1) in qualified]
    combined["paired"] = np.isin(combined["person"], paired)
    combined["posture_qualified"] = np.array([(p,t) in qualified
        for p,t in zip(combined["person"], combined["posture"], strict=True)], dtype=bool)
    output = work / f"{stage}.npz"
    temp = output.with_suffix(".tmp.npz")
    np.savez_compressed(temp, **combined)
    temp.replace(output)
    posture_totals = {t:add_totals([item[t] for item in per_person.values() if t in item]) for t in TASKS}
    represented = np.unique(combined["person"])
    totals = dict(catalogue_selected=len(selected), catalogue_omissions=len(omissions),
                  represented_people=len(represented), original_rotations=sum(q["original_rotations"] for q in posture_totals.values()),
                  retained=len(combined["person"]), paired_people=len(paired), paired_rows=int(combined["paired"].sum()),
                  one_qualified_posture_people=len(qualified)-2*len(paired),
                  no_qualified_postures_people=len(selected)-len(qualified)+len(paired),
                  by_posture=posture_totals)
    doc = dict(stage=stage, npz_sha256=digest(output), files_receipt_sha256=digest(inventory_path),
               extraction_code_sha256=digest(Path(__file__)), totals=totals,
               arrays={k:dict(shape=list(v.shape), dtype=str(v.dtype)) for k,v in combined.items()},
               per_person=per_person, catalogue_omissions=omissions)
    qc_file = work / f"{stage}-qc.json"
    qc_file.write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("work", type=Path)
    parser.add_argument("--jobs", type=int, choices=(1,2), default=1)
    args = parser.parse_args()
    print(json.dumps(extract(args.work, args.stage, args.jobs)))
