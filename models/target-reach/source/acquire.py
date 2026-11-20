"""Fetch OSF file version 1 once, cap its byte count, and verify its published SHA-256."""

import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
SELECTION = ROOT / "selection.json"
SELECTION_HASH = "9bfc6620e75981f430e5ace40518a62bd70bd81bf53982daa9776a2378992435"
PUBLISHED = "https://osf.io/download/4tq78/?version=1"


def fetch():
    if hashlib.sha256(SELECTION.read_bytes()).hexdigest() != SELECTION_HASH:
        raise ValueError("The prospective selection changed.")
    spec = json.loads(SELECTION.read_text())
    cache = ROOT / "_private"
    cache.mkdir(mode=0o700, exist_ok=True)
    dest = cache / spec["archive"]
    if dest.is_file():
        with dest.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != spec["sha256"]:
                raise ValueError("Local file differs from the OSF version-1 digest.")
        return dest
    expected = spec["bytes"]
    with NamedTemporaryFile(
        dir=cache, prefix=dest.name + ".", suffix=".partial", delete=False
    ) as out:
        temp = Path(out.name)
        try:
            with urlopen(PUBLISHED, timeout=90) as src:
                if int(src.headers.get("Content-Length", expected)) != expected:
                    raise ValueError("Unexpected OSF content length.")
                read = 0
                digest = hashlib.sha256()
                while chunk := src.read(4 << 20):
                    read += len(chunk)
                    if read > expected:
                        raise ValueError("OSF response exceeded the pinned byte count.")
                    out.write(chunk)
                    digest.update(chunk)
            if read != expected or digest.hexdigest() != spec["sha256"]:
                raise ValueError("OSF response failed size or SHA-256 verification.")
        except BaseException:
            out.close()
            temp.unlink(missing_ok=True)
            raise
    os.replace(temp, dest)
    return dest


if __name__ == "__main__":
    print(fetch())
