"""Predict the 250-ms distance from five camera samples and four optional regional spike bins."""
import argparse
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
REGIONS = ("CA1", "PFC")
OFFSETS = np.arange(-4, 1, dtype=float) * 0.25


def motion_features(cutoff, time_s, xy_cm):
    xy = np.asarray(xy_cm, dtype=float)
    times = np.asarray(time_s, dtype=float)
    if xy.shape[-2:] != (5, 2) or times.shape != xy.shape[:-1]:
        raise ValueError("Expected five camera positions with corresponding timestamps")
    ages = np.asarray(cutoff)[..., None] + OFFSETS - times
    if (not np.all(np.isfinite(xy)) or not np.all(np.isfinite(ages))
        or np.any(ages < -1e-9) or np.any(ages > 0.075000001)
        or np.any(np.diff(times, axis=-1) <= 0)):
        raise ValueError("Camera inputs must be finite, fresh, monotone and in the past")
    steps = np.diff(xy, axis=-2)
    lengths = np.linalg.norm(steps, axis=-1)
    speeds = lengths / np.diff(times, axis=-1)
    halves = np.linalg.norm(xy[..., -1, :] - xy[..., -3, :], axis=-1)
    whole = np.linalg.norm(xy[..., -1, :] - xy[..., 0, :], axis=-1)
    dot = np.sum(steps[..., :-1, :] * steps[..., 1:, :], axis=-1)
    denom = lengths[..., :-1] * lengths[..., 1:]
    cos = np.divide(dot, denom, out=np.zeros_like(dot), where=denom > 0)
    return np.concatenate([speeds, halves[...,None], whole[...,None], cos, ages[...,1:]], axis=-1)


def neural_features(regional_counts, unit_counts):
    counts = np.asarray(regional_counts, dtype=float)
    units = np.asarray(unit_counts, dtype=float)
    if counts.shape[-2:] != (4, 2) or units.shape != counts.shape[:-2]+(2,):
        raise ValueError("Expected four spike-count bins for CA1 and PFC and two unit counts")
    if (not np.all(np.isfinite(counts)) or np.any(counts < 0) or np.any(counts != np.floor(counts))
        or not np.all(np.isfinite(units)) or np.any(units <= 0) or np.any(units != np.floor(units))):
        raise ValueError("Counts must be whole numbers. Both regions must have recorded units")
    rate = counts / (0.25 * units[...,None,:])
    return np.log1p(rate).reshape(counts.shape[:-2] + (8,))


def ridge_predict(fit, features):
    z = (np.asarray(features) - fit["mean"]) / fit["scale"]
    return np.maximum(0, z @ fit["coefficient"] + fit["intercept"])


def predict_record(record, fitted):
    x = motion_features(record["cutoff_s"], record["prior_time_s"], record["prior_xy_cm"])
    n = neural_features(record["regional_counts"], record["unit_counts"])
    return {"constant_speed_cm":float(0.25 * x[3]), "motion_cm":float(ridge_predict(fitted["motion"], x)),
            "motion_and_firing_cm":float(ridge_predict(fitted["combined"], np.concatenate((x,n))))}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("input", nargs="?", type=Path, default=ROOT/"example-input.json")
    args = cli.parse_args()
    print(json.dumps(predict_record(json.loads(args.input.read_text()),
                                    json.loads((ROOT/"weights.json").read_text())), indent=2))
