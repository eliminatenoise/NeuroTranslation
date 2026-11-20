"""Forecast a change in the fixed pedal's recorded load-cell channel."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from portable import predict

HERE = Path(__file__).resolve().parent


def history(record, key):
    values = record[key]
    if not isinstance(values, list) or len(values) != 201 or any(type(v) not in (int, float) for v in values):
        raise ValueError(f'{key} requires exactly 201 numbers')
    result = np.asarray(values, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError(f'{key} requires finite numbers')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('history', nargs='?', type=Path, default=HERE / 'example.json')
    args = parser.parse_args()
    try:
        data = json.loads(args.history.read_bytes())
        if not isinstance(data, dict) or data.get('setting') not in ('angle0', 'angle5'):
            raise ValueError('Select the source setting angle0 or angle5')
        model = json.loads((HERE / 'model.json').read_bytes())
        donor = history(data, 'donor_emg') if 'donor_emg' in data else None
        results = predict(model, history(data, 'load'), history(data, 'emg'), int(data['setting'] == 'angle5'), donor)
        print(json.dumps({'setting':data['setting'], 'target':'signed change over 100 samples, nominally 100 ms',
                          'unit':'native load-conditioner units','predictions':results}, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f'Could not forecast: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
