"""Compute the four fitted readouts and their controls on eight public recording excerpts."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
for folder in ("counts", "motor"):
    sys.path.insert(0, str(HERE/folder))
import forecast as count
from reproduce import forecast_all
from replay import pooled_history


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


late = module("week_late_counts", "late_counts/score.py")
muscle = module("week_muscle_lengths", "muscles/model.py")


def read(name):
    return json.loads((HERE/name).read_bytes())


def case_list():
    choices = read("cases/selection.json")["cases"]
    index = {r["source_index"]: i for i, r in enumerate(choices, 1)}
    return [dict(case=i, **r, donor_case=index.get(r["metadata_donor_index_zero_based"]))
            for i, r in enumerate(choices, 1)]


def snapshot(number):
    with np.load(HERE/"cases"/f"case-{number}.npz", allow_pickle=False) as f:
        return dict(f)


def pooled_counts(case, donor):
    models = read("counts/fits.json")["populations"]
    guide = case["all_guide"]
    counts = lambda raw, groups: count.totals(raw[None], groups)[0]
    groups = count.group_columns(guide, models["primary"]["contacts"], "primary")
    base, residual = count.build_design(case["pose"][None], case["cue_at_k"][None],
                                        counts(case["all_history"], groups), case["movement"][None,-1])
    wrong = None
    if donor is not None:
        _, wrong = count.build_design(donor["pose"][None], donor["cue_at_k"][None],
                                      counts(donor["all_history"], groups), donor["movement"][None,-1])
    results = {}
    for mode, model in models.items():
        groups = count.group_columns(guide, model["contacts"], mode)
        results[mode] = {
            "contacts": model["contacts"],
            "observed": counts(case["all_delayed"], groups)[0],
            "base": count.predict(model["base"], base)[0],
            "update": count.predict(model["update"], np.column_stack((base, residual)))[0],
            "wrong": None if wrong is None else count.predict(model["update"], np.column_stack((base, wrong)))[0],
            "previous_100ms": counts(case["all_concurrent"], groups)[0],
            "pre_k_100ms": counts(case["all_history"][-10:], groups)[0],
            "train_mean": model["train_mean"],
        }
    return results


def late_counts(case, donor, contacts):
    fits = read("late_counts/fits.json")["arms"]
    result = {arm: [] for arm in (*late.METHODS, "observed")}
    if donor is None:
        result["wrong_donor"] = None
    for c in contacts:
        columns = (case["all_guide"][:,0] == c) & (case["all_guide"][:,1] > 0)
        if not columns.any():
            raise ValueError(f"Missing positive sort at contact {c}")
        history, recent, target = [case[name][:,columns].sum(1)[None] for name in
                                   ("all_history", "all_concurrent", "all_delayed")]
        moves = case["movement"][None]
        paths = [(arm, arm, moves) for arm in late.ARMS]
        paths.append(("zero_displacement", "measured_update", np.zeros_like(moves)))
        if donor is not None:
            paths.append(("wrong_donor", "measured_update", donor["movement"][None]))
        for name, arm, path in paths:
            x = late.design(case["pose"][None], case["cue"][None], history, recent, path, arm)
            result[name].append(float(late.rate(fits[arm][str(c)], x)[0]))
        result["previous_100ms"].append(int(recent.sum()))
        result["pre_k_100ms"].append(int(history[0,-10:].sum()))
        result["train_mean"].append(fits["measured_update"][str(c)]["mean_count"])
        result["observed"].append(int(target.sum()))
    return dict(contacts=contacts, **result)


def motion_and_lengths(case, donor):
    observations = [case] if donor is None else [donor, case]
    keys = np.stack([s["key"] for s in observations])
    d = dict(zip(("block","workspace","original","ordinal","k"), keys.T, strict=True))
    for name in ("pose","cue","movement"):
        d[name] = np.stack([s[name] for s in observations])
    d["pooled"] = np.concatenate([pooled_history(s["all_history"][None], s["all_guide"]) for s in observations])
    pred = forecast_all(d, HERE/"motor/weights")
    movement = {"observed": case["movement"]}
    for arm in ("full","pose","wrong","ridge_full","ridge_pose","ridge_wrong","frozen","stationary","velocity"):
        movement[arm] = None if donor is None and "wrong" in arm else pred[arm][-1]
    with np.load(HERE/"muscles/weights.npz", allow_pickle=False) as f:
        w = dict(f)
    lengths = {"labels": case["path_labels"], "source_model": case["source_model_delta_m"]}
    for arm in ("full","pose","wrong","frozen","ridge_full","ridge_pose","stationary","velocity"):
        if donor is None and arm == "wrong":
            lengths[arm] = None
            continue
        # Every readout uses the recipient's pre-k anchor, including the donor-count control.
        lengths[arm] = muscle.infer_path(case["pose"][None], movement[arm][None], w)[0]
    lengths["direct"] = muscle.infer_direct(case["pose"][None], case["cue"][None], w)[0]
    lengths["measured_path"] = muscle.infer_path(case["pose"][None], case["movement"][None], w)[0]
    return movement, lengths


def plain(value):
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value.tolist() if isinstance(value, np.ndarray) else value


def forecast_case(number):
    """Return forecasts, observed counts and displacement, and model-derived lengths for case 1–8."""
    if not isinstance(number, int) or not 1 <= number <= 8:
        raise ValueError("Choose a case from 1 through 8.")
    record = case_list()[number-1]
    case = snapshot(number)
    donor = snapshot(record["donor_case"]) if record["donor_case"] is not None else None
    movement, lengths = motion_and_lengths(case, donor)
    populations = pooled_counts(case, donor)
    return plain(dict(case=record, pooled_counts=populations, late_counts=late_counts(case, donor, populations["positive"]["contacts"]),
                      displacement_hand_m_elbow_m_handle_cm=movement, muscle_path_change_m=lengths))


def describe(result):
    r = result["case"]
    donor = f"case {r['donor_case']}" if r["donor_case"] else "unavailable (first eligible reach)"
    m = result["displacement_hand_m_elbow_m_handle_cm"]
    h = result["pooled_counts"]["primary"]
    late_model = result["late_counts"]
    g = result["muscle_path_change_m"]
    return (f"September 14 · case {r['case']} · block {r['block']} · workspace {r['workspace']} · reach {r['original']} · row {r['k']}\n"
            f"Earlier comparison reach: {donor}\n"
            f"Hand x displacement at 100 ms (mm): forecast {1000*m['full'][-1][0]:+.3f}, measured {1000*m['observed'][-1][0]:+.3f}\n"
            f"Contact {h['contacts'][0]}, all exported spikes over the following 100 ms: update {h['update'][0]:.3f}, observed {h['observed'][0]:g}\n"
            f"Contact {late_model['contacts'][0]}, positive-sort spikes in that interval: late update {late_model['measured_update'][0]:.3f}, observed {late_model['observed'][0]:g}\n"
            f"{g['labels'][0]} path change at 100 ms (mm): forecast {1000*g['full'][-1][0]:+.3f}, OpenSim reference {1000*g['source_model'][-1][0]:+.3f}")
