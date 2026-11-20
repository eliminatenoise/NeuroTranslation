"""Build identical eligible support for every method from explicit trial pairs."""
import hashlib
import json
from pathlib import Path

import numpy as np

from portable import features

DEV = ('A01', 'A02')
HOLD = ('A03', 'A04')
CLOCK_ATOL = 1e-8


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_trial(base, person, setting, trial):
    path = Path(base) / person / f'angle{setting}-trial-{trial}.npz'
    sidecar = path.with_suffix('.source.json')
    receipt = json.loads(sidecar.read_text())
    with np.load(path, allow_pickle=False) as f:
        arrays = {k: np.asarray(f[k], dtype=np.float64) for k in ('time_s', 'emg', 'load')}
    if arrays['time_s'].ndim != 1 or not all(a.shape == arrays['time_s'].shape for a in arrays.values()):
        raise ValueError(f'Nonconforming original clock or channels in {path.name}')
    if (receipt['person'], receipt['condition'], receipt['trial']) != (person, f'angle{setting}', trial):
        raise ValueError('Source identity disagrees with requested trial')
    if receipt['source_fields']['emg'] != 'emg_1' or receipt['source_fields']['load'] != 'loadcell_right':
        raise ValueError('Source channel mismatch')
    if receipt['time_origin'] not in ('stored_regular_vector', 'sample_index_at_published_1000_hz'):
        raise ValueError('Unrecognized time provenance')
    if len(arrays['load']) != receipt['rows']:
        raise ValueError('Original row count mismatch')
    for key, arr in arrays.items():
        if hashlib.sha256(arr.astype('<f8').tobytes()).hexdigest() != receipt['array_f64le_sha256'][key]:
            raise ValueError(f'Source vector digest mismatch: {key}')
    return arrays, {'time_origin': receipt['time_origin'], 'original_mat_sha256':receipt['sha256'], 'file': f'{person}/{path.name}', 'npz_sha256': sha(path),
                    'sidecar_sha256': sha(sidecar)}


def contiguous(t):
    return np.isfinite(t).all() and np.all(np.abs(np.diff(t)-.001) <= CLOCK_ATOL)


def windows(record, donor, setting):
    n = len(record['time_s'])
    c = {'candidates': 0, 'clock': 0, 'signal_or_target': 0, 'donor': 0, 'admitted': 0}
    ii = []
    for i in range(200, n - 100, 100):
        c['candidates'] += 1
        past = slice(i-200, i+1)
        if not contiguous(record['time_s'][i-200:i+101]):
            c['clock'] += 1
        elif not (np.isfinite(record['load'][past]).all() and np.isfinite(record['emg'][past]).all()
                  and np.isfinite(record['load'][i+100])):
            c['signal_or_target'] += 1
        elif (i >= len(donor['time_s']) or not contiguous(donor['time_s'][past])
              or not np.isfinite(donor['emg'][past]).all()):
            c['donor'] += 1
        else:
            ii.append(i)
    c['admitted'] = len(ii)
    if not ii:
        raise ValueError(f'No common windows before/after donor intersection: {c}')
    ii = np.asarray(ii)
    idx = ii[:, None] + np.arange(-200, 1)
    load = record['load'][idx]
    x = features(load, record['emg'][idx], int(setting == 5))
    wrong = features(load, donor['emg'][idx], int(setting == 5))
    return {'x': x, 'wrong': wrong, 'i': ii, 'recent': load[:, 200]-load[:, 100],
            'y': record['load'][ii+100] - record['load'][ii]}, c


def dataset(base, people):
    if tuple(people) not in (DEV, HOLD):
        raise ValueError('Use exactly one complete nominated stage')
    parts, sources = [], []
    counts = {}
    for person in people:
        for setting in (0, 5):
            paired = [read_trial(base, person, setting, t) for t in (1, 2)]
            for j in (0, 1):
                arr, count = windows(paired[j][0], paired[1-j][0], setting)
                n = len(arr['y'])
                arr.update(person=np.repeat(person, n), condition=np.repeat(setting, n), trial=np.repeat(j+1, n))
                parts.append(arr)
                counts[f'{person}/angle{setting}-trial-{j+1}'] = count
                sources.append(paired[j][1])
    return {key: np.concatenate([p[key] for p in parts]) for key in parts[0]}, counts, sources


def subset(data, choose):
    return {k: v[choose] for k, v in data.items()}
