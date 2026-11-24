"""Forecast the next 100 ms of signed vertical impulse from ten force means."""

import argparse
import json
from pathlib import Path

try:
    import numpy as np
except ModuleNotFoundError as error:
    if error.name != "numpy":
        raise
    raise SystemExit("Install NumPy in the Python environment used to run forecast.py.") from None


SEEDS = (104, 211, 389)
GRU_METHODS = ("walking_gru_residual", "mixed_gru_residual", "mixed_gru_direct")
DEFAULT_FORCE_N = (0, 0, 0, 20, 105, 280, 510, 640, 700, 680)


def sigmoid(value):
    return .5 * (1. + np.tanh(.5 * value))


def recurrent_member(scaled, weights, method, seed):
    prefix = f"{method}/{seed}/"
    ih = weights[prefix + "history.weight_ih_l0"].T
    hh = weights[prefix + "history.weight_hh_l0"].T
    ib = weights[prefix + "history.bias_ih_l0"]
    hb = weights[prefix + "history.bias_hh_l0"]
    state = np.zeros((len(scaled), 24), dtype=np.float32)
    for reading in scaled.T:
        ir, iz, inn = np.split(reading[:, None] @ ih + ib, 3, axis=1)
        hr, hz, hn = np.split(state @ hh + hb, 3, axis=1)
        reset, retain = sigmoid(ir + hr), sigmoid(iz + hz)
        proposed = np.tanh(inn + reset * hn)
        state = (1. - retain) * proposed + retain * state
    head = weights[prefix + "head.weight"].T
    bias = weights[prefix + "head.bias"]
    output = (state @ head + bias)[:, 0]
    return (output + scaled[:, -1]) if method.endswith("_residual") else output


def forecast_members(readings, weights):
    values = np.asarray(readings, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    if values.ndim != 2 or values.shape[1] != 10 or not np.isfinite(values).all():
        raise ValueError("Provide ten finite force means in newtons, earliest first.")
    x = values / 1000.
    scaled = x.astype(np.float32)
    if not np.isfinite(scaled).all():
        raise ValueError("The readings exceed the range of the model input.")
    design = np.column_stack((x, np.ones(len(values))))
    results = {
        "persistence": values[:, -1] * .1,
        "recent_trend": (values[:, -1] + 3. * (values[:, -1] - values[:, -2])) * .1,
    }
    for method in ("walking_ridge", "mixed_ridge"):
        results[method] = (x[:, -1] + design @ weights[method]) * 100.
    for method in GRU_METHODS:
        members = [recurrent_member(scaled, weights, method, seed) for seed in SEEDS]
        results[method] = np.asarray(members, dtype=np.float64) * 100.
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-n", nargs=10, type=float, metavar="N",
                        help="Ten signed upward force means in newtons, earliest first, 20 ms per mean.")
    parser.add_argument("--weights", type=Path, default=Path(__file__).with_name("weights.npz"))
    args = parser.parse_args()
    with np.load(args.weights, allow_pickle=False) as weights:
        forecasts = forecast_members(args.force_n if args.force_n is not None else DEFAULT_FORCE_N, weights)
    answer = {name: float(values.mean()) for name, values in forecasts.items()}
    print(json.dumps({"input": "supplied" if args.force_n is not None else "generated example",
                      "horizon_ms": 100, "vertical_impulse_n_s": answer}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
