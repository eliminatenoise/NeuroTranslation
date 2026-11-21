"""Fit two pretrained-movement readouts using recorded-day source windows only."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from model import design_displacement,direct_x,infer_path,infer_direct

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def original_weights(block,original):
    _,index,count=np.unique(np.column_stack((block,original)),axis=0,return_counts=True,return_inverse=True)
    return 1/(len(count)*count[index])
def rescale(sd):
    return np.where(sd>1e-9,sd,1.)
def ridge(x,y,w):
    return np.linalg.solve((x.T*w)@x+.01*np.eye(x.shape[1]),(x.T*w)@y)
def fit(pose,motion,cue,y,w):
    mean=w@pose[:,-1];sd=rescale(np.sqrt(w@((pose[:,-1]-mean)**2)))
    motion_rms=rescale(np.sqrt(w@(motion**2).mean(1)))
    dst={"anchor_mean":mean,"anchor_sd":sd,"motion_rms":motion_rms}
    x=design_displacement(pose[:,-1],motion,dst).reshape(-1,72)
    dst["geometry"]=ridge(x,y.reshape(-1,39),np.repeat(w/10,10))
    raw=direct_x(pose,cue);center=w@raw;scale=rescale(np.sqrt(w@(raw-center)**2))
    target=y.reshape(len(y),-1);bias=w@target
    dst.update(direct_mean=center,direct_sd=scale,direct_bias=bias,direct_coef=ridge((raw-center)/scale,target-bias,w))
    dst["rms_endpoint_m"]=np.sqrt(w@y[:,-1]**2)
    dst["moving_subset"]=dst["rms_endpoint_m"]>=.0001
    return dst
def run(args):
    if sha(args.source)!="edf4a94b3cb9a60a7706324b4f3a85c959df2dfdae475948706853f528136f6e":
        raise ValueError("Expected fixed day-one training inputs")
    with np.load(args.source) as d,np.load(args.lengths) as z:
        for key in ('block','original','workspace','ordinal','k'):np.testing.assert_array_equal(d[key],z[key])
        y=z["delta_m"];pose=d['pose'];motion=d['movement'];cue=d['cue'];names=z['names']
        valid=np.isfinite(y).all((1,2)) & np.isfinite(motion).all((1,2)) & np.isfinite(pose).all((1,2)) & np.isfinite(cue).all((1,2))
        block=d['block'][valid];original=d['original'][valid];fold=d['fold'][valid]
        y,pose,motion,cue=(v[valid] for v in (y,pose,motion,cue))
    w=original_weights(block,original);dst=fit(pose,motion,cue,y,w);dst["names"]=names
    val=[]
    for target in range(1,5):
        earlier=fold<target;later=fold==target
        f=fit(pose[earlier],motion[earlier],cue[earlier],y[earlier],original_weights(block[earlier],original[earlier]))
        g=infer_path(pose[later],motion[later],f);p=infer_direct(pose[later],cue[later],f)
        val.append({"fold":target,"originals":len(set(original[later].tolist())),"n":int(later.sum()),"oracle_mm":float(original_weights(block[later],original[later])@np.abs(1000*(g-y[later]))[:,-1].mean(1)),"direct_mm":float(original_weights(block[later],original[later])@np.abs(1000*(p-y[later]))[:,-1].mean(1))})
    with args.output.open("xb") as target:np.savez_compressed(target,**dst)
    report={"training":sha(args.source),"lengths":sha(args.lengths),"weights":sha(args.output),"total_rows":len(valid),"retained":int(valid.sum()),"originals":len(np.unique(np.c_[block,original],axis=0)),
            "names":names.tolist(),"moving_subset":names[dst["moving_subset"]].tolist(),"finite_failures":np.flatnonzero(~valid).tolist(),"forward_train_checks":val}
    args.output.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","lengths","output"):p.add_argument(name,type=Path)
    run(p.parse_args())
