"""Build the frozen optical measurement subset. Training and held exports are separate invocations."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime

import numpy as np
from acquire import ROOT, SELECTION, SELECTION_HASH
from windows import RATE, crossing, positions, select_window

SOURCE = ROOT / "_private" / "source"
HELD = {4, 8, 12, 16, 20, 24, 28}
HEADER = "Frame,X,Y,Z,X.1,Y.1,Z.1"
FIELD_NAMES = [
    "participant",
    "hand",
    "target",
    "repetition",
    "trial",
    "member",
    "anchor_frame",
    "time",
    "xyz",
    "y",
    "valid",
    "target_time",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")


def optical_exclusions():
    result = set()
    section = []
    for line in (SOURCE / "ExcludedTrials.txt").read_text().splitlines():
        if line.startswith("### ") and "HAND," in line:
            section = line.split()[1:]
        if line.startswith("(") and section[-1] == "OPTICAL":
            p, target, rep = map(
                int, re.match(r"\((\d+),\s*(\d+),\s*(\d+)\)", line).groups()
            )
            result.add((p, section[0][0], target, rep))
    return result


def read_session(subject, hand):
    base = SOURCE / "Output" / "measurement" / str(subject) / hand

    def load(suffix, convert):
        lines = (base / f"{subject}_{hand}_{suffix}.txt").read_text().splitlines()
        return [convert(x) for x in lines]

    def stamp(x):
        return datetime.strptime(x, "%Y-%m-%d-%H-%M-%S.%f")

    labels = load("targets", int)
    if Counter(labels) != {target: 10 for target in range(1, 10)}:
        raise ValueError("Unexpected target assignments")
    start = load("timestampsRecStart", stamp)
    stop = load("timestampsRecStop", stamp)
    delay = load("timeDelays", float)
    if not len(labels) == len(start) == len(stop) == len(delay) == 90:
        raise ValueError("Incomplete metadata")
    repeats = Counter()
    for trial, (target, a, b, d) in enumerate(zip(labels, start, stop, delay)):
        rep = repeats[target]
        repeats[target] += 1
        if rep < 2:
            path = base / "V" / f"{subject}_{hand}_V_rec{trial}.csv"
            yield (
                trial,
                target,
                rep,
                path,
                {
                    "record_start_session_s": (a - start[0]).total_seconds(),
                    "record_stop_session_s": (b - start[0]).total_seconds(),
                    "programmed_variable_delay_ms": d,
                },
            )


def read_measurement(path):
    with path.open() as stream:
        if stream.readline().strip() != HEADER:
            raise ValueError(f"Unrecognized CSV schema at {path.name}")
        data = np.genfromtxt(stream, delimiter=",", ndmin=2)
    if len(data) == 0:
        return None
    if data.shape[1] != 7 or not np.isfinite(data[:, 0]).all():
        raise ValueError(f"Nonstandard frame record at {path.name}")
    frame = data[:, 0].astype(int)
    if not np.equal(frame, data[:, 0]).all() or np.any(np.diff(frame) <= 0):
        raise ValueError(f"Invalid frame numbers at {path.name}")
    return frame, data[:, 1:].reshape(-1, 2, 3)


def example(row, frame, xyz, anchor, second, markers, events, sha):
    relative = xyz - xyz[anchor]
    return {
        "id": f"p{row['participant']:02d}-{row['hand'][0].upper()}-t{row['target']}",
        "participant": f"p{row['participant']:02d}",
        "hand": row["hand"][0].upper(),
        "target": row["target"],
        "trial": row["trial"],
        "repetition": row["repetition"],
        "member": row["member"],
        "source_sha256": sha,
        **events,
        "marker_numbers": (markers + 1).tolist(),
        "first_eligible_native_frame": int(frame[anchor]),
        "crossing_native_frame": None if second is None else int(frame[second]),
        "crossing_t_s": None
        if second is None
        else float((frame[second] - frame[anchor]) / RATE),
        "frames": [
            {
                "native_frame": int(f),
                "t_s": float((f - frame[anchor]) / RATE),
                "xyz_mm": np.round(q, 3).tolist() if np.isfinite(q).all() else None,
            }
            for f, q in zip(frame, relative)
        ],
    }


def build(split):
    if digest(SELECTION) != SELECTION_HASH:
        raise ValueError("Selection differs from the pre-inspection version")
    excluded = optical_exclusions()
    records = {"acquisition": [], "crossing": []}
    summaries = []
    gallery = []
    for p in range(1, 32):
        if (p in HELD) != (split == "test"):
            continue
        for hand in ["L", "R"]:
            for trial, target, rep, path, events in read_session(p, hand):
                key = {
                    "participant": p,
                    "hand": {"L": "left", "R": "right"}[hand],
                    "target": target,
                    "repetition": rep,
                    "trial": trial,
                    "member": path.relative_to(SOURCE).as_posix(),
                }
                audit = {**key, "acquisition": "unprocessed", "crossing": "unprocessed"}
                summaries.append(audit)
                if (p, hand, target, rep) in excluded:
                    audit.update(
                        acquisition="publisher optical exclusion",
                        crossing="publisher optical exclusion",
                    )
                    continue
                if not path.is_file():
                    audit.update(acquisition="file absent", crossing="file absent")
                    continue
                read = read_measurement(path)
                if read is None:
                    audit.update(acquisition="empty file", crossing="empty file")
                    continue
                frame, markers = read
                anchor, used, xyz = positions(markers)
                if anchor is None:
                    audit.update(
                        acquisition="no complete marker", crossing="no complete marker"
                    )
                    continue
                second = crossing(frame, xyz, anchor)
                sha = digest(path)
                audit.update(
                    sha256=sha,
                    native_frames=len(frame),
                    frame_number_gaps=int(np.sum(np.diff(frame) - 1)),
                    missing_centroid_rows=int(np.sum(~np.isfinite(xyz[:, 0]))),
                    markers=(used + 1).tolist(),
                    **events,
                )
                if p == 1 and rep == 0:
                    gallery.append(
                        example(key, frame, xyz, anchor, second, used, events, sha)
                    )
                for which, reference in [("acquisition", anchor), ("crossing", second)]:
                    if reference is None:
                        audit[which] = "no confirmed 15 mm crossing"
                        continue
                    window = select_window(frame, xyz, reference)
                    if window is None:
                        audit[which] = "incomplete 200 ms history"
                        continue
                    audit[which] = "included"
                    audit[which + "_valid"] = window["valid"].tolist()
                    row = {**key, "anchor_frame": int(frame[reference]), **window}
                    records[which].append(row)
    for which, rows in records.items():
        suffix = "" if which == "acquisition" else "-crossing"
        if not rows:
            raise ValueError("No supported histories")
        arrays = {key: np.asarray([r[key] for r in rows]) for key in FIELD_NAMES}
        np.savez_compressed(ROOT / f"{split}{suffix}.npz", **arrays)
    write_json(ROOT / ("coverage-" + split + ".json"), summaries)
    if split == "train":
        gallery.sort(key=lambda r: (r["hand"], r["target"]))
        write_json(
            ROOT / "gallery.json",
            {
                "format": "ruhr-optical-object-1",
                "rate_hz": RATE,
                "source": json.loads((ROOT / "provenance.json").read_text()),
                "frame": "Unrotated Vicon world XYZ. Per-trial displacement in mm from first eligible centroid, rounded to 0.001 mm for display. Positive screen-axis/participant-axis correspondence must be qualified separately.",
                "clock": "Native Vicon frame intervals from first eligible marker sample. Target and go event offsets to this anchor were not measured. Left and right hands performed separate trials.",
                "missing": "null denotes absent selected marker(s). Frame jumps indicate missing native samples. Source Nexus gap filling can be unmarked.",
                "trials": gallery,
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=["train", "test"])
    build(parser.parse_args().split)
