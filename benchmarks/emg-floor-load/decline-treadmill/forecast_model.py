"""Fit and replay matched short and long EMG histories for two force plates."""

import re
from time import perf_counter

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


MUSCLES = 16
LONG_BINS = 20
THRESHOLD_NS = 1.0


class RepeatedAttention(nn.Module):
    def __init__(self, passes):
        super().__init__()
        self.passes = passes
        self.project = nn.Linear(MUSCLES, 32)
        self.positions = nn.Parameter(torch.zeros(LONG_BINS, 32))
        self.block = nn.TransformerEncoderLayer(32, 4, 64, batch_first=True,
                                                activation='gelu', norm_first=True, dropout=0)
        self.readout = nn.Sequential(nn.LayerNorm(32), nn.Linear(32, 4))

    def forward(self, values):
        hidden = self.project(values) + self.positions[-values.shape[1]:]
        for _ in range(self.passes):
            hidden = self.block(hidden)
        return self.readout(hidden[:, -1])


def method_model(name):
    match = re.fullmatch(r'(affine|attention)_(200|1000)(?:_p([135]))?', name)
    if match is None:
        raise ValueError('Unknown forecast method.')
    architecture, milliseconds, passes = match.groups()
    bins = int(milliseconds) // 50
    if architecture == 'affine' and passes is None:
        return bins, nn.Sequential(nn.Flatten(), nn.Linear(bins * MUSCLES, 4))
    if architecture == 'attention' and passes is not None:
        return bins, RepeatedAttention(int(passes))
    raise ValueError('Forecast method and pass count disagree.')


def init_cpu(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision('highest')
    torch.use_deterministic_algorithms(True)


def checked_input(history):
    data = np.asarray(history, dtype=np.float64)
    if data.ndim != 3 or data.shape[1:] != (LONG_BINS, MUSCLES) or not len(data) or not np.isfinite(data).all():
        raise ValueError('Expected one finite 20 by 16 log-voltage history per forecast.')
    return data


def participant_weight(people):
    _, inverse, counts = np.unique(people, return_inverse=True, return_counts=True)
    return 1.0 / (len(counts) * counts[inverse])


def weighted_median(values, weights):
    order = np.argsort(values, kind='stable')
    cumulative = np.cumsum(weights[order])
    return values[order[np.searchsorted(cumulative, cumulative[-1] * .5)]]


def fit(history, target, people, protocol):
    data = checked_input(history)
    target = np.asarray(target, dtype=np.float64)
    if target.shape != (len(data), 2) or not np.isfinite(target).all() or len(people) != len(data):
        raise ValueError('Each history must have two finite plate outcomes and a fitting participant.')
    weights = participant_weight(people)
    row_weight = weights[:, None, None] / LONG_BINS
    center = (row_weight * data).sum(axis=(0, 1))
    scale = np.maximum(1e-6, np.sqrt((row_weight * (data - center) ** 2).sum(axis=(0, 1))))
    event = target > THRESHOLD_NS
    target_scale = float(np.median(target[event]))
    if not np.isfinite(target_scale) or target_scale <= THRESHOLD_NS:
        raise ValueError('The fitting data have no usable loaded impulse scale.')
    output = {'center': center, 'scale': scale, 'target_scale': np.asarray(target_scale),
              'fit_median': np.array([weighted_median(column, weights) for column in target.T]),
              'training_probability': (weights[:, None] * event).sum(axis=0)}
    features = torch.from_numpy(((data - center) / scale).astype(np.float32))
    impulse = torch.from_numpy((target / target_scale).astype(np.float32))
    loaded = torch.from_numpy(event.astype(np.float32))
    per_row = torch.from_numpy((len(data) * weights).astype(np.float32))
    runs = []
    batch = protocol['batch_size']
    for name in protocol['methods'][2:]:
        for seed in protocol['seeds']:
            started = perf_counter()
            torch.manual_seed(seed)
            bins, model = method_model(name)
            order = torch.Generator().manual_seed(seed + 100)
            optim = torch.optim.AdamW(model.parameters(), lr=protocol['learning_rate'], weight_decay=protocol['weight_decay'])
            epochs = []
            for _ in range(protocol['epochs']):
                total_loss = 0.
                for ids in torch.randperm(len(data), generator=order).split(batch):
                    raw = model(features[ids, -bins:, :])
                    row_error = (raw[:, :2] - impulse[ids]).abs().mean(dim=1)
                    load_error = F.binary_cross_entropy_with_logits(raw[:, 2:], loaded[ids], reduction='none').mean(dim=1)
                    loss = (per_row[ids] * (row_error + .25 * load_error)).sum() / batch
                    optim.zero_grad(set_to_none=True)
                    loss.backward()
                    optim.step()
                    total_loss += float(loss.detach()) * batch
                epochs.append(total_loss / len(data))
            if not np.isfinite(epochs).all():
                raise ValueError(f'Training diverged for {name}, seed {seed}.')
            for key, value in model.state_dict().items():
                output[f'{name}.{seed}.{key}'] = value.detach().cpu().numpy().copy()
            runs.append({'model': name, 'seed': seed, 'parameters': sum(p.numel() for p in model.parameters()),
                         'fit_loss_by_epoch': epochs, 'elapsed_seconds': perf_counter() - started})
            print(name, seed, f'{epochs[-1]:.5f}', flush=True)
    return output, runs


def predict(history, weights, protocol):
    data = checked_input(history)
    tensor = torch.from_numpy(((data - weights['center']) / weights['scale']).astype(np.float32))
    n = len(data)
    impulse = {'zero': np.zeros((n, 2)), 'fit_median': np.broadcast_to(weights['fit_median'], (n, 2)).copy()}
    probability = {name: np.broadcast_to(weights['training_probability'], (n, 2)).copy() for name in impulse}
    with torch.inference_mode():
        for name in protocol['methods'][2:]:
            force_runs, contact_runs = [], []
            for seed in protocol['seeds']:
                bins, model = method_model(name)
                model.load_state_dict({k: torch.from_numpy(weights[f'{name}.{seed}.{k}']) for k in model.state_dict()})
                model.eval()
                raw = torch.cat([model(rows[:, -bins:, :]) for rows in tensor.split(256)])
                force_runs.append(raw[:, :2].numpy().astype(np.float64) * float(weights['target_scale']))
                contact_runs.append(raw[:, 2:].sigmoid().numpy().astype(np.float64))
            impulse[name] = np.mean(force_runs, axis=0)
            probability[name] = np.mean(contact_runs, axis=0)
    if not all(np.isfinite(a).all() for a in (*impulse.values(), *probability.values())):
        raise ValueError('A stored model gave a nonfinite forecast.')
    return impulse, probability
