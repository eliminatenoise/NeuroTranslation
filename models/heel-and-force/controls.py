"""Common-input and privileged comparisons fit inside each training split."""
import numpy as np
from network import encode_initial
from records import inputs, weights, subset

ALPHAS = (.01, .1, 1.)
RIDGES = ("ridge_full", "ridge_marker", "ridge_frozen")


def design(d, norm, kind):
    x, _ = inputs(d, norm)
    if kind == "ridge_marker":
        return x[:, :, :14].reshape(len(x), -1)
    if kind == "ridge_frozen":
        return encode_initial(x)
    return x.reshape(len(x), -1)


def fit_ridge(d, norm, kind):
    x = design(d, norm, kind)
    _, y = inputs(d, norm)
    w = weights(d)
    mx, my = w @ x, w @ y
    x, y = x - mx, y - my
    gram, rhs = x.T @ (w[:, None] * x), x.T @ (w[:, None] * y)
    params = {}
    for alpha in ALPHAS:
        beta = np.linalg.solve(gram + np.eye(len(gram)) * alpha, rhs)
        bias = my - mx @ beta
        params[alpha] = {"coef": beta.tolist(), "bias": bias.tolist()}
    return params


def ridge_predict(d, norm, kind, params):
    x = design(d, norm, kind)
    return (x @ params["coef"] + params["bias"]) * norm["ys"] + norm["ym"]


def combine(heel, force):
    return {k: np.concatenate((np.asarray(heel[k])[..., :3], np.asarray(force[k])[..., 3:]), axis=-1).tolist()
            for k in ("coef", "bias")}


def fit_simple(d, norm):
    x = design(d, norm, "ridge_marker")
    phase = {}
    for off in sorted(set(d["offset"])):
        sub = subset(d, d["offset"] == off)
        phase[str(off)] = float(weights(sub) @ sub["force_n"])
    return {"phase": phase, "knn_x": x.tolist(), "knn_y": np.column_stack((d["heel_delta_mm"], d["force_n"])).tolist(),
            "knn_group": np.unique(d["person"], return_inverse=True)[1].tolist()}


def simple_predict(d, norm, fitted):
    m = d["marker_mm"][:, :, 0]
    recent = (m[:, -1] - m[:, -7]) * (10 / 6)
    repeat = m[:, -1] - m[:, -11]
    current, old = d["privileged_force_n"].T.copy()
    complete_force = np.isfinite(current) & np.isfinite(old)
    current[~complete_force] = np.nan
    old[~complete_force] = np.nan
    nan = np.full_like(current, np.nan)
    xyz = np.broadcast_to(nan[:, None], (len(m), 3))
    phase = fitted["phase"]
    p = [phase[min(phase, key=lambda x: (abs(int(x) - o), int(x)))] for o in d["offset"]]
    xq = design(d, norm, "ridge_marker")
    x, y, group = [np.asarray(fitted[k]) for k in ("knn_x", "knn_y", "knn_group")]
    knn = []
    for query in xq:
        order = np.argsort(((x - query) ** 2).sum(axis=1), kind="stable")
        _, i = np.unique(group[order], return_index=True)
        knn.append(y[order[np.sort(i)[:3]]].mean(axis=0))
    return {"stationary": np.column_stack((np.zeros_like(recent), nan)),
            "velocity": np.column_stack((recent, nan)), "repeat_motion": np.column_stack((repeat, nan)),
            "phase": np.column_stack((xyz, p)), "marker_knn": np.asarray(knn),
            "privileged_hold": np.column_stack((xyz, current)),
            "privileged_trend": np.column_stack((xyz, 2 * current - old))}
