"""Forecast the combined impulse on a treadmill from earlier pelvis motion."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from project_camera import fixed_readout, motion_history


HERE = Path(__file__).resolve().parent
FRAMES_BEFORE_ISSUE = list(range(-21, 0))
AXES = ['left', 'backward', 'away_from_belt']


def load_weights():
    artifact = HERE / 'pelvis-weights.npz'
    manifest = json.loads((HERE / 'MODEL.json').read_text(encoding='utf-8'))
    if sha256(artifact.read_bytes()).hexdigest() != manifest['portable_weights_sha256']:
        raise ValueError('The saved pelvis weights do not match this release.')
    with np.load(artifact, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def predict(data, weights):
    if (data['camera_frames_per_second'] != 100 or data['frame_offsets'] != FRAMES_BEFORE_ISSUE
            or data['coordinate_axes'] != AXES):
        raise ValueError('Use frames −21 through −1 at 100 Hz in left, backward and away-from-belt axes.')
    points = np.asarray(data['anterior_pelvis_markers_metres'], dtype=np.float64)
    if points.shape != (21, 2, 3):
        raise ValueError('Supply exactly 21 frames with two three-dimensional marker positions per frame.')
    valid = np.isfinite(points).all(axis=-1)
    relative, eligible, _ = motion_history(points, valid, np.array([21]), np.eye(3))
    if not eligible[0]:
        raise ValueError('Supply all three coordinates for both markers on every earlier frame.')
    static, estimate = fixed_readout(relative, weights, float(data['mass_kg']), float(data['slope_degrees']))
    return {'forecast_duration_ms': 100, 'last_camera_frame_ms_before_forecast': 10,
            'static_body_weight_impulse_newton_seconds': float(static[0]),
            'predicted_combined_impulse_newton_seconds': float(estimate[0])}


def main():
    cli = ArgumentParser(description=__doc__)
    cli.add_argument('recording', type=Path, default=HERE / 'Example camera frames.json', nargs='?')
    options = cli.parse_args()
    try:
        data = json.loads(options.recording.read_text(encoding='utf-8'))
        result = predict(data, load_weights())
    except (KeyError, OSError, TypeError, ValueError) as error:
        cli.error(str(error))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
