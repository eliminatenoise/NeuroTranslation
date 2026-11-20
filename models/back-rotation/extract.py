"""Causal, past-only sensor features on the verified 2 kHz source clock."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from scipy.io import loadmat

TASKS = (611, 621)
FEATURES = ['step_deg', 'from_start_deg', 'walk', 'upper_channel_spread',
            'upper_channel_difference', 'upper_common_spread', 'lower_channel_spread',
            'lower_channel_difference', 'lower_common_spread']


@dataclass
class Trial:
    x: np.ndarray           # windows × 10 tokens × 9 features, before weighting or scaling
    y: np.ndarray           # future unsigned device rotation in degrees
    code: np.ndarray        # original code at the cutoff
    cutoff: np.ndarray      # original frame index, zero based
    donor: np.ndarray       # indexes rows of x in this trial only
    excluded: dict
    member_sha256: str = ''

    def wrong_tokens(self):
        result = self.x.copy()
        result[:, :, 3:] = self.x[self.donor, :, 3:]
        return result


def angle(a, b):
    """Unsigned geodesic distance in degrees between normalized quaternions."""
    return np.rad2deg(2 * np.arccos(np.clip(np.abs(np.sum(a * b, axis=-1)), 0, 1)))


def normalize(q):
    q = np.asarray(q, dtype=np.float64)
    length = np.linalg.norm(q, axis=-1, keepdims=True)
    if not np.isfinite(length).all() or np.any(length <= 0):
        raise ValueError('Nonfinite or zero-norm source orientation')
    return q / length


def voltage_summary(history):
    # history is 32 × 200; convert before squaring or differencing float32 samples
    bins = np.asarray(history, dtype=np.float64).reshape(32, 10, 20)
    spread = np.median(np.std(bins, axis=2), axis=0)
    difference = np.median(np.sqrt(np.mean(np.diff(bins, axis=2) ** 2, axis=2)), axis=0)
    common = np.std(np.median(bins, axis=0), axis=1)
    return np.log1p(np.stack([spread, difference, common], axis=1))


def past_tokens(q_history, upper_history, lower_history, code):
    """Input is exactly t−200..t orientation and t−199..t raw voltage (µV)."""
    q_history = np.asarray(q_history)
    if (q_history.shape != (201, 4) or upper_history.shape != (32, 200) or
            lower_history.shape != (32, 200) or code not in TASKS):
        raise ValueError('Expected 201 orientation rows, 200 voltage frames at 32 electrodes per site, basic task')
    if not np.isfinite(upper_history).all() or not np.isfinite(lower_history).all():
        raise ValueError('Nonfinite raw voltage in history')
    sampled = normalize(q_history)[::20]
    columns = (angle(sampled[:-1], sampled[1:]), angle(sampled[0], sampled[1:]),
               np.full(10, float(code == 621)), voltage_summary(upper_history), voltage_summary(lower_history))
    return np.column_stack(columns)


def donor_indices(code, cutoffs):
    donor = np.empty(len(code), dtype=int)
    for task in TASKS:
        loc = np.flatnonzero(code == task)
        if len(loc) < 2 or not np.all(np.diff(cutoffs[loc]) > 0):
            raise ValueError('Missing or unordered within-task donor support')
        donor[loc] = np.roll(loc, -(len(loc) // 2))
    if np.any(code != code[donor]) or np.any(np.abs(cutoffs[donor] - cutoffs) <= 400):
        raise ValueError('Donor and recipient must have disjoint complete history+target intervals')
    return donor


def from_arrays(time, code, q, upper, lower):
    time, code = np.asarray(time, dtype=np.float64), np.asarray(code)
    if (time.ndim != 1 or code.shape != time.shape or len(time) < 401 or not np.isfinite(time).all()
            or not np.allclose(np.diff(time), 1 / 2000, atol=1e-10, rtol=0)):
        raise ValueError('Source clock, task length or sample spacing failed')
    if q.shape != (len(time), 4) or upper.shape != (32, len(time)) or lower.shape != upper.shape:
        raise ValueError('Source orientation or raw electrode shape differs from the recorded clock')
    boundaries = np.r_[0, np.flatnonzero(code[1:] != code[:-1]) + 1, len(time)]
    xs, ys, codes, cutoffs = [], [], [], []
    excluded = {str(task): {'invalid_history': 0, 'invalid_target': 0} for task in TASKS}
    for a, b in zip(boundaries[:-1], boundaries[1:]):
        task = code[a]
        if task not in TASKS:
            continue
        for t in range(a + 200, b - 200, 200):
            try:
                x = past_tokens(q[t-200:t+1], upper[:, t-199:t+1], lower[:, t-199:t+1], task)
            except ValueError:
                excluded[str(int(task))]['invalid_history'] += 1
                continue
            try:
                endpoints = normalize(q[[t, t+200]])
            except ValueError:
                excluded[str(int(task))]['invalid_target'] += 1
                continue
            xs.append(x)
            ys.append(angle(*endpoints))
            codes.append(int(task))
            cutoffs.append(t)
    codes, cutoffs = np.asarray(codes), np.asarray(cutoffs)
    return Trial(np.asarray(xs), np.asarray(ys), codes, cutoffs, donor_indices(codes, cutoffs), excluded)


def read_trial(path):
    """Open one explicitly chosen verified member; never enumerate participant archives."""
    path = Path(path)
    receipt = json.loads(path.with_suffix('.source.json').read_text())
    person = path.parent.name
    trial = re.fullmatch(r'trial-(\d\d)\.mat', path.name)
    if not trial or not re.fullmatch(r'S\d\d', person):
        raise ValueError('Expected SPERSON/trial-NN.mat')
    member = re.fullmatch(rf'{person}_(\d{{8}})_trial_{trial[1]}\.mat', receipt['member'], re.I)
    if not member or receipt['archive']['name'] != f'Experiment2_{person}_{member[1]}.zip':
        raise ValueError('Experiment, person or trial mismatch in source receipt')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != receipt['member_sha256']:
            raise ValueError('Original member failed SHA256')
        stream.seek(0)
        data = loadmat(stream, simplify_cells=True)['data_estructure']
    info = data['experiment_data']
    meanings = {int(s['task_number']): str(s['task_description']).lower() for s in info['tasks_description']}
    if info['sample_frequency'] != 2000 or any(word not in meanings[code] for code, word in
            [(611, 'static'), (611, 'basic'), (621, 'motion'), (621, 'basic')]):
        raise ValueError('Source frequency or original task meanings differ')
    labels = [str(s).strip() for s in data['quaternions']['labels']]
    if labels != [f'Quaternion ({i})[A.U]' for i in range(1, 5)]:
        raise ValueError('Unexpected original orientation channels')
    trial = from_arrays(info['time_vector'], info['task_vector'], data['quaternions']['data'].T,
                        data['brachial_matrix']['raw_data'], data['lumbar_matrix']['raw_data'])
    trial.member_sha256 = digest
    return trial
