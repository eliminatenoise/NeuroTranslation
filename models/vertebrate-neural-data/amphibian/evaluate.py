"""Replay the fixed JS14 unit-identity predictor on native salamander repeat clocks."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from scipy.io import loadmat

from acquire import verify_archive
from reference import benchmark as model

HERE = Path(__file__).resolve().parent
EXPERIMENTS = ('repeated_natural_movie', 'white_noise_checkerboard', 'randomly_moving_bar')
METHODS = ('shared_model', 'online_rate', 'recency', 'uniform')
TICKS_PER_SECOND = 10000
SHA = {
    'reference/protocol.json': 'c0c04287d26d8b1ab7996053adaee26b858ce4b2a0f0110d88726a4c4a06bc08',
    'reference/weights.json': '25f9d22ee284b794c1a4f7019587b6e4b92631ab04ff9664266045aa4718ecad',
    'reference/benchmark.py': '3514e7925fd9c833ab5f939513991eadb04b246cab3d63ee320e807410251f61',
    'clock-qc.json': 'eb27b19b4eaf165cedce7c08318a0bbe981affa55097db98953180118f570e48',
    'protocol.json': '6657d63e9f9d3bb45679d9b4ed87b86cb2e2a62abd902a1b336a88360d5a8bb9',
}


def integer_samples(values, label):
    a = np.asarray(values).reshape(-1)
    if not np.isfinite(a).all() or np.any(a != np.rint(a)) or (a < 0).any():
        raise ValueError(f'Invalid 10 kHz time samples in {label}')
    return a.astype('int64')


def session(archive, label):
    name = f'mode_paper_data/{label}/data.mat'
    raw = archive.read(name)
    data = loadmat(BytesIO(raw), struct_as_record=False, squeeze_me=True)['data']
    spikes = data.spike_times
    if spikes.sampling_rate_in_Hz != TICKS_PER_SECOND:
        raise ValueError('Unexpected sampling rate')
    cell_axis = np.asarray(spikes.all_spike_times)
    if cell_axis.ndim != 1 or cell_axis.dtype != object:
        raise ValueError('Expected one source cell entry per sorted unit')
    cells = [integer_samples(v, 'spikes') for v in cell_axis]
    begin = integer_samples(data.stimulus.repeat_begin_times, 'repeat onsets')
    end = integer_samples(data.stimulus.repeat_end_times, 'repeat ends')
    if (len(begin) != len(end) or (end <= begin).any() or (begin[1:] < end[:-1]).any()):
        raise ValueError('Invalid, unordered or overlapping repeat intervals')
    # Full source repeats with an available 10-second prefix. Keep source order.
    good = np.flatnonzero(end - begin >= 10 * TICKS_PER_SECOND)
    chosen = good[:10]
    date = data.experiment_date if isinstance(data.experiment_date, str) else None
    source = dict(member=name, sha256=sha256(raw).hexdigest(), bytes=len(raw),
                  experiment_date=date, sorted_cell_entries=len(cells),
                  source_analysis_cells=int(np.size(spikes.cells_used)) if hasattr(spikes, 'cells_used') else None,
                  source_repeat_markers=len(begin), markers_at_least_10s=len(good),
                  markers_shorter_than_10s=int(len(begin)-len(good)),
                  selected_one_based_repeat_rows=(chosen + 1).tolist(),
                  sample_rate_Hz=TICKS_PER_SECOND)
    source['global_within_unit_inversions'] = sum(int((np.diff(v) < 0).sum()) for v in cells)
    author_ids = np.asarray(spikes.cells_used).astype(int) if hasattr(spikes, 'cells_used') else None
    if author_ids is not None and (np.unique(author_ids).size != len(author_ids) or min(author_ids) < 1 or max(author_ids) > len(cells)):
        raise ValueError('Invalid source cells_used roster')
    return source, cells, [(int(i+1), int(begin[i]), int(end[i])) for i in chosen], author_ids


def trial_segments(cells, start, stop):
    return [v[(v > start) & (v < stop)] for v in cells]


def replay(cells, unit_ids, number, start, stop, sort_times=False):
    selected = trial_segments(cells, start, stop)
    if sort_times:
        selected = [np.sort(v, kind='stable') for v in selected]
    samples = np.concatenate(selected)
    times = samples.astype(np.float64) / TICKS_PER_SECOND
    # Compare the accepted float-clock conversion to exact rational arithmetic.
    _, right_ms = model.millisecond_edges(times)
    if not np.array_equal(right_ms, (samples + 9) // 10):
        raise ValueError('Floating and native sample clocks disagree')
    packet = BytesIO()
    np.savez(packet, trial_id=number, start_s=start/TICKS_PER_SECOND,
             stop_s=stop/TICKS_PER_SECOND, unit_id=unit_ids,
             spike_end=np.cumsum([len(s) for s in selected]), spike_time_s=times)
    packet.seek(0)
    trial = model.read_trial(packet, number)
    bounds = dict(start_sample=start, stop_sample=stop,
                  events_exactly_on_start_excluded=sum(int((s == start).sum()) for s in cells),
                  events_exactly_on_stop_excluded=sum(int((s == stop).sum()) for s in cells))
    return trial, bounds


def frequency_metrics(trials, weights, grouping):
    ys = np.concatenate([t.targets for t in trials])
    frequency = np.bincount(ys, minlength=len(trials[0].units))
    cutoff = (10 if grouping == 'rare' else int(np.quantile(frequency[frequency > 0], 0.25, method='inverted_cdf')))
    rare = (frequency > 0) & (frequency <= cutoff)
    rows = {}
    for t in trials:
        keep = rare[t.targets]
        x, y = t.features[keep], t.targets[keep]
        if not len(y):
            continue
        logits = {'shared_model': x @ weights, 'online_rate': x[:, :, 0],
                  'recency': x[:, :, 0] + x[:, :, 2], 'uniform': np.zeros(x.shape[:2])}
        for key, value in logits.items():
            rows.setdefault(key, []).append(model.row_scores(value, y))
    rare_y = ys[rare[ys]]
    return dict(upper_target_count=cutoff, units=int(rare.sum()), rows=len(rare_y),
                methods={k:model.metrics(np.concatenate(rows[k]), rare_y)
                         if len(rare_y) else {'rows':0} for k in METHODS})


def evaluate_roster(cells, ids, repeats, frozen, sort_times=False):
    trials, boundaries, rejected = [], [], []
    for number, start, end in repeats:
        stop = start + 10 * TICKS_PER_SECOND
        bad = {str(u):int((np.diff(v) < 0).sum()) for u, v in
               zip(ids, trial_segments(cells, start, stop), strict=True)
               if np.any(np.diff(v) < 0)}
        if bad and not sort_times:
            rejected.append(dict(source_repeat_row=number, start_sample=start, stop_sample=stop,
                                 source_end_sample=end, within_unit_inversions=bad))
            continue
        trial, bounds = replay(cells, ids, number, start, stop, sort_times=sort_times)
        trials.append(trial)
        boundaries.append(dict(source_repeat_row=number, source_end_sample=end,
                               source_within_unit_inversions=bad, **bounds))
    if not trials:
        return dict(status='No eligible validated 10 s repeats', rejected_packets=rejected)
    evaluation = model.evaluate(trials, frozen, same_recording=False)
    weights = np.array(frozen['weights'])
    return dict(intervals=boundaries, rejected_packets=rejected, **evaluation,
                rare_units=frequency_metrics(trials, weights, 'rare'),
                lower_quartile_units=frequency_metrics(trials, weights, 'quartile'))


def evaluate(path):
    for name, expected in SHA.items():
        if model.digest(HERE / name) != expected:
            raise ValueError(f'Frozen input differs: {name}')
    archive_sha = verify_archive(path)
    frozen = json.loads((HERE/'reference/weights.json').read_text())
    results, sensitivity = {}, {}
    with ZipFile(path) as archive:
        for name in EXPERIMENTS:
            evidence, cells, repeats, author_ids = session(archive, name)
            ids = np.arange(1, len(cells)+1)
            results[name] = dict(source=evidence, **evaluate_roster(cells, ids, repeats, frozen))
            if name == 'repeated_natural_movie':
                sensitivity['movie_all_178_sorted_within_unit'] = evaluate_roster(
                    cells, ids, repeats, frozen, sort_times=True)
                sensitivity['movie_authors_170_strict'] = evaluate_roster(
                    [cells[i-1] for i in author_ids], author_ids, repeats, frozen)
    eligible = [v for v in results.values() if 'methods' in v]
    macro = {m:{k:float(np.mean([v['methods'][m]['equal_trial'][k] for v in eligible]))
                for k in ['log_loss','top1','mean_rank','balanced_log_loss','balanced_top1']}
             for m in METHODS}
    return dict(archive_sha256=archive_sha, frozen_inputs=SHA, experiments=results,
                equal_experiment_of_equal_repeat_means=macro, movie_sensitivity=sensitivity)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    model.dump(args.output, evaluate(args.archive))
