"""Fit the full attention, blocked-attention and earlier-arm interventions."""
import time

import numpy as np
import torch

from .temporal import HORIZONS, SEEDS, corrections, earlier_donors, geometry, ridge_design

from .weights import PARAMETERS


def init(seed, device):
    rng = np.random.default_rng(seed)
    values = {}
    for name, shape in PARAMETERS.items():
        if name.endswith("bias"):
            value = np.full(shape, -1.0 if name == "gate_bias" else 0.0)
        else:
            value = rng.normal(0, 0.08 if name in ("side", "time") else 1 / np.sqrt(shape[0]), shape)
        values[name] = torch.nn.Parameter(torch.tensor(value, device=device))
    return torch.nn.ParameterDict(values)


def direct(x, w, cross, blocked):
    n = len(x)
    hidden = x @ w["input"] + w["input_bias"]
    hidden = (hidden + w["time"][None, None] + w["side"][None, :, None]).reshape(n, 30, 12)
    q, k, v = [(hidden @ w[name]).reshape(n, 30, 2, 6).permute(0, 2, 1, 3)
               for name in ("query", "key", "value")]
    scores = q @ k.transpose(-2, -1) / np.sqrt(6) + cross * w["other_bias"][None, :, None, None]
    if blocked:
        scores = scores.masked_fill(cross, -torch.inf)
    mixed = torch.softmax(scores, dim=-1) @ v
    hidden = hidden + mixed.permute(0, 2, 1, 3).reshape(n, 30, 12) @ w["out"]
    hidden = hidden + torch.tanh(hidden @ w["ff_in"] + w["ff_bias"]) @ w["ff_out"]
    end = hidden.reshape(n, 2, 15, 12)[:, :, -1]
    gate = torch.sigmoid(end @ w["gate"] + w["gate_bias"])
    residual = 0.5 * gate * torch.tanh(end @ w["decode"] + w["decode_bias"])
    return residual.reshape(n, 2, 2, 2).permute(0, 2, 1, 3)


def native(x, donor, w, cross, mode):
    if mode == "trained_swap":
        contra = torch.stack((x[:, 0], donor[:, 1]), dim=1)
        ipsi = torch.stack((donor[:, 0], x[:, 1]), dim=1)
        both = direct(torch.cat((contra, ipsi)), w, cross, False)
        return torch.stack((both[:len(x), :, 0], both[len(x):, :, 1]), dim=2)
    return direct(x, w, cross, mode == "blocked")


def dictionary(w):
    return {key: value.detach().cpu().numpy() for key, value in w.items()}


def fit_model(features, donors, target, prior, mode, seed, device):
    x, d, y = [torch.as_tensor(value, dtype=torch.float64, device=device)
               for value in (features, donors, target - prior["mean"])]
    ids = torch.arange(30, device=device) // 15
    cross = ids[:, None] != ids[None, :]
    weights = init(seed, device)
    opt = torch.optim.AdamW(weights.parameters(), lr=0.003, weight_decay=0.01, foreach=False)
    start = time.perf_counter()
    loss0 = None
    for _ in range(60):
        opt.zero_grad(set_to_none=True)
        err = (native(x, d, weights, cross, mode) - y) / 0.1
        loss = (torch.sqrt(1 + err.square()) - 1).mean() * 0.01
        if loss0 is None:
            loss0 = float(loss.detach())
        loss.backward()
        opt.step()
    with torch.no_grad():
        last = native(x, d, weights, cross, mode).cpu().numpy()
    saved = dictionary(weights)
    difference = np.max(np.abs(last - corrections(features, saved, mode, donors)))
    if difference > 1e-9 or not np.isfinite(difference):
        raise RuntimeError(f"Native/portable disagreement: {difference}")
    return saved, {"initial_loss": loss0, "loss_before_final_update": float(loss.detach()),
                   "max_native_numpy_normalized": float(difference), "fit_seconds": time.perf_counter() - start}


def partition(x, y, positions, matched=True):
    _, _, _, _, valid = geometry(x[positions])
    good = valid.all(axis=1)
    target_ok = np.isfinite(y[positions]).all(axis=(1, 2, 3))
    donor = earlier_donors(good)
    use = good & target_ok
    if matched:
        use &= donor >= 0
    # A placeholder for donorless rows in the all-eligible fit is never passed to donor-conditioned models.
    return positions[use], positions[np.maximum(donor[use], 0)]


def prior_fit(x, y):
    _, scale, wrist, _, _ = geometry(x)
    change_px = y - wrist[:, None]
    target = change_px / scale[:, None, :, None]
    design = ridge_design(x) / scale[:, :, None]
    ridge = np.empty((2, 2, 18, 2))
    bias = np.empty((2, 2, 2))
    for i, h in enumerate(HORIZONS):
        for s in range(2):
            a = h * design[:, s]
            b = target[:, i, s]
            ac = a - a.mean(axis=0)
            ridge[i, s] = np.linalg.solve(ac.T @ ac + np.eye(18), ac.T @ (b - b.mean(axis=0)))
            bias[i, s] = b.mean(axis=0) - a.mean(axis=0) @ ridge[i, s]
    return {"mean": target.mean(axis=0), "mean_px": change_px.mean(axis=0), "ridge": ridge, "ridge_bias": bias}, target


def fit_partition(x, y, use, donor, modes, device, label, storage, fits):
    prior, target = prior_fit(x[use], y[use])
    storage.update({f"{label}.prior.{k}": v for k, v in prior.items()})
    f = geometry(x[use])[0]
    d = geometry(x[donor])[0]
    for mode in modes:
        for seed in SEEDS:
            w, info = fit_model(f, d, target, prior, mode, seed, device)
            fits[f"{label}.{mode}.{seed}"] = info
            storage.update({f"{label}.{mode}.{seed}.{k}": v for k, v in w.items()})
