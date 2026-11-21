"""Reconstruct, fit and score the released experiment from its CC0 recording."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from freeze import digest, seal_fit, verify_stage
from motor.array_hash import content_hash

PACKAGE = Path(__file__).resolve().parent
SPLITS = ("train", "validation", "within", "transfer")
SOURCES = {
    "source": ("extract.py", "selection.json", "source-seal.json",
               "releases/validation-release.json", "releases/test-release.json"),
    "cortex": ("count_model.py", "study_io.py", "train_transformer.py", "train_glm.py", "evaluate.py"),
    "joint": ("portable.py", "fit.py", "study.py", "PROTOCOL.md"),
    "scores": ("metrics.py", "score.py"),
}


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("Supply a new or empty reproduction directory.")
    def copy(src, dst):
        target = directory / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PACKAGE / src, target)
    for part, names in SOURCES.items():
        for name in names:
            copy(f"{part}/{name}", f"{part}/{name}")
    for name in ("array_hash.py", "forecast.py", "model.py", "train.py"):
        copy("motor/" + name, "motor/product/" + name)
    for name in ("assemble_folds.py", "evaluate.py"):
        copy("motor/" + name, "motor/" + name)
    copy("freeze.py", "freeze.py")


def compare(expected, actual, trail=""):
    """Report scientific disagreement, including coverage, gate decisions and nulls."""
    import math
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError("Result fields differ at " + trail)
        for key in expected:
            compare(expected[key], actual[key], trail + "/" + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError("Result dimensions differ at " + trail)
        for i, v in enumerate(expected):
            compare(v, actual[i], f"{trail}/{i}")
    elif type(expected) is float:
        if not isinstance(actual, (float, int)) or not math.isclose(expected, actual, abs_tol=2e-5, rel_tol=2e-5):
            raise ValueError(f"Numerical difference at {trail}: expected {expected}, got {actual}")
    elif actual != expected:
        raise ValueError(f"Different value at {trail}: expected {expected}, got {actual}")


def reproduce(args):
    work = args.out.resolve()
    mat = args.mat.resolve(strict=True)
    prepare(work)
    torch_python = str(args.torch_python.absolute()) if args.torch_python else sys.executable
    def run(name, *argv, torch=False, blas=1, omp=1):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS=str(blas),
                   OMP_NUM_THREADS=str(omp), MKL_NUM_THREADS=str(omp), VECLIB_MAXIMUM_THREADS=str(blas))
        print(f"Running {name}", *(str(v) for v in argv), flush=True)
        subprocess.run([torch_python if torch else sys.executable, "-B", name, *map(str, argv)],
                       cwd=work, env=env, check=True)
    fingerprints = json.loads((PACKAGE / "results/source-fingerprints.json").read_bytes())
    def extract(split):
        run("source/extract.py", split, "--mat", mat, "--output", "source", "--releases", "source/releases")
        if content_hash(work / "source" / (split + ".npz")) != fingerprints[split]["sha256_contents"]:
            raise ValueError("Reconstructed arrays differ from the released source: " + split)
    def evaluate(split):
        if split != "train":
            run("motor/evaluate.py", split, torch=True)
        run("cortex/evaluate.py", split)
        run("joint/study.py", f"source/{split}.npz", "joint/weights", f"joint/{split}", "--with-native", torch=True)
    extract("train")
    for fold in range(1, 6):
        run("motor/product/train.py", "source/train.npz", f"motor/folds/fold-{fold}",
            "--fold", fold, "--threads", 1, "--device", "cpu", torch=True)
    run("motor/assemble_folds.py", "oof")
    run("motor/assemble_folds.py", "refit")
    run("cortex/train_transformer.py", "--device", "cpu", "--threads", 2, torch=True, omp=2)
    run("cortex/train_glm.py", blas=2)
    run("joint/fit.py", "source/train.npz", "joint/weights", "--device", "cpu", "--threads", 1, torch=True)
    seal_fit(work)
    evaluate("train")
    run("scores/score.py", "train")
    for stage, splits in (("validation", ["validation"]), ("test", ["within", "transfer"])):
        verify_stage(work, stage)
        for split in splits:
            extract(split)
            evaluate(split)
        run("scores/score.py", stage)
    for split in SPLITS:
        primary = json.loads((work / "scores" / split / "summary.json").read_bytes())
        compare(json.loads((PACKAGE / "results" / f"{split}.json").read_bytes()), primary, split)
        joint = json.loads((work / "joint" / split / "summary.json").read_bytes())
        for key in ("parameters_lock_sha256", "native_numpy_max_by_seed"):
            joint.pop(key)
        reference = json.loads((PACKAGE / "results" / f"joint-{split}.json").read_bytes())
        if (reference.pop("source") != fingerprints[split]["sha256_compressed"]
                or joint.pop("source") != digest(work / "source" / (split + ".npz"))):
            raise ValueError("Joint results do not identify their source archive: " + split)
        compare(reference, joint, "joint/" + split)
    print("Reproduced the four split summaries, secondary comparisons and all original decision rules.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mat", type=Path, required=True, help="The checksum-verified C_20170907_TRT_TD.mat")
    parser.add_argument("--out", type=Path, required=True, help="New or empty output directory")
    parser.add_argument("--torch-python", type=Path, help="Optional separate Python executable with NumPy and PyTorch")
    reproduce(parser.parse_args())
