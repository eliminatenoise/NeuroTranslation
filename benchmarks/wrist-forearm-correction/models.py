"""Fold-local CNN fitting and cross-fitted additive ridge corrections."""
from itertools import combinations
import json
import time

import numpy as np
import torch

from common import MODELS, PEOPLE, RESULT, SOURCE, digest, people_table, read_npz, seal

import forecast as cnn

PERSONS = tuple(range(len(PEOPLE)))
NETWORKS = [(arm, group) for arm, size in (("motion", 4), ("motion", 5), ("joint", 5))
            for group in combinations(PERSONS, size)]
HEADS = [(arm, group) for group in combinations(PERSONS, 5)
         for arm in ("motion_correction", "emg_correction")]
CHANNELS = {"motion": 2, "joint": 6, "motion_correction": 2, "emg_correction": 6}


def checkpoint(arm, group):
    return MODELS / (arm + "_" + "-".join(map(str, sorted(group))) + ".npz")


def centered(values, axis):
    center, scale = values.mean(axis=axis), values.std(axis=axis)
    return center, np.where(scale == 0, 1., scale)


def scales(d, channels):
    result = {}
    for name, values, axis in (("bins", d["bins"][:, :, :channels], (0, 1)),
                               ("anchor", d["anchor"], 0), ("change", d["target"] - d["anchor"], 0)):
        result[name + "_center"], result[name + "_scale"] = centered(values, axis)
    return result


def inputs(d, norms, channels):
    bins = (d["bins"][:, :, :channels] - norms["bins_center"]) / norms["bins_scale"]
    anchor = (d["anchor"] - norms["anchor_center"]) / norms["anchor_scale"]
    aux = np.column_stack((anchor, np.eye(6)[d["slot"]]))
    return cnn.torch_inputs((bins, aux))


def fit_network(d, arm, epochs=30):
    nchan = CHANNELS[arm]
    norms = scales(d, nchan)
    change = d["target"] - d["anchor"]
    y = torch.from_numpy(np.ascontiguousarray(
        (change - norms["change_center"]) / norms["change_scale"], dtype=np.float32))
    schedule = cnn.schedule_for_seed(d["person"], 17, epochs=epochs)
    bias = -norms["change_center"] / norms["change_scale"]
    net, history = cnn.fit_temporal(nchan, inputs(d, norms, nchan), y, bias, 17, schedule)
    weights = {"net_" + k: v for k, v in cnn.save_parameters(net).items()}
    return {**norms, **weights, "history": np.array(history)}


def predict_net(d, arm, state):
    nchan = CHANNELS[arm]
    weights = {k.removeprefix("net_"): v for k, v in state.items() if k.startswith("net_")}
    model = cnn.restore_parameters(nchan, weights)
    change = cnn.predict_temporal(model, inputs(d, state, nchan)).astype(np.float64)
    return d["anchor"] + change * state["change_scale"] + state["change_center"]


def rows_at(d, mask):
    return {k: v[mask] for k, v in d.items()}


def corrections_design(d, arm):
    bins = d["bins"]
    blocks = [bins[:, :, :2].reshape(len(bins), -1), d["anchor"]]
    if arm == "emg_correction":
        blocks.append(bins[:, :, 2:6].reshape(len(bins), -1))
    return np.column_stack(blocks)


def ridge_design(d, arm, state):
    x = (corrections_design(d, arm) - state["center"]) / state["scale"]
    return np.column_stack((x, np.eye(6)[d["slot"]]))


def fit_ridge(d, group, arm, oof):
    if not np.array_equal(np.unique(d["person"]), group) or oof.shape != d["target"].shape:
        raise ValueError("Cross-fit people or response shape differ")
    center, scale = centered(corrections_design(d, arm), 0)
    state = {"center": center, "scale": scale}
    x = ridge_design(d, arm, state)
    _, inverse, counts = np.unique(d["person"], return_inverse=True, return_counts=True)
    weights = 1. / (len(counts) * counts[inverse])
    xtw = x.T * weights
    penalties = np.r_[np.full(len(center), .01), np.zeros(6)]
    gram = xtw @ x + np.diag(penalties)
    rhs = xtw @ (d["target"] - oof)
    coeff = np.linalg.solve(gram, rhs)
    if not np.isfinite(coeff).all() or np.max(np.abs(gram @ coeff - rhs)) > 1e-8:
        raise ValueError("Ridge solution fails stationarity")
    return {**state, "coef": coeff}


def outcome_origin(arm, group):
    return {"arm": arm, "fit_people": list(group), "freeze": digest(SOURCE),
            "source": digest(RESULT / "extraction.json")}


def load_checkpoint(arm, group):
    path = checkpoint(arm, group)
    out = json.loads(path.with_suffix(".json").read_text())
    if out["identity"] != outcome_origin(arm, group) or digest(path) != out["sha256"]:
        raise ValueError("Model provenance mismatch")
    return read_npz(path)


def fit_one(arm, group, builder):
    path = checkpoint(arm, group)
    if path.with_suffix(".json").exists():
        load_checkpoint(arm, group)
        return
    origin = outcome_origin(arm, group)
    intent = path.with_suffix(".intent.json")
    if intent.exists() or path.exists():
        raise RuntimeError(f"Unfinished checkpoint {path.name}; reconcile before any repeat")
    seal(intent, origin)
    t0 = time.monotonic()
    output = builder()
    if not all(np.isfinite(v).all() for v in output.values()):
        raise ValueError("Nonfinite fitted state")
    seal(path, output, archive=True)
    seal(path.with_suffix(".json"), {"identity": origin, "sha256": digest(path),
                                     "seconds": time.monotonic() - t0})


def get_oof(d, group):
    output = np.full_like(d["target"], np.nan)
    source = {}
    for i in group:
        inner = tuple(j for j in group if j != i)
        state = load_checkpoint("motion", inner)
        mask = d["person"] == i
        output[mask] = predict_net(rows_at(d, mask), "motion", state)
        source[str(i)] = {"fit_people": list(inner), "sha256": digest(checkpoint("motion", inner))}
    if not np.isfinite(output).all():
        raise ValueError("Missing nested out-of-person prediction")
    return output, source


def fit_all():
    for arm, group in NETWORKS:
        fit_one(arm, group, lambda: fit_network(people_table(group), arm))
    for group in combinations(PERSONS, 5):
        separate = checkpoint("oof", group)
        if not separate.with_suffix(".json").exists():
            d = people_table(group)
            output, inputs_used = get_oof(d, group)
            packed = {k: d[k] for k in ("person", "block", "trial", "slot")}
            packed["prediction"] = output
            if separate.exists():
                raise ValueError("Incomplete OOF checkpoint requires reconciliation")
            seal(separate, packed, archive=True)
            seal(separate.with_suffix(".json"), {"sha256": digest(separate), "parents": inputs_used,
                                                 "identity": outcome_origin("oof", group)})
        for arm in ("motion_correction", "emg_correction"):
            def build():
                d = people_table(group)
                target = load_checkpoint("oof", group)
                if not all(np.array_equal(d[k], target[k]) for k in ("person", "block", "trial", "slot")):
                    raise ValueError("Cross-fit correction rows differ")
                return fit_ridge(d, group, arm, target["prediction"])
            fit_one(arm, group, build)
    inventory = [(arm, group) for arm, group in NETWORKS + HEADS]
    inventory.extend([("oof", group) for group in combinations(PERSONS, 5)])
    complete = {}
    for arm, group in inventory:
        load_checkpoint(arm, group)
        path = checkpoint(arm, group)
        complete[path.name] = digest(path)
        complete[path.with_suffix(".json").name] = digest(path.with_suffix(".json"))
    path = RESULT / "fit-complete.json"
    receipt = {"freeze": digest(SOURCE), "models_and_oof": complete,
               "new_neural_fits": len(NETWORKS), "new_ridge_fits": len(HEADS)}
    if path.exists():
        if json.loads(path.read_text()) != receipt:
            raise ValueError("Fit seal differs")
    else:
        seal(path, receipt)
