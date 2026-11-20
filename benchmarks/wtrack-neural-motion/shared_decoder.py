"""Unmodified TimeFeatures and ForecastDecoder from the project’s broader_learner.py."""
import torch
from torch import Tensor, nn

class TimeFeatures(nn.Module):
    def __init__(self, width: int, dtype: torch.dtype):
        super().__init__()
        # Seconds remain explicit. This is a trainable time basis, not implicit resampling.
        self.net = nn.Sequential(nn.Linear(3, width, device="cpu", dtype=dtype),
                                 nn.GELU(), nn.Linear(width, width, device="cpu", dtype=dtype))

    def forward(self, relative_seconds: Tensor) -> Tensor:
        return self.net(torch.stack((relative_seconds, torch.sin(relative_seconds),
                                     torch.cos(relative_seconds)), dim=-1))


class ForecastDecoder(nn.Module):
    def __init__(self, width: int, heads: int, hidden: int, dropout: float, dtype: torch.dtype):
        super().__init__()
        self.time = TimeFeatures(width, dtype)
        self.attention = nn.MultiheadAttention(width, heads, dropout=dropout,
                                              batch_first=True, device="cpu", dtype=dtype)
        self.norm1 = nn.LayerNorm(width, device="cpu", dtype=dtype)
        self.ff = nn.Sequential(nn.Linear(width, hidden, device="cpu", dtype=dtype), nn.GELU(),
                                nn.Dropout(dropout), nn.Linear(hidden, width, device="cpu", dtype=dtype))
        self.norm2 = nn.LayerNorm(width, device="cpu", dtype=dtype)

    def forward(self, relative_query: Tensor, context: Tensor, memory: Tensor, valid: Tensor) -> Tensor:
        query = self.time(relative_query) + context[:, None, :]
        attended, _ = self.attention(query, memory, memory, key_padding_mask=~valid,
                                     need_weights=False)
        hidden = self.norm1(query + attended)
        return self.norm2(hidden + self.ff(hidden))


