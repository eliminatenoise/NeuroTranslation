"""Fetch only specified CMU trials with per-source hashing and fit-lock validation."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from seal import HERE, check


def acquire(split, destination, local, published):
    if split != "train":
        check(local)
    rows = json.loads((HERE / "cohort.json").read_text())["rows"]
    destination.mkdir(parents=True, exist_ok=True)
    pins = {}
    log = []
    for row in rows:
        if row["split"] != split:
            continue
        uid, url = row["id"], row["url"]
        path = destination / (uid + ".c3d")
        if path.exists():
            raw = path.read_bytes()
        else:
            try:
                with urlopen(url, timeout=20) as response:
                    raw = response.read(32 * 1024 * 1024 + 1)
            except (URLError, TimeoutError) as e:
                log.append({"id": uid, "error": str(e)})
                continue
        if not (512 <= len(raw) <= 32 * 1024 * 1024 and raw[1] == 80):
            log.append({"id": uid, "error": "Invalid C3D file header/length"})
            continue
        digest = hashlib.sha256(raw).hexdigest()
        expected = row.get("sha256") or published.get(uid)
        if expected and digest != expected:
            raise ValueError("CMU source hash mismatch: " + uid)
        if not path.exists():
            path.write_bytes(raw)
        pins[uid] = digest
        log.append({"id": uid, "sha256": digest, "bytes": len(raw)})
    (local / (split + "-hashes.json")).write_text(json.dumps(pins, indent=2) + "\n")
    (local / (split + "-acquisition.json")).write_text(json.dumps(log, indent=2) + "\n")
    print(split, len(pins), "verified originals acquired", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("split", choices=["train", "fresh", "previous"])
    p.add_argument("destination", type=Path)
    p.add_argument("local", type=Path)
    a = p.parse_args()
    a.local.mkdir(parents=True, exist_ok=True)
    record = HERE / "fresh-hashes.json"
    acquire(a.split, a.destination, a.local, json.loads(record.read_text()) if record.exists() else {})
