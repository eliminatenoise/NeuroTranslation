"""Generate a two-plate invented 200 ms input for the Research Edition preview."""

from argparse import ArgumentParser
from copy import deepcopy
import json


CHANNELS = ['LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS']
ROWS, BINS, ISSUE_TICK, HZ = 2, 10, 199, 1000


def make():
    cutoffs = list(range(19, ISSUE_TICK + 1, 20))
    streams = {}
    for stream, labels, unit in (('emg', CHANNELS, 'V RMS'), ('force', ['signed vertical force'], 'N')):
        count = len(labels)
        clocks = [[[t] * count for t in cutoffs] for _ in range(ROWS)]
        values = [
            [[round((21 + 5 * row + tick + 3 * c) * 0.000001, 9) if stream == 'emg'
              else round(-0.3 + 0.04 * tick + 0.2 * row, 3) for c in range(count)]
             for tick in range(BINS)] for row in range(ROWS)
        ]
        streams[stream] = {'channels': labels, 'unit': unit, 'values': values,
                           'observed': [[[True] * count for _ in cutoffs] for _ in range(ROWS)],
                           'acquired_tick': clocks, 'available_tick': deepcopy(clocks)}
    streams['emg']['observed'][0][3][1] = False
    streams['emg']['available_tick'][1][-1][2] = ISSUE_TICK + 20
    streams['force']['available_tick'][1][-1][0] = ISSUE_TICK + 20
    return {
        'schema_version': 1, 'kind': 'invented', 'clock_hz': HZ, 'target_horizon_ms': 100,
        'rows': [{'example_plate': 1, 'issue_tick': ISSUE_TICK}, {'example_plate': 2, 'issue_tick': ISSUE_TICK}],
        'bin_end_tick': cutoffs, 'streams': streams,
    }


def mutate_hidden(fixture):
    """Replace unseen values to test that availability controls what enters the model."""
    changed = deepcopy(fixture)
    for name, stream in changed['streams'].items():
        for r, bins in enumerate(admitted(changed, name)):
            for t, values in enumerate(bins):
                for c, value in enumerate(values):
                    if value is None:
                        stream['values'][r][t][c] = 1.0 if name == 'emg' else -9000.0
    return changed


def admitted(fixture, name):
    stream = fixture['streams'][name]
    kept = []
    for r, bins in enumerate(stream['values']):
        row = []
        for t, channels in enumerate(bins):
            cutoff = fixture['bin_end_tick'][t]
            visibility = zip(stream['observed'][r][t], stream['acquired_tick'][r][t], stream['available_tick'][r][t],
                             channels, strict=True)
            row.append([value if seen and acquired <= cutoff and available <= cutoff else None
                        for seen, acquired, available, value in visibility])
        kept.append(row)
    return kept


def check():
    original = make()
    changed = mutate_hidden(original)
    assert original['bin_end_tick'][0] == 19 and original['bin_end_tick'][-1] == 199
    expected = {'emg': (6, 2), 'force': (1, 1)}
    for name, (width, missing) in expected.items():
        view = admitted(original, name)
        assert len(view) == ROWS and all(len(row) == BINS and all(len(t) == width for t in row) for row in view)
        assert sum(value is None for row in view for tick in row for value in tick) == missing
        assert original['streams'][name]['values'] != changed['streams'][name]['values']
        assert view == admitted(changed, name)
    return {'synthetic_shape_and_age_mask_verified': True, 'rows': ROWS, 'bins': BINS,
            'hidden_emg_values': 2, 'hidden_force_values': 1, 'forecast_calculated': False}


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('fixture', 'altered', 'check'), default='fixture')
    args = parser.parse_args()
    data = check() if args.mode == 'check' else mutate_hidden(make()) if args.mode == 'altered' else make()
    print(json.dumps(data, indent=2, allow_nan=False))
