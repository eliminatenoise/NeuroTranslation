"""Fit or independently score the prespecified heel and contact-load readouts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from forecast import OFFSETS, READOUTS, BASELINES, batch, design, baseline, tokens

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from predict import DEFAULT_CHECKPOINT, read_checkpoint
PARENT = "6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864"
MAIN = "encoder_full_rank2"
MOTION = "encoder_motion_rank2"
UNRESTRICTED = "encoder_full_unrestricted"


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def slice_rows(data, rows):
    return {k: v[rows] for k, v in data.items()}


def encoders():
    if hashlib.sha256(DEFAULT_CHECKPOINT.read_bytes()).hexdigest() != PARENT:
        raise ValueError("The original movement encoder has changed.")
    cfg, weights = read_checkpoint(DEFAULT_CHECKPOINT)
    raw = json.loads((HERE.parent / "back_rotation/random-encoder.json").read_bytes())
    return cfg, weights, {k: np.asarray(v) for k, v in raw.items()}


def weights(data):
    people = np.unique(data["person"])
    w = np.zeros(len(data["person"]))
    for person in people:
        own = data["person"] == person
        repetitions = np.unique(data["repeat"][own])
        for trial in repetitions:
            rows = own & (data["repeat"] == trial)
            w[rows] = 1 / (len(people) * len(repetitions) * rows.sum())
    return w


def center_scale(x, w):
    mean = w @ x
    scale = np.sqrt(w @ ((x - mean) ** 2))
    return mean, np.where(scale < 1e-8, 1., scale)


def median(values, w):
    order = np.argsort(values, kind="stable")
    return float(values[order[np.searchsorted(w[order].cumsum(), w.sum() / 2)]])


def fit(data, encoder):
    w = weights(data)
    force = data["force_n"]
    typical = median(force, w)
    phases = {}
    for offset in OFFSETS:
        use = data["offset"] == offset
        phases[str(offset)] = median(force[use], w[use]) if use.any() else typical
    mean, scale = center_scale(tokens(data["marker_mm"], data["emg_uv"]).reshape(-1, 17), np.repeat(w / 4, 4))
    state = {"format": 1, "parent_sha256": PARENT, "phase_medians": phases, "global_median": typical,
             "token_mean": mean.tolist(), "token_scale": scale.tolist(), "fits": {}}
    residual = np.column_stack([data["heel_delta_mm"], force]) - baseline(data, state)
    bias = w @ residual
    centered = residual - bias
    xyz_scale = np.sqrt(w @ np.sum(centered[:, :3] ** 2, axis=1))
    force_scale = np.sqrt(w @ centered[:, 3] ** 2)
    divisors = np.array([xyz_scale] * 3 + [force_scale])
    divisors[divisors < 1e-8] = 1.
    state.update(target_mean=bias.tolist(), target_scale=divisors.tolist())
    y = centered / divisors
    for mode in READOUTS:
        x = design(mode, data, state, encoder)
        xm, xs = center_scale(x, w)
        z = (x - xm) / xs
        gram = z.T @ (w[:, None] * z) + .05 * np.eye(z.shape[1])
        rhs = z.T @ (w[:, None] * y)
        full = np.linalg.solve(gram, rhs)
        row = {"mean": xm.tolist(), "scale": xs.tolist()}
        if mode.endswith("rank2"):
            matrix = full.T @ gram @ full
            eigenvalues, eigenvectors = np.linalg.eigh((matrix + matrix.T) / 2)
            top = eigenvectors[:, -2:][:, ::-1]
            factors = full @ top
            row.update(factors=factors.tolist(), decoder=top.T.tolist(),
                       eigenvalues=eigenvalues[::-1].tolist())
            np.testing.assert_allclose((z @ factors) @ top.T, z @ (factors @ top.T), atol=1e-11)
        else:
            row["coefficients"] = full.tolist()
            independent = np.column_stack([np.linalg.solve(gram, col) for col in rhs.T])
            np.testing.assert_allclose(independent, full, atol=1e-11)
        state["fits"][mode] = row
    return state


def donors(data):
    slots = {}
    for i, key in enumerate(zip(data["person"], data["offset"])):
        slots.setdefault(key, []).append(i)
    result = np.full(len(data["person"]), -1, dtype=int)
    for rows in slots.values():
        ordered = sorted(rows, key=lambda i: data["repeat"][i])
        if len(ordered) == 1:
            continue
        if len({data["repeat"][i] for i in ordered}) != len(ordered):
            raise ValueError("Duplicate person, repeat and strike offset.")
        result[ordered] = np.roll(ordered, -1)
    return result


def predictions(data, state, encoder):
    pred = {name: batch(name, data, state, encoder) for name in (*BASELINES, *READOUTS)}
    donor = donors(data)
    eligible = donor >= 0
    wrong = np.full((len(donor), 4), np.nan)
    if eligible.any():
        swapped = slice_rows(data, eligible)
        swapped["emg_uv"] = data["emg_uv"][donor[eligible]]
        wrong[eligible] = batch(MAIN, swapped, state, encoder)
    pred["wrong_full"] = wrong
    return pred


def summarize(data, pred):
    truth = np.column_stack([data["heel_delta_mm"], data["force_n"]])
    people = sorted(set(data["person"]))
    def scope(indices, methods):
        if not indices.any():
            return {"people": 0, "repeats": 0, "windows": 0, "methods": {}}, {}
        s = slice_rows(data, indices)
        wt = weights(s)
        report = {"people": len(set(s["person"])), "repeats": len(set(zip(s["person"], s["repeat"]))),
                  "windows": len(wt), "methods": {}}
        participants = {}
        for mode in methods:
            result = pred[mode][indices]
            if mode in ("force_hold", "force_trend") and not np.isfinite(result[:, 3]).all():
                finite = indices & np.isfinite(pred[mode][:, 3])
                available, _ = scope(finite, (mode,))
                observed = available["methods"].get(mode)
                report["methods"][mode] = {"eligible_people": available["people"],
                                           "eligible_repeats": available["repeats"],
                                           "eligible_windows": available["windows"],
                                           **(observed or {"heel_error_mm": None, "force_error_n": None})}
                continue
            difference = result - truth[indices]
            losses = np.column_stack([np.linalg.norm(difference[:, :3], axis=1), abs(difference[:, 3])])
            means = wt @ losses
            bias = wt @ difference
            report["methods"][mode] = {"heel_error_mm": float(means[0]), "force_error_n": float(means[1]),
                                       "xyz_bias_mm": bias[:3].tolist(), "force_bias_n": float(bias[3]),
                                       "negative_load_forecasts": int((result[:, 3] < 0).sum())}
            participants[mode] = np.array([np.average(losses[s["person"] == p], axis=0,
                                                weights=wt[s["person"] == p]) for p in people if p in s["person"]])
        return report, participants
    report, p = scope(np.ones(len(truth), bool), [k for k in pred if k != "wrong_full"])
    controls = ("wrong_full", MOTION)
    matched, q = scope(np.isfinite(pred["wrong_full"][:, 0]), (MAIN, *controls))
    full = p[MAIN].mean(axis=0)
    wins = (p[MAIN] < p["recent_heel"]).sum(axis=0)
    adequate = ((full <= 1.02 * p[UNRESTRICTED].mean(axis=0))
                & (full < p["recent_heel"].mean(axis=0)) & (wins > len(p[MAIN]) / 2))
    joint = {"beats_baseline_people_xyz_force": wins.tolist(),
             "passes_by_heel_force": adequate.tolist(), "both_pass": bool(adequate.all())}
    emg = {"both_pass": None}
    if q:
        wins = np.logical_and.reduce([q[MAIN] < q[c] for c in controls]).sum(axis=0)
        margin = np.logical_and.reduce([q[MAIN].mean(axis=0) <= .95 * q[c].mean(axis=0) for c in controls])
        passed = margin & (wins > len(q[MAIN]) / 2)
        emg = {"beats_both_controls_people_xyz_force": wins.tolist(),
               "passes_by_heel_force": passed.tolist(), "both_pass": bool(passed.all())}
    return {"main": report, "same_phase_donor_support": matched, "rank_two_adequacy": joint, "emg_advantage": emg}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "score"))
    parser.add_argument("data", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--private", type=Path)
    args = parser.parse_args()
    with np.load(args.data, allow_pickle=False) as archive:
        data = dict(archive)
    encoder = encoders()
    if args.stage == "fit":
        groups = sorted(set(data["person"]))
        count = min(5, len(groups))
        parts = {}
        for fold in range(count):
            test = np.isin(data["person"], groups[fold::count])
            state = fit(slice_rows(data, ~test), encoder)
            if args.private:
                args.private.mkdir(exist_ok=True, parents=True)
                dump(args.private / f"fold-{fold}.json", state)
            for name, values in predictions(slice_rows(data, test), state, encoder).items():
                parts.setdefault(name, np.full((len(test), 4), np.nan))[test] = values
        dump(args.model, fit(data, encoder))
    else:
        parts = predictions(data, json.loads(args.model.read_bytes()), encoder)
    dump(args.report, summarize(data, parts))
    if args.private:
        args.private.mkdir(exist_ok=True, parents=True)
        np.savez_compressed(args.private / (args.report.stem + "-predictions.npz"), **parts)


if __name__ == "__main__":
    main()
