"""NeuroTranslate 0.0 joint alpha's public, physical-unit prediction interface."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .inference import JointModel

HERE = Path(__file__).resolve().parent
WEIGHTS = HERE / "neurotranslate.npz"
TITLE = "NeuroTranslate 0.0 joint alpha"


def examples():
    return json.loads((HERE / "example.json").read_text(encoding="utf-8"))["examples"]


class Product:
    def __init__(self, path=WEIGHTS):
        self.model = JointModel.load(Path(path))
        self.digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def catalog(self):
        result = {}
        for task, schema in self.model.tasks.items():
            entry = dict(schema)
            if schema["kind"] == "categorical":
                entry["training_label"] = schema["outputs"]
                entry["training_label_units"] = schema["output_units"]
                entry["outputs"] = ["one value for each local candidate, in input order"]
                entry["output_units"] = ["probability"]
            result[task] = entry
        return result

    def predict(self, record):
        if not isinstance(record, dict) or set(record) - {"task", "X", "valid", "domain"}:
            raise ValueError("Give a joint task, X, and an optional candidate mask named valid.")
        task = record["task"]
        if not isinstance(task, str) or task not in self.model.tasks:
            raise ValueError("Choose a listed joint task.")
        if record.get("domain", "joint_alpha") != "joint_alpha":
            raise ValueError("This record names a different model.")
        spec = self.model.tasks[task]
        raw = np.asarray(record["X"], dtype=object)
        for value in raw.flat:
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError("Use JSON numbers for readings and null for missing values.")
        x = raw.astype(float)
        if x.ndim < 2 or x.shape[-1] != len(spec["channels"]):
            raise ValueError("Input channels must match the selected task.")
        for i, unit in enumerate(spec["input_units"]):
            column = x[..., i]
            observed = column[np.isfinite(column)]
            invalid = False
            if unit in ("0 or 1", "-1 or +1"):
                allowed = (0, 1) if unit == "0 or 1" else (-1, 1)
                invalid = not np.isin(observed, allowed).all()
            elif unit == "spikes/10 ms":
                invalid = np.any(observed < 0) or np.any(observed != np.floor(observed))
            elif unit.lower().startswith("log(1+"):
                invalid = np.any(observed < 0)
            if invalid:
                raise ValueError(f"{spec['channels'][i]} takes {unit}.")
        y = self.model.predict(task, x, valid=record.get("valid"))
        if spec["kind"] == "categorical":
            outputs = [f"candidate_{index + 1}" for index in range(y.shape[1])]
            units = ["probability"] * y.shape[1]
        else:
            outputs, units = spec["outputs"], spec["output_units"]
        return {
            "model": TITLE, "checkpoint_sha256": self.digest, "task": task,
            "outputs": outputs, "output_units": units,
            "prediction": y.tolist(),
        }
