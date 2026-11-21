"""Download a selected licensed assay, generate private measurements and pack them; original adapter code CC0."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
ASSAYS = ("macaque", "human", "rat", "calcium", "landmark")


def run(script, *args):
    subprocess.run([sys.executable, "-B", str(script), *map(str, args)], check=True)


def data_reader(path):
    spec = importlib.util.spec_from_file_location("optical_source_reader", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def acquire(assay, stage, cache):
    folder = cache / assay
    folder.mkdir(parents=True, exist_ok=True)
    if assay == "macaque":
        src = SOURCES / "macaque"
        name = "C_20170907_TRT_TD.mat" if stage == "train" else "C_20170914_TRT_TD.mat"
        if not (folder / name).exists():
            run(src / "fetch.py", stage, folder)
        run(src / "reconstruct.py", stage, "--mat", folder / name, "--output", folder)
    elif assay == "human":
        name = "development" if stage == "train" else "assessment"
        src = SOURCES / "human_balance"
        run(src / "acquire.py", name, folder)
        run(src / "extract.py", name, folder)
        run(src / "verify.py", name, folder)
        pair_cache = folder / "paired"
        pair_cache.mkdir(exist_ok=True)
        run(
            SOURCES / "human_pair" / "prepare.py",
            name,
            folder,
            pair_cache / (name + ".npz"),
        )
        folder = pair_cache
    elif assay == "rat":
        src = SOURCES / "rat"
        hashes = json.loads((src / "primary-packets.json").read_text())
        base = (
            "https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/"
            "3e43795adeb6c33b8302e952f45af03be5a71fb1/benchmarks/wtrack-neural-motion/recording/pairs"
        )
        part = "train" if stage == "train" else "test"
        (folder / part).mkdir(exist_ok=True)
        for i in range(55, 79) if stage == "train" else range(80, 90):
            name = f"trial-{i:03d}.npz"
            dest = folder / part / name
            if not dest.exists():
                with urlopen(f"{base}/{part}/{name}", timeout=60) as res:
                    payload = res.read()
                if hashlib.sha256(payload).hexdigest() != hashes[str(i)]:
                    raise ValueError("Source packet digest")
                dest.write_bytes(payload)
        if stage == "held":
            run(src / "get_inputs.py", "er1", folder / "er1")
    elif assay == "calcium":
        src = SOURCES / "calcium"
        reader = data_reader(src / "extract.py")
        roster = json.loads((src / "roster.json").read_bytes())
        if reader.sha((src / "roster.json").read_bytes()) != reader.SEAL:
            raise ValueError("Source roster digest")
        target = folder / stage
        target.mkdir(exist_ok=True)
        for entry in roster[stage]:
            reader.extract(entry, target)
    else:
        src = SOURCES / "landmark"
        records = json.loads((src / "source-inventory.json").read_text())["groups"]
        part = "train" if stage == "train" else "test"
        groups = [g["id"] for g in records if g["split"] == part]
        stage_folder = folder / part
        if not (stage_folder / "manifest.json").exists():
            run(
                src / "fetch_tracks.py",
                "--output",
                stage_folder,
                "--cache",
                folder / "raw",
                *[x for group in groups for x in ("--group", group)],
            )
        folder = stage_folder
    return folder


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("train", "held"))
    p.add_argument("--assay", choices=(*ASSAYS, "all"), default="all")
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--frozen-model",
        type=Path,
        help="Existing frozen checkpoint for a held evaluation",
    )
    args = p.parse_args()
    if args.stage == "held" and (
        not args.frozen_model or not args.frozen_model.is_file()
    ):
        p.error(
            "Supply --frozen-model for held replay after development selection and fit."
        )
    for assay in ASSAYS if args.assay == "all" else [args.assay]:
        inputs = acquire(assay, args.stage, args.cache.resolve())
        run(
            HERE / "pack.py",
            assay,
            args.stage,
            "--inputs",
            inputs,
            "--out",
            args.out.resolve(),
        )
