"""Portable NumPy inference for the 100-ms stored-frame force forecast."""
import argparse
import json
from pathlib import Path
import numpy as np

MODES={"markers":slice(0,24),"emg":slice(24,40),"combined":slice(0,40)}
def fields(x):
    x=np.asarray(x,dtype=np.float32)
    if x.ndim!=3 or x.shape[1:]!=(8,40):
        raise ValueError("expected [windows,8,40], oldest token first")
    x=x.copy()
    valid=np.ones(x.shape,dtype=bool)
    for j in range(6):
        valid[:,:,3*j:3*j+3]=(x[:,:,18+j:19+j]==1)
    valid[:,:,24:32]=x[:,:,32:40]==1
    return x,valid & np.isfinite(x)

def normalize(x,params):
    x,ok=fields(x)
    return np.clip(np.where(ok,(x-params["center"])/params["scale"],0),-8,8).astype("f4")

def norm(x,weights,prefix):
    d=x-x.mean(axis=-1,keepdims=True)
    return (d/np.sqrt((d*d).mean(axis=-1,keepdims=True)+1e-5))*weights[prefix+".weight"]+weights[prefix+".bias"]

def affine(x,w,prefix):
    return x@w[prefix+".weight"].T+w[prefix+".bias"]

def transformer(x,weights,mode="combined"):
    z=normalize(x,weights)[:,:,MODES[mode]]
    h=affine(z,weights,"embed")+weights["pos"]
    q,k,v=np.split(affine(norm(h,weights,"n1"),weights,"qkv"),3,axis=-1)
    heads=lambda t:t.reshape(len(h),8,3,8).transpose(0,2,1,3)
    q,k,v=map(heads,(q,k,v))
    scores=(q@k.swapaxes(-1,-2))/np.float32(np.sqrt(8))
    exp=np.exp(scores-scores.max(axis=-1,keepdims=True))
    mix=(exp/exp.sum(axis=-1,keepdims=True))@v
    h=h+affine(mix.transpose(0,2,1,3).reshape(len(h),8,24),weights,"out")
    h=h+affine(np.maximum(affine(norm(h,weights,"n2"),weights,"ff1"),0),weights,"ff2")
    return np.maximum(0,500*affine(norm(h[:,-1],weights,"n3"),weights,"head")[:,0])

def squared(x,y):
    return np.maximum((x*x).sum(axis=1)[:,None]+(y*y).sum(axis=1)[None,:]-2*x@y.T,0)

def ridge(x,weights,mode,nonlinear=False):
    x=normalize(x,weights)[:,:,MODES[mode]].reshape(len(x),-1).astype("f8")
    if nonlinear:
        x=np.exp(-squared(x,weights["centres"])/weights["bandwidth"])
    return np.maximum(0,500*(x@weights["coef"]+weights["bias"]))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights",type=Path,default=Path(__file__).with_name("weights")/"transformer-combined.npz")
    p.add_argument("--input",type=Path,default=Path(__file__).with_name("invented-example.json"))
    p.add_argument("--mode",choices=list(MODES),default="combined")
    a=p.parse_args()
    xs=np.asarray(json.loads(a.input.read_text())["rows"],dtype="f4").reshape(-1,8,40)
    with np.load(a.weights,allow_pickle=False) as w:
        print(json.dumps({"forecast_N":transformer(xs,w,a.mode).tolist()}))

if __name__=="__main__":
    main()
