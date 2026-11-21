"""Build one released repetition split from raw object-mounted sensor estimates."""

import argparse
import csv
import hashlib
import json
import os
import resource
import time
from collections import Counter
from pathlib import Path

import numpy as np

from stage import CACHE, HERE, SPLITS, digest, json_file, member, name, roster
from windows import CUTOFFS, GALLERY_COLUMNS, TOL, donor_rows, measured_windows, read_record

DATA_FIELDS = ("time", "gyro", "accel", "y_gyro", "y_accel")
IDENTITY_FIELDS = ("participant", "hand", "target", "trial", "repetition", "cutoff")


def release(split, release_dir):
    frozen = json.loads((HERE / "freeze.json").read_text())
    for filename, sha in frozen["sha256"].items():
        if digest(HERE / filename) != sha:
            raise ValueError(f"Source definition changed: {filename}")
    if split == "train":
        return None
    path = release_dir / f"{split}-release.json"
    gate = json.loads(path.read_text())
    if not (gate.get("authorized") is True and gate.get("split") == split and
            gate.get("source_freeze_sha256") == digest(HERE / "freeze.json")):
        raise ValueError("Missing valid, source-bound split release")
    return digest(path)


def slot_key(row):
    return int(row["participant"]), row["hand"], int(row["session_record_zero_based"])


def gallery(rows):
    return {
        "schema_version": 1, "columns": GALLERY_COLUMNS, "rate_hz": 100,
        "acceleration": "Native device XYZ including gravity, m/s²",
        "gyro": "Native device XYZ angular velocity, rad/s",
        "quaternion": "Sensor to local earth reference, scalar first [w,x,y,z], unitless; firmware estimate",
        "selection": "Earliest training participant and native recording per hand and target with a usable forecast window, finite gap-free gallery channels and unit quaternion within 0.001.",
        "source": "https://doi.org/10.17605/OSF.IO/J3QC8",
        "attribution": "Tim Sziburis, Susanne Blex, Tobias Glasmachers and Ioannis Iossifidis (2025).",
        "modifications": "Selected channels and recordings. Time is in seconds from the first row. Coordinates and orientation retain the source axes and precision.",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "clips": [rows[key] for key in sorted(rows)],
    }


def build(split, release_dir):
    begin = time.monotonic()
    gate_sha = release(split, release_dir)
    member_hashes = json.loads((CACHE / "raw-members.json").read_text())
    records = sorted((r for r in roster() if SPLITS[r["fold"]] == split), key=slot_key)
    fields = {k: [] for k in DATA_FIELDS + IDENTITY_FIELDS}
    counts = {c: Counter() for c in CUTOFFS}
    coverage, clips = [], {}
    source_stats = Counter()
    max_interval_error = 0.
    for row in records:
        person, side, trial = slot_key(row)
        hand = {"L": "left", "R": "right"}[side]
        target, rep = int(row["target"]), int(row["repetition_zero_based"])
        reason = row["author_qc"]
        report = dict(row)
        for c in CUTOFFS:
            counts[c]["assigned"] += 1
        if reason != "eligible":
            for c in CUTOFFS:
                counts[c][f"author_excluded_{reason}"] += 1
                report[str(c)] = f"author_excluded_{reason}"
            coverage.append(report)
            continue
        raw = (CACHE / split / name(row)).read_bytes()
        if hashlib.sha256(raw).hexdigest() != member_hashes[member(row)]:
            raise ValueError("Cached measurement differs from pinned archive")
        data = read_record(raw)
        clock, valid, rejected = measured_windows(data)
        source_stats["decoded_recordings"] += 1
        source_stats["with_a_usable_window"] += bool(valid)
        source_stats["original_rows"] += len(data)
        intervals = np.diff(clock)
        finite = np.isfinite(intervals)
        source_stats["off_nominal_intervals"] += int(np.sum(finite & (np.abs(intervals-.01) > TOL)))
        source_stats["nonfinite_intervals"] += int((~finite).sum())
        if finite.any():
            max_interval_error = max(max_interval_error, float(np.max(np.abs(intervals[finite]-.01))))
        for c in CUTOFFS:
            counts[c]["passed_author_flags"] += 1
            if c not in valid:
                counts[c][rejected[c]] += 1
                report[str(c)] = rejected[c]
                continue
            ix = len(fields["time"])
            report[str(c)] = ix
            counts[c]["usable"] += 1
            for field, value in zip(DATA_FIELDS, valid[c], strict=True):
                fields[field].append(value)
            for field, value in zip(IDENTITY_FIELDS, (person, hand, target, trial, rep, c), strict=True):
                fields[field].append(value)
        if split == "train" and valid and (hand, target) not in clips:
            display = np.column_stack([clock, data[:, 1:4], data[:, 7:10], data[:, 13:17]])
            quat_norm = np.linalg.norm(data[:, 13:17], axis=1)
            if (np.isfinite(display).all() and np.all(np.abs(np.diff(clock)-.01) <= TOL)
                    and np.all(np.abs(quat_norm - 1) <= .001)):
                clips[hand, target] = {"hand": hand, "target": target, "trial": trial, "repetition": rep,
                                       "cutoffs_ms": list(valid), "rows": display.tolist(),
                                       "member": member(row).split("/", 1)[1], "member_sha256": member_hashes[member(row)]}
        coverage.append(report)

    donors = donor_rows(fields["participant"], fields["hand"], fields["target"], fields["trial"], fields["cutoff"])
    arrays = {key: np.asarray(items, dtype=np.float64 if key in DATA_FIELDS else ("U5" if key == "hand" else np.int32))
              for key, items in fields.items()}
    arrays["donor"] = donors
    for c, d in zip(fields["cutoff"], donors, strict=True):
        counts[c]["matched" if d >= 0 else "unmatched"] += 1
    path = HERE / f"{split}.npz"
    with path.with_suffix(".npz.partial").open("wb") as out:
        np.savez_compressed(out, **arrays)
    os.replace(path.with_suffix(".npz.partial"), path)
    coverage_path = HERE / f"coverage-{split}.csv"
    with coverage_path.with_suffix(".csv.partial").open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=coverage[0].keys())
        writer.writeheader()
        writer.writerows(coverage)
    os.replace(coverage_path.with_suffix(".csv.partial"), coverage_path)
    if split == "train":
        if len(clips) != 18:
            raise ValueError("Incomplete recorded gallery")
        json_file(HERE / "gallery.json", gallery(clips))
    summary = {
        "split": split, "npz_sha256": digest(path), "npz_bytes": path.stat().st_size,
        "coverage_sha256": digest(coverage_path), "release_sha256": gate_sha,
        "freeze_sha256": digest(HERE / "freeze.json"),
        "by_cutoff_ms": counts, "all_cutoffs": dict(sum(counts.values(), Counter())),
        "author_flags_originals": dict(Counter(r["author_qc"] for r in records)),
        "assigned_originals": len(records), "usable_participants": len(set(fields["participant"])),
        "raw_clock": {**source_stats, "native_rate_hz": 100,
                      "max_abs_interval_deviation_s": max_interval_error},
    }
    json_file(HERE / f"support-{split}.json", summary)
    execution = {"elapsed_s": time.monotonic()-begin, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 "npz_sha256": summary["npz_sha256"], "numpy": np.__version__,
                 "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,
                 "blas_requested": os.environ.get("OPENBLAS_NUM_THREADS"), "omp_requested": os.environ.get("OMP_NUM_THREADS")}
    json_file(CACHE / f"build-{split}.json", execution)
    return summary["all_cutoffs"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=list(SPLITS.values()))
    parser.add_argument("--release-dir", type=Path, default=HERE.parent / "imu-model")
    args = parser.parse_args()
    print(build(args.split, args.release_dir))
