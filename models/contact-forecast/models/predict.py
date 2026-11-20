"""Predict expected event counts for 26 named cortical contacts using only NumPy."""
import argparse
import json
from pathlib import Path
import numpy as np

FORMAT = "area2-26-contact-count-v1"
SEEDS = (17, 41, 73)
CONTACTS = (4,12,13,15,16,18,19,25,27,29,31,35,36,37,39,49,51,52,53,54,58,61,65,72,88,90)
BLOCKS = {"movement":slice(0,4), "count":slice(4,30), "cue":slice(30,40)}
FIELDS = {"movement_tokens_cm":slice(0,4), "count_tokens_40ms":slice(4,30),
          "cues":slice(30,37), "cue_elapsed_s":slice(37,40)}
MODES = {"all":tuple(BLOCKS), "count_cue":("count","cue"), "cue":("cue",),
         "movement":("movement",), "count":("count",), "movement_cue":("movement","cue")}
SHAPES = {"position":(5,16)}
for key, sizes in {"embed":(16,40), "qkv":(48,16), "project":(16,16), "expand":(32,16),
                   "reduce":(16,32), "readout":(26,16)}.items():
    SHAPES[key+".weight"] = sizes
    SHAPES[key+".bias"] = (sizes[0],)
for key in ("attn_norm","ff_norm","final_norm"):
    for suffix in ("weight","bias"):
        SHAPES[key+"."+suffix] = (16,)


def mask(mode):
    keep = np.zeros(40, dtype=bool)
    for key in MODES[mode]:
        keep[BLOCKS[key]] = True
    return keep


def numeric(value,shape,name):
    a = np.asarray(value)
    if a.shape != shape or a.dtype.kind not in "iuf" or not np.isfinite(a).all():
        raise ValueError(f"{name} requires finite numeric values of shape {shape}")
    return a.astype(np.float64,copy=False)


def read_weights(path):
    w = json.loads(Path(path).read_text())
    if (w["format"] != FORMAT or tuple(w["contact_ids"]) != CONTACTS or w["mode"] not in MODES or
            w["family"] not in ("transformer","poisson")):
        raise ValueError("unrecognized parameters, family or contact order")
    if (w["family"] == "transformer" and w["seed"] not in SEEDS) or (w["family"] == "poisson" and w["seed"] is not None):
        raise ValueError("unexpected seed for this family")
    shapes = SHAPES if w["family"] == "transformer" else {"coef":(200,26),"intercept":(26,)}
    if set(w["parameters"]) != set(shapes):
        raise ValueError("incorrect parameter inventory")
    w["parameters"] = {k:numeric(w["parameters"][k],s,k) for k,s in shapes.items()}
    for key in ("x_mean","x_scale"):
        w[key] = numeric(w[key],(40,),key)
    w["x_active"] = np.asarray(w["x_active"])
    if np.any(w["x_scale"]<=0) or w["x_active"].shape!=(40,) or w["x_active"].dtype.kind!="b":
        raise ValueError("invalid feature scaler")
    return w


def stack_inputs(source):
    if tuple(source["contact_id"]) != CONTACTS:
        raise ValueError("contact identifiers or ordering differ")
    n = len(source["movement_tokens_cm"])
    raw = np.empty((n,5,40))
    for key,span in FIELDS.items():
        raw[:,:,span] = numeric(source[key],(n,5,span.stop-span.start),key)
    counts = raw[:,:,4:30]
    if (counts<0).any() or (counts!=np.floor(counts)).any():
        raise ValueError("counts must be nonnegative integers")
    for col,elapsed in ((30,37),(33,38),(36,39)):
        flags = raw[:,:,col]
        t = raw[:,:,elapsed]
        if (not np.isin(flags,[0,1]).all() or np.any(np.diff(flags)<0) or (t[flags==0]!=0).any()
                or (t[flags==1]<=0).any()):
            raise ValueError("cue times and visibility disagree")
        if col != 36:
            xy = raw[:,:,col+1:col+3]
            if ((xy[flags==0]!=0).any() or (np.sum(xy[flags==1]**2,axis=-1)!=1).any()
                    or (np.diff(xy,axis=1)[flags[:,:-1]==1]!=0).any()):
                raise ValueError("invalid visible cue direction")
    return raw


def standardize(x,w):
    z = np.clip((x-w["x_mean"])/w["x_scale"],-8,8)
    return z*(np.asarray(w["x_active"]) & mask(w["mode"]))


def forward(x,w):
    """Batched reference implementation with one row per five-token history."""
    x = standardize(x,w)
    p = w["parameters"]
    if w["family"] == "poisson":
        m = np.exp(x.reshape(-1,200) @ p["coef"] + p["intercept"])
    else:
        def affine(h,key):
            return h @ p[key+".weight"].T + p[key+".bias"]
        def norm(h,key):
            c = h - h.mean(axis=-1,keepdims=True)
            return c/np.sqrt((c*c).mean(axis=-1,keepdims=True)+1e-5)*p[key+".weight"]+p[key+".bias"]
        h = affine(x,"embed")+p["position"]
        q,k,v = affine(norm(h,"attn_norm"),"qkv").reshape(-1,5,3,2,8).transpose(2,0,3,1,4)
        a = (q @ k.swapaxes(-1,-2))/np.sqrt(8.)
        a = np.exp(a-a.max(axis=-1,keepdims=True))
        attended = ((a/a.sum(axis=-1,keepdims=True)) @ v).transpose(0,2,1,3).reshape(-1,5,16)
        h = h + affine(attended,"project")
        h = h + affine(np.maximum(affine(norm(h,"ff_norm"),"expand"),0),"reduce")
        m = np.logaddexp(0,affine(norm(h[:,-1,:],"final_norm"),"readout"))+1e-6
    if not np.isfinite(m).all() or not (m>0).all():
        raise ValueError("invalid forecast")
    return m


def predict(weights_path, history):
    """Read a single history with explicit contact order and return contact means."""
    row = {k:np.asarray(history[k])[None] for k in FIELDS}
    row["contact_id"] = history["contact_id"]
    return forward(stack_inputs(row),read_weights(weights_path))[0]


if __name__=="__main__":
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("weights",type=Path)
    cmd.add_argument("history",type=Path)
    args = cmd.parse_args()
    history = json.loads(args.history.read_text())
    counts = predict(args.weights,history)
    print(json.dumps(dict(contact_id=list(CONTACTS),expected_counts_per_100ms=counts.tolist())))
