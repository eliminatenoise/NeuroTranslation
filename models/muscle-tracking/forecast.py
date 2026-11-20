"""Forecast ten tracking steps from an invented or user-supplied history."""
import argparse
import json
from pathlib import Path

import numpy as np
from portable import predict_all

HERE = Path(__file__).resolve().parent


def history(data, key, count):
    values = data[key]
    if not isinstance(values, list) or len(values) != count or any(type(v) not in (int, float) for v in values):
        raise ValueError(f'{key} must contain {count} numbers.')
    result = np.asarray(values, dtype=float)
    if not np.isfinite(result).all() or (key == 'length_mm' and np.any(result <= 0)):
        raise ValueError('Lengths must be positive. Every input must be finite.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('history', type=Path, nargs='?', default=HERE / 'example.json',
                        help='JSON object with 21 lengths, 20 earlier angles and optionally 20 alternate angles')
    args = parser.parse_args()
    try:
        data = json.loads(args.history.read_text(encoding='utf-8'))
        lengths = history(data, 'length_mm', 21)
        angles = history(data, 'angle_deg', 20)
        has_alternate = 'other_angle_deg' in data
        alternate = history(data, 'other_angle_deg', 20) if has_alternate else angles
        model = json.loads((HERE / 'model.json').read_text(encoding='utf-8'))
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            predictions = predict_all(model, lengths, angles, alternate)
        changes = {key: float(values[0]) if np.isfinite(values[0]) else None
                   for key, values in predictions.items() if key != 'wrong' or has_alternate}
        print(json.dumps({'tracking_steps_ahead': 10, 'current_length_mm': float(lengths[-1]),
                          'signed_change_mm': changes}, indent=2, allow_nan=False))
    except (OSError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
        parser.exit(2, f'Could not forecast the change in length. {exc}\n')


if __name__ == '__main__':
    main()
