"""Compare a local refit against the distributed aggregate model and scores."""
import argparse
import json
import math
from pathlib import Path

from infer import HERE


def compare(expected, obtained, path):
    if type(expected) is not type(obtained):
        raise ValueError(f"{path}: value type differs")
    if isinstance(expected, dict):
        if expected.keys() != obtained.keys():
            raise ValueError(f"{path}: key inventory differs")
        for key in expected:
            compare(expected[key], obtained[key], f"{path}/{key}")
    elif isinstance(expected, list):
        if len(expected) != len(obtained):
            raise ValueError(f"{path}: sequence lengths differ")
        for i, (left, right) in enumerate(zip(expected, obtained)):
            compare(left, right, f"{path}/{i}")
    elif isinstance(expected, float):
        if not math.isclose(expected, obtained, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f"{path}: numeric values differ")
    elif expected != obtained:
        raise ValueError(f"{path}: values differ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("refit_dir", type=Path)
    args = parser.parse_args()
    for name in ("model.json", "scores.json"):
        original = json.loads((HERE / name).read_text(encoding="utf-8"))
        local = json.loads((args.refit_dir / name).read_text(encoding="utf-8"))
        compare(original, local, name)
    print("All refitted model parameters, grouped scores and coverage match.")
