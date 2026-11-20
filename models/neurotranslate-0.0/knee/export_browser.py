"""Export only the knee coefficients and shared encoder consumed by the browser."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from predict import read_checkpoint
from knee.adapter import scramble

RESULT_CHECKPOINT = '4541317c4e5d7f08f24d221278a0f3fec6f9f9acb9c7ea17669ef28511c187fe'
RESULT_TENSORS = '257824975fa97130068ca185e30be7832b88e1b5af95933eebd0232d0f07b207'


def tensor_digest(weights, names):
    """Fingerprint the exact knee readouts and shared encoder used for this published study."""
    digest = hashlib.sha256()
    for name in sorted(names):
        a = np.ascontiguousarray(weights[name], dtype='<f8')
        header = json.dumps([name, list(a.shape)], separators=(',', ':')).encode()
        digest.update(len(header).to_bytes(8, 'little'))
        digest.update(header)
        digest.update(a.tobytes())
    return digest.hexdigest()


def export(checkpoint, output):
    cfg,w = read_checkpoint(checkpoint)
    if (cfg['width'],cfg['heads'],cfg['layers'],cfg['knee_angle']['format']) != (24,4,1,1):
        raise ValueError('This browser implementation requires a 24-wide, one-block, four-head knee checkpoint')
    shuffled = scramble(w)
    def flat(values):
        return {name:v.ravel().tolist() for name,v in values.items()}
    scores=json.loads((HERE/'results.json').read_bytes())
    checksum=scores['checkpoint_sha256']
    names=set(shuffled) | {k for k in w if k.startswith('knee.')}
    if checksum!=RESULT_CHECKPOINT or tensor_digest(w,names)!=RESULT_TENSORS:
        raise ValueError('The knee parameters or score provenance differ from the published fit')
    payload={'format':1,'checkpoint_sha256':checksum,'scores':scores,
             'encoder':flat({k:w[k] for k in shuffled}), 'scrambled_encoder':flat(shuffled),
             'readouts':flat({k.removeprefix('knee.'):v for k,v in w.items() if k.startswith('knee.')})}
    output.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('checkpoint',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();export(args.checkpoint,args.output)
