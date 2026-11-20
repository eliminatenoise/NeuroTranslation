"""Infer signed fascicle length change (mm) ten tracking steps ahead. NumPy only."""
import argparse
import json
from pathlib import Path
import numpy as np

METHODS = ('zero', 'recent', 'typical', 'ridge', 'length', 'full', 'wrong', 'projection')
FEATURES = ('ending_length_mm', 'change_length_mm', 'mean_earlier_pennation_deg', 'change_earlier_pennation_deg')


def histories(length, angle):
    """Build five chronological tokens from 21 lengths and 20 earlier angles."""
    length, angle = map(lambda a: np.asarray(a, dtype=np.float64), (length, angle))
    if length.shape[-1:] != (21,) or angle.shape != (*length.shape[:-1], 20):
        raise ValueError('Expected 21 lengths and 20 earlier angles per example')
    if not np.isfinite(length).all() or not np.isfinite(angle).all():
        raise ValueError('Expected finite observations from a contiguous tracker segment')
    angle_bins = angle.reshape(*angle.shape[:-1], 5, 4)
    return np.stack((length[..., 4::4], np.diff(length[..., ::4], axis=-1),
                     angle_bins.mean(axis=-1), angle_bins[..., -1] - angle_bins[..., 0]), axis=-1)


def standardize(tokens, scaler, variant):
    z = (tokens - scaler['x_mean']) / scaler['x_sd']
    if variant == 'length':
        z[..., 2:] = 0
    return z


def linear(x, w, name):
    return x @ np.asarray(w[name + '.weight']).T + w[name + '.bias']


def norm(x, w, name, eps):
    centered = x - x.mean(axis=-1, keepdims=True)
    return centered / np.sqrt((centered**2).mean(axis=-1, keepdims=True) + eps) * w[name + '.weight'] + w[name + '.bias']


def forecast(model, tokens, variant='full'):
    """Accept one or a batch of raw five-by-four histories; always return a vector in mm."""
    if variant not in ('length', 'full', 'ridge'):
        raise ValueError('Expected length, full or ridge')
    tokens = np.asarray(tokens, dtype=np.float64)
    if tokens.ndim == 2:
        tokens = tokens[None]
    if tokens.ndim != 3 or tokens.shape[1:] != (5, 4) or not np.isfinite(tokens).all():
        raise ValueError('Expected finite batches of five chronological four-feature bins')
    sc = model['scaler']
    z = standardize(tokens, sc, variant)
    if variant == 'ridge':
        ridge = model['baselines']['ridge']
        y = z[..., :2].reshape(len(z), 10) @ ridge['weight'] + ridge['bias']
    else:
        w = model['models'][variant]
        cfg = model['config']
        x = linear(z, w, 'embed') + w['pos']
        n, t, width = x.shape
        h = cfg['heads']
        q, k, v = [a.reshape(n, t, h, width // h).transpose(0, 2, 1, 3)
                   for a in np.split(linear(x, w, 'qkv'), 3, axis=-1)]
        logits = q @ k.swapaxes(-1, -2) / np.sqrt(width // h)
        attn = np.exp(logits - logits.max(axis=-1, keepdims=True))
        attn /= attn.sum(axis=-1, keepdims=True)
        values = (attn @ v).transpose(0, 2, 1, 3).reshape(n, t, width)
        x = norm(x + linear(values, w, 'attn_out'), w, 'norm1', cfg['eps'])
        x = norm(x + linear(np.maximum(linear(x, w, 'fc1'), 0), w, 'fc2'), w, 'norm2', cfg['eps'])
        y = linear(x[:, -1], w, 'readout')[:, 0]
    return y * sc['y_sd'] + sc['y_mean']


def projected_change(length, angle):
    # Last eligible angle is i-1; corresponding length is second from the end.
    current, previous = np.cos(np.deg2rad(angle[..., -1])), np.cos(np.deg2rad(angle[..., -11]))
    delta = length[..., -2] * current - length[..., -12] * previous
    return np.divide(delta, current, out=np.full_like(delta, np.nan), where=np.abs(current) >= .1)


def predict_all(model, length, angle, other_angle):
    """A donor must come from a separate recording for the retrospective control."""
    length, angle, other_angle = [np.atleast_2d(np.asarray(a, dtype=np.float64)) for a in (length, angle, other_angle)]
    x = histories(length, angle)
    return {'zero': np.zeros(len(x)), 'recent': length[:, -1] - length[:, -11],
            'typical': np.full(len(x), model['baselines']['typical']), 'ridge': forecast(model, x, 'ridge'),
            'length': forecast(model, x, 'length'), 'full': forecast(model, x, 'full'),
            'wrong': forecast(model, histories(length, other_angle), 'full'), 'projection': projected_change(length, angle)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('input', type=Path, help='JSON with length_mm and angle_deg. A length-only call may omit angle_deg.')
    parser.add_argument('--variant', choices=('length', 'full', 'ridge'), default='full')
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    length = np.asarray(data['length_mm'])
    if args.variant in ('length', 'ridge'):
        angle = np.zeros((*length.shape[:-1], 20))
    else:
        angle = data['angle_deg']
    pred = forecast(json.loads(args.model.read_text()), histories(length, angle), args.variant)
    print(json.dumps({'signed_change_mm': pred.tolist(), 'tracking_steps_ahead': 10}, allow_nan=False))
