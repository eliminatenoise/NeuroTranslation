"""Forecast two camera-plane wrist positions from fifteen earlier, named image frames."""
import json
from pathlib import Path

import numpy as np

from .reference import ROLES, history, role_names
from .ridge import PRIMARY, endpoints
from .temporal import BASES, HORIZONS, SEEDS, baseline, corrections, geometry, outputs
from .weights import validate

DEFAULT_FIT = Path(__file__).with_name("synthetic-fit.json")
TEMPORAL = {
    "intact": ("full", "intact"),
    "blocked": ("full", "blocked"),
    "intact_swapped": ("full", "intact_swapped"),
    "matched_intact": ("matched", "intact"),
    "matched_blocked": ("matched", "blocked"),
    "matched_intact_swapped": ("matched", "intact_swapped"),
    "trained_swap": ("matched", "trained_swap"),
    **{label: ("full", label) for label in BASES},
}


def parameters(state, prefix):
    return {key.removeprefix(prefix + "."): value for key, value in state.items() if key.startswith(prefix + ".")}


def inputs(case):
    fields = {"domain", "implant_side", "annotated_wrist", "frame_indices", "prior_by_name"}
    if not isinstance(case, dict) or set(case) not in (fields, fields | {"earlier_donor"}):
        raise ValueError("Use the identity, frame indices, named prior and optional earlier donor only.")
    if case["domain"] != "cross_person_wrist":
        raise ValueError("Expected the cross_person_wrist domain.")
    names = role_names(case["implant_side"], case["annotated_wrist"])
    current = history(case["frame_indices"], case["prior_by_name"], names)
    donor = None
    if "earlier_donor" in case:
        entry = case["earlier_donor"]
        if not isinstance(entry, dict) or set(entry) != {"frame_indices", "prior_by_name"}:
            raise ValueError("The earlier donor needs its own frame_indices and prior_by_name.")
        donor = history(entry["frame_indices"], entry["prior_by_name"], names)
        now, then = current.indices[-1]+1, donor.indices[-1]+1
        if now - then < 900 or then // 3600 >= now // 3600:
            raise ValueError("The donor must precede this event by 900 frames and occupy an earlier 120 s block.")
    return names, current, donor


def empty(reasons):
    return {"endpoint_native_px": [[None, None] for _ in HORIZONS],
            "endpoint_shoulder_widths": [[None, None] for _ in HORIZONS],
            "reason": list(reasons),
            "reason_by_horizon": [list(reasons) for _ in HORIZONS]}


def bilateral(sample):
    if sample is None:
        return None, None, "missing_earlier_donor"
    pose = sample.pose()
    if pose is None:
        reason = sample.reason if sample.frame is None else "incomplete_bilateral_prior"
        return None, None, reason
    info = geometry(pose)
    if not info[-1].all():
        return None, None, "invalid_projected_arm_scale"
    return pose, info, "available"


def predict(case, state):
    source, fit, heads = state
    names, current, donor = inputs(case)
    frame = current.frame
    reasons = [(current.reason if frame is None else "available" if r in current.arms else "missing_role_landmark")
               for r in ROLES]
    methods = {name: empty(reasons) for name in PRIMARY}
    for k, h in enumerate(HORIZONS):
        for s, role in enumerate(ROLES):
            if reasons[s] != "available":
                continue
            head = heads[f"{role}_{h}"]
            if not head["count"]:
                for data in methods.values():
                    data["reason_by_horizon"][k][s] = "unfitted_head"
                continue
            for label, uv in endpoints(current.arms[role], h, head).items():
                methods[label]["endpoint_shoulder_widths"][k][s] = uv.tolist()
                methods[label]["endpoint_native_px"][k][s] = frame.decode(uv).tolist()
    for data in methods.values():
        for s in range(2):
            h0, h1 = (row[s] for row in data["reason_by_horizon"])
            data["reason"][s] = h0 if h0 == h1 else "see_reason_by_horizon"
    pose, info, reason = bilateral(current)
    _, earlier, donor_reason = bilateral(donor)
    scales = info[1][0].tolist() if info is not None else [None, None]
    for label, (part, mode) in TEMPORAL.items():
        swap = mode in ("intact_swapped", "trained_swap")
        why = reason
        if why == "available" and swap and donor_reason != "available":
            why = donor_reason if donor is None else "donor_" + donor_reason
        method = methods[label] = empty([why] * 2)
        method["delta_arm_lengths"] = [[None, None] for _ in HORIZONS]
        method["endpoint_from_last_shoulder_arm_lengths"] = [[None, None] for _ in HORIZONS]
        method["span_change_px"] = [None, None]
        if why != "available":
            continue
        features, scale, wrist, shoulder, _ = info
        prior = parameters(fit, f"{part}.prior")
        if mode in BASES:
            delta = baseline(pose, prior, mode)
        else:
            trained = "intact" if mode == "intact_swapped" else mode
            predictions = [corrections(features, parameters(fit, f"{part}.{trained}.{seed}"), mode,
                                       earlier[0] if swap else None) for seed in SEEDS]
            delta = prior["mean"] + np.mean(predictions, axis=0)
        pred = outputs(delta, scale, wrist, shoulder)
        uv = pred["endpoint_px"][0] / frame.width
        method.update(endpoint_shoulder_widths=uv.tolist(), endpoint_native_px=frame.decode(uv).tolist(),
                      delta_arm_lengths=delta[0].tolist(),
                      endpoint_from_last_shoulder_arm_lengths=pred["endpoint_from_last_shoulder_normalized"][0].tolist(),
                      span_change_px=pred["span_change_px"][0].tolist())
    ref = None if frame is None else {"origin_px": frame.origin.tolist(), "basis": frame.basis.tolist(),
                                      "width_px": frame.width}
    return {"domain": "cross_person_wrist", "fit_source": source, "horizons_frames": list(HORIZONS),
            "nominal_hz": 30, "roles": list(ROLES), "role_wrist": dict(zip(ROLES, (g[0] for g in names))),
            "reference": ref, "role_arm_scale_px": scales, "role_reason": dict(zip(ROLES, reasons)),
            "methods": methods}


def forecast(case, checkpoint=DEFAULT_FIT):
    return predict(case, validate(json.loads(Path(checkpoint).read_bytes())))
