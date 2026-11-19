"""Convert a compatible local CEMHSEY trial into a private browser packet."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import loadmat

import population as pop
from baseline import pinch as prior

ARRAY_PACKET = "cemhsey-array-trial-v1"
READER_FIT = "cemhsey-array-reader-fit-v1"
MAX_MAT_BYTES = 250 * 1024 * 1024
EMG_SHAPE = (prior.CHANNELS, 61500)
READER_MODELS = ("history_phase", pop.AMPLITUDE, pop.GRID, pop.GRID_RANK)


def require_new_output(path):
    if path.exists() or path.is_symlink():
        raise FileExistsError("Choose a new private output path")
    if not path.parent.is_dir():
        raise ValueError("The output directory must already exist")


def read_mat(path, expected_sha256=None, expected_bytes=None):
    """Read only the two qualified variables, accepting one file at a time."""
    if path.suffix.lower() != ".mat" or path.is_symlink():
        raise ValueError("Choose a regular local .mat file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                         | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_MAT_BYTES:
            raise ValueError("MATLAB file is absent, non-regular or too large")
        if expected_bytes is not None and before.st_size != expected_bytes:
            raise ValueError("MATLAB size differs from the exact role manifest")
        if expected_sha256 is not None:
            if before.st_uid != os.getuid() or before.st_mode & 0o077:
                raise ValueError("Staged MATLAB arrays must be owner-private")
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected_sha256:
                raise ValueError("Trial body differs from the approved SHA-256")
            stream.seek(0)
        arrays = loadmat(stream, variable_names=["data_force", "data_sEMG"],
                         squeeze_me=False, verify_compressed_data_integrity=True)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("MATLAB file changed during read")
    force = arrays.get("data_force")
    emg = arrays.get("data_sEMG")
    if (not isinstance(force, np.ndarray) or force.ndim != 2 or force.shape[0] != 1
            or force.dtype != np.float64 or force.shape[1] < prior.FORCE_TICKS
            or not isinstance(emg, np.ndarray) or emg.dtype != np.float64
            or emg.shape != EMG_SHAPE):
        raise ValueError("Expected the qualified double data_force row and data_sEMG matrix")
    return force[0], emg


def write_private_json(path, value):
    """Create a mode-0600 JSON atomically, with no replacement on collision."""
    require_new_output(path)
    text = json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n"
    descriptor, filename = tempfile.mkstemp(dir=path.parent, prefix=".cemhsey-array-")
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink()


def encode_f64le(array):
    return base64.b64encode(np.asarray(array, dtype="<f8", order="C").tobytes()).decode("ascii")


def array_packet(force, emg):
    prior.check_force(force, prior.FORCE_TICKS)
    force = force[:prior.FORCE_TICKS]
    if not np.isfinite(force).all():
        raise ValueError("Browser packet requires finite normalized force through index 5999")
    rms, older, recent = pop.window_rms(emg, prior.ISSUE_TICKS)
    if (rms.shape != (594, 320) or not np.array_equal(older, np.arange(592))
            or not np.array_equal(recent, np.arange(2, 594))):
        raise ValueError("Unexpected distinct-window layout")
    return {
        "format": ARRAY_PACKET,
        "protocol_sha256": prior.sha256(pop.PROTOCOL),
        "timing_mode": pop.TIMING_MODE,
        "force_base64": encode_f64le(force),
        "channel_rms_base64": encode_f64le(rms),
    }


def reader_fit(fit, origin):
    """Project only offline predictor weights and their explicit provenance tag."""
    pop.validate_fit(fit)
    has_local_stage = fit.get("custody") == "root_granted_measured_train"
    if ((origin == "measured_train_local" and not has_local_stage)
            or (origin == "invented_signals" and has_local_stage)
            or origin not in ("invented_signals", "measured_train_local")):
        raise ValueError("Reader origin and qualified fit envelope disagree")
    return {
        "format": READER_FIT,
        **pop.source_hashes(),
        "timing_mode": pop.TIMING_MODE,
        "fit_origin": origin,
        "models": {name: fit["models"][name] for name in READER_MODELS},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="A compatible original .mat trial")
    parser.add_argument("--output", required=True, type=Path, help="New local private JSON")
    args = parser.parse_args()
    require_new_output(args.output)
    force, emg = read_mat(args.input)
    write_private_json(args.output, array_packet(force, emg))


if __name__ == "__main__":
    main()
