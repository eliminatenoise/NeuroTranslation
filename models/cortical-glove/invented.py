# SPDX-License-Identifier: CC0-1.0
"""Run fitted weights on a deliberately invented signal without a participant file."""
import argparse
import json
from pathlib import Path

import numpy as np
from model import (encoder_predict, load_checkpoint, ridge_predict, tokens_from_history)


def invented():
    rng = np.random.default_rng(142)
    t = np.arange(280)/1000
    counts = rng.normal(0, 10, (280,46))
    counts[:,0] += 80*np.sin(2*np.pi*25*t)
    counts[:,1] += 55*np.sin(2*np.pi*87.5*t)
    glove = np.array([100.,200.,300.,400.,500.]) + np.arange(4)[:,None]*np.array([2.,3.,-1.,0.,1.])
    return counts, glove, 2, 0, 920


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    default_weights = root/'weights' if (root/'weights').is_dir() else root/'outputs/weights'
    parser.add_argument('--weights', type=Path, default=default_weights)
    parser.add_argument('--model',choices=['motion_cue','aligned','encoder_motion_cue','encoder_aligned'],default='aligned')
    args = parser.parse_args()
    x = tokens_from_history(*invented())[None]
    w = load_checkpoint(args.weights/(args.model+'.npz'))
    if args.model.startswith('encoder'):
        import torch
        torch.set_num_threads(1)
        future = encoder_predict(x,args.model=='encoder_aligned',w)
    else:
        future = ridge_predict(x,args.model,w)
    print(json.dumps({'input':'invented waveforms and invented glove history', 'model':args.model,
        'forecast_horizon_on_nominal_grid_ms':120, 'units':'glove sensor counts',
        'digit_order':['thumb','index','middle','ring','little'],
        'predicted_sensor_counts_for_invented_example':future[0].tolist()}, indent=2))


if __name__ == '__main__':
    main()
