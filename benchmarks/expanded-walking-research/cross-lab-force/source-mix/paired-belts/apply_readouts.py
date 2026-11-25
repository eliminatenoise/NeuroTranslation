"""Apply the saved force readouts to existing left and right impulse forecasts."""

from argparse import ArgumentParser
import json
from math import isfinite
from pathlib import Path


FULL = ('research_force_active_only', 'research_force_ridge')
FIT_GROUPS = ('one_lab', 'two_labs_equal_size', 'two_labs_all_windows')
FORECAST_INPUTS = ('last_20ms_mean', 'damped_trend', *FULL)


def two_values(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('Each forecast must contain two values in left, right order.')
    if not all(type(number) in (int, float) and isfinite(number) for number in value):
        raise ValueError('Use finite numerical impulse values in newton-seconds.')
    return list(map(float, value))


def combine(hold, trend, research, total_weight, split_weight):
    initial_total = trend[0] + trend[1]
    initial_split = hold[0] - hold[1]
    research_total = research[0] + research[1]
    research_split = research[0] - research[1]
    total = initial_total + total_weight * (research_total - initial_total)
    split = initial_split + split_weight * (research_split - initial_split)
    return [(total + split) * 0.5, (total - split) * 0.5]


def readout_weights(data):
    if not isinstance(data, dict) or set(data) != set(FIT_GROUPS):
        raise ValueError('Supply the three fitting groups listed in READOUTS.json.')
    for group in data.values():
        if not isinstance(group, dict) or set(group) != set(FULL):
            raise ValueError('Each fitting group must contain both Research Edition readouts.')
        for weights in group.values():
            if not isinstance(weights, dict) or set(weights) != {'total_weight', 'split_weight'}:
                raise ValueError('Supply weights for the total and the split between belts.')
            if not all(type(value) in (int, float) and 0.0 <= value <= 1.0 for value in weights.values()):
                raise ValueError('Every weight must be a number between zero and one.')
    return data


def forecast(case, readouts):
    if not isinstance(case, dict) or set(case) != set(FORECAST_INPUTS):
        raise ValueError('Each case needs the four forecast fields shown in EXAMPLE.json.')
    original = {name: two_values(case[name]) for name in FORECAST_INPUTS}
    hold = original['last_20ms_mean']
    trend = original['damped_trend']
    result = dict(original)
    result['physical_total_and_split'] = combine(hold, trend, original[FULL[0]], 0.0, 0.0)
    for family in FIT_GROUPS:
        for name in FULL:
            result[f'{family}_{name}'] = combine(hold, trend, original[name], **readouts[family][name])
    if not all(isfinite(value) for pair in result.values() for value in pair):
        raise ValueError('The supplied forecast is outside the numerical range.')
    return result


def main():
    folder = Path(__file__).resolve().parent
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, nargs='?', default=folder / 'EXAMPLE.json')
    parser.add_argument('--readouts', type=Path, default=folder / 'READOUTS.json')
    args = parser.parse_args()
    try:
        settings = json.loads(args.readouts.read_text(encoding='utf-8'))
        data = json.loads(args.input.read_text(encoding='utf-8'))
        fits = readout_weights(settings['fit_groups'])
        if not isinstance(data['cases'], list) or not data['cases']:
            raise ValueError('Provide a nonempty list of cases.')
        cases = [forecast(case, fits) for case in data['cases']]
    except (OSError, KeyError, ValueError, TypeError, OverflowError) as error:
        parser.error(str(error))
    print(json.dumps({'unit': 'N s', 'belt_order': ['left', 'right'], 'cases': cases}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
