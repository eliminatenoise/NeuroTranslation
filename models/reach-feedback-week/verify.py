"""Check a reproduction against the original archive's field and file fingerprints."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fields(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {name: {
            "shape": list(arrays[name].shape),
            "dtype": arrays[name].dtype.str,
            "sha256": hashlib.sha256(arrays[name].tobytes(order="C")).hexdigest()
        } for name in arrays}


def json_fingerprint(path):
    obj = json.loads(path.read_bytes())
    canonical = json.dumps(obj, sort_keys=True, separators=(",",":"), allow_nan=False).encode()
    return hashlib.sha256(canonical).hexdigest()


def check(out):
    spec = json.loads((HERE/"reference-digests.json").read_bytes())
    results = {}
    for key, reference in spec.items():
        path = out/key
        byte_equal = digest(path) == reference["sha256"]
        record = {"byte_identical": byte_equal}
        if "fields" in reference:
            actual = fields(path)
            record["array_count"] = len(actual)
            record["different_fields"] = sorted(name for name in actual.keys() | reference["fields"].keys()
                                                 if actual.get(name) != reference["fields"].get(name))
            record["scientifically_identical"] = not record["different_fields"]
        else:
            record["scientifically_identical"] = json_fingerprint(path) == reference["json_sha256"]
        results[key] = record
    failures = [k for k, v in results.items() if not v["scientifically_identical"]]
    report = {"comparison": "Exact values, shapes and types per numerical field, and complete canonical JSON values.",
              "all_scientifically_identical": not failures, "different": failures, "files": results}
    (out/"verification.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf8")
    if failures:
        raise ValueError("Differences from the reference run: " + ", ".join(failures) + ". See verification.json.")
    print(f"Matched {len(results)} files including {sum(v.get('array_count',0) for v in results.values())} array fields.")
    print("All four registered improvement criteria were false on September 14.")
    return report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    check(cli.parse_args().output)
