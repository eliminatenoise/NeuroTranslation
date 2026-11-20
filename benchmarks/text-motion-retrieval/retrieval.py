"""Fit and score caption-to-recording retrieval on an explicitly partitioned corpus."""
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


def check_rows(rows):
    """Check identifier groups using metadata only. Reserve payloads stay unopened."""
    owners = {}
    seen = set()
    for row in rows:
        key, part = row["key"], row["part"]
        if key in seen or part not in {"train", "assessment", "reserve"}:
            raise ValueError("Duplicate key or unknown partition")
        seen.add(key)
        if not row["recording"] or not row["group"]:
            raise ValueError("Source recording and group required")
        axes = {"recording": [row["recording"]], "group": [row["group"]],
                "family": row.get("families", []), "performer": row.get("performers", [])}
        for axis, ids in axes.items():
            for identity in ids:
                if not identity or owners.setdefault((axis, identity), part) != part:
                    raise ValueError(f"Empty or shared {axis}: {identity}")
    if {r["part"] for r in rows} != {"train", "assessment", "reserve"}:
        raise ValueError("Missing partition")


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


def norm_sequences(clips, center, scale):
    return (torch.tensor(np.stack([c.sequence for c in clips]), dtype=torch.float32) - center) / scale


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


def fit_attention(ids, by_clip, x, vocab_size, p, target):
    torch.manual_seed(p["seed"])
    model = Retrieval(vocab_size, x.shape[-1], p)
    optimizer = torch.optim.AdamW(model.parameters(), lr=p["learning_rate"], weight_decay=p["weight_decay"])
    rng = np.random.default_rng(p["seed"])
    for epoch in range(p["epochs"]):
        order = rng.permutation(len(x))
        batches = list(np.array_split(order, max(1, int(np.ceil(len(order) / p["batch"])))))
        for batch in batches:
            q = [by_clip[i][int(rng.integers(len(by_clip[i])))] for i in batch]
            t = model.from_words(ids[q])
            m = model.from_motion(x[target[batch]])
            logits = t @ m.T / p["temperature"]
            diagonal = torch.arange(len(batch))
            loss = (F.cross_entropy(logits, diagonal) + F.cross_entropy(logits.T, diagonal)) / 2
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
    return model.eval()


def unpack(clips):
    query, owner, by_clip = [], [], []
    for i, c in enumerate(clips):
        if not c.captions or any(not isinstance(s, str) or not words(s) for s in c.captions):
            raise ValueError(f"Missing usable captions for {c.key}")
        by_clip.append(list(range(len(query), len(query) + len(c.captions))))
        query.extend(c.captions)
        owner.extend([i] * len(c.captions))
    return query, np.asarray(owner), by_clip


def fit(clips, p, dest):
    if len(clips) < 3:
        raise ValueError("At least three training recordings required")
    dest.mkdir(exist_ok=False, parents=True)
    all_x = np.stack([c.sequence for c in clips]).astype(np.float64)
    center = torch.tensor(all_x.mean((0, 1)), dtype=torch.float32)
    scale = torch.tensor(all_x.std((0, 1)), dtype=torch.float32)
    scale = torch.where(scale > 1e-6, scale, 1.0)
    x = norm_sequences(clips, center, scale)
    vocab = TextMap.fit(clips, p)
    query, owner, by_clip = unpack(clips)
    ids, bow = vocab.encode(query)
    y = descriptors(x)
    # Each recording has unit total weight regardless of its caption count.
    weight = torch.tensor(1 / np.bincount(owner)[owner], dtype=torch.float64)
    a = torch.cat([bow.double(), torch.ones(len(bow), 1, dtype=torch.float64)], dim=1)
    gram = a.T @ (weight[:, None] * a)
    penalty = torch.full((a.shape[1],), p["ridge_penalty"], dtype=torch.float64)
    penalty[-1] = 0
    coef = torch.linalg.solve(gram + torch.diag(penalty), a.T @ (y[owner].double() * weight[:, None]))
    arrays = {"center": center, "scale": scale, "ridge": coef.float(), "idf": vocab.idf}
    labels = sorted({c.action for c in clips if c.action})
    if labels:
        centroids = []
        for label in labels:
            docs = [bow[by_clip[i]].mean(0) for i,c in enumerate(clips) if c.action == label]
            centroids.append(torch.stack(docs).mean(0))
        arrays["cue_centroids"] = F.normalize(torch.stack(centroids))
    np.savez_compressed(dest / "linear.npz", **{k: np.asarray(v) for k,v in arrays.items()})
    dump({"vocabulary": vocab.vocab, "cue_classes": labels, "channels": int(x.shape[-1]),
          "policy": p, "train": [c.key for c in clips]}, dest / "fit.json")
    for name, target in [("attention", np.arange(len(x))), ("wrong_pair", cyclic_derangement(len(x), p["wrong_seed"]))]:
        model = fit_attention(ids, by_clip, x, len(vocab.idf), p, target)
        # No pickles. The reader reconstructs the public architecture and checks all parameter names.
        np.savez_compressed(dest / (name + ".npz"), **{k:v.detach().numpy() for k,v in model.state_dict().items()})


def tied_scores(scores, targets):
    """Expected metrics under uniform random order within each exact score tie."""
    correct = scores[np.arange(len(scores)), targets][:, None]
    higher = (scores > correct).sum(1)
    equal = (scores == correct).sum(1)
    harmonic = np.r_[0.0, np.cumsum(1 / np.arange(1, scores.shape[1] + 1))]
    return np.stack([np.clip((1 - higher) / equal, 0, 1),
                     np.clip((min(5, scores.shape[1]) - higher) / equal, 0, 1),
                     (harmonic[higher + equal] - harmonic[higher]) / equal], axis=1)


@torch.no_grad()
def matrices(clips, fitted):
    meta = json.loads((fitted / "fit.json").read_text())
    p = meta["policy"]
    with np.load(fitted / "linear.npz", allow_pickle=False) as z:
        linear = {k:torch.from_numpy(z[k].copy()) for k in z.files}
    query, owner, _ = unpack(clips)
    vocab = TextMap(meta["vocabulary"], linear["idf"], p["text_tokens"])
    ids, bow = vocab.encode(query)
    x = norm_sequences(clips, linear["center"], linear["scale"])
    pred = torch.cat([bow, torch.ones(len(bow), 1)], dim=1) @ linear["ridge"]
    result = {"chance": np.zeros((len(owner), len(clips)), dtype=np.float32),
              "ridge": (F.normalize(pred) @ F.normalize(descriptors(x)).T).numpy()}
    for name in ("attention","wrong_pair"):
        model = Retrieval(len(vocab.idf), meta["channels"], p)
        with np.load(fitted / (name + ".npz"), allow_pickle=False) as z:
            model.load_state_dict({k: torch.from_numpy(z[k].copy()) for k in z.files})
        model.eval()
        t = torch.cat([model.from_words(batch) for batch in ids.split(p["batch"])])
        m = torch.cat([model.from_motion(batch) for batch in x.split(p["batch"])])
        result[name] = (t @ m.T).numpy()
    if all(c.action for c in clips):
        cue = np.array([c.action for c in clips])
        result["oracle_action"] = (cue[owner, None] == cue[None,:]).astype(np.float32)
        if meta["cue_classes"]:
            # Candidate cue is privileged metadata. Absent training classes receive a common floor.
            sim = (bow @ linear["cue_centroids"].T).numpy()
            label_index = {label:i for i,label in enumerate(meta["cue_classes"])}
            result["caption_to_action"] = np.stack([sim[:,label_index[k]] if k in label_index
                                                    else np.full(len(bow), -1.0) for k in cue], axis=1)
    if any(not np.isfinite(s).all() for s in result.values()):
        raise ValueError("Nonfinite gallery score")
    return result, owner, {"queries":len(query), "tokens":int((ids != 0).sum()),
                           "unknown":int((ids == 1).sum())}


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


def rows_mean_per_motion(values, owner, size):
    return np.stack([values[owner == i].mean(0) for i in range(size)])


def metric_dict(values):
    return dict(zip(("recall1", "recall5", "mrr"), map(float, values)))


def evaluate(clips, fitted, dest):
    dest.mkdir(parents=True, exist_ok=False)
    matrices_by_method, owner, coverage = matrices(clips, fitted)
    np.savez_compressed(dest / "scores.npz", owners=owner, **matrices_by_method)
    groups = np.array([c.group for c in clips])
    keys = [c.key for c in clips]
    cue = np.array([c.action for c in clips])
    query, _, _ = unpack(clips)
    tokens = [tuple(words(s)) for s in query]
    identical = {k:set() for k in tokens}
    for k,i in zip(tokens,owner):
        identical[k].add(i)
    matching_text = np.zeros((len(query),len(clips)),dtype=bool)
    for q,k in enumerate(tokens):
        matching_text[q,list(identical[k])] = True
    motion_to_captions = np.arange(len(clips))[:,None] == owner[None,:]
    results = {}
    for name, matrix in matrices_by_method.items():
        means = rows_mean_per_motion(tied_scores(matrix, owner), owner, len(clips))
        group_means = {str(g):metric_dict(means[groups == g].mean(0)) for g in np.unique(groups)}
        item = {"motion_macro":metric_dict(means.mean(0)), "group_macro":metric_dict(
            np.stack([means[groups == g].mean(0) for g in np.unique(groups)]).mean(0)),
                "by_group": group_means, "by_motion": dict(zip(keys,map(metric_dict,means)))}
        matched = multi_scores(matrix,matching_text)
        item["identical_description_any_recording"] = metric_dict(
            rows_mean_per_motion(matched,owner,len(clips)).mean(0))
        item["motion_to_any_of_its_captions"] = metric_dict(
            multi_scores(matrix.T,motion_to_captions).mean(0))
        if all(c.action for c in clips):
            # Rank the recording only against the other known examples of the same cue.
            within = []
            class_correct = []
            for i,c in enumerate(clips):
                candidates = np.flatnonzero(cue == c.action)
                row = matrix[owner == i]
                own = np.flatnonzero(candidates == i)[0]
                if len(candidates) > 1:
                    within.append(tied_scores(row[:,candidates], np.full(len(row), own)).mean(0))
                maxima = row == row.max(1, keepdims=True)
                class_correct.append((maxima[:,candidates].sum(1) / maxima.sum(1)).mean())
            item["same_action_top1_motion_macro"] = float(np.mean(class_correct))
            item["within_action_exact"] = metric_dict(np.mean(within,axis=0)) if within else None
        results[name] = item
    dump({"gallery": keys, "groups": groups.tolist(), "actions": cue.tolist(),
          "captions_per_motion": np.bincount(owner).tolist(), "coverage":coverage, "methods":results},
         dest / "results.json")
