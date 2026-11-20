"""Fixed person-separated fitting procedure; requires NumPy and PyTorch."""
import numpy as np
import torch
from torch import nn
from predict import NETWORKS, RIDGES, ONLY, attention, batch, design, inputs, transform


def balance(g):
    groups = [np.arange(len(g))]
    w = np.ones(len(g))
    for col in (0,1,2):
        children = []
        for ids in groups:
            values = g[ids,col]
            unique = np.unique(values)
            w[ids] /= len(unique)
            children.extend(ids[values==val] for val in unique)
        groups = children
    for ids in groups:
        w[ids] /= len(ids)
    return w


def donors(g):
    """Each recipient's other same-person, run and cue rows in cyclic clock order."""
    indices = []
    for row in g:
        ids = np.flatnonzero((g[:,:3]==row[:3]).all(axis=1))
        ids = ids[np.argsort(g[ids,3])]
        pos = np.flatnonzero(g[ids,3]==row[3])
        if len(pos)!=1:
            raise ValueError("Ambiguous recipient clock")
        indices.append(np.roll(ids,-int(pos[0]))[1:])
    return indices


def moments(x,w):
    mean = np.average(x,weights=w,axis=0)
    sd = np.sqrt(np.average((x-mean)**2,weights=w,axis=0))
    return mean,sd


def weighted_median(x,w):
    vals = []
    for column in x.T:
        order = np.argsort(column,kind="stable")
        v,wt = column[order],w[order]
        cum = np.cumsum(wt)/np.sum(wt)
        left = int(np.searchsorted(cum,0.5-1e-12))
        right = min(int(np.searchsorted(cum,0.5+1e-12)),len(v)-1)
        vals.append(float((v[left]+v[right])/2))
    return vals


class Transformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.project = nn.Linear(15,8)
        self.anchor = nn.Linear(3,8)
        self.cue = nn.Embedding(8,8)
        self.position = nn.Parameter(torch.empty(5,8))
        nn.init.normal_(self.position,std=0.02)
        self.q,self.k,self.v,self.attn_out = [nn.Linear(8,8) for _ in range(4)]
        self.norm1,self.norm2 = nn.LayerNorm(8),nn.LayerNorm(8)
        self.ff1,self.ff2 = nn.Linear(8,12),nn.Linear(12,8)
        self.head = nn.Linear(8,9)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self,z,a,ids):
        h = torch.cat(((self.cue(ids)+self.anchor(a))[:,None],self.project(z)),dim=1)+self.position
        q,k,v = [layer(h).reshape(-1,5,2,4).transpose(1,2) for layer in (self.q,self.k,self.v)]
        weights = torch.softmax(q @ k.transpose(-2,-1)/2,dim=-1)
        ctx = (weights @ v).transpose(1,2).reshape(-1,5,8)
        h = self.norm1(h+self.attn_out(ctx))
        h = self.norm2(h+self.ff2(torch.tanh(self.ff1(h))))
        return self.head(h[:,0])


def network(z,a,ids,target,w,steps=48,device="cpu"):
    torch.manual_seed(29371)
    net = Transformer().to(device)
    initial = {n:t.detach().clone() for n,t in net.named_parameters()}
    zz,aa,yy,ww = [torch.as_tensor(t,dtype=torch.float32,device=device) for t in (z,a,target,w)]
    ids = torch.as_tensor(ids,dtype=torch.long,device=device)
    optimizer = torch.optim.AdamW(net.parameters(),lr=0.007,weight_decay=0.025)
    def loss(pred):
        return (nn.functional.smooth_l1_loss(pred,yy,beta=0.5,reduction="none").mean(dim=1)*ww).sum()
    first = None
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        obj = loss(net(zz,aa,ids))
        if first is None:
            first = float(obj.detach())
        obj.backward()
        nn.utils.clip_grad_norm_(net.parameters(),1.0)
        optimizer.step()
    with torch.no_grad():
        pred = net(zz,aa,ids)
        last = float(loss(pred))
    weights = {k:v.detach().cpu().tolist() for k,v in net.named_parameters()}
    changes = {k:float((v.detach()-initial[k]).norm()) for k,v in net.named_parameters()}
    native = pred.detach().cpu().numpy()
    replay = attention(weights,z,a,ids.cpu().numpy())
    gap = np.max(np.abs(native-replay))
    if not np.isfinite(last) or not np.allclose(replay,native,rtol=1e-4,atol=1e-4):
        raise ValueError("Nonfinite loss or portable inference mismatch")
    diag = {"parameters":sum(v.numel() for v in net.parameters()),"updates":steps,
            "first_loss":first,"last_loss":last,"parameter_l2_updates":changes,
            "portable_max_abs_standardized_error":float(gap)}
    return weights,diag


def fit(rows):
    h,s,e,y,g = rows
    people = set(map(int,g[:,0]))
    if not people or not people.issubset(set(range(1,8))) or not set(g[:,1]).issubset({1,2,3}):
        raise ValueError("Only training people and fitting runs are eligible")
    w = balance(g)
    raw = transform(h,s,e)
    flat = y.reshape(-1,9)
    scales = {}
    for key,x in raw.items():
        if x.ndim == 3:
            x = x.reshape(-1,x.shape[-1])
            wt = np.repeat(w/4,4)
        else:
            wt = w
        mean,sd = moments(x,wt)
        scales[key] = [mean.tolist(),np.where(sd<1e-8,1,sd).tolist()]
    cue = g[:,2]
    cue_median,cue_mean = [],[]
    for i in range(7):
        focus = cue==i
        if not focus.any():
            raise ValueError("Missing training cue")
        cue_median.append(weighted_median(flat[focus],w[focus]))
        cue_mean.append(np.average(flat[focus],weights=w[focus],axis=0).tolist())
    _,sy = moments(flat,w)
    model = {"format":"early-scalp-arm-v1","scales":scales,"target_sd":np.where(sy<1e-8,1,sy).tolist(),
             "constant_targets":(sy<1e-8).tolist(),"cue_median":cue_median,"cue_mean":cue_mean,
             "global_median":weighted_median(flat,w),"fits":{}}
    diagnostics = {}
    pairs = donors(g)
    if any(not len(ids) for ids in pairs):
        raise ValueError("Mispaired fitting requires a second trial for every cue group")
    displaced = transform(h,s[[ids[0] for ids in pairs]],e)
    for method in NETWORKS+RIDGES:
        representation = displaced if method=="mispaired_fit" else raw
        z,a,ids = inputs(model,representation,cue,method)
        baseline = model["global_median"] if method in ONLY else np.asarray(cue_median)[cue]
        target = (flat-baseline)/model["target_sd"]
        if method in RIDGES:
            d = design(z,a,ids)
            dm,ym = np.average(d,axis=0,weights=w),np.average(target,axis=0,weights=w)
            d0 = d-dm
            coef = np.linalg.solve(d0.T@(w[:,None]*d0)+0.25*np.eye(d.shape[1]),d0.T@(w[:,None]*(target-ym)))
            model["fits"][method] = {"coef":coef.tolist(),"bias":(ym-dm@coef).tolist()}
        else:
            model["fits"][method],diagnostics[method] = network(z,a,ids,target,w)
    return model,diagnostics
