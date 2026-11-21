"""A five-frame shared set forecaster for 2-D optical tracker positions."""
import json
from pathlib import Path

import numpy as np


PROTOCOL = json.loads(Path(__file__).with_name("protocol.json").read_text())
METHODS = ("shape", "no_shape", "persistence", "last_velocity", "half_velocity", "rigid")
HISTORY = PROTOCOL["history_frames"]
GEOMETRY = 7
EPS = np.finfo(np.float64).eps


def norms(x):
    return np.linalg.norm(x, axis=-1)


def slope(points, times, valid):
    """Pointwise observed least-squares velocity for arbitrary missing frames."""
    count = valid.sum(axis=0)
    centered_time = times[:, None] - (times @ valid / np.maximum(count, 1))[None, :]
    centered_time *= valid
    denom = np.sum(centered_time**2, axis=0)
    velocities = np.einsum("tk,tkd->kd", centered_time, np.where(valid[..., None], points, 0))
    return velocities / np.where(denom > 0, denom, 1)[:, None]


def rigid_motion(xy, seconds, future_s):
    """Constant translation and angular velocity fitted to matched oldest/current points."""
    p = xy[-1]
    matched = np.isfinite(xy[0]).all(1) & np.isfinite(p).all(1)
    if not matched.any():
        return p.copy()
    a, b = xy[0, matched], p[matched]
    ca, cb = a.mean(0), b.mean(0)
    a, b = a - ca, b - cb
    ratio = future_s / (seconds[-1] - seconds[0])
    cross = np.sum(a[:, 0]*b[:, 1] - a[:, 1]*b[:, 0])
    dot = np.sum(a*b)
    theta = ratio * np.arctan2(cross, dot)
    rot = np.array([[np.cos(theta), np.sin(theta)], [-np.sin(theta), np.cos(theta)]])
    return (p - cb) @ rot + cb + ratio * (cb - ca)


def observe(xy, seconds, horizon_s):
    """Construct causal observations. xy has [5, landmarks, 2], horizon_s is a duration."""
    xy, seconds = np.asarray(xy, dtype=np.float64), np.asarray(seconds, dtype=np.float64)
    if xy.ndim != 3 or xy.shape[0] != HISTORY or xy.shape[-1] != 2 or not xy.shape[1]:
        raise ValueError("Expected five 2-D frames with at least one landmark")
    if seconds.shape != (HISTORY,) or not np.isfinite(seconds).all():
        raise ValueError("Expected five finite timestamps in seconds")
    seconds = seconds - seconds[-1]
    gaps = np.diff(seconds)
    if (gaps <= 0).any() or not np.isfinite(horizon_s) or horizon_s <= 0:
        raise ValueError("Timestamps must increase and the horizon must be positive")
    if gaps.max() > PROTOCOL["maximum_interframe_gap_s"] or -seconds[0] > PROTOCOL["maximum_history_span_s"]:
        raise ValueError("Observed time gaps exceed the fitted prefix domain")
    valid = np.isfinite(xy).all(-1)
    good = valid[-1] & (valid.sum(0) >= PROTOCOL["minimum_observations_per_point_including_origin"])
    size = len(good)
    origin = xy[-1].copy()
    if not good.any():
        return None
    # Translation before regression avoids cancellation with large camera offsets.
    anchor = origin[good].mean(0)
    centered = xy - anchor
    positions = centered[-1, good]
    radius = float(np.sqrt(np.mean(norms(positions)**2)))
    long = slope(centered, seconds, valid)
    recent = slope(centered[-3:], seconds[-3:], valid[-3:])
    recent = np.where((valid[-3:].sum(0) >= 2)[:, None], recent, long)
    prior = np.max(np.where(valid[:-1], np.arange(HISTORY - 1)[:, None], -1), axis=0)
    indices = np.arange(size)
    age = -seconds[np.maximum(prior, 0)]
    last = (centered[-1] - centered[np.maximum(prior, 0), indices]) / age[:, None]
    last, recent, long = [x[good] for x in (last, recent, long)]
    global_recent, global_long = recent.mean(0), long.mean(0)
    # The common motion scale contains no body geometry, including in the ablation.
    activity = np.sqrt(np.mean((norms(last)**2 + norms(recent)**2 + norms(long)**2) / 3))
    activity = float(activity) if activity > 0 else 1.
    common = [
        norms(last)/activity, norms(recent)/activity, norms(long)/activity,
        norms(last-recent)/activity, norms(recent-long)/activity,
        norms(recent-global_recent)/activity, norms(long-global_long)/activity,
        np.full(len(last), norms(global_long)/activity), valid[:, good].mean(0),
        age[good]/(-seconds[0]), np.full(len(last), horizon_s/(-seconds[0])),
    ]
    shape = np.zeros((len(last), GEOMETRY))
    if radius > 0 and len(last) > 1:
        unit = positions/radius
        radius_each = norms(unit)
        eigen = np.linalg.eigvalsh(unit.T @ unit / len(unit))
        rel = unit[:, None, :] - unit[None, :, :]
        distance = norms(rel)
        # All neighbors contribute; no ordering- or tie-dependent nearest-point choice.
        affinity = np.exp(-np.minimum(distance**2 * 2., 700.))
        np.fill_diagonal(affinity, 0.)
        affinity /= np.maximum(affinity.sum(1, keepdims=True), np.finfo(float).tiny)
        neighbor_motion = affinity @ recent
        # Distance, aspect, radial motion and relative speed are unitless.
        shape = np.column_stack([
            radius_each, (affinity*distance).sum(1), distance.mean(1),
            np.full(len(last), max(float(eigen[0]), 0.)),
            np.sum(unit*(recent-global_recent), axis=1)/(activity*np.maximum(radius_each, EPS)),
            norms(recent-neighbor_motion)/activity,
            np.full(len(last), activity*horizon_s/radius),
        ])
    features = np.clip(np.column_stack([*common, shape]), -10., 10.)
    proposals = np.stack([np.zeros_like(last), last, recent, long,
                          np.broadcast_to(global_recent, last.shape),
                          np.broadcast_to(global_long, last.shape)], axis=1)*horizon_s
    return {"features": features, "proposals": proposals, "valid": good, "origin": origin,
            "radius": radius, "rigid": rigid_motion(xy, seconds, horizon_s)[good]}


def mix(features, proposals, weights, shape=True):
    if not shape:
        features = features.copy()
        features[:, -GEOMETRY:] = 0
    hidden = np.tanh(features @ weights["w1"] + weights["b1"])
    logits = hidden @ weights["w2"] + weights["b2"]
    gates = np.exp(logits - logits.max(axis=1, keepdims=True))
    gates /= gates.sum(axis=1, keepdims=True)
    return np.einsum("ki,kid->kd", gates, proposals)


def read_weights(path):
    saved = json.loads(Path(path).read_text())
    return {model: {key: np.asarray(value, dtype=float) for key, value in values.items()}
            for model, values in saved["models"].items()}


def forecast(xy, seconds, horizon_s, weights, *, all_methods=False):
    """Return [K,2] in input units; unavailable origins return NaN for that point."""
    observation = observe(xy, seconds, horizon_s)
    selected = METHODS if all_methods else ("shape",)
    estimates = {m: np.full((np.shape(xy)[1], 2), np.nan) for m in selected}
    if observation is not None:
        good = observation["valid"]
        origin = observation["origin"][good]
        proposals = observation["proposals"]
        for method in selected:
            if method in ("shape", "no_shape"):
                d = mix(observation["features"], proposals, weights[method], method == "shape")
                estimates[method][good] = origin + d
            elif method == "rigid":
                estimates[method][good] = observation["rigid"]
            else:
                multiplier = {"persistence": 0., "last_velocity": 1., "half_velocity": 0.5}[method]
                estimates[method][good] = origin + proposals[:, 1]*multiplier
    return estimates if all_methods else estimates["shape"]
