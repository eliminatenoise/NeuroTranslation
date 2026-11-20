"""Decode six named angles and construct one participant's chronological windows."""
import csv
import hashlib
import re
from dataclasses import dataclass

import numpy as np

from extract import path_for
from predict import CHANNELS, LAGS


def label(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


@dataclass
class Trial:
    x: np.ndarray
    y: np.ndarray
    anchors: np.ndarray
    degrees: np.ndarray
    frame: np.ndarray
    info: dict


def series_digest(array):
    return hashlib.sha256(np.ascontiguousarray(array, dtype="<f8").tobytes()).hexdigest()


def samples(degrees, frame):
    valid = np.isfinite(degrees).all(axis=1) & np.isfinite(frame)
    valid &= frame == np.floor(frame)
    cuts = np.arange(max(LAGS), len(degrees) - 15, dtype=np.int64)
    # For each forecast require all frames from t-24 through t+15, including skipped tokens.
    missing = np.r_[0, (~valid).cumsum()]
    discontinuity = np.r_[0, 0, (np.diff(frame) != 1).cumsum()]
    start, end = cuts - max(LAGS), cuts + 15
    ok = (missing[end + 1] == missing[start]) & (discontinuity[end + 1] == discontinuity[start + 1])
    cuts = cuts[ok]
    return degrees[cuts[:, None] - np.asarray(LAGS)], degrees[cuts + 15, 2:4], cuts


def load_trial(cache, person):
    source = cache / path_for(person)
    with source.open(encoding="utf-8-sig", newline="") as stream:
        original = next(csv.reader(stream))
    names = [label(x) for x in original]
    frame_col = names.index("frame")
    axis_cols = []
    for joint in CHANNELS:
        movement = " Dorsiflexion/Plantarflexion" if "ankle" in joint else " Flexion/Extension"
        allowed = {label(joint + movement)}
        selected = [i for i, name in enumerate(names) if name in allowed]
        if len(selected) != 1:
            raise ValueError(f"Expected one Z flexion/extension column for {joint}, got {selected}.")
        axis_cols.append(selected[0])
    # Read only these seven numeric fields. No participant or acquisition metadata are needed.
    selected = np.genfromtxt(source, delimiter=",", skip_header=1, usecols=[frame_col, *axis_cols],
                             dtype=np.float64, invalid_raise=True, encoding="utf-8-sig", ndmin=2)
    frame, deg = selected[:, 0], selected[:, 1:]
    x, future, cuts = samples(deg, frame)
    if not len(cuts):
        raise ValueError(f"Zero eligible windows for S{person}; inspect source integrity")
    info = dict(subject=person, file_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                angle_sha256=series_digest(deg), rows=len(deg), windows=len(cuts),
                missing_or_nonfinite_rows=int((~np.isfinite(selected).all(axis=1)).sum()),
                discontinuous_frame_steps=int((np.diff(frame) != 1).sum()),
                column_headers=[original[i] for i in axis_cols], frame_header=original[frame_col],
                range_degrees=np.stack([np.nanmin(deg, axis=0), np.nanmax(deg, axis=0)]).tolist(),
                standard_deviation_degrees=np.nanstd(deg, axis=0).tolist())
    return Trial(x, future, cuts, deg, frame, info)


def load_set(cache, people, known=()):
    trials, dropped = {}, {}
    seen = {digest: "a fit series" for digest in known}
    for p in people:
        trial = load_trial(cache, p)
        digest = trial.info["angle_sha256"]
        if digest in seen:
            dropped[p] = f"same six-column numeric series as {seen[digest]}"
            continue
        seen[digest] = f"S{p}"
        trials[p] = trial
    return trials, dropped
