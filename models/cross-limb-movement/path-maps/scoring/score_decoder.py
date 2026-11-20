"""Score the preregistered development-only decoder comparison from native OOF predictions."""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np


HERE = Path(__file__).resolve().parent
MUSCLES = [f'{side} {name}' for side in ('left', 'right') for name in
           ('tibialis anterior', 'soleus', 'medial gastrocnemius', 'peroneus longus')] + [
           f'right {name}' for name in ('anterior deltoid', 'brachioradialis', 'flexor digitorum',
                                         'common extensor digitorum', 'first dorsal interosseous')]
SEEDS = (1641, 2718, 3917)
DEVELOPMENT = 'a11706a31bb049fcd84c81264cfbdc5497205602ceb67c0f7a69fbbf906f7590'
PROTOCOL = '43a0780e706beb30f93826ae55e8f65bfe156bd47fa5795eb13093427fef3911'
MODELS = ('separate', 'matched', 'original', 'specialist_exposure', 'specialist_steps')
BASELINES = ('stationary', 'velocity_exact_31_25ms', 'velocity_exact_125ms',
             'velocity_knot_31_25ms', 'velocity_knot_125ms')
DOMAINS = ('balance', 'way')
PRIMARY = ('muscle_mae', 'path_mean_distance_mm')
AXIS = tuple(f'axis{i}_{stat}_mm' for stat in ('mae', 'bias') for i in range(3))
FIELDS = (*PRIMARY, 'endpoint_distance_mm', *AXIS,
          *(f'mae {m}' for m in MUSCLES), *(f'bias {m}' for m in MUSCLES))
OFFSETS = np.arange(1, 33, dtype=float)[None, :, None] / 256
N_DRAWS = 5000


def need(value, why):
    if not value:
        raise ValueError(why)


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix('.partial')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def load_data(path):
    need(digest(path) == DEVELOPMENT, 'development checksum')
    with np.load(path, allow_pickle=False) as source:
        data = dict(source)
    n = len(data['person'])
    need(n == 6943 and all(len(v) == n for v in data.values()), 'cache rows')
    ids = set(zip(data['person'], data['session'], data['event'], strict=True))
    need(len(ids) == n, 'duplicate source event')
    mask = data['muscle_mask']
    need(mask.shape == (n, 13) and mask.dtype == bool, 'observed muscle mask')
    observed = mask.sum(1)
    lower = data['domain'] == 0
    need(np.array_equal(np.unique(data['domain']), (0, 1)), 'domain codes')
    need(lower.sum() == 5179 and np.array_equal([len(np.unique(data['person'][i])) for i in (lower, ~lower)],
                                                (18, 6)), 'expected support')
    need(mask[lower, :8].all() and not mask[lower, 8:].any() and not mask[~lower, :8].any()
         and (observed[~lower] >= 3).all(), 'study muscle coverage')
    for name in ('patch_rms', 'past_rms', 'future_rms'):
        values = data[name]
        active = mask[:, None, :] if values.ndim == 3 else mask
        need(np.isfinite(values).all() and (values >= 0).all() and np.all(np.where(active, 0, values) == 0),
             name + ' missingness')
    reproduced = np.sqrt((data['patch_rms'][:, -4:] ** 2).mean(axis=1))
    need(np.allclose(reproduced, data['past_rms'], rtol=1e-11, atol=1e-12), 'persistence unit or mask')
    need(np.isfinite(data['future_path_mm']).all(), 'finite target path')
    return data


def expected_folds(data):
    folds = np.full(len(data['person']), -1, dtype=int)
    for study in range(2):
        within = data['domain'] == study
        _, ranks = np.unique(data['person'][within], return_inverse=True)
        folds[within] = ranks % 3
    return folds


def check_prediction(rms, path, mask):
    need(rms.shape == mask.shape and path.shape == (len(mask), 32, 3), 'forecast shape')
    need(np.isfinite(rms).all() and np.isfinite(path).all(), 'nonfinite forecast')
    need((rms >= 0).all() and (rms[~mask] == 0).all(), 'negative or nonzero missing RMS')


def check_rows(raw, folds):
    need(raw['row'].dtype == np.int64 and np.array_equal(raw['row'], np.arange(len(folds))),
         'row order or coverage')
    need(raw['fold'].dtype.kind in 'iu' and np.array_equal(raw['fold'], folds), 'held-person folds')


def baselines(history):
    """Accept only causal fields. Two controls use exact past times; two use available patch samples."""
    rms, knots, ages, previous = (history[k] for k in ('past_rms', 'patch_xyz_mm', 'age_s', 'repeat_path_mm'))
    n = len(rms)
    need(knots.shape == (n, 20, 3) and ages.shape == (n, 20) and previous.shape == (n, 32, 3),
         'baseline history shape')
    need(np.isfinite(knots).all() and np.isfinite(ages).all() and np.isfinite(previous).all(),
         'nonfinite controls')
    times = np.arange(-19, 1)[None, :] / 32 - ages
    need((ages >= 0).all() and np.all(np.diff(times, axis=1) > 0) and np.all(times[:, -1] == 0)
         and np.all(knots[:, -1] == 0), 'noncausal or unanchored marker history')
    velocities = {'velocity_exact_31_25ms': (previous[:, -1] - previous[:, 23]) / .03125,
                  'velocity_exact_125ms': previous[:, -1] / .125}
    for name, lag in [('velocity_knot_31_25ms', 1), ('velocity_knot_125ms', 4)]:
        dt = times[:, -1] - times[:, -1 - lag]
        velocities[name] = (knots[:, -1] - knots[:, -1 - lag]) / dt[:, None]
    outputs = {name: (rms, vel[:, None, :] * OFFSETS) for name, vel in velocities.items()}
    outputs['stationary'] = (rms, np.zeros((n, 32, 3)))
    return outputs


def event_errors(data, rms, path):
    mask = data['muscle_mask']
    check_prediction(rms, path, mask)
    muscle = np.where(mask, rms - data['future_rms'], np.nan)
    offset = path - data['future_path_mm']
    distance = np.linalg.norm(offset, axis=2)
    return np.column_stack((np.nansum(abs(muscle), axis=1) / mask.sum(1), distance.mean(1),
                            distance[:, -1], abs(offset).mean(1), offset.mean(1), abs(muscle), muscle))


def finite_mean(values, axis=0):
    count = np.isfinite(values).sum(axis=axis)
    return np.divide(np.nansum(values, axis=axis), count, out=np.full(np.shape(count), np.nan), where=count > 0)


def cohorts(data, study):
    within = data['domain'] == study
    session = data['session']
    direction = data['direction']
    groups = {'all': within}
    if study == 0:
        for posture, name in enumerate(('standing', 'walking')):
            groups[name] = within & (session == posture)
            for cue, rotation in [(-1, 'counterclockwise'), (1, 'clockwise')]:
                groups[f'{name}_{rotation}'] = groups[name] & (direction == cue)
    else:
        for series in sorted(np.unique(session[within])):
            groups[f'series_{series}'] = within & (session == series)
        groups['fully_observed'] = within & data['complete']
        groups['quality_masked'] = within & ~data['complete']
    return groups


def cells(data, study, include):
    """Original-weight groups over the cells retained by a prespecified subset."""
    people = np.unique(data['person'][include])
    rows = []
    for person in people:
        ix = np.flatnonzero(include & (data['person'] == person))
        session = data['session'][ix].astype(int)
        cell = session * 2 + (data['direction'][ix] == 1) if study == 0 else session
        rows.append([ix[cell == key] for key in np.unique(cell)])
    return rows


def reduce_people(group, errors):
    rows = [finite_mean(np.stack([finite_mean(errors[ix]) for ix in person])) for person in group]
    return np.asarray(rows).reshape(-1, len(FIELDS))


def scores(people):
    if len(people) < 2:
        return {}
    means = finite_mean(people)
    return {k: float(means[i]) for i, k in enumerate(FIELDS) if np.isfinite(people[:, i]).sum() >= 2}


def primary_deltas(persons_by_seed, reference_by_seed):
    values = persons_by_seed - reference_by_seed
    return values.mean(axis=0), values.mean(axis=1)


def summarize_difference(person_delta, seed_means, draws, fields):
    summary = {}
    for field in fields:
        j = FIELDS.index(field)
        delta = person_delta[:, j]
        need(np.isfinite(delta).all() and len(delta) >= 2, 'paired comparison support')
        samples = delta[draws].mean(axis=1)
        q = np.percentile(samples, [2.5, 97.5, 98.75])
        seed_values = seed_means[:, j]
        loo = (delta.sum() - delta) / (len(delta) - 1)
        summary[field] = dict(mean=float(delta.mean()), ci95=q[:2].tolist(), upper98_75=float(q[2]),
                              people_lower=int((delta < 0).sum()), people=len(delta),
                              seed_means=seed_values.tolist(), seed_sd=float(seed_values.std(ddof=1)),
                              seed_range=[float(seed_values.min()), float(seed_values.max())],
                              participant_iqr=np.percentile(delta, [25, 75]).tolist(),
                              leave_one_out_range=[float(loo.min()), float(loo.max())])
    return summary


def gate(studies):
    return all(studies[s]['primary'][k]['mean'] < 0 and studies[s]['primary'][k]['upper98_75'] < 0
               for s in DOMAINS for k in PRIMARY)


def fit_costs(fit, folds):
    """Budget and timings are cumulative to a checkpoint. Exposure fits are prefixes of step fits."""
    records = {}
    receipts = {}
    for seed in SEEDS:
        for fold in range(3):
            path = fit / 'fits' / f'seed-{seed}-fold-{fold}.json'
            log = json.loads(path.read_text())
            receipts[path.name] = digest(path)
            held = np.flatnonzero(folds == fold).astype('<i8')
            need((log['seed'], log['fold'], log['held_rows_sha256']) ==
                 (seed, fold, hashlib.sha256(held.tobytes()).hexdigest()), 'fit receipt row identity')
            for name, entry in log['runs'].items():
                records.setdefault(name, []).append(entry)
    labels = (*MODELS[:3], 'lower-exposure', 'upper-exposure', 'lower-steps', 'upper-steps')
    need(set(records) == set(labels), 'all training methods')
    summary = {}
    for name in labels:
        entries = records[name]
        need(len(entries) == 9, 'three seeds and three training folds')
        param, steps, examples = ('parameters', 'updates', 'examples')
        need(all(len(set(e[key] for e in entries)) == 1 for key in (param, steps, examples)), 'fit design stability')
        domains = np.array([e['examples_by_domain'] for e in entries])
        expected_updates = 192 if name.endswith('exposure') else 384
        expected_examples = 48 * expected_updates
        if name.startswith('lower'):
            expected_domains = [expected_examples, 0]
        elif name.startswith('upper'):
            expected_domains = [0, expected_examples]
        else:
            expected_domains = [9216, 9216]
        e = entries[0]
        expected_params = 3975 if name in ('matched', 'separate') else 3924
        need((e[param], e[steps], e[examples]) == (expected_params, expected_updates, expected_examples)
             and np.all(domains == expected_domains), 'equal capacity, updates and study exposure')
        summary[name] = dict(fits=len(entries), parameters=e[param], updates_per_fit=e[steps],
                             examples_per_fit=e[examples], balance_examples_per_fit=int(domains[0, 0]),
                             way_examples_per_fit=int(domains[0, 1]),
                             fit_seconds_nine_fits=sum(e['fit_seconds'] for e in entries),
                             active_loss_gradient_range=[min(e['active_loss_gradients'] for e in entries),
                                                         max(e['active_loss_gradients'] for e in entries)])
    unique_seconds = sum(v['fit_seconds_nine_fits'] for k, v in summary.items() if not k.endswith('exposure'))
    return dict(checkpoints=summary, unique_training_loop_seconds=unique_seconds,
                specialist_accounting='Exposure is a checkpoint of steps; do not add both times.',
                fit_receipt_sha256=receipts)


def compute(data_path, fit):
    need(digest(HERE / 'PROTOCOL.md') == PROTOCOL, 'scoring protocol')
    d = load_data(data_path)
    folds = expected_folds(d)
    groups = {s: {key: cells(d, i, mask) for key, mask in cohorts(d, i).items()}
              for i, s in enumerate(DOMAINS)}
    need(all(len(person) == 4 for person in groups['balance']['all']), 'required balance cross cells')
    rows = {s: {key: {} for key in subsets} for s, subsets in groups.items()}

    def collect(name, predictions):
        errors = event_errors(d, *predictions)
        for s, subsets in groups.items():
            for key, group in subsets.items():
                if key != 'all' and name not in ('separate', 'matched'):
                    continue
                rows[s][key].setdefault(name, []).append(reduce_people(group, errors))

    history = {k: d[k] for k in ('past_rms', 'patch_xyz_mm', 'age_s', 'repeat_path_mm')}
    fixtures = baselines(history)
    for name in BASELINES:
        collect(name, fixtures[name])
    hashes = {}
    for seed in SEEDS:
        result = fit / f'oof-seed-{seed}.npz'
        hashes[result.name] = digest(result)
        receipt = json.loads(result.with_suffix('.json').read_text())
        need((seed, len(folds), hashes[result.name]) == (receipt['seed'], receipt['rows'], receipt['sha256']),
             'producer prediction receipt')
        with np.load(result, allow_pickle=False) as raw:
            check_rows(raw, folds)
            for method in MODELS:
                collect(method, (raw[f'{method}_rms'], raw[f'{method}_path']))

    studies = {}
    for domain, s in enumerate(DOMAINS):
        incl = d['domain'] == domain
        groups_all = groups[s]['all']
        n = len(groups_all)
        draws = np.random.default_rng(1641).integers(n, size=(N_DRAWS, n))
        full = {method: np.stack(v) for method, v in rows[s]['all'].items()}
        methods = {method: {'scores': scores(finite_mean(v)), 'people': n} for method, v in full.items()}
        axis_labels = ['ML', 'SI', 'AP'] if domain == 0 else ['X', 'Y', 'Z']
        subgroups = {}
        for name, group in groups[s].items():
            if name == 'all':
                continue
            count = len(group)
            keep = np.concatenate([ix for person in group for ix in person]) if count else []
            result = {'people': count, 'events': len(keep)}
            if count >= 2:
                separate, matched = [np.mean(rows[s][name][method], axis=0) for method in ('separate', 'matched')]
                result['separate_minus_matched'] = {k: v for k, v in scores(separate - matched).items()
                                                    if k in (*PRIMARY, 'endpoint_distance_mm', *AXIS[:3])}
                for method, people in [('separate', separate), ('matched', matched)]:
                    result[method] = {k: v for k, v in scores(people).items() if k in PRIMARY}
            subgroups[name] = result
        comparisons = {}
        for name in (*MODELS[1:], *BASELINES):
            delta, seeds = primary_deltas(full['separate'], full[name])
            comparisons[name] = summarize_difference(delta, seeds, draws, (*PRIMARY, 'endpoint_distance_mm', *AXIS))
        paired = finite_mean(full['separate'] - full['matched'])
        muscle_better, path_better = paired[:, 0] < 0, paired[:, 1] < 0
        cells_counts = {key: int(np.sum(ms & ps)) for key, ms, ps in
                        [('both_lower', muscle_better, path_better),
                         ('only_muscle_lower', muscle_better, ~path_better),
                         ('only_path_lower', ~muscle_better, path_better),
                         ('neither_lower', ~muscle_better, ~path_better)]}
        mask = d['muscle_mask']
        channel_support = {}
        for j, label in enumerate(MUSCLES):
            if (j < 8) != (domain == 0):
                continue
            valid = incl & mask[:, j]
            channel_support[label] = {'events': int(valid.sum()), 'people': len(np.unique(d['person'][valid]))}
        support = {str(f): dict(events=int(np.sum(incl & (folds == f))),
                                people=len(np.unique(d['person'][incl & (folds == f)]))) for f in range(3)}
        ages = d['age_s'][incl]
        actual_lags = {str(k): [float(np.min(1000 * (k / 32 + ages[:, -1-k] - ages[:, -1]))),
                                float(np.max(1000 * (k / 32 + ages[:, -1-k] - ages[:, -1])))] for k in (1, 4)}
        studies[s] = dict(people=n, events=int(incl.sum()), folds=support, axis_labels=axis_labels,
                          muscle_units=('µV' if domain == 0 else 'WAY exported amplitude units'),
                          channel_support=channel_support, marker_history_lag_ms=actual_lags,
                          methods=methods, primary={k: comparisons['matched'][k] for k in PRIMARY},
                          separate_minus=comparisons, participant_tradeoffs=cells_counts, subgroups=subgroups)
    return dict(version=1, protocol_sha256=PROTOCOL, development_sha256=DEVELOPMENT,
                oof_file_sha256=hashes, seeds=list(SEEDS), studies=studies, all_four_pass=gate(studies),
                compute=fit_costs(fit, folds))


def public_results(result):
    """Export aggregate outcomes, fit times and fixed design without private file fingerprints."""
    costs = {key: value for key, value in result['compute'].items() if key != 'fit_receipt_sha256'}
    return {key: value for key, value in result.items() if key not in ('compute', 'oof_file_sha256')} | {'compute': costs}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--data', type=Path, required=True)
    cli.add_argument('--fit', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    write_json(args.output, public_results(compute(args.data, args.fit)))
