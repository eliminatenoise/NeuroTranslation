"""Forecast observed optical fluorescence with a fixed development-assay scale; original adapter code CC0."""

import json
from pathlib import Path

import numpy as np
from pack import checked, save, schema


def nearest(t, q):
    hi = np.minimum(np.searchsorted(t, q), len(t) - 1)
    lo = np.maximum(hi - 1, 0)
    return np.where(abs(q - t[lo]) <= abs(q - t[hi]), lo, hi)


def optical_cases(p):
    with np.load(p, allow_pickle=False) as z:
        t = z["time_s"].astype(float)
        f = z["fluorescence"].astype(float)
        roi_ids = z["roi_index"]
    assert np.isfinite(t).all() and (np.diff(t) > 0).all()
    t = t - t[0]
    crop = t < 180
    f, t = f[crop, :32], t[crop]
    # Same eligibility as the archived optical assay. These observations only censor unusable traces.
    usable = np.array(
        [
            len(y) >= 20 and np.ptp(y) > 0
            for column in f[t < 30].T
            for y in [column[np.isfinite(column)]]
        ]
    )
    grid = np.arange(30, 180, 1.2)
    origin = nearest(t, grid)
    offsets = np.array([-3.6, -2.4, -1.2, 0.0, 1.2])
    requested = t[origin, None] + offsets
    fr = nearest(t, requested)
    ok = (
        (abs(t[fr] - requested) <= 0.36).all(1)
        & (abs(t[origin] - grid) <= 0.36)
        & (t[origin] >= 30)
    )
    ok &= (np.diff(fr, axis=1) > 0).all(1) & (fr[:, 3] == origin)
    assert len(np.unique(origin[ok])) == ok.sum()
    g, r = np.nonzero(ok[:, None] & usable & np.isfinite(f[fr]).all(axis=1))
    sample = f[fr[g], r[:, None]]
    ts = t[fr[g]]
    return {"s": sample, "t": ts, "roi": roi_ids[r], "grid": g}


def calcium(inputs, stage, out):
    cat = json.loads(Path(__file__).with_name("catalog.json").read_text())["calcium"]
    rec = {}
    for animal, m in cat.items():
        if m["split"] != stage:
            continue
        p = inputs / stage / (animal + ".npz")
        checked(p, m["sha256"])
        rec[animal] = optical_cases(p)
    scale_file = out / "calcium-development-scale.json"
    if stage == "train":
        scales = {}
        for species in sorted({cat[a]["species"] for a in rec}):
            vals = np.concatenate(
                [
                    v["s"][:, :4].reshape(-1)
                    for a, v in rec.items()
                    if cat[a]["species"] == species
                ]
            )
            scales[species] = [float(vals.mean()), float(vals.std())]
        assert all(v[1] > 0 for v in scales.values())
        scale_file.write_text(json.dumps(scales, indent=2) + "\n")
    scales = json.loads(scale_file.read_text())
    spec = schema(
        "continuous",
        ["optical_fluorescence", "relative_sample_time", "fish_assay"],
        ["assay-specific development SD", "s", "0 or 1"],
        ["next_fluorescence"],
        ["assay-specific development SD"],
        4,
        source="Atanas, Kim et al. nuclear GCaMP7f in freely moving adult worms (CC BY 3.0 US); Haesemeyer and Balakrishnan larval zebrafish Z0 GCaMP6s ΔF/F in DANDI 000235/0.230316.1600 (CC BY 4.0).",
        history="Four measured points nearest −3.6, −2.4, −1.2 and 0 s from forecast issue, tolerances 0.36 s; grid every 1.2 s. First 32 ROIs, first 180 s, origin >=30 s. First 30 s only establish the established finite and nonconstant eligibility condition for each ROI.",
        target="Next optical value at approximately +1.2 s, error tolerance 0.36 s, unit of this assay's training-history SD.",
        group_definition="One training fish and eight worm recordings on different dates, one subject per recording in the source. Seven distinct held zebrafish. ROIs and windows are repeated observations. No held worm assessment.",
        baseline_description="Persist most recent observed fluorescence value.",
        scales_training_history=scales,
        limits="Worm source fluorescence and fish ΔF/F are distinct source quantities. Each assay uses only development observations to set one mean and SD, including every held forecast. Upstream bleaching correction, interpolation and segmentation can use recording-wide data. Optical activity is not spikes or muscle motion.",
    )
    rows = []
    for animal, v in rec.items():
        species = cat[animal]["species"]
        mean, sd = scales[species]
        normalized = (v["s"] - mean) / sd
        t = v["t"]
        n = len(t)
        x = np.stack(
            [
                normalized[:, :4],
                t[:, :4] - t[:, 3, None],
                np.full((n, 4), float(animal.startswith("Fish"))),
            ],
            axis=2,
        )
        rows.append(
            {
                "X": x,
                "y": normalized[:, 4, None],
                "baseline": normalized[:, 3, None],
                "group": np.full(n, animal),
                "roi": v["roi"],
                "issue": t[:, 3],
                "target_time": t[:, 4],
                "grid": v["grid"],
            }
        )
    arrays = {k: np.concatenate([r[k] for r in rows]) for k in rows[0]}
    save(
        out,
        "optical_fluorescence",
        "train" if stage == "train" else "test_fish",
        spec,
        **arrays,
    )
