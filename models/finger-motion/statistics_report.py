# SPDX-License-Identifier: CC0-1.0
"""Paired estimates. Exports contain only aggregate data."""
from collections import Counter
import numpy as np

from recording import FINGERS, METHOD_HASH, PHASE_TICKS, TRIAL_TICKS, SOURCE_HASH, by_finger


def draws(n):
    starts = np.random.default_rng(48019).integers(0, n, (5000, (n+2)//3))
    return ((starts[..., None] + np.arange(3)) % n).reshape(5000, -1)[:, :n]


def value(a, sd):
    avg = a.mean(axis=(0, 1))
    phase = a.reshape(-1, 2, PHASE_TICKS, 5).mean(axis=(0, 2))
    return dict(per_finger_mae=avg, macro_normalized_mae=(avg/sd).mean(),
                phase_macro_normalized_mae=(phase/sd).mean(axis=1))


def difference(errors, baseline, candidate, sd, idx):
    # Compute equal-weight means for each trial (or each disjoint pair) first.
    d = (errors[baseline] - errors[candidate]).mean(axis=1)
    boot = d[idx].mean(axis=1)
    return dict(baseline=baseline, candidate=candidate, per_finger_gain=d.mean(axis=0),
                per_finger_interval=np.quantile(boot, [0.025, 0.975], axis=0).T,
                macro_normalized_gain=(d/sd).mean(),
                macro_interval=np.quantile((boot/sd).mean(axis=1), [0.025, 0.975]))


def matched_pairs(digits):
    # Appending on the second occurrence sorts by the later member of the pair.
    pending, pairs, support = {}, [], Counter()
    for index, digit in enumerate(digits):
        if digit in pending:
            pairs.append((pending.pop(digit), index))
            support[digit] += 1
        else:
            pending[digit] = index
    return np.asarray(pairs, dtype=int), support, Counter(pending.keys())


def report(train, dev, pred):
    sd = train.y.std(axis=0)
    y = dev.y.reshape(-1, TRIAL_TICKS, 5)
    p = {key: v.reshape(y.shape) for key, v in pred.items()}
    errors = {k: np.abs(v-y) for k, v in p.items()}
    pairs, support, omitted = matched_pairs(dev.digits)
    a, b = pairs.T
    dy = y[b] - y[a]
    pair_errors = {k: np.abs(v[b] - v[a] - dy) for k, v in p.items()}
    pair_errors["zero_difference"] = np.abs(dy)
    idx_trial, idx_pair = draws(len(y)), draws(len(pairs))
    primary, conditional, gates = [], [], {}
    adequate_support = len(pairs) >= 6 and len(support) >= 3
    for family in ("ridge", "transformer"):
        aligned = family + "_aligned"
        cue, wrong, cortex = (family + "_" + name for name in ("cue", "earlier", "cortex"))
        main = [difference(errors, baseline, aligned, sd, idx_trial) for baseline in (cue, wrong)]
        checks = [difference(pair_errors, baseline, aligned, sd, idx_pair)
                  for baseline in ("zero_difference", cue, wrong)]
        primary.extend(main + [difference(errors, cortex, aligned, sd, idx_trial)])
        conditional.extend(checks)
        gates[family] = bool(adequate_support and all(x["macro_interval"][0] > 0 for x in main+checks))
    primary.append(difference(errors, "ridge_aligned", "transformer_aligned", sd, idx_trial))
    return dict(method_sha256=METHOD_HASH, development_prefix_sha256=SOURCE_HASH,
                scope="Chronological internal development comparison on one participant, one recording.",
                fingers=FINGERS, units="stored glove sensor counts per nominal 40-ms step",
                normalization="target standard deviation within training recipients, per finger",
                phases=["display", "following blank"], person_count=1,
                train=train.support, evaluation=dev.support, train_target_sd=sd,
                conditional_support=dict(pairs=len(pairs), pairs_by_cue=by_finger(support),
                                         odd_repeats_excluded_by_cue=by_finger(omitted),
                                         min_support_met=adequate_support),
                scores={k: value(v, sd) for k, v in errors.items()},
                conditional_difference_scores={k: value(v, sd) for k, v in pair_errors.items()},
                primary_contrasts=primary, conditional_contrasts=conditional,
                gated_within_cue_advantage=gates)
