"""Reproduce the four development folds and development-only final back-sensor predictor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import numpy as np
import scipy
import torch
from torch import nn

from extract import read_trial, FEATURES, TASKS
from portable import standardized, masked, ridge_design, predict, VARIANTS, BASELINES
from score import predictions, person_scores, summarize

HERE = Path(__file__).resolve().parent
PROTOCOL_HASH = '5afb7728808ca45480ceea014e5cd72ae2a95d1bc063efa9e3e23dcd48f8f3b2'
PEOPLE = ('S01', 'S02', 'S03', 'S05')
CONFIG = {'width': 16, 'heads': 2, 'feedforward': 32, 'layers': 1, 'eps': 1e-5}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.writing')
    tmp.write_text(json.dumps(obj, allow_nan=False, separators=(',', ':')) + '\n')
    tmp.replace(path)


class RotationTransformer(nn.Module):
    """A direct bounded-horizon regressor over the 10 prior bins."""
    def __init__(self, width=16, heads=2, feedforward=32, layers=1, eps=1e-5):
        super().__init__()
        if layers != 1 or width % heads:
            raise ValueError('One attention block with width divisible by heads required')
        self.heads = heads
        self.embed = nn.Linear(9, width)
        self.pos = nn.Parameter(torch.empty(10, width))
        nn.init.normal_(self.pos, std=.02)
        self.qkv = nn.Linear(width, 3 * width)
        self.attn_out = nn.Linear(width, width)
        self.norm1 = nn.LayerNorm(width, eps=eps)
        self.fc1 = nn.Linear(width, feedforward)
        self.fc2 = nn.Linear(feedforward, width)
        self.norm2 = nn.LayerNorm(width, eps=eps)
        self.readout = nn.Linear(width, 1)

    def forward(self, x, recent):
        x = self.embed(x) + self.pos
        n, t, w = x.shape
        q, k, v = [a.reshape(n, t, self.heads, w // self.heads).transpose(1, 2)
                   for a in self.qkv(x).chunk(3, dim=-1)]
        attn = torch.softmax(q @ k.transpose(-1, -2) / (w // self.heads) ** .5, dim=-1)
        values = (attn @ v).transpose(1, 2).reshape(n, t, w)
        x = self.norm1(x + self.attn_out(values))
        x = self.norm2(x + self.fc2(torch.relu(self.fc1(x))))
        return recent + self.readout(x[:, -1]).squeeze(-1)


def fit_scaler(x, groups):
    _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    weights = 1.0 / counts[inverse]
    weights /= weights.mean()
    token_means = x.mean(axis=1)
    mean = np.average(token_means, weights=weights, axis=0)
    scale = np.sqrt(np.average(((x - mean) ** 2).mean(axis=1), weights=weights, axis=0))
    scale[scale < 1e-8] = 1
    mean[2], scale[2] = 0, 1
    return {'mean': mean.tolist(), 'scale': scale.tolist()}, weights


def fit_ridge(design, residual, weights):
    with_intercept = np.column_stack([np.ones(len(design)), design])
    w = weights / weights.sum()
    penalty = np.diag([0] + [.01] * design.shape[1])
    coef = np.linalg.solve(with_intercept.T @ (w[:, None] * with_intercept) + penalty,
                           with_intercept.T @ (w * residual))
    return {'bias': float(coef[0]), 'weight': coef[1:].tolist()}


def tensor(x):
    return torch.as_tensor(x, dtype=torch.float32)


def train_variant(z, recent, y, weights, config=CONFIG, epochs=18):
    torch.manual_seed(1941)
    generator = torch.Generator().manual_seed(1941)
    net = RotationTransformer(**config)
    initial = {name: param.detach().clone() for name, param in net.named_parameters()}
    optimizer = torch.optim.AdamW(net.parameters(), lr=.002, betas=(.9, .999), eps=1e-8, weight_decay=.01)
    z, recent, y, weights = map(tensor, (z, recent, y, weights))
    log = []
    for epoch in range(epochs):
        losses = []
        for ix in torch.randperm(len(z), generator=generator).split(96):
            optimizer.zero_grad(set_to_none=True)
            raw = net(z[ix], recent[ix])
            loss = (nn.functional.smooth_l1_loss(raw, y[ix], reduction='none', beta=1.) * weights[ix]).mean()
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()) * len(ix))
        log.append(sum(losses) / len(z))
    if not np.isfinite(log).all():
        raise RuntimeError('Nonfinite training loss')
    net.update_l2 = {name: float(torch.linalg.vector_norm(param.detach() - initial[name]))
                     for name, param in net.named_parameters()}
    return net, log


def synthetic():
    # Transparent hypothetical histories; independent of every volunteer's data.
    histories = []
    for scenario in range(3):
        j = np.arange(1, 11)
        step = .01 * j if scenario == 0 else .14 + .05 * np.cos(j + scenario)
        sites = np.stack([np.log1p((1 + scenario) * (k + 1) + .3 * j) for k in range(6)], axis=1)
        histories.append(np.column_stack([step, np.cumsum(step), np.full(10, int(scenario > 0)), sites]))
    return np.stack(histories)


def fit_bundle(data, people):
    raw = np.concatenate([trial.x for p in people for trial in data[p]])
    y = np.concatenate([trial.y for p in people for trial in data[p]])
    code = np.concatenate([trial.code for p in people for trial in data[p]])
    group = np.concatenate([i * 1000 + trial.code for i, p in enumerate(people) for trial in data[p]])
    scaler, weights = fit_scaler(raw, group)
    z = standardized(raw, scaler)
    recent = raw[:, -1, 1]
    medians = {str(t): float(np.median(y[code == t])) for t in TASKS}
    model = {'format_version': 1, 'protocol_sha256': PROTOCOL_HASH, 'feature_names': FEATURES, 'config': CONFIG,
             'input': 'Ten chronological 10 ms bins at the cutoff, source degree and raw µV-derived features.',
             'target': 'Unsigned relative back-mounted device rotation in degrees from cutoff to 100 ms later.',
             'scaler': scaler, 'models': {}, 'baselines': {'task_median': medians,
             'ridge_motion': fit_ridge(ridge_design(z), y - recent, weights)}}
    logs = {}
    for method in VARIANTS:
        start = time.perf_counter()
        net, losses = train_variant(masked(z, method), recent, y, weights)
        model['models'][method] = {k: v.detach().tolist() for k, v in net.state_dict().items()}
        # Compare every training input and independent synthetic inputs to the portable route.
        probe = np.concatenate([raw, synthetic()])
        with torch.no_grad():
            native = net(tensor(masked(standardized(probe, scaler), method)), tensor(probe[:, -1, 1])).clip(0, 180).numpy()
        deviation = float(np.max(np.abs(native - predict(model, probe, method))))
        if deviation > 2e-5:
            raise ValueError(f'Portable prediction error {deviation:g} degrees')
        logs[method] = {'seconds': time.perf_counter()-start, 'epoch_weighted_loss': losses,
                        'max_portable_error_deg': deviation, 'parameter_update_l2': net.update_l2,
                        'parameters': sum(v.numel() for v in net.parameters())}
    probe = synthetic()
    model['parity'] = {'description': 'Three synthetic histories in original feature units.', 'tokens': probe.tolist(),
                       'predictions_deg': {m: predict(model, probe, m).tolist() for m in BASELINES + VARIANTS},
                       'absolute_tolerance_deg': 2e-5}
    return model, logs


def train(cache, out, threads=1):
    if hashlib.sha256((HERE / 'protocol.json').read_bytes()).hexdigest() != PROTOCOL_HASH:
        raise ValueError('Prespecified protocol seal differs')
    existing = [out / name for name in ('model.json', 'development.json', 'seal.json')]
    existing.extend(out / 'private' / f'fold-{p}.json' for p in PEOPLE)
    if any(path.exists() for path in existing):
        raise FileExistsError('Choose a fresh output directory to preserve existing fits')
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    start = time.perf_counter()
    data = {p: [read_trial(cache / p / f'trial-{n:02}.mat') for n in (2, 3)] for p in PEOPLE}
    logs = {'inputs': {p: [trial.member_sha256 for trial in data[p]] for p in PEOPLE},
            'load_seconds': time.perf_counter()-start, 'fits': {}}
    people = {}
    for hold in PEOPLE:
        model, log = fit_bundle(data, [p for p in PEOPLE if p != hold])
        dump(out / 'private' / f'fold-{hold}.json', model)
        logs['fits'][hold] = log
        people[hold] = person_scores(data[hold], [predictions(model, trial) for trial in data[hold]])
        print('Completed development fold', hold, flush=True)
    model, log = fit_bundle(data, PEOPLE)
    logs['fits']['final'] = log
    dump(out / 'model.json', model)
    dump(out / 'development.json', {'stage': 'Four leave-one-development-person-out folds',
         'protocol_sha256': PROTOCOL_HASH, **summarize(people)})
    dump(out / 'private' / 'person-scores.json', people)
    logs.update({'complete_seconds': time.perf_counter()-start, 'python': platform.python_version(),
                 'numpy': np.__version__, 'scipy': scipy.__version__, 'torch': torch.__version__,
                 'intraop': torch.get_num_threads(), 'interop': torch.get_num_interop_threads(),
                 'threads_env': {k: os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}})
    dump(out / 'private' / 'training-run.json', logs)
    print('Sealable final model and development report written', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('development_cache', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--threads', default=1, type=int)
    args = ap.parse_args()
    train(args.development_cache, args.out, args.threads)
