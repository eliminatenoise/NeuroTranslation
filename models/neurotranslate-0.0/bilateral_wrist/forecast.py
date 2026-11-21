"""Bilateral wrist endpoints in the original two-dimensional camera frame."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .demo_math import HORIZONS, MASK, raw_transform, side_features
from .export_case import MODALITIES, PARAMETERS, SIDES, TREATMENTS, bounded, pack_case, pack_weights


def fingerprint(values):
    text = json.dumps(values, separators=(",", ":"), sort_keys=True, allow_nan=False)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def validate(package):
    if not isinstance(package, dict) or set(package) != {"format", "weights", "cases"}:
        raise ValueError("Expected exactly format, weights and cases in the wrist package.")
    if package["format"] != "wrist-forecast-v1":
        raise ValueError("Unsupported wrist package format.")
    if not isinstance(package["weights"], dict):
        raise ValueError("Expected named parameters in weights.")
    try:
        weights = pack_weights(package["weights"])
    except KeyError as exc:
        raise ValueError(f"Missing wrist parameter {exc}.") from exc
    if set(weights) != set(package["weights"]):
        raise ValueError("Unexpected parameter name in wrist package.")
    if not isinstance(package["cases"], list) or not 1 <= len(package["cases"]) <= 8:
        raise ValueError("Expected one to eight wrist histories.")
    cases = []
    for entry in package["cases"]:
        if not isinstance(entry, dict) or set(entry) not in (
            {"pose_px", "ecog_uv"}, {"pose_px", "ecog_uv", "future_px"}
        ):
            raise ValueError("A case requires earlier pose_px and ecog_uv, with an optional future_px reference.")
        # The export helper also accepts a flat six-joint training array; JSON has explicit arm axes.
        pose = bounded(entry["pose_px"], (15, 2, 3, 2))
        if "future_px" in entry:
            bounded(entry["future_px"], (2, 2, 2))
        # Discard the optional browser reference at the schema boundary.
        cases.append(pack_case(entry["ecog_uv"], pose))
    return weights, cases


def rms_normalize(x):
    return x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + 1e-5)


def temporal(x, p):
    """Single causal attention layer; the final token supplies both horizons."""
    states = x @ p["input_w"] + p["input_b"] + p["position"]
    normalized = rms_normalize(states)
    query, key, value = (normalized @ p[name] for name in ("q", "k", "v"))
    logits = (query @ key.swapaxes(-1, -2)) / np.sqrt(query.shape[-1])
    logits = np.where(MASK, -np.inf, logits)
    probabilities = np.exp(logits - logits.max(axis=-1, keepdims=True))
    probabilities /= probabilities.sum(axis=-1, keepdims=True)
    residual = states + (probabilities @ value) @ p["o"]
    hidden = np.tanh(rms_normalize(residual) @ p["ff1"] + p["ff1_b"])
    final = residual + hidden @ p["ff2"] + p["ff2_b"]
    return final[:, -1] @ p["readout"] + p["bias"]


def forecast(package, *, case_index=0, treatment="anchored", modality="full"):
    if treatment not in TREATMENTS or modality not in MODALITIES:
        raise ValueError("Select a supported wrist treatment and input modality.")
    weights, cases = validate(package)
    if type(case_index) is not int or not 0 <= case_index < len(cases):
        raise ValueError("Select an available case by its zero-based integer index.")
    case = cases[case_index]
    demo = json.loads(Path(__file__).with_name("provenance.json").read_text(encoding="utf-8"))
    voltage = np.asarray(case["ecog_uv"])[None]
    pose = np.asarray(case["pose_px"])
    method = f"transformer_{treatment}_{modality}_s17"
    origins, deltas = [], []
    for i, side in enumerate(SIDES):
        prefix = f"main__{side}__"
        w = {k[len(prefix):]: np.asarray(v) for k, v in weights.items() if k.startswith(prefix)}
        raw, anchor, velocity = side_features(voltage, pose[None, :, i])
        tokens = (raw - w["feature_mean"]) / w["feature_scale"]
        if modality == "pose":
            tokens[:, :, 10:] = 0
        params = {key: w[f"{method}__{key}"] for key in PARAMETERS}
        prediction = temporal(tokens, params)
        prior = velocity * w["damping"][:, None] if treatment == "anchored" else np.zeros_like(velocity)
        deltas.append(raw_transform(prediction, treatment, w["mean"], w["scale"], prior)[0])
        origins.append(anchor[0])
    delta = np.stack(deltas, axis=1)
    return {
        "domain": "bilateral_wrist_endpoint",
        "method": method,
        "case_index": case_index,
        "weight_source": "bundled simulation" if fingerprint(weights) == demo["weights_sha256"] else "local, unverified origin",
        "history_source": "bundled simulation" if fingerprint(case) in demo["history_sha256"] else "local, unverified origin",
        "horizons_frames": HORIZONS.astype(int).tolist(),
        "wrists": list(SIDES),
        "image_axes": ["x", "y"],
        "last_wrist_px": np.asarray(origins).tolist(),
        "displacement_px": delta.tolist(),
        "absolute_endpoint_px": (delta + np.asarray(origins)).tolist(),
    }
