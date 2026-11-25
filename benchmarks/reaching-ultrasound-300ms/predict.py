"""Run a compact reaching forecast from ten past input bins using NumPy."""

import argparse
import json
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


HERE = Path(__file__).resolve().parent
VALUES = np.r_[0:12, 16:19, 22:24]
PRESENT = np.r_[np.repeat(np.arange(12, 16), 3), 19:22, 24:26]
SEEDS = ('20261126', '20261127')


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60.0, 60.0)))


def update(incoming, state, weight, bias):
    hidden = state @ weight.T + bias
    input_reset, input_update, input_candidate = np.split(incoming, 3, axis=1)
    hidden_reset, hidden_update, hidden_candidate = np.split(hidden, 3, axis=1)
    reset = sigmoid(input_reset + hidden_reset)
    keep = sigmoid(input_update + hidden_update)
    candidate = np.tanh(input_candidate + reset * hidden_candidate)
    # The trained runtime stores each successive hidden state in FP32.
    return (candidate + keep * (state - candidate)).astype(np.float32)


def residual(inputs, weights, passes):
    conv = weights['conv.weight']
    history = np.pad(inputs, ((0, 0), (2, 0), (0, 0)))
    kernels = sliding_window_view(history, 3, axis=1).reshape(len(inputs), 10, -1)
    linear = kernels @ conv.reshape(len(conv), -1).T + weights['conv.bias']
    encoded = linear * sigmoid(linear)
    incoming = encoded @ weights['recurrent.weight_ih_l0'].T + weights['recurrent.bias_ih_l0']
    state = np.zeros((len(inputs), len(conv)))
    for time in range(10):
        state = update(incoming[:, time], state, weights['recurrent.weight_hh_l0'],
                       weights['recurrent.bias_hh_l0'])
    known = state @ weights['shared_step.weight_ih'].T + weights['shared_step.bias_ih']
    for _ in range(passes):
        state = update(known, state, weights['shared_step.weight_hh'], weights['shared_step.bias_hh'])
    return state @ weights['out.weight'].T + weights['out.bias']


def inputs_and_reference(history, ultrasound_times, norm, mode):
    if (history.ndim != 3 or history.shape[1:] != (10, 26)
            or ultrasound_times.shape != history.shape[:2] or not np.isfinite(history).all()):
        raise ValueError('Each example must contain ten finite rows of 26 fields and ten ultrasound times.')
    inputs = history.copy()
    if mode == 'gap':
        inputs[:, -5:, 22:26] = 0
    elif mode == 'blind':
        inputs[:, :, 22:26] = 0
    median = np.asarray(norm['training_median'])
    prior = np.broadcast_to(median, (len(history), 2))
    if mode != 'blind':
        visible = (inputs[..., 24:26] > .5).any(axis=2)
        edges = (np.arange(11) - 10) * .020
        if np.any(visible & (~np.isfinite(ultrasound_times) | (ultrasound_times >= 0)
                            | (ultrasound_times < edges[None, :-1] - 1e-9)
                            | (ultrasound_times >= edges[None, 1:] + 1e-9))):
            raise ValueError('Each visible ultrasound time must be inside its past 20 ms bin.')
        history_slice = slice(5, 10) if mode == 'full' else slice(0, 5)
        times = ultrasound_times[:, history_slice]
        values = inputs[:, history_slice, 22:24]
        present = inputs[:, history_slice, 24:26] > .5
        seen = present.any(axis=2)
        known = present.all(axis=1)
        times = np.where(seen, times, 0)
        mid = times.mean(axis=1)
        offset = times - mid[:, None]
        span = np.sum(offset ** 2, axis=1)
        if np.any(known.any(axis=1) & (span <= 0)):
            raise ValueError('The five visible ultrasound times must cover distinct bins.')
        slope = np.sum(offset[:, :, None] * values, axis=1) / np.maximum(span, 1e-12)[:, None]
        trend = values.mean(axis=1) + slope * (.300 - mid)[:, None]
        prior = np.where(known, trend, prior)
    flags = inputs[..., PRESENT] > .5
    mean, scale = np.asarray(norm['feature_mean']), np.asarray(norm['feature_scale'])
    inputs[..., VALUES] = np.where(flags, (inputs[..., VALUES] - mean) / scale, 0)
    return inputs.astype(np.float32).astype(np.float64), prior


def predict(history, ultrasound_times, weights, ridge, norm, mode, passes):
    inputs, prior = inputs_and_reference(history, ultrasound_times, norm, mode)
    scale = np.asarray(norm['target_scale'][mode])
    raw = [prior + residual(inputs, candidate, passes) * scale for candidate in weights]
    linear = inputs.copy()
    if mode == 'full':
        linear[:, :, :22] = 0
    elif mode == 'blind':
        linear[:, :, 16:26] = 0
    estimate = prior + ridge[0] + linear.reshape(len(inputs), -1) @ ridge[1:]
    return {
        'history_reference_mm': np.maximum(prior, 0),
        'linear_forecast_mm': np.maximum(estimate, 0),
        'learned_forecast_mm': np.maximum(np.mean(raw, axis=0), 0),
    }


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].astype(np.float64) for key in archive.files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=HERE / 'example.json')
    parser.add_argument('--mode', choices=('full', 'gap', 'blind'), default='full')
    parser.add_argument('--passes', choices=(1, 3, 5, 8), default=3, type=int)
    parser.add_argument('--seed', choices=(*SEEDS, 'both'), default=SEEDS[0])
    args = parser.parse_args()
    sample = json.loads(args.input.read_text(encoding='utf-8'))
    norm = json.loads((HERE / 'normalizer.json').read_text(encoding='utf-8'))
    files = SEEDS if args.seed == 'both' else (args.seed,)
    ridge = arrays(HERE / 'linear.npz')[args.mode]
    estimates = predict(np.asarray([sample['history']], dtype=float),
                        np.asarray([sample['ultrasound_times_from_issue_s']], dtype=float),
                        [arrays(HERE / f'shared-{seed}.npz') for seed in files],
                        ridge, norm, args.mode, args.passes)
    print(json.dumps({'look_ahead_ms': 300, 'mode': args.mode, 'passes': args.passes,
                      'seed': args.seed, 'target_order': ['triceps', 'brachialis'],
                      **{name: value[0].tolist() for name, value in estimates.items()}}, indent=2))


if __name__ == '__main__':
    main()
