"""Boosted-tree families: M3 (published tree input), S5 (compact input) and the tuned arm G9.

Ported from the published tree code (trees.py, common.py) and comparator code (comparators.py).
The tree gate checks that M3 at N = 12 reproduces the sealed tree file's predictions bit for bit.
Runtime B: CPython 3.12.14, numpy 2.5.5, scikit-learn 1.9.1. One thread per fit.
"""
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from compact import compact_columns, participant_weights, person_errors

TREE = {'iterations': 128, 'learning_rate': 0.065, 'min_samples_leaf': 24, 'l2_regularization': 0.3, 'bins': 95}
LEAVES = {'event': 7, 'impulse': 31}
LEAF_GRID = (7, 15, 31)
SEED = 20261124


def options(leaves, seed=SEED):
    return dict(max_leaf_nodes=leaves, max_iter=TREE['iterations'], learning_rate=TREE['learning_rate'],
                min_samples_leaf=TREE['min_samples_leaf'], l2_regularization=TREE['l2_regularization'],
                max_bins=TREE['bins'], early_stopping=False, random_state=seed)


# ------------------------------------------------------------------------------- published tree input
def tree_history(inputs, rows, *, emg=True):
    """(rows, 10, 8): six EMG RMS, own plate, other plate; and their availability masks."""
    rows = np.asarray(rows)
    muscle = inputs['emg_rms_v'][rows]
    force = inputs['past_force_n'][rows]
    other = inputs['other_force_n'][rows]
    muscle_ok = inputs['emg_ok'][rows][:, None, None] & np.isfinite(muscle)
    if not emg:
        muscle_ok = np.zeros_like(muscle_ok)
    force_ok = inputs['past_force_ok'][rows][:, None] & np.isfinite(force)
    other_ok = inputs['other_force_ok'][rows][:, None] & np.isfinite(other)
    values = np.concatenate((muscle, force[..., None], other[..., None]), axis=-1)
    mask = np.concatenate((muscle_ok, force_ok[..., None], other_ok[..., None]), axis=-1)
    return np.where(mask, values, 0.).astype(np.float64), mask


def fit_reference(table):
    """Fit prevalence and person-weighted median impulse (the fallback) of the training rows."""
    ew = participant_weights(table['person'], table['member'], table['tick'], table['event_supported'])
    iw = participant_weights(table['person'], table['member'], table['tick'], table['impulse_supported'])
    em, im = ew > 0, iw > 0
    prevalence = float(ew[em] @ table['event'][em])
    impulse = table['impulse'][im]
    order = np.argsort(impulse, kind='stable')
    median = float(impulse[order[np.searchsorted(np.cumsum(iw[im][order]), .5)]])
    return prevalence, median


def fit_scaling(history, available, absent=()):
    """Published scaling. `absent`: channels removed by design (S2 force-only: the six EMG channels),
    which get centre 0 and scale 1; they are always encoded as 0 with a 0 mask. With no absent channel
    this is the published computation unchanged (the tree gate checks it bit for bit)."""
    observed = np.where(available, history, np.nan)
    if absent:
        observed[..., list(absent)] = 0.
    center = np.nanmean(observed, axis=(0, 1))
    scale = np.nanstd(observed, axis=(0, 1))
    if absent:
        center[list(absent)], scale[list(absent)] = 0., 1.
    if not (np.isfinite(center).all() and np.isfinite(scale).all()):
        raise ValueError('a training input channel is unobserved')
    return center, np.where(scale > 1e-12, scale, 1.)


def impulse_reference(history, available, fallback):
    return np.where(available[:, -1, 6], history[:, -1, 6] * .1, fallback)


def tree_features(history, available, center, scale, fallback):
    scaled = np.where(available, (history - center) / scale, 0.)
    encoded = np.concatenate((scaled, available), axis=-1)
    values = encoded[:, :, :8]
    return np.column_stack((encoded.reshape(len(encoded), -1), values[:, -1], values.mean(axis=1),
                            values[:, -1] - values[:, 0], impulse_reference(history, available, fallback)))


def tree_table(inputs, targets, person_of_member, *, emg=True):
    """Training rows (event or impulse support) in (member, tick, plate) order with the tree history."""
    common = inputs['emg_ok'] & inputs['past_force_ok']
    sup_i = common & np.isfinite(targets['signed_impulse_ns'])
    sup_e = common & np.isfinite(targets['event_new_load'])
    sel = np.flatnonzero(sup_i | sup_e)
    order = sel[np.lexsort((inputs['plate'][sel], inputs['issue_tick'][sel], inputs['member_index'][sel]))]
    history, available = tree_history(inputs, order, emg=emg)
    return {'rows': order, 'person': np.asarray([person_of_member[int(m)] for m in inputs['member_index'][order]]),
            'member': inputs['member_index'][order], 'tick': inputs['issue_tick'][order],
            'history': history, 'available': available,
            'event': targets['event_new_load'][order], 'event_supported': sup_e[order],
            'impulse': targets['signed_impulse_ns'][order], 'impulse_supported': sup_i[order]}


def subset(table, keep):
    return {k: (v[keep] if isinstance(v, np.ndarray) and len(v) == len(table['rows']) else v) for k, v in table.items()}


def fit_m3(table, leaves=None, seed=SEED, force_only=False):
    """M3: published tree pair (force_only: arm S2). Returns the two models, scaling and fallback."""
    leaves = leaves or LEAVES
    _, fallback = fit_reference(table)
    center, scale = fit_scaling(table['history'], table['available'], absent=tuple(range(6)) if force_only else ())
    x = tree_features(table['history'], table['available'], center, scale, fallback)
    base = impulse_reference(table['history'], table['available'], fallback)
    models = {}
    for target in ('event', 'impulse'):
        mask = table[f'{target}_supported']
        w = participant_weights(table['person'], table['member'], table['tick'], mask)[mask]
        y = table[target][mask]
        if target == 'event':
            model = HistGradientBoostingClassifier(loss='log_loss', **options(leaves[target], seed))
        else:
            model = HistGradientBoostingRegressor(loss='absolute_error', **options(leaves[target], seed))
            y = y - base[mask]
        models[target] = model.fit(x[mask], y, sample_weight=w * len(w))
    return {'kind': 'M3', 'models': models, 'center': center, 'scale': scale, 'fallback': fallback, 'leaves': leaves}


def predict_m3(fitted, history, available):
    x = tree_features(history, available, fitted['center'], fitted['scale'], fitted['fallback'])
    base = impulse_reference(history, available, fitted['fallback'])
    return fitted['models']['event'].predict_proba(x)[:, 1], fitted['models']['impulse'].predict(x) + base


# --------------------------------------------------------------------------------- compact-input trees
def fit_s5(ctable, leaves=None, seed=SEED):
    """S5: trees on the 61 compact columns (published comparator settings)."""
    leaves = leaves or LEAVES
    x = compact_columns(ctable['x'])
    person, member, tick = ctable['participant_index'], ctable['member_index'], ctable['issue_tick']
    event_mass = participant_weights(person, member, tick, ctable['event_supported'])
    impulse_mass = participant_weights(person, member, tick, ctable['impulse_supported'])
    known = event_mass > 0
    imp = ctable['impulse_supported']
    load = HistGradientBoostingClassifier(**options(leaves['event'], seed))
    reg = HistGradientBoostingRegressor(loss='absolute_error', **options(leaves['impulse'], seed))
    load.fit(x[known], ctable['event'][known], sample_weight=event_mass[known] * known.sum())
    reg.fit(x[imp], (ctable['impulse'] - ctable['persistence'])[imp], sample_weight=impulse_mass[imp] * imp.sum())
    return {'kind': 'S5', 'models': {'event': load, 'impulse': reg}, 'leaves': leaves}


def predict_compact(fitted, x, persistence):
    cols = compact_columns(x)
    return fitted['models']['event'].predict_proba(cols)[:, 1], fitted['models']['impulse'].predict(cols) + persistence


# ------------------------------------------------------------------------------------- inner folds
def choose_leaves(table, folds, seed=SEED):
    """G9: per endpoint, leaves from {7, 15, 31} by the four inner person folds; ties go to fewer leaves."""
    scores = {leaves: {'event': {}, 'impulse': {}} for leaves in LEAF_GRID}
    for held in folds:
        held_mask = np.isin(table['code'], list(held))
        train, hold = subset(table, ~held_mask), subset(table, held_mask)
        for leaves in LEAF_GRID:
            fitted = fit_m3(train, {'event': leaves, 'impulse': leaves}, seed)
            prob, imp = predict_m3(fitted, hold['history'], hold['available'])
            for target, est in (('event', prob), ('impulse', imp)):
                mask = hold[f'{target}_supported']
                err = np.square(est - hold['event']) if target == 'event' else np.abs(est - np.nan_to_num(hold['impulse']))
                got = person_errors(hold['code'], hold['member'], hold['tick'], mask, err)
                if set(got) & set(scores[leaves][target]):
                    raise ValueError('a person was scored twice across inner folds')
                scores[leaves][target].update(got)
    chosen = {}
    for target in ('event', 'impulse'):
        means = {leaves: float(np.mean(list(scores[leaves][target].values()))) for leaves in LEAF_GRID}
        chosen[target] = min(LEAF_GRID, key=lambda leaves: (means[leaves], leaves))
    return chosen, {str(k): {t: float(np.mean(list(v[t].values()))) for t in v} for k, v in scores.items()}
