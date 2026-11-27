"""A seekable, read-only view of one immutable HTTP object, read by byte ranges (for HDF5/NWB files).

Every request is a GET with Range and If-Match (the archive ETag), paced at one request per second per
host by common.Pacer; a 429 raises common.Stop429 and nothing is retried. Each response must be 206 with
the exact Content-Range and ETag. Every request is recorded (URL, range, bytes, sha256) and written to
DOWNLOADS.json in batches.

Fetched bytes are kept in an interval cache. A read that misses bytes expands each missing piece to
aligned blocks (64 KiB) for efficiency, but the expansion is clipped so that it never enters a forbidden
interval (forbid=[(start, stop), ...]); a read that itself touches a forbidden interval raises
ForbiddenRange before any request is made. A caller that knows the file offsets of held data (for
example the samples of a recording after a time cut) forbids them, so neither HDF5 metadata reads nor
block expansion can transfer a held byte.
"""
import bisect
import http.client
import hashlib
import io
import time
import urllib.error
import urllib.parse
import urllib.request

import common

BLOCK = 64 * 1024
MAX_REQUEST = 32 * 1024 * 1024
RETRY_WAITS_S = (5, 20, 60)  # only for connection errors without an HTTP status; never for 429 or other statuses


class ForbiddenRange(Exception):
    pass


def _subtract(a, b, intervals):
    """Pieces of [a, b) outside the sorted, disjoint intervals."""
    out, cur = [], a
    for fa, fb in intervals:
        if fb <= cur or fa >= b:
            continue
        if fa > cur:
            out.append((cur, fa))
        cur = max(cur, fb)
        if cur >= b:
            break
    if cur < b:
        out.append((cur, b))
    return out


class RangeFile(io.RawIOBase):
    def __init__(self, paths, url, size, etag, dataset, label, pacer=None, budget_bytes=4_000_000_000,
                 block=BLOCK, log_every=40, forbid=()):
        self.paths, self.url, self.size, self.etag = paths, url, int(size), etag
        self.dataset, self.label = dataset, label
        self.pacer = pacer or common.Pacer(1.05)
        self.block = block
        self.pos = 0
        self.starts, self.chunks = [], []  # sorted disjoint cached intervals: start -> bytes
        self.budget = budget_bytes
        self.network_bytes = 0
        self.requests = 0
        self.pending = []
        self.log_every = log_every
        self.host = urllib.parse.urlsplit(url).netloc
        self.set_forbidden(forbid)

    # io.RawIOBase ---------------------------------------------------------------------------
    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        pos = (0, self.pos, self.size)[whence] + offset
        if pos < 0:
            raise ValueError("negative offset")
        self.pos = pos
        return pos

    def readinto(self, target):
        out = memoryview(target).cast("B")
        n = max(0, min(len(out), self.size - self.pos))
        if n == 0:
            return 0
        data = self.read_range(self.pos, self.pos + n, expand=True)
        out[:n] = data
        self.pos += n
        return n

    # ranges ---------------------------------------------------------------------------------
    def set_forbidden(self, intervals):
        iv = sorted((int(a), int(b)) for a, b in intervals if int(b) > int(a))
        merged = []
        for a, b in iv:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        self.forbid = merged

    def _touches_forbidden(self, a, b):
        return any(a < fb and fa < b for fa, fb in self.forbid)

    def _cached_pieces(self, a, b):
        """Missing pieces of [a, b) given the cache."""
        cached = [(s, s + len(c)) for s, c in zip(self.starts, self.chunks)]
        return _subtract(a, b, cached)

    def read_range(self, a, b, expand=False):
        """Bytes [a, b). Missing bytes are fetched exactly (expand=False) or expanded to aligned blocks
        clipped against forbidden intervals and already cached bytes (expand=True)."""
        if self._touches_forbidden(a, b):
            raise ForbiddenRange("read [%d, %d) touches a forbidden interval of %s" % (a, b, self.label))
        for ma, mb in self._cached_pieces(a, b):
            if expand:
                ea = (ma // self.block) * self.block
                eb = min(-(-mb // self.block) * self.block, self.size)
                pieces = _subtract(ea, eb, self.forbid)
                pieces = [p for q in pieces for p in self._cached_pieces(*q)]
            else:
                pieces = [(ma, mb)]
            for pa, pb in pieces:
                s = pa
                while s < pb:
                    e = min(pb, s + MAX_REQUEST)
                    self._fetch(s, e)
                    s = e
        return self._assemble(a, b)

    def _assemble(self, a, b):
        out = bytearray(b - a)
        i = max(0, bisect.bisect_right(self.starts, a) - 1)
        got = 0
        while i < len(self.starts) and self.starts[i] < b:
            s, c = self.starts[i], self.chunks[i]
            lo, hi = max(a, s), min(b, s + len(c))
            if hi > lo:
                out[lo - a:hi - a] = c[lo - s:hi - s]
                got += hi - lo
            i += 1
        if got != b - a:
            raise OSError("cache assembly incomplete for %s" % self.label)
        return bytes(out)

    def _insert(self, a, data):
        i = bisect.bisect_left(self.starts, a)
        self.starts.insert(i, a)
        self.chunks.insert(i, data)

    def _fetch(self, start, stop_excl):
        stop = stop_excl - 1
        if self._touches_forbidden(start, stop_excl):
            raise ForbiddenRange("fetch [%d, %d) touches a forbidden interval of %s" % (start, stop_excl, self.label))
        if self.network_bytes + (stop_excl - start) > self.budget:
            raise OSError("range budget exceeded for %s (%d bytes)" % (self.label, self.budget))
        req = urllib.request.Request(self.url, headers={
            "Range": "bytes=%d-%d" % (start, stop), "If-Match": '"%s"' % self.etag,
            "User-Agent": common.USER_AGENT, "Accept-Encoding": "identity"})
        for attempt in range(len(RETRY_WAITS_S) + 1):
            self.pacer.wait(self.host)
            try:
                resp = urllib.request.urlopen(req, timeout=180)
                data = resp.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    self.pending.append({"dataset": self.dataset, "url": self.url, "range": "bytes=%d-%d" % (start, stop),
                                         "status": 429, "bytes": 0, "sha256": None, "object": self.label,
                                         "note": "stopped on 429; no retry"})
                    self.flush_log()
                    raise common.Stop429("429 from %s" % self.host)
                raise
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError, http.client.HTTPException) as e:
                # connection-level failure (no HTTP status): a few spaced retries of the same range
                self.pending.append({"dataset": self.dataset, "url": self.url, "range": "bytes=%d-%d" % (start, stop),
                                     "status": None, "bytes": 0, "sha256": None, "object": self.label,
                                     "note": "connection error (%s); attempt %d" % (type(e).__name__, attempt + 1)})
                if attempt == len(RETRY_WAITS_S):
                    self.flush_log()
                    raise
                time.sleep(RETRY_WAITS_S[attempt])  # spaced retry of one failed connection, not a wait loop
        status = resp.status
        cr = resp.headers.get("Content-Range")
        et = (resp.headers.get("ETag") or "").strip('"')
        resp.close()
        if status != 206 or cr != "bytes %d-%d/%d" % (start, stop, self.size) or et != self.etag \
                or len(data) != stop_excl - start:
            raise OSError("range or ETag mismatch at %d for %s" % (start, self.label))
        self.requests += 1
        self.network_bytes += len(data)
        self.pending.append({"dataset": self.dataset, "url": self.url, "range": "bytes=%d-%d" % (start, stop),
                             "status": status, "content_range": cr, "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest(), "etag": et, "object": self.label})
        self._insert(start, data)
        if len(self.pending) >= self.log_every:
            self.flush_log()

    def flush_log(self):
        if self.pending:
            common.log_downloads(self.paths, self.pending)
            self.pending = []

    def drop_cache(self):
        self.starts, self.chunks = [], []

    def close(self):
        try:
            self.flush_log()
        finally:
            super().close()
