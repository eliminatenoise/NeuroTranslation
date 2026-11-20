"""Acquire selected Experiment 2 MATLAB members by exact byte range (Python 3.11+)."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import http.client
import json
from pathlib import Path
import struct
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zlib


HERE = Path(__file__).resolve().parent
CHUNK = 4 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@contextmanager
def staged_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix="." + path.name + ".", suffix=".part", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        yield temporary
    finally:
        temporary.unlink(missing_ok=True)


def save(path, data):
    with staged_file(path) as temporary:
        temporary.write_bytes(data)
        temporary.replace(path)


def save_json(path, data):
    save(path, (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())


def retry_read(operation, name):
    for attempt in range(3):
        try:
            return operation()
        except HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            if retry_after and (not retry_after.isdecimal() or int(retry_after) > 60):
                raise
            delay = max(2 ** (attempt + 1), int(retry_after or 0))
        except (URLError, TimeoutError, ConnectionError, http.client.IncompleteRead):
            if attempt == 2:
                raise
            delay = 2 ** (attempt + 1)
        print(f"Retrying {name} in {delay} s", flush=True)
        time.sleep(delay)


def read_metadata(url, limit):
    def fetch():
        with urlopen(Request(url, headers={"Accept-Encoding": "identity"}), timeout=45) as reply:
            data = reply.read(limit + 1)
            require(reply.status == 200 and len(data) <= limit, "Original metadata exceeds expected bounds")
            return data

    return retry_read(fetch, url)


def verify_catalog(source, directory):
    info = source["integrity_manifest"]
    if directory is None:
        catalog = read_metadata("https://zenodo.org/api/records/19065545", 1024 * 1024)
        manifest = read_metadata(info["url"], info["bytes"])
    else:
        catalog = (directory / "record.json").read_bytes()
        manifest = (directory / "trial_integrity_manifest.csv").read_bytes()
    record = json.loads(catalog)
    require(record["doi"] == source["doi"] == "10.5281/zenodo.19065545"
            and record["metadata"]["license"]["id"] == source["license_code"] == "cc-by-4.0",
            "Dataset identifier or license differs from the cited release")
    require(record["title"] == source["dataset"] and record["metadata"]["relations"]["version"][0]["index"] == 1,
            "Unexpected record title or version")
    files = {f["key"]: f for f in record["files"]}
    for archive in source["archives"].values():
        entry = files[archive["name"]]
        require((entry["size"], entry["checksum"], entry["links"]["self"]) ==
                (archive["size"], archive["md5"], archive["url"]), "Source archive details changed")
    entry = files["trial_integrity_manifest.csv"]
    require(entry["size"] == info["bytes"] == len(manifest) and entry["checksum"] == "md5:" + info["md5"]
            and entry["links"]["self"] == info["url"] and sha(manifest) == info["sha256"]
            and hashlib.md5(manifest, usedforsecurity=False).hexdigest() == info["md5"],
            "Original integrity manifest differs")
    selected = {(person, archive["name"].split("_")[-1][:8], trial)
                for person, archive in source["archives"].items() for trial in source["trials"]}
    for row in csv.DictReader(manifest.decode().splitlines(), delimiter=";"):
        key = (row["subject"], row["date"], int(row["trial"]))
        require(int(row["experiment"]) != 2 or key not in selected,
                f"Source integrity manifest reports a selected recording as {row['status']}")


class Archive:
    def __init__(self, info, cache):
        self.info = info
        self.cache = cache

    def read(self, start, end):
        size = self.info["size"]
        require(0 <= start <= end < size, "Invalid source interval")
        path = self.cache / f"{start}-{end}"
        length = end - start + 1
        if path.exists():
            data = path.read_bytes()
            require(len(data) == length, "Corrupt partial range cache")
            return data
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        def fetch():
            with urlopen(Request(self.info["url"], headers=headers), timeout=60) as reply:
                require(reply.status == 206 and reply.headers["Content-Range"] == f"bytes {start}-{end}/{size}",
                        "Source did not return the exact requested range")
                data = reply.read(length + 1)
                if len(data) != length:
                    raise http.client.IncompleteRead(data)
                save(path, data)
                return data

        return retry_read(fetch, f"{self.info['name']} range {start}-{end}")

    def directory(self, wanted):
        size = self.info["size"]
        trailer = self.read(size - 22, size - 1)
        magic, disk, directory_disk, entries, total, length, start, comment = struct.unpack("<4s4H2LH", trailer)
        require((magic, disk, directory_disk, entries, total, comment) == (b"PK\x05\x06", 0, 0, 24, 24, 0),
                "Unexpected end-of-central-directory record")
        require(start + length == size - 22, "Invalid directory location")
        raw = self.read(start, start + length - 1)
        position = 0
        found = {}
        for _ in range(entries):
            h = struct.unpack_from("<4s6H3L5H2L", raw, position)
            require(h[0] == b"PK\x01\x02", "Invalid central-directory signature")
            n, x, c = h[10:13]
            name = raw[position + 46:position + 46 + n].decode("ascii")
            if name in wanted:
                require(name not in found and h[3:5] == (0, 8) and h[13] == 0, "Unexpected member encoding")
                found[name] = h
            position += 46 + n + x + c
        require(position == len(raw) and set(found) == set(wanted), "Invalid or incomplete member directory")
        return found, {"central_directory_range": [start, start + length - 1], "central_directory_sha256": sha(raw),
                       "eocd_range": [size - 22, size - 1], "eocd_sha256": sha(trailer), "entries": entries}

    def member(self, name, h, directory, output, workers, pins):
        offset = h[-1]
        fixed = self.read(offset, offset + 29)
        l = struct.unpack("<4s5H3L2H", fixed)
        require(l[0] == b"PK\x03\x04" and l[1:9] == h[2:10], "Local/central member header mismatch")
        n, extra = l[-2:]
        suffix = self.read(offset + 30, offset + 29 + n + extra)
        require(suffix[:n].decode("ascii") == name, "Local member name mismatch")
        first = offset + 30 + n + extra
        past = first + h[8]
        require(past <= directory["central_directory_range"][0], "Member overlaps directory")
        ranges = [(i, min(i + CHUNK, past) - 1) for i in range(first, past, CHUNK)]
        parts = []
        outer = hashlib.sha256()
        inner = hashlib.sha256()
        crc = length = 0
        inflater = zlib.decompressobj(-15)
        with staged_file(output) as tmp:
            with ThreadPoolExecutor(workers) as pool, tmp.open("wb") as stream:
                for limits, block in zip(ranges, pool.map(lambda r: self.read(*r), ranges), strict=True):
                    parts.append({"inclusive_range": list(limits), "sha256": sha(block)})
                    outer.update(block)
                    data = inflater.decompress(block)
                    inner.update(data)
                    stream.write(data)
                    crc = zlib.crc32(data, crc)
                    length += len(data)
            require(inflater.eof and not inflater.unused_data and length == h[9] and crc == h[7],
                    "Member failed decompression length/CRC verification")
            compressed_hash, mat_hash = outer.hexdigest(), inner.hexdigest()
            with tmp.open("rb") as stream:
                require(hashlib.file_digest(stream, "sha256").hexdigest() == mat_hash, "Failed MAT readback")
            receipt = {"archive": self.info, "whole_archive_md5_verified": False, "member": name, **directory,
                       "local_header_range": [offset, first - 1], "local_header_sha256": sha(fixed + suffix),
                       "compression": "ZIP raw DEFLATE", "compressed_range": [first, past - 1], "compressed_bytes": h[8],
                       "compressed_sha256": compressed_hash, "member_bytes": h[9], "member_sha256": mat_hash,
                       "member_crc32": f"{crc:08x}", "payload_ranges": parts}
            if pins is not None:
                for field, expected in pins.items():
                    require(receipt[field] == expected, f"{name} disagrees with frozen {field}")
            if output.is_file():
                with output.open("rb") as stream:
                    require(hashlib.file_digest(stream, "sha256").hexdigest() == mat_hash, "Existing MAT is different")
            else:
                tmp.replace(output)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--people", nargs="+", default=None)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--metadata", type=Path, default=HERE / "source.json")
    parser.add_argument("--catalog-directory", type=Path,
                        help="Use saved original record.json and trial_integrity_manifest.csv for offline verification")
    parser.add_argument("--derive-member-pins", action="store_true",
                        help="First acquisition from a named source, before hashes have been published")
    args = parser.parse_args()
    source = json.loads(args.metadata.read_bytes())
    cohort = source["archives"]
    people = args.people or list(cohort)
    require(all(person in cohort for person in people) and len(set(people)) == len(people), "Choose listed participants")
    pins = source.get("members", {})
    require(pins or args.derive_member_pins, "Missing frozen member evidence")
    verify_catalog(source, args.catalog_directory)
    for person in people:
        archive = Archive(cohort[person], args.destination / "ranges" / person)
        session = archive.info["name"].removeprefix("Experiment2_").removesuffix(".zip")
        wanted = {f"{session}_trial_{trial:02}.mat": trial for trial in source["trials"]}
        headers, directory = archive.directory(wanted)
        for name, trial in wanted.items():
            output = args.destination / person / f"trial-{trial:02}.mat"
            receipt = archive.member(name, headers[name], directory, output, args.workers,
                                     pins[name] if pins else None)
            save_json(output.with_suffix(".source.json"), receipt)
            print(person, trial, receipt["member_sha256"], flush=True)


if __name__ == "__main__":
    main()
