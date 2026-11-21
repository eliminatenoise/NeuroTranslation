"""Stream the pinned gzip tar once, keeping only optical measurement and timing members."""

import json
import re
import subprocess
import tarfile
from pathlib import PurePosixPath

from acquire import ROOT, fetch

ARCHIVE_ROOT = "Ruhr_HandMotion_CenterOutTask"
# Only inert data and the source's unexecuted, plain-text processing scripts.
OPTICAL = re.compile(
    r"Output/measurement/([1-9]|[12][0-9]|3[01])/[LR]/(?:V/[^/]+\.csv|[^/]+\.txt|X/[^/]+\.txt)"
)
TOP = re.compile(
    r"(?:Readme\.txt|README\.txt|ExcludedTrials\.txt|Code/[^/]+\.(?:py|txt))",
    re.IGNORECASE,
)


def stage():
    archive = fetch()
    target = ROOT / "_private" / "source"
    target.mkdir(mode=0o700, exist_ok=True)
    count = 0
    nbytes = 0
    other_txt = []
    # gzip performs the serial deflate work while tarfile writes selected members.
    with subprocess.Popen(["gzip", "-dc", archive], stdout=subprocess.PIPE) as unzip:
        with tarfile.open(fileobj=unzip.stdout, mode="r|", bufsize=1 << 20) as members:
            for entry in members:
                path = PurePosixPath(entry.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or path.parts[0] != ARCHIVE_ROOT
                ):
                    raise ValueError("Unexpected archive path")
                rel = str(path.relative_to(ARCHIVE_ROOT))
                if not entry.isfile():
                    continue
                if not (OPTICAL.fullmatch(rel) or TOP.fullmatch(rel)):
                    if rel.endswith((".txt", ".py")) and len(other_txt) < 50:
                        other_txt.append(rel)
                    continue
                if entry.size > 4 << 20:
                    raise ValueError(f"Unexpectedly large member {rel}")
                data = members.extractfile(entry).read()
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                nbytes += len(data)
                count += 1
        # Read gzip trailer / padding for complete-process validation.
        while unzip.stdout.read(1 << 20):
            pass
        if unzip.wait():
            raise ValueError("Decompression failed")
    print(
        json.dumps(
            {
                "selected_members": count,
                "uncompressed_bytes": nbytes,
                "other_text_paths": other_txt,
            }
        )
    )


if __name__ == "__main__":
    stage()
