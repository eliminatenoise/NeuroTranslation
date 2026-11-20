"""Portable NumPy inference from nested JSON arrays; inputs are past-only raw tokens."""
import numpy as np

VARIANTS = ('motion', 'upper', 'lower', 'full')
BASELINES = ('zero', 'constant_speed', 'task_median', 'ridge_motion')
METHODS = BASELINES + VARIANTS + ('wrong',)


def standardized(raw, scaler):
    x = np.asarray(raw, dtype=np.float64)
    if x.ndim != 3 or x.shape[1:] != (10, 9) or not np.isfinite(x).all():
        raise ValueError('Expected finite windows × 10 × 9 raw features')
    if not np.all((x[:, :, 2] == 0) | (x[:, :, 2] == 1)) or np.any(x[:, :, 2] != x[:, :1, 2]):
        raise ValueError('Current task must be static (0) or motion (1) throughout each history')
    return np.clip((x - scaler['mean']) / scaler['scale'], -8, 8)


def masked(x, variant):
    if variant not in VARIANTS:
        raise ValueError(f'Unknown trained variant {variant}')
    out = x.copy()
    if variant in ('motion', 'lower'):
        out[:, :, 3:6] = 0
    if variant in ('motion', 'upper'):
        out[:, :, 6:9] = 0
    return out


def ridge_design(z):
    return np.column_stack([z[:, :, :2].reshape(len(z), 20), z[:, 0, 2]])


def linear(x, weights, name):
    return x @ np.asarray(weights[name + '.weight']).T + weights[name + '.bias']


def layer_norm(x, weights, name, eps):
    centered = x - x.mean(axis=-1, keepdims=True)
    return centered / np.sqrt((centered ** 2).mean(axis=-1, keepdims=True) + eps) * weights[name + '.weight'] + weights[name + '.bias']


def predict(model, raw, method='full'):
    """Compute degrees for a batch. For the wrong-pair control supply donor voltage to full."""
    raw = np.asarray(raw, dtype=np.float64)
    z = standardized(raw, model['scaler'])
    recent = raw[:, -1, 1]
    if method == 'zero':
        return np.zeros(len(raw))
    if method == 'constant_speed':
        return recent.copy()
    if method == 'task_median':
        return np.where(raw[:, 0, 2] == 1, model['baselines']['task_median']['621'],
                        model['baselines']['task_median']['611'])
    if method == 'ridge_motion':
        ridge = model['baselines']['ridge_motion']
        return np.clip(recent + ridge_design(z) @ ridge['weight'] + ridge['bias'], 0, 180)
    x = masked(z, method)
    weights = model['models'][method]
    cfg = model['config']
    x = linear(x, weights, 'embed') + weights['pos']
    batch, tokens, width = x.shape
    heads = cfg['heads']
    def heads_first(a):
        return a.reshape(batch, tokens, heads, width // heads).transpose(0, 2, 1, 3)
    q, k, v = [heads_first(a) for a in np.split(linear(x, weights, 'qkv'), 3, axis=-1)]
    logits = q @ k.swapaxes(-1, -2) / np.sqrt(width // heads)
    attn = np.exp(logits - logits.max(axis=-1, keepdims=True))
    values = (attn / attn.sum(axis=-1, keepdims=True)) @ v
    values = values.transpose(0, 2, 1, 3).reshape(batch, tokens, width)
    x = layer_norm(x + linear(values, weights, 'attn_out'), weights, 'norm1', cfg['eps'])
    ff = linear(np.maximum(linear(x, weights, 'fc1'), 0), weights, 'fc2')
    x = layer_norm(x + ff, weights, 'norm2', cfg['eps'])
    return np.clip(recent + linear(x[:, -1], weights, 'readout')[:, 0], 0, 180)
