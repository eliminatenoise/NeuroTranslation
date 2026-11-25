"""Match the fixed Georgia pelvis input clock without using future samples."""

import numpy as np


SOURCE_HISTORY_FRAMES = 21
ORIGINAL_200HZ_FRAMES = 40
G = 9.80665


def motion_history(points_m, observed, issues, basis):
    points = np.asarray(points_m, dtype=np.float64)
    good = np.asarray(observed, dtype=np.bool_)
    issues = np.asarray(issues, dtype=np.int64)
    basis = np.asarray(basis, dtype=np.float64)
    if points.ndim != 3 or points.shape[1:] != (2, 3) or good.shape != points.shape[:2]:
        raise ValueError('Expected time-ordered metre coordinates and validity for two anterior pelvis points.')
    if (issues.ndim != 1 or not len(issues) or issues.min() < SOURCE_HISTORY_FRAMES or issues.max() > len(points)
            or basis.shape != (3, 3) or not np.allclose(basis @ basis.T, np.eye(3), rtol=0, atol=1e-12)):
        raise ValueError('Invalid original-clock issue frame or physical axes.')
    source_offsets = issues[:, None] + np.arange(-SOURCE_HISTORY_FRAMES, 0)
    validity = (good & np.isfinite(points).all(axis=-1))[source_offsets].all(axis=(1, 2))
    pelvis = points[source_offsets].mean(axis=2) @ basis.T
    held = np.empty((len(issues), ORIGINAL_200HZ_FRAMES, 3))
    held[:, 0::2] = (pelvis[:, :-1] + pelvis[:, 1:]) * .5
    held[:, 1::2] = pelvis[:, 1:]
    mean_positions = held.reshape(len(issues), 10, 4, 3).mean(axis=2)
    relative = mean_positions[:, 1:] - mean_positions[:, :1]
    relative[~validity] = np.nan
    return relative, validity, source_offsets


def fixed_readout(relative_m, weights, measured_mass_kg, slope_deg):
    relative = np.asarray(relative_m, dtype=np.float64)
    if relative.ndim != 3 or relative.shape[1:] != (9, 3) or not np.isfinite(relative).all():
        raise ValueError('Expected one or more complete verified pelvis histories.')
    if not np.isfinite(measured_mass_kg) or measured_mass_kg <= 0 or not np.isfinite(slope_deg) or abs(slope_deg) >= 90:
        raise ValueError('Expected separately measured mass and a verified belt angle.')
    center, scale, coefficient, offset = (
        weights['pelvis_trajectory.' + key] for key in ('center', 'scale', 'coefficients', 'intercept'))
    if center.shape != (27,) or scale.shape != (27,) or coefficient.shape != (27, 2) or offset.shape != (2,):
        raise ValueError('The fixed Georgia trajectory readout has a different shape.')
    if not (scale > 0).all():
        raise ValueError('The saved scale is invalid.')
    reference = measured_mass_kg * G * np.cos(np.deg2rad(slope_deg)) * .1
    normalized = (relative.reshape(len(relative), 27) - center) / scale
    # The two original readouts are added. Individual belts have a different arrangement.
    estimate = (normalized @ coefficient + offset).sum(axis=1) * reference
    return np.full(len(relative), reference), estimate
