"""Verify the original archive and reconstruct the version-8 three-repeat roster."""
from collections import defaultdict
import hashlib
import json
import re


ARCHIVE_BYTES = 381392112
ARCHIVE_MD5 = "3b51aa30f2e138c3e2782fd6d3b7356f"
ARCHIVE_SHA256 = "e11f0f85424e7630d32dbeb8b37bf78d470dcb34c0f461417671ce7d146eaec5"
SUPPLEMENT_SHA256 = "37281bfdef06280d63019cb3008ea081f360f40d7a0cceb83293cc9aeae027d8"
SPLIT_SHA256 = "e0ccb1ae4a37c12d47c5e63ce3c9372efa212fa475275eef4dc40c2143aeda32"
SOURCE_DOI = "10.6084/m9.figshare.7734767.v8"


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def check_archive(path):
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    if path.stat().st_size != ARCHIVE_BYTES:
        raise ValueError("Archive size differs from the selected Figshare release")
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            md5.update(chunk)
            sha.update(chunk)
    if md5.hexdigest() != ARCHIVE_MD5 or sha.hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Archive hash differs from the selected Figshare release")


def selection(archive):
    by_person = defaultdict(dict)
    for info in archive.infolist():
        match = re.fullmatch(r".*/(\d+)/\1_C2_(\d+)\.c3d", info.filename)
        if match:
            person, numeric_repeat = match[1], int(match[2])
            if numeric_repeat in by_person[person]:
                raise ValueError("Repeated numeric trial identity")
            by_person[person][numeric_repeat] = info
    if len(by_person) != 50 or any(len(trials) < 3 for trials in by_person.values()):
        raise ValueError("Archive inventory differs from the selected Figshare release")
    rows = []
    for ordinal, person in enumerate(sorted(by_person), 1):
        partition = "train" if ordinal <= 30 else "assessment" if ordinal <= 40 else "reserve"
        for repeat, info in sorted(by_person[person].items())[:3]:
            rows.append({"name": info.filename, "size": info.file_size, "compressed_size": info.compress_size,
                         "crc32": f"{info.CRC:08x}", "partition": partition, "ordinal": ordinal, "repeat": repeat})
    manifest = {
        "source": SOURCE_DOI,
        "directory_sha256": "07f351cffc52506899bdabb160e53927faec588a8ae17de7687cffe1bdbd6bc5",
        "rule": "First three available numeric C2 repeats per sorted source participant, ties invalid. No outcome-based substitutions. Ordinals 1–30 train, 31–40 assessment after fit seal, 41–50 reserve no reads; only ordinal 1 repeat 01 developmental access before method lock.",
        "selected": rows,
        "prior_single_repeat_plan_sha256": "f7e0b44abd615a557206cc1025c7df9dd1265c9a24e23ad266b063d6ac78b877",
    }
    payload = (json.dumps(manifest, indent=2) + "\n").encode()
    if digest_bytes(payload) != SPLIT_SHA256:
        raise ValueError("Reconstructed split differs from the prespecified manifest")
    return rows, payload
