"""Numerical inference from 201 raw historical samples. Requires only NumPy."""
import numpy as np

FEATURES = ['load_end', 'load_step', 'load_from_start', 'angle5', 'emg_mean',
            'emg_sd', 'emg_diff_rms', 'emg_sd_times_load_step']
VARIANTS = {'load': [0, 1, 2], 'load_condition': [0, 1, 2, 3],
            'emg_condition': [3, 4, 5, 6], 'full': list(range(8))}
BASELINES = ['zero', 'continue', 'typical', 'typical_condition', 'ridge_load', 'ridge_condition']
METHODS = BASELINES + list(VARIANTS) + ['wrong']


def features(load, emg, condition):
    load, emg = (np.asarray(a, dtype=np.float64) for a in (load, emg))
    if load.shape != emg.shape or load.ndim not in (1, 2) or load.shape[-1] != 201:
        raise ValueError('Supply aligned 201-sample histories or a batch thereof')
    if not (np.isfinite(load).all() and np.isfinite(emg).all()):
        raise ValueError('Nonfinite input history')
    if condition not in (0, 1):
        raise ValueError('Expected source condition indicator 0 or 1')
    starts = np.arange(0, 200, 20)
    ends = starts + 20
    frames = emg[..., starts[:, None] + np.arange(21)]
    load_step = load[..., ends] - load[..., starts]
    emg_sd = frames.std(axis=-1)
    return np.stack([load[..., ends], load_step, load[..., ends] - load[..., :1],
                     np.full_like(load_step, condition), frames.mean(axis=-1), emg_sd,
                     np.sqrt(np.mean(np.diff(frames, axis=-1) ** 2, axis=-1)),
                     emg_sd * load_step], axis=-1)


def standardize(tokens, scaler):
    return np.clip((tokens - scaler['mean']) / scaler['scale'], -8, 8)


def mask(z, variant):
    keep = np.zeros(8, dtype=z.dtype)
    keep[VARIANTS[variant]] = 1
    return z * keep


def ridge_design(z, context):
    flat = z[:, :, :3].reshape(len(z), -1)
    return np.column_stack([flat, z[:, 0, 3]]) if context else flat


def network(z, weights, config):
    def linear(x, name):
        return x @ np.asarray(weights[name+'.weight']).T + np.asarray(weights[name+'.bias'])

    def norm(x, name):
        centered = x - x.mean(axis=-1, keepdims=True)
        normalized = centered / np.sqrt(np.mean(centered**2, axis=-1, keepdims=True) + config['eps'])
        return normalized * np.asarray(weights[name+'.weight']) + np.asarray(weights[name+'.bias'])

    x = linear(z, 'embed') + np.asarray(weights['pos'])
    batch, bins, width = x.shape
    heads = config['heads']
    head_width = width // heads
    q, k, v = [p.reshape(batch, bins, heads, head_width).swapaxes(1, 2)
               for p in np.split(linear(x, 'qkv'), 3, axis=-1)]
    logits = (q @ k.swapaxes(-1, -2)) / np.sqrt(head_width)
    attention = np.exp(logits - logits.max(axis=-1, keepdims=True))
    attention /= attention.sum(axis=-1, keepdims=True)
    value = (attention @ v).swapaxes(1, 2).reshape(batch, bins, width)
    x = norm(x + linear(value, 'attn_out'), 'norm1')
    x = norm(x + linear(np.maximum(linear(x, 'fc1'), 0), 'fc2'), 'norm2')
    return linear(x[:, -1], 'readout')[:, 0]


def predict_tokens(model, tokens, recent, wrong_tokens=None):
    z = standardize(np.asarray(tokens, dtype=np.float64), model['scaler'])
    recent = np.asarray(recent, dtype=np.float64).reshape(-1)
    if z.shape != (len(recent), 10, 8):
        raise ValueError('Expected batched tokens and matching recent changes')
    condition = z[:, 0, 3].astype(int)
    baseline = model['baselines']
    preds = {'zero': np.zeros_like(recent), 'continue': recent,
             'typical': np.full_like(recent, baseline['typical']),
             'typical_condition': np.asarray(baseline['typical_condition'])[condition]}
    y_mean, y_scale = (model['scaler'][key] for key in ('y_mean', 'y_scale'))
    for name in ('ridge_load', 'ridge_condition'):
        coef = baseline[name]
        est = ridge_design(z, name == 'ridge_condition') @ coef['weight'] + coef['bias']
        preds[name] = y_mean + y_scale * est
    for name in VARIANTS:
        preds[name] = y_mean + y_scale * network(mask(z, name), model['models'][name], model['config'])
    if wrong_tokens is not None:
        wrong = standardize(wrong_tokens, model['scaler'])
        preds['wrong'] = y_mean + y_scale * network(wrong, model['models']['full'], model['config'])
    return preds


def predict(model, load, emg, condition, donor_emg=None):
    load = np.asarray(load, dtype=np.float64)
    if load.shape != (201,):
        raise ValueError('Supply one 201-sample history')
    tokens = features(load, emg, condition)[None]
    wrong = None if donor_emg is None else features(load, donor_emg, condition)[None]
    preds = predict_tokens(model, tokens, [load[200] - load[100]], wrong)
    return {name: float(value[0]) for name, value in preds.items()}
