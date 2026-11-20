"""Inference on each outer person and paired descriptive outcomes in degrees."""
import json
import numpy as np
from common import MODELS, PEOPLE, RESULT, SOURCE, digest, people_table, read_npz, seal
from models import PERSONS, checkpoint, load_checkpoint, predict_net, ridge_design

CONTRASTS = [
    ("corrected_emg", "corrected_motion"), ("corrected_emg", "base"), ("corrected_motion", "base"),
    ("corrected_emg", "corrected_donor"), ("corrected_emg", "corrected_reverse"),
    ("joint", "joint_donor"), ("joint", "joint_reverse"), ("joint", "base"), ("corrected_emg", "joint"),
    ("base", "persistence"), ("base", "velocity")
]
KEYS = ("person", "block", "trial", "slot")


def wrong_trial(held, train):
    if np.intersect1d(held["person"], train["person"]).size or len(np.unique(held["person"])) != 1:
        raise ValueError("Held person cannot enter TRAIN donor bank")
    donor = np.full(len(held["slot"]), -1)
    for block in np.unique(held["block"]):
        people = np.unique(train["person"][train["block"] == block])
        if len(people) == 0:
            raise ValueError("No fold-local donor available for a block")
        for slot in np.unique(held["slot"]):
            rows = np.flatnonzero((held["block"] == block) & (held["slot"] == slot))
            for k, person in enumerate(people):
                take = rows[held["trial"][rows] % len(people) == k]
                bank = np.flatnonzero((train["block"] == block) & (train["slot"] == slot) & (train["person"] == person))
                bank = bank[np.argsort(train["trial"][bank], kind="stable")]
                if not len(bank):
                    raise ValueError("Empty donor block/slot")
                donor[take] = bank[(held["trial"][take] + 1) % len(bank)]
    if (np.any(donor < 0) or not np.array_equal(train["block"][donor], held["block"])
            or not np.array_equal(train["slot"][donor], held["slot"])):
        raise ValueError("Wrong-trial donor identity check failed")
    return donor


def emg_substitute(d, emg):
    if emg.shape != d["bins"][:, :, 2:6].shape:
        raise ValueError("Substituted EMG input shape mismatch")
    bins = d["bins"].copy()
    bins[:, :, 2:6] = emg
    return {**d, "bins": bins}


def infer(held_index):
    group = tuple(i for i in PERSONS if i != held_index)
    held, train = people_table([held_index]), people_table(group)
    order = wrong_trial(held, train)
    donor = emg_substitute(held, train["bins"][order, :, 2:6])
    reverse = emg_substitute(held, held["bins"][:, ::-1, 2:6])
    base = predict_net(held, "motion", load_checkpoint("motion", group))
    state_joint = load_checkpoint("joint", group)
    states = {arm: load_checkpoint(arm, group) for arm in ("motion_correction", "emg_correction")}

    def corrected(d, arm):
        state = states[arm]
        return base + ridge_design(d, arm, state) @ state["coef"]

    result = {"base": base, "joint": predict_net(held, "joint", state_joint),
              "persistence": held["anchor"],
              "velocity": held["anchor"] + 2 * (held["anchor"] - held["past"]),
              "corrected_motion": corrected(held, "motion_correction"),
              "corrected_emg": corrected(held, "emg_correction"),
              "corrected_donor": corrected(donor, "emg_correction"),
              "corrected_reverse": corrected(reverse, "emg_correction"),
              "joint_reverse": predict_net(reverse, "joint", state_joint),
              "joint_donor": predict_net(donor, "joint", state_joint)}
    if not all(v.shape == held["target"].shape and np.isfinite(v).all() for v in result.values()):
        raise ValueError("Prediction missing or nonfinite")
    return {**{k: held[k] for k in (*KEYS, "parent", "cue", "target_tick", "target")},
            **{"donor_" + k: train[k][order] for k in KEYS},
            **{"pred_" + k: v for k, v in result.items()}}


def describe(tables):
    names = [k.removeprefix("pred_") for k in tables[0] if k.startswith("pred_")]
    errors = {name: [d["pred_" + name] - d["target"] for d in tables] for name in names}
    mses = {name: np.array([np.mean(e**2, axis=0) for e in pieces]) for name, pieces in errors.items()}
    rms = lambda m: float(np.sqrt(np.mean(m)))
    scores, contrasts = {}, {}
    for name, parts in errors.items():
        mse = mses[name]
        grouped = np.array([[np.mean(e[t["slot"] == slot]**2, axis=0)
                             for slot in range(6)] for t, e in zip(tables, parts, strict=True)])
        scores[name] = {"equal_person_rmse_deg": rms(mse), "axes_rmse_deg": np.sqrt(mse.mean(axis=0)).tolist(),
                        "pooled_rmse_deg": rms(np.concatenate(parts)**2),
                        "slot_rmse_deg": np.sqrt(grouped.mean(axis=(0, 2))).tolist(),
                        "people_mse_deg2": mse.tolist(), "people_axes_rmse_deg": np.sqrt(mse).tolist(),
                        "people_rmse_deg": np.sqrt(mse.mean(axis=1)).tolist(),
                        "people_mean_signed_error_deg": [e.mean(axis=0).tolist() for e in parts]}
    for a, b in CONTRASTS:
        l, r = mses[a], mses[b]
        contrasts[a + "_minus_" + b] = {
            "overall_deg": rms(l) - rms(r),
            "axes_deg": (np.sqrt(l.mean(axis=0)) - np.sqrt(r.mean(axis=0))).tolist(),
            "people_deg": (np.sqrt(l.mean(axis=1)) - np.sqrt(r.mean(axis=1))).tolist(),
            "omit_one_range_deg": [f([rms(np.delete(l, i, axis=0)) - rms(np.delete(r, i, axis=0))
                                      for i in range(len(tables))]) for f in (min, max)]}
    return {"units": "encoder degrees", "ordered_people": list(PEOPLE), "scores": scores, "contrasts": contrasts,
            "rows": sum(len(t["slot"]) for t in tables), "trials": sum(len(t["slot"]) // 6 for t in tables),
            "people_rows": [len(t["slot"]) for t in tables],
            "competent_base": all(contrasts["base_minus_" + key]["overall_deg"] < 0 for key in ("persistence","velocity")),
            "candidate_emg_benefit": all(contrasts["corrected_emg_minus_" + key]["overall_deg"] < 0
                                         for key in ("corrected_motion", "base"))}


def score_all():
    fit_receipt = RESULT / "fit-complete.json"
    fit = json.loads(fit_receipt.read_text())
    if (fit["freeze"] != digest(SOURCE) or fit["new_neural_fits"] != 27 or fit["new_ridge_fits"] != 12
            or any(digest(MODELS / name) != sha for name, sha in fit["models_and_oof"].items())):
        raise ValueError("Complete fit/OOF inventory failed seal verification")
    records, outputs = [], {}
    for i, pid in enumerate(PEOPLE):
        path = RESULT / "predictions" / (pid + ".npz")
        meta = path.with_suffix(".json")
        if meta.exists():
            receipt = json.loads(meta.read_text())
            if receipt != {"sha256": digest(path), "fit": digest(fit_receipt)}:
                raise ValueError("Existing inference receipt differs")
            d = read_npz(path)
        else:
            if path.exists():
                raise ValueError("Unsealed predictions require reconciliation")
            d = infer(i)
            seal(path, d, archive=True)
            seal(meta, {"sha256": digest(path), "fit": digest(fit_receipt)})
        records.append(d)
        outputs[path.name] = digest(path)
    out = {**describe(records), "fit": digest(fit_receipt), "predictions_sha256": outputs}
    target = RESULT / "scores.json"
    if target.exists():
        if json.loads(target.read_text()) != out:
            raise ValueError("Existing scores differ")
    else:
        seal(target, out)
