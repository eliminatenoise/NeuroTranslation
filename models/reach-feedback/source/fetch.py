"""Save the SHA-256-verified session from the official public ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from urllib.request import Request, urlopen
from zipfile import ZipFile
import zlib

CONFIG = json.loads(Path(__file__).with_name("selection.json").read_bytes())
CHUNK = 4 * 1024 * 1024


def ranges():
    start, end = CONFIG["inclusive_archive_byte_range"]
    for lo in range(start, end + 1, CHUNK):
        hi = min(end, lo + CHUNK - 1)
        for attempt in range(3):
            try:
                request = Request(CONFIG["url"], headers={"Range": f"bytes={lo}-{hi}", "Accept-Encoding": "identity"})
                with urlopen(request, timeout=60) as reply:
                    expected = f"bytes {lo}-{hi}/{CONFIG['archive_bytes']}"
                    if reply.status != 206 or reply.headers["Content-Range"] != expected:
                        raise ValueError(f"The archive server must return exactly {expected}. "
                                         "Download the official ZIP and pass --archive if byte ranges are unavailable.")
                    chunk = reply.read(hi - lo + 2)
                    if len(chunk) != hi - lo + 1:
                        raise EOFError("Partial range")
                break
            except (OSError, EOFError):
                if attempt == 2:
                    raise
                sleep(2 ** attempt)
        yield chunk


def local_member(archive):
    with ZipFile(archive) as zipped:
        entry = zipped.getinfo(CONFIG["member"])
        size, crc = entry.file_size, f"{entry.CRC:08x}"
        if (size, crc) != (CONFIG["member_bytes"], CONFIG["member_crc32"]):
            raise ValueError("ZIP session length or CRC mismatch")
        with zipped.open(entry) as f:
            yield from iter(lambda: f.read(CHUNK), b"")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Destination for the original MATLAB session")
    parser.add_argument("--archive", type=Path, help="An already downloaded copy of the official ZIP")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    out = args.directory / Path(CONFIG["member"]).name
    if out.exists():
        with out.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != CONFIG["member_sha256"]:
                raise ValueError(f"Existing file differs from the registered session: {out}")
        print(out)
        return
    checksum = hashlib.sha256()
    crc, size = 0, 0
    with NamedTemporaryFile(dir=args.directory, delete=False) as f:
        temp = Path(f.name)
        try:
            for block in local_member(args.archive) if args.archive else ranges():
                f.write(block)
                checksum.update(block)
                crc = zlib.crc32(block, crc)
                size += len(block)
            if (size, f"{crc:08x}", checksum.hexdigest()) != (
                    CONFIG["member_bytes"], CONFIG["member_crc32"], CONFIG["member_sha256"]):
                raise ValueError("Session length, checksum or CRC mismatch")
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.link(temp, out)
    finally:
        temp.unlink(missing_ok=True)
    print(out)


if __name__ == "__main__":
    main()
