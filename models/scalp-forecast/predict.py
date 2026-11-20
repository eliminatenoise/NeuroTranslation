"""Portable single-trial and batched prediction. NumPy is the only dependency."""
import argparse
import json
from pathlib import Path
import numpy as np

CUES = ("elbow flexion","elbow extension","supination","pronation","hand close","hand open","rest")
CHANNELS = ("elbow","forearm_rotation","index_glove")
HORIZONS = (0.5,1.0,1.5)
NETWORKS = ("history","scalp","eye","scalp_eye","scalp_only","eye_only","bilateral","mispaired_fit")
RIDGES = ("ridge","history_ridge")
METHODS = NETWORKS + RIDGES + ("cue_median","cue_mean","still")
ONLY = ("scalp_only","eye_only")
SCALP = ("scalp","scalp_eye","scalp_only","mispaired_fit","ridge")
EYE = ("eye","eye_only","scalp_eye")


def transform(h,s,e):
    a = h[:,-1,:3].copy()
    z = h.copy()
    z[:,:,:3] -= a[:,None]
    s = s - s[:,0:1]
    e = e - e[:,0:1]
    b = s[:,:,::2] - s[:,:,1::2]
    return {"history":z, "anchor":a, "scalp":s, "eye":e, "bilateral":b}


def inputs(m, raw, cue, method):
    slots = np.zeros((len(cue),4,15))
    def scale(key):
        mean,sd = m["scales"][key]
        return np.clip((raw[key]-mean)/sd, -6, 6)
    a = np.zeros((len(cue),3)) if method in ONLY else scale("anchor")
    if method not in ONLY:
        slots[:,:,:6] = scale("history")
    if method in SCALP:
        slots[:,:,6:12] = scale("scalp")
    if method == "bilateral":
        slots[:,:,6:9] = scale("bilateral")
    if method in EYE:
        begin = 12 if method == "scalp_eye" else 6
        slots[:,:,begin:begin+3] = scale("eye")
    ids = np.full(len(cue),7,dtype=int) if method in ONLY else cue
    return slots,a,ids


def affine(x,w,key):
    return x @ np.asarray(w[key+".weight"]).T + w[key+".bias"]


def norm(x,w,key):
    c = x-x.mean(axis=-1,keepdims=True)
    return c/np.sqrt(np.mean(c*c,axis=-1,keepdims=True)+1e-5)*w[key+".weight"]+w[key+".bias"]


def attention(w,z,a,ids):
    first = np.asarray(w["cue.weight"])[ids]+affine(a,w,"anchor")
    h = np.concatenate((first[:,None],affine(z,w,"project")),axis=1)+w["position"]
    q,k,v = [affine(h,w,t).reshape(-1,5,2,4).transpose(0,2,1,3) for t in ("q","k","v")]
    logits = (q[:,:,:1] @ k.swapaxes(-2,-1))/2
    exp = np.exp(logits-logits.max(axis=-1,keepdims=True))
    context = ((exp/exp.sum(axis=-1,keepdims=True)) @ v).reshape(-1,8)
    h = norm(h[:,0]+affine(context,w,"attn_out"),w,"norm1")
    h = norm(h+affine(np.tanh(affine(h,w,"ff1")),w,"ff2"),w,"norm2")
    return affine(h,w,"head")


def design(z,a,ids):
    return np.column_stack((z.reshape(len(z),-1),a,np.eye(7)[ids]))


def batch(m,h,s,e,cue,method):
    if method not in METHODS:
        raise ValueError("Unknown prediction method")
    median = np.asarray(m["cue_median"])[cue]
    if method == "cue_median":
        return median
    if method == "cue_mean":
        return np.asarray(m["cue_mean"])[cue]
    if method == "still":
        return np.zeros_like(median)
    z,a,ids = inputs(m,transform(h,s,e),cue,method)
    w = m["fits"][method]
    if method in RIDGES:
        residual = design(z,a,ids) @ w["coef"] + w["bias"]
    else:
        residual = attention(w,z,a,ids)
    baseline = np.asarray(m["global_median"]) if method in ONLY else median
    return baseline + residual*m["target_sd"]


def validate_model(m):
    """Reject unsupported layouts, nonfinite coefficients, and incorrect scale shapes."""
    if not isinstance(m,dict) or m.get("format")!="early-scalp-arm-v1":
        raise ValueError("Unsupported coefficient file")
    def check(x,shape,positive=False):
        a = np.asarray(x)
        if a.shape!=shape or a.dtype.kind not in "fiu" or not np.isfinite(a).all() or (positive and (a<=0).any()):
            raise ValueError("Invalid coefficient shape, value or scale")
    check(m["target_sd"],(9,),True)
    check(m["cue_median"],(7,9)); check(m["cue_mean"],(7,9)); check(m["global_median"],(9,))
    for key,n in (("history",6),("anchor",3),("scalp",6),("eye",3),("bilateral",3)):
        mean,sd=m["scales"][key]
        check(mean,(n,)); check(sd,(n,),True)
    if set(m["fits"])!=set(NETWORKS+RIDGES):
        raise ValueError("Incomplete fitted model family")
    for name in NETWORKS:
        w=m["fits"][name]
        check(w["cue.weight"],(8,8)); check(w["position"],(5,8))
        for layer,i,o in (("project",15,8),("anchor",3,8),("q",8,8),("k",8,8),("v",8,8),
                          ("attn_out",8,8),("ff1",8,12),("ff2",12,8),("head",8,9)):
            check(w[layer+".weight"],(o,i)); check(w[layer+".bias"],(o,))
        for layer in ("norm1","norm2"):
            check(w[layer+".weight"],(8,)); check(w[layer+".bias"],(8,))
    for name in RIDGES:
        check(m["fits"][name]["coef"],(70,9)); check(m["fits"][name]["bias"],(9,))
    return m


def request(m,r):
    validate_model(m)
    fields = {"cue","method","history","scalp","eye"}
    if not isinstance(r,dict) or set(r) - fields:
        raise ValueError("Supply the cue and signals for the selected method")
    method = r.get("method","scalp")
    if method not in METHODS:
        raise ValueError("Unknown method")
    cue = r.get("cue")
    if (cue is not None or method not in ONLY+("still",)) and cue not in CUES:
        raise ValueError("Unknown or missing instruction")
    arrays = []
    for name,width,required in (("history",6,method in NETWORKS+RIDGES and method not in ONLY),
                                ("scalp",6,method in SCALP+("bilateral",)),("eye",3,method in EYE)):
        if not required and name not in r:
            arrays.append(np.zeros((1,4,width)))
            continue
        v = r.get(name)
        if (not isinstance(v,list) or len(v) != 4 or any(not isinstance(row,list) or
            len(row)!=width or any(type(x) not in (int,float) for x in row) for row in v)):
            raise ValueError(f"{name} needs four rows of {width} finite numbers")
        arr = np.asarray(v,dtype=np.float64)
        if not np.isfinite(arr).all():
            raise ValueError("Every input must be finite")
        arrays.append(arr[None])
    with np.errstate(over="raise",invalid="raise"):
        y = batch(m,*arrays,np.array([CUES.index(cue) if cue is not None else 0]),method)
    if not np.isfinite(y).all():
        raise ValueError("Prediction contains an invalid number")
    return {"cue":cue,"method":method,"channels":list(CHANNELS),"horizons_s":list(HORIZONS),
            "delta":y.reshape(3,3).tolist()}


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("request",nargs="?",type=Path,default=here/"example.json")
    p.add_argument("--model",type=Path,default=here/"model.json")
    a = p.parse_args()
    print(json.dumps(request(json.loads(a.model.read_text()),json.loads(a.request.read_text())),indent=2))
