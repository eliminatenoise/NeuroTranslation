"""Try two 100 ms forecasts with generated or user-supplied histories."""

import argparse
import json
from pathlib import Path
import sys

try:
    import numpy as np
except ModuleNotFoundError:
    raise SystemExit('NumPy is required. See the setup for your operating system in SIMPLE.md.') from None

from inference import JointModel, standardize


HERE = Path(__file__).resolve().parent
METHODS = ('latest_mean', 'linear_trend', 'fit_ridge', 'joint_attention')
UNITS = {'force': 'N s', 'waist': 'rad/s'}


def forecasts(model, task, history):
    if task not in model.tasks:
        raise ValueError(f'Choose one of {", ".join(sorted(model.tasks))}.')
    schema = model.tasks[task]
    values = np.asarray(history, dtype=np.float64)
    expected = (schema['history_steps'], len(schema['channels']))
    if values.shape != expected or not np.isfinite(values).all():
        raise ValueError(f'Each complete history needs {expected[0]} rows and {expected[1]} finite values per row.')
    last, previous = values[-1], values[-2]
    if task == 'force':
        last, previous = last / 10., previous / 10.
    else:
        last, previous = last[3:], previous[3:]
    data = model.arrays
    named = standardize(values, data[f'{task}.xmean'], data[f'{task}.xscale'])[:, :expected[1]]
    ridge = np.r_[1., named.ravel()] @ data[f'{task}.ridge'] * data[f'{task}.yscale'] + data[f'{task}.ymean']
    learned = model.predict(task, values[None])[0]
    outputs = (last, last + 3 * (last - previous), ridge, learned)
    if not all(np.isfinite(output).all() for output in outputs):
        raise ValueError('Input values exceed the numerical range of the forecast.')
    return {'task': task, 'unit': UNITS[task], 'fields': schema['outputs'],
            'forecasts': {method: output.tolist() for method, output in zip(METHODS, outputs, strict=True)}}


def examples():
    yield 'force', [[value] for value in [5, 7, 14, 35, 62, 104, 170, 224, 285, 320]]
    samples = np.arange(10, dtype=float)
    waist = np.column_stack((.02 + .004 * samples, -.04 + .003 * samples, .06 - .005 * samples,
                            .20 + .04 * samples, -.12 + .016 * samples, -.22 + .025 * samples))
    yield 'waist', waist


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input', type=Path, help='JSON object with task and a complete 10-row history')
    args = cli.parse_args()
    model = JointModel.load(HERE / 'model.npz')
    if args.input:
        try:
            data = json.loads(args.input.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or set(data) != {'task', 'history'} or not isinstance(data['task'], str):
                raise ValueError('Supply a JSON object with task and history fields.')
            output = forecasts(model, data['task'], data['history'])
        except (OSError, TypeError, ValueError, OverflowError) as error:
            cli.error(str(error))
        print(json.dumps({'horizon_ms': 100, 'input': 'local JSON history', 'results': [output]}, indent=2))
    else:
        print(json.dumps({'horizon_ms': 100, 'input': 'generated examples',
                          'results': [forecasts(model, task, history) for task, history in examples()]}, indent=2))


if __name__ == '__main__':
    main()
