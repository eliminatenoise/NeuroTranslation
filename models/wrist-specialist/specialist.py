"""Forecast two right-wrist angles 250 ms ahead from binned motion and optional forearm signals."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
DOMAIN = "wrist_angle_specialist"
AXES = ("extension", "radial_deviation")
WEIGHTS = {
    "motion-17.npz": "d67bdaaf2ed3a7ceb0aad1b8f1704aa57a6e2dd0d2a159c0ad4bd5870325e672",
    "emg-head-and-scales.npz": "b1eec74f31773aa7beab16d0f5638771fd7ca5965459bc3a0dcfd3ee9f09c504",
}


@lru_cache(maxsize=1)
def _parameters():
    state = {}
    for name, expected in WEIGHTS.items():
        with (HERE / name).open("rb") as file:
            if hashlib.sha256(file.read()).hexdigest() != expected:
                raise ValueError(f"Packaged weight file has changed: {name}")
            file.seek(0)
            with np.load(file, allow_pickle=False) as bundle:
                for key in bundle.files:
                    state[key] = bundle[key]
    return state


def _valid_convolution(x, weight, bias):
    # Each output position uses three consecutive bins in the same order as Conv1d.
    frames = np.lib.stride_tricks.sliding_window_view(x, 3, axis=2)
    n, _, positions, _ = frames.shape
    rows = frames.transpose(0, 2, 1, 3).reshape(n, positions, -1)
    y = rows @ weight.reshape(len(weight), -1).T + bias
    return np.maximum(y, 0).transpose(0, 2, 1)


def _motion(bins, anchor, timing, w):
    x = ((bins[:, :, :2] - w["bins_center"]) / w["bins_scale"]).astype(np.float32)
    z = x.transpose(0, 2, 1)
    for layer in ("encoder.0", "encoder.2"):
        z = _valid_convolution(z, w[layer + ".weight"], w[layer + ".bias"])
    context = np.column_stack(((anchor - w["anchor_center"]) / w["anchor_scale"], timing)).astype(np.float32)
    joined = np.column_stack((z.reshape(len(bins), -1), context))
    hidden = np.maximum(joined @ w["predictor.0.weight"].T + w["predictor.0.bias"], 0)
    step = hidden @ w["predictor.2.weight"].T + w["predictor.2.bias"]
    return anchor + step.astype(np.float64) * w["residual_scale"] + w["residual_center"]


def _measurements(value):
    x = np.asarray(value)
    if x.dtype.kind not in "iuf" or not np.isfinite(x).all():
        raise ValueError("Measurements must be finite real numbers")
    return x.astype(np.float64, copy=False)


def forecast_angles(bins, anchor_deg, slot, mode):
    """Return the bare CNN angles, signed additive correction and resulting absolute angles, in degrees."""
    if mode not in ("emg", "motion"):
        raise ValueError("Choose emg or motion for the dedicated wrist specialist")
    bins, anchor, slot = _measurements(bins), _measurements(anchor_deg), np.asarray(slot)
    n = len(anchor) if anchor.ndim else 0
    channels = 6 if mode == "emg" else 2
    if not n or bins.shape != (n, 16, channels) or anchor.shape != (n, 2):
        raise ValueError(f"Expected bins [N,16,{channels}] and anchor_deg [N,2] for a nonempty batch")
    if slot.dtype.kind not in "iu" or slot.shape != (n,) or np.any((slot < 0) | (slot >= 6)):
        raise ValueError("Each row needs one integer cue slot from 0 through 5")
    if np.any(np.abs(anchor) > 180) or np.any(np.abs(bins[:, :, :2] + anchor[:, None]) > 180 + 1e-9):
        raise ValueError("Absolute angles must be in the encoder's admitted range")
    if mode == "emg" and np.any((bins[:, :, 2:] < 0) | (bins[:, :, 2:] > 65535)):
        raise ValueError("Forearm amplitudes must be bipolar RMS microvolts within the source range")
    w = _parameters()
    timing = np.eye(6)[slot]
    motion = _motion(bins, anchor, timing, w)
    correction = np.zeros_like(motion)
    if mode == "emg":
        continuous = np.column_stack((bins[:, :, :2].reshape(n, 32), anchor, bins[:, :, 2:6].reshape(n, 64)))
        scaled = (continuous - w["ridge_center"]) / w["ridge_scale"]
        correction = np.column_stack((scaled, timing)) @ w["ridge_coef"]
    return {"motion_angle_deg":motion, "correction_deg":correction, "angle_deg":motion + correction}


def predict_record(record):
    if not isinstance(record, dict) or record.get("domain") != DOMAIN:
        raise ValueError(f"Choose domain {DOMAIN} for this specialist")
    result = forecast_angles(record["bins"], record["anchor_deg"], record["slot"], record["mode"])
    return {"domain":DOMAIN, "mode":record["mode"], "axes":list(AXES), "horizon_stored_ticks":128,
            "stored_hz":512, **{key:value.tolist() for key, value in result.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON containing the binned inputs")
    args = parser.parse_args()
    try:
        print(json.dumps(predict_record(json.loads(args.input.read_text(encoding="utf-8"))), indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Input or model error: {error}\n")
