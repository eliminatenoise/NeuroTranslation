"""Linear families: M2 (ridge and logistic regression on the compact input), the tuned arm G9, and the
frozen force-baselines grid F4 (refit check and penalty choice on the training pool).

M2 is ported from the published comparator code (comparators.py). The F4 refit is ported from the
earlier baseline method (baselines/model.py: closed-form ridge, logistic regression by Newton steps).
Runtime B.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge

from compact import compact_columns, participant_weights, person_errors

PENALTY_GRID = (0.001, 0.01, 0.1, 1.0)


# ------------------------------------------------------------------------------------------------ M2
def fit_m2(ctable, penalty=None):
    """penalty: None for the published settings (Ridge alpha 1, logistic C 1), or a dict per endpoint."""
    penalty = penalty or {'event': 1.0, 'impulse': 1.0}
    x = compact_columns(ctable['x'])
    person, member, tick = ctable['participant_index'], ctable['member_index'], ctable['issue_tick']
    event_mass = participant_weights(person, member, tick, ctable['event_supported'])
    impulse_mass = participant_weights(person, member, tick, ctable['impulse_supported'])
    known = event_mass > 0
    imp = ctable['impulse_supported']
    load = LogisticRegression(C=1. / penalty['event'], max_iter=1000)
    reg = Ridge(alpha=penalty['impulse'])
    load.fit(x[known], ctable['event'][known], sample_weight=event_mass[known] * known.sum())
    reg.fit(x[imp], (ctable['impulse'] - ctable['persistence'])[imp], sample_weight=impulse_mass[imp] * imp.sum())
    return {'kind': 'M2', 'models': {'event': load, 'impulse': reg}, 'penalty': penalty}


def predict_m2(fitted, x, persistence):
    cols = compact_columns(x)
    return fitted['models']['event'].predict_proba(cols)[:, 1], fitted['models']['impulse'].predict(cols) + persistence


def take_rows(ctable, keep):
    return {k: v[keep] for k, v in ctable.items()}


def choose_penalty(ctable, folds):
    """G9: per endpoint, penalty from {0.001, 0.01, 0.1, 1} by four inner person folds; ties go to the larger."""
    scores = {p: {'event': {}, 'impulse': {}} for p in PENALTY_GRID}
    person = ctable['code']
    for held in folds:
        held_mask = np.isin(person, list(held))
        train, hold = take_rows(ctable, ~held_mask), take_rows(ctable, held_mask)
        for p in PENALTY_GRID:
            fitted = fit_m2(train, {'event': p, 'impulse': p})
            prob, imp = predict_m2(fitted, hold['x'], hold['persistence'])
            for target, est in (('event', prob), ('impulse', imp)):
                mask = hold[f'{target}_supported']
                err = np.square(est - hold['event']) if target == 'event' else np.abs(est - np.nan_to_num(hold['impulse']))
                got = person_errors(hold['code'], hold['member_index'], hold['issue_tick'], mask, err)
                if set(got) & set(scores[p][target]):
                    raise ValueError('a person was scored twice across inner folds')
                scores[p][target].update(got)
    chosen = {}
    for target in ('event', 'impulse'):
        means = {p: float(np.mean(list(scores[p][target].values()))) for p in PENALTY_GRID}
        chosen[target] = min(PENALTY_GRID, key=lambda p: (means[p], -p))
    return chosen, {str(k): {t: float(np.mean(list(v[t].values()))) for t in v} for k, v in scores.items()}


# ---------------------------------------------------------------------------- F4: earlier baselines
F4_ARMS = {'main': {'emg': (True, False), 'force': (False, True), 'force_emg': (True, True)},
           'early': {'force_emg': (True, True), 'force_earlier_emg': (True, True)}}


def row_weights(people, walks, ticks):
    weights = np.zeros(len(people), dtype=np.float64)
    unique_people = np.unique(people)
    for person in unique_people:
        person_rows = people == person
        person_walks = np.unique(walks[person_rows])
        for walk in person_walks:
            rows = np.flatnonzero(person_rows & (walks == walk))
            _, order, plate_counts = np.unique(ticks[rows], return_inverse=True, return_counts=True)
            weights[rows] = 1.0 / (len(unique_people) * len(person_walks) * len(plate_counts) * plate_counts[order])
    return weights


def _scale(past, weights):
    center = weights @ past
    scale = np.sqrt(weights @ np.square(past - center))
    return center, np.where(np.ptp(past, axis=0) > 0, scale, 1.0)


def _design(center, scale, emg, force, use_emg, use_force):
    muscle = emg.reshape(len(emg), -1)
    past = np.column_stack((muscle, force))
    included = np.repeat((use_emg, use_force), (muscle.shape[1], force.shape[1]))
    design = np.zeros_like(past, dtype=np.float64)
    design[:, included] = (past[:, included] - center[included]) / scale[included]
    return np.column_stack((np.ones(len(past)), design))


def _sigmoid(logits):
    small = np.exp(-np.abs(logits))
    return np.where(logits >= 0, 1 / (1 + small), small / (1 + small))


def _ridge(design, values, weights, penalty):
    matrix = design.T @ (weights[:, None] * design)
    penalized = np.arange(1, design.shape[1])
    matrix[penalized, penalized] += penalty
    return np.linalg.solve(matrix, design.T @ (weights * values))


def _logistic(design, values, weights, penalty):
    prevalence = float(weights @ values)
    beta = np.zeros(design.shape[1])
    beta[0] = np.log(prevalence / (1 - prevalence))
    regularizer = np.full_like(beta, penalty)
    regularizer[0] = 0.0

    def loss(candidate):
        logits = design @ candidate
        return float(weights @ np.logaddexp(0.0, np.where(values == 1, -logits, logits))
                     + 0.5 * (regularizer * candidate) @ candidate)

    for _ in range(60):
        probability = _sigmoid(design @ beta)
        grad = design.T @ (weights * (probability - values)) + regularizer * beta
        if np.linalg.norm(grad, ord=np.inf) <= 1e-8:
            return beta
        curvature = weights * probability * (1 - probability)
        hessian = design.T @ (curvature[:, None] * design) + np.diag(regularizer)
        direction = np.linalg.solve(hessian, grad)
        current = loss(beta)
        slope = float(direction @ grad)
        for retry in range(25):
            step = 0.5 ** retry
            proposal = beta - step * direction
            if loss(proposal) <= current - 1e-4 * step * slope + 1e-15:
                beta = proposal
                break
        else:
            raise RuntimeError('logistic line search did not converge')
    raise RuntimeError('logistic fitting reached its iteration limit')


def f4_refit(features, targets, support):
    """Refit the 40 common-six candidates exactly as the earlier method did (gate 'F4 refit')."""
    arrays = {}
    for endpoint, target, method in (('event', 'event_new_load', _logistic), ('impulse', 'signed_impulse_ns', _ridge)):
        for group in ('main', 'early'):
            name = f'{endpoint}_{"early_" if group == "early" else ""}matched'
            chosen = support[name]
            values = targets[target][chosen].astype(np.float64)
            emg, older, force = (features[k][chosen] for k in ('emg_rms_v', 'early_emg_rms_v', 'past_force_n'))
            weights = row_weights(features['person_id'][chosen], features['member_index'][chosen], features['issue_tick'][chosen])
            center, scale = _scale(np.column_stack((emg.reshape(len(emg), -1), force)), weights)
            arrays[f'{name}_center'], arrays[f'{name}_scale'] = center, scale
            for arm, (use_emg, use_force) in F4_ARMS[group].items():
                source = older if arm == 'force_earlier_emg' else emg
                design = _design(center, scale, source, force, use_emg, use_force)
                arrays[f'{name}_{arm}_beta'] = np.stack([method(design, values, weights, p) for p in PENALTY_GRID])
    return arrays


def f4_predict(grid, endpoint, group, arm, penalty, emg, force, earlier=None):
    """Vectorised form of the published CandidateGrid.predict (checked row for row in S0)."""
    name = f'{endpoint}_{"early_" if group == "early" else ""}matched'
    center, scale = grid[name + '_center'], grid[name + '_scale']
    split = 10 * 6
    design = np.zeros((len(force), len(center) + 1), dtype=np.float64)
    design[:, 0] = 1.0
    if arm != 'force':
        source = earlier if arm == 'force_earlier_emg' else emg
        design[:, 1:split + 1] = (source.reshape(len(source), -1) - center[:split]) / scale[:split]
    if arm != 'emg':
        design[:, split + 1:] = (force - center[split:]) / scale[split:]
    beta = grid[f'{name}_{arm}_beta'][PENALTY_GRID.index(penalty)]
    value = design @ beta
    if endpoint == 'event':
        small = np.exp(-np.abs(value))
        return np.where(value >= 0.0, 1.0 / (1.0 + small), small / (1.0 + small))
    return value


def f4_choose(grid, inputs, targets, person_of_member, rows_by_group):
    """Per endpoint, group and arm: lowest person-equal error on the training pool; ties to the larger penalty."""
    person = np.asarray([person_of_member[int(m)] for m in inputs['member_index']])
    choice, table = {}, {}
    for endpoint, target in (('event', 'event_new_load'), ('impulse', 'signed_impulse_ns')):
        for group, arms in F4_ARMS.items():
            mask = rows_by_group[f'{endpoint}_{group}']
            for arm in arms:
                means = {}
                for p in PENALTY_GRID:
                    est = np.full(len(mask), np.nan)
                    sel = np.flatnonzero(mask)
                    est[sel] = f4_predict(grid, endpoint, group, arm, p, inputs['emg_rms_v'][sel],
                                          inputs['past_force_n'][sel], inputs['early_emg_rms_v'][sel])
                    y = np.nan_to_num(targets[target])
                    err = np.square(est - y) if endpoint == 'event' else np.abs(est - y)
                    got = person_errors(person, inputs['member_index'], inputs['issue_tick'], mask, np.nan_to_num(err))
                    means[p] = float(np.mean(list(got.values())))
                key = f'{endpoint}/{group}/{arm}'
                choice[key] = min(PENALTY_GRID, key=lambda p: (means[p], -p))
                table[key] = {str(p): means[p] for p in PENALTY_GRID}
    return choice, table
