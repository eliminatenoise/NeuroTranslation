"""Replay sorted rat spikes on the 1-ms clock. Original adapter code CC0; recordings CC BY 4.0."""

import json
from pathlib import Path

import numpy as np
from pack import checked, save, schema


def trial(path, number):
    with np.load(path, allow_pickle=False) as a:
        if int(a["trial_id"]) != number:
            raise ValueError("Incorrect trial")
        ids, ends, times = (a[k] for k in ("unit_id", "spike_end", "spike_time_s"))
        start, stop = float(a["start_s"]), float(a["stop_s"])
    sizes = np.diff(np.r_[0, ends])
    assert len(set(ids.tolist())) == len(ids) == len(sizes)
    assert (
        sizes.min() >= 0
        and ends[-1] == len(times)
        and (times > start).all()
        and (times < stop).all()
    )
    assert all((np.diff(v) >= 0).all() for v in np.split(times, ends[:-1].astype(int)))
    ticks = np.ceil(1000 * times).astype(np.int64) - 1
    full = (ticks >= int(np.ceil(1000 * start))) & (ticks < int(np.floor(1000 * stop)))
    bins, ix = np.unique(ticks[full], return_inverse=True)
    counts = np.zeros((len(bins), len(ids)), dtype=np.int64)
    np.add.at(counts, (ix, np.repeat(np.arange(len(ids)), sizes)[full]), 1)
    # Issue after the current bin closes; include its counts and reset at trial start.
    state = np.zeros((len(ids), 3))
    total = np.zeros(len(ids))
    tau = np.array([10.0, 100.0, 1000.0])
    x = np.empty((len(bins), len(ids), 1, 5), dtype=np.float32)
    for j, current in enumerate(counts):
        if j:
            state *= np.exp(-(bins[j] - bins[j - 1]) / tau)
        total += current
        state += current[:, None]
        x[j, :, 0, :] = np.column_stack([np.log1p(total), np.log1p(state), current > 0])
    score = counts[1:].sum(axis=1) == 1
    return {
        "X": x[:-1][score],
        "y": counts[1:][score].argmax(axis=1),
        "issue_ms": bins[:-1][score] + 1,
        "target_ms": bins[1:][score] + 1,
        "group": np.full(score.sum(), number),
        "occupied_ordinal": np.arange(1, len(bins))[score],
    }, ids


def rat(inputs, stage, out):
    cat = json.loads(Path(__file__).with_name("catalog.json").read_text())
    defs = schema(
        "categorical",
        [
            "log1p_trial_count",
            "log1p_trace_10ms",
            "log1p_trace_100ms",
            "log1p_trace_1000ms",
            "current_bin_fired",
        ],
        ["log(1+count)"] * 4 + ["0 or 1"],
        ["candidate"],
        ["local sorted unit row"],
        1,
        source="Shin and Jadhav, DANDI:000978/0.240511.0307, CC BY 4.0. JS14 and ER1 are distinct rats.",
        history="Trial-local cumulative counts and three exponentially decayed counts through the last completed occupied 1-ms bin; all source candidates retained, including inactive rows. The fifth feature marks the most recent completed bin.",
        target="Source candidate in next occupied complete 1-ms bin, conditional on exactly one spike there. Multiple events unresolved; last issue censored at trial end. Forecast receives no target clock or future gap.",
        group_definition="Trip number within recording; one rat trained, JS14 55–78 inclusive; JS14 80–89 held, trial 79 omitted. ER1 0–9 external. Never equate sorted unit IDs between rats.",
        baseline_description="Source fitted five-coefficient softmax model trained on JS14 trials 55–78. Weights fixed before historical assessment.",
        limits="Offline sorter, unverified continuous detection; sorted-unit identity is recording-local.",
    )
    parts = (
        [("train", range(55, 79), "rat_primary")]
        if stage == "train"
        else [
            ("test_js14", range(80, 90), "rat_primary"),
            ("test_er1", range(10), "rat_external"),
        ]
    )
    for split, numbers, key in parts:
        vals = []
        first = None
        for number in numbers:
            dir_name = {"train": "train", "test_js14": "test", "test_er1": "er1"}[split]
            path = inputs / dir_name / f"trial-{number:03d}.npz"
            checked(path, cat[key][str(number)])
            row, ids = trial(path, number)
            if first is None:
                first = ids.copy()
            assert np.array_equal(first, ids)
            vals.append(row)
        arr = {key: np.concatenate([r[key] for r in vals]) for key in vals[0]}
        logits = arr["X"][:, :, 0, :] @ np.array(cat["rat_baseline_weights"])
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        assert np.all(arr["issue_ms"] < arr["target_ms"])
        save(
            out,
            "rat_next_unit",
            split,
            defs,
            baseline=probs / probs.sum(axis=1, keepdims=True),
            **arr,
        )
