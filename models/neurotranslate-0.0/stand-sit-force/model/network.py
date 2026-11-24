"""Shared temporal attention with configurable width, heads, depth and feed-forward size."""
import math
import torch
from torch import nn
from torch.nn import functional as F

DEFAULT = dict(width=32, heads=4, depth=1, ff_width=64)


class AttentionBlock(nn.Module):
    def __init__(self, width, heads, ff_width):
        super().__init__()
        self.heads = heads
        self.null = nn.Parameter(torch.zeros(width))
        self.q = nn.Linear(width, width)
        self.k = nn.Linear(width, width)
        self.v = nn.Linear(width, width)
        self.proj = nn.Linear(width, width)
        self.ln1 = nn.LayerNorm(width)
        self.ff1 = nn.Linear(width, ff_width)
        self.ff2 = nn.Linear(ff_width, width)
        self.ln2 = nn.LayerNorm(width)

    def attend(self, x, state):
        n,t,d = x.shape
        h = self.heads
        memory = torch.cat((self.null.expand(n, 1, d), x), dim=1)
        q = self.q(state).reshape(n,h,d//h)
        k = self.k(memory).reshape(n,t+1,h,d//h)
        v = self.v(memory).reshape(n,t+1,h,d//h)
        scores = (q[:,None]*k).sum(dim=-1)/math.sqrt(d//h)
        attended = (scores.softmax(dim=1)[...,None]*v).sum(dim=1).reshape(n,d)
        hidden = self.ln1(state+self.proj(attended))
        return self.ln2(hidden+self.ff2(F.relu(self.ff1(hidden))))


class TemporalAttention(AttentionBlock):
    def __init__(self, width, heads, ff_width, depth):
        if width < 2 or width%2 or heads<1 or width%heads or depth<1 or ff_width<1:
            raise ValueError('Use an even width divisible by the positive head count and positive depth and feed-forward size')
        super().__init__(width,heads,ff_width)
        self.extra = nn.ModuleList([AttentionBlock(width,heads,ff_width) for _ in range(depth-1)])

    def forward(self, x):
        _,t,d = x.shape
        omega = torch.exp(torch.arange(0,d,2,device=x.device)*(-math.log(10000.)/d))
        phase = torch.arange(1-t,1,device=x.device)[:,None]*omega
        x = x+torch.stack((phase.sin(),phase.cos()),dim=-1).reshape(t,d)
        state = self.attend(x,x[:,-1])
        for block in self.extra:
            state = block.attend(x,state)
        return state


class Joint(nn.Module):
    def __init__(self, schemas, architecture=None):
        super().__init__()
        self.architecture = DEFAULT | (architecture or {})
        self.trunk = TemporalAttention(**self.architecture)
        width = self.architecture['width']
        self.adapters = nn.ModuleDict()
        self.outputs = nn.ModuleDict()
        for task, schema in schemas.items():
            self.adapters[task] = nn.Linear(2*len(schema['channels']),width)
            self.outputs[task] = nn.Linear(width,len(schema['outputs']))

    def forward(self, task, x, valid=None):
        ranking = x.ndim==4
        shape = x.shape
        x = x.reshape(-1,*shape[-2:])
        output = self.outputs[task](self.trunk(self.adapters[task](x)))
        if ranking:
            return output.reshape(shape[:2]).masked_fill(~valid,-torch.inf)
        return output
