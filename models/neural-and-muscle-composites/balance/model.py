"""Matched trainable two-branch fusion models for the visual-rotation study."""
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

PROTOCOL = json.loads(Path(__file__).with_name("protocol.json").read_bytes())
BASES = {"paired":(), "early":(), "crossed":(), "without_scalp":(0,), "without_muscle":(1,),
         "without_position":(2,), "without_physics":(3,), "without_electrical":(0,1),
         "without_mechanics":(2,3)}
STREAMS = ("scalp", "leg", "position", "physics")
WIDTHS = (33, 40, 60, 12)
KNOTS = np.array([8,16,24,32])


def load(path):
    with np.load(path, allow_pickle=False) as file:
        return {k:file[k] for k in file.files}


def targets(a):
    y_leg = np.log1p(a["y_leg"])
    y_path = a["y_path"][:, KNOTS-1].reshape(len(y_leg), -1)
    return np.column_stack((y_leg, y_path))


def scales(a):
    results = {}
    for name, x in [(k,a[k]) for k in STREAMS] + [("target",targets(a))]:
        if name == "scalp":
            mask = a["present"][:, None, :, None]
            count = np.maximum(mask.sum(axis=0), 1)
            mean = (x*mask).sum(axis=0) / count
            sd = np.sqrt((((x-mean)**2)*mask).sum(axis=0) / count)
        else:
            mean, sd = x.mean(axis=0), x.std(axis=0)
        results[name+"_mean"] = mean
        results[name+"_scale"] = np.where(sd >= 1e-6, sd, 1.)
    return results


def mapped(a, s, device):
    streams = []
    for name in STREAMS:
        x = (a[name]-s[name+"_mean"])/s[name+"_scale"]
        if name == "scalp":
            x = np.where(a["present"][:, None, :, None], x, 0)
            x = np.column_stack((x.reshape(len(x),-1), a["present"]))
        streams.append(x.reshape(len(x), -1))
    context = np.column_stack((a["posture"],a["direction"]))
    return [torch.as_tensor(x, dtype=torch.float32, device=device) for x in [*streams, context]]


class Fusion(nn.Module):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.projections = nn.ModuleList(nn.Linear(w,16) for w in WIDTHS)
        self.branches = nn.ModuleList(nn.Linear(48,16) for _ in range(2))
        self.join = nn.Linear(50,32)
        self.head = nn.Linear(32,20)

    def forward(self, xs):
        projections = []
        for i, projection in enumerate(self.projections):
            x = xs[i]
            if i in BASES[self.name]:
                x = (torch.cat((torch.zeros_like(x[:, :-3]),x[:, -3:]),dim=1)
                     if i == 0 else torch.zeros_like(x))
            projections.append(torch.tanh(projection(x)))
        a,b,c,d = projections
        if self.name == "early":
            a,b,c,d = ((a+b+c+d)*.5, (a-b+c-d)*.5, (a+b-c-d)*.5, (a-b-c+d)*.5)
        elif self.name == "crossed":
            b,c = c,b
        left = torch.tanh(self.branches[0](torch.cat((a,b,a*b), dim=1)))
        right = torch.tanh(self.branches[1](torch.cat((c,d,c*d), dim=1)))
        joined = torch.cat((left, right, left*right, xs[4]), dim=1)
        return self.head(torch.tanh(self.join(joined)))


def row_probabilities(a):
    keys = list(zip(a["person"], a["posture"], a["direction"]))
    counts = {}
    for key in keys:
        counts[key] = counts.get(key,0) + 1
    weights = np.array([1/counts[key] for key in keys])
    return weights/weights.sum()


def fit_model(name, seed, xs, y, batches, device):
    torch.manual_seed(seed)
    net = Fusion(name).to(device)
    optimizer = torch.optim.AdamW(net.parameters(), lr=.002, weight_decay=.01, foreach=False)
    for ix in batches:
        output = net([x[ix] for x in xs])
        target = y[ix]
        loss = (F.smooth_l1_loss(output[:, :8],target[:, :8]) +
                F.smooth_l1_loss(output[:, 8:],target[:, 8:]))*.5
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    net.eval()
    return net


def decode(prediction, s):
    y = prediction.astype(np.float64)*s["target_scale"]+s["target_mean"]
    emg = np.maximum(0., np.expm1(y[:, :8]))
    knots = np.concatenate((np.zeros((len(y),1,3)),y[:,8:].reshape(-1,4,3)), axis=1)
    t = np.arange(1,33)
    upper = (t+7)//8
    fraction = (t-(upper-1)*8)[None,:,None]/8
    path = (1-fraction)*knots[:, upper-1] + fraction*knots[:, upper]
    if not (np.isfinite(emg).all() and np.isfinite(path).all()):
        raise ValueError("nonfinite forecast")
    return emg, path


def draws(a, seed, updates):
    rng = np.random.default_rng(seed)
    return rng.choice(len(a["event"]), size=(updates,128), p=row_probabilities(a))


def fit_tensors(a, s, device):
    standardized = (targets(a)-s["target_mean"])/s["target_scale"]
    return mapped(a,s,device), torch.as_tensor(standardized,dtype=torch.float32,device=device)
