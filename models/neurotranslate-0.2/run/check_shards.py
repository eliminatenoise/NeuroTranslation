"""Check the token shards of one dataset before its raw downloads are deleted.

For every shard listed in shards/<dataset>/TOKENS.json: the file exists and its sha256 matches; the step
offsets agree with the recordings listed for that unit; every group array has the dataset's channel
count and feature count; every value is finite; masked entries are zero; each recording has at least
one present value. Groups whose channels differ per unit (spike units in the neural part) take their channel
list from TOKENS.json unit_channels. Writes audits/<dataset>-SHARD-CHECK.json and exits non-zero on any failure.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("dataset")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    root = Path(paths["shards"]) / a.dataset
    tok = json.loads((root / "TOKENS.json").read_text())
    by_unit = {}
    for r in tok["recordings"]:
        by_unit.setdefault(r["unit"], []).append(r)
    problems, n_steps, n_present = [], 0, 0
    for s in tok["shards"]:
        f = root / s["file"]
        if not f.exists():
            problems.append("missing " + s["file"])
            continue
        if common.sha256_file(f) != s["sha256"]:
            problems.append("sha256 " + s["file"])
        z = np.load(f)
        offs = z["rec_offsets"]
        recs = by_unit[s["unit"]]
        if list(z["rec_ids"]) != [r["rec_id"] for r in recs]:
            problems.append("recording order " + s["file"])
        if list(np.diff(offs)) != [r["steps"] for r in recs]:
            problems.append("offsets " + s["file"])
        any_present = np.zeros(int(offs[-1]), bool)
        groups = dict(tok["channels"])
        groups.update(tok.get("unit_channels", {}).get(s["unit"], {}))  # per-unit channel lists (neural part)
        for g, chans in groups.items():
            if not chans:
                continue
            F = len(tok["features"][g])
            v, m = z[g + "_val"], z[g + "_msk"]
            if v.shape != (offs[-1], len(chans), F) or m.shape != v.shape:
                problems.append("shape %s %s" % (g, s["file"]))
                continue
            if not np.isfinite(v).all():
                problems.append("non-finite %s %s" % (g, s["file"]))
            if np.any(v[~m] != 0):
                problems.append("masked non-zero %s %s" % (g, s["file"]))
            any_present |= m.any(axis=(1, 2))
        for i, r in enumerate(recs):
            if not any_present[offs[i]:offs[i + 1]].any():
                problems.append("empty recording " + r["rec_id"])
        n_steps += int(offs[-1])
        n_present += int(any_present.sum())
    out = {"dataset": a.dataset, "checked_at": common.now_iso(), "shards": len(tok["shards"]), "steps": n_steps,
           "steps_with_any_value": n_present, "problems": problems, "pass": not problems}
    common.atomic_write_json(Path(paths["audits"]) / (a.dataset + "-SHARD-CHECK.json"), out)
    print(json.dumps({k: out[k] for k in ("dataset", "shards", "steps", "pass")} | {"problems": problems[:5]}))
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
