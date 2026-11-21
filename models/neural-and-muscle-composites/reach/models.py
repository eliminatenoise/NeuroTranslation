"""Condition on measured history. Generate future tokens from earlier outputs or noise."""
import math
import torch
from torch import nn

STEPS = 8
WIDTH = 32
HORIZONS = 2


class Forecaster(nn.Module):
    def __init__(self, output, architecture, pose_features=4):
        super().__init__()
        self.architecture = architecture
        self.pose = nn.Linear(pose_features, WIDTH)
        self.spikes = nn.Linear(37, WIDTH)
        self.availability = nn.Linear(2, WIDTH, bias=False)
        self.pose_time = nn.Parameter(torch.randn(4, WIDTH)*0.02)
        self.target_time = nn.Parameter(torch.randn(HORIZONS, WIDTH)*0.02)
        self.project = nn.Linear(output, WIDTH)
        self.readout = nn.Linear(WIDTH, output)
        self.encoder = nn.TransformerEncoderLayer(WIDTH, 4, 64, 0, batch_first=True)
        self.decoder = nn.TransformerDecoderLayer(WIDTH, 4, 64, 0, batch_first=True)
        self.output = output
        f = torch.arange(WIDTH//2) * (math.log(10000) / (WIDTH//2-1))
        angle = torch.arange(STEPS+1)[:, None] * torch.exp(-f)
        self.register_buffer("step_code", torch.cat((angle.sin(), angle.cos()-1), dim=1))
        theta = torch.linspace(0, math.pi/2, STEPS+1)
        co, si = theta.cos(), theta.sin()
        co[-1], si[-1] = 0., 1.
        self.register_buffer("signal",co)
        self.register_buffer("noise",si)
        self.register_buffer("residual_scale",torch.ones(1, HORIZONS, output))

    def encode(self, p, c, mask):
        h = self.pose(p)*mask[:, None, :1] + self.spikes(c)*mask[:, None, 1:]
        return self.encoder(h + self.pose_time + self.availability(mask)[:, None])

    def autoregress(self, memory, previous):
        tokens = self.project(previous) + self.target_time[:previous.shape[1]]
        size = previous.shape[1]
        mask = torch.ones(size, size, device=tokens.device, dtype=torch.bool).triu(1)
        return self.readout(self.decoder(tokens, memory, tgt_mask=mask))

    def denoise(self, memory, value, step, prefix=None, index=None):
        if index is None:
            pos = self.target_time
        else:
            pos = self.target_time[index][:, None]
        query = self.project(value) + pos + self.step_code[step][:, None]
        if prefix is None:
            return self.readout(self.decoder(query, memory))
        # A fixed-size decoder memory supports a mixture of first/second-horizon
        # examples; first-horizon observations cannot see the clean prefix slot.
        prefix_slot = self.project(prefix) + self.target_time[:1]
        attention_memory = torch.cat([memory, prefix_slot], dim=1)
        mask = torch.zeros(attention_memory.shape[:2], device=query.device, dtype=torch.bool)
        mask[:, -1] = index == 0
        return self.readout(self.decoder(query, attention_memory, memory_key_padding_mask=mask))

    def error(self, memory, y, steps, eps, index):
        if self.architecture == "ar":
            shifted = torch.cat((torch.zeros_like(y[:, :1]), y[:, :-1]), dim=1)
            return (self.autoregress(memory, shifted) - y).square().mean()
        prefix = None
        if self.architecture == "hybrid":
            prefix = y[:, :1]
            selector = torch.arange(len(y), device=y.device)
            y = y[selector, index][:, None]
            eps = eps[selector, index][:, None]
        else:
            index = None
        signal = self.signal[steps][:, None, None]
        noise = self.noise[steps][:, None, None]
        noisy = signal*y + noise*eps
        velocity = signal*eps - noise*y
        return (self.denoise(memory, noisy, steps, prefix, index) - velocity).square().mean()

    def reverse(self, memory, x, prefix=None, index=None):
        for t in range(STEPS, 0, -1):
            step = torch.full((len(x),), t, dtype=torch.long, device=x.device)
            v = self.denoise(memory, x, step, prefix, index)
            clean = self.signal[t]*x - self.noise[t]*v
            eps = self.noise[t]*x + self.signal[t]*v
            x = self.signal[t-1]*clean + self.noise[t-1]*eps
        return x

    def generate(self, memory, z):
        if self.architecture == "ar":
            first = torch.zeros_like(z[:, :1])
            drawn = self.autoregress(memory, first) + self.residual_scale[:, :1]*z[:, :1]
            conditional = self.autoregress(memory, torch.cat((first, drawn), dim=1))[:, 1:]
            return torch.cat((drawn, conditional+self.residual_scale[:, 1:]*z[:, 1:]), dim=1)
        if self.architecture == "diffusion":
            return self.reverse(memory, z)
        index = torch.zeros(len(z), device=z.device, dtype=torch.long)
        first = self.reverse(memory, z[:, :1], torch.zeros_like(z[:, :1]), index)
        second = self.reverse(memory, z[:, 1:], first, index+1)
        return torch.cat((first, second), dim=1)
