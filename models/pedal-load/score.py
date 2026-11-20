"""Participant- and condition-balanced paired forecast error in recorded channel units."""
import numpy as np
from portable import METHODS, BASELINES


def scoring(data, predictions):
    people = np.unique(data['person'])
    if len(people) != 2:
        raise ValueError('Each stage requires exactly two nominated people')
    cells, trials, person_scores = {}, {}, {}
    for p in people:
        cells[p], trials[p] = {}, {}
        for c in (0, 5):
            take = (data['person'] == p) & (data['condition'] == c)
            def scores(sel):
                if not sel.any():
                    raise ValueError('Empty trial or cell')
                return {k: float(np.mean(np.abs(data['y'][sel]-predictions[k][sel]))) for k in METHODS}
            cells[p][str(c)] = scores(take)
            trials[p][str(c)] = {str(t): {'n': int(np.sum(take & (data['trial']==t))),
                                           'mae': scores(take & (data['trial']==t))} for t in (1, 2)}
        person_scores[p] = {k: float(np.mean([v[k] for v in cells[p].values()])) for k in METHODS}
    condition_scores = {c: {k: float(np.mean([cells[p][c][k] for p in people])) for k in METHODS}
                        for c in ('0', '5')}
    balanced = {k: float(np.mean([s[k] for s in person_scores.values()])) for k in METHODS}
    best = min(BASELINES + ['load', 'load_condition'], key=balanced.get)
    controls = ('load_condition', 'wrong')
    def diffs(cell):
        return {k: cell[k] - cell['full'] for k in METHODS if k != 'full'}
    checks = {'practical_5pct_vs_best': balanced[best] > 0 and balanced['full'] <= .95*balanced[best],
              'practical_2pct_vs_wrong': balanced['wrong'] > 0 and balanced['full'] <= .98*balanced['wrong'],
              'improves_both_in_each_person': all(s['full'] < s[k] for s in person_scores.values() for k in controls),
              'both_conditions_no_worse': all(s['full'] <= s[k] for s in condition_scores.values() for k in controls)}
    return {'unit': 'recorded right load channel change', 'n_people': len(people), 'n_windows': len(data['y']),
            'balanced_mae': balanced, 'per_person_mae': person_scores, 'per_condition_mae': condition_scores,
            'per_person_condition_mae': cells, 'per_trial': trials,
            'mae_control_minus_full': {'balanced': diffs(balanced),
                'per_person': {p: diffs(person_scores[p]) for p in people},
                'per_person_condition': {p: {c: diffs(s) for c,s in cells[p].items()} for p in people}},
            'emg_increment': {'best_non_emg': best, 'components': checks, 'passes': all(checks.values())}}
