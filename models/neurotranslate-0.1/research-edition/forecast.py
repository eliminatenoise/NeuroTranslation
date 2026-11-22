"""Connect measured histories and outcomes to the redesigned repeated decoder."""

import torch

from model import NeuroTranslate
from sensor_loop import SensorLoopDecoder


class SensorLoopForecast(NeuroTranslate):
    def __init__(self, native_decoder, streams, targets, *, message_rank, train_native=False):
        native_decoder.requires_grad_(train_native)
        backbone = SensorLoopDecoder(native_decoder, message_rank)
        super().__init__(backbone, native_decoder.config.hidden_size, streams, targets, freeze_backbone=False)

    def forward(self, streams, cutoffs, issue_s, *, passes=None):
        if (set(streams) != set(self.stream_names) or cutoffs.ndim != 2 or not cutoffs.numel()
                or issue_s.shape != cutoffs.shape[:1] or not cutoffs.is_floating_point() or not issue_s.is_floating_point()
                or cutoffs.device != issue_s.device or not torch.isfinite(cutoffs).all() or not torch.isfinite(issue_s).all()
                or (cutoffs > issue_s[:, None]).any() or (cutoffs[:, 1:] <= cutoffs[:, :-1]).any()):
            raise ValueError('Supply configured measurement streams and ordered forecast bins ending by issue.')

        encoded = [self.adapters[name](streams[name], cutoffs) for name in self.stream_names]
        times = cutoffs.unsqueeze(-1)
        availability = [
            (stream.observed & (stream.acquired_s <= times) & (stream.available_s <= times)).any(dim=-1)
            for stream in (streams[name] for name in self.stream_names)
        ]
        evidence = sum(torch.where(available.unsqueeze(-1), values, 0.0)
                       for values, available in zip(encoded, availability, strict=True))
        available = torch.stack(availability).any(dim=0)

        time_to_issue = torch.log1p((issue_s[:, None] - cutoffs) / .020).to(self.time_projection.weight.dtype)
        tokens = sum(encoded) + self.time_projection(time_to_issue.unsqueeze(-1))
        query = self.query.expand(len(tokens), -1, -1)
        result = self.backbone(torch.cat((tokens, query), dim=1),
                               torch.cat((evidence, torch.zeros_like(query)), dim=1),
                               torch.cat((available, available.new_zeros((len(tokens), 1))), dim=1), passes=passes)
        summary = result.last_hidden_state[:, -1]
        forecasts = {name: head(summary.to(head.weight.dtype)) for name, head in self.heads.items()}
        if not all(torch.isfinite(output).all() for output in forecasts.values()):
            raise ValueError('The forecast exceeds the precision of its output layer.')
        return forecasts
