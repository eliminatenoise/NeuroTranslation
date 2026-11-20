# SPDX-License-Identifier: CC0-1.0
"""Optional offline preparation from the original, separately supplied Stanford MAT member."""
import argparse
import hashlib
import io
from pathlib import Path

import numpy as np
from analysis_core import SAMPLE_SHA256

MEMBER_SHA256 = 'b8222d13c15c97ec8590ed4b9ea180c639cac0b7c3e04bce178bb349f92be03a'


def pack(arrays, destination):
    payload=io.BytesIO()
    np.savez_compressed(payload, **arrays)
    if hashlib.sha256(payload.getbuffer()).hexdigest()!=SAMPLE_SHA256:
        raise ValueError('Prepared archive bytes differ from the fixed study input; no file written')
    with destination.open('xb') as out:
        out.write(payload.getbuffer())


def prepare(member,destination):
    from scipy.io import loadmat
    with member.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=MEMBER_SHA256:
            raise ValueError('Expected the verified original FingerFlex MAT member')
        f.seek(0)
        # The source stores complete variables in the MAT file. Decoding such a
        # variable transiently includes its later rows; only the prefix is retained.
        m=loadmat(f,variable_names=['data','flex','elec_regions','cue'])
    end=362000
    pack({'ecog':m['data'][:end], 'flex':m['flex'][:end],
          'region_code':m['elec_regions'].ravel(), 'cue':m['cue'][:end,0]},destination)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('member',type=Path,help='Verified original MAT member')
    ap.add_argument('destination',type=Path,help='New output file; never overwrites an existing file')
    args=ap.parse_args()
    prepare(args.member,args.destination)
