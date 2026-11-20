"""Window selection, forecast equations and scoring from the frozen comparison."""
import time
from zipfile import ZipFile

import numpy as np

HORIZONS = (1, 3, 6, 12)
PEOPLE = {"TRAIN": ("p1", "p2", "p3", "p4"), "DEV": ("p5", "p6")}
CUTOFFS = tuple(range(15, 112, 16))


def read_windows(archive, partition):
    if partition not in PEOPLE:
        raise ValueError("Study admits TRAIN or previously assessed DEV only")
    rows, histories, measured = [], [], []
    with ZipFile(archive) as source:
        for activity in ("a09", "a10"):
            for person in PEOPLE[partition]:
                for segment in range(1, 61):
                    member = f"data/{activity}/{person}/s{segment:02}.txt"
                    with source.open(member) as stream:
                        clip = np.loadtxt(stream, delimiter=",", usecols=(9, 10, 11))
                    if clip.shape != (125, 3) or not np.isfinite(clip).all():
                        raise ValueError(f"Unexpected shape or values in {member}")
                    for origin in CUTOFFS:
                        rows.append((activity, person, str(segment), str(origin)))
                        histories.append(clip[origin - 15:origin + 1])
                        measured.append(clip[origin + np.array(HORIZONS)])
    if len(rows) != 840 * len(PEOPLE[partition]) or len(rows) != len(set(rows)):
        raise ValueError("Unexpected repeated or missing origin")
    return np.array(rows), np.stack(histories), np.stack(measured)


def fit_new(mod, state, x, y):
    center, scale = state["center"].numpy(), state["scale"].numpy()
    if not np.allclose(x.mean((0, 1)), center, atol=1e-12, rtol=0) or not np.allclose(
            x.std((0, 1)), scale, atol=1e-12, rtol=0):
        raise ValueError("TRAIN normalization disagrees with the previous fit")
    norm = (x - center) / scale
    coef, intercept = [], []
    for index, lead in enumerate(HORIZONS):
        if lead == 3:
            head = state["ridge"].numpy(), state["intercept"].numpy()
        else:
            head = mod.fit_ridge(norm, (y[:, index] - center) / scale)
        coef.append(head[0])
        intercept.append(head[1])
    return {"center": center, "scale": scale, "coef": np.concatenate(coef, axis=1),
            "intercept": np.concatenate(intercept)}


def direct(x, params):
    norm = (x - params["center"]) / params["scale"]
    deltas = norm.reshape(len(x), -1) @ params["coef"] + params["intercept"]
    return x[:, -1:, :] + deltas.reshape(len(x), len(HORIZONS), 3) * params["scale"]


def recursive(x, params):
    context = (x - params["center"]) / params["scale"]
    results = []
    for step in range(1, max(HORIZONS) + 1):
        delta = context.reshape(len(x), -1) @ params["coef"][:, :3] + params["intercept"][:3]
        prediction = context[:, -1, :] + delta
        if step in HORIZONS:
            results.append(prediction * params["scale"] + params["center"])
        context = np.concatenate((context[:, 1:, :], prediction[:, None, :]), axis=1)
    return np.stack(results, axis=1)


def repeat(x):
    return np.repeat(x[:, -1:, :], len(HORIZONS), axis=1)


def summarize_forecast(prediction, y):
    delta = prediction - y
    error = abs(delta)
    return {"mae": error.mean((0, 2)).tolist(), "mae_xyz": error.mean(0).tolist(),
            "bias_xyz": delta.mean(0).tolist(), "q95_absolute_error_xyz": np.quantile(error, .95, axis=0).tolist()}


def interval(q, y):
    lo, hi = q[..., 0], q[..., -1]
    levels = np.arange(1, 10) / 10
    diff = y[..., None] - q
    loss = np.maximum(levels * diff, (levels - 1) * diff)
    return {"nominal": .8, "coverage_xyz": ((lo <= y) & (y <= hi)).mean(0).tolist(),
            "width_xyz": (hi - lo).mean(0).tolist(), "adjacent_crossings": int(np.count_nonzero(np.diff(q, axis=-1) < 0)),
            "reversed_outer_pairs": int(np.count_nonzero(lo > hi)), "pinball_loss_mean_q_xyz": loss.mean((0, 3)).tolist()}


def groups(ids):
    keys = {"pooled": np.full(len(ids), True)}
    for p in PEOPLE["DEV"]:
        keys[p] = ids[:, 1] == p
    for activity in ("a09", "a10"):
        keys[activity] = ids[:, 0] == activity
        for p in PEOPLE["DEV"]:
            keys[p + "/" + activity] = keys[p] & keys[activity]
    return keys


def live_timing(models, history, count=64):
    collected = {name: [] for name in models}
    for _, fn in models.items():
        for _ in range(4):
            fn(history)
    names = list(models)
    for i in range(count):
        for key in names[i % len(names):] + names[:i % len(names)]:
            before = time.perf_counter_ns()
            out = models[key](history)
            collected[key].append((time.perf_counter_ns() - before) / 1e6)
            if not np.isfinite(out).all():
                raise ValueError("Nonfinite live output")
    return {name: {"calls": count, "p50_ms": float(np.median(sample)),
                   "p95_ms": float(np.quantile(sample, .95))} for name, sample in collected.items()}
