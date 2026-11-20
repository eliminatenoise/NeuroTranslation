"""Training implementation of the shared time encoder."""
import json
import numpy as np
import torch
from torch import nn

from predict import DOMAINS

MODEL = dict(format=1, width=24, heads=4, feedforward=48, layers=1, domains=list(DOMAINS))


class Block(nn.Module):
    def __init__(self, width, heads, feedforward):
        super().__init__()
        self.heads = heads
        self.attention_norm = nn.LayerNorm(width)
        self.qkv = nn.Linear(width, 3*width)
        self.attention_out = nn.Linear(width, width)
        self.ff_norm = nn.LayerNorm(width)
        self.ff_in = nn.Linear(width, feedforward)
        self.ff_out = nn.Linear(feedforward, width)

    def forward(self, z):
        n, tokens, width = z.shape
        size = width // self.heads
        q, k, v = self.qkv(self.attention_norm(z)).reshape(
            n, tokens, 3, self.heads, size).permute(2, 0, 3, 1, 4).unbind(0)
        weights = torch.softmax((q @ k.transpose(-2, -1)) / size**.5, dim=-1)
        mix = (weights @ v).transpose(1, 2).reshape(n, tokens, width)
        z = z + self.attention_out(mix)
        return z + self.ff_out(torch.relu(self.ff_in(self.ff_norm(z))))


class SharedMotion(nn.Module):
    def __init__(self, config=MODEL):
        super().__init__()
        self.config = dict(config)
        width = config['width']
        if width % config['heads']:
            raise ValueError("Head count must divide width")
        self.project = nn.Linear(6, width)
        self.position = nn.Parameter(torch.empty(4, width))
        nn.init.normal_(self.position, std=.02)
        self.blocks = nn.ModuleList([Block(width, config['heads'], config['feedforward'])
                                     for _ in range(config['layers'])])
        self.last_norm = nn.LayerNorm(width)
        self.readout = nn.Linear(width, len(DOMAINS))
        nn.init.zeros_(self.readout.weight)
        nn.init.zeros_(self.readout.bias)

    def forward(self, x, recent_log, domain):
        z = self.project(x) + self.position
        for block in self.blocks:
            z = block(z)
        out = self.readout(self.last_norm(z[:, -1]))
        return recent_log + out.gather(1, domain[:, None]).squeeze(1)

    def save(self, path):
        values = {key:value.detach().cpu().numpy() for key,value in self.state_dict().items()}
        np.savez_compressed(path, configuration=np.array(json.dumps(self.config)), **values)

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as d:
            model = cls(json.loads(str(d["configuration"])))
            model.load_state_dict({key:torch.from_numpy(d[key]) for key in d.files
                                   if key != "configuration" and not key.startswith("angular.")})
        return model
