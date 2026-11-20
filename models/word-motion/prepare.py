"""Extract phase-registered CMU skin-marker targets from hash-checked recordings."""

import argparse
import json
from pathlib import Path

import ezc3d
import numpy as np
from acquire import HERE, digest, manifest

SCHEMA = json.loads((HERE / "schema.json").read_text())
OFFSETS = np.arange(-36, 37, 3)


class Ineligible(ValueError):
    """A frozen recording lacks the required measurements."""


def extract(path):
    capture = ezc3d.c3d(str(path))
    header = capture["header"]["points"]
    point = capture["parameters"]["POINT"]
    if point["UNITS"]["value"] != ["mm"] or header["frame_rate"] != 120:
        raise Ineligible("source clock or units")
    screen = point.get("Y_SCREEN", {}).get("value")
    if screen and screen != ["+Z"]:
        raise Ineligible("inconsistent screen vertical")
    labels = []
    for n in range(1, 20):
        key = "LABELS" if n == 1 else f"LABELS{n}"
        if key not in point:
            break
        labels.extend(label.strip().split(":")[-1] for label in point[key]["value"])
    if len(labels) != header["size"]:
        raise Ineligible("incomplete source point catalogue")
    names = sorted({name for group in SCHEMA["sites"] for name in group})
    if any(labels.count(name) != 1 for name in names):
        raise Ineligible("missing or ambiguous marker names")
    index = [labels.index(name) for name in names]
    raw = capture["data"]["points"][:3, index].transpose(2, 1, 0).copy()
    flags = capture["data"]["meta_points"]["residuals"][0, index].T
    raw[~(np.isfinite(flags) & (flags >= 0))] = np.nan
    sites = np.stack(
        [raw[:, [names.index(n) for n in group]].mean(1) for group in SCHEMA["sites"]],
        axis=1,
    )
    hip = sites[:, 2:4].mean(1)
    valid_hip = hip[np.isfinite(hip).all(axis=-1)]
    if len(valid_hip) < 2:
        raise Ineligible("unavailable pelvis")
    travel = np.median(valid_hip[-12:], axis=0) - np.median(valid_hip[:12], axis=0)
    travel[2] = 0
    span = np.linalg.norm(travel)
    if span < 250:
        raise Ineligible("less than 250 mm of net travel")
    height = np.nanmedian(sites[:, 0, 2] - sites[:, 14:16, 2].mean(1))
    if not np.isfinite(height) or height < 800:
        raise Ineligible("unconfirmed head above heels")
    forward = travel / span
    up = np.array([0.0, 0.0, 1.0])
    basis = np.stack([np.cross(forward, up), forward, up], axis=1)
    t = np.arange(len(raw))
    candidates = t[
        (t >= max(36, (len(t) - 1) / 4)) & (t <= min(len(t) - 37, 3 * (len(t) - 1) / 4))
    ]
    complete = np.isfinite(sites).all(axis=(1, 2))
    candidates = candidates[complete[candidates[:, None] + OFFSETS].all(axis=1)]
    if not len(candidates):
        raise Ineligible("no complete phase window")
    lead = (sites[candidates, 15] - sites[candidates, 14]) @ forward
    centre = int(candidates[np.argmax(lead)])
    frames = centre + OFFSETS
    body = (sites[frames] - hip[frames, None]) @ basis
    root = (hip[frames] - hip[frames[0]]) @ basis
    y = np.concatenate([body.reshape(len(frames), -1), root], axis=1)
    start = int(header["first_frame"]) + 1
    return y.astype(np.float32), {
        "sourceFirstFrame": start,
        "sourceLastFrame": int(header["last_frame"]) + 1,
        "sampledSourceFrames": (start + frames).tolist(),
        "forwardLab": forward.tolist(),
        "netCourseMm": float(span),
        "headAboveHeelMm": float(height),
        "sourceScreenVertical": screen,
        "centreHeelLeadMm": float(max(lead)),
        "candidateCentres": len(candidates),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("split", choices=["train", "assessment"])
    p.add_argument("--local", type=Path, required=True)
    args = p.parse_args()
    src = args.local / args.split
    acquisition = {
        r["id"]: r for r in json.loads((src / "acquisition.json").read_text())
    }
    rows = [r for r in manifest()["clips"] if r["split"] == args.split]
    records, ys, ids = [], [], []
    for row in rows:
        uid = row["id"]
        path = src / (uid + ".c3d")
        if digest(path.read_bytes()) != acquisition[uid]["sha256"]:
            raise ValueError("Acquired source changed: " + uid)
        try:
            y, meta = extract(path)
        except Ineligible as exc:
            records.append({"id": uid, "excluded": str(exc)})
            continue
        records.append({"id": uid, **meta})
        ids.append(uid)
        ys.append(y)
    if not ys:
        raise ValueError("No eligible clips")
    np.savez(src / "targets.npz", ids=ids, y=np.stack(ys))
    (src / "geometry.json").write_text(json.dumps(records, indent=2) + "\n")
    print(
        args.split,
        "eligible",
        len(ids),
        "/",
        len(rows),
        "exclusions",
        [(r["id"], r["excluded"]) for r in records if "excluded" in r],
    )


if __name__ == "__main__":
    main()
