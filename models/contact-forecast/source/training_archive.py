"""Write the exact first-day training archive expected by the frozen fitting program."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import numpy as np


def canonical_training(source, destination):
    contract = json.loads(Path(__file__).with_name("identities.json").read_bytes())
    with np.load(source, allow_pickle=False) as data:
        fields = {}
        for name, spec in contract["training_fields"].items():
            value = data[name]
            if (value.dtype.str != spec["dtype"] or list(value.shape) != spec["shape"] or
                    hashlib.sha256(value.tobytes(order="C")).hexdigest() != spec["sha256_C_order"]):
                raise ValueError(f"Training field failed its published identity: {name}")
            fields[name] = value
    destination.parent.mkdir(exist_ok=True, parents=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".npz", delete=False) as output:
        temporary = Path(output.name)
        try:
            np.savez_compressed(output, **fields)
            output.flush()
            with temporary.open("rb") as f:
                filehash = hashlib.file_digest(f, "sha256").hexdigest()
            if filehash != contract["accepted_training_archive_sha256"]:
                raise ValueError("Field identities match but ZIP bytes differ from the fitting program's archive. "
                                 "Use the reference NumPy and zlib versions in the source README.")
        except BaseException:
            output.close()
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(destination)
    return filehash


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(canonical_training(args.source, args.destination))
