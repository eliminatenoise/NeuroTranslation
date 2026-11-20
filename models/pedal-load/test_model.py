"""Causality, support, mixed donor features, scalar meaning, and portable parity tests."""
import json
from pathlib import Path
import unittest
import numpy as np
from data import windows
from portable import features, mask, predict

HERE = Path(__file__).resolve().parent


def record(n=601):
    j = np.arange(n)
    return dict(time_s=j/1000, load=.07*j + .15*np.sin(j/15), emg=.16*np.sin(j/4))


class Checks(unittest.TestCase):
    def test_support_donor_and_dimensions(self):
        r, d = record(),record(350)
        x,c=windows(r,d,0)
        self.assertEqual(x['i'].tolist(),[200,300])
        self.assertEqual(c,dict(candidates=4,clock=0,signal_or_target=0,donor=2,admitted=2))
        self.assertEqual(x['x'].shape,(2,10,8))
        self.assertEqual(x['recent'][0],r['load'][200]-r['load'][100])
        self.assertEqual(x['y'][0],r['load'][300]-r['load'][200])

    def test_target_and_future_cannot_change_predictors(self):
        r,d=record(),record()
        base,_=windows(r,d,5)
        r['emg'][201:]=83
        r['load'][201:]+=123
        d['emg'][201:]=-12
        changed,_=windows(r,d,5)
        for k in ('x','wrong','recent'):
            np.testing.assert_array_equal(base[k][0],changed[k][0])
        self.assertAlmostEqual(changed['y'][0]-base['y'][0],123)

    def test_clock_gaps_nonfinite_control_and_boundaries(self):
        r,d=record(),record()
        r['time_s'][0]=-.001
        x,c=windows(r,d,0)
        self.assertEqual(c['clock'],1)
        self.assertEqual(x['i'][0],300)
        r,d=record(),record()
        d['emg'][0]=np.nan
        self.assertEqual(windows(r,d,0)[1]['donor'],1)
        r['emg'][0]=np.nan
        self.assertEqual(windows(r,d,0)[1]['signal_or_target'],1)
        r,d=record(300),record()
        with self.assertRaises(ValueError):
            windows(r,d,0)

    def test_features_and_mixed_donor(self):
        r,d=record(),record()
        d['emg']*=3
        x,_=windows(r,d,5)
        history = r['emg'][:21]
        step = r['load'][20]-r['load'][0]
        expected=[r['load'][20],step,step,1,np.mean(history),np.std(history),
                  np.sqrt(np.mean(np.diff(history)**2)),np.std(history)*step]
        np.testing.assert_allclose(expected,x['x'][0,0])
        np.testing.assert_allclose(x['wrong'][:,:,:4],x['x'][:,:,:4])
        np.testing.assert_allclose(x['wrong'][:,:,4:],3*x['x'][:,:,4:])
        masked=mask(x['x'],'emg_condition'); np.testing.assert_equal(masked[:,:,[0,1,2,7]],0)
        with self.assertRaises(ValueError):
            features(r['load'][:200],r['emg'][:200],0)

    def test_export_fixture(self):
        if not (HERE/'model.json').exists():
            self.skipTest('Model not yet trained')
        model=json.loads((HERE/'model.json').read_text()); f=json.loads((HERE/'fixture.json').read_text())
        for c in (0,1):
            real=predict(model,f['load'],f['emg'],c,f['donor_emg'])
            for k,v in real.items():
                self.assertAlmostEqual(v,f['conditions'][str(c)][k],places=11)
            same=predict(model,f['load'],f['emg'],c,f['emg'])
            self.assertAlmostEqual(same['wrong'],same['full'],places=11)


if __name__ == '__main__':
    unittest.main()
