"""Export the six deployable methods and omit individual training examples."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent


def export(source, target):
    fit = json.loads((HERE / "fit.json").read_bytes())
    if hashlib.sha256(source.read_bytes()).hexdigest() != fit["checkpoint"]:
        raise ValueError("Expected the full original fit. Use the registered source reproduction procedure.")
    if source.resolve() == target.resolve():
        raise ValueError("Use a different path for the public checkpoint.")
    with np.load(source, allow_pickle=False) as z:
        arrays = {k:z[k] for k in z.files if k not in
                  ("point_motion.centres", "point_motion.bandwidth2", "point_motion.raw.mean", "point_motion.raw.scale")
                  and not k.startswith("point_motion.radial.")}
    cfg = json.loads(str(arrays["configuration"]))
    cfg["point_motion"]["modes"].remove("radial")
    cfg["point_motion"]["radial_control"] = "Reproduce from original training data; scores are in point-motion/results.json."
    arrays["configuration"] = np.array(json.dumps(cfg))
    np.savez_compressed(target, **arrays)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fitted", type=Path)
    parser.add_argument("public", type=Path)
    args = parser.parse_args()
    export(args.fitted, args.public)
