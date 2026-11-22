"""Continuous source histories and measured numeric targets on the Inkling text backbone."""

from dataclasses import dataclass
import re

import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class StreamSpec:
    name: str
    channels: int


@dataclass(frozen=True)
class TargetSpec:
    name: str
    size: int
    kind: str


@dataclass(frozen=True)
class History:
    values: torch.Tensor
    observed: torch.Tensor
    acquired_s: torch.Tensor
    available_s: torch.Tensor


@dataclass(frozen=True)
class Measurement:
    values: torch.Tensor
    observed: torch.Tensor
    source_kind: str
    reference_sha256: str | None


def checked_names(specs):
    names = tuple(spec.name for spec in specs)
    if not names or len(set(names)) != len(names) or any(not re.fullmatch('[a-z][a-z_0-9]*', name) for name in names):
        raise ValueError('Use unique simple names for the measured streams and target heads.')
    return names


class StreamAdapter(nn.Module):
    def __init__(self, channels, hidden_size):
        super().__init__()
        if channels <= 0:
            raise ValueError('Each stream requires a positive channel count.')
        self.channels = channels
        self.register_buffer('center', torch.zeros(channels))
        self.register_buffer('scale', torch.ones(channels))
        self.project = nn.Linear(3 * channels, hidden_size)

    @torch.no_grad()
    def set_training_scale(self, center, scale):
        center, scale = center.to(self.center), scale.to(self.scale)
        if (center.shape != self.center.shape or scale.shape != self.scale.shape
                or not torch.isfinite(center).all() or not torch.isfinite(scale).all() or (scale <= 0.).any()):
            raise ValueError('Require finite fitting-only location and positive scale for each channel.')
        self.center.copy_(center)
        self.scale.copy_(scale)

    def forward(self, history, cutoffs):
        shape = cutoffs.shape + (self.channels,)
        values, observed, acquired, available = history.values, history.observed, history.acquired_s, history.available_s
        if (any(field.shape != shape or field.device != cutoffs.device for field in (values, observed, acquired, available))
                or observed.dtype != torch.bool or not all(field.is_floating_point() for field in (values, acquired, available))):
            raise ValueError('Each stream needs values, masks, and the two observed clocks for each channel and bin.')
        if (observed & ~(torch.isfinite(acquired) & torch.isfinite(available) & (available >= acquired))).any():
            raise ValueError('Observed samples require finite acquisition and availability times in source-clock order.')
        cut = cutoffs.unsqueeze(-1)
        usable = observed & (acquired <= cut) & (available <= cut)
        if (usable & ~torch.isfinite(values)).any():
            raise ValueError('An available measurement must be finite.')
        clean = torch.where(usable, values, self.center)
        normalized = ((clean - self.center) / self.scale).to(self.project.weight.dtype)
        sample = torch.where(usable, acquired, cut)
        age = torch.log1p((cut - sample) / .020).to(self.project.weight.dtype)
        if not torch.isfinite(normalized).all() or not torch.isfinite(age).all():
            raise ValueError('The available input does not fit the adapter precision.')
        return self.project(torch.cat((normalized, usable.to(normalized.dtype), age), dim=-1))


class NeuroTranslate(nn.Module):
    """Reuse the causal decoder and its shared-weight loop for non-text histories."""

    def __init__(self, backbone, hidden_size, streams, targets, freeze_backbone=True):
        super().__init__()
        streams, targets = tuple(streams), tuple(targets)
        self.stream_names = checked_names(streams)
        self.target_names = checked_names(targets)
        native_width = getattr(getattr(backbone, 'config', None), 'hidden_size', hidden_size)
        if (hidden_size <= 0 or hidden_size != native_width
                or any(spec.size <= 0 or spec.kind not in ('movement', 'event', 'count') for spec in targets)):
            raise ValueError('Use measured movement, event or count heads with positive dimensions.')
        self.backbone = backbone
        if freeze_backbone:
            self.backbone.requires_grad_(False)
        self.adapters = nn.ModuleDict({spec.name: StreamAdapter(spec.channels, hidden_size) for spec in streams})
        self.time_projection = nn.Linear(1, hidden_size)
        self.query = nn.Parameter(torch.zeros(1, 1, hidden_size))
        self.heads = nn.ModuleDict({spec.name: nn.Linear(hidden_size, spec.size) for spec in targets})
        self.target_kind = {spec.name: spec.kind for spec in targets}

    def forward(self, streams, cutoffs, issue_s):
        """Return signed estimates, event logits and count log-rates in named heads."""
        if (set(streams) != set(self.stream_names) or cutoffs.ndim != 2 or not cutoffs.numel()
                or issue_s.shape != cutoffs.shape[:1] or not cutoffs.is_floating_point() or not issue_s.is_floating_point()
                or cutoffs.device != issue_s.device or not torch.isfinite(cutoffs).all() or not torch.isfinite(issue_s).all()
                or (cutoffs > issue_s[:, None]).any() or (cutoffs[:, 1:] <= cutoffs[:, :-1]).any()):
            raise ValueError('Supply only configured streams and strictly ordered forecast bins ending by issue.')
        blocks = sum(self.adapters[name](streams[name], cutoffs) for name in self.stream_names)
        relative = torch.log1p((issue_s[:, None] - cutoffs) / .020).to(self.time_projection.weight.dtype)
        blocks = blocks + self.time_projection(relative.unsqueeze(-1))
        tokens = torch.cat((blocks, self.query.expand(len(blocks), -1, -1)), dim=1)
        decoder = self.backbone(inputs_embeds=tokens, attention_mask=torch.ones(tokens.shape[:2], dtype=torch.long, device=tokens.device),
                                use_cache=False, return_dict=True)
        summary = decoder.last_hidden_state[:, -1, :]
        return {name: self.heads[name](summary) for name in self.target_names}

    def natural_outputs(self, forecasts):
        """Convert event logits to probabilities and count log-rates to expected counts."""
        if set(forecasts) != set(self.target_names):
            raise ValueError('Readouts must match the configured target heads.')
        outputs = {}
        for name, values in forecasts.items():
            kind = self.target_kind[name]
            outputs[name] = values.sigmoid() if kind == 'event' else values.exp() if kind == 'count' else values
            if not torch.isfinite(outputs[name]).all():
                raise ValueError('A decoded forecast is outside its finite numerical range.')
        return outputs

    def measured_loss(self, forecasts, measurements):
        """Only available measured targets contribute, with equal weight per participating head."""
        if set(forecasts) != set(self.target_names) or not set(measurements).issubset(self.target_names):
            raise ValueError('Outcomes may supervise only the configured measurement heads.')
        losses = []
        for name, target in measurements.items():
            output = forecasts[name]
            if (target.values.shape != output.shape or target.observed.shape != output.shape or target.observed.dtype != torch.bool
                    or target.values.device != output.device or target.observed.device != output.device):
                raise ValueError('Forecasts and measured outcomes must match in shape, device and observation mask.')
            if not target.observed.any():
                continue
            if target.source_kind != 'measured' or not re.fullmatch('[0-9a-f]{64}', target.reference_sha256 or ''):
                raise ValueError('Observed numeric outcomes require an exact measured-source reference.')
            y = target.values[target.observed]
            prediction = output[target.observed]
            if not torch.isfinite(y).all():
                raise ValueError('An observed target must be finite.')
            kind = self.target_kind[name]
            if kind == 'event' and not ((y == 0.) | (y == 1.)).all():
                raise ValueError('Measured event labels must be zero or one in the source dtype.')
            if kind == 'count' and ((y < 0.).any() or (y.is_floating_point() and not torch.equal(y, y.round()))):
                raise ValueError('Measured counts must be nonnegative integers in the source dtype.')
            y = y.to(output.dtype)
            if not torch.isfinite(y).all():
                raise ValueError('An observed outcome is outside the model dtype range.')
            if kind == 'movement':
                loss = F.smooth_l1_loss(prediction, y)
            elif kind == 'event':
                loss = F.binary_cross_entropy_with_logits(prediction, y)
            else:
                loss = F.poisson_nll_loss(prediction, y, log_input=True)
            losses.append(loss)
        return torch.stack(losses).mean() if losses else None
