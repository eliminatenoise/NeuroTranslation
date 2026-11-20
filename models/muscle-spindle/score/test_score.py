"""Small, deterministic regression checks on artificial data and stage interfaces."""

import json
import tempfile
import unittest
from pathlib import Path

import auxiliary
import evaluate
import numpy as np
import poisson
from read_counts import predict_count


def fake_source():
    rng = np.random.default_rng(180)
    meta = {k: [] for k in poisson.KEYS}
    xs, ys = [], []
    for prefix, members in (
        (0, ("aff001", "aff002")),
        (1, ("aff101",)),
        (4, ("aff401",)),
    ):
        for i, aff in enumerate(members):
            for trial in range(1, 3 - i):
                n = 14 + 5 * i + trial
                tokens = rng.normal(size=(n + 5, 5))
                tokens[:, 4] = rng.poisson(1, n + 5)
                for j in range(5, n):
                    xs.append(tokens[j - 5 : j])
                    ys.append(tokens[j, 4])
                    for key, v in zip(meta, (prefix, aff, trial, j)):
                        meta[key].append(v)
    x = np.array(xs)
    return x, np.array(ys, dtype=int), {k: np.array(v) for k, v in meta.items()}


class CountScore(unittest.TestCase):
    def test_zero_and_positive(self):
        y = np.array([0.0, 0.0, 1.0, 2.0])
        pred = np.array([0.0, 1.0, 0.0, 2.0])
        d, e = evaluate.loss(y, pred)
        np.testing.assert_allclose(d, [2e-8, 2.0, -2 * np.log(1e-8) - 2 + 2e-8, 0])
        np.testing.assert_allclose(e, [0, 1, 1, 0])
        self.assertRaises(ValueError, evaluate.loss, y, -np.ones_like(y))

    def test_hierarchy_stale_and_folds(self):
        x, y, meta = fake_source()
        w = poisson.balanced_weights(meta)
        for prefix in np.unique(meta["prefix"]):
            np.testing.assert_allclose(w[meta["prefix"] == prefix].sum(), 1 / 3)
        member = meta["afferent"] == "aff001"
        for trial in (1, 2):
            np.testing.assert_allclose(
                w[member & (meta["trial"] == trial)].sum(), 1 / 12
            )
        prior = poisson.earlier_indices(meta)
        for now in np.flatnonzero(prior >= 0):
            source = prior[now]
            for key in ("afferent", "trial", "prefix"):
                self.assertEqual(meta[key][now], meta[key][source])
            self.assertEqual(meta["bin_index"][now] - meta["bin_index"][source], 5)
        np.testing.assert_array_equal(prior < 0, meta["bin_index"] < 10)
        self.assertRaises(
            ValueError,
            poisson.earlier_indices,
            {k: np.repeat(v, 2) for k, v in meta.items()},
        )
        held = meta["prefix"] == 4
        train = ~held
        wt = poisson.balanced_weights(poisson.subset(meta, train))
        a = poisson.fit(x[train], y[train], wt, [0, 4])
        x[held] += 10000
        b = poisson.fit(x[train], y[train], wt, [0, 4])
        self.assertEqual(a, b)
        np.testing.assert_allclose(
            np.average(x[train].mean(axis=1)[:, [0, 4]], axis=0, weights=wt), a["mean"]
        )
        null = poisson.fit(x[train], y[train] * 0, wt, [0, 4])
        self.assertTrue(null["zero_boundary"])
        np.testing.assert_array_equal(
            poisson.predict(x[held], null), np.zeros(held.sum())
        )
        # With constant features even the held outlier maps to the constant fitted intercept.
        constant = np.ones_like(x[train])
        params = poisson.fit(constant, y[train], wt, [0, 4])
        self.assertEqual(params["scale"], [1, 1])
        np.testing.assert_allclose(
            poisson.predict(x[held], params), np.average(y[train], weights=wt)
        )
        np.testing.assert_allclose(
            [predict_count(window, a) for window in x[:5]], poisson.predict(x[:5], a)
        )

    def test_balanced_reporting_and_calibration(self):
        _, y, meta = fake_source()
        pred = np.ones(len(y))
        mask = np.ones(len(y), dtype=bool)
        tab, _, bins = evaluate.summarize({"test": pred}, meta, y, mask, "full")
        score = tab["test", "fixed"]
        prefix_values = [v["mae"] for v in score["prefix"].values()]
        self.assertAlmostEqual(score["macro"]["all"]["mae"], sum(prefix_values) / 3)
        self.assertNotAlmostEqual(score["macro"]["all"]["mae"], np.abs(y - pred).mean())
        selected = [r for r in bins if r["prefix"] == "all" and r["left"] == 1]
        self.assertEqual(selected[0]["n_windows"], len(pred))
        self.assertAlmostEqual(
            selected[0]["observed"], score["macro"]["all"]["observed"]
        )

    def test_complete_pipeline(self):
        x, y, meta = fake_source()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            windows = root / "windows.npz"
            np.savez(windows, X=x, mech_mean=x[:, :, :2] + 0.002, y_count=y, **meta)
            poisson.run(windows, root)
            p = evaluate.load_npz(root / "poisson-oof.npz")
            # Change the entire held recording before entering the normal pipeline.
            # Its fold parameters, trained mean and normalization must stay identical.
            held_mask = meta["prefix"] == 4
            x_mut, y_mut = x.copy(), y.copy()
            x_mut[held_mask, :, :4] += 5
            x_mut[held_mask, :, 4] += 7
            y_mut[held_mask] += 17
            modified = root / "held-mutation.npz"
            np.savez(
                modified,
                X=x_mut,
                mech_mean=x_mut[:, :, :2] + 0.002,
                y_count=y_mut,
                **meta,
            )
            poisson.run(modified, root / "mutation")
            original_params = json.loads((root / "coefficients.json").read_text())[
                "folds"
            ]["4"]
            tested_params = json.loads(
                (root / "mutation" / "coefficients.json").read_text()
            )["folds"]["4"]
            self.assertEqual(tested_params, original_params)
            valid = np.isfinite(p["stale"])
            self.assertEqual(valid.sum(), (meta["bin_index"] >= 10).sum())
            seed_indices = {
                f"prefix{held}-seed{s}": np.random.default_rng(s).choice(
                    np.flatnonzero(meta["prefix"] != held), size=19200
                )
                for held in (0, 1, 4)
                for s in auxiliary.SEEDS
            }
            np.savez(root / "draws.npz", **seed_indices)
            auxiliary.run(windows, root / "draws.npz", root)
            modes = list(poisson.MODES)
            rate = np.stack([np.tile(p[k][:, None], (1, 3)) for k in modes], axis=1)
            np.savez(
                root / "mock-transformer.npz",
                rate=rate,
                seeds=np.array(evaluate.SEEDS),
                wrong_mechanics=np.tile(p["stale"][:, None], (1, 3)),
                modes=np.array(modes),
                y_count=y,
                **meta,
            )
            evaluate.run(
                root / "poisson-oof.npz",
                root / "mock-transformer.npz",
                root / "auxiliary-oof.npz",
                root,
            )
            summary = json.loads((root / "summary.json").read_text())
            self.assertFalse(
                summary["gates"]["transformer_over_primary_glm"]["pass_all"]
            )
            bad = {**meta, "trial": meta["trial"][::-1]}
            self.assertRaises(
                ValueError, evaluate.require_metadata, meta, {**bad, "y_count": y}, y
            )


if __name__ == "__main__":
    unittest.main()
