"""Run the optional movement blend on each of three fixed NeuroTranslate models."""

from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np

from base_runner import SEEDS, example, ordered_window, session


def blend_forecasts(counts, original, rule):
    endpoint = original[:, :, :2]
    length = np.linalg.norm(endpoint, axis=-1).mean(axis=0)
    agreement = np.linalg.norm(endpoint.mean(axis=0), axis=-1) / (length + 1e-6)
    latest = counts[:, :, -3:].mean(axis=-1)
    earlier = counts[:, :, :3].mean(axis=(1, 2))
    rate = np.log1p(latest.mean(axis=1))
    inputs = np.column_stack((np.log1p(length), np.log1p(original[:, :, 2].mean(axis=0)), agreement,
                              rate, rate - np.log1p(earlier), np.log1p(latest.std(axis=1))))
    standardized = np.clip((inputs - rule['mean']) / rule['scale'], -5, 5)
    logit = standardized @ np.asarray(rule['slope']) + rule['bias']
    blend = np.exp(-np.logaddexp(0., -logit))
    return original * blend[None, :, None], blend


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='JSON containing electrode_ids and counts')
    options = parser.parse_args()
    if options.input:
        source = json.loads(options.input.read_text(encoding='utf-8'))
        counts = ordered_window(source['electrode_ids'], source['counts'])
        origin = 'supplied counts'
    else:
        counts = example()
        origin = 'generated example'
    rule = json.loads(Path(__file__).with_name('BLEND.json').read_text(encoding='utf-8'))
    original = np.asarray([session(seed).run(['movement_mm'], {'counts': counts})[0] for seed in SEEDS],
                          dtype=np.float64)
    if original.shape != (len(SEEDS), 1, 3) or not np.isfinite(original).all():
        raise ValueError('The three models must each return a finite displacement estimate.')
    blended, blend = blend_forecasts(counts, original, rule)
    keys = ('x_change_mm', 'y_change_mm', 'distance_estimate_mm')
    models = [{'training_seed': seed, 'original': dict(zip(keys, first[0].tolist(), strict=True)),
               'blended': dict(zip(keys, second[0].tolist(), strict=True))}
              for seed, first, second in zip(SEEDS, original, blended, strict=True)]
    print(json.dumps({'input': origin, 'forecast_ahead_ms': 100, 'blend_weight': float(blend[0]),
                      'models': models}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
