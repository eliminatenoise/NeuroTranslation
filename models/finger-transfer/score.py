# SPDX-License-Identifier: CC0-1.0
"""Reduce cutoffs to whole-trial, whole-person evidence before person resampling."""
from itertools import product

import numpy as np

CONTRASTS = ('cue', 'table', 'earlier', 'cortex')
REPEAT = ('zero', 'cue', 'earlier')


def digit_mean(error):
    return error.mean(axis=(0, 1))


def score_person(p, pred):
    target = p.y[p.recipients]
    digit_errors = {k: digit_mean(np.abs(a - target)) for k, a in pred.items()}
    row = {'support': p.support, 'models': {}, 'gains': {}}
    for name, digits in digit_errors.items():
        row['models'][name] = {'scaled_mae': float(digits.mean()), 'scaled_by_digit': digits,
                               'sensor_counts_per_step_by_digit': digits * p.cal['gain']}
    second, first = p.quartets[:, 1], p.quartets[:, 0]
    delta = target[second] - target[first]
    for family in ('ridge', 'transformer'):
        aligned = digit_errors[f'{family}_aligned']
        for mode in CONTRASTS:
            baseline = 'cue_table' if mode == 'table' else f'{family}_{mode}'
            row['gains'][f'{family}.primary.{mode}'] = digit_errors[baseline] - aligned
        aligned_pred = pred[f'{family}_aligned']
        delta_error = digit_mean(np.abs(aligned_pred[second] - aligned_pred[first] - delta))
        for mode in REPEAT:
            if mode == 'zero':
                difference = np.zeros(delta.shape)
            else:
                control = pred[f'{family}_{mode}']
                difference = control[second] - control[first]
            row['gains'][f'{family}.repeat.{mode}'] = digit_mean(np.abs(difference-delta)) - delta_error
    row['gains']['aligned.ridge_minus_transformer'] = (digit_errors['ridge_aligned'] -
                                                       digit_errors['transformer_aligned'])
    return row


def summary(people):
    keys = list(people)
    n = len(keys)
    samples = np.array(list(product(range(n), repeat=n)))
    result = {'people': people, 'person_order': keys, 'contrasts': {}, 'gate': {},
              'cohort_mean_scaled_mae': {}, 'interval': 'descriptive equal-person percentile resampling'}
    for mode in people[keys[0]]['models']:
        result['cohort_mean_scaled_mae'][mode] = float(np.mean(
            [people[key]['models'][mode]['scaled_mae'] for key in keys]))
    for contrast in people[keys[0]]['gains']:
        digits = np.stack([people[key]['gains'][contrast] for key in keys])
        person_means = digits.mean(axis=1)
        draws = digits[samples].mean(axis=1)
        result['contrasts'][contrast] = dict(
            person_means=person_means, mean=float(person_means.mean()),
            mean_by_digit=digits.mean(axis=0), interval=np.percentile(draws.mean(axis=1), [2.5, 97.5]),
            interval_by_digit=np.percentile(draws, [2.5, 97.5], axis=0).T)
    support = all(sum(people[key]['support']['quartets_by_cue']) >= 6 and
                  np.count_nonzero(people[key]['support']['quartets_by_cue']) >= 3 for key in keys)
    for family in ('ridge', 'transformer'):
        contrasts = ([f'{family}.primary.{mode}' for mode in ('cue', 'table', 'earlier')]
                     + [f'{family}.repeat.{mode}' for mode in REPEAT])
        met = {k: bool(np.all(result['contrasts'][k]['person_means'] > 0)
                       and result['contrasts'][k]['interval'][0] > 0) for k in contrasts}
        result['gate'][family] = {'support': support, 'contrasts_met': met,
                                  'eligible_subset_pass': support and all(met.values()),
                                  'five_person_pass': n == 5 and support and all(met.values())}
    return result
