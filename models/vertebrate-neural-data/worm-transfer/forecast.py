"""Budget-matched calcium fluorescence forecast. Requires Python 3.10+ and NumPy."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'protocol.json').read_text())
ARM_NAMES = ('fish', 'worm', 'fish_new_roi', 'fish_late_time')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    return sha(path.read_bytes())


def document(path, contents):
    path.write_text(json.dumps(contents, indent=2, allow_nan=False) + '\n')


def nearest(t, targets):
    right = np.clip(np.searchsorted(t, targets), 0, len(t) - 1)
    left = np.maximum(right - 1, 0)
    return np.where(abs(targets - t[left]) <= abs(targets - t[right]), left, right)


def stats(values):
    return {'minimum': float(np.min(values)), 'median': float(np.median(values)),
            'maximum': float(np.max(values))}


class Recording:
    def __init__(self, animal, path):
        self.animal = animal
        with np.load(path, allow_pickle=False) as packet:
            t = np.array(packet['time_s'], dtype=np.float64)
            f = np.array(packet['fluorescence'], dtype=np.float64)
        if t.ndim != 1 or t.size < 2 or f.ndim != 2 or t.size != f.shape[0]:
            raise ValueError(f'{animal}: expected time_s[T] and fluorescence[T, R]')
        if not np.all(np.isfinite(t)) or np.any(np.diff(t) <= 0):
            raise ValueError(f'{animal}: timestamps must increase strictly')
        t = t - t[0]
        crop = t < P['time_limit_s']
        f = f[crop, :P['roi_limit']]
        t = t[crop]
        prefix = f[t < P['prefix_s']]
        avg = np.full(f.shape[1], np.nan)
        sd = avg.copy()
        for r in range(f.shape[1]):
            finite = prefix[np.isfinite(prefix[:, r]), r]
            if finite.size >= P['minimum_prefix_observations']:
                avg[r] = finite.mean()
                scale = finite.std(ddof=0)
                if scale > 0:
                    sd[r] = scale
        f = (f - avg) / sd
        # All feature times are anchored to the actual last observed frame.
        grid = np.arange(P['prefix_s'], P['time_limit_s'], P['grid_step_s'])
        origin = nearest(t, grid)
        offsets = np.array([-v for v in P['lags_s']] + [P['horizon_s']])
        requested = t[origin, None] + offsets
        frames = nearest(t, requested)
        valid = (np.abs(t[frames] - requested) <= P['timing_tolerance_s']).all(axis=1)
        valid &= np.abs(t[origin] - grid) <= P['timing_tolerance_s']
        valid &= t[origin] >= P['prefix_s']
        valid &= np.all(frames[:, :-1] <= origin[:, None], axis=1)
        valid &= np.all(np.diff(frames[:, :-1], axis=1) < 0, axis=1)
        valid &= frames[:, -1] > origin
        if np.unique(origin[valid]).size != valid.sum():
            raise ValueError(f'{animal}: duplicate origin frame')
        # np.nonzero returns the same grid/ROI order for every scoring arm.
        grid_idx, roi = np.nonzero(valid[:, None] & np.isfinite(f[frames]).all(axis=1))
        if not len(roi):
            raise ValueError(f'{animal}: no eligible case')
        self.grid = grid_idx
        self.roi = roi
        self.origin = t[origin[grid_idx]]
        self.frame_idx = frames[grid_idx]
        samples = f[self.frame_idx, roi[:, None]]
        self.x = samples[:, :-1].copy()
        self.y = samples[:, -1].copy()
        offsets_actual = t[self.frame_idx] - self.origin[:, None]
        self.audit = {
            'input_sha256': file_hash(path), 'sampled_frames': int(t.size),
            'time_span_s': float(t[-1]), 'native_step_s': stats(np.diff(t)),
            'raw_roi_count_in_crop': int(f.shape[1]),
            'prefix_qualified_rois': int(np.isfinite(sd).sum()),
            'eligible_rois': int(np.unique(roi).size), 'eligible_cases': int(roi.size),
            'first_forecast_origin_s': float(self.origin.min()),
            'first_forecast_target_s': float(np.min(t[self.frame_idx[:, -1]])),
            'observed_offsets_s': [stats(s) for s in offsets_actual.T],
        }

    def key(self, i):
        return f"{P['sample_seed']}|{self.animal}|{self.roi[i]}|{self.grid[i]}"

    def take(self, eligible, count):
        indices = np.flatnonzero(eligible)
        if indices.size < count:
            raise ValueError(f'{self.animal}: only {indices.size} candidates for {count} slots')
        ranked = sorted(indices, key=lambda i: sha(self.key(i).encode('ascii')))
        return np.asarray(ranked[:count], dtype=np.int64)

    def rows_digest(self, indices):
        return sha(''.join(self.key(i) + '|' + ','.join(str(j) for j in self.frame_idx[i]) + '\n'
                           for i in indices).encode('ascii'))


def load_split(path):
    split = json.loads(path.read_text())
    worms = split['train_worms']
    animals = [split['train_fish'], *worms, *split['held_fish']]
    if split['train_fish'] != P['training_vertebrate'] or split['held_fish'] != P['evaluation_vertebrates']:
        raise ValueError('fish roster differs from protocol')
    if len(worms) != 8 or sorted(worms) != worms or len(set(animals)) != len(animals):
        raise ValueError('need eight ordered worm identities and globally disjoint animals')
    if any(Path(a).name != a or not a.isascii() or '|' in a for a in animals):
        raise ValueError('invalid animal identity')
    return split


def frozen_sources(split_path):
    return {'forecast.py': file_hash(Path(__file__)), 'protocol.json': file_hash(HERE / 'protocol.json'),
            'split.json': file_hash(split_path)}


def fit(split_path, files, out):
    split = load_split(split_path)
    corpus = {a: Recording(a, files / f'{a}.npz') for a in [split['train_fish'], *split['train_worms']]}
    if len({r.audit['input_sha256'] for r in corpus.values()}) != len(corpus):
        raise ValueError('repeated training input')
    fish = corpus[split['train_fish']]
    even = fish.roi % 2 == 0
    early = fish.origin < P['early_train_boundary_s']
    count = P['core_slots']
    extra = P['replacement_slots']
    ranked = fish.take(even & early, count + extra)
    core = (fish, ranked[:count])
    slots = {
        'fish': [(fish, ranked[count:])],
        'worm': [(corpus[a], corpus[a].take(np.ones(len(corpus[a].y), dtype=bool), extra // 8))
                 for a in split['train_worms']],
        'fish_new_roi': [(fish, fish.take(~even & early, extra))],
        'fish_late_time': [(fish, fish.take(even & ~early, extra))],
    }
    result = {'frozen_sources': frozen_sources(split_path), 'training_sources': {a:r.audit for a,r in corpus.items()},
              'shared_core': {'rows': count, 'row_sha256': fish.rows_digest(core[1])}, 'arms': {}}
    for arm, additions in slots.items():
        groups = [core, *additions]
        x = np.concatenate([rec.x[idx] for rec, idx in groups])
        future = np.concatenate([rec.y[idx] for rec, idx in groups])
        if len(x) != count + extra:
            raise ValueError('unmatched budgets')
        delta = future - x[:, 0]
        weights = np.linalg.solve(x.T @ x + len(x) * P['ridge'] * np.eye(x.shape[1]), x.T @ delta)
        result['arms'][arm] = {'rows': len(x), 'weights_predicting_change': weights.tolist(),
                               'replacement_samples': [{'id': rec.animal, 'rows': len(idx),
                                  'row_sha256': rec.rows_digest(idx)} for rec, idx in additions]}
    document(out, result)


def score_group(rec, predictions, keep):
    idx = np.flatnonzero(keep)
    if not len(idx):
        return {'cases': 0, 'rois': 0}
    rois = np.unique(rec.roi[idx])
    result = {'cases': int(idx.size), 'rois': int(len(rois)), 'mse': {}, 'mae': {}}
    for arm, p in predictions.items():
        err = p[idx] - rec.y[idx]
        roi_loss = [(np.mean(e * e), np.mean(abs(e))) for roi in rois for e in [err[rec.roi[idx] == roi]]]
        result['mse'][arm], result['mae'][arm] = np.mean(roi_loss, axis=0).tolist()
    return result


def pooled(groups):
    valid = [g for g in groups if g['cases']]
    if not valid:
        return {'animals': 0}
    result = {'animals': len(valid), 'cases': sum(g['cases'] for g in valid)}
    for loss in ('mse', 'mae'):
        result[loss] = {arm: float(np.mean([g[loss][arm] for g in valid])) for arm in (*ARM_NAMES, 'persistence')}
    return result


def evaluate(split_path, files, fit_path, expected, out):
    if file_hash(fit_path) != expected:
        raise ValueError('wrong pre-release fit seal')
    frozen = json.loads(fit_path.read_text())
    if frozen['frozen_sources'] != frozen_sources(split_path):
        raise ValueError('code, protocol or split changed since fit')
    split = load_split(split_path)
    ids = split['held_fish']
    previous_hashes = {r['input_sha256'] for r in frozen['training_sources'].values()}
    indiv = {}
    for a in ids:
        rec = Recording(a, files / f'{a}.npz')
        digest = rec.audit['input_sha256']
        if digest in previous_hashes:
            raise ValueError('repeated source across donors or train and held')
        previous_hashes.add(digest)
        curr = rec.x[:, 0]
        pred = {arm: curr + rec.x @ frozen['arms'][arm]['weights_predicting_change'] for arm in ARM_NAMES}
        pred['persistence'] = curr.copy()
        high = abs(curr - rec.x[:, 1]) >= 0.5
        bands = {'all': np.ones(len(curr), dtype=bool), 'early': rec.origin < 60,
                 'middle': (rec.origin >= 60) & (rec.origin < 120), 'late': rec.origin >= 120,
                 'low_prior_change': ~high, 'high_prior_change': high}
        scores = {key: score_group(rec, pred, mask) for key, mask in bands.items()}
        loss = scores['all']['mse']
        indiv[a] = {'recording': rec.audit, 'paired_rows_sha256': rec.rows_digest(range(len(curr))),
                    'scores': scores, 'worm_minus_fish_mse': loss['worm'] - loss['fish']}
    summary = {band: pooled([indiv[a]['scores'][band] for a in ids]) for band in bands}
    primary = summary['all']['mse']
    paired = np.array([indiv[a]['worm_minus_fish_mse'] for a in ids])
    result = {'fit_sha256': expected, 'held_animals': indiv, 'equal_animal_scores': summary,
              'primary': {'worm_minus_fish_mse': float(paired.mean()),
                          'relative_change_percent_vs_fish': 100 * float(paired.mean()) / primary['fish'],
                          'animals_improved': int(np.sum(paired < 0)),
                          'omit_one_animal_mean_differences': {a: float(np.delete(paired, i).mean())
                                                              for i, a in enumerate(ids)},
                          'mse_over_persistence': {arm: primary[arm] / primary['persistence'] for arm in ARM_NAMES}}}
    document(out, result)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stage', choices=['fit', 'evaluate'])
    cli.add_argument('--split', type=Path, required=True)
    cli.add_argument('--files', type=Path, required=True, help='directory of <animal ID>.npz')
    cli.add_argument('--out', type=Path, required=True)
    cli.add_argument('--fit', type=Path)
    cli.add_argument('--fit-sha256', help='fit digest issued before held access')
    args = cli.parse_args()
    if args.stage == 'fit':
        fit(args.split, args.files, args.out)
    else:
        if not args.fit or not args.fit_sha256:
            cli.error('evaluation requires --fit and --fit-sha256')
        evaluate(args.split, args.files, args.fit, args.fit_sha256, args.out)


if __name__ == '__main__':
    main()
