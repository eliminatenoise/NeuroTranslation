"""Combine a locally fitted shoulder-frame ensemble and ridge heads for offline replay."""
import argparse
import json
from pathlib import Path

import numpy as np

from .weights import write


def convert(temporal_path, ridge_path, out):
    with np.load(temporal_path, allow_pickle=False) as data:
        if str(data["bridge_version"].item()) != "shoulder-frame-v1":
            raise ValueError("Require an ensemble fitted in the earlier shoulder frame.")
        weights = {k: data[k] for k in data.files if k != "bridge_version"}
    heads = json.loads(ridge_path.read_bytes())["heads"]
    write(out, weights, heads, "local")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ensemble", type=Path)
    parser.add_argument("ridge", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    convert(args.ensemble, args.ridge, args.output)
