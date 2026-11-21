"""Reproduce the published worm/fish comparison from the public archives."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


MODEL = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for locally downloaded slices and derived results")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"Choose a new output directory: {output}")
    output.mkdir(parents=True)
    sources = output / "sources"
    sources.mkdir()
    for name in ("roster.json", "extract.py", "verify.py"):
        shutil.copyfile(MODEL / "sources" / name, sources / name)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    env.pop("PYTHONOPTIMIZE", None)

    def run(*args):
        subprocess.run([sys.executable, "-B", *map(str, args)], env=env, cwd=output, check=True)

    def verify_inputs(role, expected):
        run(sources / "verify.py", role)
        rows = json.loads((sources / (role + "-manifest.json")).read_text())["records"]
        supplied = {r["id"]: r["sha256"] for r in rows}
        if supplied != expected:
            raise ValueError(f"Downloaded {role} slices differ from the published study inputs")

    reference_fit = json.loads((MODEL / "fit.json").read_text())
    reference_scores = json.loads((MODEL / "results.json").read_text())
    run(sources / "extract.py", "train")
    verify_inputs("train", {a: r["input_sha256"] for a, r in reference_fit["training_sources"].items()})
    fit = output / "fit.json"
    run(MODEL / "forecast.py", "fit", "--split", MODEL / "split.json", "--files", sources / "private/train", "--out", fit)
    fit_hash = digest(fit)
    frozen = output / "frozen-fit.json"
    roster = json.loads((sources / "roster.json").read_text())
    frozen.write_text(json.dumps({
        "authorization": "held ROI slices only",
        "roster_sha256": digest(sources / "roster.json"),
        "fit_manifest_path": fit.name,
        "fit_manifest_sha256": fit_hash,
        "ids": [entry["id"] for entry in roster["held"]],
    }, indent=2) + "\n")
    run(sources / "extract.py", "held", "--approval", frozen)
    verify_inputs("held", {a: r["recording"]["input_sha256"] for a, r in reference_scores["held_animals"].items()})
    scores = output / "results.json"
    run(MODEL / "forecast.py", "evaluate", "--split", MODEL / "split.json", "--files", sources / "private/held",
        "--fit", fit, "--fit-sha256", fit_hash, "--out", scores)
    print(f"Per-fish errors and the primary comparison are in {scores}")


if __name__ == "__main__":
    main()
