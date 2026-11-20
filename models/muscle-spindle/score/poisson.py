"""Train, serialize and replay the held-prefix count regressions in double precision."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

MODES = {
    "history": [4],
    "force": [0, 2],
    "position": [1, 3],
    "mechanics": [0, 1, 2, 3],
    "all": [0, 1, 2, 3, 4],
}
KEYS = ("prefix", "afferent", "trial", "bin_index")
RIDGE = 0.01


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, allow_nan=False, indent=2) + "\n")


def versioned_input(path, population="synthetic-test"):
    with np.load(path, allow_pickle=False) as data:
        meta = {name: data[name].copy() for name in KEYS}
        y = data["y_count"].copy()
        x = data["X"].astype("float64")
        means = data["mech_mean"].astype("float64")
    if means.shape != x[:, :, :2].shape or x.shape[1:] != (5, 5):
        raise ValueError("Input tensor must be five completed bins by five features")
    x[:, :, :2] = means
    if (
        not np.isfinite(x).all()
        or not np.isfinite(y).all()
        or np.min(y) < 0
        or np.any(y != np.floor(y))
    ):
        raise ValueError("Nonfinite inputs or non-integer/negative spike counts")
    prefixes = meta["prefix"].astype(int)
    expected = {0} if population == "strict-afferent" else {0, 1, 4}
    if population == "strict-afferent" and set(meta["afferent"]) != {
        "aff004",
        "aff015",
        "aff017",
    }:
        raise ValueError("Unexpected available original afferents")
    if set(prefixes) != expected or any(
        str(a)[3] != str(p) for p, a in zip(prefixes, meta["afferent"])
    ):
        raise ValueError("Unexpected held-group identity")
    return x, y, meta


def held_folds(meta, population):
    if population == "strict-afferent":
        return [
            (name, meta["afferent"] == name, name)
            for name in sorted(set(meta["afferent"].tolist()))
        ]
    return [(name, meta["prefix"] == name, "prefix" + str(name)) for name in (0, 1, 4)]


def group_ids(*columns):
    """Integer IDs for arbitrary combinations of integer or Unicode labels."""
    codes = np.stack([np.unique(c, return_inverse=True)[1] for c in columns], axis=1)
    return np.unique(codes, axis=0, return_inverse=True)[1]


def hierarchy(meta):
    return [group_ids(*(meta[k] for k in KEYS[:i])) for i in (1, 2, 3)]


def balanced_weights(meta):
    """Each group divides its parent weight equally among its children."""
    ids = hierarchy(meta)
    mass = np.ones(len(ids[0])) / len(np.unique(ids[0]))
    for parent, child in zip(ids[:-1], ids[1:]):
        children = np.unique(np.column_stack((parent, child)), axis=0)
        mass /= np.bincount(children[:, 0])[parent]
    return mass / np.bincount(ids[-1])[ids[-1]]


def subset(meta, select):
    return {k: v[select] for k, v in meta.items()}


def earlier_indices(meta):
    """Look up only a disjoint five-bin earlier window from the same recording/trial."""
    rows = list(zip(*(meta[k].tolist() for k in KEYS)))
    index = {key: i for i, key in enumerate(rows)}
    if len(index) != len(rows):
        raise ValueError("Duplicate source row identity")
    return np.array(
        [index.get((*key[:-1], key[-1] - 5), -1) for key in rows], dtype=int
    )


def fit(x, y, weights, fields):
    data = x[:, :, fields]
    mu = np.einsum("n,ntc->c", weights, data, optimize=True) / data.shape[1]
    var = (
        np.einsum("n,ntc->c", weights, (data - mu) ** 2, optimize=True) / data.shape[1]
    )
    sd = np.sqrt(var)
    sd[sd < 1e-8] = 1.0
    z = np.ascontiguousarray(np.clip((data - mu) / sd, -10, 10).reshape(len(y), -1))
    target_mean = weights @ y
    if target_mean == 0:
        # The exact boundary solution of the all-zero Poisson likelihood is zero everywhere.
        return dict(
            fields=fields, mean=mu.tolist(), scale=sd.tolist(), zero_boundary=True
        )
    start = np.zeros(z.shape[1] + 1)
    start[0] = np.log(target_mean)

    def loss(parameters):
        eta = parameters[0] + z @ parameters[1:]
        rate = np.exp(eta)
        residual = weights * (rate - y)
        obj = weights @ (rate - y * eta) + 0.5 * RIDGE * (
            parameters[1:] @ parameters[1:]
        )
        gradient = np.r_[residual.sum(), z.T @ residual + RIDGE * parameters[1:]]
        return obj, gradient

    result = minimize(
        loss,
        start,
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 400, "gtol": 1e-8, "ftol": 1e-12, "maxls": 32},
    )
    if not result.success or not np.isfinite(result.fun):
        raise ValueError(f"Poisson fit failed: {result.message}")
    return dict(
        fields=fields,
        mean=mu.tolist(),
        scale=sd.tolist(),
        intercept=float(result.x[0]),
        coefficients=result.x[1:].reshape(5, len(fields)).tolist(),
        ridge=RIDGE,
        iterations=int(result.nit),
        objective=float(result.fun),
        gradient_inf=float(np.abs(result.jac).max()),
    )


def predict(x, params):
    if params.get("zero_boundary"):
        return np.zeros(len(x))
    z = np.clip((x[:, :, params["fields"]] - params["mean"]) / params["scale"], -10, 10)
    rates = np.exp(
        params["intercept"] + np.einsum("ntc,tc->n", z, params["coefficients"])
    )
    if not np.isfinite(rates).all():
        raise ValueError("Nonfinite held prediction")
    return rates


def run(window_file, out, population="synthetic-test"):
    x, y, meta = versioned_input(window_file, population)
    prior = earlier_indices(meta)
    held_rates = {
        name: np.full(len(y), np.nan)
        for name in [
            "constant",
            "recent_one",
            "recent_five",
            "recent_smoothed",
            *MODES,
            "stale",
        ]
    }
    output = {"population": population, "window_sha256": sha(window_file), "folds": {}}
    for held, test, _ in held_folds(meta, population):
        train = ~test
        train_meta = subset(meta, train)
        weights = balanced_weights(train_meta)
        if not np.isclose(weights.sum(), 1):
            raise ValueError("Training balance")
        train_mean = float(weights @ y[train])
        folds = {
            "train_members": sorted(set(train_meta["afferent"].tolist())),
            "test_members": sorted(set(meta["afferent"][test].tolist())),
            "training_mean_spikes": train_mean,
            "modes": {},
        }
        if set(folds["train_members"]) & set(folds["test_members"]):
            raise ValueError("Held recording leaked into training")
        output["folds"][str(held)] = folds
        recent = x[test, :, 4]
        for name, value in (
            ("constant", train_mean),
            ("recent_one", recent[:, -1]),
            ("recent_five", recent.mean(axis=1)),
            ("recent_smoothed", (recent.sum(axis=1) + train_mean) / 6),
        ):
            held_rates[name][test] = value
        for mode, fields in MODES.items():
            params = fit(x[train], y[train], weights, fields)
            folds["modes"][mode] = params
            held_rates[mode][test] = predict(x[test], params)
        eligible = test & (prior >= 0)
        shifted = x[eligible].copy()
        shifted[:, :, :4] = x[prior[eligible], :, :4]
        held_rates["stale"][eligible] = predict(shifted, folds["modes"]["all"])
    out.mkdir(parents=True, exist_ok=True)
    dump(out / "coefficients.json", output)
    np.savez_compressed(
        out / "poisson-oof.npz", **meta, population=population, y_count=y, **held_rates
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("windows", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--population",
        required=True,
        choices=("strict", "mixed-clock", "strict-afferent"),
    )
    args = parser.parse_args()
    run(args.windows, args.out, args.population)
