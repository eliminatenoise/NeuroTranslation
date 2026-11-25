"""Forecast the next tenth of a second of treadmill load from earlier muscle readings."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from forecast_model import RepeatedAttention, init_cpu


HERE = Path(__file__).resolve().parent
MUSCLES = ('LBF', 'LTA', 'LRF', 'RBF', 'RTA', 'RRF')
DEPTHS = (1, 3, 5, 7, 9)
SEEDS = (20261125, 20261126)
GRAVITY = 9.80665
HORIZON_SECONDS = .1


def relative_history(volts):
    """Produce seven observed bins from 400 earlier voltage rows."""
    voltage = np.asarray(volts, dtype=np.float64)
    if voltage.shape != (400, len(MUSCLES)) or not np.isfinite(voltage).all():
        raise ValueError('Supply exactly 400 finite voltage rows for the six named muscle channels.')
    bins = voltage.reshape(10, 40, len(MUSCLES))
    centered = bins - bins[:, :1, :]
    centered -= centered.mean(axis=1, keepdims=True)
    energies = np.square(centered).mean(axis=1)
    earlier = np.stack([energies[:index].sum(axis=0) for index in range(3, 10)])
    count = np.arange(3, 10)[:, None]
    if not (earlier > 0).all():
        raise ValueError('Every channel needs measurable variation in its first three voltage bins.')
    relative = np.log1p(np.sqrt(energies[3:] * count / earlier))
    if not np.isfinite(relative).all():
        raise ValueError('The voltage input is outside the supported numerical range.')
    return relative.astype(np.float32)[None, :, :]


def read_muscles(path):
    if path.suffix.lower() == '.npz':
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != {'relative', 'muscles'} or tuple(data['muscles']) != MUSCLES:
                raise ValueError('Use the documented relative array and six muscle labels in order.')
            return data['relative']
    if path.suffix.lower() != '.csv':
        raise ValueError('Choose a voltage CSV or a prepared NumPy file.')
    with path.open(newline='', encoding='utf-8-sig') as stream:
        rows = csv.reader(stream)
        if tuple(next(rows, ())) != MUSCLES:
            raise ValueError('The CSV header must be LBF,LTA,LRF,RBF,RTA,RRF.')
        return relative_history([[float(value) for value in row] for row in rows])


def gravity_impulse(mass_kg, slope_degrees):
    mass = np.asarray(mass_kg, dtype=np.float64)
    slope = np.asarray(slope_degrees, dtype=np.float64)
    if not np.isfinite(mass).all() or (mass <= 0).any():
        raise ValueError('Body mass must be a finite positive number in kilograms.')
    if not np.isfinite(slope).all() or (np.abs(slope) >= 90).any():
        raise ValueError('Slope must be a finite angle between −90 and 90 degrees.')
    return mass * GRAVITY * np.cos(np.deg2rad(slope)) * HORIZON_SECONDS


def check_histories(relative):
    values = np.asarray(relative, dtype=np.float32)
    if values.ndim != 3 or values.shape[1:] != (7, len(MUSCLES)) or not len(values) or not np.isfinite(values).all():
        raise ValueError('Use one or more complete histories containing seven relative bins and six named channels.')
    return values.astype(np.float64).reshape(len(values), 7 * len(MUSCLES))


def attention_model(weights, depth, seed, has_mass):
    model = RepeatedAttention(depth)
    model.project = nn.Linear(12, 32)
    model.positions = nn.Parameter(torch.zeros(10, 32))
    model.readout = nn.Sequential(nn.LayerNorm(32), nn.Linear(32, 2))
    prefix = f'compact.{"known_mass" if has_mass else "muscle"}.p{depth}.{seed}.'
    model.load_state_dict({key: torch.from_numpy(weights[prefix + key]) for key in model.state_dict()}, strict=True)
    scale = tuple(weights[prefix + name] for name in ('center', 'scale', 'location', 'unit'))
    return model.eval(), scale


def attention_forecast(features, weights, depth, has_mass):
    estimates = []
    for seed in SEEDS:
        model, (center, scale, location, unit) = attention_model(weights, depth, seed, has_mass)
        values = np.zeros((len(features), 10, 12), dtype=np.float32)
        values[:, 3:, :6] = (features.reshape(len(features), 7, 6) - center) / scale
        values[:, 3:, 6:] = 1.
        with torch.inference_mode():
            estimate = torch.cat([model(batch) for batch in torch.from_numpy(values).split(256)]).numpy().astype(np.float64)
        estimates.append(estimate * unit + location)
    return np.mean(estimates, axis=0)


def linear_forecast(features, weights, prefix, coefficient_key='slope'):
    center, scale, coefficient, intercept = (
        weights[prefix + name] for name in ('center', 'scale', coefficient_key, 'intercept')
    )
    return ((features - center) / scale) @ coefficient + intercept


def predict(relative, weights, depths, gravity_total=None, research=None):
    features = check_histories(relative)
    has_mass = gravity_total is not None
    scale = np.broadcast_to(np.asarray(gravity_total, dtype=np.float64), (len(features),)) if has_mass else np.ones(len(features))
    reference = scale if has_mass else np.full(len(features), float(weights['linear.muscle.fixed_total']))
    context = 'known_mass' if has_mass else 'muscle'
    estimates = {'linear': linear_forecast(features, weights, f'linear.{context}.') * scale[:, None]}
    for depth in depths:
        if depth not in DEPTHS:
            raise ValueError('Choose an available compact checkpoint with 1, 3, 5, 7 or 9 passes.')
        estimates[f'attention_{depth}_passes'] = attention_forecast(features, weights, depth, has_mass) * scale[:, None]
    prefix = 'research.given_body_mass_and_slope.' if has_mass else 'research.muscle_only.'
    heads = {'relative_muscle': features}
    if research is not None:
        representation = np.asarray(research, dtype=np.float64)
        if representation.shape != (len(features), 2304) or not np.isfinite(representation).all():
            raise ValueError('Supply 2,304 finite Research Edition values for each matching muscle window.')
        heads['research_edition'] = representation
        heads['research_and_relative'] = np.column_stack((features, representation))
    applied = {name: linear_forecast(values, weights, prefix + name + '.', 'coefficient') * scale[:, None]
               for name, values in heads.items()}
    share = float(weights[prefix + 'blend_research_share'])
    if share == 0.:
        applied['late_blend'] = applied['relative_muscle']
    elif 'research_edition' in applied:
        applied['late_blend'] = share * applied['research_edition'] + (1. - share) * applied['relative_muscle']
    estimates.update({f'head_{name}': value for name, value in applied.items()})
    if not all(np.isfinite(value).all() for value in (*estimates.values(), reference)):
        raise ValueError('The forecast exceeded the supported numerical range.')
    return reference, estimates


def read_research(path, model):
    with np.load(path, allow_pickle=False) as data:
        expected = model['research_readout_state']
        for name in ('base_checkpoint_sha256', 'relative_projection_sha256', 'passes'):
            if data[name].shape != () or data[name].item() != expected[name]:
                raise ValueError('The Research Edition state identity does not match the fitted readout.')
        return data['representation']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=HERE / 'Example Muscles.csv')
    parser.add_argument('--mass-kg', type=float, help='Measured body mass in kilograms. Supply slope too.')
    parser.add_argument('--slope-deg', type=float, help='Belt slope in degrees. Use a negative number for downhill.')
    parser.add_argument('--passes', choices=DEPTHS, type=int, default=None, help='Number of passes for the compact attention forecast.')
    parser.add_argument('--threads', type=int, default=4, help='Number of CPU threads.')
    parser.add_argument('--research-state', type=Path, help='Optional matching exported Research Edition model state.')
    args = parser.parse_args()
    if (args.mass_kg is None) != (args.slope_deg is None):
        parser.error('Supply both measured body mass and slope, or leave both out.')
    if args.threads < 1:
        parser.error('Choose at least one CPU thread.')
    init_cpu(args.threads)
    try:
        model = json.loads((HERE / 'TRANSFER-MODEL.json').read_bytes())
        relative = read_muscles(args.input)
        mass_total = None if args.mass_kg is None else gravity_impulse(args.mass_kg, args.slope_deg)
        research = read_research(args.research_state, model) if args.research_state else None
        passes = args.passes if args.passes is not None else (9 if mass_total is not None else 5)
        with np.load(HERE / 'TRANSFER-WEIGHTS.npz', allow_pickle=False) as weights:
            reference, predictions = predict(relative, weights, (passes,), mass_total, research)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({
        'forecast_horizon_ms': 100, 'model_inputs': 'muscle_with_mass_and_slope' if mass_total is not None else 'muscle_only',
        'unit': 'newton-seconds', 'plates_in_recording_order': [1, 2], 'attention_passes': passes,
        'example_is_invented': args.input.resolve() == (HERE / 'Example Muscles.csv').resolve(),
        'fixed_total': reference.tolist(),
        'forecasts': {name: {'plate_impulse': values.tolist(), 'total_impulse': values.sum(axis=1).tolist()}
                      for name, values in predictions.items()},
    }, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
