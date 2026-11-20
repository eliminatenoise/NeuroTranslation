"""Fit or score the fixed rat adapter on the separately released six-packet study."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from predict import population_states, read_checkpoint
from population.adapter import TAPS, rates_for_bins, readout_features, ridge_prediction
from population.source_rows import checked, digest

PROTOCOL = '679c858206898bbb3d36d3f3ad79bf19d6452b56ed3a52f601dccfd459edae24'
FIELDS = ('mean', 'scale', 'coef', 'intercept')


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def read_rows(source, split):
    cmd = [sys.executable, '-B', str(HERE / 'source_rows.py'), str(source), split]
    return json.loads(subprocess.check_output(cmd, text=True))


def values(rows, field):
    return np.asarray([row[field] for row in rows])


def row_weights(rows):
    groups = [(r['rat'], r['trip']) for r in rows]
    windows = Counter(groups)
    trips = Counter(rat for rat, trip in windows)
    return np.array([1 / (len(trips) * trips[rat] * windows[rat, trip]) for rat, trip in groups])


def fit_head(features, y, weights):
    mean = np.average(features, weights=weights, axis=0)
    scale = np.sqrt(np.average((features - mean) ** 2, weights=weights, axis=0))
    scale[scale < 1e-8] = 1
    x = (features - mean) / scale
    intercept = np.average(y, weights=weights)
    coef = np.linalg.solve((x.T * weights) @ x + 0.03 * np.eye(x.shape[1]), (x.T * weights) @ (y - intercept))
    return dict(mean=mean, scale=scale, coef=coef, intercept=intercept)


def scrambled(weights):
    rng = np.random.default_rng(20261120)
    names = sorted(k for k in weights if not k.startswith(('angular.', 'population.')))
    return {k: rng.permutation(weights[k].ravel()).reshape(weights[k].shape) for k in names}


def camera(config, weights, rows):
    return population_states(config, weights, *[values(rows, field) for field in ('cutoff_s', 'prior_time_s', 'prior_xy_cm')])


def count_rates(rows, key='regional_counts'):
    return rates_for_bins(values(rows, key), values(rows, 'unit_counts'), len(rows))


def time_limits(rows):
    time = values(rows, 'prior_time_s')
    ages = values(rows, 'cutoff_s')[:, None] + TAPS - time
    durations = np.diff(time, axis=1)
    exceeds_age = np.any(ages > .05 + 1e-7, axis=1)
    exceeds_duration = np.any((durations < .2 - 1e-7) | (durations > .3 + 1e-7), axis=1)
    return dict(windows=len(rows), above_old_50ms_age=int(exceeds_age.sum()),
                outside_old_200_to_300ms_duration=int(exceeds_duration.sum()),
                outside_either=int(np.sum(exceeds_age | exceeds_duration)),
                max_age_s=float(ages.max()), duration_range_s=[float(durations.min()), float(durations.max())])


def fit(args, protocol):
    if digest(args.base) != protocol['frozen_base_sha256']:
        raise ValueError('Original checkpoint identity mismatch')
    rows = read_rows(args.source, 'train')
    config, weights = read_checkpoint(args.base)
    y, w, neural = values(rows, 'target_cm'), row_weights(rows), count_rates(rows)
    with np.load(args.base, allow_pickle=False) as f:
        deploy = {key: f[key] for key in f.files}
    controls = {}
    for destination, encoder in [(deploy, weights), (controls, scrambled(weights))]:
        kin = camera(config, encoder, rows)
        for mode, bins in [('motion', None), ('combined', neural)]:
            state = fit_head(readout_features(*kin, bins), y, w)
            destination.update({f'population.{mode}.{k}': v for k, v in state.items()})
    config['rat_population'] = dict(format=1, region_order=['CA1', 'PFC'], protocol_sha256=PROTOCOL,
                                    original_checkpoint_sha256=protocol['frozen_base_sha256'])
    deploy['configuration'] = np.array(json.dumps(config))
    args.out.mkdir(parents=True, exist_ok=False)
    for filename, arrays in [('movement-weights.npz', deploy), ('scrambled-heads.npz', controls)]:
        np.savez_compressed(args.out / filename, **arrays)
    write_json(args.out / 'fit-seal.json', dict(protocol_sha256=PROTOCOL, train=protocol['train'],
        time_limits=time_limits(rows), files={name: digest(args.out / name) for name in ('movement-weights.npz', 'scrambled-heads.npz')}))


def aggregate(rows, pred, target):
    groups = list(dict.fromkeys((r['rat'], r['trip']) for r in rows))
    by_trip = []
    for rat, trip in groups:
        ids = [i for i, r in enumerate(rows) if (r['rat'], r['trip']) == (rat, trip)]
        by_trip.append(dict(rat=rat, trip=trip, windows=len(ids), **{
            name: float(np.abs(p[ids] - target[ids]).mean()) for name, p in pred.items()}))
    by_rat = []
    for rat in dict.fromkeys(r['rat'] for r in rows):
        trips = [r for r in by_trip if r['rat'] == rat]
        by_rat.append(dict(rat=rat, trips=len(trips), windows=sum(r['windows'] for r in trips), **{
            name: float(np.mean([r[name] for r in trips])) for name in pred}))
    return dict(by_trip=by_trip, by_rat=by_rat,
                equal_rat={name: float(np.mean([r[name] for r in by_rat])) for name in pred},
                pooled_window={name: float(np.abs(p - target).mean()) for name, p in pred.items()})


def direct_comparators(rows, source):
    checked(source, ['predictions.csv'])
    with (source / 'predictions.csv').open(newline='') as stream:
        records = list(csv.DictReader(stream))
    for row, old in zip(rows, records, strict=True):
        for key in ('rat', 'trip', 'cutoff_s', 'target_cm', 'target_time_s', 'donor_trip', 'donor_cutoff_s'):
            if type(row[key])(old[key]) != row[key]:
                raise ValueError(f'Previous forecast has different {key}')
    return {new: np.array([float(r[old]) for r in records]) for new, old in (
        ('speed', 'constant_speed'), ('direct_motion', 'motion'), ('direct_combined', 'combined'), ('direct_donor', 'earlier_trip'))}


def score(args, protocol):
    seal = json.loads((args.fitted / 'fit-seal.json').read_text())
    if seal['protocol_sha256'] != PROTOCOL:
        raise ValueError('Fitted protocol mismatch')
    for name in ('movement-weights.npz', 'scrambled-heads.npz'):
        if digest(args.fitted / name) != seal['files'][name]:
            raise ValueError(f'Fitted weights changed: {name}')
    config, weights = read_checkpoint(args.fitted / 'movement-weights.npz')
    with np.load(args.fitted / 'scrambled-heads.npz', allow_pickle=False) as f:
        controls = {k: f[k] for k in f.files}
    rows = read_rows(args.source, 'test')
    aligned, donor = count_rates(rows), count_rates(rows, 'donor_counts')
    pred = direct_comparators(rows, args.source)
    for prefix, encoder, heads in [('shared', weights, weights), ('scrambled', scrambled(weights), controls)]:
        kin = camera(config, encoder, rows)
        for name, mode, rates in [('motion', 'motion', None), ('combined', 'combined', aligned),
                                  ('donor', 'combined', donor), ('reversed', 'combined', aligned[:, ::-1, :])]:
            state = {k: heads[f'population.{mode}.{k}'] for k in FIELDS}
            pred[f'{prefix}_{name}'] = ridge_prediction(readout_features(*kin, rates), state)
    target = values(rows, 'target_cm')
    result = aggregate(rows, pred, target)
    result.update(unit='cm MAE', test=protocol['test'], retrospective=True,
                  train_time_limits=seal['time_limits'], test_time_limits=time_limits(rows))
    result['checks_by_rat'] = [{ 'rat':r['rat'], **{
        name: bool(r['shared_combined'] < r[name]) for name in ['shared_motion', 'shared_donor', 'direct_combined', 'speed', 'scrambled_combined']}}
        for r in result['by_rat']]
    result['consistent_neural_gain'] = all(r['shared_motion'] and r['shared_donor'] for r in result['checks_by_rat'])
    shifts = {}
    for rat in [*protocol['test'], 'all_pooled_windows']:
        mask = np.ones(len(rows), dtype=bool) if rat == 'all_pooled_windows' else values(rows, 'rat') == rat
        shifts[rat] = {}
        for name in ['shared_donor', 'shared_reversed']:
            delta = (pred['shared_combined'] - pred[name])[mask]
            shifts[rat][name] = dict(rows_changed=int(np.sum(abs(delta) > 1e-8)), total=len(delta),
                                     rms_cm=float(np.sqrt(np.mean(delta**2))), max_abs_cm=float(abs(delta).max()))
    result['sensitivity'] = shifts
    args.out.mkdir(parents=True, exist_ok=False)
    write_json(args.out / 'results.json', result)
    first = rows[0]
    write_json(args.out / 'example.json', dict(domain='rat_population', mode='combined', **{
        k: first[k] for k in ('cutoff_s', 'prior_time_s', 'prior_xy_cm', 'regional_counts', 'unit_counts')}))
    write_json(args.out / 'example-result.json', dict(rat=first['rat'], trip=first['trip'],
        target_xy_cm=first['target_xy_cm'], target_time_s=first['target_time_s'], measured_cm=first['target_cm'],
        predictions_cm={k: float(p[0]) for k, p in pred.items()}))
    ids = ['rat', 'trip', 'cutoff_s', 'target_time_s', 'donor_trip', 'donor_cutoff_s', 'target_cm']
    with (args.out / 'predictions.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(ids + list(pred))
        for i, r in enumerate(rows):
            writer.writerow([r[k] for k in ids] + [p[i] for p in pred.values()])


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest='phase', required=True)
    for phase, flag in [('fit', '--base'), ('score', '--fitted')]:
        parser = sub.add_parser(phase)
        parser.add_argument(flag, type=Path, required=True)
        parser.add_argument('--source', type=Path, required=True)
        parser.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    if digest(HERE / 'protocol.json') != PROTOCOL:
        raise ValueError('Design freeze changed')
    protocol = json.loads((HERE / 'protocol.json').read_text())
    (fit if args.phase == 'fit' else score)(args, protocol)
