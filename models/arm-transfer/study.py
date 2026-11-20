"""Reproduce the cued arm training or score a frozen checkpoint on the prespecified assessment people."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from extract import rows
from predict import CHANNELS, CUES, HORIZONS, METHODS, predict
from score import person_results, summary

HERE = Path(__file__).resolve().parent
PROTOCOL_SHA256 = "f550ce4a9787a00d0a372eea6f05af84c8c4c4a1c9faddbb5588c7a178877aae"
STUDY_FILES = (
    "PROTOCOL.md",
    "extract.py",
    "ofner_transfer.py",
    "predict.py",
    "predict.js",
    "fit.py",
    "score.py",
    "study.py",
)
FROZEN_OUTPUTS = (
    "model.json",
    "development.json",
    "fit-diagnostics.json",
    "training-source.json",
    "example.json",
    "parity.json",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp:
        json.dump(data, tmp, allow_nan=False, separators=(",", ":"))
        tmp.write("\n")
    os.replace(tmp.name, path)


def report(label, people, expected, audit):
    return {
        "cohort": label,
        "channels": list(CHANNELS),
        "horizons_s": list(HORIZONS),
        "cues": list(CUES),
        "n": sum(p["n"] for p in people),
        "people": people,
        "summary": summary(people, expected),
        "source_runs": audit,
    }


def make_fixtures(model, x, out):
    # Invent one stationary history near rounded componentwise medians of the fitting anchors.
    anchor = np.round(np.median(x[:, -1, :3], axis=0), 2).tolist()
    flat = [anchor + [0.0, 0.0, 0.0] for _ in range(4)]
    example = {"cue": "elbow flexion", "history": flat}
    save(out / "example.json", example)
    rng = np.random.default_rng(192)
    # A separate synthetic moving history checks time order, endpoints and cue handling.
    lo, hi = (
        np.asarray(model["scales"]["raw_min"]),
        np.asarray(model["scales"]["raw_max"]),
    )
    moving = (lo + (hi - lo) * rng.uniform(0.25, 0.75, size=(4, 6))).tolist()
    fixtures = []
    for history in (flat, moving):
        for cue in CUES:
            req = {"cue": cue, "history": history}
            fixtures.append(
                {
                    "input": req,
                    "outputs": {
                        m: predict(model, {**req, "method": m}) for m in METHODS
                    },
                }
            )
    save(out / "parity.json", fixtures)


def train(cache, out, private, threads):
    import torch
    from fit import fit

    if sha(HERE / "PROTOCOL.md") != PROTOCOL_SHA256:
        raise ValueError("The fixed protocol has changed.")
    if (out / "freeze.json").exists():
        raise ValueError("Use a new output directory to reproduce a frozen fit.")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    x, y, g, audit = rows(cache, range(1, 8))
    if sorted(set(g[:, 0])) != list(range(1, 8)):
        raise ValueError("The fit requires all seven planned people.")
    private.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(private / "training-rows.npz", x=x, y=y, g=g)
    dev = []
    fold_digests = {}
    diagnostics = {}
    for held in range(1, 8):
        use = g[:, 0] != held
        fold, diag = fit(x[use], y[use], g[use])
        path = private / f"left-out-S{held}.json"
        save(path, fold)
        fold_digests[str(held)] = sha(path)
        diagnostics[f"left_out_S{held}"] = diag
        dev.extend(person_results(fold, x[~use], y[~use], g[~use]))
    save(
        out / "development.json",
        report("leave_one_fitting_person_out", dev, range(1, 8), audit),
    )
    model, diag = fit(x, y, g)
    model["protocol_sha256"] = PROTOCOL_SHA256
    model["source_doi"] = "10.5281/zenodo.834976"
    model["derived_weights_license"] = "CC BY 4.0"
    save(out / "model.json", model)
    diagnostics["all_seven"] = diag
    save(out / "fit-diagnostics.json", diagnostics)
    save(out / "training-source.json", audit)
    make_fixtures(model, x, out)
    seal = {
        "format": "cued-arm-fit-seal-1",
        "fitting_people": list(range(1, 8)),
        "assessment_people": list(range(8, 13)),
        "rows": len(g),
        "source": {k: sha(HERE / k) for k in STUDY_FILES},
        "products": {k: sha(out / k) for k in FROZEN_OUTPUTS},
        "development_fold_checkpoints": fold_digests,
        "environment": {
            "numpy": np.__version__,
            "torch": str(torch.__version__),
            "device": "cpu",
            "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
        },
    }
    save(out / "freeze.json", seal)
    print("Frozen cohort, code and weights", sha(out / "freeze.json"), flush=True)


def assess(cache, out, seal_path, accepted):
    if sha(seal_path) != accepted:
        raise ValueError("The supplied independent freeze digest does not match.")
    seal = json.loads(seal_path.read_text())
    if seal["fitting_people"] != list(range(1, 8)) or seal["assessment_people"] != list(
        range(8, 13)
    ):
        raise ValueError("The cohort identity does not match the protocol.")
    if set(seal["source"]) != set(STUDY_FILES) or set(seal["products"]) != set(
        FROZEN_OUTPUTS
    ):
        raise ValueError("Incomplete fit and code inventory.")
    for base, items in [(HERE, seal["source"]), (seal_path.parent, seal["products"])]:
        for name, identity in items.items():
            if sha(base / name) != identity:
                raise ValueError("Frozen source or product differs: " + name)
    if out.exists():
        raise ValueError("Choose a new destination for this assessment report.")
    model = json.loads((seal_path.parent / "model.json").read_text())
    x, y, g, audit = rows(cache, range(8, 13))
    results = report(
        "frozen_unseen_people", person_results(model, x, y, g), range(8, 13), audit
    )
    results.update(
        {"freeze_sha256": accepted, "model_sha256": seal["products"]["model.json"]}
    )
    save(out, results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("train")
    t.add_argument("cache", type=Path)
    t.add_argument("output", type=Path)
    t.add_argument("fold_directory", type=Path)
    t.add_argument("--threads", type=int, default=4)
    a = sub.add_parser("assess")
    a.add_argument("cache", type=Path)
    a.add_argument("report", type=Path)
    a.add_argument("seal", type=Path)
    a.add_argument("accepted_sha256")
    opt = parser.parse_args()
    if opt.command == "train":
        train(opt.cache, opt.output, opt.fold_directory, opt.threads)
    else:
        assess(opt.cache, opt.report, opt.seal, opt.accepted_sha256)
