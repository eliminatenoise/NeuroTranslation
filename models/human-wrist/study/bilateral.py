"""Bilateral wrist forecasting from earlier camera and voltage measurements."""

import numpy as np
from attention import SEEDS, initial, native_forward, np_forward, MASK, STEPS, LR, DECAY

SIDES = ("right", "left")
MODALITIES = ("full", "pose")
TREATMENTS = ("direct", "bounded_zero", "anchored")
HORIZONS = np.array([8, 15], dtype=np.float64)
CONTACTS = np.array([0, 9, 18, 27, 36, 45, 54, 63])
PARAMS = tuple(initial(17))


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


def donors(data):
    """Return a strictly earlier input-only electrical donor in another source block."""
    electrical, _ = eligibility(data)
    result = np.full(len(electrical), -1, dtype=int)
    previous = -1
    for i, block in enumerate(data["source_block"]):
        if previous >= 0 and data["source_block"][previous] < block:
            result[i] = previous
        if electrical[i]:
            previous = i
    return result


def side_features(voltage, arm):
    voltage = np.asarray(voltage, dtype=np.float64)
    arm = np.asarray(arm, dtype=np.float64)
    n = len(arm)
    last = arm[:, 2::3]
    relative = (last[:, :, :2] - last[:, :, 2:3]).reshape(n, 5, 4)
    delta = (last - arm[:, :1]).reshape(n, 5, 6)
    group = voltage.reshape(n, 5, 50, 8)
    log_rms = np.log(np.maximum(np.sqrt(np.mean(group**2, axis=2)), 1e-6))
    raw = np.concatenate((relative, delta, group.mean(axis=2), log_rms), axis=2)
    anchor = arm[:, -1, 0, :]
    velocity = (anchor - arm[:, 0, 0, :])[:, None, :] * HORIZONS[None, :, None] / 14.0
    return raw, anchor, velocity


def methods(scope):
    prefix = "" if scope == "main" else scope + "_"
    for name in ("zero", "velocity", "half_velocity", "mean", "fitted_velocity"):
        yield prefix + name
    for treatment in TREATMENTS:
        for modality in MODALITIES:
            stem = f"{treatment}_{modality}"
            base = ["ridge_" + stem] + [f"transformer_{stem}_s{s}" for s in SEEDS]
            for model in base:
                yield prefix + model
                if modality == "full":
                    yield prefix + model + "_wrong"


def raw_transform(raw, treatment, mean, scale, prior):
    """Map final network activations to displacement in camera pixels."""
    out = raw.reshape(-1, 2, 2)
    if treatment == "direct":
        return out * scale + mean
    return prior + 0.25 * scale * np.tanh(out)


def infer_arm(voltage, arm, w, native_device=None):
    """Infer every non-counterfactual method. Inputs must already have passed eligibility."""
    raw, anchor, vel = side_features(voltage, arm)
    x = (raw - w["feature_mean"]) / w["feature_scale"]
    fitted = vel * w["damping"][None, :, None]
    zero = np.zeros_like(vel)
    displacement = dict(
        zero=zero,
        velocity=vel,
        half_velocity=0.5 * vel,
        mean=np.broadcast_to(w["mean"], vel.shape),
        fitted_velocity=fitted,
    )
    for modality in MODALITIES:
        token = x.copy()
        if modality == "pose":
            token[:, :, 10:] = 0
        flat = token.reshape(len(token), -1)
        for treatment in TREATMENTS:
            stem = f"{treatment}_{modality}"
            prior = fitted if treatment == "anchored" else zero
            name = "ridge_" + stem
            correction = np.stack(
                [
                    (flat - w[name + "__center"][h]) @ w[name + "__coef"][h] + w[name + "__bias"][h]
                    for h in range(2)
                ],
                axis=1,
            )
            if treatment == "direct":
                displacement[name] = correction * w["scale"] + w["mean"]
            else:
                displacement[name] = prior + 0.25 * w["scale"] * np.tanh(correction / 0.25)
            for seed in SEEDS:
                name = f"transformer_{stem}_s{seed}"
                parameters = {k: w[name + "__" + k] for k in PARAMS}
                if native_device is None:
                    output = np_forward(token, parameters)
                else:
                    import torch

                    with torch.no_grad():
                        p = {
                            k: torch.tensor(v, device=native_device) for k, v in parameters.items()
                        }
                        xt = torch.tensor(token, device=native_device)
                        mt = torch.tensor(MASK, device=native_device)
                        output = native_forward(xt, p, mt).cpu().numpy()
                displacement[name] = raw_transform(output, treatment, w["mean"], w["scale"], prior)
    return {key: value + anchor[:, None] for key, value in displacement.items()}


def arm_weights(weights, scope, side):
    prefix = scope + "__" + side + "__"
    return {k.removeprefix(prefix): v for k, v in weights.items() if k.startswith(prefix)}


def forecast(data, weights, native_device=None, selected=None):
    """All rows preserve the input's local native order. Partial-arm missingness is retained."""
    electrical, pose = eligibility(data)
    donor = donors(data)
    n = len(donor)
    chosen = np.ones(n, bool) if selected is None else np.isin(np.arange(n), selected)
    output = {}
    for scope in ("main", "small16"):
        prefix = "" if scope == "main" else scope + "_"
        for name in methods(scope):
            output[name] = np.full((n, 2, 2, 2), np.nan)
        for side_idx, side in enumerate(SIDES):
            if scope == "small16" and side == "left":
                continue
            arm = data["prior_pose_px"][:, :, 3 * side_idx : 3 * side_idx + 3, :]
            w = arm_weights(weights, scope, side)
            for wrong in (False, True):
                ok = chosen & electrical & pose[:, side_idx]
                if wrong:
                    ok &= donor >= 0
                recipient = np.flatnonzero(ok)
                if not len(recipient):
                    continue
                voltage = data["ecog_uv"][donor[recipient] if wrong else recipient]
                predictions = infer_arm(voltage, arm[recipient], w, native_device=native_device)
                for method, value in predictions.items():
                    if wrong and "_full" not in method:
                        continue
                    name = prefix + method + ("_wrong" if wrong else "")
                    output[name][recipient, :, side_idx, :] = value
    donor_ok = donor >= 0
    return output, {
        "native_event_row": data["native_event_row"],
        "onset_s": data["onset_s"],
        "source_block": data["source_block"],
        "ecog_qc": electrical,
        "pose_qc": pose,
        "input_qc": electrical[:, None] & pose,
        "donor_index": donor,
        "donor_native_event_row": np.where(donor_ok, data["native_event_row"][donor], -1),
        "donor_source_block": np.where(donor_ok, data["source_block"][donor], -1),
    }


def head_data(data, future, allowed, side_i):
    eok, pok = eligibility(data)
    target_ok = np.isfinite(future[:, :, side_i, :]).all(axis=2)
    keep = allowed & eok & pok[:, side_i] & target_ok.any(axis=1)
    ids = np.flatnonzero(keep)
    arm = data["prior_pose_px"][ids, :, 3 * side_i : 3 * side_i + 3, :]
    raw, anchor, velocity = side_features(data["ecog_uv"][ids], arm)
    y = future[ids, :, side_i, :] - anchor[:, None]
    mask = target_ok[ids]
    stats = {"feature_mean": raw.mean(axis=(0, 1)), "feature_scale": raw.std(axis=(0, 1))}
    stats["feature_scale"][stats["feature_scale"] < 1e-8] = 1.0
    mean, scale, damping = [], [], []
    for h in range(2):
        valid = mask[:, h]
        if valid.sum() < 2:
            raise ValueError("Fewer than two fitting rows for a horizon")
        target = y[valid, h]
        v = velocity[valid, h]
        v2 = np.sum(v * v, axis=1)
        regularizer = 16 * max(float(np.median(v2)), 1.0)
        damping.append(
            np.clip(((v * target).sum() + regularizer * 0.5) / (v2.sum() + regularizer), 0, 1)
        )
        mean.append(target.mean(axis=0))
        scale.append(np.maximum(target.std(axis=0), 1.0))
    stats.update(mean=np.array(mean), scale=np.array(scale), damping=np.array(damping))
    return (raw - stats["feature_mean"]) / stats["feature_scale"], y, velocity, mask, ids, stats


def targets(y, vel, mask, stats, treatment):
    prior = vel * stats["damping"][None, :, None] if treatment == "anchored" else np.zeros_like(vel)
    center = stats["mean"] if treatment == "direct" else 0.0
    target = (y - prior - center) / stats["scale"]
    # Invalid entries take zero weight. A finite placeholder avoids NaN gradients under masking.
    return np.where(mask[:, :, None], target, 0.0)


def fit_net(x, target, mask, seed, treatment, device):
    import torch

    p = {k: torch.nn.Parameter(torch.tensor(v, device=device)) for k, v in initial(seed).items()}
    opt = torch.optim.AdamW(
        p.values(),
        lr=LR,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=DECAY,
        foreach=False,
        fused=False,
    )
    xt = torch.tensor(x, device=device)
    yt = torch.tensor(target, device=device)
    keep = torch.tensor(np.broadcast_to(mask[:, :, None], target.shape).copy(), device=device)
    causal = torch.tensor(MASK, device=device)

    def loss():
        raw = native_forward(xt, p, causal).reshape(-1, 2, 2)
        if treatment == "direct":
            return ((raw[keep] - yt[keep]) ** 2).mean()
        adjusted = 0.25 * torch.tanh(raw)
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
    return (
        {k: v.detach().cpu().numpy().copy() for k, v in p.items()},
        torch.stack(trajectory).cpu().numpy(),
        native_raw,
    )


def ridge(x, target, mask, direct):
    flat = x.reshape(len(x), -1)
    stats = {k: [] for k in ("center", "bias", "coef")}
    for h in range(2):
        z, y = flat[mask[:, h]], target[mask[:, h], h]
        zm = z.mean(axis=0)
        zc = z - zm
        mean = y.mean(axis=0)
        factor = 1.0 if direct else 0.5
        dual = np.linalg.solve(zc @ zc.T + len(z) * factor * np.eye(len(z)), (y - mean) * factor)
        for key, value in (("center", zm), ("bias", mean * factor), ("coef", zc.T @ dual)):
            stats[key].append(value)
    return {k: np.stack(v) for k, v in stats.items()}
