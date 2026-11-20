"""Extract event-anchored forecasts from the single pinned C_20170912 TrialData MAT.

The split manifest and original MAT are required. No network, model fit, or other
source file is used. Indices in all public arrays and records follow MATLAB
(one-based, inclusive); only the local tensor index operation subtracts one.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat


MAT_SHA = "a391516945a67aff89039f33c0829a1c5423d859ce79baaaca962985916996af"
SPLIT_SHA = "f3893a92e459887fc04701ccc29e8f28a482ed6675bce46551e4523386e1214f"
GUIDE_SHA = "f33ad237cd39b7b8a2c962d96ff5368b055ae3564436754230ed9f64950704b4"
BLOCKS = {"train": "fit", "validation": "validation", "test": "sealed_within_session_test"}
EVENTS = {"bump": "idx_bumpTime", "target": "idx_tgtOnTime", "go": "idx_goCueTime"}
OFFSETS = (0, 5, 10, 15)
MARKER_NAMES = tuple([f"Marker_{i}" for i in range(1, 9)] + ["Pronation_Pt1", "Shoulder_JC"])
CARDINAL = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}
MARKER_COLS = [6, 7, 8, 24, 25, 26]  # verified against full exact names below


class WindowExclusion(Exception):
    """A forecast ineligible under the prespecified per-window rules."""


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_source(mat, split_path):
    if file_sha(mat) != MAT_SHA or file_sha(split_path) != SPLIT_SHA:
        raise ValueError("The MAT or the original chronological split failed SHA-256 verification")
    split = json.loads(Path(split_path).read_text())
    td = loadmat(mat, variable_names=["trial_data"], struct_as_record=False, squeeze_me=True)["trial_data"]
    ids, starts, ends = [np.asarray(getattr(td, f)) for f in ("trialID", "idx_startTime", "idx_endTime")]
    results = str(td.result)
    if len(ids) != 638 or len(set(ids)) != len(ids) or len(results) != len(ids):
        raise ValueError("Invalid original trial identities or outcomes")
    if not (np.all(starts > 0) and np.all(ends >= starts) and np.all(starts[1:] > ends[:-1])):
        raise ValueError("Invalid original trial intervals")
    rewarded = [{"trial": int(i), "start": int(a), "end": int(b)}
                for i, a, b, r in zip(ids, starts, ends, results, strict=True) if r == "R"]
    expected = (rewarded[:324], rewarded[324:432], rewarded[432:])
    if tuple(split["blocks"][field] for field in BLOCKS.values()) != expected or len(rewarded) != 540:
        raise ValueError("Split does not reproduce rewarded original trial identities and boundaries")
    if float(td.bin_size) != 0.01 or td.pos.shape != (td.S1_spikes.shape[0], 2):
        raise ValueError("Incorrect stored row clock or planar handle dimensions")
    guide = td.S1_unit_guide
    if (guide.shape != (82, 2) or td.S1_spikes.shape[1] != 82 or
            hashlib.sha256(guide.astype("<u2").tobytes()).hexdigest() != GUIDE_SHA):
        raise ValueError("Invalid channel/sort identity or order")
    names = tuple(str(x) for x in td.marker_names)
    if names != tuple(f"{label}_{axis}" for label in MARKER_NAMES for axis in "xyz"):
        raise ValueError("Unexpected source marker names/coordinate order")
    if td.markers.shape != (td.pos.shape[0], len(names)):
        raise ValueError("Incorrect marker array dimensions")
    return td, split["blocks"]


def event_prefix(td, originals):
    """Read sparse timestamps only through the final selected rewarded trial.

    The earlier independent check on this immutable member established at most
    one of each event per original and exactly one of each for all rewards.
    Stop at the first event in the last original: no lookahead into test sparse
    timestamps when preparing development. All earlier selected multiplicities
    are still explicitly checked per original, without aligning by event rank.
    """
    last = originals[-1]
    selected = {}
    for key, field in EVENTS.items():
        prefix = []
        for raw in getattr(td, field):
            stamp = int(raw)
            if stamp < 1 or stamp != raw or (prefix and stamp < prefix[-1]) or stamp > last["end"]:
                raise ValueError(f"Invalid or missing final sparse {key} event in verified source")
            prefix.append(stamp)
            if stamp >= last["start"]:
                break
        if not prefix or prefix[-1] < last["start"]:
            raise ValueError(f"Final rewarded trial lacks its previously verified {key} event")
        selected[key] = np.array(prefix, dtype=np.int32)
    return selected


def events_within(event_streams, start, end):
    events = {}
    for key, stream in event_streams.items():
        left = np.searchsorted(stream, start)
        right = np.searchsorted(stream, end, side="right")
        events[key] = stream[left:right].tolist()
    return events


def known_cues(edges, event, degrees):
    cues = np.zeros((len(edges), 7))
    for j, typ in ((0, "bump"), (3, "target")):
        known = event[typ] < edges
        cues[known, j] = 1
        if known.any():
            if degrees[typ] not in CARDINAL:
                raise WindowExclusion(f"unknown_visible_{typ}_direction")
            cues[known, j + 1:j + 3] = CARDINAL[degrees[typ]]
    cues[:, 6] = event["go"] < edges
    return cues


def sample(td, original, event, degrees, epoch, k, sorted_cols):
    if k - 20 < original["start"] or k + 10 > original["end"]:
        raise WindowExclusion("cross_original_bounds")
    if epoch == 0 and k + 10 >= min(event["target"], event["go"]):
        raise WindowExclusion("perturbation_target_reaches_display_or_go")
    if epoch == 1 and event["target"] > k:
        raise WindowExclusion("reach_anchor_precedes_display")
    anchor_dir = "target" if epoch else "bump"
    if degrees[anchor_dir] not in CARDINAL:
        raise WindowExclusion(f"missing_condition_{anchor_dir}_direction")
    edge = np.arange(k - 20, k + 1, 4)
    cue = known_cues(edge[1:], event, degrees)
    # All MATLAB rows k-20..k are the retained encoder history; k+10 is the target endpoint.
    history = td.pos[k - 21:k].astype(np.float64)
    future = td.pos[k + 9].astype(np.float64)
    if not np.isfinite(history).all() or not np.isfinite(future).all():
        raise WindowExclusion("nonfinite_encoder")
    spike = td.S1_spikes[k - 21:k - 1, :][:, sorted_cols]
    if not np.isfinite(spike).all() or np.any(spike < 0) or not np.equal(spike, np.floor(spike)).all():
        raise WindowExclusion("invalid_sorted_count")
    neural = spike.reshape(5, 4, 30).sum(axis=1, dtype=np.int64)
    endpoints = history[::4]
    movement = np.column_stack((endpoints[1:], np.diff(endpoints, axis=0)))
    cv = np.stack([(history[-1] - history[20 - lag]) * (10 / lag) for lag in (4, 10, 20)])
    landmarks = td.markers[np.ix_(edge - 1, MARKER_COLS)].astype(np.float64)
    marker = np.column_stack((landmarks[1:], np.diff(landmarks, axis=0)))
    marker_valid = np.isfinite(marker)
    marker[~marker_valid] = np.nan
    visible = [degrees[name] if event[name] < k else np.nan for name in ("bump", "target")]
    return dict(neural=neural, movement=movement, cue=cue, y=future - history[-1],
                cv=cv, marker=marker, marker_valid=marker_valid, observed_direction=visible)


def safe_numbers(values):
    """Standard JSON null for any missing coordinate, retaining all rows/order."""
    array = np.asarray(values)
    return np.where(np.isfinite(array), array, None).tolist()


def make_demo(td, original, events, degrees, guide, sorted_cols, records):
    start, end = original["start"], original["end"]
    span = slice(start - 1, end)
    return dict(trial=original["trial"], start=start, end=end, dt_s=float(td.bin_size),
                events=events, event_s_from_start={q: [(t - start) * .01 for t in ts] for q, ts in events.items()},
                direction_deg={key: (float(x) if np.isfinite(x) else None) for key, x in degrees.items()},
                marker_names=MARKER_NAMES, marker_xyz_m=safe_numbers(td.markers[span].reshape(-1, 10, 3)),
                position_xy_cm=safe_numbers(td.pos[span]), sorted_counts=td.S1_spikes[span, :][:, sorted_cols].tolist(),
                unit_guide=guide.tolist(), examples=records, source_sha256=MAT_SHA, split_sha256=SPLIT_SHA)


def extract(td, originals, *, include_demo=False):
    events = event_prefix(td, originals)
    id_to_i = {int(orig): i for i, orig in enumerate(td.trialID)}
    sorted_cols = td.S1_unit_guide[:, 1] > 0
    guide = td.S1_unit_guide[sorted_cols]
    if len(guide) != 30 or sum(~sorted_cols) != 52:
        raise ValueError("Invalid sorted/unsorted counts")
    samples = collections.defaultdict(list)
    donor_map, trial_records, demo = {}, [], None
    for original in originals:
        tid, start, end = (original[x] for x in ("trial", "start", "end"))
        i = id_to_i[tid]
        trial_events = events_within(events, start, end)
        counts = {key: len(indices) for key, indices in trial_events.items()}
        event_ok = all(count == 1 for count in counts.values())
        event = {key: v[0] for key, v in trial_events.items()} if event_ok else {}
        degrees = {"bump": float(td.bumpDir[i]), "target": float(td.tgtDir[i])}
        attempts = []
        pending = {}
        for epoch, anchor in enumerate(("bump", "go")):
            for offset in OFFSETS:
                record = dict(epoch=epoch, offset=offset, k=None, row=None, reason=None)
                attempts.append(record)
                if not event_ok:
                    record["reason"] = "missing_or_ambiguous_event"
                    continue
                k = event[anchor] + offset
                record["k"] = k
                if event["bump"] >= min(event["target"], event["go"]):
                    record["reason"] = "invalid_pair_order"
                    continue
                try:
                    values = sample(td, original, event, degrees, epoch, k, sorted_cols)
                except WindowExclusion as exc:
                    record["reason"] = str(exc)
                    continue
                # The matching key uses only the final token's observed state.
                # Most recent matching earlier original wins; pending rows become eligible
                # only after all samples for this original have been collected.
                key = (epoch, offset, *values["cue"][-1].astype(int))
                row = len(samples["trial"])
                rec = dict(trial=tid, epoch=epoch, k=k, offset=offset, donor=donor_map.get(key, -1), **values)
                for field, value in rec.items():
                    samples[field].append(value)
                pending[key] = row
                record["row"] = row
        donor_map.update(pending)
        trial_records.append(dict(**original, events=trial_events, event_multiplicity=counts,
                                  ctrHoldBump=int(td.ctrHoldBump[i]), attempts=attempts))
        if include_demo and original == originals[0]:
            demo = make_demo(td, original, trial_events, degrees, guide, sorted_cols, attempts)
    if not samples["trial"]:
        raise ValueError("The block has no eligible original-window pair")
    arr = {key: np.asarray(value) for key, value in samples.items()}
    arr.update(unit_guide=guide, original_trial=np.asarray([r["trial"] for r in originals], dtype=np.int32))
    return arr, trial_records, demo


def summary(arr, records):
    exclusions = collections.Counter(a["reason"] for r in records for a in r["attempts"] if a["reason"])
    return dict(original_trials=len(records), retained_original_trials=len(np.unique(arr["trial"])),
                attempted=len(records) * 8, retained=len(arr["trial"]),
                retained_per_epoch=np.bincount(arr["epoch"], minlength=2).tolist(),
                exclusions=dict(exclusions), donor_matched=int((arr["donor"] >= 0).sum()),
                complete_marker_rows=int(arr["marker_valid"].all(axis=(1, 2)).sum()),
                rewarded_zero_bump_flag=[r["trial"] for r in records if not r["ctrHoldBump"]])


def write_json(path, obj):
    data = json.dumps(obj, allow_nan=False, separators=(",", ":")) + "\n"
    Path(path).write_text(data)


def build(mat, split_path, out, *, stage="train", release_test=False):
    if stage not in BLOCKS or (stage == "test" and not release_test):
        raise ValueError("Test extraction requires a separate explicit release")
    td, blocks = open_source(mat, split_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    reports = {}
    if stage == "train":
        assigned = {row["trial"]: name for name, field in BLOCKS.items() for row in blocks[field]}
        membership = [dict(trial=int(i), start=int(lo), end=int(hi), outcome=r,
                           block=assigned.get(int(i)), exclusion=None if r == "R" else "nonrewarded_original")
                      for i, lo, hi, r in zip(td.trialID, td.idx_startTime, td.idx_endTime, str(td.result), strict=True)]
        write_json(out / "membership.json", membership)
    block = stage
    arr, originals, demo = extract(td, blocks[BLOCKS[block]], include_demo=(stage == "test"))
    reports[block] = summary(arr, originals)
    np.savez(out / f"{block}.npz", **arr)
    write_json(out / f"{block}-audit.json", {"summary": reports[block], "originals": originals})
    if demo is not None:
        write_json(out / "demo.json", demo)
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mat", type=Path)
    parser.add_argument("split", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--stage", default="train", choices=tuple(BLOCKS))
    parser.add_argument("--release-test", action="store_true", help="Use only after explicit study-owner release")
    args = parser.parse_args()
    print(json.dumps(build(args.mat, args.split, args.out, stage=args.stage, release_test=args.release_test), indent=2))
