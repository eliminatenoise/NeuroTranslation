"""Frozen person-balanced scoring and paired four-person descriptive uncertainty."""
from itertools import product
import numpy as np
from extract import TASKS
from portable import METHODS, BASELINES, predict


def predictions(model, trial):
    result = {method: predict(model, trial.x, method) for method in METHODS if method != 'wrong'}
    result['wrong'] = predict(model, trial.wrong_tokens(), 'full')
    return result


def person_scores(trials, outputs):
    if len(trials) != 2 or len(outputs) != 2:
        raise ValueError('Two prespecified recordings per person are required')
    task = np.concatenate([trial.code for trial in trials])
    target = np.concatenate([trial.y for trial in trials])
    counts = {str(t): int(np.sum(task == t)) for t in TASKS}
    if min(counts.values()) == 0:
        raise ValueError('Both basic tasks required for scoring')
    res = {}
    for method in METHODS:
        pred = np.concatenate([result[method] for result in outputs])
        if pred.shape != target.shape or not np.isfinite(pred).all():
            raise ValueError('Invalid or unpaired predictions')
        error = np.abs(pred - target)
        scores = {str(t): float(error[task == t].mean()) for t in TASKS}
        scores['balanced'] = sum(scores.values()) / 2
        res[method] = scores
    exclusions = {str(t): {reason: sum(trial.excluded[str(t)][reason] for trial in trials)
                  for reason in ('invalid_history', 'invalid_target')} for t in TASKS}
    paired = {m: res[m]['balanced'] - res['full']['balanced'] for m in METHODS if m != 'full'}
    return {'n': counts, 'excluded': exclusions, 'mae_deg': res, 'comparator_minus_full_balanced_deg': paired}


def summarize(people):
    if len(people) != 4:
        raise ValueError('This prespecified analysis requires exactly four people per stage')
    rows = list(people.values())
    matrix = {method: {key: np.array([p['mae_deg'][method][key] for p in rows])
              for key in ('611', '621', 'balanced')} for method in METHODS}
    mean = {m: {k: float(v.mean()) for k, v in values.items()} for m, values in matrix.items()}
    resamples = np.array(list(product(range(4), repeat=4)))
    paired = {}
    for m in METHODS:
        if m == 'full':
            continue
        d = matrix[m]['balanced'] - matrix['full']['balanced']
        paired[m] = {'mean_reduction_deg': float(d.mean()), 'people_improved': int(np.sum(d > 0)),
                     'descriptive_person_bootstrap_95_deg': np.percentile(d[resamples].mean(axis=1), [2.5, 97.5]).tolist()}
    best = min(BASELINES + ('motion',), key=lambda m: mean[m]['balanced'])
    both = np.logical_and(matrix['full']['balanced'] < matrix['motion']['balanced'],
                          matrix['full']['balanced'] < matrix['wrong']['balanced'])
    def margin(m, fraction):
        return mean[m]['balanced'] > 0 and mean['full']['balanced'] <= (1 - fraction) * mean[m]['balanced']
    checks = {'five_percent_below_best_motion_or_simple': margin(best, .05),
              'two_percent_below_wrong': margin('wrong', .02),
              'beats_motion_and_wrong_in_three_people': int(both.sum()) >= 3,
              'standing_no_worse_than_motion_and_wrong': all(mean['full']['611'] <= mean[m]['611'] for m in ('motion', 'wrong')),
              'movement_no_worse_than_motion_and_wrong': all(mean['full']['621'] <= mean[m]['621'] for m in ('motion', 'wrong'))}
    passed = all(checks.values())
    regional = {}
    for site, without in [('upper', 'lower'), ('lower', 'upper')]:
        regional[site] = {'meets_two_percent': margin(without, .02),
                          'people_improved': paired[without]['people_improved'],
                          'passes': passed and margin(without, .02) and paired[without]['people_improved'] >= 3}
    return {'n_people': 4, 'n_trials': 8, 'n': {str(t): sum(p['n'][str(t)] for p in rows) for t in TASKS},
            'excluded': {str(t): {reason: sum(p['excluded'][str(t)][reason] for p in rows)
             for reason in ('invalid_history', 'invalid_target')} for t in TASKS}, 'mae_deg': mean,
            'comparator_minus_full': paired, 'best_non_voltage': best, 'people_beating_motion_and_wrong': int(both.sum()),
            'incremental_checks': checks, 'incremental_gate_passes': passed, 'regional_gates': regional}
