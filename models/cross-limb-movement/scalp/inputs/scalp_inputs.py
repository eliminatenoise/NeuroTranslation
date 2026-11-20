"""Reproduce past scalp/control histories, fold scales and earlier-trial controls.

Requires Python 3.10+ and NumPy. See DESIGN.md for timing, support and interpretation.
"""
from collections import defaultdict
from dataclasses import dataclass
import hashlib

import numpy as np


KEYS = ("person", "domain", "session", "event", "direction", "block", "cutoff", "cutoff_s")
FIELDS = ("rows", "names", "mean", "rms", "good", "reason", "bin_samples",
          "bin_first_offset", "bin_last_offset", "source_session", "source_ordinal",
          "source_anchor", "source_issue_s", "original_event_tick", "latest_minus_cutoff_s")
NATIVE = ("balance", "way")
SITES = {
    "central": (("D19", "A1", "B22"), ("C3", "Cz", "C4")),
    "frontal": (("C29", "C16"), ("Fp1", "Fp2")),
    "eye": (("R_horizontal_eog", "L_horizontal_eog", "L_vertical_eog"), ()),
    "neck": (("L_neck_emg", "R_neck_emg"), ()),
}
COHORT_KEYS_SHA256 = "5d7794ae276deee157f82abbdfe59b12f6a4a98ac3e6dbb58507687dac33dc09"
PAIRED_SHA256 = "27d3c00bb6afe91194db45b2d6ebe4298fa2b616ed4742e493d33d7fb9c0eb73"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def typed_digest(arrays):
    digest = hashlib.sha256()
    for key in sorted(arrays):
        a = arrays[key]
        digest.update(f"{key}/{a.dtype.str}/{a.shape}\n".encode("ascii"))
        digest.update(np.ascontiguousarray(a).view(np.uint8))
    return digest.hexdigest()


@dataclass
class ScalpInputs:
    keys: dict
    values: dict
    mask: dict
    source_session: np.ndarray
    envelope_start: np.ndarray
    envelope_end: np.ndarray
    donor: np.ndarray


def _row_index(rows, n):
    a = np.asarray(rows)
    require(a.ndim == 1 and a.dtype.kind in "iu", "integer row vector required")
    require(np.all((a >= 0) & (a < n)), "row outside development cohort")
    return a.astype(np.intp, copy=False)


def earlier_donors(keys, source_session, mask, starts, ends):
    """One-use mapping sorted by recorded clock, independent of input row order."""
    n = len(source_session)
    require(mask.shape == (n, 3) and mask.dtype == np.bool_, "central mask")
    require(starts.shape == ends.shape == (n,) and np.all(starts <= ends), "envelope")
    strata = defaultdict(list)
    for i in np.flatnonzero(mask.any(axis=1)):
        group = (keys["domain"][i], keys["person"][i], keys["session"][i],
                 source_session[i], keys["direction"][i], keys["block"][i], tuple(mask[i]))
        strata[group].append(i)
    donor = np.full(n, -1, dtype=np.int64)
    for group in strata.values():
        ordered = sorted(group, key=lambda i: (keys["cutoff"][i], keys["event"][i]))
        available = []
        for target in ordered:
            for pos in range(len(available) - 1, -1, -1):
                candidate = available[pos]
                if ends[candidate] < starts[target] and keys["event"][candidate] != keys["event"][target]:
                    donor[target] = available.pop(pos)
                    break
            available.append(target)
    return donor


def _clock_checks(source, d, keys, rows):
    rate = (256, 500)[d]
    guard_ticks = (0, 64)[d]
    step = 32000 // rate
    for b in range(20):
        lo = -20000 + 1000 * b
        offsets = np.arange(-rate, 1)
        offsets = offsets[(offsets * step > lo + guard_ticks) &
                          (offsets * step <= lo + 1000 - guard_ticks)]
        require((len(offsets), offsets[0], offsets[-1]) ==
                (source["bin_samples"][b], source["bin_first_offset"][b], source["bin_last_offset"][b]),
                "incorrect source bin or post-cutoff support")
    cutoff = keys["cutoff"][rows]
    issue = source["source_issue_s"]
    cue = source["original_event_tick"]
    require(np.allclose(keys["cutoff_s"][rows] * rate, cutoff, atol=1e-7, rtol=0),
            "clock disagrees with common series/session tick")
    require(np.array_equal(source["source_ordinal"], keys["event"][rows]), "original ordinal")
    require(np.allclose(source["latest_minus_cutoff_s"], source["bin_last_offset"][-1] / rate,
                        atol=1e-8, rtol=0), "last input clock")
    if d == 1:
        require(np.allclose((issue - 0.4) * rate, cue, atol=1e-7, rtol=0)
                and np.array_equal(source["source_session"], keys["session"][rows])
                and np.all(source["source_anchor"] + source["bin_first_offset"][0] >= 0),
                "WAY trial-local cue/grid/series")
    else:
        require(np.array_equal(np.ceil(cue) + 32, cutoff)
                and np.array_equal(source["source_anchor"], cutoff)
                and np.array_equal(issue, cutoff / rate), "balance continuous session clock")


def load_inputs(cohort_path, scalp_path):
    """Open specified input members only. Typed fingerprints permit ZIP repackaging."""
    with np.load(cohort_path, allow_pickle=False) as cohort:
        keys = {k: cohort[k] for k in KEYS}
    require(typed_digest(keys) == COHORT_KEYS_SHA256, "unrecognized development cohort or row order")
    with np.load(scalp_path, allow_pickle=False) as archive:
        fields = (*KEYS, *(f"{n}_{k}" for n in NATIVE for k in FIELDS))
        paired = {k: archive[k] for k in fields}
    require(typed_digest(paired) == PAIRED_SHA256, "unrecognized paired inputs or row order")
    require(all(np.array_equal(keys[k], paired[k]) for k in KEYS), "joint/scalp key mismatch")
    n = len(keys["domain"])
    values = {k: np.zeros((n, 20, 3, 2), dtype=np.float32) for k in SITES}
    masks = {k: np.zeros((n, 3), dtype=bool) for k in SITES}
    sessions = np.empty(n, dtype=np.int64)
    for d, name in enumerate(NATIVE):
        source = {k: paired[f"{name}_{k}"] for k in FIELDS}
        rows = source["rows"]
        require(np.array_equal(rows, np.flatnonzero(keys["domain"] == d)), "source row order")
        _clock_checks(source, d, keys, rows)
        sessions[rows] = source["source_session"]
        labels = source["names"].tolist()
        require(len(set(labels)) == len(labels), "duplicate channel name")
        good = source["good"]
        require(good.dtype == np.bool_ and np.array_equal(good, source["reason"] == 0),
                "source mask/reason disagreement")
        for kind, per_study in SITES.items():
            for slot, label in enumerate(per_study[d]):
                native = labels.index(label)
                ok = good[:, native]
                masks[kind][rows, slot] = ok
                for feature, key in enumerate(("mean", "rms")):
                    x = source[key][:, :, native]
                    require(np.isfinite(x).all() and (x[~ok] == 0).all(), "invalid input/mask")
                    values[kind][rows, :, slot, feature] = x
    # Conservative, inclusive local measurement/target/QC envelopes in native session ticks.
    way = keys["domain"] == 1
    starts = keys["cutoff"] - np.where(way, 314, 198)
    ends = keys["cutoff"] + np.where(way, 64, 71)
    donor = earlier_donors(keys, sessions, masks["central"], starts, ends)
    return ScalpInputs(keys, values, masks, sessions, starts, ends, donor)


def fit_normalizers(inp, train):
    """Per-site mean/population SD over observed training bins (float64)."""
    n = len(inp.keys["domain"])
    train = _row_index(train, n)
    require(train.size and np.unique(train).size == train.size, "empty or repeated training rows")
    # Refuse partial-person subsets. A development fold includes whole individuals.
    people = inp.keys["person"]
    require(np.count_nonzero(np.isin(people, np.unique(people[train]))) == len(train),
            "training split cuts through a person")
    result = {}
    for kind in SITES:
        result[kind] = {}
        for d in (0, 1):
            rows = train[inp.keys["domain"][train] == d]
            means = np.zeros((3, 2))
            scales = np.ones((3, 2))
            counts = np.zeros(3, dtype=np.int64)
            for site in range(3):
                selected = rows[inp.mask[kind][rows, site]]
                history = inp.values[kind][selected, :, site, :].reshape(-1, 2).astype(np.float64)
                counts[site] = len(history)
                if len(history):
                    require(np.isfinite(history).all(), "nonfinite observed training input")
                    means[site] = np.mean(history, axis=0)
                    spread = np.std(history, axis=0, ddof=0)
                    scales[site] = np.where(spread > 0, spread, 1.)
            result[kind][str(d)] = {"mean": means.tolist(), "scale": scales.tolist(),
                                    "count": counts.tolist()}
    return result


def normalize_values(values, mask, domain, scales, kind):
    """Three interleaved float32 feature/feature/mask triples per chronological bin.

    values: (rows,20,3,2); mask: (rows,3) bool; domain: vector or scalar 0/1.
    """
    require(kind in SITES, "unknown electrode group")
    values, mask = np.asarray(values), np.asarray(mask)
    n = len(values)
    require(values.shape == (n, 20, 3, 2) and values.dtype.kind in "if"
            and mask.shape == (n, 3) and mask.dtype == np.bool_, "raw value/mask schema")
    ds = np.asarray(domain)
    require(ds.dtype.kind in "iu" and ds.shape in ((), (n,)) and np.isin(ds, [0, 1]).all(),
            "unknown or invalid study index")
    ds = np.broadcast_to(ds, (n,))
    out = np.zeros((n, 20, 3, 3), dtype=np.float32)
    out[:, :, :, 2] = mask[:, None, :]
    for d in np.unique(ds):
        stat = scales[kind][str(d)]
        means, spread, counts = (np.asarray(stat[f]) for f in ("mean", "scale", "count"))
        require(means.shape == spread.shape == (3, 2) and np.isfinite(means).all()
                and np.isfinite(spread).all() and (spread > 0).all()
                and counts.shape == (3,) and counts.dtype.kind in "iu" and (counts >= 0).all(),
                "unusable training scales")
        for site in range(3):
            rows = np.flatnonzero((ds == d) & mask[:, site])
            if rows.size:
                require(site < len(SITES[kind][int(d)]) and counts[site] > 0,
                        "unsupported observed site or no training measurements")
                x = values[rows, :, site, :].astype(np.float64)
                require(np.isfinite(x).all(), "nonfinite observed input")
                out[rows, :, site, :2] = (x - means[site]) / spread[site]
    require(np.isfinite(out).all(), "normalized input exceeds float32 range")
    return out.reshape(n, 20, 9)


def tokens(inp, scales, rows, kind, mode="real"):
    """Resolve aligned, training-reference or earlier donor histories for a fit."""
    rows = _row_index(rows, len(inp.keys["domain"]))
    require(kind in SITES and mode in ("real", "reference", "wrong"), "unknown electrode group/mode")
    selected = rows
    if mode == "wrong":
        require(kind == "central", "wrong-trial control uses central sites")
        selected = inp.donor[rows]
        require((selected >= 0).all(), "unmatched control row")
        require(np.array_equal(inp.mask[kind][selected], inp.mask[kind][rows]), "donor mask differs")
    mask = inp.mask[kind][rows]
    if mode == "reference":
        output = np.zeros((len(rows), 20, 3, 3), dtype=np.float32)
        output[:, :, :, 2] = mask[:, None, :]
        return output.reshape(len(rows), 20, 9)
    return normalize_values(inp.values[kind][selected], mask, inp.keys["domain"][rows], scales, kind)
