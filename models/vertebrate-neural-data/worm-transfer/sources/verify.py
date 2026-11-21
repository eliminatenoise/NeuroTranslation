"""Check the extracted traces against a stored manifest without printing observations."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(base, role):
    manifest = json.loads((base / f"{role}-manifest.json").read_text())
    for entry in manifest["records"]:
        file = base / manifest["private_directory"] / entry["filename"]
        assert sha(file.read_bytes()) == entry["sha256"]
        with np.load(file, allow_pickle=False) as data:
            assert set(data.files) == {"fluorescence", "roi_index", "time_s"}
            times, rois, traces = data["time_s"], data["roi_index"], data["fluorescence"]
            assert traces.shape == (times.size, rois.size) == tuple(entry["shape"])
            assert times[0] == 0 and (np.diff(times) > 0).all() and float(times[-1]) < 180
            assert np.array_equal(rois, np.arange(traces.shape[1]))
            assert traces.dtype.str == times.dtype.str == "<f8" and rois.dtype.str == "<i8"
            assert np.count_nonzero(~np.isfinite(traces)) == entry["nonfinite_elements"]
            for key, digest in entry["fields_sha256_c_order_le"].items():
                assert sha(data[key].tobytes(order="C")) == digest
    return len(manifest["records"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["train", "held"])
    args = parser.parse_args()
    n = verify(Path(__file__).resolve().parent, args.role)
    print(f"Verified {n} files and all three arrays per file.")
