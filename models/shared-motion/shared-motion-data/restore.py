"""Recover one frozen role from the existing NeuroTranslation benchmark checkout."""

import argparse
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen
import os

from prepare import CONTRACT_SHA, HERE, sha


UPSTREAM = "https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/4d046b86bfa797e28f29cd4f6b8445a1f4b90487/benchmarks/"


def pinned_converter(contract):
    return {
        "windows.py": "bbe0583cd7eea9186a09aa403e0067a3783ac7665a6dcb23854d54ead8f824c5",
        "restore_tracks.py": "bc1c6499ae16e0c6a76b23acfeab2b4bdbce5677b142190c26fd1a5954289e7f",
        "protocol.json": contract["source_hashes"][
            "preceding-words-model/protocol.json"
        ],
    }


def fetch_benchmarks(contract, role, folder):
    files = {
        "preceding-instructions/preceding-words-model/" + name: digest
        for name, digest in pinned_converter(contract).items()
    }
    files["preceding-instructions/preceding-words-source/COHORT.json"] = contract[
        "source_hashes"
    ]["preceding-words-source/COHORT.json"]
    for e in contract["records"]:
        if e["domain"] == "rat" and e["role"] == role:
            rel = Path(e["path"]).relative_to("wtrack-source").as_posix()
            files["wtrack-neural-motion/recording/" + rel] = e["sha256"]
    for name, digest in files.items():
        dst = folder / name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=dst.parent) as tmp:
                candidate = Path(tmp) / dst.name
                with (
                    urlopen(UPSTREAM + name, timeout=35) as response,
                    candidate.open("wb") as stream,
                ):
                    shutil.copyfileobj(response, stream)
                if sha(candidate) != digest:
                    raise ValueError(f"Upstream bytes differ: {name}")
                try:
                    os.link(candidate, dst)
                except FileExistsError:
                    pass
        if sha(dst) != digest:
            raise ValueError(f"Unexpected cached upstream file: {name}")
    return folder


def restore(role, benchmarks, root):
    if sha(HERE / "contract.json") != CONTRACT_SHA:
        raise ValueError("Unexpected data contract")
    contract = json.loads((HERE / "contract.json").read_bytes())
    if benchmarks is None:
        benchmarks = fetch_benchmarks(contract, role, root / ".upstream-benchmarks")
    old = benchmarks / "preceding-instructions"
    source = old / "preceding-words-model"
    trusted = pinned_converter(contract)
    if any(sha(source / p) != h for p, h in trusted.items()):
        raise ValueError("Upstream hand converter or protocol changed")
    cohort = old / "preceding-words-source/COHORT.json"
    if sha(cohort) != contract["source_hashes"]["preceding-words-source/COHORT.json"]:
        raise ValueError("Unexpected source cohort")
    lookup = {r["recording"]: r for r in json.loads(cohort.read_bytes())["recordings"]}
    sys.path.insert(0, str(source.resolve()))
    converter = importlib.import_module("restore_tracks")
    converter.HERE = root / "hand-text-source"
    count = 0
    for entry in contract["records"]:
        if entry["role"] != role:
            continue
        dest = root / entry["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            if entry["domain"] == "rat":
                src = (
                    benchmarks
                    / "wtrack-neural-motion/recording"
                    / Path(entry["path"]).relative_to("wtrack-source")
                )
                if sha(src) != entry["sha256"]:
                    raise ValueError(f"Unexpected source trip: {src}")
                with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
                    candidate = Path(tmp) / dest.name
                    shutil.copyfile(src, candidate)
                    try:
                        os.link(candidate, dest)
                    except FileExistsError:
                        pass
            else:
                item = lookup[entry["recording"]]
                if (
                    item["hand_npz_sha256"] != entry["sha256"]
                    or item["hand_source_member_sha256"]
                    != entry["source_member_sha256"]
                ):
                    raise ValueError("Hand member hash conflict")
                converter.extract(item)
        if sha(dest) != entry["sha256"]:
            raise ValueError(f"Unexpected existing or restored file: {dest}")
        count += 1
    print(f"Verified {count} pinned {role} sources")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["train", "assessment"])
    parser.add_argument(
        "--benchmarks",
        type=Path,
        help="optional existing NeuroTranslation/benchmarks directory instead of pinned remote source",
    )
    parser.add_argument(
        "--root", type=Path, required=True, help="local reconstruction directory"
    )
    args = parser.parse_args()
    restore(args.role, args.benchmarks, args.root)
