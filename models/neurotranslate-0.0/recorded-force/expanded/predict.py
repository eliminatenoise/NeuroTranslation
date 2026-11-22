"""Run the two NeuroTranslate force-plate previews with saved sensor summaries."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

try:
    import numpy as np
except ModuleNotFoundError as error:
    if error.name != 'numpy':
        raise
    sys.exit('Install NumPy in this Python environment with python -m pip install numpy. See README.md for setup.')

from inference import JointModel


ROOT = Path(__file__).resolve().parent
VERSION = '0.0.0-expanded-force-preview.1'
TASK = 'recorded_plate_loading_common_six_100ms'
CHANNELS = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS', 'named_plate_upward_force_mean')
CHECKPOINTS = {
    'frozen_core': ('models/frozen-core.npz', 'da97baca8e56cc3aac35b60d51b08683386a7bedf650963b3d66d1cee9aedbc1'),
    'trainable_core': ('models/trainable-core.npz', 'b371040dae65d580ae7d7786d22bbc0b2e09bcb8bfcce495d6e8205befbf568e'),
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def number(value, *, voltage=False):
    if value is None:
        return np.nan
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Each measurement must be a finite number or null.')
    if voltage and value < 0:
        raise ValueError('EMG magnitudes in volts must be nonnegative.')
    return value


def histories(document):
    if type(document) is not dict or set(document) != {'histories'}:
        raise ValueError('Use a JSON object with a histories list like example.json.')
    rows = document['histories']
    if not isinstance(rows, list) or not rows:
        raise ValueError('Supply at least one history.')
    samples = []
    for row in rows:
        if type(row) is not dict or set(row) != {'emg_rms_v', 'force_mean_n'}:
            raise ValueError('Each history needs emg_rms_v and force_mean_n.')
        emg, force = row['emg_rms_v'], row['force_mean_n']
        if not (isinstance(emg, list) and isinstance(force, list) and len(emg) == len(force) == 10
                and all(isinstance(block, list) and len(block) == 6 for block in emg)):
            raise ValueError('Supply ten 20 ms bins, each with six EMG channels and one force mean.')
        blocks = [[*(number(x, voltage=True) for x in block), number(force_mean)]
                  for block, force_mean in zip(emg, force)]
        if all(np.isnan(value) for block in blocks for value in block):
            raise ValueError('A history with every measurement missing cannot produce a forecast.')
        samples.append(blocks)
    return np.asarray(samples, dtype=np.float64)


def forecasts(inputs):
    output = {'version': VERSION, 'horizon_ms': 100, 'forecasts': {}}
    for label, (filename, checksum) in CHECKPOINTS.items():
        path = ROOT / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError(f'{filename} differs from this preview. Extract a fresh copy.')
        model = JointModel.load(path)
        schema = model.tasks[TASK]
        if tuple(schema['channels']) != CHANNELS or schema['history_steps'] != 10 or schema['horizon_ticks'] != 100:
            raise ValueError(f'{filename} has an incompatible sensor layout.')
        prediction = model.predict(TASK, inputs).astype(np.float64)
        logit = prediction[:, 0]
        small = np.exp(-np.abs(logit))
        probability = np.where(logit >= 0, 1 / (1 + small), small / (1 + small))
        output['forecasts'][label] = [
            {'new_load_probability': float(prob), 'signed_force_impulse_n_s': float(impulse)}
            for prob, impulse in zip(probability, prediction[:, 1])
        ]
    return output


def verify_example(actual, expected):
    if set(actual) != set(expected) or actual['version'] != expected['version'] or actual['horizon_ms'] != expected['horizon_ms']:
        raise ValueError('The example version or format differs from the saved output.')
    if actual['forecasts'].keys() != expected['forecasts'].keys():
        raise ValueError('The example checkpoint names differ from the saved output.')
    keys = ('new_load_probability', 'signed_force_impulse_n_s')
    for label, estimates in actual['forecasts'].items():
        reference = expected['forecasts'][label]
        if len(estimates) != len(reference) or any(estimate.keys() != target.keys()
               or any(not math.isclose(estimate[key], target[key], rel_tol=5e-5, abs_tol=1e-5) for key in keys)
               for estimate, target in zip(estimates, reference)):
            raise ValueError(f'{label} output differs from the example reference.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--input', type=Path, help='run a JSON file in the example format')
    mode.add_argument('--check-example', action='store_true', help='check the bundled example against the reference')
    options = parser.parse_args()
    try:
        output = forecasts(histories(read_json(options.input or ROOT / 'example.json')))
        if options.check_example:
            verify_example(output, read_json(ROOT / 'expected.json'))
            print('Example matches the reference for both checkpoints.', file=sys.stderr)
    except (OSError, OverflowError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
