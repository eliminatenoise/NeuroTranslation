"""CPU fitting and inference arithmetic shared with the two-wrist experiment."""
import math
from collections import OrderedDict

import numpy as np

MASK = np.triu(np.ones((5, 5), dtype=bool), k=1)
STEPS, LR, DECAY = 48, 0.003, 0.02
HORIZONS = np.array([8, 15], dtype=np.float64)

def initial(seed):
    rng = np.random.default_rng(seed)
    def weight(shape, fan):
        return rng.normal(size=shape) / math.sqrt(fan)
    return OrderedDict(
        input_w=weight((26,8),26), input_b=np.zeros(8), position=.05*rng.normal(size=(5,8)),
        q=weight((8,8),8), k=weight((8,8),8), v=weight((8,8),8), o=weight((8,8),8),
        ff1=weight((8,12),8), ff1_b=np.zeros(12), ff2=weight((12,8),12), ff2_b=np.zeros(8),
        readout=weight((8,4),8), bias=np.zeros(4),
    )


def native_forward(x, p, mask):
    import torch
    def norm(t):
        return t * torch.rsqrt((t*t).mean(dim=-1,keepdim=True) + 1e-5)
    h = x @ p["input_w"] + p["input_b"] + p["position"]
    n = norm(h)
    q,k,v = [n @ p[key] for key in ("q","k","v")]
    score = (q @ k.transpose(1,2))/math.sqrt(8)
    att = torch.softmax(score.masked_fill(mask, -torch.inf), dim=2)
    h2 = h + (att @ v) @ p["o"]
    ff = torch.tanh(norm(h2) @ p["ff1"] + p["ff1_b"])
    h3 = h2 + ff @ p["ff2"] + p["ff2_b"]
    return h3[:,-1] @ p["readout"] + p["bias"]


def eligibility(data):
    """Same prespecified electrical mask for all methods, independent arm pose masks."""
    voltage = np.asarray(data["ecog_uv"], dtype=np.float64)
    n = len(voltage)
    finite = np.isfinite(voltage).all(axis=(1, 2))
    varying = np.zeros(n, bool)
    varying[finite] = (np.ptp(voltage[finite], axis=1) > 0).any(axis=1)
    electrical = finite & varying & ~(voltage == 0).all(axis=2).any(axis=1)
    arms = data["prior_pose_px"].reshape(n, 15, 2, 3, 2)
    pose = np.isfinite(arms).all(axis=(1, 3, 4))
    return electrical, pose


def side_features(voltage, arm):
    voltage = np.asarray(voltage, dtype=np.float64)
    arm = np.asarray(arm, dtype=np.float64)
    n = len(arm)
    last = arm[:, 2::3]
    relative = (last[:, :, :2] - last[:, :, 2:3]).reshape(n, 5, 4)
    delta = (last - arm[:, :1]).reshape(n, 5, 6)
    group = voltage.reshape(n, 5, 50, 8)
    log_rms = np.log(np.maximum(np.sqrt(np.mean(group ** 2, axis=2)), 1e-6))
    raw = np.concatenate((relative, delta, group.mean(axis=2), log_rms), axis=2)
    anchor = arm[:, -1, 0, :]
    velocity = (anchor - arm[:, 0, 0, :])[:, None, :] * HORIZONS[None, :, None] / 14.
    return raw, anchor, velocity


def raw_transform(raw, treatment, mean, scale, prior):
    """Map final network activations to displacement in camera pixels."""
    out = raw.reshape(-1, 2, 2)
    if treatment == "direct":
        return out * scale + mean
    return prior + 0.25 * scale * np.tanh(out)


def head_data(data, future, allowed, side_i):
    eok, pok = eligibility(data)
    target_ok = np.isfinite(future[:, :, side_i, :]).all(axis=2)
    keep = allowed & eok & pok[:, side_i] & target_ok.any(axis=1)
    ids = np.flatnonzero(keep)
    arm = data["prior_pose_px"][ids, :, 3 * side_i:3 * side_i + 3, :]
    raw, anchor, velocity = side_features(data["ecog_uv"][ids], arm)
    y = future[ids, :, side_i, :] - anchor[:, None]
    mask = target_ok[ids]
    stats = {"feature_mean": raw.mean(axis=(0, 1)), "feature_scale": raw.std(axis=(0, 1))}
    stats["feature_scale"][stats["feature_scale"] < 1e-8] = 1.
    mean, scale, damping = [], [], []
    for h in range(2):
        valid = mask[:, h]
        if valid.sum() < 2:
            raise ValueError("Fewer than two fitting rows for a horizon")
        target = y[valid, h]
        v = velocity[valid, h]
        v2 = np.sum(v * v, axis=1)
        regularizer = 16 * max(float(np.median(v2)), 1.)
        damping.append(np.clip(((v * target).sum() + regularizer * .5) / (v2.sum() + regularizer), 0, 1))
        mean.append(target.mean(axis=0))
        scale.append(np.maximum(target.std(axis=0), 1.))
    stats.update(mean=np.array(mean), scale=np.array(scale), damping=np.array(damping))
    return (raw - stats["feature_mean"]) / stats["feature_scale"], y, velocity, mask, ids, stats


def targets(y, vel, mask, stats, treatment):
    prior = vel * stats["damping"][None, :, None] if treatment == "anchored" else np.zeros_like(vel)
    center = stats["mean"] if treatment == "direct" else 0.
    target = (y - prior - center) / stats["scale"]
    # Invalid entries take zero weight. A finite placeholder avoids NaN gradients under masking.
    return np.where(mask[:, :, None], target, 0.)


def fit_net(x, target, mask, seed, treatment, device):
    import torch
    p = {k: torch.nn.Parameter(torch.tensor(v, device=device)) for k, v in initial(seed).items()}
    opt = torch.optim.AdamW(p.values(), lr=LR, betas=(.9, .999), eps=1e-8, weight_decay=DECAY,
                            foreach=False, fused=False)
    xt = torch.tensor(x, device=device)
    yt = torch.tensor(target, device=device)
    keep = torch.tensor(np.broadcast_to(mask[:, :, None], target.shape).copy(), device=device)
    causal = torch.tensor(MASK, device=device)

    def loss():
        raw = native_forward(xt, p, causal).reshape(-1, 2, 2)
        if treatment == "direct":
            return ((raw[keep] - yt[keep]) ** 2).mean()
        adjusted = .25 * torch.tanh(raw)
        return ((adjusted[keep] - yt[keep]) ** 2).mean() + (adjusted[keep] ** 2).mean()

    trajectory = []
    for _ in range(STEPS):
        opt.zero_grad(set_to_none=True)
        objective = loss()
        objective.backward()
        opt.step()
        trajectory.append(objective.detach())
    with torch.no_grad():
        trajectory.append(loss())
        native_raw = native_forward(xt, p, causal).cpu().numpy()
    return {k: v.detach().cpu().numpy().copy() for k, v in p.items()}, torch.stack(trajectory).cpu().numpy(), native_raw
