"""Pin every fitted candidate and the unmodified evaluation implementation."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = ["train.npz", "conditional.json", "history-only.json", "ridge.npz"]
SOURCES = ["cohort.json", "schema.json", "protocol.md", "forecast.py", "fit.py", "prepare.py", "assess.py", "seal.py", "acquire.py"]


def hashes(base, files):
    return {f: hashlib.sha256((base / f).read_bytes()).hexdigest() for f in files}


def pin(local):
    return {"artifacts": hashes(local, ARTIFACTS), "sources": hashes(HERE, SOURCES)}


def check(local):
    if json.loads((local / "lock.json").read_text()) != pin(local):
        raise ValueError("The training gallery, checkpoint, protocol or scoring code changed after fit lock")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("local", type=Path)
    a = p.parse_args()
    with (a.local / "lock.json").open("x") as stream:
        json.dump(pin(a.local), stream, indent=2)
        stream.write("\n")
