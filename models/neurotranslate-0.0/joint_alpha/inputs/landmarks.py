"""Five observed frames of a 2D tracked point and its visible neighbours; original adapter code CC0."""

import json
from pathlib import Path

import numpy as np
from pack import checked, save, schema


def windows(xy, t, maximum, nominal):
    """Original frozen physical-time origin and endpoint selection."""
    finite = np.isfinite(xy).all(2)
    cumulative = np.vstack([np.zeros(xy.shape[1], int), finite.cumsum(0)])
    origins = np.arange(4, len(t) - 1)
    good = (
        finite[origins] & ((cumulative[origins + 1] - cumulative[origins - 4]) >= 3)
    ).any(1)
    good &= np.lib.stride_tricks.sliding_window_view(np.diff(t), 4).max(1)[:-1] <= 0.24
    good &= t[origins] - t[origins - 4] <= 0.96
    origins = origins[good]
    hi = np.minimum(np.searchsorted(t, t[origins] + nominal), len(t) - 1)
    lo = np.maximum(hi - 1, origins + 1)
    e = np.where(
        abs(t[hi] - t[origins] - nominal) < abs(t[lo] - t[origins] - nominal), hi, lo
    )
    good = (e > origins) & (abs(t[e] - t[origins] - nominal) <= 0.04 + 1e-10)
    selected = []
    last = -np.inf
    for o, target in zip(origins[good], e[good], strict=True):
        if t[o] >= last + 0.12 - 1e-10:
            selected.append((o, target))
            last = t[o]
    if len(selected) > maximum:
        selected = [
            selected[i] for i in np.linspace(0, len(selected) - 1, maximum).astype(int)
        ]
    return selected


def frame(xy, t, o, e, nominal):
    hist = xy[o - 4 : o + 1]
    valid = np.isfinite(hist).all(2)
    eligible = valid[-1] & (valid.sum(0) >= 3)
    if not eligible.any():
        return None
    origin = hist[-1, eligible]
    center = origin.mean(0)
    radius = float(np.sqrt(np.mean(np.sum((origin - center) ** 2, axis=1))))
    if not np.isfinite(radius) or radius <= 0:
        return None
    # Convert each observation into a coordinate frame known at issue, invariant to native length units.
    v = valid[:, eligible]
    dx = np.where(v[:, :, None], (hist[:, eligible] - origin) / radius, np.nan)
    present = v.sum(1)
    mean = np.nansum(dx, axis=1) / np.where(present > 0, present, np.nan)[:, None]
    n = eligible.sum()
    shape = (origin - center) / radius
    offsets = t[o - 4 : o + 1] - t[o]
    feat = np.concatenate(
        [
            dx,
            np.broadcast_to(mean[:, None, :], (5, n, 2)),
            np.broadcast_to(shape[None, :, :], (5, n, 2)),
            np.broadcast_to(offsets[:, None, None], (5, n, 1)),
            np.full((5, n, 1), nominal),
        ],
        axis=2,
    ).transpose(1, 0, 2)
    # Use the nearest previous observed point only; no unobserved interval enters its velocity.
    prev = np.where(v[:-1], np.arange(4)[:, None], -1).max(axis=0)
    assert (prev >= 0).all()
    j = np.arange(n)
    disp = (xy[e, eligible] - origin) / radius
    baseline = -dx[prev, j] * nominal / (-offsets[prev])[:, None]
    observed = np.isfinite(disp).all(1)
    if not observed.any():
        return None
    return {
        "X": feat[observed],
        "y": disp[observed],
        "baseline": baseline[observed],
        "point": np.flatnonzero(eligible)[observed],
        "radius_native": np.full(observed.sum(), radius),
    }


def landmark(inputs, stage, out):
    cat = json.loads(Path(__file__).with_name("catalog.json").read_text())["landmarks"]
    spec = schema(
        "continuous",
        [
            "point_dx",
            "point_dy",
            "matched_set_dx",
            "matched_set_dy",
            "point_from_center_x",
            "point_from_center_y",
            "sample_time_relative_to_issue",
            "requested_lead",
        ],
        ["observed origin RMS radius"] * 6 + ["s", "s"],
        ["delta_x", "delta_y"],
        ["observed origin RMS radius"] * 2,
        5,
        source="SLEAP (Clear BSD), Albi/Carlesso locust tracks (CC BY 4.0), Javer et al. WCON tracks (CC BY 4.0).",
        history="Five consecutive timed camera frames. Per-point coordinates relative to its current location, pooled offsets of matched currently eligible points, and current point relative to visible body centroid; divide by the physical radius measured at the issue frame. No atlas point or skeleton correspondence across recordings.",
        target="One optical point's 2D displacement at nearest source frame to the requested 120 ms (200 ms for the 5-Hz locust camera), tolerance 40 ms. Model and extrapolator use nominal duration fixed by recording protocol. Native-unit reversal multiplies by stored per-origin body radius.",
        group_definition="Two original development recording groups containing 9 within-video tracks (mouse open field and gerbils). Historical test retains all 14 original held recording groups. Track IDs are local; cross-recording individual identity unverified.",
        baseline_description="Constant-velocity from current and most recent earlier visible point, for the requested horizon.",
        limits="Camera/tracker pixels or worm micrometres. Local point indices and fractional centreline samples are not cross-species anatomy. A point is scored only with an eligible visible origin and measured endpoint; no held-group statistics or adaptation.",
    )
    groups = {}
    split = "train" if stage == "train" else "test"
    for track, r in cat.items():
        if r["split"] != split:
            continue
        p = inputs / r["path"]
        checked(p, r["sha256"])
        with np.load(p, allow_pickle=False) as a:
            xy, t = a["xy"].astype(float), a["seconds"]
        assert np.isfinite(t).all() and (np.diff(t) > 0).all()
        nominal = 0.20 if r["group"] == "locust" else 0.12
        assert (0.20 if np.median(np.diff(t)) > 0.12 else 0.12) == nominal
        split_key = (
            split
            if split == "train"
            else ("test_200ms" if nominal == 0.20 else "test_120ms")
        )
        arr = groups.setdefault(split_key, [])
        for o, e in windows(xy, t, 160 if split == "train" else 48, nominal):
            row = frame(xy, t, o, e, nominal)
            if row is None:
                continue
            n = len(row["y"])
            row.update(
                group=np.full(n, r["group"]),
                track=np.full(n, track),
                issue_s=np.full(n, t[o]),
                target_s=np.full(n, t[e]),
                issue_frame=np.full(n, o),
                source_unit=np.full(n, r["units"]),
            )
            arr.append(row)
    for split_key, rows in groups.items():
        save(
            out,
            "landmark_motion",
            split_key,
            spec,
            **{k: np.concatenate([r[k] for r in rows]) for k in rows[0]},
        )
