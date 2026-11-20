"""Verify and align admitted PhysioNet angle members for this comparison."""
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from extract import TRAIN, TEST, path_for
from predict import PERIODS, phase_tokens


HERE = Path(__file__).resolve().parent
SOURCE_SHA256 = "695d0ff23daba2093e04467aeb3900de2a4735843baec54bf3ca4bab51e731c1"
PROTOCOL_SHA256 = "a96040d1cfd327d1170bb836137aa8abf622bf1bebdc18288f30a76880ecb890"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    with path.open("x") as out:
        json.dump(data, out, indent=2, allow_nan=False)
        out.write("\n")


def series_hash(x, dtype):
    return hashlib.sha256(np.asarray(x, dtype=dtype).tobytes(order="C")).hexdigest()


@dataclass
class Trial:
    person: int
    frames: np.ndarray
    knees: np.ndarray
    cuts: np.ndarray
    periods: np.ndarray
    tokens: np.ndarray
    stride: np.ndarray
    target: np.ndarray
    join: dict


def select_periods(knees, cuts):
    # A cumulative sum per lag reuses overlapping 60-frame past comparisons.
    # For cutoff i, the upper bound indexes the sample pair ending exactly at i.
    cost = np.empty((len(PERIODS), len(cuts)))
    for k, period in enumerate(PERIODS):
        delta = knees[period:] - knees[:-period]
        sq = np.nan_to_num(np.sum(delta ** 2, axis=1))
        summed = np.r_[0., np.cumsum(sq)]
        cost[k] = summed[cuts - period + 1] - summed[cuts - period - 59]
    return PERIODS[cost.argmin(axis=0)]


def load_trial(cache, person):
    if person not in TRAIN + TEST:
        raise ValueError("Participant outside declared splits")
    manifest = HERE / "source-members.json"
    if digest(manifest) != SOURCE_SHA256 or digest(HERE / "protocol.json") != PROTOCOL_SHA256:
        raise ValueError("Source manifest or study protocol differs from the frozen copy")
    meta = json.loads(manifest.read_text())
    member = next(row for row in meta["members"] if row["subject"] == person)
    path = cache / path_for(person)
    if digest(path) != member["sha256"] or member["path"] != path_for(person):
        raise ValueError(f"Source member mismatch for S{person}")
    with path.open(encoding="utf-8-sig", newline="") as src:
        names = next(csv.reader(src))
    wanted = [meta["frame_column"], *meta["columns"]]
    if any(names.count(s) != 1 for s in wanted):
        raise ValueError(f"Ambiguous source columns for S{person}")
    raw = np.genfromtxt(path, delimiter=",", skip_header=1, usecols=[names.index(s) for s in wanted],
                        dtype=np.float64, encoding="utf-8-sig", ndmin=2)
    frames, channels = raw[:, 0], raw[:, 1:]
    knees = channels[:, 2:4].copy()
    contiguous = np.diff(frames) == 1
    good = np.isfinite(raw).all(axis=1) & (frames == np.floor(frames))
    window = np.lib.stride_tricks.sliding_window_view
    cuts = np.arange(24, len(raw) - 15)[window(good, 40).all(axis=1) & window(contiguous, 39).all(axis=1)]
    if len(cuts) != member["eligible_windows"] or len(raw) != member["rows"]:
        raise ValueError(f"Original cutoff or row count differs for S{person}")
    clean_step = contiguous & np.isfinite(knees[1:]).all(axis=1) & np.isfinite(knees[:-1]).all(axis=1)
    cuts = cuts[np.r_[np.zeros(239, dtype=bool), window(clean_step, 239).all(axis=1)][cuts]]
    periods = select_periods(knees, cuts)
    tokens, stride = phase_tokens(knees, cuts, periods)
    join = dict(participant=person, split=member["split"], member=member["path"], member_sha256=member["sha256"],
                source_rows=len(raw), cutoffs=len(cuts), cutoff_frames_sha256_le_i8=series_hash(frames[cuts], "<i8"),
                knee_series_sha256_le_f8=series_hash(knees, "<f8"))
    return Trial(person, frames, knees, cuts, periods, tokens, stride, knees[cuts + 15], join)
