# SPDX-License-Identifier: CC0-1.0
"""Development-prefix reader and complete chronological trials."""
from collections import Counter
from dataclasses import dataclass
import hashlib

import numpy as np

from features import TOKEN_LAGS, WINDOW, band_features, cue_basis

SOURCE_HASH = "57ea209841127b6cc04f2c03f8f6146f01b3e0235d169365d009cf3f9c643e9c"
METHOD_HASH = "3831e8a178b1bc70be38df94a218df1209ed1a18cad88aa9cdfbc085c0eb4dca"
FINGERS = ("thumb", "index", "middle", "ring", "little")
FIT_BOUNDS = (0, 236000)
EVAL_BOUNDS = (244000, 362000)
PHASE_TICKS = 34
TRIAL_TICKS = 2 * PHASE_TICKS


def load_prefix(path):
    with path.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != SOURCE_HASH:
            raise ValueError("Expected the verified FingerFlex development prefix")
        f.seek(0)
        with np.load(f, allow_pickle=False) as z:
            return z["ecog"], z["flex"], z["cue"]


def complete_trials(cue):
    changes = np.r_[0, 1 + np.flatnonzero(cue[1:] != cue[:-1])]
    for i in range(1, len(changes)-2):
        onset, blank, end = changes[i:i+3]
        digit = int(cue[onset])
        if digit in range(1, 6) and cue[blank] == 0:
            yield digit, onset, blank, end


def grid(start, stop):
    cut = (start + 39)//40*40 + np.arange(9, 43)*40
    if cut[0] + TOKEN_LAGS[0] - WINDOW + 1 < start or cut[-1] + 160 >= stop:
        return None
    return cut


def target(flex, cut):
    four_readings = flex[cut[:, None] + np.arange(40, 161, 40)].astype(np.float64)
    return np.abs(np.diff(four_readings, axis=1)).mean(axis=1)


def glove_history(flex, cut):
    past = flex[cut[:, None] + TOKEN_LAGS].astype(np.float64)
    return np.concatenate([past.reshape(len(cut), 20), np.abs(np.diff(past, axis=1)).reshape(len(cut), 15)], axis=1)


def main_packets(ecog, digit, phase, start, cut):
    ends = cut[:, None] + TOKEN_LAGS
    unique, inverse = np.unique(ends, return_inverse=True)
    window = ecog[unique[:, None] + np.arange(-159, 1)]
    spectrum = band_features(window)[inverse.reshape(ends.shape)]
    cue = cue_basis(digit, phase, (ends-start)/1000)
    return np.concatenate([cue, spectrum], axis=-1)


def by_finger(counter):
    return {finger: int(counter[i]) for i, finger in enumerate(FINGERS, 1)}


@dataclass
class Partition:
    packets: np.ndarray
    wrong: np.ndarray
    history: np.ndarray
    y: np.ndarray
    digits: list
    support: dict


def partition(source, bounds):
    ecog, flex, cue = source
    donors = {}
    packets, wrong, history, y, digits = [], [], [], [], []
    eligible, first, short = Counter(), Counter(), Counter()
    for digit, onset, blank, end in complete_trials(cue):
        if onset < bounds[0] or end > bounds[1]:
            continue
        display_cut, blank_cut = grid(onset, blank), grid(blank, end)
        if display_cut is None or blank_cut is None:
            short[digit] += 1
            continue
        eligible[digit] += 1
        current = np.concatenate([main_packets(ecog, digit, 0, onset, display_cut),
                                  main_packets(ecog, digit, 1, blank, blank_cut)])
        if digit in donors:
            previous_end, previous_cortex = donors[digit]
            assert previous_end <= onset
            cut = np.concatenate([display_cut, blank_cut])
            packets.append(current)
            wrong.append(np.concatenate([current[..., :60], previous_cortex], axis=-1))
            history.append(glove_history(flex, cut))
            y.append(target(flex, cut))
            digits.append(digit)
        else:
            first[digit] += 1
        donors[digit] = end, current[..., 60:].copy()

    support = dict(eligible_by_cue=by_finger(eligible), excluded_short_by_cue=by_finger(short),
                   donor_only_by_cue=by_finger(first), recipients_by_cue=by_finger(Counter(digits)),
                   trials=len(digits), cutoffs=len(digits)*TRIAL_TICKS, cutoffs_per_trial=TRIAL_TICKS)
    return Partition(np.concatenate(packets), np.concatenate(wrong), np.concatenate(history),
                     np.concatenate(y), digits, support)
