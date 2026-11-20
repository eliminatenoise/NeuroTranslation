"""Fetch only frozen right-hand members and retain movements, original flags and clocks."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import os
import tempfile
import time

import numpy as np
import requests

from index_source import HERE, HANDS, OBJECTS, SELECTED, get, sha

TRANSLATIONS = [3 + 16 * j + k for j in range(26) for k in (3, 7, 11)]


def extract(row):
    rec = row["recording"]
    role = SELECTED[rec]["role"]
    if (
        row["name"] != f"{rec}/Export_py/Hands/Right_sync.txt"
        or row["etag"] != OBJECTS[HANDS][0]
    ):
        raise ValueError("Unpermitted member")
    dest = HERE / role / (rec + ".npz")
    receipt = HERE / "receipts" / (rec + ".json")
    if dest.exists() and receipt.exists():
        prior = json.loads(receipt.read_text())
        if (
            prior["npz_sha256"] != sha(dest.read_bytes())
            or prior["source_member"] != row
        ):
            raise ValueError("Inconsistent existing result")
        return rec, "reused"
    start = time.monotonic()
    with requests.Session() as session:
        hi = get(session, HANDS, row["offset"] - 512, 512).content
        import tarfile

        member = tarfile.TarInfo.frombuf(hi, "utf8", "strict")
        if (
            sha(hi) != row["header_sha256"]
            or member.name != row["name"]
            or member.size != row["length"]
        ):
            raise ValueError("Archive member header changed")
        with (
            get(session, HANDS, row["offset"], row["length"], stream=True) as r,
            tempfile.TemporaryFile() as tmp,
        ):
            h = hashlib.sha256()
            for chunk in r.iter_content(chunk_size=512 * 1024):
                h.update(chunk)
                tmp.write(chunk)
            if tmp.tell() != row["length"]:
                raise ValueError("Short member")
            received = time.monotonic()
            tmp.seek(0)
            times = []
            ticks = []
            active = []
            valid = []
            tracked = []
            positions = []
            for line in tmp:
                f = line.split()
                if len(f) != 471:
                    raise ValueError((rec, len(times), len(f)))
                if f[2] not in (b"0", b"1") or any(
                    x not in (b"0", b"1") for x in f[419:]
                ):
                    raise ValueError("Unexpected hand validity flags")
                times.append(float(f[0]))
                ticks.append(int(f[1]))
                active.append(f[2] == b"1")
                valid.append([i == b"1" for i in f[419:445]])
                tracked.append([i == b"1" for i in f[445:471]])
                positions.append([float(f[i]) for i in TRANSLATIONS])
    active = np.array(active)
    valid = np.array(valid)
    tracked = np.array(tracked)
    xyz = np.asarray(positions, dtype=np.float32).reshape(-1, 26, 3)
    mask = active[:, None] & valid & tracked & np.isfinite(xyz).all(axis=-1)
    xyz[~mask] = np.nan
    t = np.array(times, np.float64)
    ticks = np.array(ticks, np.int64)
    if not np.all(np.diff(t) > 0) or not np.isfinite(t).all():
        raise ValueError((rec, "non-monotone recording clock"))
    with tempfile.NamedTemporaryFile(
        dir=dest.parent, suffix=".npz", delete=False
    ) as output:
        np.savez_compressed(
            output,
            t=t,
            ticks=ticks,
            xyz=xyz,
            active=active,
            valid=valid,
            tracked=tracked,
        )
    os.replace(output.name, dest)
    result = dict(
        recording=rec,
        role=role,
        source_member=row,
        source_member_sha256=h.hexdigest(),
        npz_sha256=sha(dest.read_bytes()),
        npz_bytes=dest.stat().st_size,
        frames=len(t),
        first_s=float(t[0]),
        last_s=float(t[-1]),
        elapsed_clock_step_s_median=float(np.median(np.diff(t))),
        repeated_adjacent_ticks=int((np.diff(ticks) == 0).sum()),
        reversing_adjacent_ticks=int((np.diff(ticks) < 0).sum()),
        unique_ticks=int(len(np.unique(ticks))),
        active_frames=int(active.sum()),
        any_tracked_valid_active_frames=int(mask.any(axis=1).sum()),
        all_tracked_valid_active_frames=int(mask.all(axis=1).sum()),
        fetch_s=round(received - start, 3),
        whole_s=round(time.monotonic() - start, 3),
    )
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    return rec, result["frames"], result["fetch_s"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--roles", nargs="+", choices=["train", "review"], default=["train", "review"]
    )
    parser.add_argument("--recording")
    args = parser.parse_args()
    (HERE / "receipts").mkdir(exist_ok=True)
    rows = [
        json.loads(l) for l in (HERE / "tar-headers.jsonl").read_text().splitlines()
    ]
    rows = [
        r
        for r in rows
        if SELECTED[r["recording"]]["role"] in args.roles
        and (not args.recording or args.recording == r["recording"])
    ]
    if not rows:
        raise ValueError("No indexed allowed recordings")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for f in as_completed([ex.submit(extract, r) for r in rows]):
            print(*f.result(), flush=True)


if __name__ == "__main__":
    main()
