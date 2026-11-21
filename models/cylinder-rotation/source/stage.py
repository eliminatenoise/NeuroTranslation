"""Copy only pinned licensed measurement members. No CSV values are decoded here."""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE_NAME = "Ruhr_HandMotion_CenterOutTask"
ARCHIVE_BYTES = 1928361942
ARCHIVE_SHA = "ebcde74b260f4a1e7b57ce0bb626bb6ee0703e6ba75c258267211933da3d8c79"
ROSTER_SHA = "636d035a298cf4a3517d039e08b1111e210b170ad4acfabb9ae3328b15130828"
CACHE = HERE / "_private"
SPLITS = {"fit": "train", "validation": "validation", "test": "test"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_file(path, value):
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def roster():
    path = HERE / "prospective-repetitions.csv"
    if digest(path) != ROSTER_SHA:
        raise ValueError("Prospective source roster differs from the frozen digest")
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def member(row):
    person, hand, rec = row["participant"], row["hand"], row["session_record_zero_based"]
    return f"{ARCHIVE_NAME}/Output/measurement/{person}/{hand}/X/{person}_{hand}_X_rec{rec}.csv"


def name(row):
    return member(row).rsplit("/", 1)[-1]


def stage(archive):
    started = time.monotonic()
    rows = [row for row in roster() if row["author_qc"] == "eligible"]
    wanted = {member(row): (SPLITS[row["fold"]], name(row)) for row in rows}
    if len(wanted) != len(rows) or len(rows) != 3241:
        raise ValueError("Unexpected source inventory")
    if archive.stat().st_size != ARCHIVE_BYTES or digest(archive) != ARCHIVE_SHA:
        raise ValueError("Use the exact OSF v1 archive (size and SHA-256 mismatch)")
    CACHE.mkdir(mode=0o700, exist_ok=True)
    receipt = CACHE / "raw-members.json"
    if receipt.exists():
        hashes = json.loads(receipt.read_text())
        if set(hashes) == wanted.keys() and all(
            digest(CACHE / split / filename) == hashes[key]
            for key, (split, filename) in wanted.items()
        ):
            return
        raise ValueError("Inconsistent cache proof; inspect the local cache")
    for split in SPLITS.values():
        (CACHE / split).mkdir(mode=0o700, exist_ok=True)
    hashes = {}
    with subprocess.Popen(["gzip", "-dc", str(archive)], stdout=subprocess.PIPE) as decoder:
        try:
            with tarfile.open(fileobj=decoder.stdout, mode="r|", bufsize=1 << 20) as tar:
                for entry in tar:
                    if entry.name not in wanted:
                        continue
                    if entry.name in hashes or not entry.isfile() or not 0 < entry.size < 1 << 20:
                        raise ValueError("Unexpected or duplicate selected member")
                    split, filename = wanted[entry.name]
                    raw = tar.extractfile(entry).read()
                    if len(raw) != entry.size:
                        raise ValueError("Incomplete tar member")
                    path = CACHE / split / filename
                    tmp = path.with_suffix(".partial")
                    tmp.write_bytes(raw)
                    os.replace(tmp, path)
                    hashes[entry.name] = hashlib.sha256(raw).hexdigest()
            while decoder.stdout.read(1 << 20):
                pass
        finally:
            decoder.stdout.close()
        if decoder.wait() != 0:
            raise ValueError("Decompressor failed")
    if hashes.keys() != wanted.keys():
        raise ValueError("Missing selected original recordings")
    json_file(receipt, hashes)
    json_file(CACHE / "stage-execution.json", {
        "members": len(hashes), "archive_sha256": ARCHIVE_SHA, "archive_bytes": ARCHIVE_BYTES,
        "seconds_including_input_verification": time.monotonic() - started,
        "compressed_archive_passes": "One plain-byte SHA verification and one gzip decode. No CSV decoded.",
        "primary_reader_processes": 1, "decompressor_processes": 1,
        "decoder": subprocess.check_output(["gzip", "--version"], text=True).splitlines()[0],
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    stage(parser.parse_args().archive)
