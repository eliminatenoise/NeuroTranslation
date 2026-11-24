"""Forecast new loads on two force plates and, with the pace models, force impulse."""

import argparse
import json
import math
from pathlib import Path

CHANNELS = ('LBF', 'LRF', 'LTA', 'RBF', 'RRF', 'RTA')
ARMS = ('global_prior', 'pair_state_prior', 'own_force', 'paired_force',
        'paired_force_with_channel_flags', 'paired_relative_muscle')
TIMING_ARMS = ('timing_linear', 'timing_attention')
PACE_ATTENTION_ARMS = ('single_pace_attention', 'three_pace_attention')
PACE_ARMS = (*PACE_ATTENTION_ARMS, 'three_pace_short')
DELAYS_MS = [0, 100, 200, 300, 500]
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(rows, outer, width, name):
    require(isinstance(rows, list) and len(rows) == outer and
            all(isinstance(row, list) and len(row) == width for row in rows), f'{name} has the wrong shape.')


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def finite_or_empty(rows, name):
    require(all(value is None or numeric(value) for row in rows for value in row),
            f'{name} needs finite numbers or null for a missing value.')


def vector(force, state):
    return [float(state == code) for code in (1, 2, 3)] + [
        float(value is not None) for value in force] + [
        float(value) if value is not None else 0. for value in force]


def probability(model, items):
    columns, centers, scales, coefficients = (model[key] for key in ('columns', 'mean', 'scale', 'theta'))
    require(len(columns) == len(centers) == len(scales) == len(coefficients) - 1,
            'The saved model has the wrong number of coefficients.')
    contributions = [coefficients[0]]
    for column, center, scale, coefficient in zip(columns, centers, scales, coefficients[1:]):
        contributions.append(coefficient * ((items[column] - center) / scale))
    return sigmoid(math.fsum(contributions))


def sigmoid(logit):
    if logit < 0.:
        chance = math.exp(logit)
        return chance / (1. + chance)
    return 1. / (1. + math.exp(-logit))


def read_short_history(history):
    times, force, states = (history[key] for key in ('bin_end_ms', 'vertical_force_n', 'plate_state'))
    shape(times, 2, 10, 'bin_end_ms')
    shape(force, 2, 10, 'vertical_force_n')
    require(all(type(value) is int for row in times for value in row) and times[0] == times[1] and
            all(later - earlier == 20 for earlier, later in zip(times[0], times[0][1:])),
            'Both plates need the same ten bin end times, spaced 20 ms apart.')
    require(isinstance(states, list) and len(states) == 2 and
            all(type(state) is int and state in range(4) for state in states),
            'Give each plate an observed state code from 0 to 3.')
    finite_or_empty(force, 'vertical_force_n')
    return force, states


def forecast(checkpoint, history, arm):
    """Return two probabilities in the same order as the input force plates."""
    require(checkpoint['format'] == 'paired_plate_load_head_v1' and tuple(checkpoint['channel_names']) == CHANNELS,
            'The checkpoint format or muscle names differ from this version.')
    require(arm in ARMS, 'Choose one of the saved comparisons.')
    force, states = read_short_history(history)
    model = checkpoint['models'][arm]
    if arm == 'global_prior':
        return [model, model]
    if arm == 'pair_state_prior':
        return [model[4 * state + other] for state, other in (states, states[::-1])]

    named = [vector(row, state) for row, state in zip(force, states)]
    if arm == 'own_force':
        return [probability(model, row) for row in named]

    extra = []
    if arm in ('paired_force_with_channel_flags', 'paired_relative_muscle'):
        relative = history['relative_muscle_activity']
        shape(relative, 10, len(CHANNELS), 'relative_muscle_activity')
        finite_or_empty(relative, 'relative_muscle_activity')
        require(all(value is None for row in relative[:3] for value in row),
                'Leave the first three relative muscle bins empty.')
        require(tuple(history.get('muscle_channels', ())) == CHANNELS, 'Keep the stated muscle channel order.')
        recent = [value for row in relative[3:] for value in row]
        extra = [float(value is not None) for value in recent]
        if arm == 'paired_relative_muscle':
            extra += [float(value) if value is not None else 0. for value in recent]
    return [probability(model, own + companion + extra) for own, companion in (named, named[::-1])]


def dense(vector, weights, bias=None):
    return [math.fsum(weight * value for weight, value in zip(row, vector))
            + (bias[index] if bias is not None else 0.) for index, row in enumerate(weights)]


def timing_windows(history):
    times, force, states = (history[key] for key in ('bin_end_ms', 'vertical_force_n', 'plate_state_by_bin'))
    shape(times, 2, 35, 'bin_end_ms')
    shape(force, 2, 35, 'vertical_force_n')
    shape(states, 2, 35, 'plate_state_by_bin')
    require(all(type(value) is int for row in times for value in row) and times[0] == times[1]
            and all(right - left == 20 for left, right in zip(times[0], times[0][1:])),
            'Both plates must share 35 bin end times, spaced 20 ms apart.')
    require(all(numeric(value) for row in force for value in row), 'The timing forecast needs complete force readings.')
    require(all(type(value) is int and 0 <= value <= 3 for row in states for value in row),
            'Give a recorded state code from 0 to 3 at each bin end.')

    return [[vector(row[end - 9:end + 1], state[end])
             for end in (34 - delay // 20 for delay in DELAYS_MS)]
            for row, state in zip(force, states)]


def attention_readouts(windows, normalizers, fit):
    def normalize(values, location_and_scale):
        centers, scales = location_and_scale
        return [(value - center) / scale for value, center, scale in zip(values, centers, scales)]

    own_scale, other_scale = normalizers
    predictions = []
    for main, other in (windows, windows[::-1]):
        query = [math.tanh(x) for x in dense(normalize(main[0], own_scale), fit['own.weight'], fit['own.bias'])]
        context = [[math.tanh(x) + offset for x, offset in zip(
            dense(normalize(row, other_scale), fit['other.weight'], fit['other.bias']), lag)]
            for row, lag in zip(other, fit['lag'])]
        logits = [math.fsum(a * b for a, b in zip(query, key)) / math.sqrt(len(query))
                  for key in (dense(row, fit['key.weight']) for row in context)]
        peak = max(logits)
        weights = [math.exp(x - peak) for x in logits]
        total = math.fsum(weights)
        pooled = [math.fsum(weight * x for weight, x in zip(weights, column)) / total
                  for column in zip(*context)]
        predictions.append(dense(query + pooled, fit['readout.weight'], fit['readout.bias']))
    return predictions


def timing_forecast(checkpoint, history, arm):
    """Predict from 700 ms of force and the states observed at the five window ends."""
    require(arm in TIMING_ARMS, 'Choose a timing comparison.')
    require(checkpoint['format'] == 'paired_plate_timing_head_v1' and checkpoint['lags_ms'] == DELAYS_MS,
            'The saved timing model uses a different spacing of earlier readings.')
    windows = timing_windows(history)
    if arm == TIMING_ARMS[0]:
        return [probability(checkpoint['linear'], main[0] + [value for window in other for value in window])
                for main, other in (windows, windows[::-1])]
    return [sigmoid(result[0]) for result in attention_readouts(windows, checkpoint['normalizers'], checkpoint['attention'])]


def pace_forecast(checkpoint, history, arm):
    """Return one event probability and one signed impulse estimate per input plate."""
    require(arm in PACE_ARMS and checkpoint['format'] == 'paired_plate_pace_heads_v1' and checkpoint['lags_ms'] == DELAYS_MS,
            'The saved pace model or requested option has a different format.')
    fit = checkpoint['models'][arm]
    if arm == 'three_pace_short':
        force, states = read_short_history(history)
        require(all(numeric(value) for row in force for value in row), 'The trained pace models need complete force readings.')
        vectors = [vector(values, state) for values, state in zip(force, states)]
        pair = [own + other for own, other in (vectors, vectors[::-1])]
        impulse = []
        intercept, *coefficients = fit['impulse_coefficients']
        require(len(pair[0]) == len(fit['impulse_center']) == len(fit['impulse_scale']) == len(coefficients),
                'The saved impulse model has the wrong number of coefficients.')
        for values in pair:
            terms = [coefficient * ((value - center) / spread) for value, center, spread, coefficient in
                     zip(values, fit['impulse_center'], fit['impulse_scale'], coefficients)]
            impulse.append(math.fsum((intercept, *terms)))
        return [probability(fit['event'], values) for values in pair], impulse

    result = attention_readouts(timing_windows(history), fit['normalizers'], fit['weights'])
    return ([sigmoid(row[0]) for row in result],
            [row[1] * fit['impulse_scale'] + fit['impulse_center'] for row in result])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--example', action='store_true', help='Run the included invented history.')
    inputs.add_argument('--input', type=Path, help='Read your own JSON history.')
    parser.add_argument('--arm', choices=(*ARMS, *TIMING_ARMS, *PACE_ARMS), default='paired_force')
    args = parser.parse_args()
    try:
        paced = args.arm in PACE_ARMS
        timed = args.arm in (*TIMING_ARMS, *PACE_ATTENTION_ARMS)
        filename = 'pace-heads.json' if paced else ('timing-head.json' if timed else 'load-event-head.json')
        with (HERE / filename).open(encoding='utf-8') as stream:
            checkpoint = json.load(stream)
        sample = HERE / ('example-timing.json' if timed else 'example.json')
        with (args.input or sample).open(encoding='utf-8') as stream:
            history = json.load(stream)
        if paced:
            estimates, impulse_estimates = pace_forecast(checkpoint, history, args.arm)
        else:
            estimates = (timing_forecast if timed else forecast)(checkpoint, history, args.arm)
        states = [row[-1] for row in history['plate_state_by_bin']] if timed else history['plate_state']
        output = {'input_kind': 'user supplied' if args.input else 'invented example',
                  'horizon_ms': 100, 'issue_time_ms': history['bin_end_ms'][0][-1],
                  'head': args.arm, 'new_load_probability': estimates,
                  'plate_state_in_scored_recordings': [state in (1, 3) for state in states]}
        if paced:
            output['signed_impulse_ns'] = impulse_estimates
        if 'signed_impulse_ns' in history:
            impulse = history['signed_impulse_ns']
            require(isinstance(impulse, list) and len(impulse) == 2 and all(numeric(value) for value in impulse),
                    'Give one finite signed impulse estimate per plate in newton-seconds.')
            output['supplied_signed_impulse_ns'] = impulse
        print(json.dumps(output, indent=2, allow_nan=False))
    except (OSError, TypeError, ValueError, KeyError, IndexError, OverflowError) as error:
        parser.exit(2, f'Unable to forecast. {error}\n')


if __name__ == '__main__':
    main()
