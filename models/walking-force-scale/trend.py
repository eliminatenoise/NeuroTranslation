"""Trend forms, the sealed predictions P1 and P2, and the trend test (protocol section 11). NumPy only.

Forms, fitted to rung means only when at least three rungs lie below N_max:
  primary       MAE(N) = L + a / sqrt(N), least squares, L >= 0 (if the free fit gives L < 0, L = 0 and a is refitted);
  competitor    MAE(N) = c + b log2 N, least squares;
  competitor    carry-forward of the largest rung below N_max.
Every computation is closed-form and deterministic; bootstrap resamples are fitted in one vectorised pass.
"""
import numpy as np

FORMS = ('inverse_sqrt', 'log2', 'carry_forward')


def _ls2(u, y):
    """Least squares y = p0 + p1 u for each column of y (u: (k,), y: (k, B))."""
    um = u.mean()
    uc = u - um
    slope = (uc @ (y - y.mean(axis=0))) / (uc @ uc)
    return y.mean(axis=0) - slope * um, slope


def fit_forms(n, y):
    """n: (k,) rung sizes ascending; y: (k,) or (k, B) rung means. Returns params per form."""
    n = np.asarray(n, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    squeeze = y.ndim == 1
    y = y[:, None] if squeeze else y
    u = 1. / np.sqrt(n)
    big_l, a = _ls2(u, y)
    neg = big_l < 0
    if neg.any():
        a = np.where(neg, (u @ y) / (u @ u), a)
        big_l = np.where(neg, 0., big_l)
    c, b = _ls2(np.log2(n), y)
    params = {'inverse_sqrt': (big_l, a), 'log2': (c, b), 'carry_forward': (y[-1],)}
    if squeeze:
        params = {k: tuple(float(v[0]) for v in p) for k, p in params.items()}
    return params


def predict(form, params, n):
    if form == 'inverse_sqrt':
        return params[0] + params[1] / np.sqrt(n)
    if form == 'log2':
        return params[0] + params[1] * np.log2(n)
    return params[0]


def predictions(n, y, n_max):
    params = fit_forms(n, y)
    return {f: predict(f, params[f], float(n_max)) for f in FORMS}, params


def needs_trend(rungs_below):
    return len(rungs_below) >= 3


def bootstrap_predictions(n, person_values, idx, n_max):
    """person_values: (k rungs, people) in ascending code order; idx: (B, people). Returns form -> (B,)."""
    means = person_values[:, idx].mean(axis=2)  # (k, B)
    params = fit_forms(n, means)
    return {f: np.asarray(predict(f, params[f], float(n_max)), dtype=np.float64) for f in FORMS}


def trend_test(actual_point, actual_boot, predicted_point, predicted_boot):
    """Difference actual minus predicted at N_max on the same resamples; label held / faster / slower."""
    diff = np.asarray(actual_boot) - np.asarray(predicted_boot)
    lo, hi = np.percentile(diff, [2.5, 97.5])
    label = 'held' if lo <= 0 <= hi else ('faster' if hi < 0 else 'slower')
    return {'difference': float(actual_point - predicted_point), 'interval95': [float(lo), float(hi)],
            'label': label, 'absolute_miss': float(abs(actual_point - predicted_point))}


def p1_curve(curves_by_draw, n_max):
    """P1: draw-averaged pool-tail curve -> trend predictions of the relative gain at N_max.

    curves_by_draw: {draw: {N: tail-people mean error}} with the same N in every draw.
    """
    ns = sorted({n for c in curves_by_draw.values() for n in c})
    y = np.array([np.mean([curves_by_draw[d][n] for d in curves_by_draw]) for n in ns])
    preds, params = predictions(ns, y, n_max)
    base = float(y[0])
    return {'N': ns, 'curve': y.tolist(), 'n_max': n_max, 'predicted_mae_n_max': preds,
            'predicted_relative_gain': {f: (preds[f] - base) / base for f in FORMS},
            'params': {f: list(params[f]) for f in FORMS}}
