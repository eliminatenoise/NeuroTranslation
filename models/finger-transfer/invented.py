# SPDX-License-Identifier: CC0-1.0
"""An invented bedside packet with an index-finger display. It contains no clinical trace."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from decode import decode

HERE = Path(__file__).resolve().parent


def example():
    codes = np.array([1, 2, 3, 4, 6, 7, 0])
    t = np.arange(280)[:, None] / 1000
    contact = np.arange(len(codes))[None]
    voltage = np.rint(65*np.sin(2*np.pi*(17+contact)*t + .25*contact) +
                      26*np.cos(2*np.pi*(76+2*contact)*t + .33*contact)).astype(np.int32)
    cal = dict(mean=np.full((2,len(codes)), .18), sd=np.full((2,len(codes)), .35),
               gain=np.array([12., 20., 15., 16., 10.]), region=codes.copy())
    result = {'origin':'invented voltages, region assignments and calibration, no measured outcome',
              'finger_cue':'index', 'phase':'display', 'elapsed_ms':800, 'predictions': {}}
    for family in ['ridge','transformer']:
        for mode in ['cue','cortex','aligned']:
            result['predictions'][family+'_'+mode] = decode(voltage, codes, cal, 2, 0, 800, family, mode)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    torch.set_num_threads(2)
    out = example()
    if args.check:
        expected = json.loads((HERE/'invented-result.json').read_text())
        for key, pred in out['predictions'].items():
            for field in ['personal_calibration_units','sensor_counts_per_40ms_step']:
                np.testing.assert_allclose(pred[field], expected['predictions'][key][field], rtol=1e-5, atol=1e-5)
        print('Six trained readouts reproduce their invented example.')
    else:
        print(json.dumps(out, indent=2))
