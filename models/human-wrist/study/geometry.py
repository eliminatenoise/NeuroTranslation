"""Fit projected arm movement from three recent intervals of camera frames."""

import numpy as np
from scipy.optimize import minimize

HORIZONS = (8, 15)
WINDOWS = (4, 8, 15)


def slopes(history, mode):
    """Return [N, side, coordinate, arm component, time window] image-plane slopes."""
    history = np.asarray(history, dtype=float)
    if history.ndim != 4 or history.shape[1:] != (15, 6, 2):
        raise ValueError(
            "Expected fifteen frames, six right-then-left landmarks and two image axes"
        )
    points = history.reshape(len(history), 15, 2, 3, 2)
    wrist, elbow, shoulder = (points[:, :, :, i] for i in range(3))
    if mode == "segments":
        series = np.stack((shoulder, elbow - shoulder, wrist - elbow), axis=-2)
    elif mode == "whole":
        series = wrist[:, :, :, None, :]
    else:
        raise ValueError("Unknown motion decomposition")
    slopes_by_window = []
    for window in WINDOWS:
        time = np.arange(window, dtype=float) - (window - 1) / 2
        slopes_by_window.append(
            np.einsum("t,ntscd->nsdc", time, series[:, -window:]) / (time @ time)
        )
    return np.stack(slopes_by_window, axis=-1)


def anchors(history):
    return history[:, -1, (0, 3), :]


def forecast(history, fit):
    predictors = slopes(history, fit["mode"])
    anchor = anchors(history)
    out = []
    for horizon, weights in zip(HORIZONS, fit["coefficients"], strict=True):
        weights = np.asarray(weights, dtype=float)
        # Side dimension 1 shares the same fitted dynamics between shoulders.
        change = (predictors * weights[None, :, None, :, :]).sum(axis=(-1, -2)) * horizon
        out.append(anchor + change)
    return np.stack(out, axis=1)


def train_one(x, y, event, scale):
    n = len(y)
    c = x.shape[-2]
    p = c * 3
    x = x.reshape(n, 2, p)
    _, inverse, count = np.unique(event, return_inverse=True, return_counts=True)
    w = 1 / (len(count) * count[inverse])
    prior = np.tile([0.0, 0.0, 1.0], c)
    matrix = np.kron(np.eye(c), np.ones((1, 3)))

    def fun(b):
        e = (np.einsum("ndp,p->nd", x, b) - y) / scale
        huber = np.sqrt(1.0 + (e**2).sum(axis=1))
        delta = b - prior
        value = w @ (huber - 1) + 0.025 * (delta @ delta) / p
        grad = np.einsum("n,nd,ndp->p", w / huber, e, x) / scale + 0.05 * delta / p
        return value, grad

    result = minimize(
        fun,
        prior,
        jac=True,
        method="SLSQP",
        bounds=[(0, 1)] * p,
        constraints=[{"type": "ineq", "fun": lambda b: 1 - matrix @ b, "jac": lambda b: -matrix}],
        options={"ftol": 1e-12, "maxiter": 1200},
    )
    if not result.success or np.any(result.x < -1e-8) or np.any(matrix @ result.x > 1 + 1e-8):
        raise ValueError(result.message)
    # Frank-Wolfe gap for the product of capped simplexes. Each linear minimization is a vertex search.
    grad = fun(result.x)[1].reshape(c, 3)
    min_linear = np.minimum(0, grad.min(1)).sum()
    gap = float(grad.ravel() @ result.x - min_linear)
    if gap > 1e-4:
        raise ValueError(f"Stationarity gap {gap}")
    return result.x.reshape(c, 3).tolist(), dict(
        events=len(count),
        sides=n,
        scale_px=scale,
        iterations=result.nit,
        objective=float(result.fun),
        optimality_gap=gap,
    )


def fit(history, targets, events, mode, separate):
    # Future measurements reside in training only.
    pred = slopes(history, mode)
    anchor = anchors(history)
    weights = []
    diags = []
    sides = np.arange(2)[None, :] * np.ones((len(history), 1), int)
    for j, h in enumerate(HORIZONS):
        dy = targets[:, j] - anchor
        valid = np.isfinite(pred).all(axis=(2, 3, 4)) & np.isfinite(dy).all(axis=2)
        if mode == "whole":
            allpose = history.reshape(len(history), 15, 2, 3, 2)
            valid &= np.isfinite(allpose).all(axis=(1, 3, 4))
        coeff = []
        diagnostics = []
        for side in range(2 if separate else 1):
            use = valid & (sides == side) if separate else valid
            i, _ = np.nonzero(use)
            scale = max(1.0, float(np.median(np.linalg.norm(dy[use], axis=1))))
            b, d = train_one(h * pred[use], dy[use], events[i], scale)
            coeff.append(b)
            diagnostics.append(d)
        weights.append(coeff)
        diags.append(diagnostics)
    return dict(mode=mode, coefficients=weights, diagnostics=diags)
