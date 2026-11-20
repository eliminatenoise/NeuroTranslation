"""Synthetic, deterministic tests of the chronology, weights, donor lookup and score executable."""
from pathlib import Path
import gzip
import json
import tempfile
import unittest

import numpy as np

import score as s


class ScoringTests(unittest.TestCase):
    def test_deviance_floor_and_noncommuting_seed_mean(self):
        y = np.array([0, 2, 2])
        m = s.measures(y, np.array([0., 0., 2.]))
        np.testing.assert_allclose(m[:, 0], [0, 2, 0])
        np.testing.assert_allclose(m[:, 1], [2e-6, 2 * (2*np.log(2/1e-6) - 2 + 1e-6), 0])
        p = np.array([1., 3., 2.])
        self.assertAlmostEqual(s.measures(np.array([2.]), p)[:, 0].mean(), 2/3)
        self.assertEqual(s.measures(np.array([2.]), p.mean(keepdims=True))[0, 0], 0)

    def test_exact_block_reference_and_gaps(self):
        n, block, reps = 19, 4, 211
        hits = s.bootstrap_counts(n, reps, block, seed=91)
        starts = np.random.default_rng(91).integers(n-block+1, size=(reps, (n+block-1)//block))
        literal = np.array([[i for start in row for i in range(start, start+block)][:n] for row in starts])
        np.testing.assert_array_equal(hits, [np.bincount(r, minlength=n) for r in literal])
        ids = np.array([1, 3, 7])
        timeline = np.arange(n)
        vals = np.array([[4., 5.], [2., -3.], [9., 1.]])
        point, boot = s.draws_for(ids, timeline, hits, vals)
        np.testing.assert_allclose(point, vals.mean(axis=0))
        all_values = np.full((n, 2), np.nan)
        all_values[ids] = vals
        expected = np.array([np.nanmean(all_values[idx], axis=0) for idx in literal if np.isin(idx, ids).any()])
        np.testing.assert_allclose(boot, expected)
        self.assertLess(len(boot), reps)

    def test_full_cues_and_separate_phases(self):
        trial = np.array([5, 3, 4, 1, 2, 6])
        data = dict(trial=trial, phase=np.array([0, 1, 0, 0, 0, 0]), direction=np.zeros(6),
                    offset=np.zeros(6), cues=np.zeros((6, 5, 7)))
        data['cues'][2, 0, 1] = 1
        np.testing.assert_array_equal(s.expected_donors(data), [4, -1, -1, -1, 3, 0])

    def test_windows_equal_within_original(self):
        ids, n, means = s.original_means(np.array([2, 3, 8]), np.array([5, 1, 5]))
        np.testing.assert_array_equal(ids, [1, 5])
        np.testing.assert_array_equal(n, [1, 2])
        np.testing.assert_allclose(means, [3, 5])
        self.assertEqual(means.mean(), 4)

    def test_held_release_precedes_all_input_reads(self):
        with self.assertRaisesRegex(ValueError, 'explicit held-day'):
            s.check_and_open('test', Path('absent'), Path('absent'), Path('absent'), None)

    def test_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            contacts = np.arange(1, 27)
            fit = np.array([1, 2])
            np.savez(base/'train.npz', trial=[1, 1, 2], contact_id=contacts, original_ids=fit,
                     target_count_100ms=np.tile(np.array([0, 2, 5])[:, None], (1, 26)))
            def save(name, data):
                (base/name).write_text(json.dumps(data))
            save('identities.json', dict(contacts=contacts.tolist(), sources={'2017-09-12': {'sha256': 'synthetic'}},
                                        accepted_training_archive_sha256=s.sha(base/'train.npz')))
            assigned = list(range(200, 308))
            save('first-day-split.json', dict(fit=[{'trial': int(i)} for i in fit],
                                              validation=[{'trial': i} for i in assigned]))
            eligible = assigned[:31:2]
            pre = [[i, 0, i*100 + off, off, 90] for i in eligible for off in (0, 5)]
            post = [r for r in pre if r[0] != eligible[2] and (r[0],r[3]) != (eligible[-1],5)]
            save('validation-qc.json', dict(stage='validation', source_mat_sha256='synthetic',
                                            pre_qc_rows=pre, phase_eligible_original_ids={s.REGIMES[0]: eligible}))
            data = dict(zip(s.KEYS, np.array(post).T, strict=True))
            n = len(post)
            data['cues'] = np.zeros((n, 5, 7))
            data['donor'] = s.expected_donors(data)
            data['contact_id'] = contacts
            y = np.full((n, 26), 2)
            data.update(prior_count_100ms=np.zeros_like(y), target_count_100ms=y)
            np.savez(base/'validation.npz', **data)
            meta = {k: data[k] for k in (*s.KEYS, 'donor')}
            for family in ('poisson','transformer'):
                arms = {}
                for name in s.ARMS:
                    p = np.tile(np.array([1., 3., 2.])[:, None, None], (1,n,26))
                    if name != 'all':
                        p *= .75
                    if name == 'wrong_movement':
                        p[:,data['donor'] < 0] = np.nan
                    arms[name] = p[0] if family == 'poisson' else p
                np.savez(base/f'validation-{family}.npz', **meta, **arms, seeds=[] if family == 'poisson' else s.SEEDS)
            out = base/'out'
            s.run('validation', base/'train.npz', base, base, out)
            result = s.load_json(out/'summary.json')
            phase = result['phases']['pre_target_bump']
            self.assertEqual(result['primary']['passed'], None)
            self.assertEqual(phase['support']['pre_qc_originals'], 16)
            self.assertEqual(phase['support']['qc_excluded_windows'], 3)
            self.assertEqual(phase['matched']['originals'], 14)
            self.assertEqual(phase['matched']['windows'], len(post)-2)
            self.assertEqual(result['training_mean_count_per_contact_100ms'], [3] * 26)
            self.assertNotIn('transformer_wrong_movement', phase['all_eligible']['scores'])
            self.assertEqual(phase['matched']['scores']['training_mean']['deviance']['draws'], 5000)
            self.assertAlmostEqual(phase['matched']['scores']['transformer_all']['mae']['estimate'], 2/3)
            for filename in ('original-scores.csv.gz', 'strata.csv.gz', 'donors.csv.gz'):
                with gzip.open(out/filename, 'rt') as stream:
                    self.assertGreater(len(stream.readlines()), len(eligible))


if __name__ == '__main__':
    unittest.main(verbosity=2)
