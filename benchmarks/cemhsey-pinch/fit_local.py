"""Fit a local offline pinch predictor from the owner's selected original MATLAB files."""

from __future__ import annotations

import argparse
import os
import re
import stat
from itertools import product
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from pinch import TIMING_MODES, extract_trial, fit_panel, sha256, validate_fit
from trial_io import MAX_MAT_BYTES, read_mat, write_private_json

TRIAL_NAME = re.compile(r"S([1-9][0-9]*)_Day([1-9][0-9]*)_Session5_Task2_Trial([12])\.mat")


def inventory(paths):
    trials = {}
    for path in paths:
        original = path.resolve(strict=True)
        match = TRIAL_NAME.fullmatch(original.name)
        if match is None:
            raise ValueError("Choose original Session5_Task2 MATLAB trial names")
        source = original.stat()
        if not stat.S_ISREG(source.st_mode) or not 0 < source.st_size <= MAX_MAT_BYTES:
            raise ValueError("Choose bounded regular MATLAB files")
        key = tuple(map(int, match.groups()))
        if key in trials:
            raise ValueError("Each person, day and repeat must occur exactly once")
        trials[key] = original
    people = sorted({key[0] for key in trials})
    days = sorted({key[1] for key in trials})
    if not people or set(trials) != set(product(people, days, (1, 2))):
        raise ValueError("Choose both repeats for each person on the same selected days")
    return trials


def project_local_fit(fit):
    validate_fit(fit, full=True)
    return {
        "format": fit["format"],
        "protocol_sha256": fit["protocol_sha256"],
        "timing_mode": fit["timing_mode"],
        "models": {name: model for name, model in fit["models"].items()
                   if name != "history_phase_other_emg"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--trial-list", type=Path,
                        help="UTF-8 text with one original .mat path per line")
    source.add_argument("--trial", action="append", type=Path,
                        help="Original .mat path. Repeat for each trial.")
    parser.add_argument("--timing-mode", choices=TIMING_MODES, default="force_only")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("Choose a new fit file in an existing private output directory")
    paths = args.trial
    if args.trial_list is not None:
        names = args.trial_list.read_text(encoding="utf-8").splitlines()
        paths = [args.trial_list.parent / name.strip() for name in names if name.strip()]

    trials = inventory(paths)
    hashes = set()
    inputs = {}
    for key, original in sorted(trials.items()):
        digest = sha256(original)
        if digest in hashes:
            raise ValueError("The same original MATLAB bytes occur under two trial names")
        hashes.add(digest)
        force, emg = read_mat(original, args.timing_mode, expected_digest=digest)
        inputs[key] = extract_trial(force, emg)
        del force, emg
    fit = project_local_fit(fit_panel(inputs, args.timing_mode))
    write_private_json(args.output, fit)


if __name__ == "__main__":
    main()
