"""Verify the reader package, original-source receipt and resulting private arrays."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from acquire import STAGES


def canonical_json(value):
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def arrays_digest(path):
    # ZIP headers can differ between operating systems. Hash the typed array contents.
    signature = hashlib.sha256()
    with np.load(path, allow_pickle=False) as archive:
        for name in sorted(archive.files):
            array = archive[name]
            dtype = array.dtype.newbyteorder("<")
            signature.update(canonical_json([name, dtype.str, list(array.shape)]))
            signature.update(b"\n")
            signature.update(np.asarray(array, dtype=dtype).tobytes(order="C"))
    return signature.hexdigest()


def observed_stage(work, stage):
    receipt = json.loads((work / f"{stage}-files.json").read_bytes())
    qc = json.loads((work / f"{stage}-qc.json").read_bytes())
    return {
        "canonical_files_receipt_sha256": hashlib.sha256(
            canonical_json(receipt)
        ).hexdigest(),
        "typed_arrays_sha256": arrays_digest(work / f"{stage}.npz"),
        "totals": qc["totals"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    inventory = json.loads((here / "integrity.json").read_bytes())
    for name, expected in inventory["package_sha256_lf"].items():
        if (
            hashlib.sha256(
                (here / name).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            != expected
        ):
            raise ValueError(f"Package differs at {name}")
    if observed_stage(args.work, args.stage) != inventory["stages"][args.stage]:
        raise ValueError(
            f"{args.stage} arrays, original file receipt or QC totals differ"
        )
    print(f"Verified {args.stage} source inventory, arrays and eligibility counts.")


if __name__ == "__main__":
    main()
