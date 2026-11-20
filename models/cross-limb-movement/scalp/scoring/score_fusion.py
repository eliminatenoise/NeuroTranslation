"""Score development-only scalp/muscle/motion forecasts on common events within each study."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROTOCOL = 'e360cbd26cec5e3bc92e544c14bad7a63c13010b5f30258e0b014fc8da269de0'
METRICS = 'fe9de0be289b4d1638095b2f371606d933fbdc14b317ccc4ddff6394b3bacb44'
SCALP = '71420a52c1e3870a30e35176dde80ba5a082c681ed6e13289ada5e2029aceced'
FITTED = ('central', 'reference', 'frontal', 'eye', 'neck', 'wrong_trial',
          'original', 'specialist_exposure', 'specialist_steps')
ARCHIVED = FITTED[-3:]
SLOTS = {
    'central': (('D19', 'A1', 'B22'), ('C3', 'Cz', 'C4')),
    'frontal': (('C29', 'C16'), ('Fp1', 'Fp2')),
    'eye': (('R_horizontal_eog', 'L_horizontal_eog', 'L_vertical_eog'), ()),
    'neck': (('L_neck_emg', 'R_neck_emg'), ()),
}
PUBLIC_NAMES = {
    'central': ('C3', 'Cz', 'C4'), 'frontal': ('Fp1', 'Fp2'),
    'eye': ('right horizontal eye', 'left horizontal eye', 'left vertical eye'),
    'neck': ('left neck', 'right neck')
}


def require(test, why):
    if not test:
        raise ValueError(why)


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_support(data, path, inputs):
    n = len(data['domain'])
    require(digest(path) == SCALP, 'scalp input identity')
    masks = {k: np.zeros((n, 3), dtype=bool) for k in SLOTS}
    with np.load(path, allow_pickle=False) as f:
        for key in ('domain', 'person', 'session', 'event', 'direction', 'block', 'cutoff', 'cutoff_s'):
            require(np.array_equal(f[key], data[key]), f'input row joint identity: {key}')
        for study, prefix in enumerate(('balance', 'way')):
            rows = f[prefix + '_rows']
            require(np.array_equal(rows, np.flatnonzero(data['domain'] == study)), 'source study row order')
            names = f[prefix + '_names'].tolist()
            good = f[prefix + '_good']
            require(good.dtype == bool, 'native channel mask type')
            for key, by_study in SLOTS.items():
                for slot, name in enumerate(by_study[study]):
                    masks[key][rows, slot] = good[:, names.index(name)]
    for key, mask in masks.items():
        require(inputs.mask[key].dtype == bool and np.array_equal(mask, inputs.mask[key]),
                f'{key} native positions, masks or padding')
    donor = inputs.donor
    require(donor.shape == (n,) and donor.dtype.kind in 'iu' and ((donor >= -1) & (donor < n)).all(),
            'wrong-trial donor indices')
    rows = np.flatnonzero(donor >= 0)
    use = donor[rows]
    for key in ('domain', 'person', 'session', 'direction', 'block'):
        require(np.array_equal(data[key][rows], data[key][use]), 'donor mismatch: ' + key)
    require((data['event'][rows] != data['event'][use]).all()
            and np.array_equal(masks['central'][rows], masks['central'][use]), 'donor trial and mask')
    require(len(np.unique(use)) == len(use), 'donor reuse')
    # Guard inclusive source envelopes around the two event cutoffs in native ticks.
    minimum_separation = np.where(data['domain'][rows] == 0, 198 + 71, 314 + 64)
    require((data['cutoff'][rows] - data['cutoff'][use] > minimum_separation).all(),
            'overlapping or future wrong-trial history')
    all_rows = np.ones(n, dtype=bool)
    supports = {name: mask.any(axis=1) for name, mask in masks.items()}
    require(supports['central'].all(), 'primary needs all development events')
    supports.update(reference=supports['central'], wrong_trial=(donor >= 0))
    supports.update({k: all_rows for k in ARCHIVED})
    return masks, supports


def check_support(raw, name, expected):
    field = raw[name + '_support']
    require(field.dtype == bool and np.array_equal(field, expected), f'{name} support or dtype')
    return field


def partial_errors(metrics, data, raw, name, expected):
    mask = check_support(raw, name, expected)
    rms, path = raw[name + '_rms'], raw[name + '_path']
    n = len(mask)
    require(rms.shape == (n, 13) and path.shape == (n, 32, 3), name + ' shape')
    require(np.isnan(rms[~mask]).all() and np.isnan(path[~mask]).all(), name + ' off-support forecasts')
    selected = {k: data[k][mask] for k in ('muscle_mask', 'future_rms', 'future_path_mm')}
    errors = np.full((n, len(metrics.FIELDS)), np.nan)
    errors[mask] = metrics.event_errors(selected, rms[mask], path[mask])
    return errors


def support_counts(data, mask):
    return dict(events=int(mask.sum()), people=len(np.unique(data['person'][mask])))


def matched_support(data, population, use):
    result = support_counts(data, use)
    total = support_counts(data, population)
    return {**result, 'excluded_events': total['events'] - result['events'],
            'people_with_no_eligible_event': total['people'] - result['people']}


def selected_fields(scores, fields):
    return {k: scores[k] for k in fields if k in scores}


def reduce_seeds(metrics, group, errors):
    return np.stack([metrics.reduce_people(group, arr) for arr in errors])


def study_comparison(metrics, data, study, support, a, b, primary=False):
    population = data['domain'] == study
    use = population & support
    out = matched_support(data, population, use)
    n = out['people']
    if n < 2:
        return out
    group = metrics.cells(data, study, use)
    if primary and study == 0:
        require(all(len(person) == 4 for person in group), 'four posture by direction cells per person')
    first = reduce_seeds(metrics, group, a)
    second = reduce_seeds(metrics, group, b)
    out['central'] = metrics.scores(metrics.finite_mean(first))
    out['comparator'] = metrics.scores(metrics.finite_mean(second))
    deltas = first - second
    avg = metrics.finite_mean(deltas)
    seeds = metrics.finite_mean(deltas, axis=1)
    out['mean_paired_difference'] = metrics.scores(avg)
    if n > 2:
        draws = np.random.default_rng(1641).integers(n, size=(5000, n))
        stats = metrics.summarize_difference(avg, seeds, draws, metrics.PRIMARY)
        if not primary:
            for field in metrics.PRIMARY:
                stats[field].pop('upper98_75')
        out['paired_intervals'] = stats
    if primary:
        muscle_lower, path_lower = avg[:, 0] < 0, avg[:, 1] < 0
        out['participant_directions'] = {
            key: int((left & right).sum()) for key, left, right in (
                ('both_lower', muscle_lower, path_lower), ('only_muscle_lower', muscle_lower, ~path_lower),
                ('only_path_lower', ~muscle_lower, path_lower), ('neither_lower', ~muscle_lower, ~path_lower))}
    return out


def groups_with_sites(metrics, data, study, masks):
    groups = metrics.cohorts(data, study)
    within = groups['all']
    for j, name in enumerate(PUBLIC_NAMES['central']):
        present = masks['central'][:, j]
        groups[name + '_present'] = within & present
        groups[name + '_absent'] = within & ~present
    number = masks['central'].sum(1)
    for k in (1, 2, 3):
        groups['available_central_sites_' + str(k)] = within & (number == k)
    return groups


def subgroups(metrics, data, study, masks, a, b):
    groups = groups_with_sites(metrics, data, study, masks)
    results = {}
    fields = (*metrics.PRIMARY, 'endpoint_distance_mm', *metrics.AXIS)
    for name, mask in groups.items():
        if name == 'all':
            continue
        out = support_counts(data, mask)
        if out['people'] >= 2:
            group = metrics.cells(data, study, mask)
            first, second = [reduce_seeds(metrics, group, errors) for errors in (a, b)]
            for label, v in (('central', first), ('reference', second), ('central_minus_reference', first-second)):
                out[label] = selected_fields(metrics.scores(metrics.finite_mean(v)), fields)
        results[name] = out
    return results


def availability(metrics, data, study, masks):
    groups = metrics.cohorts(data, study)
    results = {}
    for condition, group in groups.items():
        channels = {}
        for k, slot_names in PUBLIC_NAMES.items():
            for j, name in enumerate(slot_names):
                channels[name] = support_counts(data, group & masks[k][:, j])
        muscles = {}
        for j, name in enumerate(metrics.MUSCLES):
            if (j < 8) == (study == 0):
                muscles[name] = support_counts(data, group & data['muscle_mask'][:, j])
        results[condition] = {**support_counts(data, group), 'channels': channels, 'muscles': muscles}
    return results


def compute(data_path, scalp_path, input_source, metrics_source, fit_dir, old_fit):
    require(digest(HERE / 'PROTOCOL.md') == PROTOCOL, 'scoring protocol hash')
    require(digest(metrics_source) == METRICS, 'common scoring source hash')
    metrics = load_module(metrics_source)
    data = metrics.load_data(data_path)
    require(digest(scalp_path) == SCALP, 'scalp input identity')
    inputs = load_module(input_source).load_inputs(data_path, scalp_path)
    masks, supports = source_support(data, scalp_path, inputs)
    del inputs
    folds = metrics.expected_folds(data)
    errors = {k: [] for k in FITTED}
    for seed in metrics.SEEDS:
        name = f'oof-seed-{seed}.npz'
        path = fit_dir / name
        receipt = json.loads(path.with_suffix('.json').read_text())
        require((receipt['seed'], receipt['rows'], receipt['sha256']) == (seed, len(folds), digest(path)),
                'new OOF receipt')
        original = old_fit / name
        old_receipt = json.loads(original.with_suffix('.json').read_text())
        require((old_receipt['seed'], old_receipt['rows'], old_receipt['sha256'])
                == (seed, len(folds), digest(original)), 'historical OOF receipt')
        with np.load(path, allow_pickle=False) as raw, np.load(original, allow_pickle=False) as old:
            metrics.check_rows(raw, folds)
            metrics.check_rows(old, folds)
            for method in ARCHIVED:
                for suffix in ('_path', '_rms'):
                    require(np.array_equal(raw[method+suffix], old[method+suffix]), 'reused forecast parity')
            for method in FITTED:
                errors[method].append(partial_errors(metrics, data, raw, method, supports[method]))

    history = {k: data[k] for k in ('past_rms', 'patch_xyz_mm', 'age_s', 'repeat_path_mm')}
    for name, predictions in metrics.baselines(history).items():
        errors[name] = [metrics.event_errors(data, *predictions)]
        supports[name] = np.ones(len(folds), dtype=bool)
    results = {}
    for study, name in enumerate(metrics.DOMAINS):
        within = data['domain'] == study
        comparisons = {}
        for method in (*FITTED[1:], *metrics.BASELINES):
            common = supports[method] & supports['central']
            comparisons[method] = study_comparison(metrics, data, study, common, errors['central'],
                                                     errors[method], primary=(method == 'reference'))
        primary = comparisons['reference']
        results[name] = {
            **support_counts(data, within), 'unit_muscle': 'µV' if study == 0 else 'WAY exported amplitude units',
            'unit_path': 'mm', 'axes': ['ML', 'SI', 'AP'] if study == 0 else ['X', 'Y', 'Z'],
            'fold_support': {str(k): support_counts(data, within & (folds == k)) for k in range(3)},
            'primary': primary['paired_intervals'], 'central_minus': comparisons,
            'primary_subgroups': subgroups(metrics, data, study, masks, errors['central'], errors['reference']),
            'availability': availability(metrics, data, study, masks)
        }
    return {
        'version': 1, 'seeds': list(metrics.SEEDS), 'protocol_sha256': PROTOCOL,
        'development_sha256': metrics.DEVELOPMENT, 'scalp_sha256': SCALP,
        'all_four_pass': metrics.gate(results), 'studies': results,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ('data', 'scalp', 'input-source', 'metrics-source', 'fit', 'original-fit', 'out'):
        cli.add_argument('--' + key, type=Path, required=True)
    args = cli.parse_args()
    result = compute(args.data, args.scalp, args.input_source, args.metrics_source, args.fit, args.original_fit)
    tmp = args.out.with_suffix('.partial')
    tmp.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    tmp.replace(args.out)


if __name__ == '__main__':
    main()
