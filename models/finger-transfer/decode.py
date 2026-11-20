# SPDX-License-Identifier: CC0-1.0
"""Calibrate on an initial recording, then decode a new packet without using the glove."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from model import load_weights, predict
from movement import FINGERS, calibrate, packet, trials

HERE = Path(__file__).resolve().parent


def integer_codes(codes):
    codes = np.asarray(codes)
    if codes.ndim != 1 or len(codes) == 0 or not np.issubdtype(codes.dtype, np.integer):
        raise ValueError('Need a nonempty one-dimensional vector of integer region codes')
    return codes


def calibration_packet(source):
    voltage = np.asarray(source['voltage'])
    cue = np.asarray(source['cue'])
    ticks = np.asarray(source['time_ms'])
    glove = np.asarray(source['glove'])
    codes = integer_codes(source['region'])
    if voltage.shape != (80000, len(codes)) or cue.shape != (80000,):
        raise ValueError('Calibration requires exactly the first 80000 ms and matching cue rows')
    if not np.array_equal(ticks, np.arange(0, 80000, 40)) or glove.shape != (len(ticks), 5):
        raise ValueError('Expected five glove readings per verified 40-ms tick, beginning at row 0')
    if (not np.issubdtype(cue.dtype, np.integer) or not np.isin(cue, np.arange(6)).all()
            or not np.isfinite(voltage).all() or not np.isfinite(glove).all()):
        raise ValueError('Unexpected cue or nonfinite calibration value')
    eligible = list(trials(cue, (0, 80000)))
    return {**calibrate(voltage, glove, ticks, eligible), 'region': codes.copy()}


def decode(raw, codes, cal, digit, phase, elapsed_ms, family='transformer', mode='aligned',
           weights_dir=HERE/'weights'):
    codes = integer_codes(codes)
    if not np.array_equal(codes, cal['region']):
        raise ValueError('Contact order must match calibration, including every region code')
    gains = np.asarray(cal['gain'])
    if gains.shape != (5,) or not np.isfinite(gains).all() or np.any(gains < 1):
        raise ValueError('Expected five calibrated sensor gains of at least 1 sensor count')
    if elapsed_ms < 279:
        raise ValueError('Electrical support would begin before the current phase')
    x = packet(raw, codes, cal, digit, phase, elapsed_ms)[None].astype(np.float32)
    w = load_weights(weights_dir/f'{family}_{mode}.npz')
    y = predict(x, family, mode, w)[0]
    return {'digit_order': list(FINGERS), 'personal_calibration_units': y.tolist(),
            'sensor_counts_per_40ms_step': (y*gains).tolist()}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    subs = ap.add_subparsers(dest='command', required=True)
    c = subs.add_parser('calibrate')
    c.add_argument('input', type=Path)
    c.add_argument('output', type=Path)
    d = subs.add_parser('predict')
    d.add_argument('input', type=Path)
    d.add_argument('calibration', type=Path)
    d.add_argument('--digit', type=int, required=True, choices=range(1,6))
    d.add_argument('--phase', choices=['display','blank'], required=True)
    d.add_argument('--elapsed-ms', type=int, required=True)
    d.add_argument('--family', choices=['ridge','transformer'], default='transformer')
    d.add_argument('--mode', choices=['cue','cortex','aligned'], default='aligned')
    args = ap.parse_args()
    if args.command == 'calibrate':
        with np.load(args.input, allow_pickle=False) as source:
            scales = calibration_packet(source)
        with args.output.open('xb') as f:
            np.savez(f, **scales)
    else:
        torch.set_num_threads(2)
        with np.load(args.input, allow_pickle=False) as source:
            if set(source.files) != {'voltage', 'region'}:
                raise ValueError('Prediction input requires exactly voltage and region')
            out = decode(source['voltage'], source['region'], load_weights(args.calibration),
                         args.digit, int(args.phase == 'blank'), args.elapsed_ms, args.family, args.mode)
        print(json.dumps(out, indent=2))
