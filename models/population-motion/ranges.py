"""Read sparse, immutable ranges. Persist a digest for each block used in the analysis."""
from pathlib import Path
import hashlib
import io
import requests


class PinnedRanges(io.RawIOBase):
    block = 262144
    limit = 480

    def __init__(self, cache, pin, expected=None):
        self.pin = pin
        self.cache = Path(cache) / pin["etag"]
        self.cache.mkdir(parents=True, exist_ok=True)
        self.client = requests.Session()
        self.offset = 0
        self.digests = {}
        self.expected = expected or {}
        self.network_bytes = 0

    def seek(self, offset, whence=0):
        self.offset = (0, self.offset, self.pin["size"])[whence] + offset
        if self.offset < 0:
            raise ValueError("Negative seek")
        return self.offset

    def tell(self):
        return self.offset

    def readinto(self, target):
        dest = memoryview(target).cast("B")
        count = max(0, min(len(dest), self.pin["size"] - self.offset))
        done = 0
        while done < count:
            index, inside = divmod(self.offset, self.block)
            start = index * self.block
            stop = min(start + self.block, self.pin["size"]) - 1
            file = self.cache / str(index)
            if str(index) not in self.digests and len(self.digests) >= self.limit:
                raise OSError("120 MiB per-asset sparse-read limit reached")
            if not file.exists():
                headers = {"Range": f"bytes={start}-{stop}", "If-Match": f'"{self.pin["etag"]}"'}
                with self.client.get(self.pin["url"], headers=headers, stream=True, timeout=30) as res:
                    if (res.status_code != 206 or res.headers["Content-Range"] !=
                        f'bytes {start}-{stop}/{self.pin["size"]}' or
                        res.headers["ETag"].strip('"') != self.pin["etag"]):
                        raise OSError(f"Archive range/identity mismatch at {start}")
                    data = res.content
                if len(data) != stop - start + 1:
                    raise OSError("Incomplete range")
                self.network_bytes += len(data)
                tmp = file.with_suffix(".partial")
                tmp.write_bytes(data)
                tmp.replace(file)
            else:
                data = file.read_bytes()
            if len(data) != stop - start + 1:
                raise OSError("Incomplete cached range")
            if str(index) not in self.digests:
                self.digests[str(index)] = hashlib.sha256(data).hexdigest()
                if str(index) in self.expected and self.digests[str(index)] != self.expected[str(index)]:
                    raise OSError(f"Range {index} differs from recorded digest")
            used = min(count - done, len(data) - inside)
            dest[done:done+used] = data[inside:inside+used]
            done += used
            self.offset += used
        return done

    def close(self):
        self.client.close()
        super().close()
