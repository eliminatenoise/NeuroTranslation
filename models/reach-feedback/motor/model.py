"""Train one temporal Transformer or weighted ridge from one set of earlier originals."""
import numpy as np
import torch
from torch import nn

from forecast import standardized


class ReachTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(42, 24)
        self.position = nn.Parameter(torch.zeros(20, 24))
        self.qkv = nn.Linear(24, 72)
        self.project = nn.Linear(24, 24)
        self.attention_norm = nn.LayerNorm(24)
        self.expand = nn.Linear(24, 48)
        self.reduce = nn.Linear(48, 24)
        self.final_norm = nn.LayerNorm(24)
        self.out = nn.Linear(24, 80)

    def forward(self, x):
        x = self.embed(x) + self.position
        q, k, v = [a.reshape(-1, 20, 3, 8).transpose(1, 2) for a in self.qkv(x).chunk(3, dim=-1)]
        scores = (q @ k.transpose(-1, -2)) / (8 ** .5)
        attended = (scores.softmax(dim=-1) @ v).transpose(1, 2).reshape(-1, 20, 24)
        x = self.attention_norm(x + self.project(attended))
        x = self.final_norm(x + self.reduce(torch.relu(self.expand(x))))
        return self.out(x[:, -1])


def weights_by_original(original):
    _, inverse, counts = np.unique(original, return_inverse=True, return_counts=True)
    return 1 / (len(counts) * counts[inverse])


def training_scales(raw, movement, w):
    x_mean = w @ raw.mean(1)
    x_std = np.sqrt(w @ np.mean((raw - x_mean) ** 2, axis=1))
    y_mean = np.einsum("n,ntd->td", w, movement)
    y_std = np.sqrt(w @ np.mean((movement - y_mean) ** 2, axis=1))
    return dict(x_mean=x_mean, x_scale=np.where(x_std < 1e-8, 1., x_std),
                y_mean=y_mean, y_scale=np.where(y_std < 1e-8, 1., y_std))


def ridge(x, y, w):
    x = x.reshape(len(y), -1)
    mx, my = w @ x, w @ y
    weighted_x = (x - mx) * np.sqrt(w[:, None])
    weighted_y = (y - my) * np.sqrt(w[:, None])
    if len(w) < x.shape[1]:
        gram = weighted_x @ weighted_x.T + .05 * np.eye(len(w))
        coef = weighted_x.T @ np.linalg.solve(gram, weighted_y)
    else:
        gram = weighted_x.T @ weighted_x + .05 * np.eye(x.shape[1])
        coef = np.linalg.solve(gram, weighted_x.T @ weighted_y)
    return dict(family="ridge", coef=coef, bias=my - mx @ coef)


def fit_transformer(x, y, w, seed, device, step_limit=None):
    torch.manual_seed(seed)
    generator = np.random.default_rng(seed)
    net = ReachTransformer().to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=.0015, weight_decay=.001, foreach=False, fused=False)
    xx, yy, ww = [torch.as_tensor(a, dtype=torch.float32, device=device)
                  for a in (x, y, w * len(w))]
    steps = 0
    for _ in range(24):
        order = generator.permutation(len(x))
        for start in range(0, len(x), 64):
            ids = torch.as_tensor(order[start:start + 64], device=device)
            opt.zero_grad(set_to_none=True)
            err = (net(xx[ids]) - yy[ids]).square().mean(dim=1)
            ((err * ww[ids]).sum() / 64).backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1)
            opt.step()
            steps += 1
            if steps == step_limit:
                break
        if steps == step_limit:
            break
    net.eval()
    params = {k: v.detach().cpu().numpy() for k, v in net.state_dict().items()}
    return net, dict(family="transformer", seed=seed, **params), steps


def native_forecast(net, raw, model, device):
    native = []
    with torch.no_grad():
        for start in range(0, len(raw), 96):
            x = standardized(raw[start:start + 96], model)
            xx = torch.as_tensor(x, dtype=torch.float32, device=device)
            native.append(net(xx).cpu().numpy().reshape(-1, 10, 8))
    return np.concatenate(native)
