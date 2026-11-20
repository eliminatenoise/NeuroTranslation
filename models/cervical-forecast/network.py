"""Trainable single-block self-attention model for the frozen causal tokens."""
import math
import torch
from torch import nn
from torch.nn import functional as F

UPDATES = 100
SEED = 1701


class CervicalTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(6, 16)
        self.position = nn.Parameter(torch.empty(16, 16))
        nn.init.normal_(self.position, std=0.02)
        self.norm1 = nn.LayerNorm(16)
        self.qkv = nn.Linear(16, 48)
        self.mix = nn.Linear(16, 16)
        self.norm2 = nn.LayerNorm(16)
        self.ff1 = nn.Linear(16, 32)
        self.ff2 = nn.Linear(32, 16)
        self.outnorm = nn.LayerNorm(16)
        self.readout = nn.Linear(16, 1)

    def forward(self, x):
        x = self.embed(x) + self.position
        qkv = self.qkv(self.norm1(x)).chunk(3, dim=-1)
        q, k, v = [a.reshape(x.shape[0], 16, 2, 8).transpose(1, 2) for a in qkv]
        weights = torch.softmax((q @ k.transpose(-2, -1)) / math.sqrt(8), dim=-1)
        context = (weights @ v).transpose(1, 2).reshape(x.shape[0], 16, 16)
        x = x + self.mix(context)
        x = x + self.ff2(F.gelu(self.ff1(self.norm2(x)), approximate="none"))
        return self.readout(self.outnorm(x).mean(dim=1)).squeeze(-1)


def train(x, y, updates=UPDATES, device="cpu"):
    torch.manual_seed(SEED)
    model = CervicalTransformer().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.01, foreach=False)
    x = torch.as_tensor(x, dtype=torch.float32, device=device)
    y = torch.as_tensor(y, dtype=torch.float32, device=device)
    for _ in range(updates):
        optimizer.zero_grad(set_to_none=True)
        error = model(x) - y
        error.square().mean().backward()
        optimizer.step()
    return model.cpu().eval()
