"""Use recorded muscle-voltage features to forecast load on two plates."""

from argparse import ArgumentParser
from pathlib import Path
import json

import numpy as np

from forecast_model import init_cpu, predict


HERE = Path(__file__).resolve().parent


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, nargs='?', default=HERE/'EXAMPLE.npz')
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('Choose one or more CPU threads.')
    init_cpu(args.threads)
    protocol = json.loads((HERE/'MODEL.json').read_bytes())
    with np.load(HERE/'WEIGHTS.npz', allow_pickle=False) as source:
        weights = dict(source)
    with np.load(args.input, allow_pickle=False) as source:
        if tuple(source['muscles']) != tuple(weights['muscles']):
            parser.error('Supply the 16 muscle names and order given in the guide.')
        history = source['history']
    force, probability = predict(history, weights, protocol)
    print(json.dumps({'plate_order': [1, 2], 'forecast_horizon_ms': 100, 'force_quantity': 'plate-normal impulse',
                      'unit': 'N s', 'probability_event_strictly_over_ns': 1,
                      'example_is_generated': args.input.resolve() == HERE/'EXAMPLE.npz',
                      'impulse': {method: values.tolist() for method, values in force.items()},
                      'load_probability': {method: values.tolist() for method, values in probability.items()}},
                     indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
