"""Two-coefficient residual calibration on Hyser Day 1, followed by Day 2 scoring."""

from itertools import product

import numpy as np

from calibration import calibrate
from hyser_index import TICKS, moments, stack_rows
from study import choose_model, trial_rows

EXPERIMENT = "hyser-index-crossday-20261119-v1"
ARMS = ("force", "aligned")
METHODS = ("base", "own_day1", "wrong_day1")
RESAMPLE_SEED = 10720261119


def reciprocal_pairs(people):
    if len(people) < 4 or len(set(people)) != len(people) or len(people) % 2:
        raise ValueError("Need a distinct even list of people with at least two pairs")
    return tuple(zip(people[::2], people[1::2]))


def assemble_rows(day, people):
    if set(day) != set(people) or any(len(day[p]) != 5 for p in people):
        raise ValueError("Incomplete or mismatched day support")
    rows = {arm: {p: trial_rows(day[p], list(range(5)), arm) for p in people} for arm in ARMS}
    if any(len(rows[arm][p].truth) != 5 * len(TICKS) for arm in ARMS for p in people):
        raise ValueError("A day does not contain the full frozen row support")
    return rows


def train_pair_bases(day1, day2, people):
    """Fit on the complement of each reciprocal pair, including in inner selection."""
    result = {}
    for arm in ARMS:
        days = {person: [day1[arm][person], day2[arm][person]] for person in people}
        summaries = {person: moments(stack_rows(days[person])) for person in people}
        for pair in reciprocal_pairs(people):
            others = [person for person in people if person not in pair]
            result[arm, pair] = choose_model(days, summaries, others)
    return result


def frozen_pair_bases(models, people):
    return {(arm, pair): models[arm] for arm in ARMS for pair in reciprocal_pairs(people)}


def fit_day1(day1, people, bases):
    adapters = {}
    for arm in ARMS:
        for pair in reciprocal_pairs(people):
            model = bases[arm, pair]
            for person in pair:
                rows = day1[arm][person]
                adapters[arm, person] = calibrate(rows.current, model.predict(rows), rows.truth)
    return adapters


def score_day2(day2, people, bases, adapters):
    scores = np.empty((len(people) // 2, 2, len(ARMS), len(METHODS), 2))
    for arm_index, arm in enumerate(ARMS):
        for pair_index, pair in enumerate(reciprocal_pairs(people)):
            model = bases[arm, pair]
            for member, person in enumerate(pair):
                rows = day2[arm][person]
                base = model.predict(rows)
                own = adapters[arm, person].predict(rows.current, base)
                wrong = adapters[arm, pair[1 - member]].predict(rows.current, base)
                error = np.array([base, own, wrong]) - rows.truth
                scores[pair_index, member, arm_index, :, 0] = np.mean(np.abs(error), axis=1)
                scores[pair_index, member, arm_index, :, 1] = np.sqrt(np.mean(error * error, axis=1))
    return scores


def summary(scores):
    """Export only aggregates. Each resampling unit is a reciprocal donor pair."""
    if (scores.ndim != 5 or scores.shape[1:] != (2, len(ARMS), len(METHODS), 2)
            or len(scores) < 2 or not np.isfinite(scores).all()):
        raise ValueError("Unexpected or nonfinite paired score shape")
    pair_count = len(scores)
    if pair_count == 2:
        samples = np.asarray(list(product(range(pair_count), repeat=pair_count)))
    else:
        samples = np.random.default_rng(RESAMPLE_SEED).integers(0, pair_count, (10000, pair_count))

    def differences(delta):
        pair_means = delta.mean(axis=1)
        delete_pair = (pair_means.sum() - pair_means) / (pair_count - 1)
        return {
            "mean_gain_v": float(pair_means.mean()),
            "observed_pair_resampling_95_percentile_v":
                np.quantile(pair_means[samples].mean(axis=1), [0.025, 0.975], method="linear").tolist(),
            "leave_one_pair_out_mean_range_v": [float(delete_pair.min()), float(delete_pair.max())],
            "persons_with_positive_gain": int((delta > 0).sum()),
            "persons_with_zero_gain": int((delta == 0).sum()),
        }

    def metrics(delta):
        return {"mae": differences(delta[:, :, 0]), "rmse": differences(delta[:, :, 1])}

    macro = scores.mean(axis=(0, 1))
    n_people = 2 * pair_count
    trials = 5 * n_people
    windows = trials * len(TICKS)
    comparisons = {
        arm: {"own_vs_base": metrics(scores[:, :, i, 0] - scores[:, :, i, 1]),
              "own_vs_wrong": metrics(scores[:, :, i, 2] - scores[:, :, i, 1])}
        for i, arm in enumerate(ARMS)
    }
    comparisons["aligned_own_vs_force_own"] = metrics(scores[:, :, 0, 1] - scores[:, :, 1, 1])
    return {
        "counts": {
            "people": n_people, "pairs": pair_count,
            "day1_calibration_trials": trials, "day1_calibration_windows": windows,
            "day2_scored_trials": trials, "day2_scored_windows": windows,
        },
        "arms": {arm: {method: {"macro_mae_v": float(macro[i, j, 0]), "macro_rmse_v": float(macro[i, j, 1])}
                       for j, method in enumerate(METHODS)} for i, arm in enumerate(ARMS)},
        "comparisons": comparisons,
    }
