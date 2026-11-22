"""Try NeuroTranslate 0.0 on an invented walk or read your own prepared JSON."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from _joint_inference import JointModel


HERE = Path(__file__).resolve().parent
CATALOGUE = json.loads((HERE / 'CHECKPOINTS.json').read_text(encoding='utf-8'))
TASK = CATALOGUE['task']
DOMAIN = CATALOGUE['domain']
INPUT_FIELDS = {'task', 'domain', 'plate', 'issue_tick', 'analog_sample_rate_hz', 'bin_end_ticks', 'X'}


def read_history(packet):
    if not isinstance(packet, dict) or set(packet) != INPUT_FIELDS:
        raise ValueError('Use the fields in example.json.')
    if packet['task'] != TASK or packet['domain'] != DOMAIN:
        raise ValueError('Use the task and domain in example.json.')
    plate, tick, rate = packet['plate'], packet['issue_tick'], packet['analog_sample_rate_hz']
    if type(plate) is not int or plate not in (1, 2):
        raise ValueError('Choose plate 1 or 2.')
    if type(rate) is not int or rate != 1000 or type(tick) is not int or tick < 199 or (tick - 199) % 20:
        raise ValueError('Use the 1,000 Hz clock and issue at tick 199 plus a multiple of 20 samples.')
    bins = packet['bin_end_ticks']
    if not isinstance(bins, list) or any(type(value) is not int for value in bins) or bins != list(range(tick - 180, tick + 1, 20)):
        raise ValueError('Supply ten bin ends spaced by 20 samples. The last bin ends at issue.')
    rows = packet['X']
    if not isinstance(rows, list) or len(rows) != 10 or not all(isinstance(row, list) and len(row) == 15 for row in rows):
        raise ValueError('Each of ten X rows needs fourteen muscle readings and one force reading.')
    missing = False
    for row in rows:
        for column, value in enumerate(row):
            if value is None:
                missing = True
                continue
            if type(value) not in (float, int) or (isinstance(value, int) and value.bit_length() > 128):
                raise ValueError('Use finite numbers for readings and null for a missing reading.')
            if not math.isfinite(value) or abs(value) > np.finfo(np.float32).max:
                raise ValueError('A reading is outside the numeric range of the model.')
            if column < 14 and value < 0:
                raise ValueError('Muscle voltage summaries must be zero or greater. Plate force may be signed.')
    return None if missing else np.asarray([rows], dtype=np.float64)


class WalkingForce:
    def __init__(self, name):
        details = CATALOGUE['checkpoints'][name]
        filename = HERE / details['file']
        if hashlib.sha256(filename.read_bytes()).hexdigest() != details['sha256']:
            raise ValueError('The checkpoint file changed. Extract a fresh copy and try again.')
        self.name = name
        self.details = details
        self.model = JointModel.load(filename)

    def predict(self, packet):
        history = read_history(packet)
        tick = packet['issue_tick']
        result = {
            'model': self.name,
            'checkpoint_sha256': self.details['sha256'],
            'scope': 'fit_only',
            'plate': packet['plate'],
            'issue_tick': tick,
            'forecast_samples_inclusive': [tick + 1, tick + 100],
            'issued': history is not None,
            'chance_of_new_plate_load': None,
            'signed_force_impulse_newton_seconds': None,
        }
        if history is None:
            result['reason'] = 'A required muscle or plate-force reading is missing.'
            return result
        with np.errstate(over='ignore', invalid='ignore'):
            logit, impulse = (float(value) for value in self.model.predict(TASK, history)[0])
        exp = math.exp(-abs(logit))
        result['chance_of_new_plate_load'] = 1 / (1 + exp) if logit >= 0 else exp / (1 + exp)
        result['signed_force_impulse_newton_seconds'] = impulse
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', nargs='?', type=Path, default=HERE / 'example.json', help='JSON with the ten input bins')
    parser.add_argument('--model', choices=['all', *CATALOGUE['checkpoints']], default='all', help='checkpoint to open')
    args = parser.parse_args()
    try:
        packet = json.loads(args.request.read_text(encoding='utf-8'))
        choices = CATALOGUE['checkpoints'] if args.model == 'all' else (args.model,)
        forecasts = [WalkingForce(name).predict(packet) for name in choices]
    except (OSError, ValueError) as error:
        parser.exit(2, f'Could not run the forecast. {error}\n')
    print(json.dumps(forecasts, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
