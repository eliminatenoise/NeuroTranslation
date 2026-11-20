"""Fetch the selected original recording objects from a version-verified catalogue."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

COMMIT = "f15449b6aecb83044b49a1798955e8a212a68fc1"
TREE = "9aae84faaa554e6cf79f569c22d40235c99c2158"
REPO = "https://github.com/OpenNeuroDatasets/ds003739.git"
S3 = "https://s3.amazonaws.com/openneuro.org/ds003739/"
STAGES = ("development", "assessment")
SUFFIXES = (
    "eeg.fdt",
    "eeg.set",
    "channels.tsv",
    "events.tsv",
    "events.json",
    "eeg.json",
)


def digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def git(catalogue, *args):
    return subprocess.check_output(["git", "-C", str(catalogue), *args])


def roster(stage, people):
    ordered = sorted(people, key=lambda name: int(name.split("-")[1]))
    pilot, rest = ordered[0], ordered[1:]
    randomized = sorted(
        rest,
        key=lambda name: hashlib.sha256(
            ("balance-stance-20261121:" + name).encode("utf-8")
        ).hexdigest(),
    )
    return {"development": [pilot, *randomized[:17]], "assessment": randomized[17:23]}[
        stage
    ]


def selection(catalogue, stage):
    if git(catalogue, "rev-parse", "HEAD", "HEAD^{tree}").decode().splitlines() != [
        COMMIT,
        TREE,
    ]:
        raise ValueError("Catalogue differs from OpenNeuro ds003739 v1.0.3")
    tree = {}
    for line in git(catalogue, "ls-tree", "-r", "HEAD").decode().splitlines():
        fields, name = line.split("\t")
        mode, _kind, blob = fields.split()
        tree[name] = (mode, blob)
    people = sorted({name.split("/")[0] for name in tree if name.startswith("sub-")})
    if len(people) != 30 or not all(re.fullmatch(r"sub-\d{3}", p) for p in people):
        raise ValueError("Unexpected BIDS participant roster")
    records, omissions = [], {}
    selected = roster(stage, people)
    for person in selected:
        matches = [
            name
            for name in tree
            if name.startswith(person + "/") and "_task-rotatewalk_" in name
        ]
        sessions = {name.rsplit("_", 1)[0] for name in matches}
        if len(sessions) != 1:
            omissions[person] = "missing or ambiguous rotatewalk session"
            continue
        prefix = sessions.pop()
        paths = [prefix + "_" + suffix for suffix in SUFFIXES]
        if any(path not in tree for path in paths):
            omissions[person] = [path for path in paths if path not in tree]
            continue
        for path in paths:
            mode, blob = tree[path]
            records.append((path, mode, blob))
    for name in ("dataset_description.json", "README"):
        records.append((name, *tree[name]))
    return records, omissions, selected


def acquire(record, catalogue, raw, reuse):
    name, mode, blob = record
    pointer = git(catalogue, "cat-file", "blob", blob)
    if (
        hashlib.sha1(
            b"blob " + str(len(pointer)).encode() + b"\0" + pointer
        ).hexdigest()
        != blob
    ):
        raise ValueError(f"Git metadata mismatch for {name}")
    target = raw / name
    target.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"git_blob": blob}
    if mode == "120000":
        key = pointer.decode().split("/")[-1]
        match = re.fullmatch(r"(MD5E|SHA256E)-s(\d+)--([a-f0-9]+)\.(?:fdt|set)", key)
        if not match:
            raise ValueError(f"Unrecognized annex pointer {key}")
        algo = {"MD5E": "md5", "SHA256E": "sha256"}[match[1]]
        size, expected = int(match[2]), match[3]
        metadata.update(annex_key=key)

        def verify(path):
            if path.stat().st_size != size or digest(path, algo) != expected:
                raise ValueError(f"Annex content mismatch for {name}")

        if target.exists():
            verify(target)
        else:
            existing = reuse / target.name if reuse is not None else None
            if existing and existing.is_file():
                verify(existing)
                try:
                    os.link(existing, target)
                except OSError:
                    shutil.copyfile(existing, target)
            else:
                tmp = None
                try:
                    with tempfile.NamedTemporaryFile(
                        dir=target.parent, delete=False
                    ) as stream:
                        tmp = Path(stream.name)
                        req = urllib.request.Request(
                            S3 + name,
                            headers={
                                "User-Agent": "OpenNeuro ds003739 reproducibility"
                            },
                        )
                        with urllib.request.urlopen(req, timeout=90) as response:
                            shutil.copyfileobj(response, stream, 1024 * 1024)
                    verify(tmp)
                    tmp.replace(target)
                finally:
                    if tmp is not None:
                        tmp.unlink(missing_ok=True)
    elif mode == "100644":
        if not target.exists() or target.read_bytes() != pointer:
            target.write_bytes(pointer)
    else:
        raise ValueError(f"Unexpected mode {mode} for {name}")
    metadata.update(bytes=target.stat().st_size, sha256=digest(target))
    return name, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("work", type=Path)
    parser.add_argument(
        "--reuse-flat", type=Path, help="optional existing verified flat cache"
    )
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 8:
        parser.error("Use 1–8 concurrent reads")
    args.work.mkdir(exist_ok=True, parents=True)
    catalogue = args.work / "catalogue"
    if not catalogue.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                "--depth",
                "1",
                "--branch",
                "1.0.3",
                REPO,
                str(catalogue),
            ],
            check=True,
        )
    records, omissions, selected = selection(catalogue, args.stage)
    raw = args.work / "raw"

    def one(record):
        return acquire(record, catalogue, raw, args.reuse_flat)

    with ThreadPoolExecutor(args.jobs) as pool:
        inventory = dict(pool.map(one, records))
    receipt = {
        "dataset": "ds003739",
        "version": "1.0.3",
        "commit": COMMIT,
        "tree": TREE,
        "stage": args.stage,
        "selected": selected,
        "catalogue_omissions": omissions,
        "files": inventory,
    }
    path = args.work / f"{args.stage}-files.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        f"{len(inventory)} files verified; {len(omissions)} catalogue omissions. Receipt: {path}"
    )


if __name__ == "__main__":
    main()
