"""Relative study paths and verified local checkpoints."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
RESULT = Path(os.environ["WRIST_STUDY_WORK"]).resolve()
ROWS = RESULT / "people"
MODELS = RESULT / "models"
SOURCE = HERE / "study.json"
PEOPLE = tuple(row["subject"] for row in json.loads(SOURCE.read_text())["archives"])


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def seal(path, value, archive=False):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            if archive:
                np.savez(f, **value)
            else:
                f.write((json.dumps(value, indent=2, allow_nan=False) + "\n").encode())
            f.flush()
            os.fsync(f.fileno())
            os.link(tmp, path)
        finally:
            tmp.unlink()


def read_npz(path):
    with np.load(path, allow_pickle=False) as file:
        return dict(file)


def people_table(indices):
    indices = tuple(indices)
    if not indices or len(set(indices)) != len(indices) or not set(indices) <= set(range(len(PEOPLE))):
        raise ValueError("Unadmitted person index")
    receipt = json.loads((RESULT / "extraction.json").read_text())
    if receipt["freeze_sha256"] != digest(SOURCE):
        raise ValueError("Extraction receipt refers to a different freeze")
    parts = []
    for i in sorted(indices):
        path = ROWS / (PEOPLE[i] + ".npz")
        if digest(path) != receipt["outputs"][path.name]:
            raise ValueError("Person table failed source seal")
        part = read_npz(path)
        if not np.all(part["person"] == i):
            raise ValueError("Person table identity mismatch")
        parts.append(part)
    return {key: np.concatenate([part[key] for part in parts]) for key in parts[0]}
