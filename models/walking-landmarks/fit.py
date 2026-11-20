"""Fit both residual Transformers, matched ridge regressions, and event-time means."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from predict import standardize, net_residual

HERE = Path(__file__).resolve().parent
SEED = 20261121


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weights_per_window(data):
    people, repeats = data["person"], data["repeat"]
    result = np.empty(len(people))
    for who in np.unique(people):
        indices = people == who
        trials = np.unique(repeats[indices])
        for trial in trials:
            valid = indices & (repeats == trial)
            result[valid] = 1/(len(np.unique(people))*len(trials)*valid.sum())
    return result


def means(x, w):
    w = w.reshape((len(w),) + (1,)*(x.ndim-1))
    good = np.isfinite(x)
    total = (good*w).sum(axis=0)
    return np.divide((np.where(good,x,0)*w).sum(axis=0),total,
                     out=np.full(x.shape[1:], np.nan), where=total>0)


def fit_ridge(flat, y, weight, penalty=.01):
    p = flat.shape[1]
    beta = np.zeros((p,y.shape[1]))
    intercept = np.zeros(y.shape[1])
    # Solve coordinates with identical masks together.
    masks = {}
    for j in range(y.shape[1]):
        masks.setdefault(np.isfinite(y[:,j]).tobytes(), []).append(j)
    for mask, js in masks.items():
        good = np.frombuffer(mask, bool)
        w = weight[good]/weight[good].sum()
        X, Y = flat[good], y[good][:,js]
        xm, ym = w@X, w@Y
        xc, yc = X-xm, Y-ym
        gram = (xc.T*w)@xc
        gram.flat[::p+1] += penalty
        b = np.linalg.solve(gram, (xc.T*w)@yc)
        beta[:,js] = b
        intercept[js] = ym-xm@b
    return beta, intercept


class TemporalResidual(nn.Module):
    def __init__(self, dimension, width=32, heads=4, hidden=64):
        super().__init__()
        if width % heads:
            raise ValueError("Width must divide into equal heads.")
        self.heads = heads
        self.embed = nn.Linear(dimension,width)
        self.pos = nn.Parameter(torch.randn(8,width)*.02)
        self.ln1 = nn.LayerNorm(width)
        self.qkv = nn.Linear(width,3*width)
        self.out = nn.Linear(width,width)
        self.ln2 = nn.LayerNorm(width)
        self.ff1 = nn.Linear(width,hidden)
        self.ff2 = nn.Linear(hidden,width)
        self.head = nn.Linear(width,18)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self,z):
        h = self.embed(z) + self.pos
        batch, length, width = h.shape
        qkv = self.qkv(self.ln1(h)).reshape(batch,length,3,self.heads,width//self.heads)
        q,k,v = qkv.permute(2,0,3,1,4).unbind(0)
        attn = (q@k.transpose(-1,-2)/(width//self.heads)**.5).softmax(-1)
        h = h+self.out((attn@v).transpose(1,2).reshape(h.shape))
        h = h+self.ff2(torch.relu(self.ff1(self.ln2(h))))
        return self.head(h[:,-1])


def fit_one(data, weights, family, store, epochs, max_batches=None):
    x = data["x"][...,:64 if family=="markers" else 80]
    y = data["y"].reshape(len(x),18)
    if not np.isfinite(y).any(axis=0).all():
        raise ValueError("Missing all targets for at least one coordinate.")
    wt = np.repeat(weights/8,8)
    raw = x.reshape(-1,x.shape[-1])
    mean = np.nan_to_num(means(raw,wt))
    sd = np.sqrt(means((raw-mean)**2, wt))
    def put(key, value):
        store[family + "." + key] = np.asarray(value)
    put("mean", mean)
    put("sd", np.where(sd>1e-6,sd,1))
    z = standardize(x,store,family)
    flat = z.reshape(len(z),-1)
    beta, intercept = fit_ridge(flat,y,weights)
    put("beta",beta)
    put("intercept",intercept)
    residual = y - (flat@beta+intercept)
    scale = np.sqrt(means(residual**2, weights))
    put("resid_sd", np.where(scale>1e-6,scale,1))
    residual /= store[family+".resid_sd"]
    torch.manual_seed(SEED)
    net = TemporalResidual(z.shape[-1])
    optimizer = torch.optim.AdamW(net.parameters(),lr=.002,weight_decay=.001)
    source = torch.tensor(z, dtype=torch.float32)
    good = torch.tensor(np.isfinite(residual))
    target = torch.tensor(np.nan_to_num(residual),dtype=torch.float32)
    importance = torch.tensor(weights*len(z),dtype=torch.float32)
    rng = np.random.default_rng(SEED)
    updates = 0
    for _ in range(epochs):
        order = rng.permutation(len(z))
        for off in range(0,len(z),128):
            ix = order[off:off+128]
            pred = net(source[ix])
            loss = (((pred-target[ix])**2)*good[ix]*importance[ix,None]).sum()/(18*len(ix))
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            updates += 1
            if updates == max_batches:
                break
        if updates == max_batches:
            break
    put("heads",net.heads)
    for key, value in net.state_dict().items():
        put(key,value.detach().cpu().numpy())
    with torch.no_grad():
        reference = net(source[:64]).numpy()
    portable = net_residual(z[:64],store,family)
    diff = float(np.max(abs((reference-portable)*store[family+".resid_sd"])))
    if diff > .002:
        raise RuntimeError(f"Portable prediction disagrees by {diff} mm.")
    return {"updates":updates,"max_portable_error_mm":diff,"probe":float(reference.mean())}


def phase_means(data,w):
    y, phase, bins = data["y"].reshape(-1,18), data["phase"], data["phase_bin"]
    result = {"global":means(y,w).tolist()}
    for label in sorted(set(phase)):
        group = phase==label
        base = means(y[group],w[group])
        base = np.where(np.isfinite(base),base,result["global"])
        result[str(label)] = base.tolist()
        for lag in np.unique(bins[group]):
            keep = group & (bins==lag)
            val = means(y[keep],w[keep])
            result[f"{label}.{lag}"] = np.where(np.isfinite(val),val,base).tolist()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--threads",type=int,default=1)
    parser.add_argument("--benchmark",action="store_true",help="Fixed training-prefix comparison, no fitted weights written")
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    data = np.load(args.train,allow_pickle=False)
    data = {key:data[key] for key in data.files}
    if set(data["person"])!=set(range(1,31)):
        raise ValueError("Expected only the thirty training participants.")
    started = time.monotonic()
    weights = weights_per_window(data)
    store, quality = {}, {}
    for family in ("markers","combined"):
        quality[family] = fit_one(data,weights,family,store,24,16 if args.benchmark else None)
    summary = {"threads":torch.get_num_threads(),"interop_threads":torch.get_num_interop_threads(),
               "torch":str(torch.__version__),"numpy":np.__version__,"cuda":torch.cuda.is_available(),
               "people":len(set(data["person"])),"trials":len(set(zip(data["person"],data["repeat"]))),
               "cutoffs":len(weights),"valid_by_landmark":np.isfinite(data["y"]).all(-1).sum(0).tolist(),
               "quality":quality,"fit_seconds":time.monotonic()-started}
    if not args.benchmark:
        out = args.output
        out.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(out/"weights.npz",**store)
        (out/"phase.json").write_text(json.dumps(phase_means(data,weights),separators=(",",":"))+"\n")
        frozen = ["protocol.json","source-clarification.json","fit.py","predict.py","assess.py","extract.py"]
        summary.update(protocol_sha256=sha(HERE/"protocol.json"),weights_sha256=sha(out/"weights.npz"),
                       phase_sha256=sha(out/"phase.json"),train_data_sha256=sha(args.train),
                       source_sha256={name:sha(HERE/name) for name in frozen})
        (out/"fit-seal.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
