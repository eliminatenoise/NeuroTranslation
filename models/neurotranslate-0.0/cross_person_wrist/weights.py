"""Validate portable JSON weights before numerical evaluation."""
import json
from pathlib import Path

import numpy as np

from .reference import ROLES
from .temporal import HORIZONS, MODES, SEEDS

FORMAT = "cross-person-wrist-fit-v1"
PARAMETERS = {"input": (8, 12), "input_bias": (12,), "side": (2, 12), "time": (15, 12),
              "query": (12, 12), "key": (12, 12), "value": (12, 12), "other_bias": (2,),
              "out": (12, 12), "ff_in": (12, 24), "ff_bias": (24,), "ff_out": (24, 12),
              "decode": (12, 4), "decode_bias": (4,), "gate": (12, 4), "gate_bias": (4,)}
PRIORS = {"mean": (2, 2, 2), "mean_px": (2, 2, 2), "ridge": (2, 2, 18, 2), "ridge_bias": (2, 2, 2)}
HEAD = {"mean": (90,), "std": (90,), "coef": (90, 2), "bias": (2,), "gain": ()}


def arrays(values, schema):
    if not isinstance(values, dict) or set(values) != set(schema):
        raise ValueError("The checkpoint parameter names do not match the wrist model.")
    out = {}
    for key, shape in schema.items():
        a = np.asarray(values[key])
        if a.shape != shape or a.dtype.kind not in "fiu" or not np.isfinite(a).all():
            raise ValueError(f"Invalid shape or numeric values for {key}.")
        out[key] = a.astype(np.float64)
    return out


def transport_schema():
    schema = {}
    for part, modes in (("full", ("intact", "blocked")), ("matched", MODES)):
        schema.update({f"{part}.prior.{k}": shape for k, shape in PRIORS.items()})
        for mode in modes:
            for seed in SEEDS:
                schema.update({f"{part}.{mode}.{seed}.{k}": shape for k, shape in PARAMETERS.items()})
    return schema


def validate(data):
    if not isinstance(data, dict) or set(data) != {"format", "source", "transport", "heads"}:
        raise ValueError("The checkpoint needs a format, source, temporal parameters and four ridge heads.")
    if data["format"] != FORMAT or data["source"] not in ("synthetic", "local"):
        raise ValueError("Unsupported cross-person wrist checkpoint.")
    transport = arrays(data["transport"], transport_schema())
    names = {f"{r}_{h}" for r in ROLES for h in HORIZONS}
    if not isinstance(data["heads"], dict) or set(data["heads"]) != names:
        raise ValueError("Need one source ridge head for each role and horizon.")
    heads = {}
    for name, h in data["heads"].items():
        if not isinstance(h, dict) or type(h.get("count")) is not int or h["count"] < 0:
            raise ValueError("Each ridge head needs a nonnegative integer training count.")
        fields = {k: v for k, v in h.items() if k != "count"}
        checked = arrays(fields, HEAD if h["count"] else {})
        if h["count"] and (np.any(checked["std"] <= 0) or not 0 <= checked["gain"] <= 1):
            raise ValueError("Invalid ridge scale or damped-velocity gain.")
        heads[name] = {"count": h["count"], **checked}
    return data["source"], transport, heads


def serializable(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    raise TypeError(f"Unsupported checkpoint field {type(x).__name__}")


def write(path, transport, heads, source):
    data = dict(format=FORMAT, source=source, transport=transport, heads=heads)
    validate(data)
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(data, f, allow_nan=False, sort_keys=True, separators=(",", ":"), default=serializable)
        f.write("\n")
