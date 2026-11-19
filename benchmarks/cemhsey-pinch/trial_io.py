"""Convert one local CEMHSEY MATLAB recording to a private offline trial packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from pinch import TIMING_MODES, extract_trial, packet_from_features

MAX_MAT_BYTES = 250 * 1024 * 1024


def read_mat(path, timing_mode, expected_digest=None):
    if timing_mode not in TIMING_MODES:
        raise ValueError("Unknown timing mode")
    if path.suffix.lower() != ".mat":
        raise ValueError("Choose a local MATLAB .mat file")
    variables = ["data_force"]
    if timing_mode == "nominal_release_index":
        variables.append("data_sEMG")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_MAT_BYTES:
            raise ValueError("Need a bounded regular MATLAB file")
        if expected_digest is not None:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected_digest:
                raise ValueError("Trial body does not match the approved manifest")
            stream.seek(0)
        arrays = loadmat(stream, variable_names=variables, squeeze_me=False,
                         verify_compressed_data_integrity=True)
        after = os.fstat(stream.fileno())
        if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                before.st_size, before.st_mtime_ns, before.st_ctime_ns):
            raise ValueError("MATLAB file changed during read")
    force = arrays.get("data_force")
    if (not isinstance(force, np.ndarray) or force.ndim != 2 or force.shape[0] != 1
            or force.dtype != np.float64):
        raise ValueError("MATLAB data_force must be a float64 row")
    emg = arrays.get("data_sEMG")
    if timing_mode == "nominal_release_index" and not isinstance(emg, np.ndarray):
        raise ValueError("MATLAB data_sEMG matrix is absent")
    return force[0, :], emg


def write_private_json(path, value):
    if path.exists() or path.is_symlink():
        raise FileExistsError("Choose a new private output path")
    text = json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n"
    descriptor, filename = tempfile.mkstemp(dir=path.parent, prefix=".pinch-")
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timing-mode", choices=TIMING_MODES, default="force_only")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("Choose a new output file in an existing private directory")
    force, emg = read_mat(args.input, args.timing_mode)
    result = packet_from_features(extract_trial(force, emg), args.timing_mode)
    write_private_json(args.output, result)


if __name__ == "__main__":
    main()
