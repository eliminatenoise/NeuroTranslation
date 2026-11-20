"""Rebuild the study fits or repeat the published test using verified local source arrays."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fit", "score"))
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    stage = "development" if args.action == "fit" else "assessment"
    subprocess.run([sys.executable, str(here / "source/verify.py"), stage,
                    str(args.prepared)], check=True)
    data = args.prepared / (stage + ".npz")
    cmd = [sys.executable, str(here / "train.py"), args.action, str(data),
           str(args.output), "--sha256", sha(data), "--threads", "2"]
    if args.action == "score":
        cmd.extend(["--weights", str(here / "weights.json"), "--weights-sha256",
                    "bcdfe0ee16a5b25f6b9375deb3b931c1ee3cc2f216edbf5c163fd0b8368bbea7"])
    subprocess.run(cmd, check=True)
    ref = here / (stage + "-summary.json")
    own = args.output / (stage + "-summary.json")
    print("Released summary matches all JSON values:", json.loads(own.read_text()) == json.loads(ref.read_text()))
    if args.action == "fit":
        print("Regenerated weight SHA-256:", sha(args.output / "weights.json"))


if __name__ == "__main__":
    main()
