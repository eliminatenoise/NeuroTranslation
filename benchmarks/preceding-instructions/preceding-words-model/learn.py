"""Fixed regularized forecasts and an optional small attention residual."""

from collections import Counter

import numpy as np

RIDGE = 0.025
STRUCTURES = {
    "context": ["context", "task"],
    "context_words": ["context", "task", "words"],
    "motion": ["motion"],
    "motion_context": ["motion", "context", "task"],
    "motion_context_words": ["motion", "context", "task", "words"],
}


def balanced_weights(rows):
    recordings = Counter(r["record"] for r in rows)
    groups = {r["group"] for r in rows}
    per_group = {g: len({r["record"] for r in rows if r["group"] == g}) for g in groups}
    return np.array(
        [
            1 / (len(groups) * per_group[r["group"]] * recordings[r["record"]])
            for r in rows
        ]
    )


def make_spec(rows):
    word_counts = Counter(w for r in rows for w in r["tokens"])
    spec = {
        "vocabulary": sorted(w for w, n in word_counts.items() if n >= 3),
        "tasks": sorted({r["task"] for r in rows}),
    }
    for field in ["context", "motion"]:
        matrix = np.stack([r[field] for r in rows])
        spec[field + "_mean"] = matrix.mean(0).tolist()
        scale = matrix.std(0)
        spec[field + "_scale"] = np.where(scale > 1e-8, scale, 1.0).tolist()
    return spec


def inputs(rows, spec):
    components = {}
    for field in ["context", "motion"]:
        matrix = np.stack([r[field] for r in rows])
        components[field] = (matrix - spec[field + "_mean"]) / spec[field + "_scale"]
    components["task"] = np.array(
        [[r["task"] == t for t in spec["tasks"]] for r in rows], dtype=float
    )
    components["words"] = np.array(
        [[w in r["tokens"] for w in spec["vocabulary"]] for r in rows], dtype=float
    )
    return components


def design(components, model):
    return np.concatenate([components[field] for field in STRUCTURES[model]], axis=1)


def fit_ridge(x, y, weights):
    xm = weights @ x
    ym = float(weights @ y)
    centered = x - xm
    lhs = centered.T @ (weights[:, None] * centered) + RIDGE * np.eye(x.shape[1])
    slope = np.linalg.solve(lhs, centered.T @ (weights * (y - ym)))
    return np.r_[ym - xm @ slope, slope]


def raw_predict(coefficients, matrix):
    return coefficients[0] + matrix @ coefficients[1:]


def fit_attention(x, words, y, base, weights, width=8, epochs=80, seed=17):
    import torch
    from torch import nn

    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    scale = max(float(y.std()), 1e-8)
    tx = torch.as_tensor(x, dtype=torch.float32)
    mask = torch.as_tensor(np.c_[np.ones(len(x)), words], dtype=torch.bool)
    truth = torch.as_tensor((y - base) / scale, dtype=torch.float32)
    wt = torch.as_tensor(weights, dtype=torch.float32)
    query = nn.Linear(x.shape[1], width)
    keys = nn.Parameter(torch.randn(words.shape[1] + 1, width) * 0.1)
    values = nn.Parameter(torch.zeros(words.shape[1] + 1))
    optimizer = torch.optim.AdamW(
        [*query.parameters(), keys, values], lr=0.01, weight_decay=0.01
    )
    for _ in range(epochs):
        logits = (query(tx) @ keys.T) / np.sqrt(width)
        attention = torch.softmax(logits.masked_fill(~mask, float("-inf")), dim=1)
        loss = torch.sum(wt * torch.square(attention @ values - truth))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return {
        "attention_query": query.weight.detach().numpy(),
        "attention_bias": query.bias.detach().numpy(),
        "attention_keys": keys.detach().numpy(),
        "attention_values": values.detach().numpy(),
        "attention_scale": np.array(scale),
    }


def attention_predict(weights, x, words, base):
    query = x @ weights["attention_query"].T + weights["attention_bias"]
    logits = (query @ weights["attention_keys"].T) / np.sqrt(query.shape[1])
    mask = np.c_[np.ones(len(x)), words].astype(bool)
    logits = np.where(mask, logits, -np.inf)
    probs = np.exp(logits - np.max(logits, axis=1, keepdims=True))
    probs /= probs.sum(axis=1, keepdims=True)
    return np.maximum(
        0.0, base + weights["attention_scale"] * (probs @ weights["attention_values"])
    )


def fit(rows):
    spec = make_spec(rows)
    parts = inputs(rows, spec)
    y = np.array([r["y"] for r in rows])
    w = balanced_weights(rows)
    weights = {name: fit_ridge(design(parts, name), y, w) for name in STRUCTURES}
    spec["attention_admitted"] = (
        len(rows) >= 160
        and len({r["group"] for r in rows}) >= 8
        and len(spec["vocabulary"]) >= 20
    )
    if spec["attention_admitted"]:
        x = design(parts, "motion_context")
        base = np.maximum(0.0, raw_predict(weights["motion_context"], x))
        weights.update(fit_attention(x, parts["words"], y, base, w))
    return spec, weights


def find_donors(rows, training, spec):
    vocab = set(spec["vocabulary"])
    bags = [frozenset(r["tokens"]) & vocab for r in training]
    candidates = {}
    for i, r in enumerate(training):
        candidates.setdefault(r["task"], []).append(i)
    result = []
    for r in rows:
        bag = frozenset(r["tokens"]) & vocab
        eligible = [
            i
            for i in candidates.get(r["task"], [])
            if training[i]["group"] != r["group"] and bags[i] != bag
        ]
        if not eligible:
            result.append(None)
            continue

        def distance(i, recipient=r):
            d = training[i]
            return (
                sum(abs(d["context"][:2] - recipient["context"][:2])),
                d["record"],
                d["id"],
            )

        result.append(min(eligible, key=distance))
    return result


def predictions(rows, spec, weights, training):
    pred = {
        "persistence": np.zeros(len(rows)),
        "constant_velocity": np.array([r["cv"] for r in rows]),
        "prior_net": np.array([r["prior_net"] for r in rows]),
    }
    if not spec:
        return pred, np.zeros(len(rows), dtype=bool)
    parts = inputs(rows, spec)
    for model in STRUCTURES:
        pred[model] = np.maximum(0.0, raw_predict(weights[model], design(parts, model)))
    full = "motion_context_words"
    donors = find_donors(rows, training, spec)
    matched = np.array([i is not None for i in donors])
    substituted = np.array(
        [
            [w in training[i]["tokens"] for w in spec["vocabulary"]]
            if i is not None
            else [False] * len(spec["vocabulary"])
            for i in donors
        ],
        dtype=float,
    )
    for label, words in [
        ("actual", parts["words"]),
        ("removed", np.zeros_like(parts["words"])),
        ("substituted", substituted),
    ]:
        if label != "actual":
            pred["ridge_" + label] = np.maximum(
                0.0, raw_predict(weights[full], design({**parts, "words": words}, full))
            )
        if spec["attention_admitted"]:
            pred["attention_" + label] = attention_predict(
                weights, design(parts, "motion_context"), words, pred["motion_context"]
            )
    return pred, matched
