"""Compare the stored Ofner shards with a fresh run of the reader on every source file that is at hand.

  python check_ofner_kin.py --paths PATHS.json [--workers 8] [--before DIR]

For each training run whose GDF file is on disk with the recorded digest (runs 1-3 locally; runs 4-10 only
while a downloaded copy exists), the reader's tokens of that run (datasets/ofner.py: field features, and arm
and glove tokens on the file's times delayed by one whole step) are written through the shard writer and
compared, array by array, with that recording's slice of the stored shard. The arm and glove arrays must be
equal bit for bit, as must the field arrays and masks. Runs without a file at hand are listed, not checked.
With --before (a copy of the shards from before delay_ofner_kin.py), the field arrays of every recording are
also compared with that copy, and the arm and glove arrays with the copy delayed by one step.
Writes audits/ofner-KIN-DELAY-CHECK.json and exits non-zero on any difference. No recording value is printed.
"""
import argparse
import hashlib
import importlib
import json
import multiprocessing as mp
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import common  # noqa: E402
import neural_common as nc  # noqa: E402

_S = {}


def _init(paths, shared):
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    _S["mod"] = importlib.import_module("datasets.ofner")
    _S["paths"], _S["shared"] = paths, shared


def _at_hand(it):
    p = Path(it["path"])
    if not p.exists():
        return False
    if "sha256" in it:
        return common.sha256_file(p) == it["sha256"]
    if p.stat().st_size != it["bytes"]:
        return False
    h = hashlib.md5()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest() == it["md5"]


def _work(job):
    unit, it = job
    mod, paths, shared = _S["mod"], _S["paths"], _S["shared"]
    rid = "%s_run%02d" % (unit, it["run"])
    if not _at_hand(it):
        return {"rec_id": rid, "checked": False}
    recs, metas, checks, _ = mod.process_unit(paths, unit, [it], shared)
    counts = {g: len(c) for g, c in shared.items()}
    with tempfile.TemporaryDirectory(dir=paths["raw"]) as d:
        nc.write_shard(Path(d) / "one.npz", unit, recs, counts)
        with np.load(Path(d) / "one.npz") as z:
            fresh = {k: z[k] for k in z.files}
    with np.load(Path(paths["shards"]) / mod.DATASET / (unit + ".npz")) as z:
        ids = list(z["rec_ids"])
        i = ids.index(rid)
        lo, hi = int(z["rec_offsets"][i]), int(z["rec_offsets"][i + 1])
        stored = {k: z[k][lo:hi] for k in z.files if k.endswith("_val") or k.endswith("_msk")}
    out = {"rec_id": rid, "checked": True, "steps": hi - lo, "steps_equal": recs[0].n_steps == hi - lo}
    for k, v in stored.items():
        out[k + "_equal"] = bool(v.shape == fresh[k].shape and np.array_equal(v, fresh[k]))
    out["first_kin_step_absent"] = bool(not stored["kin_msk"][:mod.KIN_DELAY_STEPS].any())
    out["pass"] = all(v for k, v in out.items() if k.endswith("_equal")) and out["first_kin_step_absent"]
    return out


def compare_with_copy(paths, mod, before):
    """Every recording: field arrays unchanged and kin arrays equal to the copy delayed by the reader's delay."""
    tok = json.loads((Path(paths["shards"]) / mod.DATASET / "TOKENS.json").read_text())
    rows = []
    for s in tok["shards"]:
        with np.load(Path(before) / s["file"]) as z0, np.load(Path(paths["shards"]) / mod.DATASET / s["file"]) as z1:
            offs = z1["rec_offsets"]
            same_layout = bool(np.array_equal(z0["rec_offsets"], offs) and list(z0["rec_ids"]) == list(z1["rec_ids"]))
            field = bool(np.array_equal(z0["field_val"], z1["field_val"]) and np.array_equal(z0["field_msk"], z1["field_msk"]))
            kv0, km0, kv1, km1 = z0["kin_val"], z0["kin_msk"], z1["kin_val"], z1["kin_msk"]
            kin = True
            for i in range(len(offs) - 1):
                lo, hi = int(offs[i]), int(offs[i + 1])
                v, m = common.delay_steps(kv0[lo:hi], km0[lo:hi], mod.KIN_DELAY_STEPS)
                kin &= bool(np.array_equal(v, kv1[lo:hi]) and np.array_equal(m, km1[lo:hi]))
            rows.append({"shard": s["file"], "recordings": len(offs) - 1, "same_layout": same_layout,
                         "field_unchanged": field, "kin_equals_copy_delayed": kin,
                         "pass": same_layout and field and kin})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--before")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    mod = importlib.import_module("datasets.ofner")
    shared = mod.channels(paths)
    jobs = [(u, it) for u, items in mod.jobs(paths, mod.roster(paths)["units"]) for it in items]
    ctx = mp.get_context("fork")
    with ctx.Pool(max(1, min(a.workers, 8)), initializer=_init, initargs=(paths, shared)) as pool:
        rows = pool.map(_work, jobs, chunksize=1)
    checked = [r for r in rows if r["checked"]]
    out = {"dataset": mod.DATASET, "checked_at": common.now_iso(), "kin_delay_steps": mod.KIN_DELAY_STEPS,
           "recordings": len(rows), "recordings_checked_against_source_files": len(checked),
           "recordings_without_a_source_file_at_hand": sorted(r["rec_id"] for r in rows if not r["checked"]),
           "rows": checked, "pass": bool(checked) and all(r["pass"] for r in checked)}
    if a.before:
        out["against_copy_from_before_the_delay"] = compare_with_copy(paths, mod, a.before)
        out["pass"] = out["pass"] and all(r["pass"] for r in out["against_copy_from_before_the_delay"])
    common.atomic_write_json(Path(paths["audits"]) / (mod.DATASET + "-KIN-DELAY-CHECK.json"), out)
    print(json.dumps({k: out[k] for k in ("recordings", "recordings_checked_against_source_files", "pass")} |
                     {"failed": [r["rec_id"] for r in checked if not r["pass"]][:10],
                      "copy": [r["pass"] for r in out.get("against_copy_from_before_the_delay", [])]}))
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
