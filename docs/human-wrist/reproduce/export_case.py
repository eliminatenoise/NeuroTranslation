"""Pack seed-17 numeric parameters and one bilateral camera/voltage history for the offline reader."""
import argparse
import json
import os
from pathlib import Path

import numpy as np

SIDES = ("right", "left")
MODALITIES = ("full", "pose")
TREATMENTS = ("direct", "anchored", "bounded_zero")
PARAMETERS = dict(input_w=(26, 8), input_b=(8,), position=(5, 8), q=(8, 8), k=(8, 8), v=(8, 8),
                  o=(8, 8), ff1=(8, 12), ff1_b=(12,), ff2=(12, 8), ff2_b=(8,), readout=(8, 4), bias=(4,))
SCALERS = dict(feature_mean=(26,), feature_scale=(26,), mean=(2, 2), scale=(2, 2), damping=(2,))


def bounded(array, shape):
    array = np.asarray(array)
    if array.shape != shape or array.dtype.kind not in "iuf" or not np.isfinite(array).all() or np.max(np.abs(array)) > 1e8:
        raise ValueError(f"Expected a finite numeric array with shape {shape} and absolute values at most 1e8.")
    return array.astype(np.float64, copy=False).tolist()


def pack_weights(weights):
    values = {}
    for side in SIDES:
        prefix = f"main__{side}__"
        for name, shape in SCALERS.items():
            values[prefix + name] = bounded(weights[prefix + name], shape)
        if np.any(np.array(values[prefix + "feature_scale"]) < 1e-8) or np.any(np.array(values[prefix + "scale"]) < 1):
            raise ValueError("Invalid feature or target scale")
        damping = np.array(values[prefix + "damping"])
        if np.any((damping < 0) | (damping > 1)):
            raise ValueError("Fitted damping must lie in [0, 1]")
        for treatment in TREATMENTS:
            for modality in MODALITIES:
                stem = prefix + f"transformer_{treatment}_{modality}_s17__"
                for name, shape in PARAMETERS.items():
                    values[stem + name] = bounded(weights[stem + name], shape)
    return values


def pack_case(ecog_uv, prior_pose_px, future_wrist_px=None):
    pose = np.asarray(prior_pose_px)
    if pose.shape == (15, 6, 2):
        pose = pose.reshape(15, 2, 3, 2)
    result = dict(ecog_uv=bounded(ecog_uv, (250, 8)), pose_px=bounded(pose, (15, 2, 3, 2)))
    voltage = np.asarray(ecog_uv)
    if (voltage == 0).all(axis=1).any() or not (np.ptp(voltage, axis=0) > 0).any():
        raise ValueError("Voltage history fails the recording-quality rule")
    if future_wrist_px is not None:
        result["future_px"] = bounded(future_wrist_px, (2, 2, 2))
    return result


def make_package(weights, cases):
    if not 1 <= len(cases) <= 8:
        raise ValueError("Supply one to eight bilateral examples.")
    return {"format": "wrist-forecast-v1", "weights": pack_weights(weights), "cases": list(cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("weights", type=Path, help="Trusted local fitted NPZ")
    parser.add_argument("inputs", type=Path, help="Trusted local earlier-input or training NPZ")
    parser.add_argument("output", type=Path, help="New private JSON file")
    parser.add_argument("--row", type=int, default=0, help="Zero-based row in the input file")
    parser.add_argument("--with-reference", action="store_true", help="Also read the matched future_wrist_px from this file")
    args = parser.parse_args()
    if args.row < 0:
        parser.error("A nonnegative row is required.")
    os.umask(0o077)
    with np.load(args.weights, allow_pickle=False) as weights, np.load(args.inputs, allow_pickle=False) as inputs:
        future = inputs["future_wrist_px"][args.row] if args.with_reference else None
        case = pack_case(inputs["ecog_uv"][args.row], inputs["prior_pose_px"][args.row], future)
        package = make_package(weights, [case])
    text = json.dumps(package, separators=(",", ":"), allow_nan=False) + "\n"
    if len(text.encode()) > 2 * 1024**2:
        raise ValueError("Package exceeds the browser limit of 2 MiB.")
    with args.output.open("x", encoding="utf-8") as output:
        output.write(text)


if __name__ == "__main__":
    main()
