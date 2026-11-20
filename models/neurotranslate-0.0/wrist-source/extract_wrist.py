"""Rebuild the six original training participants' window table from Figshare v3."""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np

import decode_source as src
from features import OFFSETS, collect_rows

HERE = Path(__file__).resolve().parent
PEOPLE = ("sub-37", "sub-03", "sub-15", "sub-17", "sub-38", "sub-43")
KEY_HASH = "4037557ec9f0ff97fa9412e4531f5099d891b8eeeccff6d3c9446d82388dc975"


def read_archives(directory):
    records = json.loads((HERE / "archives.json").read_text())["archives"]
    if tuple(r["subject"] for r in records) != PEOPLE:
        raise ValueError("Unexpected training roster")
    for person, record in enumerate(records):
        pid = PEOPLE[person]
        path = directory / (pid + ".zip")
        if (record["file"] != path.name or path.stat().st_size != record["bytes"]
                or src.sha256_file(path) != record["sha256"]):
            raise ValueError(f"Publisher archive identity differs for {pid}")
        stem = pid + "_task-WristPointingTask"
        with zipfile.ZipFile(path) as archive:
            channel_rows = src.read_dictionary(archive, f"{pid}/eeg/{stem}_channels.tsv")
            labels = [(r["name"], r["type"], r["units"]) for r in channel_rows]
            expected = [(k, "EEG", "microV") for k in src.EEG] + [(k, "EMG", "microV") for k in src.EMG]
            if labels != expected:
                raise ValueError("Source electrode order or units differ")
            motion_rows = src.read_dictionary(archive, f"{pid}/motion/{stem}_tracksys-BiomechWrist_channels.tsv")
            if [(r["name"], r["tracked_point"], r["units"]) for r in motion_rows] != [
                ("X", "RightWrist", "rad"), ("Y", "RightWrist", "rad")
            ]:
                raise ValueError("Source motion dictionary differs")
            available = src.archive_run_ids(archive, pid) - {"01", "11"}
            if available != set(src.TASK_RUN_IDS) - ({"03"} if pid == "sub-17" else set()):
                raise ValueError("Unexpected task runs")
            for run in sorted(available):
                block = int(run) - 2
                signal, _ = src.decode_edf(archive.read(f"{pid}/eeg/{stem}_run-{run}_eeg.edf"))
                motion = archive.read(f"{pid}/motion/{stem}_tracksys-BiomechWrist_run-{run}_motion.tsv")
                _, angles, valid = src.coordinate_data(motion, signal)
                _, cues, returns = src.trial_ticks(signal)
                rows, _ = collect_rows(signal[:, :8], signal[:, 8:16], angles, valid, cues, returns, person, block)
                cue = cues[rows.trial]
                ticks = cue + OFFSETS[rows.slot]
                if not (np.array_equal(rows.target, angles[ticks]) and np.array_equal(rows.anchor, angles[ticks-128])):
                    raise ValueError("Independent target/anchor lookup failed")
                yield {**vars(rows), "cue": cue, "target_tick": ticks,
                       "parent": np.full(len(cue), f"{pid}/run-{run}", dtype="U32")}


def array_identity(table):
    return {
        key: {"dtype": a.dtype.str, "shape": list(a.shape),
              "sha256": hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}
        for key, a in sorted(table.items())
    }


def assemble(pieces):
    ordered = list(pieces)
    table = {k: np.concatenate([d[k] for d in ordered]) for k in ordered[0]}
    person, block, trial, slot = (table[k] for k in ("person", "block", "trial", "slot"))
    keys = np.column_stack((person, block, trial, slot)).astype("<i8")
    if (len(keys) != 11274 or hashlib.sha256(keys.tobytes()).hexdigest() != KEY_HASH
            or table["bins"].shape != (11274, 16, 14) or not np.isfinite(table["bins"]).all()):
        raise ValueError("Feature width or the original ordered set of complete trials changed")
    donor = np.empty(len(keys), dtype=np.int64)
    for p, b in np.unique(keys[:, :2], axis=0):
        for s in range(len(OFFSETS)):
            pos = np.flatnonzero((person == p) & (block == b) & (slot == s))
            ix = pos[np.argsort(trial[pos], kind="stable")]
            donor[ix] = np.roll(ix, -1)
    if (not np.array_equal(np.sort(donor), np.arange(len(keys))) or not (trial[donor] != trial).all()
            or not np.array_equal(keys[donor][:, (0, 1, 3)], keys[:, (0, 1, 3)])):
        raise ValueError("Invalid control donor pairing")
    table["donor"] = donor
    return table


def check_existing(path, table):
    with np.load(path, allow_pickle=False) as original:
        if set(original) != set(table) or array_identity(dict(original)) != array_identity(table):
            raise ValueError("Existing output differs; choose a new output path")


def write_table(path, table):
    """Keep complete files and verify an existing output on repeat runs."""
    if path.exists():
        check_existing(path, table)
        return
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".wrist-")
    try:
        with os.fdopen(fd, "wb") as tmp:
            np.savez(tmp, **{key: table[key] for key in sorted(table)})
            tmp.flush()
            os.fsync(tmp.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            check_existing(path, table)
    finally:
        os.unlink(name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archives", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    table = assemble(read_archives(args.archives))
    expected = json.loads((HERE / "array-hashes.json").read_text())
    if array_identity(table) != expected:
        raise ValueError("Rebuilt table differs from the verified six-person extraction")
    write_table(args.output, table)
    print(f"Verified {len(table['target']):,} windows from six participants at {args.output}.")


if __name__ == "__main__":
    main()
