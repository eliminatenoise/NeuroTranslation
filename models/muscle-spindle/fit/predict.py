"""Predict the expected spike count in the next 20 ms. Python standard library only."""
import argparse
import json
import math
from pathlib import Path

def predict_count(model, history):
    """history is five completed bins, oldest first, in the order in model['channels']."""
    if model.get("format") != "spindle-count-transformer-1":
        raise ValueError("Unsupported weight format")
    if not isinstance(history,(list,tuple)) or len(history) != 5:
        raise ValueError("Supply five completed 20 ms bins, oldest first")
    active = set(model["active"])
    mean, sd = (model["normalizer"][k] for k in ("mean","sd"))
    tokens = []
    for row in history:
        if not isinstance(row,(list,tuple)) or len(row) != 5:
            raise ValueError("Each bin needs five input numbers")
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or abs(x) > float.fromhex('0x1.fffffffffffffp+1023') or not math.isfinite(x) for x in row):
            raise ValueError("Inputs must be finite numbers")
        if row[4] < 0 or row[4] > 2**53-1 or int(row[4]) != row[4]:
            raise ValueError("Spike counts must be nonnegative safe integers")
        tokens.append([max(-10.,min(10.,(x-mean[i])/sd[i])) if i in active else 0. for i,x in enumerate(row)])
    weights = model["weights"]
    def linear(name, x):
        return [sum(a*b for a,b in zip(x,row))+bias
                for row,bias in zip(weights[name+".weight"],weights[name+".bias"])]
    def norm(name, x):
        avg = sum(x)/len(x)
        inv = 1/math.sqrt(sum((a-avg)**2 for a in x)/len(x)+1e-5)
        return [(a-avg)*inv*w+b for a,w,b in zip(x,weights[name+".weight"],weights[name+".bias"])]
    def add(x,y):
        return [a+b for a,b in zip(x,y)]
    h = [add(linear("embed", row), pos) for row,pos in zip(tokens,weights["position"])]
    qkv = [linear("qkv",norm("attn_norm",row)) for row in h]
    width = model["width"]
    depth = width//model["heads"]
    out = []
    for t, item in enumerate(h):
        attended = []
        for head in range(model["heads"]):
            offset = head*depth
            q = qkv[t][offset:offset+depth]
            scores = [sum(a*b for a,b in zip(q,row[width+offset:width+offset+depth]))/math.sqrt(depth) for row in qkv]
            top = max(scores)
            scores = [math.exp(score-top) for score in scores]
            total = sum(scores)
            for j in range(depth):
                attended.append(sum(s*row[2*width+offset+j] for s,row in zip(scores,qkv))/total)
        u = add(item,linear("proj",attended))
        hidden = [max(0.,v) for v in linear("expand",norm("ff_norm",u))]
        out.append(add(u,linear("reduce",hidden)))
    z = linear("readout",norm("final_norm",out[-1]))[0]
    return max(0.,z)+math.log1p(math.exp(-abs(z)))+1e-6

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("weights",type=Path)
    p.add_argument("history",type=Path,help="JSON array of five raw input rows, oldest first")
    args=p.parse_args()
    print(json.dumps({"expected_spikes_next_20ms":predict_count(json.loads(args.weights.read_text()),json.loads(args.history.read_text()))},allow_nan=False))
