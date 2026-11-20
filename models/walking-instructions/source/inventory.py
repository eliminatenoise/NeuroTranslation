"""Rebuild the fixed C4/C5 inventory using only the original ZIP directory."""
from collections import defaultdict
from pathlib import Path
import re

from prepare_source import selection


def roster(archive):
    original, _ = selection(archive)
    by_ordinal = {row["ordinal"]: Path(row["name"]).parent.name for row in original}
    by_key = {}
    for member in archive.infolist():
        match = re.fullmatch(r".*/(\d+)/\1_C([45])_(0[123])\.c3d", member.filename)
        if match:
            key = (match[1], int(match[2]), int(match[3]))
            if key in by_key:
                raise ValueError("Duplicate recording")
            by_key[key] = member
    rows = defaultdict(list)
    for ordinal in range(1, 41):
        person = by_ordinal[ordinal]
        stage = "development" if ordinal <= 30 else "historical"
        for condition in (4, 5):
            for repeat in (1, 2, 3):
                member = by_key.get((person, condition, repeat))
                rows[stage].append((ordinal, person, condition, repeat, member))
    return dict(rows)


def public_metadata(rows):
    return {stage: [
        {"ordinal": ordinal, "condition": condition, "repeat": repeat, "member": None if member is None else {
            "bytes": member.file_size, "compressed_bytes": member.compress_size, "crc32": f"{member.CRC:08x}"}}
        for ordinal, _, condition, repeat, member in trials] for stage, trials in rows.items()}
