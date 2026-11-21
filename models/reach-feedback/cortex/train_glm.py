"""Original-balanced regularized Poisson GLMs and naive train-rate controls."""
import argparse
import json
import time

import numpy as np
import scipy
from scipy.optimize import minimize

from count_model import ARMS, glm_features, normalizers, original_weights, patches, predict
from study_io import HERE, arm_input, dump, load_inputs, npz, sha


def fit(data, arm):
    w = original_weights(data["original"])
    raw = arm_input(data, arm, data["ridge"])
    norm = normalizers(arm, raw, w)
    all_x = glm_features(*patches(norm, raw, np.float64))
    active = np.any(all_x != 0, axis=0)
    x = np.ascontiguousarray(all_x[:, active])
    y = data["delayed"].astype(np.float64).reshape(len(w), 230)
    mean = ((data["delayed"] * w[:, None, None]).sum(axis=(0, 1)) + .5) / (10 * w.sum() + 1.)
    anchor = np.tile(np.log(mean), 10)
    w /= w.sum()
    initial = np.vstack((np.zeros((x.shape[1], 230)), anchor))

    def value_gradient(flat):
        params = flat.reshape(initial.shape)
        coef, bias = params[:-1], params[-1]
        eta = x @ coef + bias
        rate = np.exp(eta)
        residual = w[:, None] * (rate - y)
        delta = bias - anchor
        value = np.einsum("ij,i->", rate - y * eta, w)
        value += .5 * (.35 * np.square(coef).sum() + .02 * np.square(delta).sum())
        grad = np.vstack((x.T @ residual + .35 * coef, residual.sum(axis=0) + .02 * delta))
        return value, grad.ravel()

    sol = minimize(value_gradient, initial.ravel(), jac=True, method="L-BFGS-B",
                   options={"maxiter":400, "gtol":1e-7, "ftol":1e-13, "maxls":50})
    grad = np.abs(sol.jac).max()
    if not sol.success or not np.isfinite(grad) or grad > 2e-4:
        raise RuntimeError(f"GLM convergence failure: {arm} {grad:g} {sol.message}")
    coef = np.zeros((all_x.shape[1], 230))
    final = sol.x.reshape(initial.shape)
    coef[active] = final[:-1]
    weights = {**norm, "family": np.array("glm"), "coefficient": coef,
               "intercept": final[-1], "unit_guide": data["unit_guide"]}
    native = np.exp(x @ final[:-1] + final[-1]).reshape(-1, 10, 23)
    port = predict(weights, **raw)
    np.testing.assert_allclose(native, port, atol=1e-10, rtol=1e-10)
    if not np.isfinite(port).all() or (port <= 0).any():
        raise ValueError("Nonpositive or nonfinite training predictions")
    return weights, {"iterations": sol.nit, "objective_evaluations": sol.nfev,
                     "initial_objective": float(value_gradient(initial.ravel())[0]),
                     "final_objective": float(sol.fun), "gradient_max": float(grad),
                     "convergence": str(sol.message), "parity_max_abs": float(abs(port-native).max()),
                     "windows": len(w), "originals": len(np.unique(data["original"])),
                     "active_features": int(active.sum()), "scipy": scipy.__version__}


def rates(data):
    def mean_for(rows):
        w = original_weights(data["original"][rows])
        return np.average(data["delayed"][rows], weights=w, axis=0)

    ordinal = data["ordinal"]
    ordinals = np.unique(ordinal)
    return {"train_mean": mean_for(np.arange(len(ordinal))), "ordinals": ordinals,
            "ordinal_rates": np.stack([mean_for(ordinal == o) for o in ordinals]),
            "unit_guide": data["unit_guide"]}


def main():
    data = load_inputs("train", fit=True)
    target = HERE / "weights"
    target.mkdir(exist_ok=True)
    if (HERE / "fit-lock.json").exists():
        raise RuntimeError("Heads already sealed")
    npz(target / "rates.npz", rates(data))
    for arm in ARMS:
        path = target / f"glm-{arm}.npz"
        done = HERE / f"fit-glm-{arm}.json"
        if done.exists():
            if sha(path) != json.loads(done.read_text())["weight_sha256"]:
                raise RuntimeError("Partial checkpoint mismatch")
            continue
        start = time.monotonic()
        weights, stats = fit(data, arm)
        npz(path, weights)
        stats.update(weight_sha256=sha(path), arm=arm, elapsed_s=time.monotonic()-start)
        dump(done, stats)
        print(arm, stats["iterations"], stats["elapsed_s"], flush=True)


if __name__ == "__main__":
    main()
