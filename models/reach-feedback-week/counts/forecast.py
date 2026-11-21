"""Predict events in a future 100-ms interval from reaching measurements."""
import json
from pathlib import Path

import numpy as np

from roster import require, sealed_json

HERE = Path(__file__).resolve().parent
MAP_HASH = "2e0c458184d731e36c7671281df985026d4430ca2f1699950e82ea07110cf2ba"
TRAIN_MEMBER = "6062b7e8dacdf46f7eee465bd844ffe1fb3b7ce0793c34d3e4d106be357f4746"
TEST_MEMBER = "4456c7bf8cda177f31c849e3fe794100269ca951c741c1718dd5c750d5432a76"
TRAIN_KEYS = "d85237f8f6ebb1c918e814436225880c3cd55c1fb2109117ef59fd95eaf51af3"
LABELS = [f"{p}_{a}" for p in ("Marker_1", "Pronation_Pt1") for a in "xyz"] + ["handle_x", "handle_y"]
POPULATIONS = ("primary", "zero", "positive")


def contact_map():
    return sealed_json(HERE / "contact-crosswalk.json", MAP_HASH)


def channels(mapping, population):
    require(population in POPULATIONS, "Unknown population")
    return mapping["shared_contacts_by_presence"]["positive" if population == "positive" else "zero"]


def group_columns(guide, contacts, population):
    """Group one physical recording's columns by contact using its own sort assignments."""
    require(population in POPULATIONS, "Unknown population")
    guide = np.asarray(guide)
    require(guide.ndim == 2 and guide.shape[1] == 2 and guide.dtype.kind in "ui", "Invalid native guide")
    require(len(np.unique(guide, axis=0)) == len(guide), "Repeated guide row")
    active = {"primary":guide[:, 1] >= 0, "zero":guide[:, 1] == 0, "positive":guide[:, 1] > 0}[population]
    groups = [np.flatnonzero(active & (guide[:, 0] == c)) for c in contacts]
    require(all(len(g) for g in groups), "Absent contact class; missing coverage cannot become zero")
    return groups


def totals(cube, groups):
    """Sum over raw bins and local columns; preserve a validity flag per contact."""
    cube = np.asarray(cube)
    require(cube.ndim == 3 and cube.dtype.kind in "iuf", "Expected numeric bins")
    result = np.empty((len(cube), len(groups)))
    valid = np.empty(result.shape, dtype=bool)
    for i, columns in enumerate(groups):
        raw = cube[:, :, columns]
        ok = (np.isfinite(raw) & (raw >= 0) & (np.floor(raw) == raw)).all(axis=(1, 2))
        valid[:, i] = ok
        result[:, i] = np.sum(raw, axis=(1, 2), dtype=float, where=ok[:, None, None])
        result[~ok, i] = np.nan
    return result, valid


def build_design(pose, cue_at_k, history_counts, displacement=None):
    """Construct unscaled rows. The slope is per native 10-ms sample."""
    pose = np.asarray(pose, dtype=float)
    last = pose[:, -1, :]
    slope = (last - pose[:, -5, :]) / 4.
    base = np.column_stack((last, slope, history_counts, cue_at_k))
    if displacement is None:
        return base
    return base, np.asarray(displacement) - 10. * slope


def predict(head, design):
    """Return one expected count per row and contact. Flooring applies only to scoring."""
    beta = np.asarray(head["coefficients"])
    z = (np.asarray(design) - head["mean"]) / head["scale"]
    with np.errstate(over="ignore", under="ignore"):
        result = np.exp(z @ beta[:, 1:].T + beta[:, 0])
    require(np.isfinite(result).all(), "Unscorable nonfinite expectation")
    return result


def write_json(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, allow_nan=False, separators=(",", ":"))
        stream.write("\n")
