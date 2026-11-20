"""Synthetic tests. No recorded person's data is accessed."""
import itertools
import unittest
from pathlib import Path
import tempfile

import numpy as np

from retrieval import Clip, check_rows, cyclic_derangement, multi_scores, TextMap, tied_scores
from study import load


class Validation(unittest.TestCase):
    def test_fractional_tie_metrics(self):
        for size in range(1, 7):
            scores = np.array([[1,1,1,0,0,0][:size]],dtype=float)
            for mask in range(1, 2**size):
                good = np.array([[(mask >> i) & 1 for i in range(size)]],dtype=bool)
                first,low = [],[]
                for perm in itertools.permutations(range(size)):
                    if any(scores[0,a] < scores[0,b] for a,b in zip(perm,perm[1:])):
                        continue
                    first.append(next(i for i,j in enumerate(perm,1) if good[0,j]))
                r = np.array(first)
                expected = [np.mean(r<=1),np.mean(r<=5),np.mean(1/r)]
                np.testing.assert_allclose(multi_scores(scores,good)[0],expected)
                if good.sum() == 1:
                    target = np.flatnonzero(good)
                    np.testing.assert_allclose(tied_scores(scores,target)[0],expected)

    def test_split_does_not_leak_keys(self):
        def row(k):
            return {"part":k,"key":k,"performers":[k],"families":[k],"recording":k,"group":k}
        clean = [row(k) for k in ("train","assessment","reserve")]
        check_rows(clean)
        for field in ("key","group","performers","families","recording"):
            candidate = [dict(r) for r in clean]
            candidate[1][field] = candidate[0][field]
            with self.assertRaises(ValueError):
                check_rows(candidate)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"accessible"):
                load(clean,"reserve",Path(directory),{"motion_steps":24})

    def test_unknown_word_has_no_ridge_coordinate(self):
        c = Clip("t","g",None,["word word"],np.zeros((24,2)))
        fitted = TextMap.fit([c],{"vocabulary_cap":32,"text_tokens":6})
        ids,bow = fitted.encode(["unseen"])
        self.assertEqual(ids.tolist(),[[1,0,0,0,0,0]])
        self.assertEqual(float(bow.abs().sum()),0.0)

    def test_wrong_pair_preserves_clips(self):
        for n in range(2,9):
            ix = cyclic_derangement(n,455)
            self.assertEqual(sorted(ix.tolist()),list(range(n)))
            self.assertFalse(np.any(ix==np.arange(n)))


if __name__=="__main__":
    unittest.main()
