"""Synthetic invariance, time boundary, controls and inference tests; no participant inputs."""
import copy
import unittest

import numpy as np
from extract import angle, donor_indices, from_arrays, past_tokens
from fit import fit_ridge, fit_scaler, RotationTransformer, tensor
from portable import masked, predict, ridge_design, standardized, VARIANTS
from score import summarize
import torch


def source():
    n = 5600
    time = (np.arange(n) + 1) / 2000
    phase = np.arange(n) * .0003
    q = np.column_stack([np.cos(phase), np.sin(phase), np.zeros((n, 2))])
    seed = np.random.default_rng(2026)
    u = seed.normal(size=(32, n)); l = seed.normal(size=(32, n))
    code = np.where(np.arange(n) < n // 2, 611, 621)
    return time, code, q, u, l


class Tests(unittest.TestCase):
    def test_time_causality_sign_and_control(self):
        time, code, q, u, l = source()
        tri = from_arrays(time, code, q, u, l)
        t = tri.cutoff[0]
        np.testing.assert_allclose(tri.x[0], past_tokens(q[t-200:t+1], u[:, t-199:t+1], l[:, t-199:t+1], 611))
        q2 = q.copy(); q2[:t+1:2] *= -7; q2[t+1:] = [0, 1, 0, 0]
        u2 = u.copy(); u2[:, t+1:] *= 50
        tri2 = from_arrays(time, code, q2, u2, l)
        np.testing.assert_allclose(tri.x[0], tri2.x[0], atol=1e-9)
        self.assertGreater(abs(tri.y[0] - tri2.y[0]), 10)
        np.testing.assert_allclose(tri.y, 2 * np.rad2deg(.06), atol=1e-9)
        np.testing.assert_equal(tri.code[tri.donor], tri.code)
        self.assertTrue(np.all(abs(tri.cutoff[tri.donor] - tri.cutoff) > 400))
        np.testing.assert_equal(tri.wrong_tokens()[:, :, :3], tri.x[:, :, :3])
        np.testing.assert_equal(tri.wrong_tokens()[:, :, 3:], tri.x[tri.donor, :, 3:])
        for i in range(len(tri.x)):
            self.assertEqual(code[tri.cutoff[i]-200], code[tri.cutoff[i]+200])
        with self.assertRaises(ValueError):
            donor_indices(np.array([611, 611, 621, 621]), np.array([0, 200, 400, 600]))

    def test_broken_clock_invalid_history_and_zero_target(self):
        time, code, q, u, l = source()
        shifted = time.copy(); shifted[311] += .0001
        with self.assertRaisesRegex(ValueError, 'clock'):
            from_arrays(shifted, code, q, u, l)
        u[0, 25] = np.nan
        q[800] = 0
        trial = from_arrays(time, code, q, u, l)
        self.assertEqual(trial.excluded['611'], {'invalid_history': 3, 'invalid_target': 1})
        self.assertEqual(trial.x.shape[1:], (10, 9))

    def test_voltage_units(self):
        _, _, q, u, l = source()
        u = np.broadcast_to(np.arange(200, dtype=float), (32, 200))
        x = past_tokens(q[:201], u, np.ones_like(u), 621)
        np.testing.assert_allclose(x[:, 3], np.log1p(np.std(np.arange(20))))
        np.testing.assert_allclose(x[:, 4], np.log(2))
        np.testing.assert_allclose(x[:, 5], x[:, 3]); np.testing.assert_equal(x[:, 6:], 0)

    def test_weights_mask_and_portable(self):
        x = from_arrays(*source()).x
        groups = np.r_[np.zeros(len(x)-1), 1]
        scaler, w = fit_scaler(x, groups)
        self.assertAlmostEqual(w[:-1].sum(), w[-1])
        np.testing.assert_equal([scaler['mean'][2], scaler['scale'][2]], [0,1])
        z = standardized(x, scaler)
        net = RotationTransformer(width=8, heads=2, feedforward=12).eval()
        weights = {k: v.detach().tolist() for k, v in net.state_dict().items()}
        model = {'scaler': scaler, 'config': {'heads': 2, 'eps': 1e-5}, 'models': {m: weights for m in VARIANTS}}
        for method in VARIANTS:
            with torch.no_grad():
                expected = net(tensor(masked(z, method)), tensor(x[:, -1, 1])).clip(0, 180).numpy()
            np.testing.assert_allclose(predict(model, x, method), expected, atol=2e-5, rtol=0)
        perturbed = x.copy(); perturbed[:, :, 3:] += 200
        np.testing.assert_equal(predict(model, x, 'motion'), predict(model, perturbed, 'motion'))
        ridge = fit_ridge(ridge_design(z), np.ones(len(x)) * 3, w)
        np.testing.assert_allclose(ridge['bias'], 3, atol=1e-10)
        np.testing.assert_allclose(ridge['weight'], 0, atol=1e-10)

    def test_paired_gates(self):
        from portable import METHODS
        row = {'n': {'611': 2, '621': 4}, 'excluded': {str(t): {'invalid_history': 0, 'invalid_target': 0}
                for t in (611,621)}, 'mae_deg': {m: dict.fromkeys(['611','621','balanced'], 1.) for m in METHODS}}
        row['mae_deg']['full'] = dict.fromkeys(['611','621','balanced'], .5)
        people = {p: copy.deepcopy(row) for p in range(4)}
        summary = summarize(people)
        self.assertTrue(summary['incremental_gate_passes']); self.assertTrue(summary['regional_gates']['lower']['passes'])
        self.assertEqual(summary['comparator_minus_full']['motion']['descriptive_person_bootstrap_95_deg'], [.5,.5])
        for p in [0,1]:
            people[p]['mae_deg']['wrong'] = dict.fromkeys(['611','621','balanced'], .499)
        self.assertFalse(summarize(people)['incremental_gate_passes'])

if __name__ == '__main__':
    unittest.main()
