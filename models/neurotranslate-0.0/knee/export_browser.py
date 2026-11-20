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

def export(checkpoint, output):
    cfg,w = read_checkpoint(checkpoint)
    if (cfg['width'],cfg['heads'],cfg['layers'],cfg['knee_angle']['format']) != (24,4,1,1):
        raise ValueError('This browser implementation requires a 24-wide, one-block, four-head knee checkpoint')
    shuffled = scramble(w)
    def flat(values):
        return {name:v.ravel().tolist() for name,v in values.items()}
    scores=json.loads((HERE/'results.json').read_bytes())
    checksum=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if scores['checkpoint_sha256']!=checksum:
        raise ValueError('Scores and checkpoint differ')
    payload={'format':1,'checkpoint_sha256':checksum,'scores':scores,
             'encoder':flat({k:w[k] for k in shuffled}), 'scrambled_encoder':flat(shuffled),
             'readouts':flat({k.removeprefix('knee.'):v for k,v in w.items() if k.startswith('knee.')})}
    output.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('checkpoint',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();export(args.checkpoint,args.output)
