"""Forecast two-plate impulse from a recorded or generated muscle-history array."""

from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np


CHANNELS = ('TibialisAnterior', 'GastrocnemiusMedialis', 'GastrocnemiusLateralis', 'VastusMedialis',
            'VastusLateralis', 'RectusFemoris', 'Semitendinosus', 'BicepsFemoris')
SEEDS = (20261125, 20261126, 20261127)


def predict(history, weights, threads=1):
    import torch
    from torch import nn

    history = np.asarray(history, dtype=np.float64)
    if history.ndim != 3 or history.shape[1:] != (10, 8) or not len(history):
        raise ValueError('Supply one or more histories with ten time bins and eight channels each.')
    present = np.isfinite(history)
    if np.isinf(history).any() or present[:, :3].any() or not present.any(axis=(1, 2)).all():
        raise ValueError('Use NaN for missing activity. Leave the first three bins missing and include at least one later value.')

    class Forecast(nn.Module):
        def __init__(self):
            super().__init__()
            self.input = nn.Linear(16, 32)
            self.positions = nn.Parameter(torch.zeros(10, 32))
            self.block = nn.TransformerEncoderLayer(32, 4, 64, dropout=0, batch_first=True,
                                                     norm_first=True, activation='gelu')
            self.output = nn.Sequential(nn.LayerNorm(32), nn.Linear(32, 1))

        def forward(self, x, passes):
            hidden = self.input(x) + self.positions
            for _ in range(passes):
                hidden = self.block(hidden)
            return self.output(hidden[:, -1]).squeeze(-1)

    torch.set_num_threads(threads)
    torch.set_float32_matmul_precision('highest')
    torch.use_deterministic_algorithms(True)
    normalized = np.where(present, (history - weights['feature_center']) / weights['feature_scale'], 0.)
    values = np.concatenate((normalized, present.astype(np.float64)), axis=2)
    reverse = np.concatenate((values[:, :3], values[:, 3:][:, ::-1]), axis=1)
    order, backward = (torch.from_numpy(a.astype(np.float32)) for a in (values, reverse))
    columns = np.column_stack((np.ones(len(values)), values.reshape(len(values), -1)))
    output = {'fitted_median': np.full(len(values), float(weights['prior'])), 'ridge': columns @ weights['ridge']}
    separate_runs = {name: [] for name in ('attention_1', 'attention_3', 'attention_3_reversed')}
    for passes in (1, 3):
        for seed in SEEDS:
            model = Forecast().eval()
            state = {name: torch.from_numpy(weights[f'pass{passes}.{seed}.{name}']) for name in model.state_dict()}
            model.load_state_dict(state)
            with torch.inference_mode():
                separate_runs[f'attention_{passes}'].append(model(order, passes).numpy().astype(np.float64))
                if passes == 3:
                    separate_runs['attention_3_reversed'].append(model(backward, passes).numpy().astype(np.float64))
    for name, predictions in separate_runs.items():
        output[name] = np.mean(predictions, axis=0) * weights['target_scale'] + weights['target_center']
    return output


def main():
    arguments = ArgumentParser(description=__doc__)
    arguments.add_argument('inputs', type=Path, help='NPZ with history and channels arrays')
    arguments.add_argument('--weights', type=Path, default=Path(__file__).with_name('ENGINEERING-WEIGHTS.npz'))
    arguments.add_argument('--threads', type=int, default=1)
    options = arguments.parse_args()
    if options.threads < 1:
        arguments.error('Use at least one CPU thread.')
    with np.load(options.inputs, allow_pickle=False) as data:
        if tuple(data['channels']) != CHANNELS:
            arguments.error('The channel names and order must match the Technical guide.')
        history = data['history']
    with np.load(options.weights, allow_pickle=False) as stored:
        results = predict(history, dict(stored), threads=options.threads)
    print(json.dumps({'unit': 'N s', 'predictions': {name: values.tolist() for name, values in results.items()}},
                     indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
