"""Convert aligned reaching and balance replay windows to typed measurements; original adapter code CC0."""

import numpy as np
from pack import checked, save, schema

CONTACTS = [
    2,
    4,
    6,
    10,
    12,
    13,
    15,
    16,
    18,
    19,
    20,
    21,
    23,
    28,
    33,
    35,
    36,
    37,
    39,
    44,
    46,
    47,
    49,
    53,
    55,
    56,
    58,
    59,
    64,
    72,
    74,
    84,
    87,
    88,
    89,
    94,
    95,
]
MACAQUE = {
    "train": (
        "train.npz",
        "edf4a94b3cb9a60a7706324b4f3a85c959df2dfdae475948706853f528136f6e",
    ),
    "test_block1": (
        "block1.npz",
        "b0be522db123796da5a7f0ddb50f4b9b7e7c8980493904d7fb776abdb23525e9",
    ),
    "test_block2": (
        "block2.npz",
        "4e28e2173402418efead06c8b815ad4f9cbf9e5418d700f146db5efa3fbf6bb8",
    ),
}
HUMAN = {
    "train": (
        "development.npz",
        "56571adae22e7a1bd8cd161d49fed222a88be865f09ef6ad74942bad0d23472a",
    ),
    "test": (
        "assessment.npz",
        "d19fcf391562ba6980d3dcba68bdfe9b4bae86ffb6ff972342ce524301e263ab",
    ),
}


def human(inputs, stage, out):
    split = "train" if stage == "train" else "test"
    name, checksum = HUMAN[split]
    checked(inputs / name, checksum)
    muscles = [
        s + "_" + m
        for s in ("left", "right")
        for m in (
            "tibialis_anterior",
            "soleus",
            "medial_gastrocnemius",
            "peroneus_longus",
        )
    ]
    axes = ["mediolateral", "superior_inferior", "anterior_posterior"]
    sites = ["D19", "A1", "B22"]
    channels = [f"scalp_{s}_{stat}" for s in sites for stat in ("mean", "log_rms")]
    channels += [f"emg_log_rms_{m}" for m in muscles]
    channels += [f"sacrum_{axis}_sample_{k}" for k in (8, 16, 24, 32) for axis in axes]
    channels += ["posture_walking", "cue_clockwise"]
    units = (
        ["uV", "log(1+RMS/uV)"] * 3
        + ["log(1+RMS/uV)"] * 8
        + ["mm"] * 12
        + ["0 or 1", "-1 or +1"]
    )
    details = {
        "source": "OpenNeuro ds003739 v1.0.3 (CC0), healthy adults, standing and walking visual rotations.",
        "history": "Five consecutive 32-sample bins at 256 Hz. Cutoff c=ceil(rotation onset in samples)+32; c-159 through c. Each sacrum value is relative to c, available at issue. EEG missing site is NaN for both moments.",
        "group_definition": "Whole person; all events and both posture sessions travel together. 18 development and six historical assessment participants. The separate reserve is excluded.",
        "metadata": "person group, session posture, cue direction, event-log third, native event ordinal and native cutoff are separate replay metadata. Only posture and direction enter X.",
        "limits": "Full source offline filtering, retrospective quality, and future outcome completeness restrict live claims. Surface EMG measures muscle voltage. Anatomical positive coordinate signs unverified.",
    }
    with np.load(inputs / name, allow_pickle=False) as a:
        n = len(a["event"])
        scalp = np.where(a["present"][:, None, :, None], a["scalp"], np.nan)
        context = np.broadcast_to(
            np.stack([a["posture"], a["direction"]], 1)[:, None, :], (n, 5, 2)
        )
        x = np.concatenate(
            [
                scalp.reshape(n, 5, 6),
                a["leg"],
                a["position"].reshape(n, 5, 12),
                context,
            ],
            2,
        )
        fields = {
            "X": x,
            "group": a["person"],
            "issue": a["cutoff"],
            "event": a["event"],
            "posture": a["posture"],
            "direction": a["direction"],
            "stratum": a["block"],
            "site_present": a["present"],
        }
        muscle = schema(
            "continuous",
            channels,
            units,
            muscles,
            ["uV RMS"] * 8,
            5,
            **details,
            target="Eight measured channel RMS voltages over c+1..c+32 (125 ms).",
            baseline_description="Previous 32-sample per-channel measured RMS.",
        )
        save(
            out,
            "human_leg_emg",
            split,
            muscle,
            **fields,
            y=a["y_leg"],
            baseline=a["previous_rms"],
        )
        labels = [f"future_{axis}_{k}" for k in (8, 16, 24, 32) for axis in axes]
        path = schema(
            "continuous",
            channels,
            units,
            labels,
            ["mm"] * 12,
            5,
            **details,
            target="Time-major XYZ sacrum displacement from c at samples +8,+16,+24,+32 (31.25, 62.5, 93.75, 125 ms).",
            baseline_description="Previous 32-sample secant velocity, per-axis constant extrapolation at each requested future knot.",
        )
        baseline = (
            a["physics"][:, 2, None, :]
            * np.array([0.25, 0.5, 0.75, 1.0])[None, :, None]
        )
        save(
            out,
            "human_sacrum_path",
            split,
            path,
            **fields,
            y=a["y_path"][:, 7::8, :].reshape(n, 12),
            baseline=baseline.reshape(n, 12),
        )


def macaque(inputs, stage, out):
    positions = [f"{m}_{axis}" for m in ("hand", "elbow") for axis in "xyz"] + [
        "handle_x",
        "handle_y",
    ]
    cortical = [f"area2_contact_{c}" for c in CONTACTS]
    units = ["mm"] * 8 + ["spikes/10 ms"] * 37
    channels = positions + cortical
    details = {
        "source": "Chowdhury, Glaser and Miller, Dryad 10.5061/dryad.nk98sf7q7, CC0; one macaque reaching in a planar task.",
        "history": "20 consecutive completed 10-ms bins from k-20 through k-1. Optical marker positions converted from metres and handle from cm into mm. All available local sorts, including sort zero, summed once on each of 37 predeclared acquisition contacts; original guide differs across days.",
        "group_definition": "Original trial nested within date and physical block. Earlier date train only. Both physical blocks seven days later held. This is one animal.",
        "metadata": "Block, workspace, go ordinal, native forecast row and original trial stored for auditing. They do not enter X.",
        "limits": "Processed camera clock and offline spike sorting. Same electrode ID across days does not establish neuron identity. Movement and neural counts co-recorded within each row.",
    }
    for split, (name, checksum) in MACAQUE.items():
        if (split == "train") != (stage == "train"):
            continue
        checked(inputs / name, checksum)
        with np.load(inputs / name, allow_pickle=False) as a:
            k = a["k"]
            assert np.array_equal(a["history_rows"], k[:, None] + np.arange(-20, 0))
            assert np.array_equal(a["movement_rows"], k[:, None] + np.arange(10))
            guide = a["all_guide"]
            h = a["all_history"]
            c = a["all_concurrent"]

            def pool(data, guide=guide):
                part = []
                for contact in CONTACTS:
                    match = guide[:, 0] == contact
                    assert np.any(match & (guide[:, 1] == 0))
                    val = data[:, :, match]
                    assert np.all(
                        ~np.isfinite(val) | ((val >= 0) & (val == np.floor(val)))
                    )
                    part.append(val.sum(axis=2))
                return np.stack(part, axis=2)

            history = pool(h)
            scale = np.array([1000.0] * 6 + [10.0] * 2)
            pos = a["pose"] * scale
            x = np.concatenate([pos, history], 2)
            fields = {
                "X": x,
                "group": a["block"] * 1_000_000 + a["original"],
                "original": a["original"],
                "block": a["block"],
                "workspace": a["workspace"],
                "ordinal": a["ordinal"],
                "issue": k,
            }
            if split == "train":
                fields["development_fold"] = a["fold"]
            motion = schema(
                "continuous",
                channels,
                units,
                [f"delta_{s}" for s in positions],
                ["mm"] * 8,
                20,
                **details,
                target="Endpoint displacement relative to k-1 at k+9 (100 ms).",
                baseline_description="Constant-velocity extrapolation of displacement over last four intersample intervals.",
            )
            save(
                out,
                "macaque_cortex_to_motion",
                split,
                motion,
                **fields,
                y=a["movement"][:, -1] * scale,
                baseline=(pos[:, -1] - pos[:, -5]) * 2.5,
            )
            counts = schema(
                "count",
                channels,
                units,
                cortical,
                ["spikes/100 ms"] * 37,
                20,
                **details,
                target="Summed source-observed contact spike counts for k through k+9 (100 ms).",
                baseline_description="Previous 100 ms observed contact totals.",
            )
            save(
                out,
                "macaque_motion_to_cortex",
                split,
                counts,
                **fields,
                y=pool(c).sum(1),
                baseline=history[:, -10:].sum(1),
            )
