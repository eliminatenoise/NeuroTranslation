"""Forecast unsigned back sensor rotation from ten bins of past measurements."""
import argparse
import json
from pathlib import Path

import numpy as np

from portable import BASELINES, VARIANTS, predict

HERE = Path(__file__).resolve().parent

def forecast(model, request):
    if not isinstance(request, dict) or set(request) != {'tokens'}:
        raise ValueError("Supply a JSON object with one field named tokens.")
    raw = np.asarray(request['tokens'])
    if raw.shape != (10, 9) or not np.issubdtype(raw.dtype, np.number):
        raise ValueError("Supply ten rows of nine numeric features, in the order listed in model.json.")
    x = raw.astype(np.float64)[None, :, :]
    if not np.isfinite(x).all() or np.any(x[:, :, :2] < 0) or np.any(x[:, :, :2] > 180):
        raise ValueError("Use finite features and unsigned angles between 0 and 180 degrees.")
    return {method: float(predict(model, x, method)[0]) for method in BASELINES + VARIANTS}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=HERE / 'example.json')
    args = parser.parse_args()
    try:
        model = json.loads((HERE / 'model.json').read_text(encoding='utf-8'))
        request = json.loads(args.input.read_text(encoding='utf-8'))
        degrees = forecast(model, request)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Could not forecast rotation: {exc}\n")
    print(json.dumps({'horizon_ms': 100, 'unsigned_sensor_rotation_deg': degrees}, indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
