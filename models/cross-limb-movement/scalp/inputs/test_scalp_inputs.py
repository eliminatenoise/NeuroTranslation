"""Synthetic contract tests; add --cohort/--scalp/--splits to audit the original cache."""
import argparse
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

import scalp_inputs as si
from reproduce_inputs import numerical_evidence

paths = argparse.Namespace(cohort=None, scalp=None, splits=None)


def fixture():
    n = 12
    ds = np.repeat([0, 1], 6)
    person = np.array(["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3)
    times = np.tile([100, 200, 300], 4)
    keys = dict(domain=ds, person=person, event=np.tile([1, 2, 3], 4), session=np.ones(n, int),
                cutoff=times, direction=np.where(ds == 0, -1, 0), block=np.zeros(n, int))
    values, masks = {}, {}
    for kind, per_study in si.SITES.items():
        mask = np.zeros((n, 3), bool)
        for d, names in enumerate(per_study):
            mask[ds == d, :len(names)] = True
        mask[0, 1] = False
        values[kind] = np.arange(n * 20 * 3 * 2, dtype=np.float32).reshape(n, 20, 3, 2)
        values[kind] *= mask[:, None, :, None]
        masks[kind] = mask
    sessions = np.ones(n, int)
    starts, ends = times - 35, times + 10
    donors = si.earlier_donors(keys, sessions, masks["central"], starts, ends)
    return si.ScalpInputs(keys, values, masks, sessions, starts, ends, donors)


class SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.inp = fixture()
        self.train = np.array([0, 1, 2, 6, 7, 8])
        self.scales = si.fit_normalizers(self.inp, self.train)

    def test_site_scale_only_observed_training_bins(self):
        rows = np.array([1, 2])
        expected = self.inp.values["central"][rows, :, 1, :].reshape(-1, 2).astype(float)
        got = self.scales["central"]["0"]
        self.assertEqual(got["count"][1], 40)
        np.testing.assert_allclose(got["mean"][1], expected.mean(0))
        np.testing.assert_allclose(got["scale"][1], expected.std(0))
        for kind in si.SITES:
            held = np.setdiff1d(np.arange(len(self.inp.donor)), self.train)
            self.inp.values[kind][held] = np.nan
            self.inp.mask[kind][held] = False
            self.inp.values[kind][0, :, 1, :] = np.nan  # unavailable training site
        self.assertEqual(self.scales, si.fit_normalizers(self.inp, self.train))

    def test_reference_and_padding(self):
        rows = np.arange(12)
        for kind in si.SITES:
            real = si.tokens(self.inp, self.scales, rows, kind).reshape(-1, 20, 3, 3)
            ref = si.tokens(self.inp, self.scales, rows, kind, "reference").reshape(-1, 20, 3, 3)
            np.testing.assert_array_equal(real[..., 2], ref[..., 2])
            self.assertTrue(np.all(ref[..., :2] == 0))
            self.assertTrue(np.all(real[..., :2][real[..., 2] == 0] == 0))
            if kind in ("eye", "neck"):
                self.assertFalse(real[self.inp.keys["domain"] == 1].any())
        self.inp.values["central"][0, :, 1, :] = np.nan
        self.assertTrue(np.isfinite(si.tokens(self.inp, self.scales, [0], "central")).all())
        self.inp.values["central"][0, :, 0, :] = np.nan
        with self.assertRaisesRegex(ValueError, "nonfinite observed"):
            si.tokens(self.inp, self.scales, [0], "central")

    def test_unseen_or_impossible_site_and_constant(self):
        self.inp.values["central"][self.train, :, 0] = 9
        rebuilt = si.fit_normalizers(self.inp, self.train)
        self.assertEqual(rebuilt["central"]["0"]["scale"][0], [1., 1.])
        self.assertEqual(rebuilt["central"]["0"]["mean"][0], [9., 9.])
        rebuilt["central"]["0"]["count"][0] = 0
        with self.assertRaisesRegex(ValueError, "no training"):
            si.tokens(self.inp, rebuilt, [0], "central")
        self.inp.mask["eye"][6, 0] = True
        with self.assertRaisesRegex(ValueError, "unsupported"):
            si.tokens(self.inp, self.scales, [6], "eye")

    def test_illegal_splits_indices_and_modes(self):
        for train in (self.train[1:], [0, 0, 1, 2], [-1], [1.5], [12]):
            with self.assertRaises(ValueError):
                si.fit_normalizers(self.inp, train)
        with self.assertRaisesRegex(ValueError, "unmatched"):
            si.tokens(self.inp, self.scales, [0], "central", "wrong")
        with self.assertRaises(ValueError):
            si.tokens(self.inp, self.scales, [1], "frontal", "wrong")
        with self.assertRaises(ValueError):
            si.tokens(self.inp, self.scales, [-1], "central")

    def test_donor_masks_controls_and_reordering(self):
        inp = self.inp
        donor = inp.donor.copy()
        self.assertEqual(donor[:3].tolist(), [-1, -1, 1])  # first named-site pattern differs
        np.testing.assert_array_equal(donor[3:6], [-1, 3, 4])
        rows = np.flatnonzero(donor >= 0)
        np.testing.assert_array_equal(si.tokens(inp, self.scales, rows, "central", "wrong"),
                                      si.tokens(inp, self.scales, donor[rows], "central"))
        order = np.random.default_rng(24).permutation(len(donor))
        shuffled = si.earlier_donors({k: v[order] for k, v in inp.keys.items()},
                                     inp.source_session[order], inp.mask["central"][order],
                                     inp.envelope_start[order], inp.envelope_end[order])
        for j, new_donor in enumerate(shuffled):
            self.assertEqual(-1 if new_donor < 0 else order[new_donor], donor[order[j]])
        inp.mask["central"][3, 0] = False
        with self.assertRaisesRegex(ValueError, "mask differs"):
            si.tokens(inp, self.scales, [4], "central", "wrong")

    def test_touching_envelopes_and_strata_boundaries(self):
        inp = self.inp
        def match():
            return si.earlier_donors(inp.keys, inp.source_session, inp.mask["central"],
                                     inp.envelope_start, inp.envelope_end)
        inp.envelope_start[4] = inp.envelope_end[3]
        self.assertEqual(match()[4], -1)
        self.assertEqual(match()[5], 4)
        inp.envelope_start[4] += 1
        self.assertEqual(match()[4], 3)
        for field in ("block", "direction", "session", "domain", "person"):
            old = inp.keys[field].copy()
            inp.keys[field][4] = "z" if field == "person" else 8
            self.assertEqual(match()[4], -1)
            inp.keys[field] = old
        inp.source_session[4] = 9
        self.assertEqual(match()[4], -1)


class FrozenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if paths.cohort is None:
            raise unittest.SkipTest("original cache paths not provided")
        cls.inp = si.load_inputs(paths.cohort, paths.scalp)
        with np.load(paths.splits, allow_pickle=False) as z:
            cls.fold = z["fold"]

    def test_all_source_counts_and_native_clock(self):
        counts = numerical_evidence(self.inp, self.fold)
        for study, expected in (("balance", [5179, 4010, 5179, 5179, 4963]),
                                ("way", [1764, 1764, 0, 0, 1602])):
            data = counts[study]["total"]
            self.assertEqual([data[k]["any_site"]["events"] for k in si.SITES] +
                             [data["wrong"]["events"]], expected)
        self.assertEqual(counts["balance"]["earlier_end_to_later_start_ticks_min_median_max"][0], 502)
        self.assertEqual(counts["way"]["earlier_end_to_later_start_ticks_min_median_max"][0], 2486)

    def test_all_scaled_histories_and_masks(self):
        inp = self.inp
        for f in range(3):
            train, held = (np.flatnonzero(self.fold != f), np.flatnonzero(self.fold == f))
            scales = si.fit_normalizers(inp, train)
            self.assertEqual(scales, json.loads(json.dumps(scales, allow_nan=False)))
            for kind in si.SITES:
                real = si.tokens(inp, scales, held, kind)
                ref = si.tokens(inp, scales, held, kind, "reference")
                np.testing.assert_array_equal(real[..., 2::3], ref[..., 2::3])
                np.testing.assert_array_equal(real[:, 0, 2::3], inp.mask[kind][held])
                self.assertFalse(ref.reshape(-1, 3)[:, :2].any())
                for d in (0, 1):
                    group = train[inp.keys["domain"][train] == d]
                    out = si.tokens(inp, scales, group, kind).reshape(-1, 20, 3, 3)
                    for s in range(3):
                        x = out[inp.mask[kind][group, s], :, s, :2].reshape(-1, 2).astype(np.float64)
                        if len(x):
                            np.testing.assert_allclose(x.mean(0), 0., atol=1e-6)
                            np.testing.assert_allclose(x.std(0), 1., atol=1e-6)
            matched = held[inp.donor[held] >= 0]
            np.testing.assert_array_equal(si.tokens(inp, scales, matched, "central", "wrong"),
                                          si.tokens(inp, scales, inp.donor[matched], "central"))

    def test_forbidden_cohort_members_never_loaded(self):
        original = np.load
        keys_read = []
        class KeysOnly:
            def __enter__(self):
                self.z = original(paths.cohort, allow_pickle=False)
                return self
            def __exit__(self, *args):
                self.z.close()
            def __getitem__(self, key):
                if key not in si.KEYS:
                    raise AssertionError(f"unauthorized cohort member {key}")
                keys_read.append(key)
                return self.z[key]
        def guard(path, **args):
            return KeysOnly() if path == paths.cohort else original(path, **args)
        with patch.object(si.np, "load", side_effect=guard):
            result = si.load_inputs(paths.cohort, paths.scalp)
        self.assertEqual(tuple(keys_read), si.KEYS)
        np.testing.assert_array_equal(result.donor, self.inp.donor)

    def test_key_permutation_mutated_site_mask_and_future_bin_fail_closed(self):
        keys = {k: a.copy() for k, a in self.inp.keys.items()}
        keys["event"][[0, 1]] = keys["event"][[1, 0]]
        self.assertNotEqual(si.typed_digest(keys), si.COHORT_KEYS_SHA256)
        with np.load(paths.scalp, allow_pickle=False) as z:
            source = {k: z["way_" + k] for k in si.FIELDS}
        rows = source["rows"]
        source["bin_last_offset"][-1] = 1
        with self.assertRaisesRegex(ValueError, "post-cutoff"):
            si._clock_checks(source, 1, self.inp.keys, rows)
        original = np.load
        class Mutated:
            def __enter__(self):
                self.z = original(paths.scalp, allow_pickle=False)
                return self
            def __exit__(self, *args):
                self.z.close()
            def __getitem__(self, key):
                a = self.z[key]
                if key == "way_good":
                    a[0, 0] ^= True
                return a
        def guard(path, **args):
            return Mutated() if path == paths.scalp else original(path, **args)
        with patch.object(si.np, "load", side_effect=guard), self.assertRaisesRegex(ValueError, "unrecognized paired"):
            si.load_inputs(paths.cohort, paths.scalp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cohort", "scalp", "splits"):
        parser.add_argument("--" + name, type=Path)
    paths, rest = parser.parse_known_args()
    if any([paths.cohort, paths.scalp, paths.splits]) and not all([paths.cohort, paths.scalp, paths.splits]):
        parser.error("complete original test requires all three paths")
    unittest.main(argv=[sys.argv[0], *rest])
