"""Seekable metadata pages and bounded reads of immutable AJILE12 gzip chunks."""

import hashlib
import io
import json
import os
import threading
from functools import lru_cache
from pathlib import Path

ASSETS = json.loads(Path(__file__).with_name("assets.json").read_text())
MIB = 1024**2


class Source(io.RawIOBase):
    def __init__(self, day, path, private, cap_mib):
        self.asset = ASSETS[str(day)]
        self.size = self.asset["size"]
        self.position = 0
        self.cap = cap_mib * MIB
        self.file = None
        self.lock = threading.Lock()
        self.local = threading.local()
        self.spent = 0
        if path is not None:
            if path.stat().st_size != self.size:
                raise ValueError(f"Unexpected size for session {day}; see assets.json.")
            self.file = path.open("rb")
        else:
            self.cache = private / ("ranges-" + self.asset["asset_id"])
            self.cache.mkdir(mode=0o700, exist_ok=True)
            self.ledger = self.cache / "requested-bytes.txt"
            if self.ledger.exists():
                self.spent = sum(map(int, self.ledger.read_text().splitlines()))

    def fetch(self, lo, hi):
        if not 0 <= lo < hi <= self.size:
            raise ValueError("Range lies outside the asset")
        if self.file is not None:
            with self.lock:
                self.file.seek(lo)
                blob = self.file.read(hi - lo)
            if len(blob) != hi - lo:
                raise IOError("Unexpected end of NWB file")
            return blob
        path = self.cache / f"{lo}-{hi}"
        tag = path.with_suffix(".sha256")
        if tag.exists():
            blob = path.read_bytes()
            if len(blob) != hi - lo or hashlib.sha256(blob).hexdigest() != tag.read_text():
                raise IOError("Corrupt range cache")
            return blob
        # Charge even unsuccessful responses. A server returning a full-object 200
        # is rejected before its body is read. Each worker receives a disjoint chunk.
        with self.lock:
            if self.spent + hi - lo > self.cap:
                raise ValueError("Per-asset HTTP range byte cap reached")
            with self.ledger.open("a") as f:
                f.write(f"{hi - lo}\n")
                f.flush()
                os.fsync(f.fileno())
            self.spent += hi - lo
        if not hasattr(self.local, "session"):
            import requests

            self.local.session = requests.Session()
        headers = {
            "Range": f"bytes={lo}-{hi - 1}",
            "If-Match": f'"{self.asset["etag"]}"',
            "Accept-Encoding": "identity",
        }
        with self.local.session.get(
            self.asset["url"], headers=headers, stream=True, timeout=(12, 45)
        ) as resp:
            if (
                resp.status_code != 206
                or resp.headers.get("Content-Range") != f"bytes {lo}-{hi - 1}/{self.size}"
                or resp.headers.get("ETag", "").strip('"') != self.asset["etag"]
                or int(resp.headers.get("Content-Length", -1)) != hi - lo
                or resp.headers.get("Content-Encoding", "identity") != "identity"
            ):
                raise IOError(f"Wrong HTTP range or asset identity ({resp.status_code})")
            blob = resp.raw.read(hi - lo + 1)
        if len(blob) != hi - lo:
            raise IOError("Truncated HTTP range")
        path.write_bytes(blob)
        tag.write_text(hashlib.sha256(blob).hexdigest())
        return blob

    @lru_cache(maxsize=512)
    def page(self, index):
        lo = index * 65536
        return self.fetch(lo, min(lo + 65536, self.size))

    def header(self, start, size):
        if self.file is not None:
            return self.fetch(start, start + size)
        stop = min(self.size, start + size)
        parts = []
        while start < stop:
            i, j = divmod(start, 65536)
            n = min(65536 - j, stop - start)
            parts.append(self.page(i)[j : j + n])
            start += n
        return b"".join(parts)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = (0, self.position, self.size)[whence] + offset
        if self.position < 0:
            raise ValueError("Negative NWB position")
        return self.position

    def readinto(self, buf):
        n = min(len(buf), self.size - self.position)
        if n <= 0:
            return 0
        buf[:n] = self.header(self.position, n)
        self.position += n
        return n

    def close(self):
        self.page.cache_clear()
        if self.file is not None:
            self.file.close()
        super().close()
