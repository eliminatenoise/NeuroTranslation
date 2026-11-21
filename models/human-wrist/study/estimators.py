"""Fit on one recording and forecast without opening future camera positions."""

import numpy as np
import bilateral as model
import geometry
import legacy


def fit(training):
    n = len(training["source_block"])
    future = training["future_wrist_px"]
    weights = {}
    for scope, side, mask in (
        ("main", 0, np.ones(n, bool)),
        ("main", 1, np.ones(n, bool)),
        ("small16", 0, np.arange(n) < 16),
    ):
        prefix = f"{scope}__{model.SIDES[side]}__"
        x, y, vel, valid, _, stats = model.head_data(training, future, mask, side)
        weights.update({prefix + k: v for k, v in stats.items()})
        for modality in model.MODALITIES:
            tokens = x.copy()
            if modality == "pose":
                tokens[:, :, 10:] = 0
            for treatment in model.TREATMENTS:
                stem = f"{treatment}_{modality}"
                normalized = model.targets(y, vel, valid, stats, treatment)
                linear = model.ridge(tokens, normalized, valid, treatment == "direct")
                weights.update({prefix + "ridge_" + stem + "__" + k: v for k, v in linear.items()})
                for seed in model.SEEDS:
                    head = prefix + f"transformer_{stem}_s{seed}__"
                    params, loss, _ = model.fit_net(
                        tokens, normalized, valid, seed, treatment, "cpu"
                    )
                    weights.update({head + k: v for k, v in params.items()})
                    weights[head + "loss"] = loss
    geometric = {}
    for name, mode, separate in (
        ("segments_shared", "segments", False),
        ("segments_by_side", "segments", True),
        ("whole_shared", "whole", False),
    ):
        geometric[name] = geometry.fit(
            training["prior_pose_px"], future, training["source_block"], mode, separate
        )
    return weights, geometric, legacy.training(training)


def predict(inputs, weights, geometric, historical):
    if any("target" in k or "future" in k or "outcome" in k for k in inputs):
        raise ValueError("Held prediction requires an earlier-input-only archive")
    outputs, meta = model.forecast(inputs, weights)
    x = inputs["prior_pose_px"]
    anchor = geometry.anchors(x)
    v = (anchor - x[:, 0, (0, 3)]) / 14.0
    geo = {
        "zero": np.repeat(anchor[:, None], 2, axis=1),
        "velocity": anchor[:, None] + np.array([8.0, 15.0])[None, :, None, None] * v[:, None],
    }
    geo.update({k: geometry.forecast(x, v) for k, v in geometric.items()})
    for k, v in geo.items():
        outputs["geo_" + k] = np.where(meta["pose_qc"][:, None, :, None], v, np.nan)
    outputs.update(legacy.forecast(inputs, historical))
    if len(outputs) != 110:
        raise RuntimeError(
            "Study requires 82 new methods, five geometric methods and 23 historical methods"
        )
    return outputs, meta
