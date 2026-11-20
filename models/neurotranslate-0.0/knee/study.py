"""Refit or score the shared knee-angle head from the checksummed joint-angle exports."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import predict
from knee.adapter import PERIODS, design, features, scramble

TRAIN = tuple(i for i in range(1, 41) if i != 24)
TEST = tuple(range(41, 53))
ARMS = ('raw', 'shared', 'scrambled')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def load_people(cache, people, fit):
    spec = json.loads((HERE / 'protocol.json').read_text())
    manifest = HERE / 'sources.json'
    if digest(manifest) != spec['source']['manifest_sha256']:
        raise ValueError('Source manifest changed')
    src = json.loads(manifest.read_bytes())
    members = {m['subject']: m for m in src['members']}
    for person in people:
        m = members[person]
        relative = f'IMU_S{person}_0.5/Joint_Angles_ZXY.csv'
        if m['path'] != relative or m['split'] != ('train' if fit else 'test'):
            raise ValueError('Unexpected person or survey condition')
        path = cache / relative
        if digest(path) != m['sha256']:
            raise ValueError(f'Unverified angle file for S{person}')
        clean = lambda x: ''.join(ch for ch in x.lower() if ch.isalnum())
        with path.open(encoding='utf-8-sig', newline='') as f:
            headers = [clean(x) for x in next(csv.reader(f))]
        needed = [clean(n) for n in [src['frame_column'], *src['columns']]]
        if any(headers.count(n) != 1 for n in needed):
            raise ValueError('Expected one field for each source angle and the frame counter')
        selected = np.genfromtxt(path, delimiter=',', skip_header=1, usecols=[headers.index(n) for n in needed])
        frame, knees = selected[:, 0], selected[:, 3:5]
        # Retain the preceding study's finite six-channel and frame-eligibility gate.
        finite = np.isfinite(selected).all(axis=1) & (frame == np.floor(frame))
        good_knee = np.isfinite(knees).all(axis=1)
        cut = np.arange(239, len(frame)-15)
        invalid = np.r_[0, (~finite).cumsum()]
        bad_knee = np.r_[0, (~good_knee).cumsum()]
        gaps = np.r_[0, 0, (np.diff(frame) != 1).cumsum()]
        cut = cut[(invalid[cut+16] == invalid[cut-24]) & (bad_knee[cut+1] == bad_knee[cut-239]) &
                  (gaps[cut+16] == gaps[cut-238])]
        if fit:
            cut = cut[::6]
        if len(cut) == 0:
            raise ValueError(f'No eligible windows for S{person}')
        # Calculate the same 60-sample squared differences once per delay per trial.
        costs = []
        for p in PERIODS:
            differences = np.square(knees[p:] - knees[:-p]).sum(axis=1)
            cumulative = np.r_[0., np.cumsum(np.where(np.isfinite(differences), differences, 0.))]
            costs.append(cumulative[cut-p+1] - cumulative[cut-p-59])
        period = np.argmin(costs, axis=0) + PERIODS.start
        windows = np.lib.stride_tricks.sliding_window_view(knees, (240, 2))[:, 0]
        token, extra = features(windows[cut-239], period)
        yield person, token, extra, knees[cut+15]


def standardize(x, weight):
    mean = np.average(x, axis=0, weights=weight)
    scale = np.sqrt(np.average((x-mean)**2, axis=0, weights=weight))
    return mean, np.where(scale < 1e-8, 1., scale)


def design_batched(mode, token, extra, config, encoder):
    return np.concatenate([design(mode, token[i:i+512], extra[i:i+512], config, encoder,
                                  predict.linear, predict.encode) for i in range(0, len(token), 512)])


def fit(cache, parent, output):
    source = json.loads((HERE/'protocol.json').read_text())['source']
    if digest(parent) != source['parent_weights_sha256']:
        raise ValueError('This fit requires the exact released parent checkpoint')
    rows = list(load_people(cache, TRAIN, fit=True))
    n = [len(r[1]) for r in rows]
    weight = np.concatenate([np.full(count, 1 / (len(rows)*count)) for count in n])
    token, extra, actual = [np.concatenate([r[k] for r in rows]) for k in [1, 2, 3]]
    residual = actual - extra[:, :2]
    center, scale = standardize(token.reshape(-1, 6), np.repeat(weight/4, 4))
    tok = (token - center) / scale
    config, weights = predict.read_checkpoint(parent)
    with np.load(parent, allow_pickle=False) as old:
        out = {k:old[k] for k in old.files}
    out.update({'knee.token_center':center, 'knee.token_scale':scale})
    intercept = np.average(residual, axis=0, weights=weight)
    for mode in ARMS:
        encoder = scramble(weights) if mode == 'scrambled' else weights
        x = design_batched(mode, tok, extra, config, encoder)
        mean, std = standardize(x, weight)
        z = (x - mean) / std
        zt = z.T * weight
        coef = np.linalg.solve(zt @ z + .03*np.eye(z.shape[1]), zt @ (residual - intercept))
        for name, value in [('center',mean),('scale',std),('coef',coef),('intercept',intercept)]:
            out['knee.'+mode+'.'+name] = value
    config['knee_angle'] = {'format':1, 'input_frames':240, 'horizon_stored_frames':15,
                            'stored_hz':60, 'modes':['stride', *ARMS]}
    out['configuration'] = np.array(json.dumps(config))
    np.savez_compressed(output, **out)
    print(json.dumps({'people':len(rows), 'windows':int(sum(n)), 'weights_sha256':digest(output)}))


def score(cache, path, output):
    config, weights = predict.read_checkpoint(path)
    if config.get('knee_angle',{}).get('format') != 1:
        raise ValueError('Expected the fitted four-second knee head')
    people = []
    for person, token, extra, actual in load_people(cache, TEST, fit=False):
        anchor = extra[:, :2]
        pred = {'stride':anchor}
        z = (token - weights['knee.token_center'])/weights['knee.token_scale']
        for mode in ARMS:
            encoder = scramble(weights) if mode == 'scrambled' else weights
            x = design_batched(mode, z, extra, config, encoder)
            key = 'knee.' + mode + '.'
            pred[mode] = anchor + ((x - weights[key+'center']) / weights[key+'scale']) @ weights[key+'coef'] + weights[key+'intercept']
        people.append({'person':person,'cutoffs':len(actual),'mae_degrees':{k:np.abs(v-actual).mean(axis=0).tolist() for k,v in pred.items()}})
    means = {k:np.array([np.mean(r['mae_degrees'][k]) for r in people]) for k in ('stride', *ARMS)}
    indices = np.random.default_rng(9913).integers(len(people), size=(10000,len(people)))
    comparisons = {}
    for k in ('stride', 'raw', 'scrambled'):
        d = means['shared'] - means[k]
        comparisons[k] = {'shared_minus_comparator_deg':float(d.mean()), 'shared_wins':int((d<0).sum()),
                          'ties':int((d==0).sum()), 'paired_ci95':np.quantile(d[indices].mean(axis=1), [.025,.975]).tolist()}
    write_json(output, {'checkpoint_sha256':digest(path),'protocol_sha256':digest(HERE/'protocol.json'),
                         'evaluation':'Reused S41–52; all previously assessed eligible cutoffs at 0.5 m/s',
                         'cutoffs':sum(r['cutoffs'] for r in people),'per_person':people,
                         'mae_degrees':{k:float(v.mean()) for k,v in means.items()},
                         'comparisons':comparisons,'shared_advantage_criterion_met':all(c['shared_minus_comparator_deg']<0 and c['shared_wins']>=7 for c in comparisons.values())})
    print(output.read_text().split('"mae_degrees"')[-1][:1350])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fit','score'))
    parser.add_argument('cache', type=Path, help='Directory containing verified IMU_S* folders')
    parser.add_argument('checkpoint', type=Path, help='Exact parent for fit or the newly fitted checkpoint for score')
    parser.add_argument('output', type=Path, help='New NPZ for fit or new JSON results for score')
    args = parser.parse_args()
    if args.checkpoint.resolve() == args.output.resolve():
        parser.error('Select a separate output file')
    (fit if args.action == 'fit' else score)(args.cache, args.checkpoint, args.output)
