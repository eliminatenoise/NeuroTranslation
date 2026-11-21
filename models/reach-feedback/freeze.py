"""Bind held evaluation to the scientific software, weights and actual source releases."""
from hashlib import file_digest
import json
from pathlib import Path

def digest(path):
    with path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def seal_fit(work):
    sources = sorted(p for p in work.rglob("*.py") if p.is_file())
    targets = [work / "source/train.npz", work / "motor/oof.npz"]
    for folder, pattern, count in (("motor/product/weights", "*.npz", 20),
                                   ("cortex/weights", "*.npz", 29),
                                   ("joint/weights", "*.json", 16)):
        files = sorted((work / folder).glob(pattern))
        if len(files) != count:
            raise ValueError(f"Expected {count} fitted files in {folder}, found {len(files)}")
        targets.extend(files)
    targets.extend(work / "source/releases" / (s + "-release.json") for s in ("validation", "test"))
    record = {p.relative_to(work).as_posix(): digest(p) for p in sources + targets}
    (work / "fitted-inputs.json").write_text(json.dumps(record, indent=2) + "\n")


def verify_stage(work, stage):
    if stage == "train":
        return None
    expected = {"validation": ["validation"], "test": ["within", "transfer"]}[stage]
    receipt = work / "source/releases" / (stage + "-release.json")
    record = json.loads(receipt.read_text())
    if (record["authorized"] is not True or record["stage"] != stage or record["splits"] != expected
            or record["source_seal_sha256"] != digest(work / "source/source-seal.json")):
        raise ValueError("The published release does not cover this source and stage")
    for rel, value in json.loads((work / "fitted-inputs.json").read_text()).items():
        if digest(work / rel) != value:
            raise ValueError("A fitted input or method changed after training: " + rel)
    return digest(receipt)
