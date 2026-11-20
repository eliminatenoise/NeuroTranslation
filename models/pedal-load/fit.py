"""Fixed two-person leave-one-person-out development and final source-fenced fit."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from data import DEV, dataset, sha, subset
from portable import FEATURES, METHODS, VARIANTS, mask, network, predict, predict_tokens, ridge_design, standardize
from score import scoring

HERE = Path(__file__).resolve().parent
PROTOCOL = '133d3c6b85560d6b889ac43d8979e5250d75077443a2c110be0cf42128d09946'
CONFIG = dict(width=12, heads=2, feedforward=24, layers=1, tokens=10, inputs=8, eps=1e-5)
CLOCK_ADDENDUM = '4bb07122c48cbe8a0d44efabd39c076a558796601dfb22558baee5a5f581eefb'
SEED = 6731


def save(path, value):
    path = Path(path)
    temp = path.with_suffix('.writing')
    temp.write_text(json.dumps(value, allow_nan=False, separators=(',', ':'))+'\n')
    temp.replace(path)


class PedalTransformer(nn.Module):
    def __init__(self, width=12, heads=2, feedforward=24, layers=1, tokens=10, inputs=8, eps=1e-5):
        super().__init__()
        if layers != 1 or width % heads:
            raise ValueError('Use one attention block and a width divisible by head count')
        self.heads = heads
        self.embed = nn.Linear(inputs, width)
        self.pos = nn.Parameter(torch.empty(tokens, width))
        nn.init.normal_(self.pos, std=.02)
        self.qkv = nn.Linear(width, width*3)
        self.attn_out = nn.Linear(width, width)
        self.norm1 = nn.LayerNorm(width, eps)
        self.fc1 = nn.Linear(width, feedforward)
        self.fc2 = nn.Linear(feedforward, width)
        self.norm2 = nn.LayerNorm(width, eps)
        self.readout = nn.Linear(width, 1)

    def forward(self, inputs):
        x = self.embed(inputs) + self.pos
        batch, tokens, width = x.shape
        head_width = width // self.heads
        q,k,v = [a.reshape(batch,tokens,self.heads,head_width).transpose(1,2)
                 for a in self.qkv(x).chunk(3, dim=-1)]
        attention = torch.softmax(q @ k.transpose(-1,-2) / head_width**.5, dim=-1)
        x = self.norm1(x + self.attn_out((attention @ v).transpose(1,2).reshape(batch,tokens,width)))
        x = self.norm2(x + self.fc2(torch.relu(self.fc1(x))))
        return self.readout(x[:, -1])[:, 0]


def weights_for(data):
    weights = np.zeros(len(data['y']))
    people = np.unique(data['person'])
    for p in people:
        for c in (0,5):
            keep = (data['person']==p) & (data['condition']==c)
            weights[keep] = 1/(len(people)*2*keep.sum())
    return weights / weights.sum()


def weighted_median(x, weights):
    order = np.argsort(x, kind='stable')
    cum = np.cumsum(weights[order], dtype=np.longdouble)
    return float(x[order[np.searchsorted(cum, cum[-1]/2)]])


def scaler_for(data, w):
    x, y = data['x'], data['y']
    mu = np.average(x.mean(axis=1), axis=0, weights=w)
    sd = np.sqrt(np.average(((x-mu)**2).mean(axis=1), axis=0, weights=w))
    mu[3], sd[3] = 0, 1
    sd[sd < 1e-12] = 1
    y_mean = float(np.average(y, weights=w))
    y_scale = np.sqrt(np.average((y-y_mean)**2, weights=w))
    return dict(mean=mu.tolist(), scale=sd.tolist(), y_mean=y_mean,
                y_scale=float(1 if y_scale < 1e-12 else y_scale))


def ridge(z, y, w, context):
    x = np.column_stack([np.ones(len(y)), ridge_design(z, context)])
    penalty = np.diag([0]+[.01]*(x.shape[1]-1))
    coef = np.linalg.solve(x.T @ (x*w[:, None]) + penalty, x.T @ (w*y))
    return dict(bias=float(coef[0]), weight=coef[1:].tolist())


def tensor(x, device):
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def train(z, target, weights, device='cpu', updates=96):
    torch.manual_seed(SEED)
    net = PedalTransformer(**CONFIG)
    init_hash = hashlib.sha256(b''.join(t.detach().numpy().tobytes() for t in net.parameters())).hexdigest()
    net.to(device)
    x, y, w = (tensor(v, device) for v in (z,target,weights))
    optimizer = torch.optim.AdamW(net.parameters(), lr=.002, weight_decay=.01, betas=(.9,.999), eps=1e-8, foreach=False)
    first_loss = None
    for _ in range(updates):
        optimizer.zero_grad(set_to_none=True)
        loss = (nn.functional.smooth_l1_loss(net(x), y, beta=1., reduction='none') * w).sum()
        if first_loss is None:
            first_loss = float(loss.detach().cpu())
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        pred = net(x).cpu().numpy().astype(float)
    state = {k: t.detach().cpu().tolist() for k,t in net.state_dict().items()}
    parity = float(np.max(np.abs(network(z,state,CONFIG)-pred)))
    if parity > 5e-5:
        raise ValueError(f'Portable prediction disagrees with native PyTorch: {parity}')
    return state, dict(updates=updates, init_sha256=init_hash, weighted_loss_initial=first_loss,
                       weighted_loss_before_last_step=float(loss.detach().cpu()),
                       torch_numpy_max_abs_standardized=parity), pred


def fit(data, device):
    w = weights_for(data)
    scaler = scaler_for(data,w)
    z = standardize(data['x'], scaler)
    y = data['y']; target = (y-scaler['y_mean'])/scaler['y_scale']
    medians = [weighted_median(y[data['condition']==c],w[data['condition']==c]) for c in (0,5)]
    baselines = dict(typical=weighted_median(y,w), typical_condition=medians,
                     ridge_load=ridge(z,target,w,False), ridge_condition=ridge(z,target,w,True))
    model = dict(version=1, protocol_sha256=PROTOCOL, clock_addendum_sha256=CLOCK_ADDENDUM, feature_names=FEATURES, variants=VARIANTS,
                 config=CONFIG, scaler=scaler, baselines=baselines, models={})
    diagnostics = {}
    for variant in VARIANTS:
        model['models'][variant], diagnostics[variant], _ = train(mask(z,variant), target, w, device)
    if len({a['init_sha256'] for a in diagnostics.values()}) != 1:
        raise AssertionError('Unequal initial weights')
    return model, diagnostics


def synthetic_fixture(model):
    j = np.arange(201)
    load = -.031 + .004*np.sin(j*.019) + .00007*j
    emg = .020*np.sin(j*.39) + .003*np.cos(j*.013)
    donor = .014*np.cos(j*.61) - .005*np.sin(j*.023)
    return dict(origin='Mathematical signals, no participant recordings', load=load.tolist(), emg=emg.tolist(),
                donor_emg=donor.tolist(), conditions={str(c): predict(model,load,emg,c,donor) for c in (0,1)})


def setup(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision('highest')
    torch.use_deterministic_algorithms(True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--device', choices=('cpu','cuda'), default='cpu')
    args = parser.parse_args()
    if sha(HERE/'protocol.json') != '34c190d03d0b9e83390a35959589784ad67bdb95a0c37389613a9f9e0d2daa94' or sha(HERE/'clock-addendum.json') != CLOCK_ADDENDUM:
        raise ValueError('Preregistration digest mismatch')
    args.output.mkdir(parents=True, exist_ok=True)
    setup(args.threads)
    data, counts, sources = dataset(args.source, DEV)
    predictions = {name: np.empty(len(data['y'])) for name in METHODS}
    logs = {}
    for person in DEV:
        take = data['person']==person
        fit_on, evaluate = subset(data,~take), subset(data,take)
        model, logs[person] = fit(fit_on,args.device)
        pp = predict_tokens(model,evaluate['x'],evaluate['recent'],evaluate['wrong'])
        for name in METHODS:
            predictions[name][take] = pp[name]
    dev_scores = scoring(data,predictions)
    final, logs['final'] = fit(data,args.device)
    save(args.output/'model.json', final)
    save(args.output/'fixture.json', synthetic_fixture(final))
    fields = ('n_people', 'n_windows', 'balanced_mae', 'per_condition_mae', 'emg_increment', 'unit')
    save(args.output/'development.json', {key:dev_scores[key] for key in fields})
    print(json.dumps(dev_scores['balanced_mae']))


if __name__ == '__main__':
    main()
