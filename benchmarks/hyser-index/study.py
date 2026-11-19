"""Frozen repeated-trial and person-held-out scoring."""

from __future__ import annotations

from itertools import product

import numpy as np

from hyser_index import (
    ALPHAS, ARMS, CONTROLS, FITTED_ARMS, TICKS, WITHIN_DAY_ALPHA,
    Ridge, fit, merge_moments, moments, pair_rows, stack_rows,
)


def trial_rows(trials, subset, arm):
    """Cycle phase-control donors only among the specified trials."""
    donors = [*subset[1:], subset[0]]
    return stack_rows([pair_rows(trials[trial], trials[donor], arm) for trial, donor in zip(subset, donors)])


def person_days(dataset):
    subset = list(range(5))
    return {
        arm: {
            person: [trial_rows(trials, subset, arm) for trials in days]
            for person, days in dataset.items()
        }
        for arm in ARMS
    }


def model_prediction(arm, rows, model):
    if arm == "persistence":
        return rows.current
    if arm == "slope":
        return rows.slope
    return model.predict(rows)


def metrics(arm, rows, model: Ridge | None):
    diff = model_prediction(arm, rows, model) - rows.truth
    return np.array([np.abs(diff).mean(), np.sqrt((diff**2).mean())])


def choose_model(days, part_moments, train):
    """Select each arm on people strictly inside the supplied TRAIN fold."""
    macro_error = np.zeros(len(ALPHAS))
    for held_person in train:
        train_moment = merge_moments([part_moments[p] for p in train if p != held_person])
        held_rows = stack_rows(days[held_person])
        for index, alpha in enumerate(ALPHAS):
            model = fit(train_moment, alpha)
            error = np.abs(model.predict(held_rows) - held_rows.truth)
            macro_error[index] += error.mean() / len(train)
    candidates = zip(macro_error, ALPHAS)
    _, alpha = min(candidates, key=lambda pair: (pair[0], -pair[1]))
    return fit(merge_moments([part_moments[p] for p in train]), alpha)


def nested_train(dataset):
    """Run primary TRAIN nested LOPO, then refit using only the same TRAIN persons."""
    rows = person_days(dataset)
    people = list(dataset)
    scores = np.empty((len(people), 2, len(ARMS), 2))
    refit = {}
    for arm_index, arm in enumerate(ARMS):
        arm_rows = rows[arm]
        if arm in FITTED_ARMS:
            summary = {p: moments(stack_rows(arm_rows[p])) for p in people}
            fold_models = {
                held: choose_model(arm_rows, summary, [p for p in people if p != held])
                for held in people
            }
            refit[arm] = choose_model(arm_rows, summary, people)
        else:
            fold_models = dict.fromkeys(people)
        for index, held in enumerate(people):
            for day, held_rows in enumerate(arm_rows[held]):
                scores[index, day, arm_index] = metrics(arm, held_rows, fold_models[held])
    return scores, refit


def fixed_test(dataset, models):
    rows = person_days(dataset)
    scores = np.empty((len(dataset), 2, len(ARMS), 2))
    for arm_index, arm in enumerate(ARMS):
        for index, person in enumerate(dataset):
            for day, held_rows in enumerate(rows[arm][person]):
                scores[index, day, arm_index] = metrics(arm, held_rows, models.get(arm))
    return scores


def same_person_day(dataset):
    """Fit each held pair on the other three same-day trials, score once per target trial."""
    scores = np.empty((len(dataset), 2, len(ARMS), 2))
    for index, days in enumerate(dataset.values()):
        for day, trials in enumerate(days):
            for arm_index, arm in enumerate(ARMS):
                errors = []
                for held_trial in range(5):
                    held_donor = (held_trial + 1) % 5
                    subset = [k for k in range(5) if k not in (held_trial, held_donor)]
                    model = None
                    if arm in FITTED_ARMS:
                        model = fit(moments(trial_rows(trials, subset, arm)), WITHIN_DAY_ALPHA)
                    rows = pair_rows(trials[held_trial], trials[held_donor], arm)
                    errors.append(model_prediction(arm, rows, model) - rows.truth)
                diff = np.concatenate(errors)
                scores[index, day, arm_index] = [np.abs(diff).mean(), np.sqrt((diff**2).mean())]
    return scores


def summarize_pair(delta, samples):
    count = len(delta)
    sensitivity = (delta.sum() - delta) / (count - 1)
    percentile = np.quantile(delta[samples].mean(axis=1), [0.025, 0.975], method="linear")
    return {
        "mean_gain_v": float(delta.mean()),
        "observed_person_resampling_95_percentile_v": percentile.tolist(),
        "leave_one_person_out_mean_range_v": [float(sensitivity.min()), float(sensitivity.max())],
        "persons_with_positive_gain": int((delta > 0).sum()),
        "persons_with_zero_gain": int((delta == 0).sum()),
    }


def aggregate(scores):
    if not np.isfinite(scores).all():
        raise ValueError("Nonfinite study metric")
    count = len(scores)
    if count <= 4:
        samples = np.array(list(product(range(count), repeat=count)))
    else:
        samples = np.random.default_rng(196233).integers(0, count, (10000, count))
    both_days = scores.mean(axis=1)
    results = {}
    for label, group, day_count in (("both_days", both_days, 2), ("day1", scores[:, 0], 1), ("day2", scores[:, 1], 1)):
        arm_scores = {}
        comparison_scores = {}
        for index, arm in enumerate(ARMS):
            arm_scores[arm] = {
                "macro_mae_v": float(group[:, index, 0].mean()),
                "macro_rmse_v": float(group[:, index, 1].mean()),
            }
        aligned = group[:, ARMS.index("aligned")]
        for control in CONTROLS:
            delta = group[:, ARMS.index(control)] - aligned
            comparison_scores[control] = {
                "mae": summarize_pair(delta[:, 0], samples),
                "rmse": summarize_pair(delta[:, 1], samples),
            }
        results[label] = {
            "people": count,
            "trials_expected": count * day_count * 5,
            "trials_scored": count * day_count * 5,
            "identical_rows_per_arm": count * day_count * 5 * len(TICKS),
            "arms": arm_scores,
            "paired_aligned_vs": comparison_scores,
        }
    return results
