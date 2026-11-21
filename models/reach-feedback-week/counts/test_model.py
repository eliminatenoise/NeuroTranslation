"""Exercise the scoring contract using public metadata and fabricated signals."""
import unittest

import numpy as np

from forecast import build_design, group_columns, totals
from roster import KEY, deviance, draws, resample_weights, summarize
from score import evaluate


def fixture():
    rng = np.random.default_rng(105)
    contacts = {"zero":[1,2], "positive":[1,3]}
    mapping = {"shared_contacts_by_presence":contacts}
    fits = {"populations":{}}
    for pop in ("primary","zero","positive"):
        ids = contacts["positive" if pop=="positive" else "zero"]
        m = {"contacts":ids, "train_mean":[1.,2.]}
        for arm,len_x in (("base",20),("update",28)):
            weights = rng.normal(0,.02,size=(len(ids),len_x+1))
            m[arm]={"coefficients":weights.tolist(),"mean":np.zeros(len_x).tolist(),"scale":np.ones(len_x).tolist()}
        fits["populations"][pop]=m
    packs, roster = [], []
    for b in (1,2):
        guide = np.array([[1,0],[1,1],[1,2],[2,0],[3,1 + b]])
        keys = []
        for i in range(27):
            start = 100+i*200
            r = dict(block=b,workspace=1+i%2,original=88-i,result="A" if i in (4,7,12) else "R",
                     start=start,end=start+160)
            roster.append(r)
            if r["result"]=="R":
                for ordinal, offset in ((2,45),(3,100)):
                    keys.append((b,r["workspace"],r["original"],ordinal,start+offset))
        n = len(keys)
        p = {k:np.array([r[j] for r in keys]) for j,k in enumerate(KEY)}
        p.update(all_guide=guide, pose=rng.normal(size=(n,20,8)),cue_at_k=np.array([[o,.05] for _,_,_,o,_ in keys]),
                 movement=rng.normal(size=(n,10,8)))
        for field,length in (("all_history",20),("all_concurrent",10),("all_delayed",10)):
            p[field]=rng.poisson(.08,size=(n,length,len(guide))).astype(float)
            p[field][:,:,3]=0
        packs.append(p)
    return packs,roster,fits,mapping


class TestModel(unittest.TestCase):
    def test_features_and_column_sums(self):
        packs,_,_,_ = fixture()
        p = packs[0]
        primary = group_columns(p["all_guide"],[1,2],"primary")
        h,ok = totals(p["all_history"],primary)
        np.testing.assert_array_equal(h[:,0],p["all_history"][:,:,:3].sum(axis=(1,2)))
        np.testing.assert_array_equal(h[:,1],0.)
        self.assertTrue(ok.all())
        x,r = build_design(p["pose"],p["cue_at_k"],h,p["movement"][:,-1])
        expected_slope=(p["pose"][:,19]-p["pose"][:,15])/4
        np.testing.assert_array_equal(x[:,8:16],expected_slope)
        np.testing.assert_array_equal(r,p["movement"][:,9]-10*expected_slope)
        with self.assertRaises(ValueError):
            group_columns(p["all_guide"],[2],"positive")

    def test_missing_stays_missing_and_donor_uses_same_original_history(self):
        p,roster,fit,mapping=fixture()
        # This row has invalid late counts only. It remains an eligible primary donor.
        p[0]["all_concurrent"][6,0,0]=np.nan
        # Missing response only for a positive-only contact absent from the primary endpoint.
        p[0]["all_delayed"][8,5,4]=.5
        # Missing primary predictor drops the recipient for every endpoint.
        p[1]["all_history"][8,0,1]=-1
        # A failure on an unconsumed camera row cannot enter these forecasts.
        p[1]["pose"][3,7,2]=np.nan
        report,z=evaluate(p,roster,fit,mapping)
        self.assertTrue(z["primary_matched"][6])
        self.assertFalse(z["primary_all_matched"][6])
        self.assertTrue(z["primary_observable"][8])
        self.assertFalse(z["positive_observable"][8])
        n=len(p[0]["k"])
        self.assertTrue(z["positive_observable"][n+3])
        self.assertFalse(z["positive_observable"][n+8])
        self.assertFalse(z["zero_observable"][n+8])
        main=fit["populations"]["primary"]
        E=z["primary_expected"]
        for i in np.flatnonzero(z["primary_matched"]):
            prior=[j for j in range(i) if z["primary_observable"][j] and
                   all(z[key][j]==z[key][i] for key in ("block","workspace","ordinal")) and
                   z["original"][j]!=z["original"][i]]
            donor=prior[-1]
            self.assertEqual(donor,z["primary_donor"][i])
            b=int(z["block"][i]-1)
            w=p[b]
            local=i-b*n
            g=w["all_guide"]
            H=np.array([w["all_history"][local,:,g[:,0]==c].sum() for c in (1,2)])
            slope=(w["pose"][local,19]-w["pose"][local,15])/4
            base=np.r_[w["pose"][local,19],slope,H,w["cue_at_k"][local]]
            m=donor-b*n
            shift=w["movement"][m,9]-2.5*(w["pose"][m,19]-w["pose"][m,15])
            B=np.array(main["update"]["coefficients"])
            expect=np.exp(B[:,0]+B[:,1:]@np.r_[base,shift])
            np.testing.assert_allclose(E[i,:,2],expect,atol=1e-12)
        # Independent scalar construction verifies averaging within original and across contacts.
        for ws in (1,2):
            ix=np.flatnonzero(z["primary_matched"] & (z["workspace"]==ws))
            table={}
            for i in ix:
                key=(z["block"][i],z["original"][i])
                table.setdefault(key,[]).append(deviance(z["primary_observed"][i],E[i,:,0]).mean())
            expected=np.mean([np.mean(v) for v in table.values()])
            rr=report["workspaces"][ws]["populations"]["primary"]["prespecified"]["matched"]
            self.assertAlmostEqual(expected,rr["mean"][0],places=12)
        # Unsupported slots are still available to resampling.
        self.assertEqual(len(report["roster"]),54)
        self.assertEqual(report["workspaces"][1]["assigned_originals"],28)

    def test_draws_and_undefined_intervals(self):
        d=draws([1]*10+[2]*16,True,repetitions=150)
        self.assertTrue((d[:,:10]<10).all() and (d[:,10:]>=10).all())
        for s,t in [(0,8),(8,10),(10,18),(18,26)]:
            self.assertTrue((np.diff(d[:,s:t],axis=1)==1).all())
        weights=resample_weights([1]*10+[2]*16)
        x=summarize(np.array([[1.],[4.]]),np.array([0,25]),26,weights)
        self.assertIsNone(x["moving8"]["interval"])
        self.assertGreater(x["moving8"]["empty_draws"],0)
        self.assertIsNone(draws([1]*7+[2]*16,True))
        np.testing.assert_allclose(deviance(np.array([0.,1.]),np.zeros(2)),[2e-6,2*(1e-6-1-np.log(1e-6))])


if __name__=="__main__":
    unittest.main()
