"""Reproduce the aggregate assessment on the two reserved participants."""
import argparse
import json
from pathlib import Path

from data import HOLD, dataset, sha
from portable import predict_tokens
from score import scoring

HERE = Path(__file__).resolve().parent
PUBLIC_FIELDS = ('n_people', 'n_windows', 'balanced_mae', 'per_condition_mae', 'emg_increment', 'unit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='New JSON file for the aggregate results')
    args = parser.parse_args()
    checks = json.loads((HERE / 'PRETEST-SHA256.json').read_bytes())
    for name, expected in checks['unchanged_specialist_files'].items():
        if sha(HERE / name) != expected:
            raise ValueError(f'Frozen file has changed: {name}')
    model = json.loads((HERE / 'model.json').read_bytes())
    data, _, _ = dataset(args.source, HOLD)
    predicted = predict_tokens(model, data['x'], data['recent'], data['wrong'])
    result = scoring(data, predicted)
    with args.output.open('x') as fp:
        json.dump({key:result[key] for key in PUBLIC_FIELDS}, fp, allow_nan=False, indent=2)
        fp.write('\n')


if __name__ == '__main__':
    main()
