"""Write an attributed observed training prefix and outcome beside its forecast."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from forecast import HERE, STEPS, forecast, load_weights
from prepare import COHORT, origins, read_sites


def example(row, src, weights):
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    if sha != row["sha256"]:
        raise ValueError("Training source hash mismatch")
    sites, meta = read_sites(src)
    for t, hist, future in origins(sites, meta):
        if hist is None or future is None:
            continue
        history_t = (t + np.arange(-10, 1)) / 20
        frames = meta["firstFrame"] + (t + np.arange(-10, 13)) * (meta["rateHz"] // 20)
        return {"action": row["action"], "source": {"database": "CMU Graphics Lab Motion Capture Database", "role": "recorded training example", "id": row["id"], "sha256": sha, "url": row["url"], "terms": "https://mocap.cs.cmu.edu/", "rateHz": meta["rateHz"], "firstRecordedFrame": meta["firstFrame"], "historyFrames": frames[:11].tolist(), "outcomeFrames": frames[11:].tolist(), "clock": "seconds since first recorded frame", "timeOriginFrame": int(frames[10])}, "history": {"timesS": history_t.tolist(), "positionsMm": hist.tolist()}, "observedFuture": {"timesS": (t/20 + STEPS).tolist(), "positionsMm": future.tolist(), "pelvisMm": future[:, 2:4].mean(axis=1).tolist()}, "forecast": forecast(hist, history_t, row["action"], weights)}
    raise ValueError("No fully observed example")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source_folder", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    weights = load_weights(HERE / "conditional.json")
    for uid in ("07_01", "09_01"):
        row = next(r for r in COHORT if r["id"] == uid and r["split"] == "train")
        val = example(row, args.source_folder / (uid + ".c3d"), weights)
        (args.output / ("example-" + row["action"] + ".json")).write_text(json.dumps(val, separators=(",", ":"), allow_nan=False) + "\n")
