"""Fit only the four development people; export final weights and fold diagnostics."""
import argparse
import os
from pathlib import Path
from time import perf_counter
from resource import getrusage, RUSAGE_SELF
import numpy as np
import torch
from torch import nn

from portable import FEATURES, histories, standardize, forecast, predict_all
from study import PROTOCOL, HERE, DEV, digest, load_person, save, score_person, summarize

CONFIG = {'width': 16, 'heads': 2, 'feedforward': 32, 'eps': 1e-5}


class FascicleTransformer(nn.Module):
    def __init__(self, width=16, heads=2, feedforward=32, eps=1e-5):
        super().__init__()
        if width % heads:
            raise ValueError('Model width must be divisible by the number of heads')
        self.heads = heads
        self.embed = nn.Linear(4, width)
        self.pos = nn.Parameter(torch.empty(5, width))
        nn.init.normal_(self.pos, std=.02)
        self.qkv = nn.Linear(width, 3*width)
        self.attn_out = nn.Linear(width, width)
        self.norm1 = nn.LayerNorm(width, eps=eps)
        self.fc1 = nn.Linear(width, feedforward)
        self.fc2 = nn.Linear(feedforward, width)
        self.norm2 = nn.LayerNorm(width, eps=eps)
        self.readout = nn.Linear(width, 1)

    def forward(self, tokens):
        x = self.embed(tokens) + self.pos
        n, t, width = x.shape
        q, k, v = [a.reshape(n, t, self.heads, width // self.heads).transpose(1, 2)
                   for a in self.qkv(x).chunk(3, dim=-1)]
        attn = torch.softmax(q @ k.transpose(-1, -2) / (width // self.heads)**.5, dim=-1)
        value = (attn @ v).transpose(1, 2).reshape(n, t, width)
        x = self.norm1(x + self.attn_out(value))
        x = self.norm2(x + self.fc2(torch.relu(self.fc1(x))))
        return self.readout(x[:, -1]).squeeze(-1)


def learn(z, y, w, device='cpu', updates=120, cfg=CONFIG):
    torch.manual_seed(2718)
    model = FascicleTransformer(**cfg).to(device)
    initial = {k: v.detach().clone() for k, v in model.named_parameters()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=.003, betas=(.9, .999), eps=1e-8, weight_decay=.01)
    z, y, w = (torch.as_tensor(v, dtype=torch.float32, device=device) for v in (z, y, w))
    losses = []
    for _ in range(updates):
        optimizer.zero_grad(set_to_none=True)
        loss = (nn.functional.smooth_l1_loss(model(z), y, reduction='none', beta=1.0) * w).sum()
        loss.backward()
        optimizer.step()
        losses.append(loss.detach())
    updates_l2 = {k: float(torch.linalg.vector_norm(v.detach()-initial[k]).cpu()) for k, v in model.named_parameters()}
    losses = torch.stack(losses).cpu().numpy()
    if not np.isfinite(losses).all() or not all(np.isfinite(list(updates_l2.values()))):
        raise ArithmeticError('Nonfinite training state')
    return model.eval(), {'updates': updates, 'first_loss': float(losses[0]), 'last_loss': float(losses[-1]),
                          'update_l2': updates_l2, 'parameters': sum(v.numel() for v in model.parameters())}


def weighted_median(y, w):
    order = np.argsort(y, kind='stable')
    index = np.searchsorted(np.cumsum(w[order]), .5*w.sum(), side='left')
    return float(y[order[index]])


def synthetic_cases():
    k = np.arange(21, dtype=np.float64)
    a = k[:-1]
    return [
        {'name': 'constant', 'length_mm': np.full(21, 28.).tolist(), 'angle_deg': np.full(20, 10.).tolist(),
         'other_angle_deg': np.linspace(8., 12., 20).tolist()},
        {'name': 'shortening', 'length_mm': (32. - .07*k).tolist(), 'angle_deg': (10. + .12*a).tolist(),
         'other_angle_deg': (12. - .1*a).tolist()},
        {'name': 'turn', 'length_mm': (27. + .02*k + .6*np.sin(.26*k)).tolist(),
         'angle_deg': (9.5 + .6*np.cos(.23*a)).tolist(), 'other_angle_deg': (9. + .7*np.sin(.23*a)).tolist()}]


def fit_bundle(people, data, probes):
    trials = [t for p in people for t in data[p]]
    x = np.concatenate([histories(t.length, t.angle) for t in trials])
    y = np.concatenate([t.target for t in trials])
    w = np.concatenate([np.full(len(t.target), 1./(len(trials)*len(t.target))) for t in trials])
    x_mean = np.average(x.mean(axis=1), weights=w, axis=0)
    x_sd = np.maximum(np.average(((x-x_mean)**2).mean(axis=1), weights=w, axis=0)**.5, 1e-6)
    y_mean = float(np.average(y, weights=w))
    y_sd = float(max(np.average((y-y_mean)**2, weights=w)**.5, 1e-6))
    scaler = {'x_mean': x_mean.tolist(), 'x_sd': x_sd.tolist(), 'y_mean': y_mean, 'y_sd': y_sd}
    z = standardize(x, scaler, 'full')
    y = (y-y_mean)/y_sd
    design = np.column_stack([np.ones(len(z)), z[..., :2].reshape(len(z), 10)])
    ridge = np.linalg.solve(design.T @ (design*w[:, None]) + np.diag([0]+[.01]*10), design.T @ (y*w))
    out = {'format_version': 1, 'config': CONFIG, 'protocol_sha256': PROTOCOL, 'feature_names': FEATURES,
           'target': 'Signed later minus current tracked length in mm after 10 original tracking steps.',
           'scaler': scaler, 'baselines': {'typical': weighted_median(np.concatenate([t.target for t in trials]), w),
           'ridge': {'bias': float(ridge[0]), 'weight': ridge[1:].tolist()}}, 'models': {}}
    report = {}
    probe = np.concatenate([x, np.stack([histories(p['length_mm'], p['angle_deg']) for p in probes])])
    for variant in ('length', 'full'):
        model, report[variant] = learn(standardize(x, scaler, variant), y, w)
        out['models'][variant] = {k: v.detach().cpu().tolist() for k, v in model.state_dict().items()}
        with torch.no_grad():
            native = model(torch.tensor(standardize(probe, scaler, variant), dtype=torch.float32)).double().numpy()*y_sd + y_mean
        error = float(np.max(np.abs(native-forecast(out, probe, variant))))
        report[variant]['max_export_error_mm'] = error
        if error >= 1e-4:
            raise ArithmeticError('NumPy/Torch mismatch')
    return out, report


def train(cache, out, threads):
    if digest(HERE / 'PROTOCOL.md') != PROTOCOL:
        raise ValueError('Prospective protocol seal changed')
    if any((out / name).exists() for name in ('model.json', 'development.json', 'seal.json', 'private/development-person.json')) or list((out/'private').glob('*.model.json')):
        raise FileExistsError('Training requires a fresh output path')
    started = perf_counter()
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    data = {p: load_person(cache, p) for p in DEV}
    if len({t.source['mat_sha256'] for trials in data.values() for t in trials}) != 8:
        raise ValueError('Shared sources between recordings')
    probes = synthetic_cases()
    rows, training = {}, {}
    for p in DEV:
        model, training[p] = fit_bundle([q for q in DEV if q != p], data, probes)
        save(out / 'private' / (p + '.model.json'), model)
        rows[p] = score_person(model, data[p])
    save(out / 'private/development-person.json', rows)
    model, training['all_four'] = fit_bundle(DEV, data, probes)
    save(out / 'model.json', model)
    for probe in probes:
        pred = predict_all(model, probe['length_mm'], probe['angle_deg'], probe['other_angle_deg'])
        probe['predictions_mm'] = {k: float(v[0]) for k, v in pred.items()}
    save(out / 'synthetic.json', {'origin': 'Invented histories independent of the recordings.', 'cases': probes})
    result = summarize(rows)
    result['study'] = 'Leave each development person out. No final assessment participant entered these fits.'
    result['largest_numpy_torch_difference_mm'] = max(v['max_export_error_mm'] for variants in training.values() for v in variants.values())
    save(out / 'development.json', result)
    save(out / 'private/fit-trace.json', {'fits': training, 'torch': torch.__version__, 'numpy': np.__version__,
         'intraop': torch.get_num_threads(), 'interop': torch.get_num_interop_threads(),
         'affinity': sorted(os.sched_getaffinity(0)), 'maxrss_kib': getrusage(RUSAGE_SELF).ru_maxrss,
         'seconds_through_export': perf_counter()-started})
    files = ['model.json', 'development.json', 'synthetic.json']
    sources = ['PROTOCOL.md', 'portable.py', 'study.py', 'fit.py', 'assess.py']
    save(out / 'seal.json', {'protocol_sha256': PROTOCOL, 'files': {name: digest(out/name) for name in files},
         'code': {name: digest(HERE/name) for name in sources},
         'development_sources': [t.source for p in DEV for t in data[p]]})
    print('Sealed four-person development assessment and final weights.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('development_cache', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args()
    train(args.development_cache, args.out, args.threads)
