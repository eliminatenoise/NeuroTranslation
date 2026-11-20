"""Fetch the explicitly admitted members only, using exact ZIP member byte ranges."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import struct
import time
import urllib.error
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parent
FREEZE = json.loads((ROOT / "SOURCE-FREEZE.json").read_text())
MEMBERS = {Path(row["name"]).name: row for row in FREEZE["members"]}
OFFICIAL = "https://zenodo.org/api/records/4315453/files/spindle_data.zip/content"
ARCHIVE = FREEZE["archive_bytes"]
HEADER = struct.Struct("<4s5H3I2H")
BLOCK = 1024 * 1024


def identity(path):
    sha = hashlib.sha256()
    crc = 0
    n = 0
    with path.open("rb") as fin:
        while data := fin.read(BLOCK):
            sha.update(data)
            crc = zlib.crc32(data, crc)
            n += len(data)
    return {"size": n, "crc32": f"{crc:08x}", "sha256": sha.hexdigest()}


def check(path, row):
    proof = identity(path)
    if (proof["size"], proof["crc32"]) != (row["uncompressed_size"], row["crc32"]):
        raise ValueError(f"{path.name}: local size/CRC mismatch")
    name = Path(row["name"]).name
    manifest_path = ROOT / "member-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        if manifest[name] != proof:
            raise ValueError(f"{name}: SHA-256 or source identity differs from the reproduction manifest")
    if name == "aff015_proc.mat" and proof["sha256"] != FREEZE["original_pilot"]["sha256"]:
        raise ValueError("Pilot SHA-256 mismatch")
    return proof


def byte_range(start, stop, sink):
    label = f"{start}-{stop}"
    request = urllib.request.Request(
        OFFICIAL + "?range=" + label,
        headers={"Range": "bytes=" + label, "Accept-Encoding": "identity"},
    )
    sha = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(request, timeout=100) as response:
        if response.status != 206 or response.headers.get("Content-Range") != f"bytes {label}/{ARCHIVE}":
            raise ValueError(f"Server returned an unexpected range at {label}")
        while data := response.read(BLOCK):
            n += len(data)
            if n > stop - start + 1:
                raise ValueError("Oversized range")
            sha.update(data)
            sink(data)
    if n != stop - start + 1:
        raise EOFError(f"Incomplete response at {label}")
    return {"start": start, "end": stop, "sha256": sha.hexdigest()}


def fetch(directory, name, chunk_mib):
    row = MEMBERS[name]
    path = directory / name
    if path.exists():
        return {"member": name, **check(path, row), "route": "verified existing member"}
    start = row["header_offset"]
    data = bytearray()
    parts = [byte_range(start, start + HEADER.size - 1, data.extend)]
    sig, _, flags, method, _, _, crc, packed, size, name_n, extra_n = HEADER.unpack(data)
    if sig != b"PK\x03\x04" or flags & 1 or method != 8:
        raise ValueError("Unsupported local ZIP header")
    if not flags & 8 and (crc, packed, size) != (int(row["crc32"], 16), row["compressed_size"], row["uncompressed_size"]):
        raise ValueError("ZIP header differs from directory")
    start += HEADER.size
    header_end = start + name_n + extra_n - 1
    data.clear()
    parts.append(byte_range(start, header_end, data.extend))
    if data[:name_n].decode("utf8") != row["name"]:
        raise ValueError("Unexpected member filename")
    start = header_end + 1
    chunksize = chunk_mib * BLOCK
    spool = directory.parent / "range-cache" / name
    spool.mkdir(parents=True, exist_ok=True)
    last = start + row["compressed_size"] - 1
    payload = []
    for a in range(start, last+1, chunksize):
        b = min(a+chunksize-1, last)
        chunk = spool / f"{a}-{b}.deflate"
        receipt = chunk.with_suffix(".json")
        if chunk.exists() and receipt.exists():
            saved = json.loads(receipt.read_text())
            if saved["sha256"] != identity(chunk)["sha256"] or chunk.stat().st_size != b-a+1:
                raise ValueError("Existing bounded range cache differs from its proof")
        else:
            tmpchunk = chunk.with_suffix(".partial")
            issues = []
            for attempt in range(3):
                try:
                    with tmpchunk.open("wb") as part:
                        saved = byte_range(a, b, part.write)
                    break
                except (urllib.error.URLError, TimeoutError, EOFError, ConnectionError) as exc:
                    issues.append(repr(exc))
                    if attempt==2:
                        raise
                    time.sleep(2**attempt)
            if issues:
                saved["failed_attempts"] = issues
            tmpchunk.replace(chunk)
            receipt.write_text(json.dumps(saved)+"\n")
        parts.append(saved)
        payload.append(chunk)
    decoded = zlib.decompressobj(-15)
    tmp = path.with_suffix(".mat.partial")
    with tmp.open("wb") as out:
        for chunk in payload:
            with chunk.open("rb") as source:
                while block := source.read(BLOCK):
                    out.write(decoded.decompress(block))
        out.write(decoded.flush())
    if not decoded.eof or decoded.unused_data or decoded.unconsumed_tail:
        raise ValueError("Unexpected deflate stream end")
    proof = check(tmp, row)
    if name == "aff015_proc.mat" and proof["sha256"] != FREEZE["original_pilot"]["sha256"]:
        raise ValueError("Pilot SHA-256 mismatch")
    tmp.replace(path)
    return {"member": name, **proof, "route": "official exact ranges", "ranges": parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "private" / "members")
    parser.add_argument("--jobs", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--chunk-mib", type=int, choices=(2,4,8,16,32), default=8)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    ledger = args.directory.parent / "fetch-receipts.json"
    receipts = json.loads(ledger.read_text()) if ledger.exists() else {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        jobs = {pool.submit(fetch, args.directory, name, args.chunk_mib): name for name in MEMBERS}
        failures = []
        for result in concurrent.futures.as_completed(jobs):
            name = jobs[result]
            try:
                proof = result.result()
                if not (proof["route"] == "verified existing member" and receipts.get(name, {}).get("sha256") == proof["sha256"]):
                    receipts[name] = proof
                print(name, proof["size"], proof["route"], flush=True)
            except Exception as exc:
                failures.append((name, type(exc).__name__, str(exc)))
                print(name, repr(exc), flush=True)
            temp = ledger.with_suffix(".tmp")
            temp.write_text(json.dumps(receipts, indent=2, sort_keys=True) + "\n")
            temp.replace(ledger)
    if failures:
        raise SystemExit(f"Retrieval failures: {failures}")


if __name__ == "__main__":
    main()
