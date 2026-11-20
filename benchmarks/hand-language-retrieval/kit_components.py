"""Components reused from the CC0 KIT recording retrieval study."""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import time
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


def words(caption):
    return re.findall(r"[a-z]+(?:'[a-z]+)?|[0-9]+", caption.lower())


@dataclass
class Clip:
    key: str
    group: str
    action: str | None
    captions: list[str]
    sequence: np.ndarray


class TextMap:
    def __init__(self, vocab, idf, length):
        self.vocab = vocab
        self.idf = np.asarray(idf, dtype=np.float32)
        self.length = length

    @classmethod
    def fit(cls, clips, policy):
        frequency = Counter()
        for c in clips:
            frequency.update(set(w for text in c.captions for w in words(text)))
        terms = sorted(frequency, key=lambda w: (-frequency[w], w))[:policy["vocabulary_cap"]]
        vocab = {w: i + 2 for i, w in enumerate(terms)}
        idf = [0, 0] + [np.log((1 + len(clips)) / (1 + frequency[w])) + 1 for w in terms]
        return cls(vocab, idf, policy["text_tokens"])

    def encode(self, captions):
        ids = np.zeros((len(captions), self.length), dtype=np.int64)
        counts = np.zeros((len(captions), len(self.idf)), dtype=np.float32)
        for j, text in enumerate(captions):
            encoded = [self.vocab.get(w, 1) for w in words(text)[:self.length]] or [1]
            ids[j, :len(encoded)] = encoded
            counts[j] = np.bincount(encoded, minlength=len(self.idf)) * self.idf
        return torch.from_numpy(ids), F.normalize(torch.from_numpy(counts))


class Encoder(nn.Module):
    def __init__(self, width, heads, length):
        super().__init__()
        self.positions = nn.Parameter(torch.randn(length, width) * 0.02)
        self.block = nn.TransformerEncoderLayer(width, heads, 2 * width, dropout=0,
                                                activation="gelu", batch_first=True, norm_first=True)
        self.norm = nn.LayerNorm(width)
        self.projection = nn.Linear(width, width)

    def forward(self, x, padding=None):
        h = self.block(x + self.positions[:x.shape[1]], src_key_padding_mask=padding)
        if padding is None:
            pooled = h.mean(1)
        else:
            weight = (~padding).unsqueeze(-1)
            pooled = (h * weight).sum(1) / weight.sum(1).clamp_min(1)
        return F.normalize(self.projection(self.norm(pooled)))


class Retrieval(nn.Module):
    def __init__(self, vocab_size, channels, p):
        super().__init__()
        dim = p["width"]
        self.word = nn.Embedding(vocab_size, dim, padding_idx=0)
        self.frame = nn.Linear(channels, dim)
        self.text = Encoder(dim, p["heads"], p["text_tokens"])
        self.motion = Encoder(dim, p["heads"], p["motion_steps"])

    def from_words(self, ids):
        return self.text(self.word(ids), ids == 0)

    def from_motion(self, x):
        return self.motion(self.frame(x))


def descriptors(x):
    return torch.cat([x.mean(1), x.std(1, unbiased=False), (x[:, 1:] - x[:, :-1]).abs().mean(1),
                      x[:, -1] - x[:, 0]], dim=1)


def cyclic_derangement(n, seed):
    if n < 2:
        raise ValueError("A wrong-pair comparison needs two recordings")
    order = np.random.default_rng(seed).permutation(n)
    mapping = np.empty(n, dtype=np.int64)
    mapping[order] = np.roll(order, -1)
    return mapping


def tied_scores(scores, targets):
    """Expected metrics under uniform random order within each exact score tie."""
    correct = scores[np.arange(len(scores)), targets][:, None]
    higher = (scores > correct).sum(1)
    equal = (scores == correct).sum(1)
    harmonic = np.r_[0.0, np.cumsum(1 / np.arange(1, scores.shape[1] + 1))]
    return np.stack([np.clip((1 - higher) / equal, 0, 1),
                     np.clip((min(5, scores.shape[1]) - higher) / equal, 0, 1),
                     (harmonic[higher + equal] - harmonic[higher]) / equal], axis=1)


def multi_scores(scores, positives):
    """Recall and first-positive reciprocal rank, averaging uniform permutations of ties."""
    if scores.shape != positives.shape or not positives.any(axis=1).all():
        raise ValueError("Every query must have at least one positive candidate")
    values = []
    for row, good in zip(scores, positives):
        first_score = row[good].max()
        preceding = int((row > first_score).sum())
        tied = row == first_score
        total, matches = int(tied.sum()), int((tied & good).sum())
        probability = matches / total
        result = np.zeros(3)
        for offset in range(1, total-matches+2):
            position = preceding + offset
            result += probability * np.array([position <= 1, position <= 5, 1.0 / position])
            if offset <= total-matches:
                probability *= (total - offset - matches + 1) / (total - offset)
        values.append(result)
    return np.asarray(values)


