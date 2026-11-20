"""Measure past wrist history and subsequently observed displacement on the RGB grid."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HOLDOUT = set(json.loads((HERE / "protocol.json").read_text())["assessment_groups"])
OFFSETS = np.array([1.0, 0.5, 0.25, 0.0])
COHORT_SHA = "873e7081ff0ff309cd5b8ffc8f7d6bc900fa56c090f3e2ee90aa57a142493b6d"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_source(root, role):
    source_dir = root / "preceding-words-source"
    cohort_path = source_dir / "COHORT.json"
    if sha(cohort_path) != COHORT_SHA:
        raise ValueError("Changed source cohort")
    cohort = json.loads(cohort_path.read_text())
    records = cohort["recordings"]
    if len(records) != 29 or len({r["group"] for r in records}) != 17:
        raise ValueError("Unexpected prior development cohort")
    selected = {
        r["recording"]: r
        for r in records
        if (r["group"] in HOLDOUT) == (role == "assessment")
    }
    permitted = set(cohort["allowlist"])
    events = defaultdict(list)
    seen = set()
    event_path = source_dir / "events.jsonl"
    if (
        sha(event_path)
        != "68c36838a6b4648bb4c6e771b3ca1bf59e5bc235acc3121cdad5288d4d57796c"
    ):
        raise ValueError("Changed safe instructor event source")
    for line in event_path.read_text().splitlines():
        e = json.loads(line)
        name = e["recording"]
        if name not in selected:
            continue
        r = selected[name]
        identity = (name, e["id"])
        if (
            identity in seen
            or not set(e["tokens"]) <= permitted
            or e["tokens"] != sorted(set(e["tokens"]))
            or e["task"] != r["task"]
            or e["group"] != r["group"]
            or not (0 <= e["start"] < e["end"] and np.isfinite(e["end"]))
            or abs((e["end"] - e["start"]) - e["duration_s"]) > 1e-6
            or e["confidence_status"] not in ("unrated", "explicit-high")
        ):
            raise ValueError("Invalid source event")
        seen.add(identity)
        events[name].append(e)
    return selected, events


def last_observation(observed_time, request):
    idx = int(np.searchsorted(observed_time, request + 1e-12, side="right")) - 1
    if idx < 0 or request - observed_time[idx] > 0.100000000001:
        return None
    return idx


def measure_recording(record, events, hand):
    clock = hand["t"]
    all_xyz = hand["xyz"][:, 1]
    use = (
        hand["active"]
        & hand["valid"][:, 1]
        & hand["tracked"][:, 1]
        & np.isfinite(all_xyz).all(axis=1)
    )
    observed = clock[use]
    ticks = hand["ticks"][use]
    xyz = all_xyz[use].astype(np.float64) * 100.0
    if np.any(np.diff(clock) <= 0) or not np.all(np.isfinite(clock)):
        raise ValueError("Recording grid must increase strictly")
    counts, rows = Counter(), []
    used_cutoffs, used_ticks = set(), set()
    for event in sorted(events, key=lambda e: (e["end"], e["start"], e["id"])):
        counts["admitted_speech"] += 1
        counts["speech_" + event["confidence_status"]] += 1
        index = int(np.searchsorted(clock, event["end"] + 0.25 - 1e-12))
        if index >= len(clock):
            counts["no_cutoff_in_recording"] += 1
            continue
        if index in used_cutoffs:
            counts["duplicate_cutoff"] += 1
            continue
        used_cutoffs.add(index)
        cutoff = float(clock[index])
        requests = cutoff - OFFSETS
        idx = [last_observation(observed, t) for t in requests]
        if any(i is None for i in idx):
            counts["missing_past_observation"] += 1
            continue
        history_time = observed[idx]
        if np.any(np.diff(ticks[idx]) <= 0) or np.any(np.diff(history_time) <= 0):
            counts["nonadvancing_past_clock"] += 1
            continue
        if ticks[idx[-1]] in used_ticks:
            counts["duplicate_latest_native_tick"] += 1
            continue
        used_ticks.add(ticks[idx[-1]])
        counts["past_eligible"] += 1
        counts["past_" + event["confidence_status"]] += 1
        position = xyz[idx]
        velocity = np.diff(position, axis=0) / np.diff(history_time)[:, None]
        speed = np.linalg.norm(velocity, axis=1)
        prior_net = float(np.linalg.norm(position[-1] - position[0]))
        stale = requests - history_time
        motion = np.r_[np.c_[velocity, speed].ravel(), prior_net, stale]
        duration = float(event["end"] - event["start"])
        context = np.array(
            [
                np.log1p(cutoff),
                np.log1p(duration),
                len(event["tokens"]),
                event["confidence_status"] == "unrated",
            ]
        )
        horizon = cutoff + 1.0
        if horizon > clock[-1] + 1e-12:
            counts["future_right_censored"] += 1
            continue
        future = last_observation(observed, horizon)
        if future is None or observed[future] <= cutoff:
            counts["missing_future_observation"] += 1
            continue
        if ticks[future] <= ticks[idx[-1]]:
            counts["nonadvancing_future_clock"] += 1
            continue
        counts["scorable"] += 1
        counts["scorable_" + event["confidence_status"]] += 1
        lead = observed[future] - cutoff
        rows.append(
            {
                "record": record["recording"],
                "group": record["group"],
                "task": record["task"],
                "id": event["id"],
                "tokens": tuple(event["tokens"]),
                "motion": motion,
                "context": context,
                "cutoff": cutoff,
                "duration": duration,
                "y": float(np.linalg.norm(xyz[future] - position[-1])),
                "prior_net": prior_net,
                "cv": float(speed[-1] * (horizon - history_time[-1])),
                "lead": [
                    cutoff - event["end"],
                    lead,
                    observed[future] - history_time[-1],
                    (int(ticks[future]) - int(ticks[idx[-1]])) * 1e-7,
                ],
                "confidence": event["confidence_status"],
            }
        )
    return rows, counts


def load_role(root, role):
    selected, events = read_source(root, role)
    rows, counts = [], {}
    for name, record in selected.items():
        expected_path = Path("hand-text-source/train") / (name + ".npz")
        if name.split("-")[0] != record["group"] or record["hand_npz"] != str(
            expected_path
        ):
            raise ValueError("Unexpected group or source path")
        hand_path = root / expected_path
        if sha(hand_path) != record["hand_npz_sha256"]:
            raise ValueError("Changed hand source file")
        with np.load(hand_path, allow_pickle=False) as hand:
            part, count = measure_recording(record, events[name], hand)
        rows.extend(part)
        counts[name] = {
            "group": record["group"],
            "task": record["task"],
            "counts": dict(count),
        }
    return rows, counts


def coverage(rows, counts):
    total = Counter()
    for record in counts.values():
        total.update(record["counts"])
    leads = np.array([r["lead"] for r in rows]).reshape(-1, 4)
    fields = [
        "speech_end_to_cutoff",
        "cutoff_to_target",
        "last_observed_to_target",
        "native_wrist_elapsed",
    ]
    return {
        "flow": dict(total),
        "recordings_with_targets": len({r["record"] for r in rows}),
        "groups_with_targets": len({r["group"] for r in rows}),
        "tasks_with_targets": len({r["task"] for r in rows}),
        "lead_seconds": {
            f: dict(
                zip(
                    ["min", "median", "max"],
                    np.quantile(leads[:, i], [0, 0.5, 1]).tolist(),
                )
            )
            for i, f in enumerate(fields)
        }
        if rows
        else {},
        "by_recording": counts,
    }
