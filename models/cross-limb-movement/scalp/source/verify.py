"""Verify input-only grouping, units, masks, clocks, and four shared walking intervals."""

import argparse
import json
from pathlib import Path

import numpy as np
from prepare import BANKS, COHORT, CONTROLS, KEYS, WAY, bound, require


def typed_check(keys, z, name, labels, rate, guard):
    rows = z[name + "_rows"]
    flag = z[name + "_reason"]
    good = z[name + "_good"]
    require(
        np.array_equal(
            rows, np.flatnonzero(keys["domain"] == (1 if name == "way" else 0))
        )
        and np.array_equal(labels, z[name + "_names"]),
        "row index or electrode order",
    )
    require(
        good.dtype == np.bool_
        and np.array_equal(good, flag == 0)
        and flag.shape == (len(rows), len(labels))
        and np.all((flag & 240) == 0),
        "mask bits",
    )
    mean, rms = z[name + "_mean"], z[name + "_rms"]
    require(
        mean.shape == rms.shape == (len(rows), 20, len(labels))
        and all(
            a.dtype == np.dtype("float32") and np.isfinite(a).all() for a in (mean, rms)
        ),
        "feature type, shape or finite",
    )
    require(
        not np.any(np.where(good[:, None, :], 0, mean))
        and not np.any(np.where(good[:, None, :], 0, rms))
        and np.all(rms >= abs(mean) - 1e-5),
        "mask placeholder or mean/RMS inequality",
    )
    first = z[name + "_bin_first_offset"]
    last = z[name + "_bin_last_offset"]
    counts = z[name + "_bin_samples"]
    for b in range(20):
        left, right = -0.625 + b / 32, -0.625 + (b + 1) / 32
        offsets = [
            h
            for h in range(-rate, 1)
            if (h / rate > left + guard + 1e-10 and h / rate <= right - guard + 1e-10)
        ]
        require(
            offsets == list(range(first[b], last[b] + 1)) and len(offsets) == counts[b],
            "bin support",
        )
    require(
        np.max(abs(z[name + "_latest_minus_cutoff_s"] - last[-1] / rate)) < 1e-8
        and np.array_equal(z[name + "_source_ordinal"], keys["event"][rows]),
        "timing or original ordinals",
    )
    bychannel = {
        n: {
            "obtained": int(good[:, j].sum()),
            "possible": len(rows),
            "flags": {
                f: int(np.count_nonzero(flag[:, j] & b))
                for f, b in [
                    ("missing", 1),
                    ("source_bad", 2),
                    ("nonfinite", 4),
                    ("flat", 8),
                ]
            },
        }
        for j, n in enumerate(labels)
    }
    return {
        "rows": len(rows),
        "n_people": len(set(keys["person"][rows])),
        "scalp_good_per_row_minmax": [
            int(a)
            for a in (
                good[:, : len(WAY) if name == "way" else 128].sum(1).min(),
                good[:, : len(WAY) if name == "way" else 128].sum(1).max(),
            )
        ],
        "obtained_by_channel": bychannel,
        "native_samples_per_bin": counts.tolist(),
    }


def walk_check(keys, z, walk_path):
    # Their eight 20-sample patches and these twenty 8-sample patches have common 40-sample boundaries.
    rows = z["balance_rows"]
    positions = rows[keys["session"][rows] == 1]
    ix = {
        (
            str(keys["person"][i]).removeprefix("balance:"),
            int(keys["event"][i]),
            int(keys["cutoff"][i]),
        ): j
        for j, i in enumerate(rows)
        if keys["session"][i] == 1
    }
    expected = "1a030856ec7d06ac331226a20fcb614482756c193e7212976bcd8648f7ac8d71"
    with np.load(bound(walk_path, expected), allow_pickle=False) as w:
        matches = [
            (j, ix[(p, int(e), int(c))])
            for j, (p, e, c) in enumerate(
                zip(w["person"], w["event"], w["cutoff"], strict=True)
            )
            if (p, int(e), int(c)) in ix
        ]
        require(len(set(matches)) == len(matches) > 0, "walking overlap")
        a, b = np.asarray(matches).T
        valid = np.c_[w["eeg_good"][a], w["nuisance_good"][a, :5]]
        require(np.array_equal(valid, z["balance_good"][b]), "walking masks")
        err = {}
        for kind in ("mean", "rms"):
            alt = np.concatenate(
                (w[f"eeg_{kind}_uv"][a], w[f"nuisance_{kind}_uv"][a, :, :5]), axis=-1
            )
            ours = z[f"balance_{kind}"][b].astype(np.float64)
            if kind == "mean":
                ours = ours.reshape(len(a), 4, 5, -1).mean(2)
                alt = alt.reshape(len(a), 4, 2, -1).mean(2)
            else:
                ours = np.sqrt(np.square(ours).reshape(len(a), 4, 5, -1).mean(2))
                alt = np.sqrt(np.square(alt).reshape(len(a), 4, 2, -1).mean(2))
            require(
                np.allclose(alt, ours, rtol=1e-6, atol=1e-4), "walking 40-sample parity"
            )
            err[kind] = float(np.abs(ours - alt).max())
    return {
        "matched_walking_events": len(matches),
        "possible_in_joint": len(positions),
        "overlap_only": True,
        "max_abs_difference_microV": err,
        "criteria": "Same masked 40-sample means and RMS, across four shared time intervals. rtol=1e-6, atol=1e-4 microV.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for label in ("cohort", "cache", "walk-development", "output"):
        p.add_argument("--" + label, required=True, type=Path)
    paths = p.parse_args()
    with (
        np.load(bound(paths.cohort, COHORT), allow_pickle=False) as original,
        np.load(paths.cache, allow_pickle=False) as z,
    ):
        keys = {k: original[k] for k in KEYS}
        require(all(np.array_equal(keys[k], z[k]) for k in KEYS), "metadata mismatch")
        way = typed_check(keys, z, "way", WAY, 500, 0.002)
        balance = typed_check(keys, z, "balance", BANKS + CONTROLS, 256, 0.0)
        controls = z["balance_good"][:, 128:]
        require(controls.shape[1] == 5, "neck/eye controls")
        overlay = json.loads(
            (Path(__file__).parent / "nominal-cap-sites.json").read_bytes()
        )
        sites = [overlay["sites"][n]["bank"] for n in WAY]
        mask = z["balance_good"][:, [BANKS.index(s) for s in sites]]
        balance["nominal_nine"] = dict(zip(WAY, map(int, mask.sum(0)), strict=True))
        complete_rows = z["balance_rows"][mask.all(1)]
        balance["all_nominal_nine"] = len(complete_rows)
        balance["people_with_all_nine"] = len(set(keys["person"][complete_rows]))
        balance["sessions_with_all_nine"] = len(
            set(
                zip(
                    keys["person"][complete_rows],
                    keys["session"][complete_rows],
                    strict=True,
                )
            )
        )
        result = {
            "way": way,
            "balance": balance,
            "walk": walk_check(keys, z, paths.walk_development),
        }
    paths.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
