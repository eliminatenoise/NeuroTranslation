"""Restore only the pinned 29 right-hand members from the original publisher."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import requests

from windows import COHORT_SHA
from windows import sha as file_sha

root = Path(__file__).resolve().parent.parent
cohort_path = root / "preceding-words-source/COHORT.json"
if file_sha(cohort_path) != COHORT_SHA:
    raise ValueError("Source cohort hash mismatch")
records = json.loads(cohort_path.read_text())["recordings"]
directory = HERE = root / "hand-text-source"
HANDS = "https://hl2data.z5.web.core.windows.net/holoassist-data-release/hands.tar"
OBJECTS = {HANDS: ('"0x8DC8C9DE150FE51"', 235404984320)}
SELECTED = {r["recording"]: {"role": "train"} for r in records}
TRANSLATIONS = [3 + 16 * j + k for j in range(26) for k in (3, 7, 11)]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def get(session, url, start, length, stream=False):
    etag, total = OBJECTS[url]
    headers = {
        "Accept-Encoding": "identity",
        "If-Match": etag,
        "Range": f"bytes={start}-{start + length - 1}",
    }
    response = session.get(url, headers=headers, timeout=(10, 60), stream=stream)
    if (
        response.status_code != 206
        or response.headers.get("ETag") != etag
        or response.headers.get("Content-Range")
        != f"bytes {start}-{start + length - 1}/{total}"
    ):
        response.close()
        raise ValueError("Unexpected publisher byte range or edition")
    return response


# Source-preserving conversion from the earlier verified right-hand reader.
def extract(record):
    row = record["hand_source_member"]
    rec = row["recording"]
    role = SELECTED[rec]["role"]
    if (
        row["name"] != f"{rec}/Export_py/Hands/Right_sync.txt"
        or row["etag"] != OBJECTS[HANDS][0]
    ):
        raise ValueError("Unpermitted member")
    dest = HERE / role / (rec + ".npz")
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
            if h.hexdigest() != record["hand_source_member_sha256"]:
                raise ValueError(f"Publisher member digest differs: {rec}")
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
    with tempfile.TemporaryDirectory(dir=dest.parent) as pending:
        candidate = Path(pending) / dest.name
        np.savez_compressed(
            candidate,
            t=t,
            ticks=ticks,
            xyz=xyz,
            active=active,
            valid=valid,
            tracked=tracked,
        )
        if file_sha(candidate) != record["hand_npz_sha256"]:
            raise ValueError(f"Converted hand archive differs: {rec}")
        try:
            os.link(candidate, dest)
        except FileExistsError:
            if file_sha(dest) != record["hand_npz_sha256"]:
                raise ValueError(
                    f"Concurrent conflicting hand archive: {rec}"
                ) from None


if __name__ == "__main__":
    (directory / "train").mkdir(parents=True, exist_ok=True)
    for r in records:
        p = root / r["hand_npz"]
        if p.exists():
            if file_sha(p) != r["hand_npz_sha256"]:
                raise ValueError(
                    f"Existing converted hand file differs: {r['recording']}"
                )
            continue
        extract(r)
        print(r["recording"], flush=True)
    print(f"Verified {len(records)} required hand files.")
