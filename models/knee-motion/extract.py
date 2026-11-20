"""Extract selected joint-angle CSVs and summarize two technical fields from a verified archive."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile

ARCHIVE_SHA256 = "70ebdfee244c78c5726ec99be7864b99629c0b1eb02a66a558a625fd095b06b2"
URL = "https://physionet.org/files/multimodal-gait-dataset/1.0.0/Dataset/IMU_Data/IMU.tar.gz"
TRAIN = tuple(i for i in range(1, 41) if i != 24)
TEST = tuple(range(41, 53))


def path_for(person):
    return f"IMU_S{person}_0.5/Joint_Angles_ZXY.csv"


def technical_fields(stream):
    needed = {"Frame Rate", "Processing Quality"}
    selected = {}
    raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Technical header exceeds the source format")
    for row in csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")):
        if row and row[0] in needed:
            if len(row) != 2 or row[0] in selected:
                raise ValueError("Ambiguous technical metadata")
            selected[row[0]] = row[1].strip()
    if set(selected) != needed or selected["Processing Quality"] not in ("HD", "Live"):
        raise ValueError("Unknown technical format in this dataset version")
    return float(selected["Frame Rate"]), selected["Processing Quality"].upper()


def copy_angle(contents, target, size):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        with target.open("rb") as existing:
            if hashlib.file_digest(existing, "sha256").digest() != hashlib.file_digest(contents, "sha256").digest():
                raise ValueError(f"Different existing contents at {target}")
        return
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        tmpname = Path(tmp.name)
        try:
            shutil.copyfileobj(contents, tmp)
            if tmp.tell() != size:
                raise ValueError(f"Incomplete source member for {target}")
        except BaseException:
            tmpname.unlink(missing_ok=True)
            raise
    os.replace(tmpname, target)


def extract(archive, destination):
    angle = {path_for(p) for p in TRAIN + TEST}
    meta = {p.replace("Joint_Angles_ZXY", "General_Information") for p in angle}
    expected = angle | meta
    seen, counts = set(), Counter()
    with archive.open("rb") as raw:
        if hashlib.file_digest(raw, "sha256").hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Archive SHA-256 differs from the PhysioNet release index")
        raw.seek(0)
        with gzip.GzipFile(fileobj=raw) as uncompressed, tarfile.open(fileobj=uncompressed, mode="r|", bufsize=1024*1024) as handle:
            for member in handle:
                name = member.name
                if name not in expected:
                    continue
                if name in seen or not member.isfile() or not 0 < member.size < 32_000_000:
                    raise ValueError(f"Unexpected archive member {name}")
                with handle.extractfile(member) as contents:
                    if name in angle:
                        copy_angle(contents, destination / name, member.size)
                    else:
                        counts[technical_fields(contents)] += 1
                seen.add(name)
    if seen != expected:
        raise ValueError(f"Missing source members {sorted(expected - seen)}")
    return dict(files=sum(counts.values()), counts=[
        dict(frame_rate_hz=hz, processing_quality=quality, files=count)
        for (hz, quality), count in sorted(counts.items())])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, epilog=f"Obtain the official release archive from {URL}")
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.archive, args.destination), indent=2))
