"""Seek into one immutable HTTP object. Each cached range is bound to the archive ETag."""

import hashlib
import io
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ASSET = "4b7c7959-04b3-4817-8f96-1af6f41888c1"
ETAG = "ca822b7303cf85d5d7172f85db8799e1-422"
SHA256 = "6b8cf8ce3bbe34374e10a8a310592d1ae9762b20554569bc3c45fcfecdcf67b6"
URL = "https://dandiarchive.s3.amazonaws.com/blobs/73c/440/73c440fb-d948-4f24-b1a6-bf792e2cd870"
SIZE = 28291364968
BLOCK = 256 * 1024


class PinnedRanges(io.RawIOBase):
    def __init__(self, cache):
        self.cache = Path(cache) / ETAG
        self.cache.mkdir(exist_ok=True, parents=True)
        self.client = requests.Session()
        self.pos = 0
        record = ROOT / "evidence/blocks.json"
        self.expected = json.loads(record.read_bytes()) if record.exists() else {}
        self.seen = {}
        self.download_bytes = 0

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        pos = [0, self.pos, SIZE][whence] + offset
        if pos < 0:
            raise ValueError("negative offset")
        self.pos = pos
        return pos

    def readinto(self, target):
        out = memoryview(target).cast("B")
        n = max(0, min(len(out), SIZE - self.pos))
        written = 0
        while written < n:
            index, off = divmod(self.pos, BLOCK)
            first = index * BLOCK
            last = min(first + BLOCK, SIZE) - 1
            path = self.cache / str(index)
            if not path.exists():
                if len(self.seen) >= 480:
                    raise OSError("Sparse read budget exceeded (120 MiB)")
                headers = {"Range": f"bytes={first}-{last}", "If-Match": f'"{ETAG}"'}
                with self.client.get(
                    URL, headers=headers, timeout=25, stream=True
                ) as reply:
                    if (
                        reply.status_code != 206
                        or reply.headers.get("Content-Range")
                        != f"bytes {first}-{last}/{SIZE}"
                        or reply.headers.get("ETag", "").strip('"') != ETAG
                    ):
                        raise OSError(
                            f"Archive range or ETag mismatch for block {index}"
                        )
                    data = reply.content
                if len(data) != last - first + 1:
                    raise OSError("Short range")
                temp = path.with_suffix(f".{os.getpid()}.tmp")
                temp.write_bytes(data)
                os.replace(temp, path)
                self.download_bytes += len(data)
            else:
                data = path.read_bytes()
            if index not in self.seen:
                self.seen[index] = hashlib.sha256(data).hexdigest()
                expected = self.expected.get(str(index))
                if expected is not None and expected != self.seen[index]:
                    raise OSError(
                        f"Cached range {index} differs from the verified source digest"
                    )
            size = min(n - written, len(data) - off)
            if size <= 0:
                raise OSError("Short cached range")
            out[written : written + size] = data[off : off + size]
            self.pos += size
            written += size
        return n

    def close(self):
        self.client.close()
        super().close()
