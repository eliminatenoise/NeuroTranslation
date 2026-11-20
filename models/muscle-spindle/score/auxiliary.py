"""Sensitivity to weighting and to the exact data drawn for Transformer training."""

import argparse
from pathlib import Path

import numpy as np
from poisson import (
    MODES,
    dump,
    fit,
    group_ids,
    held_folds,
    predict,
    sha,
    versioned_input,
)

SEEDS = (1641, 2718, 3917)


def afferent_weights(members, trials):
    member = group_ids(members)
    trial = group_ids(members, trials)
    parents = np.unique(np.stack((member, trial), axis=1), axis=0)
    return 1.0 / (
        len(np.unique(member))
        * np.bincount(parents[:, 0])[member]
        * np.bincount(trial)[trial]
    )


def run(source, sampled, out, population="synthetic-test"):
    x, y, meta = versioned_input(source, population)
    rates = np.full((len(y), 4), np.nan)
    coefficients = {
        "population": population,
        "sampled_sha256": sha(sampled),
        "source_sha256": sha(source),
        "folds": {},
    }
    with np.load(sampled, allow_pickle=False) as draws:
        for held, test, sample_key in held_folds(meta, population):
            mask = ~test
            params = fit(
                x[mask],
                y[mask],
                afferent_weights(meta["afferent"][mask], meta["trial"][mask]),
                MODES["all"],
            )
            folds = {"afferent": params}
            coefficients["folds"][str(held)] = folds
            rates[~mask, 0] = predict(x[~mask], params)
            for i, seed in enumerate(SEEDS, 1):
                indices = draws[f"{sample_key}-seed{seed}"].reshape(-1)
                if (
                    len(indices) != 19200
                    or indices.min() < 0
                    or indices.max() >= len(x)
                    or not mask[indices].all()
                ):
                    raise ValueError("Incorrect multiset or held row leaked into fit")
                chosen, counts = np.unique(indices, return_counts=True)
                params = fit(x[chosen], y[chosen], counts / len(indices), MODES["all"])
                folds[str(seed)] = {
                    "n_distinct": len(chosen),
                    "n_draws": len(indices),
                    "params": params,
                }
                rates[~mask, i] = predict(x[~mask], params)
    np.savez_compressed(
        out / "auxiliary-oof.npz",
        **meta,
        population=population,
        y_count=y,
        afferent_weighted=rates[:, 0],
        sampled=rates[:, 1:],
        seeds=np.array(SEEDS),
    )
    dump(out / "auxiliary-coefficients.json", coefficients)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "sampled", "out"):
        parser.add_argument(name, type=Path)
    parser.add_argument(
        "--population",
        required=True,
        choices=("strict", "mixed-clock", "strict-afferent"),
    )
    args = parser.parse_args()
    run(args.source, args.sampled, args.out, args.population)
