"""Recover the original positive-sort-only archive from reconstructed September 7 arrays."""
import argparse
import hashlib
from pathlib import Path

import numpy as np


def export(whole, output):
    fields = ("block", "original", "ordinal", "k", "workspace", "fold", "donor",
              "pose", "movement", "spikes", "concurrent", "delayed", "cue", "unit_guide",
              "sorted_columns", "roster_original", "roster_block", "roster_start",
              "roster_end", "roster_fold", "history_rows", "movement_rows", "delayed_rows")
    with np.load(whole, allow_pickle=False) as rows:
        data = {k: np.ascontiguousarray(rows[k]) for k in fields}
    for key in ("spikes", "concurrent", "delayed"):
        data[key] = data[key].astype("<i8")
    with output.open("xb") as stream:
        np.savez_compressed(stream, **data)
    if hashlib.sha256(output.read_bytes()).hexdigest() != "40bb17cd64e61bfb4ef52b5ee943d27d50e1c82bbf487d58c623c4ed2d6666ab":
        raise ValueError("The reconstructed archive differs from the original September 7 training input")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("input", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    export(args.input, args.output)
