"""Build one cutoff-safe model window from the frozen NeuroSurge development replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

CLIP_SHA256 = "e50331490f2f2f33208e89c9a5f2679f08349c1030b9e5d2424e6bce955db59d"
DOI = "10.6084/m9.figshare.29666735.v3"
PARENT = f"{DOI}/sub-41/run-03"
PAIR = f"{PARENT}/block-1/trial-1"
CLOCK = PARENT + "/512-Hz-stored-row"
ALIGNMENT = PAIR + "/same-stored-row"
TASK = "neurosurge-right-wrist-pointing"
RATE = 512
HISTORY = 32
WORDS = ("right", "wrist", "visual", "pointing", "release")
CONTEXT = tuple("protocol_word_" + word for word in WORDS) + ("visual_cue_started",)
CHANNELS = {
    "neural": ("scalpC3_uV",),
    "myographic": ("forearmM3LminusM3R_uV",),
    "measured_motion": ("wristExtension_deg", "wristRadialDeviation_deg"),
}
UNAVAILABLE = ("intracranial activity", "spinal activity", "peripheral afferent activity",
               "peripheral motor nerve activity", "muscle force", "joint torque", "video", "speech")
SOURCE_IDS = {family: PAIR + "/" + "+".join(names) for family, names in CHANNELS.items()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def context_features(protocol, first_row, cue_row, cutoff, rate):
    """Protocol dictionary known offline; evidence for the visual event starts at its marker."""
    words = protocol.lower().split()
    require(bool(words) and set(words) <= set(WORDS), "Unsupported protocol vocabulary")
    occurred = cue_row is not None and cue_row <= cutoff
    values = [float(word in words) for word in WORDS] + [float(occurred)]
    availability = [first_row / rate] * len(WORDS) + [(cue_row if occurred else cutoff) / rate]
    return values, availability


def modality_record(sample, parent, pairing, source_id, values, times):
    observed = [[value is not None for value in row] for row in values]
    require(all(math.isfinite(v) for row in values for v in row if v is not None),
            "Observed source value must be finite")
    return {"source_id": source_id, "sample_ids": [sample], "raw_parent_ids": [parent],
            "pairing_id": pairing, "values": [[[0.0 if v is None else v for v in row] for row in values]],
            "observed": [observed], "available_at_s": [[[t] * len(row) for t, row in zip(times, values, strict=True)]]}


def load_replay(path):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CLIP_SHA256, "Replay SHA-256 differs")
    return json.loads(raw)


def replay_sample(path, cutoff_offset=256, target_offset=384):
    """Offsets are stored rows from the cue. Only a packet-verified encoder target is eligible."""
    clip = load_replay(path)
    cue, first, last = (clip[k] for k in ("cueSourceRow", "firstSourceRow", "lastSourceRow"))
    require(type(cutoff_offset) is int and type(target_offset) is int, "Integer source offsets required")
    cutoff, target_row = cue + cutoff_offset, cue + target_offset
    require(first <= cutoff - HISTORY + 1 and cutoff < target_row <= last,
            "Need 32 recorded history rows and a strictly later recorded target")
    require((clip["sourceSampleRateHz"], clip["encoderUpdateRateHz"], clip["task"]) ==
            (RATE, 100, "right wrist visual pointing"), "Unexpected recording or protocol")
    history_rows = range(cutoff - HISTORY + 1, cutoff + 1)
    times = [row / RATE for row in history_rows]
    sample_id = f"{PAIR}/cutoff-{cutoff}"
    context, available = context_features(clip["task"], first, cue, cutoff, RATE)
    series = clip["series"]
    modalities = {}
    for family, names in CHANNELS.items():
        values = [[series[name][row - first] for name in names] for row in history_rows]
        modalities[family] = modality_record(sample_id, PARENT, PAIR, SOURCE_IDS[family], values, times)
    obs = {"sample_ids": [sample_id], "raw_parent_ids": [PARENT], "partition": "DEV",
           "task_id": TASK, "clock_id": CLOCK, "alignment_id": ALIGNMENT, "pairing_id": PAIR,
           "times_s": [times], "valid_steps": [[True] * HISTORY], "context_values": [context],
           "context_available_at_s": [available], "modalities": modalities}

    # A distinct producer retained target ticks and encoder values. Match them to the requested
    # row and the replay before constructing the target. Never give this packet to the predictor.
    packet = clip["forecastInput"]
    candidates = [(tick, values) for tick, values in
                  zip(packet["source"]["targetTicks"], packet["measuredDegrees"], strict=True) if tick == target_row]
    require(len(candidates) == 1, "Expected exactly one stored encoder label at requested row")
    label_tick, label_angles = candidates[0]
    angles = [series[name][label_tick - first] for name in CHANNELS["measured_motion"]]
    require(angles == label_angles, "Target packet differs from the raw replay angles")
    event_time = label_tick / RATE
    target = modality_record(sample_id, PARENT, PAIR, SOURCE_IDS["measured_motion"], [angles], [event_time])
    return {
        "format": "wrist-language-motion-window-v1", "source_clip_sha256": CLIP_SHA256,
        "data_credit": {
            "title": "EEG-EMG-WristMotion Dataset, version 3",
            "creators": ["Jorge German Perez Blanco", "Javier Mauricio Anteliz Ortiz"],
            "url": "https://doi.org/" + DOI, "licence": "https://creativecommons.org/licenses/by/4.0/",
            "changes": "Excerpt, forearm electrode subtraction, row selection, task encoding and authored caption."},
        "origin": {"dataset": DOI, "subject": clip["subject"], "run": clip["run"],
                   "block": 1, "trial": clip["trial"], "first_history_row": history_rows.start,
                   "cutoff_row": cutoff, "cue_row": cue, "requested_target_row": target_row,
                   "actual_target_row": label_tick, "stored_hz": RATE, "encoder_hz": 100,
                   "availability": "offline stored-row replay; hardware and filter delays unknown"},
        "context_features": list(CONTEXT), "observations": obs,
        "query": {"times_s": [[target_row / RATE]], "valid_steps": [[True]]},
        "target": {"family": "measured_motion", "record": target, "event_times_s": [[event_time]],
                   "training_loss_weight": 0.0, "role": "exposed development replay"},
        "unobserved": {name: {"observed": False, "training_loss_weight": 0.0} for name in UNAVAILABLE},
        "events": [
            {"kind": "protocol_description", "text": clip["task"], "scope": "whole trial",
             "conditioning": "controlled vocabulary", "spoken": False},
            {"kind": "visual_target_onset", "source": clip["cueChannel"], "target_code": clip["targetCodeAtCue"],
             "source_row": cue, "available_to_model_by_cutoff": cue <= cutoff},
        ],
        "annotation": {
            "kind": "authored_retrospective_description", "text": "The right wrist bends toward the palm.",
            "evidence_rows": [cue, last], "extension_degrees_at_bounds":
                [series["wristExtension_deg"][row - first] for row in (cue, last)],
            "clock": "describes the interval; no word onset or recording of speech",
            "model_conditioning": False, "training_loss_weight": 0.0},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--cutoff-offset", type=int, default=256)
    parser.add_argument("--target-offset", type=int, default=384)
    args = parser.parse_args()
    print(json.dumps(replay_sample(args.replay, args.cutoff_offset, args.target_offset),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
