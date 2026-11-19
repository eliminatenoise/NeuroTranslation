"""Fit the offline grid reader from twelve compatible, user-selected original MATLAB trials."""

from __future__ import annotations

import argparse
import os
import re
import stat
from itertools import product
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import population as pop
import trial_packet as packet
from baseline import pinch as prior

TRIAL_NAME = re.compile(r"S([1-9][0-9]*)_Day([1-9][0-9]*)_Session5_Task2_Trial([12])\.mat")


def inventory(paths):
    trials = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError("Choose regular original MATLAB files")
        original = path.resolve(strict=True)
        match = TRIAL_NAME.fullmatch(original.name)
        metadata = original.stat()
        if (match is None or not stat.S_ISREG(metadata.st_mode)
                or not 0 < metadata.st_size <= packet.MAX_MAT_BYTES):
            raise ValueError("Choose compatible original Session5_Task2 MATLAB files")
        key = tuple(map(int, match.groups()))
        if key in trials:
            raise ValueError("Each person, day and repeat must occur exactly once")
        trials[key] = original
    people = {key[0] for key in trials}
    if len(people) != pop.TRAIN_PEOPLE or set(trials) != set(product(people, pop.TRAIN_DAYS, (1, 2))):
        raise ValueError("Choose both repeats on days 1 and 2 for exactly three people")
    return trials


def fit_owner_trials(paths):
    originals = inventory(paths)
    hashes = set()
    trials = {}
    for key, original in sorted(originals.items()):
        digest = prior.sha256(original)
        if digest in hashes:
            raise ValueError("The same original MATLAB bytes occur under two trial names")
        force, emg = packet.read_mat(original)
        if prior.sha256(original) != digest:
            raise ValueError("A source changed during the local fit")
        hashes.add(digest)
        trials[key] = pop.extract_trial(force, emg)
        del force, emg
    fitted = pop.fit_panel(trials)
    return {
        "format": packet.READER_FIT,
        **pop.source_hashes(),
        "timing_mode": pop.TIMING_MODE,
        "fit_origin": "user_supplied_local",
        "models": {name: fitted["models"][name] for name in packet.READER_MODELS},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--trial-list", type=Path,
                        help="UTF-8 text with one original .mat path per line")
    source.add_argument("--trial", action="append", type=Path,
                        help="Original .mat path. Repeat for each trial.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    packet.require_new_output(args.output)
    paths = args.trial
    if args.trial_list is not None:
        paths = [
            args.trial_list.parent / name.strip()
            for name in args.trial_list.read_text(encoding="utf-8").splitlines()
            if name.strip()
        ]
    packet.write_private_json(args.output, fit_owner_trials(paths))


if __name__ == "__main__":
    main()
