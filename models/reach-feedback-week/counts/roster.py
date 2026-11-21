"""Chronological, original-balanced scoring utilities shared with the positive-sort analysis."""
from collections import Counter
import hashlib
import json

import numpy as np

KEY = ("block", "workspace", "original", "ordinal", "k")


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sealed_json(path, expected):
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, f"Unexpected contents: {path}")
    return json.loads(raw)


def keyed_rows(pack):
    return list(zip(*(map(int, pack[n]) for n in KEY), strict=True))


def native_cue(rows, events):
    count = np.searchsorted(events, rows, side="left")
    elapsed = np.zeros(len(rows))
    has = count > 0
    elapsed[has] = .01 * (rows[has] - np.array(events)[count[has] - 1])
    return np.column_stack((count, elapsed, has))


def previous_donors(rows, roster, eligible):
    """Return last numerically eligible earlier original within physical block, workspace and ordinal."""
    ordered = {(r["block"], r["original"]):r for r in roster}
    require(len(ordered) == len(roster), "Duplicate physical block/original key")
    result = np.full(len(rows), -1, dtype=int)
    last = {}
    windows_seen = set()
    prior_k = {}
    for i, (block, ws, oid, ordinal, k) in enumerate(rows):
        r = ordered[block, oid]
        require((block, oid, ordinal) not in windows_seen, "Repeated ordinal in physical original")
        windows_seen.add((block, oid, ordinal))
        require(r["workspace"] == ws and r["start"] <= k-20 and k+20 <= r["end"], "Invalid original/time key")
        require(k > prior_k.get(block, -1), "Windows must follow native row chronology")
        prior_k[block] = k
        key = (block, ws, ordinal)
        if key in last:
            j = last[key]
            donor_original = ordered[block, rows[j][2]]
            require(donor_original["original"] != oid and donor_original["end"] < r["start"],
                    "Donor must be a distinct strictly earlier original")
            result[i] = j
        if eligible[i]:
            last[key] = i
    return result


def draws(blocks, moving, repetitions=5000, seed=20261125):
    """Return positions in the full workspace roster, stratified by acquisition block."""
    blocks = np.asarray(blocks)
    if not len(blocks):
        return None
    rng = np.random.default_rng(seed)
    samples = []
    for b in dict.fromkeys(blocks):
        pos = np.flatnonzero(blocks == b)
        size = len(pos)
        if moving:
            if size < 8:
                return None
            starts = rng.integers(size-7, size=(repetitions, (size+7)//8))
            picked = (starts[...,None] + np.arange(8)).reshape(repetitions, -1)[:, :size]
        else:
            picked = rng.integers(size, size=(repetitions, size))
        samples.append(pos[picked])
    return np.concatenate(samples, axis=1)


def per_original(values, positions, length):
    sums = np.zeros((length, values.shape[1]))
    np.add.at(sums, positions, values)
    counts = np.bincount(positions, minlength=length)[:,None]
    return np.divide(sums, counts, where=counts > 0, out=np.full_like(sums, np.nan))


def summarize(values, positions, roster_length, weights):
    table = per_original(values, positions, roster_length)
    ok = np.isfinite(table).all(1)
    shape = table.shape[1]
    out = {"originals":int(ok.sum()), "windows":len(values),
           "mean":table[ok].mean(0).tolist() if ok.any() else [None]*shape}
    for method, w in weights.items():
        entry = {"interval":None}
        if w is None:
            entry["reason"] = "no assigned roster or fewer than eight assigned originals in a physical block"
        elif not ok.any():
            entry.update(reason="no supported original", empty_draws=len(w))
        else:
            denom = w @ ok.astype(float)
            empty = int(np.count_nonzero(denom == 0))
            entry["empty_draws"] = empty
            if empty or ok.sum() < 2:
                entry["reason"] = "empty bootstrap draw or fewer than two supported originals"
            else:
                samples = (w @ np.nan_to_num(table)) / denom[:,None]
                entry["interval"] = np.quantile(samples, [.025, .975], axis=0).T.tolist()
        out[method] = entry
    return out


def resample_weights(blocks):
    out = {}
    for label, moving in (("moving8", True), ("original_bootstrap", False)):
        d = draws(blocks, moving)
        if d is None:
            out[label] = None
        else:
            size = d.shape[1]
            shifted = d + np.arange(len(d))[:,None]*size
            out[label] = np.bincount(shifted.ravel(), minlength=d.size).reshape(d.shape).astype(float)
    return out


def deviance(y, mu):
    mu = np.maximum(mu, 1e-6)
    value = mu-y
    nz = y > 0
    value[nz] += y[nz] * np.log(y[nz]/mu[nz])
    return 2*value


def memberships(rows, mask):
    selected = [r for i,r in enumerate(rows) if mask[i]]
    return {"windows":len(selected), "originals":len({(r[0], r[2]) for r in selected}),
            "by_ordinal":dict(sorted(Counter(r[3] for r in selected).items()))}


def count_reasons(select, masks):
    return {k:int(np.count_nonzero(select & ~m)) for k,m in masks.items()}
