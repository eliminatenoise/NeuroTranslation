"""Convert selected original C3Ds to strictly observed 20 Hz gait histories."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from forecast import HERE, encode, observed_residual

COHORT = json.loads((HERE / "cohort.json").read_text())["rows"]
SCHEMA = json.loads((HERE / "schema.json").read_text())


def read_sites(path):
    import ezc3d
    c = ezc3d.c3d(str(path))
    h, p = c["header"]["points"], c["parameters"]["POINT"]
    rate = h["frame_rate"]
    if rate not in (60, 120) or p["UNITS"]["value"] != ["mm"]:
        raise ValueError("Unsupported native clock or units")
    if p.get("Y_SCREEN", {}).get("value") not in (None, [], ["+Z"]):
        raise ValueError("Incompatible vertical axis")
    labels = []
    for i in range(1, 100):
        key = "LABELS" if i == 1 else f"LABELS{i}"
        if key not in p:
            break
        labels.extend(x.strip().split(":")[-1] for x in p[key]["value"])
    names = sorted({n for group in SCHEMA["sites"] for n in group})
    if len(labels) != h["size"] or any(labels.count(n) != 1 for n in names):
        raise ValueError("Missing or ambiguous site names")
    idx = [labels.index(n) for n in names]
    points = c["data"]["points"][:3, idx].transpose(2, 1, 0).copy()
    residual = c["data"]["meta_points"]["residuals"][0, idx].T
    points[~(np.isfinite(residual) & (residual >= 0))] = np.nan
    sites = np.stack([points[:, [names.index(n) for n in group]].mean(1) for group in SCHEMA["sites"]], axis=1)
    if len(sites) != h["last_frame"] - h["first_frame"] + 1:
        raise ValueError("Frame count disagrees with source header")
    return sites, {"rateHz": int(rate), "firstFrame": int(h["first_frame"] + 1), "lastFrame": int(h["last_frame"] + 1), "sourceFrameConvention": "C3D point frame numbers, first frame is ezc3d zero-based header + 1"}


def origins(sites, meta):
    """Yield deterministic cutoffs, eligible histories and optional observed outcomes."""
    grid = sites[::meta["rateHz"] // 20]
    for t in range(10, len(grid), 2):
        hist = grid[t-10:t+1]
        try:
            encode(hist)
        except ValueError:
            yield t, None, None
            continue
        fut = grid[t+1:t+13]
        yield t, hist, fut if len(fut) == 12 and np.isfinite(fut).all() else None


def prepare(split, rawdir, outdir, extra_hashes=None):
    paths = []
    counts = []
    extras = {} if extra_hashes is None else json.loads(extra_hashes.read_text())
    for row in COHORT:
        if row["split"] != split:
            continue
        cid = row["id"]
        path = rawdir / (cid + ".c3d")
        log = {"id": cid, "scheduled": 0, "pastEligible": 0, "scorable": 0}
        counts.append(log)
        if not path.exists():
            log["excluded"] = "source file unavailable"
            continue
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = row.get("sha256") or extras.get(cid)
        if not expected or expected != sha:
            raise ValueError("Source hash absent or changed: " + cid)
        try:
            sites, meta = read_sites(path)
        except ValueError as exc:
            log["excluded"] = str(exc)
            continue
        log.update(meta, sha256=sha)
        for t, hist, fut in origins(sites, meta):
            log["scheduled"] += 1
            if hist is None:
                continue
            log["pastEligible"] += 1
            if fut is None:
                continue
            log["scorable"] += 1
            x, *geom = encode(hist)
            paths.append((cid, row["subject"], int(row["action"] == "run"), t, x, observed_residual(fut, *geom)))
    outdir.mkdir(parents=True, exist_ok=True)
    data = dict(zip(("id", "subject", "token", "t", "x", "y"), map(np.asarray, zip(*paths)))) if paths else dict(id=np.array([], dtype="U8"),subject=np.array([],dtype="U8"),token=np.empty(0,int),t=np.empty(0,int),x=np.empty((0,11,57)),y=np.empty((0,12,57)))
    np.savez_compressed(outdir / (split + ".npz"), **data)
    (outdir / (split + "-coverage.json")).write_text(json.dumps(counts, indent=2) + "\n")
    print(split, len(paths), "windows", len(set(data["id"])), "scorable recordings")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("split", choices=["train", "fresh", "previous"])
    p.add_argument("rawdir", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--extra-hashes", type=Path)
    a = p.parse_args()
    if a.split != "train":
        from seal import check
        check(a.output)
    prepare(a.split, a.rawdir, a.output, a.extra_hashes)
