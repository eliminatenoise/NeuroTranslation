"""Fit one prespecified nested residual study; leave subject-linked files in private output."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import fit as original
from predict import angular_tokens, read_checkpoint
from score import held_forecast, matched_comparators
from forearm.residual import ARMS, apply, estimate

PEOPLE = tuple(range(6))
PLAN = {"PROTOCOL.md": "405641c20e33e2ca3c1cb036b7fd473e9b0b5395f483633d4981616cb42749e1",
        "PROTOCOL-ADDENDUM.md": "be1e0e3104ec0b7be89cc70f7e6ed9b2462cca817fc75293ccfcb47d5f15216b"}
BASE = "8636991f783c781142ab811096b0f1769db0a6bcf9386810a3ad7b25fae4e2a6"
digest = original.digest
save = original.save_json
archive = original.write_state


def values(path):
    with np.load(path, allow_pickle=False) as f:
        return dict(f)


def array_hash(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def pin(path, expected):
    if digest(path) != expected:
        raise ValueError(f"Unexpected source identity: {path.name}")


def subset_without(*excluded):
    return tuple(i for i in PEOPLE if i not in excluded)


def label(group):
    return "fit-" + "-".join(str(p) for p in group)


def indices(table, group):
    return np.flatnonzero(np.isin(table["person"], group))


def load_data(args):
    for name, checksum in PLAN.items():
        pin(HERE / name, checksum)
    return original.read_table(args.data, args.manifest)


def outer_bases(args):
    receipt = json.loads((args.bases / "seal.json").read_text())
    expected = json.loads((HERE / "outer-arrays.json").read_text())
    bases = {}
    for held in PEOPLE:
        name = f"held-{held}"
        allowed = subset_without(held)
        if receipt["fits"][name]["fitting_people"] != list(allowed):
            raise ValueError(f"Unexpected outer training roster: {held}")
        path = args.bases / (name + ".npz")
        pin(path, receipt["files"][path.name])
        w = values(path)
        w = {k: v for k, v in w.items() if k.startswith(("angular.stats.", "pretrained.motion.", "pretrained.emg."))}
        if {k: array_hash(v) for k, v in w.items()} != expected[name]:
            raise ValueError(f"Outer motion/EMG parameters or scales changed: {held}")
        bases[allowed] = w
    return bases


def base_prediction(table, rows, w, config, core, mode="motion"):
    return held_forecast(w, config, core, "pretrained", mode, table["bins"][rows, :, :ARMS[mode]],
                         table["anchor"][rows], table["slot"][rows])


def inner_state(table, group, core):
    rows = indices(table, group)
    stats = original.normalization(table, rows)
    y = original.tensor_array((table["target"][rows] - table["anchor"][rows] - stats["residual_center"])
                              / stats["residual_scale"])
    x = original.tensor_array(angular_tokens(table["bins"][rows, :, :2], table["anchor"][rows],
                                             table["slot"][rows], "motion", stats))
    w, detail = original.fit_one(core, x, y)
    state = {"angular.stats." + k: v for k, v in stats.items()}
    state.update({"pretrained.motion." + k: v for k, v in w.items()})
    return state, {**detail, "fitting_people": list(group), "fitting_rows": len(rows),
                   "fitting_row_index_sha256": array_hash(rows.astype("<i8"))}


def nested_rows(table, group, bases, config, core):
    rows = indices(table, group)
    person = table["person"][rows]
    oof = np.full((len(rows), 2), np.nan)
    parents = {}
    for recipient in group:
        providers = tuple(i for i in group if i != recipient)
        mask = person == recipient
        oof[mask] = base_prediction(table, rows[mask], bases[providers], config, core)
        parents[str(recipient)] = {"training_people": list(providers), "rows": int(mask.sum()),
                                   "row_index_sha256": array_hash(rows[mask].astype("<i8"))}
    if not np.isfinite(oof).all():
        raise ValueError("A nested training forecast is missing")
    return rows, oof, parents


def fit_study(args):
    started = time.perf_counter()
    route = original.configure(2)
    table = load_data(args)
    bases = outer_bases(args)
    cfg, numpy_core = read_checkpoint(args.spatial)
    core = original.cores(args.spatial)["pretrained"]
    original_checkpoint = args.bases / "movement-weights.npz"
    pin(original_checkpoint, BASE)
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {"plan": PLAN, "route": route, "original_combined_sha256": BASE, "inner": {},
              "residuals": {}, "files": {}, "outer_source": digest(args.bases / "seal.json")}
    for group in itertools.combinations(PEOPLE, 4):
        w, detail = inner_state(table, group, core)
        bases[group] = w
        path = args.out / (label(group) + ".npz")
        archive(path, w)
        report["inner"][label(group)] = detail
        report["files"][path.name] = digest(path)
    for group in [subset_without(h) for h in PEOPLE] + [PEOPLE]:
        rows, oof, parents = nested_rows(table, group, bases, cfg, numpy_core)
        path = args.out / ("oof-" + label(group) + ".npz")
        archive(path, {"row": rows, "base": oof})
        report["files"][path.name] = digest(path)
        states = {}
        for arm, c in ARMS.items():
            state = estimate(table["bins"][rows, :, :c], table["anchor"][rows], oof, table["slot"][rows],
                             table["target"][rows], table["person"][rows], arm)
            states.update({arm + "." + k: v for k, v in state.items()})
        path = args.out / ("residual-" + label(group) + ".npz")
        archive(path, states)
        report["files"][path.name] = digest(path)
        report["residuals"][label(group)] = {"training_people": list(group), "n": len(rows), "oof_parents": parents}
    # The final group is all six. Its coefficients were fitted from five-person out-of-person base forecasts.
    combined = values(original_checkpoint)
    conf = json.loads(str(combined["configuration"]))
    conf["angular"]["forearm_residual"] = {"format": 1, "arms": list(ARMS), "base_mode": "motion", "plan": PLAN}
    combined["configuration"] = np.array(json.dumps(conf))
    combined.update({"angular.residual." + k: v for k, v in states.items()})
    path = args.out / "movement-weights.npz"
    archive(path, combined)
    report["files"][path.name] = digest(path)
    report["seconds"] = time.perf_counter() - started
    save(args.out / "seal.json", report)


def donor_check(table):
    donor = table["donor"]
    expected = np.empty_like(donor)
    keys = np.column_stack([table[k] for k in ("person", "block", "slot")])
    for k in np.unique(keys, axis=0):
        rows = np.flatnonzero((keys == k).all(axis=1))
        ordered = rows[np.argsort(table["trial"][rows])]
        if len(ordered) < 2 or len(np.unique(table["trial"][ordered])) != len(ordered):
            raise ValueError("A wrong-trial control has no distinct eligible donor")
        expected[ordered] = np.roll(ordered, -1)
    np.testing.assert_array_equal(expected, donor)
    return donor


def one_fold(table, held, fold, heads, cfg, core, comparators, comparator_hashes):
    rows = indices(table, (held,))
    anchor, slot = table["anchor"][rows], table["slot"][rows]
    bins = table["bins"][rows, :, :6]
    motion = base_prediction(table, rows, fold, cfg, core)
    preds = {"zero": motion, "persistence": anchor, "direct_shared_emg": base_prediction(table, rows, fold, cfg, core, "emg")}
    preds.update(matched_comparators(comparators, table, held, rows, comparator_hashes))
    for arm, c in ARMS.items():
        state = {k: heads[arm + "." + k] for k in ("center", "scale", "coef")}
        preds[arm] = apply(bins[:, :, :c], anchor, motion, slot, arm, state)
        if arm == "emg":
            for name, signal in (("wrong_trial", table["bins"][table["donor"][rows], :, 2:6]),
                                 ("reversed", bins[:, ::-1, 2:6]),
                                 ("time_constant", bins[:, :, 2:6].mean(axis=1, keepdims=True))):
                switched = bins.copy()
                switched[:, :, 2:6] = signal
                preds[name] = apply(switched, anchor, motion, slot, arm, state)
    return rows, preds


def aggregate(predictions, table):
    person = table["person"]
    target = table["target"]
    mses, scores = {}, {}
    for k, v in predictions.items():
        err = v - target
        mse = np.stack([np.mean(err[person == p]**2, axis=0) for p in PEOPLE])
        mses[k] = mse
        scores[k] = {"equal_person_rmse_deg": float(np.sqrt(mse.mean())),
                     "axis_rmse_deg": np.sqrt(mse.mean(axis=0)).tolist(),
                     "pooled_window_rmse_deg": float(np.sqrt((err**2).mean()))}
    contrasts = {}
    person_differences = {}
    for a, b in [("emg", k) for k in scores if k != "emg"] + [("motion", "zero")]:
        left, right = mses[a], mses[b]
        deltas = np.sqrt(left.mean(axis=1)) - np.sqrt(right.mean(axis=1))
        omit = [np.sqrt(np.delete(left, i, axis=0).mean()) - np.sqrt(np.delete(right, i, axis=0).mean()) for i in PEOPLE]
        key = a + "_minus_" + b
        contrasts[key] = {"difference_deg": float(np.sqrt(left.mean()) - np.sqrt(right.mean())),
                          "people_lower_error": int((deltas < 0).sum()), "omit_one_range_deg": [float(min(omit)), float(max(omit))]}
        person_differences[key] = deltas
    paired = all(contrasts["emg_minus_" + k]["difference_deg"] < 0 for k in ["motion", "zero", "wrong_trial", "reversed", "time_constant"])
    beats_cnn = contrasts["emg_minus_prior_emg_corrected_cnn"]["difference_deg"] < 0
    return {"units": "degrees", "people": 6, "runs": 47, "trials": 1879, "overlapping_windows": 11274,
            "axes": ["extension", "radial_deviation"], "scores": scores, "contrasts": contrasts,
            "aligned_forearm_gate": paired, "beats_prior_corrected_cnn_on_these_rows": beats_cnn}, mses, person_differences


def score_study(args):
    table = load_data(args)
    donor_check(table)
    cfg, core = read_checkpoint(args.spatial)
    pin(args.spatial, original.BASE_HASH)
    bases = outer_bases(args)
    seal = json.loads((args.fitted / "seal.json").read_text())
    if seal["plan"] != PLAN:
        raise ValueError("Fitting plan differs")
    for name, expected in seal["files"].items():
        pin(args.fitted / name, expected)
    hashes = json.loads((HERE.parent / "comparator-arrays.json").read_text())
    preds = {}
    for h in PEOPLE:
        group = subset_without(h)
        heads = values(args.fitted / ("residual-" + label(group) + ".npz"))
        rows, fold = one_fold(table, h, bases[group], heads, cfg, core, args.comparators, hashes)
        for name, v in fold.items():
            if name not in preds:
                preds[name] = np.full_like(table["target"], np.nan)
            preds[name][rows] = v
    if not all(np.isfinite(v).all() for v in preds.values()):
        raise ValueError("Missing or invalid held-person forecast")
    summary, mses, differences = aggregate(preds, table)
    summary["fit_seal_sha256"] = digest(args.fitted / "seal.json")
    summary["table_manifest_sha256"] = original.TABLE_MANIFEST_HASH
    out = {k: table[k] for k in ("person", "block", "trial", "slot", "parent", "cue", "target_tick", "donor", "anchor", "target")}
    out.update({"pred." + k: v for k, v in preds.items()})
    out.update({"mse." + k: v for k, v in mses.items()})
    out.update({"difference." + k: v for k, v in differences.items()})
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    archive(args.out / "private-scores.npz", out)
    save(args.out / "results.json", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="command", required=True)
    for cmd in ("fit", "score"):
        p = modes.add_parser(cmd)
        for name in ("data", "manifest", "spatial", "bases", "out"):
            p.add_argument("--" + name, type=Path, required=True)
        if cmd == "score":
            for name in ("fitted", "comparators"):
                p.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    (fit_study if args.command == "fit" else score_study)(args)
