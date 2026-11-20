"""Shared temporal model for displacement of two walking landmarks over 100 ms."""
from collections import Counter
import numpy as np
import torch
from torch import nn

OFFSETS = (10, 20, 30, 40)
KINDS = ("cue", "withheld", "permuted")
KEYS = ("person", "condition", "repeat", "offset", "cutoff", "history_mm", "future_delta_mm")


def load_rows(path):
    with np.load(path, allow_pickle=False) as archive:
        d = {name: archive[name] for name in KEYS}
    n = len(d["person"])
    if n == 0 or d["history_mm"].shape != (n, 21, 2, 3) or d["future_delta_mm"].shape != (n, 2, 3):
        raise ValueError("Expected nonempty 21-frame pelvis/heel windows and one XYZ target per landmark")
    for name in KEYS[:5]:
        if d[name].shape != (n,):
            raise ValueError("Expected one value per row in " + name)
    row_keys = list(zip(*(d[k] for k in ("person", "condition", "repeat", "offset"))))
    if len(set(row_keys)) != n:
        raise ValueError("Duplicate person/condition/repeat/offset")
    if not (np.isin(d["condition"], [4, 5]).all() and np.isin(d["repeat"], [1, 2, 3]).all()
            and np.isin(d["offset"], OFFSETS).all() and np.isfinite(d["history_mm"]).all()
            and np.isfinite(d["future_delta_mm"]).all()):
        raise ValueError("Unsupported condition, repeat, offset or nonfinite measurement")
    h = d["history_mm"]
    if not (np.allclose(h[:, -1, 0], 0, atol=1e-4) and np.max(np.abs(h[:, 0, 0, 1])) < 1e-3
            and np.max(h[:, 0, 0, 0]) <= -10 + 1e-4):
        raise ValueError("Unexpected history orientation or origin")
    return d


def subset(d, mask):
    return {k: v[mask] for k, v in d.items()}


def weights(d):
    """Each person, their available conditions, then trials, then windows count equally."""
    ids = list(zip(d["person"], d["condition"], d["repeat"]))
    windows = Counter(ids)
    trials = Counter((p, c) for p, c, _ in windows)
    conditions = Counter(p for p, _ in trials)
    return np.array([1 / (len(conditions) * conditions[p] * trials[p,c] * windows[p,c,r])
                     for p, c, r in ids])


def permuted_conditions(d):
    rng = np.random.default_rng(7081)
    ids = list(zip(d["person"], d["condition"], d["repeat"]))
    keys = sorted(set(ids))
    remap = {}
    for person in sorted(set(d["person"])):
        trials = [key for key in keys if key[0] == person]
        shuffled = rng.permutation([key[1] for key in trials])
        remap.update(zip(trials, shuffled))
    return np.array([remap[key] for key in ids]), {
        "trials": len(keys), "changed_trials": sum(remap[key] != key[1] for key in keys).item()
        if keys else 0}


def history_features(history):
    h = np.asarray(history, dtype=np.float64).reshape(-1, 7, 3, 6)
    return np.concatenate((h[:, :, 2], h[:, :, 1] - h[:, :, 0], h[:, :, 2] - h[:, :, 1]), axis=-1)


def skip(history):
    return np.asarray(history[:, -1] - history[:, 10], dtype=np.float64).reshape(-1, 6)


def normalizer(d):
    x = history_features(d["history_mm"])
    y = d["future_delta_mm"].reshape(-1, 6) - skip(d["history_mm"])
    w = weights(d)
    xm = w @ x.mean(axis=1)
    xs = np.sqrt(w @ ((x - xm) ** 2).mean(axis=1)).clip(min=1)
    ym = w @ y
    ys = np.sqrt(w @ (y - ym) ** 2).clip(min=1)
    return {k: v.tolist() for k, v in (("xm", xm), ("xs", xs), ("ym", ym), ("ys", ys))}


def features(history, offset, codes, norm):
    x = (history_features(history) - norm["xm"]) / norm["xs"]
    phase = (np.asarray(offset) - 25) / 15
    context = np.column_stack((phase, codes))[:, None, :]
    return np.concatenate((x, np.repeat(context, 7, axis=1)), axis=-1)


class Forecast(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(20, 24)
        self.position = nn.Parameter(torch.empty(7, 24))
        nn.init.normal_(self.position, std=.02)
        self.qkv = nn.Linear(24, 72)
        self.attn_out = nn.Linear(24, 24)
        self.norm1 = nn.LayerNorm(24)
        self.hidden = nn.Linear(24, 48)
        self.project = nn.Linear(48, 24)
        self.norm2 = nn.LayerNorm(24)
        self.readout = nn.Linear(24, 6)

    def forward(self, x):
        h = self.embed(x) + self.position
        q, k, v = (a.reshape(len(x), 7, 3, 8).transpose(1, 2)
                   for a in self.qkv(h).chunk(3, dim=-1))
        # Only the final token is read out. Earlier queries cannot affect it in one block.
        attention = (q[:, :, -1:] @ k.transpose(-1, -2) / (8 ** .5)).softmax(dim=-1)
        mixed = (attention @ v).reshape(len(h), 24)
        z = self.norm1(h[:, -1] + self.attn_out(mixed))
        return self.readout(self.norm2(z + self.project(self.hidden(z).tanh())))


def tensor(x, device):
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def codes(conditions):
    return np.asarray(conditions, dtype=np.float64) * 2 - 9


def fitted(d, norm, kind, device="cpu", updates=180):
    torch.manual_seed(7319)
    net = Forecast().to(device)
    shuffled, shuffle_counts = permuted_conditions(d)
    cue = codes(shuffled if kind == "permuted" else d["condition"])
    if kind == "withheld":
        cue = np.zeros(len(cue))
    x = tensor(features(d["history_mm"], d["offset"], cue, norm), device)
    y = tensor((d["future_delta_mm"].reshape(-1, 6) - skip(d["history_mm"]) - norm["ym"]) / norm["ys"], device)
    w = tensor(weights(d), device)
    optim = torch.optim.AdamW(net.parameters(), lr=.003, weight_decay=.01, foreach=False)
    trunk = [p for k, p in net.named_parameters() if not k.startswith("readout.")]
    initial = torch.cat([p.detach().flatten() for p in trunk]).clone()
    proof = {"updates": updates, "parameter_count": sum(p.numel() for p in net.parameters())}
    for step in range(updates):
        optim.zero_grad(set_to_none=True)
        error = (net(x) - y).square().reshape(-1, 2, 3).mean(dim=-1)
        landmark_losses = w @ error
        if step == 0:
            for j, name in enumerate(("pelvis", "heel")):
                grad = torch.autograd.grad(landmark_losses[j], trunk, retain_graph=True)
                proof[name + "_first_trunk_gradient_l2"] = torch.cat([g.flatten() for g in grad]).norm().item()
        loss = landmark_losses.mean()
        loss.backward()
        optim.step()
    final = torch.cat([p.detach().flatten() for p in trunk])
    proof["trunk_change_l2"] = (final - initial).norm().item()
    if kind == "permuted":
        proof["training_label_permutation"] = shuffle_counts
    state = {k: v.detach().cpu().tolist() for k, v in net.state_dict().items()}
    return state, proof


def predict(bundle, history, offset, conditions, kind="cue"):
    norm = bundle["norm"]
    state = bundle["models"]["cue" if kind == "swapped" else kind]
    net = Forecast()
    net.load_state_dict({k: tensor(v, "cpu") for k, v in state.items()})
    cue = codes(conditions)
    if kind == "swapped":
        cue = -cue
    if kind == "withheld":
        cue = np.zeros(len(cue))
    x = features(history, offset, cue, norm)
    with torch.inference_mode():
        result = net(tensor(x, "cpu")).double().numpy() * norm["ys"] + norm["ym"] + skip(history)
    if not np.isfinite(result).all():
        raise ArithmeticError("Nonfinite prediction")
    return result.reshape(-1, 2, 3)


def phase_profile(d):
    def profile(rows):
        table = {}
        for offset in np.unique(rows["offset"]):
            cell = subset(rows, rows["offset"] == offset)
            table[str(offset)] = np.einsum("n,nmc->mc", weights(cell), cell["future_delta_mm"]).tolist()
        return table
    tables = {"pooled": profile(d)}
    for condition in np.unique(d["condition"]):
        tables[str(condition)] = profile(subset(d, d["condition"] == condition))
    return tables


def predictions(bundle, d):
    result = {kind: predict(bundle, d["history_mm"], d["offset"], d["condition"], kind)
              for kind in (*KINDS, "swapped")}
    profile = bundle["cue_phase_profile"]
    typical = []
    for c, o in zip(d["condition"], d["offset"]):
        tab = profile.get(str(c), profile["pooled"])
        nearest = min(map(int, tab), key=lambda v: (abs(v - o), v))
        typical.append(tab[str(nearest)])
    result["cue_phase"] = np.array(typical)
    return result
