"""Predict the next recorded unit from a single trial's completed 1-ms bins."""
import json
from pathlib import Path

import numpy as np

from .history import History, logprobs


def predict(record):
    if set(record) != {"domain", "local_units", "bins"}:
        raise ValueError("next_neuron_prediction requires domain, local_units and bins")
    units = record["local_units"]
    if not isinstance(units, list) or len(units) < 2:
        raise ValueError("List at least two candidate units from this recording")
    if any(type(u) not in (int, str) or (isinstance(u, str) and not u.strip()) for u in units):
        raise ValueError("Each unit ID must be an integer or a nonempty name")
    if len(set(units)) != len(units):
        raise ValueError("Use a unique local ID for each candidate unit")
    if not isinstance(record["bins"], list):
        raise ValueError("bins must be a list of completed observation bins")
    model = json.loads(Path(__file__).with_name("weights.json").read_text())
    weights = np.asarray(model["weights"])
    history = History(len(units))
    observed_through = None
    occupied = 0
    logits = None
    limit = np.iinfo(np.int64).max
    for row in record["bins"]:
        if not isinstance(row, dict) or set(row) != {"end_ms", "counts"}:
            raise ValueError("Each bin requires end_ms and counts")
        end, counts = row["end_ms"], row["counts"]
        if type(end) is not int or abs(end) > limit:
            raise ValueError("end_ms must be an integer millisecond closing boundary within int64")
        if observed_through is not None and end <= observed_through:
            raise ValueError("Bin end times must strictly increase within one trial")
        if not isinstance(counts, list) or len(counts) != len(units):
            raise ValueError("Supply one observed count for every listed unit")
        if any(type(n) is not int or n < 0 or n > limit for n in counts):
            raise ValueError("Counts must be known nonnegative integers within int64; split at missing observations")
        observed_through = end
        if any(counts):
            counts = np.asarray(counts, dtype=np.int64)
            if np.any(counts > limit - history.count):
                raise ValueError("Cumulative spike counts exceed int64")
            features = history.observe(end, counts)
            logits = features @ weights
            occupied += 1
    return {"local_units": units, "candidate_units": len(units), "observed_through_ms": observed_through,
            "forecast_time_ms": history.last_tick, "occupied_bins": occupied,
            "logits": None if logits is None else logits.tolist(),
            "next_unit_probabilities": None if logits is None else np.exp(logprobs(logits)).tolist()}
