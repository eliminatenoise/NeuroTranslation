"""Check every exported history, target mean, donor and displayed sample against its source."""

import argparse
import csv
import json
from collections import defaultdict

import numpy as np

from build import release
from stage import CACHE, HERE, SPLITS, digest, member, name, roster
from windows import CUTOFFS, GALLERY_COLUMNS, HEADER, TOL


def verify(split, release_dir):
    release(split, release_dir)
    support = json.loads((HERE / f"support-{split}.json").read_text())
    assert digest(HERE / f"{split}.npz") == support["npz_sha256"]
    assert digest(HERE / f"coverage-{split}.csv") == support["coverage_sha256"]
    with (HERE / f"coverage-{split}.csv").open() as stream:
        coverage = list(csv.DictReader(stream))
    records = {(int(r["participant"]), r["hand"], int(r["session_record_zero_based"])): r
               for r in roster() if SPLITS[r["fold"]] == split}
    assert len(coverage) == len(records)
    gallery = json.loads((HERE / "gallery.json").read_text()) if split == "train" else {"clips": []}
    displayed = {c["member"]: c for c in gallery["clips"]}
    if displayed:
        assert len(displayed) == 18 and gallery["columns"] == GALLERY_COLUMNS
    count, gallery_count = 0, 0
    member_hashes = json.loads((CACHE / "raw-members.json").read_text())
    with np.load(HERE / f"{split}.npz", allow_pickle=False) as array:
        ary = {k: array[k] for k in array.files}
    shape = len(ary["time"])
    assert set(ary) == {"time","gyro","accel","y_gyro","y_accel","participant","hand","target","trial","repetition","cutoff","donor"}
    assert all(len(v) == shape for v in ary.values())
    assert ary["time"].shape == (shape,20)
    assert all(ary[k].shape == (shape,20,3) for k in ("accel","gyro"))
    assert all(ary[k].shape == (shape,3) for k in ("y_accel","y_gyro"))
    seen = set()
    donors_by_original = defaultdict(list)
    for rr in coverage:
        pid, side, rec = int(rr["participant"]), rr["hand"], int(rr["session_record_zero_based"])
        original = records.pop((pid,side,rec))
        assert all(rr[k] == v for k, v in original.items())
        row_ids = [int(rr[str(c)]) for c in CUTOFFS if rr[str(c)].isdigit()]
        if rr["author_qc"] != "eligible":
            assert not row_ids
            continue
        path = CACHE / split / name(rr)
        assert digest(path) == member_hashes[member(rr)]
        with path.open() as f:
            assert f.readline().rstrip() == HEADER
            # Empty unused channels or out-of-window cells must not invalidate the file.
            reader = csv.reader(f, delimiter=";")
            data = np.asarray([[float(cell) if cell.strip() else np.nan for cell in line]
                               for line in reader if line], dtype=np.float64)
        rel = data[:, 0] - data[0, 0]
        display_key = member(rr).split("/",1)[1]
        clip = displayed.get(display_key)
        if clip:
            reference = np.column_stack((rel, data[:,1:4], data[:,7:10], data[:,13:17]))
            np.testing.assert_array_equal(clip["rows"], reference)
            assert clip["member_sha256"] == digest(path)
            assert clip["cutoffs_ms"] == [c for c in CUTOFFS if rr[str(c)].isdigit()]
            gallery_count += 1
        for c in CUTOFFS:
            # Independently place the cutoff via the native timestamp; no future inputs.
            mid = np.flatnonzero(np.abs(rel - c/1000) <= TOL)
            indices = np.arange(int(mid[0])-20, int(mid[0])+10) if len(mid) == 1 else []
            good = len(indices) == 30 and indices[0] >= 0 and indices[-1] < len(data)
            if good:
                t = rel[indices]
                good = (np.isfinite(rel[0]) and np.all(np.diff(rel[np.isfinite(rel)]) > 0)
                        and np.max(abs(t - ((c/1000) + np.arange(-20,10)*.01))) <= TOL
                        and np.max(abs(np.diff(t) - .01)) <= TOL
                        and np.isfinite(data[indices][:,[1,2,3,7,8,9]]).all())
            assert bool(good) == rr[str(c)].isdigit()
            if not good:
                continue
            i = int(rr[str(c)])
            assert i not in seen
            seen.add(i)
            assert [ary[k][i] for k in ("participant","trial","repetition","target","cutoff")] == [
                pid, rec, int(rr["repetition_zero_based"]), int(rr["target"]), c]
            assert ary["hand"][i] == {"L":"left","R":"right"}[side]
            np.testing.assert_array_equal(ary["time"][i], rel[indices[:20]])
            for sensor, cols in [("gyro",slice(7,10)),("accel",slice(1,4))]:
                np.testing.assert_array_equal(ary[sensor][i], data[indices[:20],cols])
                future = data[indices[20:],cols].mean(axis=0)
                np.testing.assert_allclose(ary["y_"+sensor][i],future,rtol=1e-14,atol=1e-14)
            donors_by_original[pid,side,rr["target"],c].append((rec,i))
            count += 1
    assert not records and gallery_count == len(displayed)
    assert seen == set(range(shape))
    for series in donors_by_original.values():
        order = sorted(series)
        for j, (rec, row) in enumerate(order):
            assert ary["donor"][row] == (-1 if j == 0 else order[j-1][1])
    assert shape == support["all_cutoffs"]["usable"] == count
    return {"split": split, "arrays_sha256": support["npz_sha256"], "source_matched_windows": count,
            "source_matched_gallery_clips":gallery_count,
            "closest_past_donors":int(np.sum(ary["donor"] >= 0)), "unmatched":int(np.sum(ary["donor"] < 0))}


if __name__ == "__main__":
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split",choices=list(SPLITS.values()))
    parser.add_argument("--release-dir", type=Path, default=HERE.parent/"imu-model")
    args=parser.parse_args()
    print(json.dumps(verify(args.split,args.release_dir)))
