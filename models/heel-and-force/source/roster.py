"""Reconstruct both original and supplemental rosters from archive-directory metadata."""
import json
from pathlib import Path
import re

from prepare_source import selection


def build(archive, table):
    original, split_payload = selection(archive)
    historic = [r for r in original if r["partition"] == "assessment"]
    people = {Path(r["name"]).parent.name: r["ordinal"] for r in historic}
    original_names = {r["name"] for r in historic}
    later = []
    for item in archive.infolist():
        match = re.fullmatch(r".*/(\d+)/\1_C2_(\d+)\.c3d", item.filename)
        if not match or match[1] not in people or item.filename in original_names:
            continue
        repeat = int(match[2])
        if repeat not in (4, 5):
            raise ValueError("Unrecognized additional historic-assessment repeat")
        later.append({"name": item.filename, "size": item.file_size, "compressed_size": item.compress_size,
                      "crc32": f"{item.CRC:08x}", "partition": "later-repeats",
                      "ordinal": people[match[1]], "repeat": repeat})
    later.sort(key=lambda r: (r["ordinal"], r["repeat"]))
    if len(later) != 18 or len({r["name"] for r in later}) != len(later):
        raise ValueError("Supplemental recording inventory changed")
    return {"train": [r for r in original if r["partition"] == "train"], "assessment": historic,
            "later-repeats": later}, split_payload


def supplement_manifest(rows, table):
    return {"scope": "Every remaining C2 repeat (04 or 05) in the 10 previously used assessment participants. Separate secondary analysis; never replace original trials or people. No reserve participants.",
            "source": "10.6084/m9.figshare.7734767.v8",
            "members": [dict(r, contact=table.contacts(Path(r["name"]).name)) for r in rows]}
