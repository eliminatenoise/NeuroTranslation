"""Delay the Ofner arm and glove tokens by one whole 20 ms step in the stored shards. No source file is read.

  python delay_ofner_kin.py --paths PATHS.json [--keep DIR]

Why: the first tokenisation placed 64 Hz reading j at j / 64 s. A reading may have been acquired up to 7 ticks of
the 512 Hz clock (13.7 ms) later, so a token could hold a value from just after its step. Placing each reading
at the end of its 8-tick block cannot be done from the shards: in a step that held two readings, the earlier one
would then be the step's last, and the shards keep only the last reading of each step and its change. A delay of
one whole step can be done exactly: the token of step k becomes the token of step k - 1 (both features, so
'change' still equals the difference of two consecutive 'last' values), the first step of each recording holds
nothing and the last token of each recording is dropped. datasets/ofner.py now tokenises the same way, so a
fresh run of the reader gives the same arrays (check_ofner_kin.py compares them on the source files at hand).

Every other array of a shard is written back unchanged. The counts of each recording, TOKENS.json, the audit
file and the manifest part are rebuilt by the same code as a fresh run (p2_neural.finish). The script refuses
to run on shards that already record the delay. --keep copies the shards and TOKENS.json there first.
"""
import argparse
import importlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import common  # noqa: E402
import neural_common as nc  # noqa: E402
import p2_neural  # noqa: E402

GROUP = "kin"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--keep", help="folder that receives a copy of the shards and TOKENS.json before the change")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    mod = importlib.import_module("datasets.ofner")
    ds, n = mod.DATASET, mod.KIN_DELAY_STEPS
    root = Path(paths["shards"]) / ds
    tok = json.loads((root / "TOKENS.json").read_text())
    if tok.get("stream_delays"):
        sys.exit("these shards already record a stream delay: %s" % json.dumps(tok["stream_delays"]))
    t0 = time.time()
    head = common.protocol_head(paths)
    proto, alloc = common.protocol_files(paths)
    audit, ros, inner_val = p2_neural.role_audit(mod, paths, alloc, head)
    if not audit["all_units_pass"]:
        sys.exit("role audit failed for %s" % ds)
    old_audit = json.loads((Path(paths["audits"]) / (ds + "-AUDIT.json")).read_text())
    old_part = json.loads((Path(paths["manifest_parts"]) / (ds + ".json")).read_text())
    shared = mod.channels(paths)
    kinds = {g: nc.kinds_of(c) for g, c in shared.items()}
    by_unit = {}
    for m in tok["recordings"]:
        by_unit.setdefault(m["unit"], []).append({k: v for k, v in m.items() if k != "unit"})
    assert sorted(by_unit) == sorted(ros["units"]) == sorted(s["unit"] for s in tok["shards"])

    for s in tok["shards"]:  # every shard is the one TOKENS.json lists before anything is changed
        if common.sha256_file(root / s["file"]) != s["sha256"]:
            sys.exit("shard %s differs from TOKENS.json" % s["file"])
    if a.keep:
        keep = Path(a.keep)
        keep.mkdir(parents=True, exist_ok=False)
        for name in [s["file"] for s in tok["shards"]] + ["TOKENS.json"]:
            shutil.copy2(root / name, keep / name)

    results, before = [], []
    for s in tok["shards"]:
        f = root / s["file"]
        t1 = time.time()
        with np.load(f) as z:
            arrays = {k: z[k] for k in z.files}
        offs = arrays["rec_offsets"]
        metas = by_unit[s["unit"]]
        assert list(arrays["rec_ids"]) == [m["rec_id"] for m in metas]
        assert list(np.diff(offs)) == [m["steps"] for m in metas]
        val, msk = arrays[GROUP + "_val"], arrays[GROUP + "_msk"]
        new_v, new_m = np.zeros_like(val), np.zeros_like(msk)
        for i in range(len(metas)):
            lo, hi = int(offs[i]), int(offs[i + 1])
            new_v[lo:hi], new_m[lo:hi] = common.delay_steps(val[lo:hi], msk[lo:hi], n)
        assert not np.any(new_v[~new_m] != 0)
        arrays[GROUP + "_val"], arrays[GROUP + "_msk"] = new_v, new_m
        for i, m in enumerate(metas):
            lo, hi = int(offs[i]), int(offs[i + 1])
            rec = nc.Rec(m["rec_id"], s["unit"], hi - lo)
            for g in shared:
                rec.groups[g] = (arrays[g + "_val"][lo:hi], arrays[g + "_msk"][lo:hi])
            counts = nc.count_rec(rec, kinds)
            assert counts["steps"] == m["steps"] and counts["windows"] == m["windows"]
            m.update(counts)
        tmp = f.with_name(f.name + ".tmp.npz")
        np.savez_compressed(tmp, **arrays)
        os.replace(tmp, f)
        before.append({"unit": s["unit"], "file": s["file"], "sha256": s["sha256"], "bytes": s["bytes"]})
        results.append({"unit": s["unit"], "recordings": metas, "dropped_recordings": [],
                        "checks": old_audit["unit_checks"][s["unit"]], "float16_error": {}, "unit_channels": {},
                        "shard": f.name, "shard_sha256": common.sha256_file(f), "shard_bytes": f.stat().st_size,
                        "seconds": round(time.time() - t1, 2)})
        print(json.dumps({"unit": s["unit"], "recordings": len(metas), "seconds": results[-1]["seconds"]}), flush=True)

    correction = {
        "what": "the %s tokens of every recording were delayed by %d whole 20 ms step(s) in the stored shards; no "
                "source file was read; every other array was written back unchanged" % (GROUP, n),
        "script": "delay_ofner_kin.py", "done_at": common.now_iso(),
        "tokenised_first_at_protocol_head": tok.get("protocol_head"),
        "shards_before": before,
        "storage_error_summary": "carried over from the first tokenisation (the field arrays are unchanged)"}
    results.sort(key=lambda r: r["unit"])
    p2_neural.finish(mod, paths, results, audit, ros, inner_val, shared, head, t0,
                     float16=old_part["tokens"]["float16_rms_error_over_channel_sd_max"], correction=correction)


if __name__ == "__main__":
    main()
