"""Reproduce the pooled eight-task forecast and its matched touch-only control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

# The original fit used one process, one OpenBLAS thread and two PyTorch CPU threads.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
import numpy as np
import torch

VERSION = "shared-temporal-touch-candidate-1"
NEW = "human_touch_afferent"
HERE = Path(__file__).resolve().parent
SOURCES = {
    "train.py": "b300c41913f9f28a3901912abff1536cbb0413e0ab6afaf0b5bdca1a6d2ae7df",
    "network.py": "6313cfce4716c9eaf1ee4105e87d0f5e7a209827c8327b7dae89d38360a18666",
    "inference.py": "f29848baa787581a979a5d9f3d5eca3f1fd894bfb2e40125a9b6a11abf88b1d8",
    "protocol.json": "522c16a08533a6eb870cef4be3465847c88475a34563f26b394df7374913bf45",
}
PRIOR = "f58dec8857015d84962aeb00259badf71b42d9bf7105cec35851a87826ed57d6"


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def training_content_digest(cases):
    """Hash the ordered model inputs, targets, group labels and candidate masks."""
    value = hashlib.sha256()
    for name in ("x", "y", "group", "valid"):
        array = getattr(cases, name)
        if array is None:
            continue
        array = np.ascontiguousarray(array)
        value.update(json.dumps([name, array.dtype.str, list(array.shape)], separators=(",", ":")).encode())
        value.update(memoryview(array).cast("B"))
    return value.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path, help="JSON manifest with seven or eight tasks; train paths are relative to the manifest")
    p.add_argument("output", type=Path, help="New or empty directory for the fitted checkpoint files")
    p.add_argument("--seven-dir", type=Path, default=HERE.parents[1],
                   help="Released seven-task model directory")
    p.add_argument("--touch-train", type=Path, help="Touch NPZ built from the public recordings; required for a seven-task input manifest")
    p.add_argument("--mode", choices=("both", "eight", "touch", "seven"), default="both")
    args = p.parse_args()
    for name, expected in {**SOURCES, "neurotranslate.npz": PRIOR}.items():
        if digest(args.seven_dir / name) != expected:
            raise ValueError("Unexpected seven-task dependency: " + name)
    sys.path.insert(0, str(args.seven_dir.resolve()))
    import train
    from network import Joint
    from inference import JointModel
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)

    prior = JointModel.load(args.seven_dir / "neurotranslate.npz")
    original = json.loads((args.seven_dir / "training-summary.json").read_text())
    spec = json.loads(args.manifest.read_text())["tasks"]
    tasks = [*sorted(prior.tasks), NEW]
    if args.touch_train is not None:
        touch_schema = json.loads((HERE / "touch-schema.json").read_text())
        spec[NEW] = {**touch_schema, "splits": {"train": str(args.touch_train.resolve())}}
    if set(spec) != set(tasks):
        raise ValueError("Expected the seven released tasks plus human_touch_afferent")
    schemas, cases, scales = {}, {}, {}
    training_hashes = json.loads((HERE / "fit-results.json").read_text())["training_content_sha256"]
    for t in tasks:
        src = spec[t]
        schemas[t] = {k: src[k] for k in train.SCHEMA_FIELDS if k in src}
        if t == "human_leg_emg":
            schemas[t]["output_bound"] = "nonnegative"
        if t in prior.tasks and schemas[t] != prior.tasks[t]:
            raise ValueError("Earlier task definition differs for " + t)
        cases[t] = train.Cases(args.manifest.parent, src, "train")
        if training_content_digest(cases[t]) != training_hashes[t]:
            raise ValueError("Ordered model inputs, targets, groups or mask differ for " + t)
        scales[t] = cases[t].stats()
    if cases[NEW].kind != "count" or cases[NEW].x.shape[1:] != (10, 5) or len(cases[NEW].groups) != 7:
        raise ValueError("Expected pooled touch counts and ten five-channel bins from seven training people")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Use a new or empty output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(431)
    initial = Joint(schemas, {"width": 32, "heads": 4, "depth": 1, "ff_width": 64})
    if train.weights_hash(initial.trunk.named_parameters()) != original["initial_shared_hash"]:
        raise ValueError("Seven-task initialization differs")
    recipes = {"seven": (tasks[:-1], "seven-task.npz"), "eight": (tasks, "eight-task.npz"),
               "touch": ([NEW], "touch-only.npz")}
    modes = ("eight", "touch") if args.mode == "both" else (args.mode,)
    for mode in modes:
        selected, name = recipes[mode]
        model = Joint({k: schemas[k] for k in selected}, initial.architecture)
        model.load_state_dict({k: initial.state_dict()[k] for k in model.state_dict()})
        train.train(model, selected, cases, scales, 1920, True, 0.0015, 431, "warmup_cosine")
        train.PLAN["version"] = original.get("version", "shared-temporal-alpha-1") if mode == "seven" else VERSION
        path = args.output / name
        train.save(model, {t: schemas[t] for t in selected}, {t: scales[t] for t in selected}, path)
        print(name, digest(path), flush=True)


if __name__ == "__main__":
    main()
