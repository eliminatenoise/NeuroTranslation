"""Score the two-date area 2 count forecast. Requires NumPy."""
from __future__ import annotations

import argparse
import contextlib
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np

PHASES = ('pre_target_bump', 'post_bump_go', 'unbumped_go')
REGIMES = ('bump_before_target_and_go', 'go_after_bump_before_target', 'go_without_bump')
KEYS = ('trial', 'phase', 'k', 'offset', 'direction')
ARMS = ('all', 'count_cue', 'wrong_movement', 'movement_cue', 'cue', 'movement', 'count')
METRICS = ('mae', 'deviance', 'observed_mean', 'predicted_mean')
SEEDS = (17, 41, 73)
OFFSETS = (0, 5, 10, 15)
DIRECTIONS = (0, 90, 180, 270)
REPS, BLOCK, BOOT_SEED = 5000, 12, 20170913
FLOOR = 1e-6


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_json(path):
    return json.loads(path.read_text())


def take(path, fields):
    with np.load(path, allow_pickle=False) as data:
        return {k: data[k] for k in fields}


def original_means(rows, trial):
    """Return per-original means with a single grouping shared across columns."""
    order = np.argsort(trial, kind='stable')
    ids, first, counts = np.unique(trial[order], return_index=True, return_counts=True)
    total = np.add.reduceat(rows[order], first, axis=0, dtype=np.float64)
    divisor = counts.reshape((-1,) + (1,) * (rows.ndim - 1))
    return ids, counts, total / divisor


def bootstrap_counts(n, reps=REPS, block=BLOCK, seed=BOOT_SEED):
    """Each row counts occurrences of all original slots in one bootstrap draw."""
    check(n >= block > 0, 'too few assigned originals for the fixed block')
    rng = np.random.default_rng(seed)
    blocks = (n + block - 1) // block
    starts = rng.integers(0, n - block + 1, size=(reps, blocks))
    stop = starts + block
    stop[:, -1] = starts[:, -1] + n - (blocks - 1) * block
    edge = np.zeros((reps, n + 1), dtype=np.int32)
    rows = np.arange(reps)[:, None]
    np.add.at(edge, (rows, starts), 1)
    np.add.at(edge, (rows, stop), -1)
    return edge[:, :-1].cumsum(axis=1, dtype=np.int32)


def draws_for(ids, chronology, hits, original):
    ix = np.searchsorted(chronology, ids)
    check(np.array_equal(chronology[ix], ids), 'original missing on bootstrap timeline')
    weights = hits[:, ix].T
    denominators = weights.sum(axis=0)
    valid = denominators > 0
    draws = weights.T.astype(float) @ original
    return original.mean(axis=0), draws[valid] / denominators[valid, None]


def expected_donors(data):
    n = len(data['trial'])
    donors = np.full(n, -1, dtype=int)
    latest = {}
    keys = list(zip(data['phase'], data['offset'], data['direction'], strict=True))
    for i in np.argsort(data['trial'], kind='stable'):
        key = (*keys[i], tuple(data['cues'][i].ravel()))
        donor = latest.get(key, -1)
        if donor >= 0:
            check(data['trial'][donor] < data['trial'][i], 'duplicate donor key in original')
        donors[i] = donor
        latest[key] = i
    return donors


def check_and_open(stage, train_path, source_dir, models_dir, release, metadata=None):
    if stage == 'test':
        check(release is not None, 'explicit held-day release required')
        permit = load_json(release)
        check(permit.get('status') == 'released' and permit.get('authorized') is True
              and permit.get('split') == 'test', 'held-day release not acknowledged')
    metadata = metadata or source_dir
    identity_path = metadata / 'identities.json'
    identity = load_json(identity_path)
    train = take(train_path, ('trial', 'contact_id', 'target_count_100ms', 'original_ids'))
    train_sha = sha(train_path)
    if train_sha != identity['accepted_training_archive_sha256']:
        # A source rebuild can use a different ZIP layout or contain additional row keys.
        with np.load(train_path, allow_pickle=False) as rebuilt:
            for key, spec in identity['training_fields'].items():
                array = rebuilt[key]
                check(list(array.shape) == spec['shape'] and array.dtype.str == spec['dtype']
                      and hashlib.sha256(array.tobytes(order='C')).hexdigest() == spec['sha256_C_order'],
                      'day-one training field identity: ' + key)
    split_path = metadata / 'first-day-split.json'
    split = load_json(split_path)
    check(np.array_equal(train['original_ids'], [r['trial'] for r in split['fit']]), 'training originals')
    contacts = np.array(identity['contacts'])
    check(len(contacts) == 26 and np.array_equal(contacts, train['contact_id']), 'day-one contacts')
    _, _, per_trial = original_means(train['target_count_100ms'], train['trial'])
    training_mean = per_trial.mean(axis=0)

    source_path = source_dir / f'{stage}.npz'
    qc_path = source_dir / f'{stage}-qc.json'
    qc = load_json(qc_path)
    source = take(source_path, KEYS + ('donor', 'target_count_100ms', 'prior_count_100ms',
                                       'contact_id', 'cues'))
    pre_rows = np.asarray(qc['pre_qc_rows'])
    check(pre_rows.ndim == 2 and pre_rows.shape[1] == len(KEYS), 'pre-QC schema')
    check(np.isfinite(pre_rows).all() and np.equal(pre_rows, pre_rows.astype(int)).all(), 'pre-QC integral keys')
    pre_rows = pre_rows.astype(int)
    if stage == 'test':
        assigned = np.arange(identity['held_original_range_inclusive'][0], identity['held_original_range_inclusive'][1] + 1)
        membership_path = metadata / 'held-day-membership.json'
        raw = load_json(membership_path)
        locked = [(int(i), REGIMES.index(p), int(k), int(o), int(d)) for i, p, k, o, d in raw['rows']]
        check(sorted(locked) == sorted(map(tuple, pre_rows)), 'held-day membership changed after lock')
    else:
        assigned = np.array([row['trial'] for row in split['validation']])
        check(np.all(pre_rows[:, 1] == 0), 'unexpected validation phase')
    check(qc['stage'] == stage and qc['source_mat_sha256'] == identity['sources']['2017-09-' + ('13' if stage == 'test' else '12')]['sha256'], 'QC source identity')
    for phase in np.unique(pre_rows[:, 1]):
        check(np.array_equal(np.unique(pre_rows[pre_rows[:, 1] == phase, 0]),
                             qc['phase_eligible_original_ids'][REGIMES[phase]]), 'pre-QC eligible IDs')
    n = len(source['trial'])
    check(np.isin(pre_rows[:, 0], assigned).all() and len(set(map(tuple, pre_rows))) == len(pre_rows),
          'unassigned or duplicate pre-QC rows')
    check(len(assigned) == (1387 if stage == 'test' else 108) and np.all(np.diff(assigned) > 0), 'assigned IDs')
    for key in (*KEYS, 'donor'):
        v = source[key]
        check(v.shape == (n,) and np.issubdtype(v.dtype, np.number)
              and np.isfinite(v).all() and np.equal(v, v.astype(int)).all(), 'invalid source key ' + key)
        source[key] = v.astype(int)
    check(np.isin(source['phase'], range(3)).all() and np.isin(source['offset'], OFFSETS).all()
          and np.isin(source['direction'], DIRECTIONS).all(), 'phase, offset or direction')
    post = np.column_stack([source[k] for k in KEYS])
    check(set(map(tuple, post)).issubset(set(map(tuple, pre_rows))), 'source rows outside membership')
    check(len(np.unique(post[:, [0, 1, 3]], axis=0)) == n, 'duplicate original, phase or offset')
    check(np.array_equal(source['contact_id'], contacts), 'evaluation contact order')
    check(source['cues'].shape == (n, 5, 7) and np.isfinite(source['cues']).all(), 'cue history')
    check(np.array_equal(source['donor'], expected_donors(source)), 'incorrect or missing nearest eligible donor')
    for k in ('target_count_100ms', 'prior_count_100ms'):
        a = source[k]
        check(a.shape == (n, 26) and np.isfinite(a).all() and (a >= 0).all() and np.equal(a, np.floor(a)).all(), k)
    predictions = {'training_mean': np.broadcast_to(training_mean, (1, n, 26)),
                   'persistence': source['prior_count_100ms'][None]}
    paths = [source_path, qc_path, split_path, identity_path]
    if stage == 'test':
        paths.append(membership_path)
    for family in ('transformer', 'poisson'):
        path = models_dir / f'{stage}-{family}.npz'
        paths.append(path)
        arrays = take(path, (*KEYS, 'donor', 'seeds', *ARMS))
        for key in (*KEYS, 'donor'):
            check(np.array_equal(arrays[key], source[key]), f'{family} row mismatch: {key}')
        expected_seeds = SEEDS if family == 'transformer' else ()
        check(np.array_equal(arrays['seeds'], expected_seeds), f'{family} seeds')
        for arm in ARMS:
            a = arrays[arm]
            check(a.shape == ((3, n, 26) if family == 'transformer' else (n, 26)), f'{family} {arm} shape')
            if family == 'poisson':
                a = a[None]
            valid = source['donor'] >= 0 if arm == 'wrong_movement' else np.ones(n, dtype=bool)
            check(np.isfinite(a[:, valid]).all() and (a[:, valid] >= 0).all()
                  and np.isnan(a[:, ~valid]).all(), f'{family} {arm} forecast support')
            predictions[f'{family}_{arm}'] = a
    hashes = {p.name: sha(p) for p in paths}
    hashes['training_archive'] = train_sha
    return source, assigned, pre_rows, predictions, training_mean, hashes


def measures(observed, predicted):
    """Raw signed count means and two losses; deviance alone uses the floor."""
    y = np.broadcast_to(np.asarray(observed, dtype=float), predicted.shape)
    p = np.asarray(predicted, dtype=float)
    m = np.maximum(p, FLOOR)
    ratio = np.ones_like(m)
    np.divide(y, m, out=ratio, where=y > 0)
    dev = 2 * (y * np.log(ratio) - y + m)
    return np.stack((np.abs(y - p), dev, y, p), axis=-1)


def pair_indices(names):
    pairs = []
    for j, name in enumerate(names):
        if name != 'transformer_all':
            pairs.append((names.index('transformer_all'), j))
        if name in ('poisson_count_cue', 'poisson_wrong_movement'):
            pairs.append((names.index('poisson_all'), j))
    return pairs


def estimates(names, original, ids, timeline, hits):
    point, draws = draws_for(ids, timeline, hits, original.reshape(len(ids), -1))
    point = point.reshape(-1, len(METRICS))
    draws = draws.reshape(len(draws), len(names), len(METRICS))
    # Quantile along the draw axis once for all scores and once for all paired contrasts.
    def records(labels, means, sample, metrics):
        if len(sample):
            low, high = np.quantile(sample, (0.025, 0.975), axis=0, method='linear')
        else:
            low = high = np.full(means.shape, np.nan)
        return {name: {m: dict(estimate=float(means[i, j]),
                               interval=[float(low[i, j]), float(high[i, j])] if len(sample) else [None, None],
                               draws=len(sample)) for j, m in enumerate(metrics)} for i, name in enumerate(labels)}
    scores = records(names, point, draws, METRICS)
    left, right = np.asarray(pair_indices(names)).T
    pair_names = [f'{names[l]}-minus-{names[r]}' for l, r in zip(left, right, strict=True)]
    contrasts = records(pair_names, point[left, :2] - point[right, :2],
                        draws[:, left, :2] - draws[:, right, :2], METRICS[:2])
    return dict(scores=scores, contrasts=contrasts)


@contextlib.contextmanager
def csv_writer(path, header):
    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
        with io.TextIOWrapper(gz, encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\n')
            writer.writerow(header.split())
            yield writer


def donor_table(writer, source, pre):
    lookup = {tuple(map(int, row)): i for i, row in enumerate(zip(*(source[k] for k in KEYS), strict=True))}
    for trial, phase, k, offset, direction in sorted(map(tuple, pre)):
        i = lookup.get((trial, phase, k, offset, direction))
        d = source['donor'][i] if i is not None else -1
        writer.writerow((PHASES[phase], trial, k, offset, direction, i if i is not None else '', int(i is not None),
                         int(d >= 0), d if d >= 0 else '', source['trial'][d] if d >= 0 else '',
                         source['k'][d] if d >= 0 else ''))


def phase_tables(source, forecasts, pre, assigned, phase, tables):
    s_mask = source['phase'] == phase
    phase_rows = np.flatnonzero(s_mask)
    selected_pre = pre[pre[:, 1] == phase]
    timeline = np.unique(selected_pre[:, 0])
    hits = bootstrap_counts(len(timeline))
    assigned_hits = bootstrap_counts(len(assigned))
    phase_name = PHASES[phase]
    trial = source['trial'][phase_rows]
    y = source['target_count_100ms'][phase_rows]
    donor_mask = source['donor'][phase_rows] >= 0
    support = dict(assigned_originals=len(assigned), pre_qc_originals=len(timeline),
                   pre_qc_windows=len(selected_pre), eligible_originals=len(np.unique(trial)), eligible_windows=len(trial),
                   qc_excluded_windows=len(selected_pre) - len(trial),
                   qc_excluded_originals=np.setdiff1d(timeline, trial).tolist(),
                   donor_missing_windows=int((~donor_mask).sum()),
                   donor_missing_whole_originals=np.setdiff1d(trial, trial[donor_mask]).tolist())
    out = {'support': support}
    for pop in ('all_eligible', 'matched'):
        pop_mask = donor_mask if pop == 'matched' else np.ones(len(trial), dtype=bool)
        names = [n for n in forecasts if pop == 'matched' or not n.endswith('wrong_movement')]
        rows = phase_rows[pop_mask]
        trials = trial[pop_mask]
        observed = y[pop_mask]
        if not len(rows):
            out[pop] = dict(originals=0, windows=0, scores={}, contrasts={})
            continue
        per_contact = []
        seed_aggregates = []
        zero_counts = {}
        for name in names:
            pred = forecasts[name][:, rows, :]
            losses = measures(observed[None], pred)
            per_contact.append(losses.mean(axis=0))
            seed_aggregates.append(losses.mean(axis=2))
            zero_counts[name] = {'predicted_zero_cells_by_seed': (pred == 0).sum(axis=(1, 2)).tolist(),
                                 'positive_target_at_zero_by_seed': ((pred == 0) & (observed > 0)).sum(axis=(1, 2)).tolist()}
        cells = np.stack(per_contact, axis=2)  # row, contact, method, measure
        aggregate = cells.mean(axis=1)
        ids, counts, original = original_means(aggregate, trials)
        report = dict(originals=len(ids), windows=len(rows), contacts=len(source['contact_id']),
                      count_cells=int(observed.size), observed_zero_cells=int((observed == 0).sum()),
                      forecast_zero_counts=zero_counts, **estimates(names, original, ids, timeline, hits))
        report['assigned_timeline_sensitivity'] = estimates(names, original, ids, assigned, assigned_hits)['contrasts']
        seed_records = {}
        for j, seed in enumerate(SEEDS):
            seed_rows = np.stack([m[j if len(m) == 3 else 0] for m in seed_aggregates], axis=1)
            _, _, seed_original = original_means(seed_rows, trials)
            seed_records[str(seed)] = estimates(names, seed_original, ids, timeline, hits)
        report['seeds'] = seed_records
        out[pop] = report
        original_idx = {tid: i for i, tid in enumerate(ids)}
        for tid in timeline:
            i = original_idx.get(tid)
            for j, name in enumerate(names):
                values = ('',) * len(METRICS) if i is None else original[i, j]
                tables['original'].writerow((phase_name, pop, tid, name, 0 if i is None else counts[i], *values))
        offsets, directions = source['offset'][rows], source['direction'][rows]
        all_rows = np.ones(len(rows), dtype=bool)
        groups = [('direction_deg', str(d), directions == d, None) for d in DIRECTIONS]
        groups += [('offset_ms', str(o * 10), offsets == o, None) for o in OFFSETS]
        groups += [('direction_deg/offset_ms', f'{d}/{o * 10}', (directions == d) & (offsets == o), None)
                   for d in DIRECTIONS for o in OFFSETS]
        groups += [('contact', str(c), all_rows, j) for j, c in enumerate(source['contact_id'])]
        for stratum, label, keep, contact in groups:
            subset = aggregate if contact is None else cells[:, contact]
            contacts = len(source['contact_id']) if contact is None else 1
            if not keep.any():
                tables['strata'].writerow((phase_name, pop, stratum, label, 0, 0, contacts, '', '', '', '', '', '', 0))
                continue
            grp_ids, _, grp_orig = original_means(subset[keep], trials[keep])
            records = estimates(names, grp_orig, grp_ids, timeline, hits)
            prefix = (phase_name, pop, stratum, label, len(grp_ids), int(keep.sum()), contacts)
            for role, methods in records.items():
                for model, metrics in methods.items():
                    for measure, record in metrics.items():
                        tables['strata'].writerow((*prefix, role, model, measure, record['estimate'],
                                                   *record['interval'], record['draws']))
    return out


def decision(stage, phases):
    results = phases['pre_target_bump']['matched']['contrasts']
    checks = {}
    for other in ('count_cue', 'wrong_movement'):
        key = 'transformer_all-minus-transformer_' + other
        if key not in results:
            checks[other] = 'unsupported'
            continue
        low, high = results[key]['deviance']['interval']
        checks[other] = ('unsupported' if low is None else 'lower_error' if high < 0 else
                         'higher_error' if low > 0 else 'unresolved')
    passed = all(v == 'lower_error' for v in checks.values())
    status = 'both_comparisons_favour_full' if passed else 'incremental_signal_criterion_not_met'
    return dict(passed=passed if stage == 'test' else None, status=status if stage == 'test' else 'development_only', checks=checks)


def report_text(summary):
    stage = summary['stage']
    when = '13 September 2017' if stage == 'test' else '12 September 2017, the validation block'
    lines = [f'# Forecasting the next 100 ms on {when}', '',
             'A macaque holds a robotic handle. When the robot pushes, does the movement of the handle help predict how many events each of 26 contacts in sensory cortex will register next? The model learned from the early push trials on 12 September. It gets the preceding 200 ms of movement, cortical counts and available cues.', '']
    bump = summary['phases']['pre_target_bump']
    support = bump['support']
    lines.append(f"Of {support['pre_qc_windows']:,} candidate push windows from {support['pre_qc_originals']:,} originals, {bump['all_eligible']['windows']:,} windows survived signal checks. An earlier original with a matching push, timing and cue history supplied a substitute movement for {bump['matched']['windows']:,} windows from {bump['matched']['originals']:,} originals. The two comparisons below use those same windows.")
    lines += ['', '| Input for comparison | Full minus comparison, Poisson deviance | Paired 95% interval |',
              '|---|---:|---:|']
    for arm, text in (('count_cue', 'Past counts and cues'), ('wrong_movement', 'Movement borrowed from another trial')):
        record = bump['matched']['contrasts'].get('transformer_all-minus-transformer_' + arm)
        if record:
            m = record['deviance']
            lines.append(f"| {text} | {m['estimate']:+.6f} | [{m['interval'][0]:+.6f}, {m['interval'][1]:+.6f}] |")
    lines += ['', 'Lower deviance means a closer count forecast. For movement to pass this test, both intervals must fall entirely below zero.']
    if stage == 'test':
        lines.append('Both comparisons pass.' if summary['primary']['passed'] else 'The held-day result falls short of that requirement.')
    else:
        lines.append('These trials come from the training date and serve as a development check.')
    lines += ['', '| Phase and donor-matched sample | Originals | Windows | Full-model deviance | Mean absolute error, counts/contact/100 ms |',
              '|---|---:|---:|---:|---:|']
    labels = ('Push before target', 'Go cue after push', 'Go cue without a push')
    for index, phase in enumerate(PHASES):
        if phase in summary['phases']:
            matched = summary['phases'][phase]['matched']
            if matched['windows']:
                scores = matched['scores']['transformer_all']
                lines.append(f"| {labels[index]} | {matched['originals']} | {matched['windows']} | {scores['deviance']['estimate']:.6f} | {scores['mae']['estimate']:.6f} |")
    lines += ['', 'Each original trial has equal weight. The three fits contribute their individual errors equally. Intervals resample consecutive groups of 12 originals and hold the fits fixed. The go-cue phases extend beyond the push windows used for training.',
              '', 'The instrument records unsorted events at each named contact. The recordings on these two dates come from one animal. A contact can pick up different cells from one day to the next. These errors measure agreement with the deposited counts. Perception, motor commands and performance in a live feedback loop remain unmeasured.', '']
    return '\n'.join(lines)


def run(stage, train, source_dir, models, output, release=None, metadata=None):
    source, assigned, pre, forecasts, mean, hashes = check_and_open(stage, train, source_dir, models, release, metadata)
    output.mkdir(parents=True, exist_ok=True)
    summary = dict(schema_version=1, stage=stage, hashes=hashes, contact_ids=source['contact_id'].tolist(),
                   training_mean_count_per_contact_100ms=mean.tolist(), seeds=list(SEEDS),
                   deviance_expected_count_floor=FLOOR, bootstrap=dict(replicates=REPS, block=BLOCK, seed=BOOT_SEED,
                   primary='pre-QC phase chronology', sensitivity='full assigned original chronology',
                   sampling='non-circular uniformly sampled moving blocks, truncated final block, percentile intervals'),
                   phases={})
    with contextlib.ExitStack() as stack:
        def table(filename, header):
            return stack.enter_context(csv_writer(output / filename, header))
        donor_table(table('donors.csv.gz', 'phase original k offset_bins direction_deg row_0based passed_qc matched donor_row_0based donor_original donor_k'), source, pre)
        tables = dict(original=table('original-scores.csv.gz', 'phase population original model windows ' + ' '.join(METRICS)),
                      strata=table('strata.csv.gz', 'phase population stratum level originals windows contacts kind model metric estimate ci_low ci_high draws'))
        for phase in np.unique(pre[:, 1]):
            summary['phases'][PHASES[phase]] = phase_tables(source, forecasts, pre, assigned, phase, tables)
    summary['primary'] = decision(stage, summary['phases'])
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (output / 'RESULTS.md').write_text(report_text(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=('validation', 'test'))
    for flag in ('train', 'source', 'models', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--release', type=Path, help='Data-only held-day release JSON')
    parser.add_argument('--metadata', type=Path, help='Directory with source identity and split metadata, defaults to --source')
    args = parser.parse_args()
    run(args.stage, args.train, args.source, args.models, args.output, args.release, args.metadata)
