import unittest
import numpy as np
from portable import histories, projected_change
from study import windows, donor_ranks, summarize
from portable import METHODS


class StudyChecks(unittest.TestCase):
    def setUp(self):
        self.rows = np.arange(1, 102)
        self.time = self.rows.astype(float)
        self.seg = np.zeros_like(self.rows)
        self.length = self.rows.astype(float) ** 2
        self.angle = self.rows.astype(float)*.1

    def test_source_cutoffs(self):
        t = windows(self.rows,self.time,self.seg,self.length,self.angle)
        np.testing.assert_array_equal(t.cutoff_row, np.arange(21,92,10))
        np.testing.assert_array_equal(t.target, (t.cutoff_row+10)**2 - t.cutoff_row**2)
        self.assertEqual(t.angle[0,-1], 2.)
        self.assertEqual(t.length[0,-1], 441.)

    def test_gap_and_invalid(self):
        self.seg[40:] = 1
        self.angle[98] = np.nan
        t = windows(self.rows,self.time,self.seg,self.length,self.angle)
        np.testing.assert_array_equal(t.cutoff_row,[21,61,71,81])
        keep = self.rows != 39
        t = windows(self.rows[keep],self.time[keep],self.seg[keep],self.length[keep],self.angle[keep])
        np.testing.assert_array_equal(t.cutoff_row,[21,61,71,81])

    def test_person_vote_and_aggregation(self):
        # Three narrow individual improvements do not offset a much larger loss.
        people = {}
        for i in range(4):
            errors = dict.fromkeys(METHODS, 2.)
            errors['full'] = 1.9 if i < 3 else 2.9
            t = {'eligible': 10, 'candidates': 11, 'score_counts': {'projection': 9}}
            people[i] = {'mae_mm': errors, 'trials': [t, t]}
        s = summarize(people)
        row = s['comparisons']['full_vs_length']
        self.assertEqual(row['people_improved'], 3)
        self.assertAlmostEqual(row['two_sided_exact_sign_p'], .625)
        self.assertAlmostEqual(row['mean_gain_mm'], -.15)
        self.assertFalse(row['passes'])
        self.assertEqual(s['eligible_windows'], 80)
        self.assertEqual(s['projection_windows'], 72)

    def test_features(self):
        x = histories(np.arange(21.), np.arange(20.))
        np.testing.assert_array_equal(x[-1], [20,4,17.5,3])
        np.testing.assert_array_equal(x[0], [4,4,1.5,3])
        self.assertEqual(projected_change(np.arange(21.), np.zeros(20)), 10.)
        self.assertTrue(np.isnan(projected_change(np.arange(21.), np.full(20, 90.))))
        np.testing.assert_array_equal(donor_ranks(5,3), [0,1,1,2,2])
        np.testing.assert_array_equal(donor_ranks(1,3), [0])


if __name__ == '__main__':
    unittest.main()
