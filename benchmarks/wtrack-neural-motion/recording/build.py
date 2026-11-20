"""Rebuild or check aligned, strictly within-trip W-track data from an immutable NWB."""

import argparse
import hashlib
import io
import json
import os
from bisect import bisect_left, bisect_right
from pathlib import Path

import h5py
import numpy as np
from ranges import ASSET, ETAG, ROOT, SHA256, SIZE, URL, PinnedRanges

TRAIN = list(range(55, 79))
TEST = list(range(80, 90))
RESERVE = list(range(91, 96))
VERSION = "000978/versions/0.240511.0307"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_raw(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def store(path, raw, check):
    if check:
        if not path.is_file() or raw != path.read_bytes():
            raise ValueError(f"Rebuilt bytes differ: {path}")
        return
    path.parent.mkdir(exist_ok=True, parents=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)


def archive_receipts():
    receipts = [
        ROOT / "evidence" / f"{item}.json" for item in ("asset", "release", "members")
    ]
    asset, release, members = [json.loads(p.read_bytes()) for p in receipts]
    assert asset["id"] == f"dandiasset:{ASSET}" and asset["contentSize"] == SIZE
    assert (
        ETAG == asset["digest"]["dandi:dandi-etag"]
        and SHA256 == asset["digest"]["dandi:sha2-256"]
    )
    assert URL in asset["contentUrl"] and release["id"] == "DANDI:" + VERSION.replace(
        "/versions", ""
    )
    assert (
        release["license"] == ["spdx:CC-BY-4.0"]
        and release["access"][0]["status"] == "dandi:OpenAccess"
    )
    assert any(
        a["asset_id"] == ASSET and a["path"] == asset["path"]
        for a in members["results"]
    )
    return {p.name: digest(p) for p in receipts}


def validate_source(f):
    assert (
        f["general/session_id"][()] == b"01"
        and f["general/subject/subject_id"][()] == b"JDS-SingleDay-JS14"
    )
    assert f["session_start_time"][()] == f["timestamps_reference_time"][()]
    epochs = f["intervals/epoch intervals"]
    assert epochs["id"][5] == 5 and epochs["start_time"][5] == 5970.043333333333
    assert epochs["stop_time"][5] == 6923.783033333333
    t = f["intervals/trials"]
    ids, starts, stops = [t[k][:] for k in ("id", "start_time", "stop_time")]
    assert (
        np.array_equal(ids, np.arange(len(ids)))
        and np.all(starts < stops)
        and np.all(stops[:-1] <= starts[1:])
    )
    runs = np.flatnonzero(
        (starts >= epochs["start_time"][5]) & (stops <= epochs["stop_time"][5])
    )
    assert np.array_equal(runs, np.arange(55, 96))
    frozen = json.loads((ROOT / "split.json").read_bytes())
    groups = frozen["groups"]
    split_members = {
        "train": TRAIN,
        "between_train_test": [79],
        "test": TEST,
        "between_test_reserve": [90],
        "reserve": RESERVE,
    }
    for group, trial_ids in split_members.items():
        expected = groups[group]
        assert expected["trial_ids"] == trial_ids
        assert expected["start_s"] == starts[trial_ids[0]]
        assert expected["stop_s"] == stops[trial_ids[-1]]

    spatial = f["processing/behavior/Position/SpatialSeries"]
    assert (
        spatial["reference_frame"][()] == b"center well"
        and spatial["timestamps"].attrs["unit"] == "seconds"
    )
    assert spatial["data"].attrs["unit"] == "centimeters; centimeters/second"
    assert (
        spatial["data"].attrs["conversion"] == 1
        and spatial["data"].attrs["offset"] == 0
    )
    assert "row1:xpos row2:ypos row3:velocity" in spatial.attrs["comments"]
    u = f["units"]
    assert "obs_intervals" not in u and np.array_equal(u["id"][:], np.arange(72))
    assert len(u["spike_times_index"]) == len(u["id"]) and u["spike_times_index"][
        -1
    ] == len(u["spike_times"])
    return starts, stops, spatial, u


def unit_table(f, u):
    result = []
    electrodes = f[u["electrodes"].attrs["table"]]
    for i, (uid, erow) in enumerate(zip(u["id"][:], u["electrodes"][:], strict=True)):
        obj = f[electrodes["group"][erow]]
        name = electrodes["group_name"][erow].decode()
        reg = electrodes["location"][erow].decode()
        result.append(
            {
                "unit_id": int(uid),
                "unit_row": i,
                "electrode_row": int(erow),
                "electrode_id": int(electrodes["id"][erow]),
                "electrode_region": reg,
                "electrode_ref_label": electrodes["label"][erow].decode(),
                "electrode_group_name": name,
                "referenced_group_path": obj.name,
                "referenced_group_region": obj.attrs["location"],
                "group_name_agrees": name.lower() == obj.name.split("/")[-1].lower(),
                "region_agrees": (reg == obj.attrs["location"]),
            }
        )
    assert all(r["group_name_agrees"] and r["region_agrees"] for r in result)
    return result


def read_segment(spatial, u, a, b):
    # Binary searches touch timestamps for indexing. Only included times/coordinates
    # and sorted events inside one admitted segment are retained or analyzed.
    t = spatial["timestamps"]
    pfirst, plast = bisect_right(t, a), bisect_left(t, b)
    pt = t[pfirst:plast]
    assert len(pt) and np.all(np.diff(pt) > 0) and a < pt[0] <= pt[-1] < b
    assert pfirst == 0 or t[pfirst - 1] <= a
    assert plast == len(t) or t[plast] >= b
    xy = spatial["data"][pfirst:plast, :2]
    times = u["spike_times"]
    unit_ends = u["spike_times_index"][:].astype(int)
    chunks = []
    offsets = []
    for lo, hi in zip(np.r_[0, unit_ends[:-1]], unit_ends, strict=True):
        lower = bisect_right(times, a, int(lo), int(hi))
        upper = bisect_left(times, b, lower, int(hi))
        s = times[lower:upper]
        assert not len(s) or (a < s[0] <= s[-1] < b and np.all(np.diff(s) >= 0))
        assert lower == lo or times[lower - 1] <= a
        assert upper == hi or times[upper] >= b
        chunks.append(s)
        offsets.append(lower)
    return pfirst, pt, xy, offsets, chunks


def extract(f, check):
    starts, stops, position, u = validate_source(f)
    table = unit_table(f, u)
    store(ROOT / "evidence/units.json", json_raw(table), check)
    registry = []
    ids = u["id"][:]
    for split, trials in [("train", TRAIN), ("test", TEST)]:
        pfirst, pt, xy, offs, chunks = read_segment(
            position, u, starts[trials[0]], stops[trials[-1]]
        )
        for i in trials:
            a, b = starts[i], stops[i]
            p0, p1 = (
                int(np.searchsorted(pt, a, "right")),
                int(np.searchsorted(pt, b, "left")),
            )
            st_bounds = [
                (
                    int(np.searchsorted(s, a, "right")),
                    int(np.searchsorted(s, b, "left")),
                )
                for s in chunks
            ]
            s_counts = np.array([hi - lo for lo, hi in st_bounds], dtype=np.int64)
            ss = np.concatenate(
                [s[lo:hi] for s, (lo, hi) in zip(chunks, st_bounds, strict=True)]
            )
            x, t = xy[p0:p1], pt[p0:p1]
            ix = np.arange(pfirst + p0, pfirst + p1, dtype=np.int64)
            assert len(t) > 1
            raw = io.BytesIO()
            np.savez_compressed(
                raw,
                trial_id=np.int64(i),
                start_s=a,
                stop_s=b,
                tracking_time_s=t,
                xy_cm=x,
                camera_row=ix,
                unit_id=ids,
                spike_time_s=ss,
                spike_end=np.cumsum(s_counts),
            )
            path = ROOT / "pairs" / split / f"trial-{i:03d}.npz"
            store(path, raw.getvalue(), check)
            registry.append(
                {
                    "split": split,
                    "trial_id": i,
                    "trial_row": i,
                    "start_s": a,
                    "stop_s": b,
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": digest(path),
                    "camera_bounds": [int(ix[0]), int(ix[-1]) + 1],
                    "spike_bounds": [
                        [o + lo, o + hi]
                        for o, (lo, hi) in zip(offs, st_bounds, strict=True)
                    ],
                    "tracking_rows": len(t),
                    "finite_xy_rows": int(np.isfinite(x).all(axis=1).sum()),
                    "min_max_tracking_gap_s": [
                        float(np.diff(t).min()),
                        float(np.diff(t).max()),
                    ],
                    "observed_events": len(ss),
                    "units_with_recorded_events": int((s_counts > 0).sum()),
                }
            )
    return registry


def main():
    if not __debug__:
        raise RuntimeError("Run with Python assertion checks enabled (omit -O).")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare derived paired arrays and manifest byte-for-byte",
    )
    parser.add_argument("--cache", type=Path, default=ROOT / "cache")
    args = parser.parse_args()
    receipts = archive_receipts()
    with PinnedRanges(args.cache) as src, h5py.File(src, "r") as f:
        registry = extract(f, args.check)
        rel = {
            "version": VERSION,
            "asset_id": ASSET,
            "archive_sha256": SHA256,
            "source_receipt_sha256": receipts,
            "split_contract_sha256": digest(ROOT / "split.json"),
            "unit_metadata_sha256": digest(ROOT / "evidence/units.json"),
            "source_offset_convention": "All camera and flat spike index bounds are zero-based, half-open; spike bounds are in NWB unit-row order.",
            "arrays": registry,
        }
        store(ROOT / "manifest.json", json_raw(rel), args.check)
        used = {str(i): v for i, v in sorted(src.seen.items())}
        store(ROOT / "evidence/blocks.json", json_raw(used), args.check)
        print(
            json.dumps(
                {
                    "packets": len(registry),
                    "sha256": digest(ROOT / "manifest.json"),
                    "camera_rows": sum(r["tracking_rows"] for r in registry),
                    "spike_times": sum(r["observed_events"] for r in registry),
                    "unique_pinned_blocks": len(used),
                    "network_bytes": src.download_bytes,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
