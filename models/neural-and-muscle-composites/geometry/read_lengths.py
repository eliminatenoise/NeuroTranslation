"""Retrieve labelled OpenSim path-length changes on the recording grid at existing k keys."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import loadmat

MEMBERS={"train":"6062b7e8dacdf46f7eee465bd844ffe1fb3b7ce0793c34d3e4d106be357f4746",
         "held":"4456c7bf8cda177f31c849e3fe794100269ca951c741c1718dd5c750d5432a76"}
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args):
    if digest(args.mat)!=MEMBERS[args.stage]:raise ValueError("Unexpected acquisition file")
    with np.load(args.source,allow_pickle=False) as source:
        ids={k:source[k] for k in ("block","original","workspace","ordinal","k")}
    if args.stage=="train" and digest(args.source)!="edf4a94b3cb9a60a7706324b4f3a85c959df2dfdae475948706853f528136f6e":
        raise ValueError("Training rows differ from admitted TRAIN")
    blocks=np.atleast_1d(loadmat(args.mat,squeeze_me=True,struct_as_record=False,variable_names=['trial_data'])['trial_data'])
    native_order=np.asarray(blocks[0].muscle_names).astype(str)
    names=np.asarray(json.loads(args.labels.read_text())) if args.labels else native_order
    if len(names)!=39 or len(set(names))!=39:raise ValueError("Unexpected muscle path roster")
    length=np.empty((len(ids['k']),10,len(names)))
    anchor=np.empty((len(length),len(names)))
    for b in np.unique(ids['block']):
        block=blocks[int(b)-1]
        day_names=list(np.asarray(block.muscle_names).astype(str))
        if len(day_names)!=39 or set(day_names)!=set(names) or block.muscle_len.shape!=(block.S1_spikes.shape[0],39):
            raise ValueError("Muscle labels or source clock differs")
        cols=[day_names.index(label) for label in names]
        pick=np.flatnonzero(ids["block"]==b)
        k=ids["k"][pick]
        if k.min()<2 or max(k)+9>len(block.muscle_len): raise ValueError("Original time bounds")
        anchor[pick]=block.muscle_len[k-2][:,cols]
        values=block.muscle_len[(k[:,None]-1)+np.arange(10)]
        length[pick]=values[:,:,cols]-anchor[pick,None,:]
    with args.output.open("xb") as stream:
        np.savez_compressed(stream,**ids,names=names,delta_m=length,anchor_m=anchor)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("train","held"));p.add_argument("mat",type=Path)
    p.add_argument("source",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--labels",type=Path)
    run(p.parse_args())
