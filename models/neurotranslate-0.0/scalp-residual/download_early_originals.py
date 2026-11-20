"""Fetch or check the selected motor-execution files from Zenodo record 834976."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import os
import tempfile
from urllib.request import Request, urlopen

from ofner_early import API, ASSESSMENT, FILES, FITTING, digests, filename


def original(cache, person, run_number, check_only=False):
    """Return the verified SHA-256. Publish complete files only, one writer per name."""
    name = filename(person, run_number)
    path = Path(cache) / name
    size, checksum = FILES[person, run_number]

    def checked():
        with path.open("rb") as stream:
            length, md5, sha = digests(stream)
        if (length, md5) != (size, checksum):
            raise ValueError(f"{name} differs from the published size or MD5")
        return sha

    if check_only or path.exists():
        return checked()
    lock = path.with_suffix(".gdf.lock")
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RuntimeError(f"Another download may be writing {name}. Inspect {lock}") from exc
    temp_path = None
    try:
        if path.exists():
            return checked()
        url = f"{API}/files/{name}/content?download=1"
        req = Request(url, headers={"Accept-Encoding": "identity"})
        with tempfile.NamedTemporaryFile(dir=cache, prefix=name + ".", delete=False) as temp:
            temp_path = Path(temp.name)
            with urlopen(req, timeout=120) as response:
                if response.status != 200:
                    raise ValueError(f"Expected HTTP 200 for the complete {name}")
                # Read at most one byte beyond the known original length.
                remaining = size
                md5 = hashlib.md5(usedforsecurity=False)
                sha = hashlib.sha256()
                while remaining:
                    block = response.read(min(1024 * 1024, remaining))
                    if not block:
                        break
                    remaining -= len(block)
                    md5.update(block)
                    sha.update(block)
                    temp.write(block)
                if remaining or response.read(1) or md5.hexdigest() != checksum:
                    raise ValueError(f"{name} differs from the published size or MD5")
        if path.exists():
            return checked()
        os.replace(temp_path, path)
        return sha.hexdigest()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=("fitting", "fourth"))
    parser.add_argument("directory", type=Path, help="folder holding the original recordings")
    parser.add_argument("--workers", type=int, choices=(1, 2, 3, 4), default=2)
    parser.add_argument("--check-only", action="store_true", help="check original files entirely offline")
    args = parser.parse_args()
    if not args.check_only:
        args.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    jobs = FITTING if args.group == "fitting" else ASSESSMENT

    def verify(job):
        person, number = job
        return original(args.directory, person, number, args.check_only), filename(person, number)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for sha, name in pool.map(verify, jobs):
            print(f"{sha}  {name}", flush=True)


if __name__ == "__main__":
    main()
