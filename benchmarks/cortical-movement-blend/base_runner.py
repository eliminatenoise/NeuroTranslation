"""Forecast a hand displacement 100 milliseconds ahead from ten M1 count bins."""

from argparse import ArgumentParser
from json import dumps, loads
from pathlib import Path

import numpy as np
import onnxruntime as ort


HERE = Path(__file__).resolve().parent
SEEDS = (20261124, 20261125, 20261126)
ELECTRODES = np.arange(96, 192)


def ordered_window(electrode_ids, counts):
    ids, values = np.asarray(electrode_ids), np.asarray(counts)
    if ids.shape != (96,) or ids.dtype.kind not in 'iu':
        raise ValueError('Provide 96 integer electrode IDs from 96 through 191.')
    order = np.argsort(ids)
    if not np.array_equal(ids[order], ELECTRODES):
        raise ValueError('Use each electrode ID from 96 through 191 exactly once.')
    if (values.shape != (96, 10) or values.dtype.kind not in 'iu' or
            np.any(values < 0) or np.any(values > np.iinfo(np.uint16).max)):
        raise ValueError('Provide ten nonnegative integer counts per electrode, oldest bin first.')
    return values[order].astype(np.int32)[None]


def example():
    generated = np.random.default_rng(289).poisson(0.8, size=(96, 10))
    return ordered_window(ELECTRODES, generated)


def session(seed):
    options = ort.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    return ort.InferenceSession(str(HERE / f'electrode-identity-{seed}.onnx'), sess_options=options,
                                providers=['CPUExecutionProvider'])


def main():
    args = ArgumentParser(description=__doc__)
    args.add_argument('--input', type=Path, help='JSON with electrode_ids and counts fields')
    args.add_argument('--seed', type=int, choices=SEEDS, default=SEEDS[0])
    config = args.parse_args()
    label = 'generated example'
    if config.input is None:
        window = example()
    else:
        data = loads(config.input.read_text(encoding='utf-8'))
        window = ordered_window(data['electrode_ids'], data['counts'])
        label = 'supplied counts'
    forecast = session(config.seed).run(['movement_mm'], {'counts': window})[0]
    if forecast.shape != (1, 3) or not np.isfinite(forecast).all():
        raise ValueError('The model did not return three finite values.')
    dx, dy, distance = map(float, forecast[0])
    print(dumps({'input': label, 'training_seed': config.seed, 'forecast_ahead_ms': 100,
                'x_change_mm': dx, 'y_change_mm': dy, 'distance_estimate_mm': distance}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
