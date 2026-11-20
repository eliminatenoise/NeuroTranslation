"""Keep cohort-level results and coverage. Leave individual summaries in the local workspace."""
import argparse
import json
from pathlib import Path

import numpy as np


def cohort(value):
    if not isinstance(value, dict):
        return value
    result = {}
    for key, child in value.items():
        if key == "trials_by_walker":
            trials = [t for p in child for t in p["trials"]]
            counts = [t["possible_cutoffs"] for t in trials]
            result["trial_cutoff_range"] = [min(counts),max(counts)]
        elif key == "by_walker":
            if child and "by_landmark_mm" in child[0]:
                person = np.array([p["mean_mm"] for p in child],dtype=float)
                finite = person[np.isfinite(person)]
                result["walker_mean_range_mm"] = [float(finite.min()),float(finite.max())] if len(finite) else []
                result["walker_mean_sd_mm"] = float(np.std(finite,ddof=1)) if len(finite)>1 else None
                counts = [p["cutoffs"] for p in child if p["cutoffs"]]
                result["cutoff_range_per_scored_walker"] = [min(counts),max(counts)] if counts else []
        else:
            result[key] = cohort(child)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("full",type=Path)
    p.add_argument("out",type=Path)
    args = p.parse_args()
    args.out.write_text(json.dumps(cohort(json.loads(args.full.read_bytes())),indent=2,allow_nan=False)+"\n")
