"""Apply sealed all-original movement models to an authorized numerical partition."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "product"))
from forecast import ARMS, SEEDS, history_tokens, load_model, predict, standardized
from model import ReachTransformer, native_forecast
from train import configure, IDENTITIES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def released(split):
    sys.path.insert(0, str(HERE.parent))
    from freeze import verify_stage
    return verify_stage(HERE.parent, "validation" if split == "validation" else "test")


def evaluate(split):
    start = time.perf_counter()
    gate = released(split)
    configure(1)
    path = HERE.parent / "source" / (split + ".npz")
    # Only genuine pre-cutoff history and row identity enter inference.
    with np.load(path, allow_pickle=False) as source:
        output = {k: source[k] for k in IDENTITIES}
        raw = history_tokens(source["pose"], source["spikes"], source["cue"])
        guide = source["unit_guide"]
    output["seeds"] = np.array(SEEDS)
    weights = HERE / "product/weights"
    errors = {}
    for arm in ARMS:
        predictions = []
        for kind in (*SEEDS, "ridge"):
            name = f"{arm}-{kind}.npz"
            p = load_model(weights / name)
            est = predict(raw, p, guide)
            if kind == "ridge":
                x = torch.from_numpy(standardized(raw, p).reshape(len(raw), 840))
                native = (x @ torch.from_numpy(p["coef"]) + torch.from_numpy(p["bias"])).numpy().reshape(-1, 10, 8)
                output["ridge_" + arm] = est
            else:
                net = ReachTransformer()
                net.load_state_dict({k: torch.from_numpy(p[k]) for k in net.state_dict()})
                net.eval()
                native = native_forecast(net, raw, p, "cpu")
                predictions.append(est)
            err = float(np.max(np.abs((est - p["y_mean"]) / p["y_scale"] - native)))
            if not np.isfinite(err) or err >= .0005:
                raise ValueError(f"{name} failed frozen numerical portability threshold: {err}")
            errors[name] = err
        output[arm] = np.stack(predictions)
    out = HERE / (split + "-predictions.npz")
    tmp = out.with_suffix(".tmp")
    with tmp.open("xb") as f:
        np.savez_compressed(f, **output)
    if out.exists():
        raise FileExistsError(out)
    tmp.rename(out)
    result = dict(split=split, gate_sha256=gate, input_sha256=sha(path), predictions_sha256=sha(out),
                  rows=len(raw), normalized_port_max_abs_by_weight=errors,
                  elapsed_seconds=time.perf_counter() - start)
    with (HERE / "folds" / (split + "-prediction.json")).open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(split, result["rows"], result["predictions_sha256"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("split", choices=("validation", "within", "transfer"))
    evaluate(p.parse_args().split)
