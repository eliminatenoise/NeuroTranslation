"""Join observed force and marker displacement for a floor-impulse forecast."""

import torch
from torch import nn


class ForceMotionForecast(nn.Module):
    def __init__(self, temporal_attention, config, marker_count):
        super().__init__()
        width = config["width"]
        self.marker_count = marker_count
        self.force = nn.Linear(2, width)
        self.motion = nn.Linear(4 * marker_count, width)
        self.gate = nn.Linear(2 * width, width)
        self.temporal = temporal_attention(**config)
        self.output = nn.Linear(width, 2)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, force_n, motion):
        load = self.force(force_n)
        movement = self.motion(motion)
        available = motion[..., -self.marker_count:].any(dim=-1, keepdim=True)
        contribution = self.gate(torch.cat((load, movement), dim=-1)).sigmoid() * movement
        merged = load + available * contribution
        return self.output(self.temporal(merged))
