"""Compact input (shared by M1, M2, S5 and their arms) and the published person weights. NumPy only.

Ported from the published compact input code (inputs.py, comparators.columns) and the person-weight
function of the earlier rolling scorer (sha256 values in PROTOCOL.json).
"""
import numpy as np


def history_features(emg, emg_available, force, force_available):
    """Ten past bins: force / 800 N, median and 80th percentile of within-window EMG change, two masks."""
    strength = np.where(emg_available, np.square(emg), 0.)
    sum_strength = np.cumsum(strength, axis=1)[:, 2:-1]
    count = np.cumsum(emg_available, axis=1)[:, 2:-1]
    baseline = np.sqrt(sum_strength / np.maximum(count, 1))
    use = (count >= 3) & (baseline > 1e-12) & emg_available[:, 3:]
    ratio = np.log1p(np.divide(emg[:, 3:], baseline, out=np.zeros_like(baseline), where=use))
    summary = np.zeros((len(force), 10, 2), dtype=np.float64)
    present = np.zeros_like(force_available)
    for row, tick in np.ndindex(use.shape[:2]):
        sensors = ratio[row, tick, use[row, tick]]
        if sensors.size:
            summary[row, tick + 3] = np.quantile(sensors, [.5, .8])
            present[row, tick + 3] = True
    values = np.concatenate((np.where(force_available, force / 800., 0.)[..., None], summary,
                             force_available[..., None], present[..., None]), axis=-1)
    if not np.isfinite(values).all():
        raise ValueError('nonfinite encoded input')
    return values.astype(np.float32)


def compact_inputs(inputs, rows, *, emg_mode='current'):
    """Compact input x and persistence for the given row indices.

    emg_mode: 'current' (published), 'earlier' (S6: window ending 500 ms before issue) or 'none' (S2).
    """
    rows = np.asarray(rows)
    if emg_mode == 'earlier':
        emg, ok = inputs['early_emg_rms_v'][rows], inputs['early_emg_ok'][rows]
    else:
        emg, ok = inputs['emg_rms_v'][rows], inputs['emg_ok'][rows]
    force = inputs['past_force_n'][rows]
    known = np.isfinite(emg) & ok[:, None, None]
    if emg_mode == 'none':
        known = np.zeros_like(known)
    fknown = np.isfinite(force) & inputs['past_force_ok'][rows][:, None]
    emg0 = np.where(known, emg, 0.)
    force0 = np.where(fknown, force, 0.)
    return history_features(emg0, known, force0, fknown), force0[:, -1] * .1


def participant_weights(person, member, tick, mask):
    """People, then walks, then issue ticks, then represented plates weighted equally (published weights)."""
    people = np.unique(person[mask])
    weights = np.zeros(len(mask), dtype=np.float64)
    for p in people:
        in_person = mask & (person == p)
        walks = np.unique(member[in_person])
        for w in walks:
            rows = np.flatnonzero(in_person & (member == w))
            _, index, plate_counts = np.unique(tick[rows], return_inverse=True, return_counts=True)
            weights[rows] = 1. / (len(people) * len(walks) * len(plate_counts) * plate_counts[index])
    return weights


def training_table(inputs, targets, person_of_member, *, emg_mode='current'):
    """Rows with event or impulse support, ordered by (member, tick, plate): the earlier cache layout."""
    common = inputs['emg_ok'] & inputs['past_force_ok']
    if emg_mode == 'earlier':
        common = common & inputs['early_emg_ok']
    sup_i = common & np.isfinite(targets['signed_impulse_ns'])
    sup_e = common & np.isfinite(targets['event_new_load'])
    sel = np.flatnonzero(sup_i | sup_e)
    order = sel[np.lexsort((inputs['plate'][sel], inputs['issue_tick'][sel], inputs['member_index'][sel]))]
    x, persistence = compact_inputs(inputs, order, emg_mode=emg_mode)
    return {
        'participant_index': np.asarray([person_of_member[int(m)] for m in inputs['member_index'][order]], dtype=np.int64),
        'member_index': inputs['member_index'][order], 'issue_tick': inputs['issue_tick'][order],
        'plate': inputs['plate'][order], 'x': x, 'persistence': persistence,
        'lab': np.zeros(len(order), dtype=np.int64),
        'event': np.where(sup_e[order], targets['event_new_load'][order], 0.), 'event_supported': sup_e[order],
        'impulse': targets['signed_impulse_ns'][order], 'impulse_supported': sup_i[order],
    }


def take(table, rows):
    return {k: v[rows] for k, v in table.items()}



def compact_columns(x):
    """61 columns: flattened input, last bin, window mean, last minus first force (comparators.columns)."""
    values = x.astype(np.float64)
    return np.column_stack((values.reshape(len(values), -1), values[:, -1],
                            values.mean(axis=1), values[:, -1, 0] - values[:, 0, 0]))


def person_errors(person, member, tick, mask, error):
    """Per-person weighted mean error with the published weights (as the earlier scorer)."""
    w = participant_weights(person, member, tick, mask)
    out = {}
    for p in np.unique(person[mask]):
        sel = mask & (person == p)
        out[p] = float(np.average(error[sel], weights=w[sel]))
    return out
