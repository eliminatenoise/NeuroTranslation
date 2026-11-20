"""One causal-cutoff temporal attention encoder, exposed to both task gradients."""
import numpy as np
import torch
from torch import nn
from records import inputs, weights

SEED = 8347
EPOCHS = (12, 36, 90)


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(22, 16)
        self.position = nn.Parameter(torch.empty(4, 16))
        nn.init.normal_(self.position, std=.02)
        self.qkv = nn.Linear(16, 48)
        self.attn_out = nn.Linear(16, 16)
        self.norm1 = nn.LayerNorm(16)
        self.hidden = nn.Linear(16, 32)
        self.project = nn.Linear(32, 16)
        self.norm2 = nn.LayerNorm(16)
        self.heel = nn.Linear(16, 3)
        self.force = nn.Linear(16, 1)

    def encode(self, x):
        h = self.embed(x) + self.position
        q, k, v = (a.reshape(len(x), 4, 2, 8).transpose(1, 2)
                   for a in self.qkv(h).chunk(3, dim=-1))
        att = ((q @ k.transpose(-1, -2)) / (8 ** .5)).softmax(dim=-1) @ v
        mixed = self.norm1(h + self.attn_out(att.transpose(1, 2).reshape(len(x), 4, 16)))
        return self.norm2(mixed + self.project(self.hidden(mixed).tanh()))[:, -1]

    def forward(self, x):
        h = self.encode(x)
        return torch.cat([self.heel(h), self.force(h)], dim=1)


def tensor(x, device):
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def initialized(device):
    torch.manual_seed(SEED)
    return Model().to(device)


def train(d, norm, kind, device, epochs=EPOCHS, proof=False):
    model = initialized(device)
    x, y = [tensor(a, device) for a in inputs(d, norm, kind == "marker")]
    w = tensor(weights(d), device)
    opt = torch.optim.AdamW(model.parameters(), lr=.003, weight_decay=.01, foreach=False)
    grad_proof = {}
    trunk = [p for k, p in model.named_parameters() if not k.startswith(("heel.", "force."))]
    initial = torch.cat([p.detach().reshape(-1) for p in trunk]).clone()
    checkpoints = {}
    for step in range(1, max(epochs) + 1):
        opt.zero_grad(set_to_none=True)
        pred = model(x)
        motion = w @ ((pred[:, :3] - y[:, :3]) ** 2).mean(dim=1)
        force = w @ ((pred[:, 3] - y[:, 3]) ** 2)
        loss = motion if kind == "heel" else force if kind == "force" else (motion + force) * .5
        if proof and step == 1:
            def flat_grad(objective):
                gs = torch.autograd.grad(objective, trunk, retain_graph=True)
                return torch.cat([g.reshape(-1) for g in gs])
            gm, gf, gj = [flat_grad(obj) for obj in (motion, force, loss)]
            grad_proof = {"trunk_parameters": len(gm), "heel_gradient_L2": gm.norm().item(),
                          "load_gradient_L2": gf.norm().item(), "joint_gradient_L2": gj.norm().item(),
                          "gradient_sum_residual_L2": (gj - (gm + gf) / 2).norm().item(),
                          "gradient_cosine": (gm @ gf / (gm.norm() * gf.norm())).item()}
        loss.backward()
        opt.step()
        if step in epochs:
            checkpoints[step] = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if proof:
        final = torch.cat([p.detach().reshape(-1) for p in trunk])
        grad_proof["trunk_update_L2"] = (final - initial).norm().item()
    return checkpoints, grad_proof


def encode_initial(x):
    with torch.no_grad():
        return initialized("cpu").encode(tensor(x, "cpu")).numpy().astype(float)


def predict(state, d, norm, kind, device="cpu"):
    model = initialized(device)
    model.load_state_dict(state)
    x, _ = inputs(d, norm, kind == "marker")
    with torch.no_grad():
        pred = model(tensor(x, device)).cpu().numpy().astype(float) * norm["ys"] + norm["ym"]
    if kind == "heel":
        pred[:, 3] = np.nan
    if kind == "force":
        pred[:, :3] = np.nan
    return pred


def encode_state(state, kind):
    return {k: v.tolist() for k, v in state.items()
            if not (kind == "heel" and k.startswith("force.")) and
               not (kind == "force" and k.startswith("heel."))}


def decode_state(pack):
    state = initialized("cpu").state_dict()
    for k, v in pack["state"].items():
        state[k] = tensor(v, "cpu")
    return state
