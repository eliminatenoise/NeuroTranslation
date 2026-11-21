"""Five-token causal attention encoder; deterministic AdamW training."""

from collections import OrderedDict
import math
import numpy as np

STEPS = 48
LR = 0.003
DECAY = 0.02
SEEDS = (17, 37, 73)
MASK = np.triu(np.ones((5, 5), dtype=bool), k=1)


def initial(seed):
    rng = np.random.default_rng(seed)

    def weight(shape, fan):
        return rng.normal(size=shape) / math.sqrt(fan)

    return OrderedDict(
        input_w=weight((26, 8), 26),
        input_b=np.zeros(8),
        position=0.05 * rng.normal(size=(5, 8)),
        q=weight((8, 8), 8),
        k=weight((8, 8), 8),
        v=weight((8, 8), 8),
        o=weight((8, 8), 8),
        ff1=weight((8, 12), 8),
        ff1_b=np.zeros(12),
        ff2=weight((12, 8), 12),
        ff2_b=np.zeros(8),
        readout=weight((8, 4), 8),
        bias=np.zeros(4),
    )


def rms_norm(a):
    inv = 1 / np.sqrt(np.mean(a * a, axis=-1, keepdims=True) + 1e-5)
    return a * inv, inv


def np_forward(x, p, cache=False):
    h = x @ p["input_w"] + p["input_b"] + p["position"]
    n, hi = rms_norm(h)
    q, k, v = [n @ p[name] for name in ("q", "k", "v")]
    score = q @ k.transpose(0, 2, 1) / math.sqrt(8)
    score = np.where(MASK, -np.inf, score)
    exp = np.exp(score - score.max(axis=2, keepdims=True))
    att = exp / exp.sum(axis=2, keepdims=True)
    context = att @ v
    h2 = h + context @ p["o"]
    m, mi = rms_norm(h2)
    ff = np.tanh(m @ p["ff1"] + p["ff1_b"])
    h3 = h2 + ff @ p["ff2"] + p["ff2_b"]
    out = h3[:, -1] @ p["readout"] + p["bias"]
    if cache:
        return out, (x, n, hi, q, k, v, att, context, m, mi, ff, h3)
    return out


def native_forward(x, p, mask):
    import torch

    def norm(t):
        return t * torch.rsqrt((t * t).mean(dim=-1, keepdim=True) + 1e-5)

    h = x @ p["input_w"] + p["input_b"] + p["position"]
    n = norm(h)
    q, k, v = [n @ p[key] for key in ("q", "k", "v")]
    score = (q @ k.transpose(1, 2)) / math.sqrt(8)
    att = torch.softmax(score.masked_fill(mask, -torch.inf), dim=2)
    h2 = h + (att @ v) @ p["o"]
    ff = torch.tanh(norm(h2) @ p["ff1"] + p["ff1_b"])
    h3 = h2 + ff @ p["ff2"] + p["ff2_b"]
    return h3[:, -1] @ p["readout"] + p["bias"]


def native_fit(x, target, init, device):
    import torch

    p = {k: torch.nn.Parameter(torch.tensor(v, device=device)) for k, v in init.items()}
    optimizer = torch.optim.AdamW(
        p.values(),
        lr=LR,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=DECAY,
        foreach=False,
        fused=False,
    )
    tx, ty = [torch.tensor(v, device=device) for v in (x, target)]
    mask = torch.tensor(MASK, device=device)
    losses = []
    for t in range(STEPS):
        optimizer.zero_grad(set_to_none=True)
        loss = ((native_forward(tx, p, mask) - ty) ** 2).mean()
        loss.backward()
        if t == 0:
            first_grad = {k: v.grad.detach().cpu().numpy().copy() for k, v in p.items()}
        losses.append(loss.detach())
        optimizer.step()
    with torch.no_grad():
        losses.append(((native_forward(tx, p, mask) - ty) ** 2).mean())
    return (
        {k: v.detach().cpu().numpy().copy() for k, v in p.items()},
        first_grad,
        torch.stack(losses).cpu().numpy(),
    )


def prepare(raw, velocity, target, modality, treatment):
    mu, sd = raw[:16].mean(axis=(0, 1)), raw[:16].std(axis=(0, 1))
    sd = np.where(sd < 1e-8, 1.0, sd)
    x = (raw - mu) / sd
    if modality == "pose":
        x[:, :, 10:] = 0
    prior = 0.5 * velocity if treatment == "residual" else np.zeros_like(velocity)
    center = (target[:16] - prior[:16]).mean(axis=0)
    scale = np.maximum(target[:16].std(axis=0), 1.0)
    yfit = (target[:16] - prior[:16] - center) / scale
    return (
        x,
        yfit,
        prior,
        {"feature_mean": mu, "feature_scale": sd, "center": center, "scale": scale},
    )


def linear(x, target, prior):
    z = x.reshape(len(x), -1)
    zm = z[:16].mean(axis=0)
    zc = z[:16] - zm
    target_res = target[:16] - prior[:16]
    offset = target_res.mean(axis=0)
    alpha = np.linalg.solve(zc @ zc.T + 16 * np.eye(16), target_res - offset)
    coef = zc.T @ alpha
    return (z - zm) @ coef + offset + prior, {"coef": coef, "offset": offset, "zmean": zm}
