# SPDX-License-Identifier: CC0-1.0
"""Fixed readouts of cued finger motion. All five outputs are in personal calibration units."""
import numpy as np
import torch
from torch import nn

MODES = {'cue': slice(0, 60), 'cortex': slice(60, 85), 'aligned': slice(0, 85)}


def moments(x, weights):
    """Population moments; caller supplies one weight per row, summing to one."""
    mean = np.einsum('i,ij->j', weights, x, dtype=np.float64)
    delta = x - mean
    sd = np.sqrt(np.einsum('i,ij,ij->j', weights, delta, delta, dtype=np.float64))
    return mean, np.where(sd < 1e-8, 1., sd)


class Decoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.project = nn.Linear(85, 16)
        self.pos = nn.Parameter(torch.zeros(4, 16))
        self.layer = nn.TransformerEncoderLayer(16, 2, 32, dropout=0.,
                                                activation='gelu', batch_first=True)
        self.out = nn.Linear(16, 5)

    def forward(self, x):
        return self.out(self.layer(self.project(x) + self.pos)[:, -1])


def encoder_input(x, mode, norms):
    if x.ndim != 3 or x.shape[1:] != (4, 85):
        raise ValueError('Expected [packet,4,85] with cue followed by regional features')
    z = np.zeros(x.shape, dtype=np.float32)
    selected = MODES[mode]
    z[..., selected] = (x[..., selected] - norms['mean']) / norms['sd']
    return torch.from_numpy(z)


def fit(x, y, row_weights, family, mode):
    """row_weights sum to one, with equal total mass for each training person."""
    if y.shape != (len(x), 5) or not np.isclose(row_weights.sum(), 1):
        raise ValueError('Invalid training weights or movement targets')
    inputs = x[..., MODES[mode]]
    if family == 'ridge':
        inputs = inputs.reshape(len(y), -1)
        mean, sd = moments(inputs, row_weights)
        z = (inputs-mean) / sd
        intercept = row_weights @ y
        gram = (z.T * row_weights) @ z
        gram.flat[::len(gram)+1] += .05
        beta = np.linalg.solve(gram, (z.T * row_weights) @ (y - intercept))
        return dict(mean=mean, sd=sd, intercept=intercept, beta=beta)
    if family != 'transformer':
        raise ValueError('Unknown readout family')
    tokens = inputs.reshape(-1, inputs.shape[-1])
    mean, sd = moments(tokens, np.repeat(row_weights / 4, 4))
    norms = dict(mean=mean, sd=sd)
    z = encoder_input(x, mode, norms)
    target = torch.from_numpy(y.astype(np.float32))
    importance = torch.from_numpy((len(y)*row_weights).astype(np.float32))
    torch.manual_seed(319)
    net = Decoder()
    opt = torch.optim.AdamW(net.parameters(), lr=.001, weight_decay=.01)
    rng = torch.Generator().manual_seed(319)
    for _ in range(8):
        for idx in torch.randperm(len(z), generator=rng).split(512):
            opt.zero_grad(set_to_none=True)
            per_row = (net(z[idx]) - target[idx]).square().mean(dim=1)
            (importance[idx] * per_row).mean().backward()
            opt.step()
    return {**norms, **{f'param.{k}': a.detach().numpy() for k, a in net.state_dict().items()}}


def predict(x, family, mode, weights):
    if family == 'ridge':
        z = (x[..., MODES[mode]].reshape(len(x), -1) - weights['mean']) / weights['sd']
        pred = z @ weights['beta'] + weights['intercept']
    elif family == 'transformer':
        net = Decoder()
        net.load_state_dict({k[6:]: torch.from_numpy(a.copy()) for k, a in weights.items()
                             if k.startswith('param.')})
        net.eval()
        with torch.inference_mode():
            z = encoder_input(x, mode, weights)
            pred = torch.cat([net(batch) for batch in z.split(512)]).numpy().astype(np.float64)
    else:
        raise ValueError('Unknown readout family')
    return np.maximum(0., pred)


def training_data(people):
    features, targets, weights, tables = [], [], [], []
    for p in people:
        x = p.x[p.recipients].reshape(-1, 4, 85)
        y = p.y[p.recipients]
        features.append(x)
        targets.append(y.reshape(-1, 5))
        weights.append(np.full(len(x), 1 / (len(people)*len(x))))
        cues = p.cues[p.recipients]
        table = np.full((5, 68, 5), np.nan)
        for digit in range(1, 6):
            if (cues == digit).any():
                table[digit-1] = y[cues == digit].mean(axis=0)
        tables.append(table)
    stack = np.stack(tables)
    finite = np.isfinite(stack)
    mean = np.divide(np.nansum(stack, axis=0), np.maximum(finite.sum(axis=0), 1))
    fallback = np.mean([a.mean(axis=0) for a in targets], axis=0)
    table = np.where(finite.any(axis=0), mean, fallback)
    return (np.concatenate(features), np.concatenate(targets), np.concatenate(weights), table)


def load_weights(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}
