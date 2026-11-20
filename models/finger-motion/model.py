# SPDX-License-Identifier: CC0-1.0
"""Fixed direct-regression readouts. Only history uses a glove input."""
from pathlib import Path

import numpy as np

MODALITY = {"cue": slice(0, 60), "cortex": slice(60, 152), "aligned": slice(0, 152)}


def selected(x, mode):
    x = np.asarray(x)
    if mode == "history":
        if x.ndim != 2 or x.shape[1] != 35:
            raise ValueError("The history comparator requires 35 past-glove features")
        return x
    if x.ndim != 3 or x.shape[1:] != (4, 152):
        raise ValueError("Expected N packets of four 152-feature tokens")
    return x[..., MODALITY[mode]]


def scales(x):
    sd = x.std(axis=0)
    return x.mean(axis=0), np.where(sd < 1e-8, 1., sd)


def target_scales(y):
    sd = y.std(axis=0)
    if np.any(sd < 1e-8):
        raise ValueError("Cannot scale a constant training target")
    return dict(ym=y.mean(axis=0), ys=sd)


def ridge_fit(packets, y, mode):
    x = selected(packets, mode).reshape(len(y), -1)
    mean, sd = scales(x)
    z = (x - mean) / sd
    norm = target_scales(y)
    target = (y - norm["ym"]) / norm["ys"]
    intercept = target.mean(axis=0)
    gram = z.T @ z
    gram.flat[::len(gram)+1] += 0.05 * len(y)
    weights = np.linalg.solve(gram, z.T @ (target - intercept))
    return dict(mean=mean, sd=sd, intercept=intercept, weights=weights, **norm)


def ridge_predict(packets, mode, w):
    x = selected(packets, mode).reshape(len(packets), -1)
    standardized = (x - w["mean"]) / w["sd"] @ w["weights"] + w["intercept"]
    return np.maximum(0., standardized * w["ys"] + w["ym"])


def encoder():
    from torch import nn
    import torch

    class TemporalEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.project = nn.Linear(152, 24)
            self.pos = nn.Parameter(torch.zeros(4, 24))
            self.layer = nn.TransformerEncoderLayer(24, 2, 48, dropout=0.,
                                                    activation="gelu", batch_first=True)
            self.out = nn.Linear(24, 5)

        def forward(self, x):
            return self.out(self.layer(self.project(x) + self.pos)[:, -1])

    return TemporalEncoder()


def encoder_input(packets, mode, w):
    import torch
    x = np.zeros((len(packets), 4, 152), dtype=np.float32)
    x[..., MODALITY[mode]] = (selected(packets, mode) - w["mean"]) / w["sd"]
    return torch.from_numpy(x)


def encoder_fit(packets, y, mode):
    import torch
    torch.manual_seed(319)
    net = encoder()
    feats = selected(packets, mode)
    mean, sd = scales(feats.reshape(-1, feats.shape[-1]))
    w = dict(mean=mean, sd=sd, **target_scales(y))
    x = encoder_input(packets, mode, w)
    target = torch.tensor((y-w["ym"])/w["ys"], dtype=torch.float32)
    opt = torch.optim.AdamW(net.parameters(), lr=0.001, weight_decay=0.01)
    order = torch.Generator().manual_seed(319)
    for _ in range(24):
        for idx in torch.randperm(len(x), generator=order).split(128):
            opt.zero_grad(set_to_none=True)
            torch.nn.functional.mse_loss(net(x[idx]), target[idx]).backward()
            opt.step()
    return {**w, **{f"param.{k}": v.detach().numpy() for k, v in net.state_dict().items()}}


def encoder_predict(packets, mode, w):
    import torch
    net = encoder()
    net.load_state_dict({k[6:]: torch.from_numpy(v.copy()) for k, v in w.items() if k.startswith("param.")})
    net.eval()
    with torch.inference_mode():
        x = encoder_input(packets, mode, w)
        standardized = torch.cat([net(batch) for batch in x.split(128)]).numpy()
    return np.maximum(0., standardized * w["ys"] + w["ym"])


def load(path):
    with np.load(Path(path), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}
