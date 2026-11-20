"""Export fixed candidate vectors for the included five-interval training gallery."""
import argparse
from pathlib import Path

import numpy as np
import torch

from fit import normalized
from kit_components import descriptors, digest, dump
from rank import Scorer, unit


@torch.no_grad()
def export(bundle, dest):
    scorer=Scorer(bundle/'fit')
    clips=scorer.gallery(bundle)
    z=scorer.z
    x=torch.from_numpy(normalized(np.stack([c.sequence for c in clips]),z['center'],z['scale']))
    ridge=unit(normalized(descriptors(x).numpy(),z['desc_center'],z['desc_scale']))
    attention=scorer.networks['attention'].from_motion(x).numpy()
    dest.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(dest/'candidates.npz',ridge=ridge,attention=attention)
    dump({'keys':[c.key for c in clips],'recording':clips[0].recording,'partition':'train',
          'fit_seal_sha256':digest(bundle/'fit/seal.json'),'input_gallery_sha256':digest(bundle/'gallery.npz'),
          'arrays_sha256':digest(dest/'candidates.npz'),'units':'unit-normalized candidate representations',
          'shapes':{'ridge':list(ridge.shape),'attention':list(attention.shape)}},dest/'candidates.json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent/'bundle')
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    export(args.bundle,args.output)
