# SPDX-License-Identifier: CC0-1.0
"""Reproduce the frozen analysis from a separately prepared, verified prefix."""
import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np
from analysis_core import SAMPLE_SHA256, run


@dataclass
class Prefix:
    ecog: np.ndarray
    flex: np.ndarray
    cue: np.ndarray

    def complete_trials(self):
        changes=np.r_[0,1+np.flatnonzero(np.diff(self.cue) != 0)]
        for i in range(1,len(changes)-2):
            a,b,c=map(int,changes[i:i+3])
            d=int(self.cue[a])
            if 1<=d<=5 and self.cue[b]==0:
                yield d,a,b,c


def load(path):
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest() != SAMPLE_SHA256:
            raise ValueError('This file does not match the frozen development prefix')
        f.seek(0)
        with np.load(f,allow_pickle=False) as z:
            return Prefix(z['ecog'],z['flex'],z['cue'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prefix',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--mode',default='all',choices=['ridge','all'])
    args=ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        ap.error('Choose an empty output directory to preserve the existing fit')
    run(args.output, args.mode, False, 2, lambda:load(args.prefix))
