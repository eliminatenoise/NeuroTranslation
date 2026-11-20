"""Obtain only the frozen CMU split, keeping original source bytes locally."""

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
FROZEN = "91cbc857cbd09c354535b7897829ec569e8786381d69c1fefc3fe3b08dd1ace2"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    raw = (HERE / "split.json").read_bytes()
    if digest(raw) != FROZEN:
        raise ValueError("Unexpected selection manifest")
    return json.loads(raw)


def fetch(row, dest, expected):
    path = dest / (row["id"] + ".c3d")
    if path.exists():
        raw = path.read_bytes()
    else:
        with urlopen(row["url"], timeout=35) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
        if not (512 <= len(raw) <= 32 * 1024 * 1024 and raw[1] == 80):
            raise ValueError(f"Invalid C3D response for {row['id']}")
    sha = digest(raw)
    if expected is not None and expected != sha:
        raise ValueError(f"Unexpected source hash for {row['id']}")
    if not path.exists():
        tmp = path.with_suffix(".part")
        tmp.write_bytes(raw)
        tmp.replace(path)
    return {"id": row["id"], "sha256": sha, "bytes": len(raw)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("split", choices=["train", "assessment"])
    p.add_argument("--local", required=True, type=Path)
    args = p.parse_args()
    if args.split == "assessment":
        lock = args.local / "fit" / "lock.json"
        if not lock.exists():
            raise ValueError("Fit on training data and seal the checkpoints first")
        for name, sha in json.loads(lock.read_text()).items():
            if digest((lock.parent / name).read_bytes()) != sha:
                raise ValueError(f"Checkpoint changed: {name}")
    dest = args.local / args.split
    dest.mkdir(parents=True, exist_ok=True)
    pins_file = HERE / "source-hashes.json"
    pins = json.loads(pins_file.read_text())
    selected = [r for r in manifest()["clips"] if r["split"] == args.split]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(fetch, row, dest, pins[row["id"]]) for row in selected]
        results = [job.result() for job in jobs]
    (dest / "acquisition.json").write_text(json.dumps(results, indent=2) + "\n")
    print(args.split, len(results), sum(r["bytes"] for r in results))


if __name__ == "__main__":
    main()
