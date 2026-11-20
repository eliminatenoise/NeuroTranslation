"""Bind the read-only wrist window and a separate analytic fixture to HandArmLearner."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

import torch

from aligned_forecast import AlignedQuery, AlignedTarget, ForecastRows, validate_aligned_forecast
from broader_learner import (
    MODALITIES, DirectionSpec, HandArmLearner, ModelSpec, ModalitySpec,
    ScientificFreeze, SourceSpec, TaskSpec, configure_cpu_runtime, fit_train_normalizer,
    tensorize_modality, tensorize_observation, tensorize_query,
)
from wrist_bridge import (
    ALIGNMENT, CHANNELS, CLOCK, CONTEXT, DOI, HISTORY, PAIR, PARENT, RATE, SOURCE_IDS,
    TASK, context_features, modality_record, replay_sample,
)

SIM_KIND = "physics_generated"
SIM_ID = "ideal-torsional-spring-v1"
SIM_FEATURES = ("angle_rad", "angular_velocity_rad_s", "restoring_torque_Nm")
SIM_UNITS = ("rad", "rad/s", "N m")
SIM_CLOCK = "analytic-64-Hz"
SIM_TRAIN = SIM_ID + "/invented-amplitude-0.4"
SIM_DEMO = SIM_ID + "/invented-amplitude-0.2"
SIM_INERTIA = 0.02
SIM_STIFFNESS = 0.50


def specification(name, clock, alignment, mechanics, source, max_horizon):
    return TaskSpec(name, clock, alignment, mechanics, "offline-row-availability",
                    CONTEXT, ("indicator",) * len(CONTEXT),
                    ("task_constant",) * (len(CONTEXT) - 1) + ("derived",),
                    (source,) * len(CONTEXT), 1, HISTORY, 1, 1.0, 1 / RATE, max_horizon)


def replay_contracts():
    spec = specification(TASK, CLOCK, ALIGNMENT, "right wrist encoder angles only", DOI, 3.0)
    units = {"neural": ("uV",), "myographic": ("uV",), "measured_motion": ("deg", "deg")}
    frames = {"neural": "scalp C3", "myographic": "right forearm M3L minus M3R",
              "measured_motion": "right wrist; extension positive and radial deviation positive"}
    sources = {}
    for family, names in CHANNELS.items():
        status = "processed" if family == "myographic" else "declared_stored"
        provenance = "derived" if family == "myographic" else "measured"
        sources[family] = SourceSpec(SOURCE_IDS[family], family, "human", frames[family], frames[family],
                                     names, units[family], (status,) * len(names), (None,) * len(names),
                                     (provenance,) * len(names), DOI, PARENT, CLOCK, ALIGNMENT)
        sources[family].validate()
    spec.validate()
    return spec, sources


def replay_tensors(path, cutoff_offset=256, target_offset=384):
    """Return an aligned DEV observation, query and target. This path has no training entry point."""
    window = replay_sample(path, cutoff_offset, target_offset)
    obs = tensorize_observation(window["observations"], "float32")
    target = window["target"]
    record = tensorize_modality(target["record"], "float32")
    rows = ForecastRows(obs.sample_ids, obs.raw_parent_ids, TASK, CLOCK, ALIGNMENT, "DEV",
                        PAIR, obs.times_s[:, -1])
    query = AlignedQuery(rows, tensorize_query(window["query"]))
    event_times = torch.tensor(target["event_times_s"], dtype=torch.float64)
    targets = {target["family"]: AlignedTarget(rows, record, event_times)}
    task, sources = replay_contracts()
    validate_aligned_forecast(task, obs, query, targets, {"measured_motion": sources["measured_motion"].source_id})
    return obs, query, targets


def oscillator(t, amplitude):
    """Closed-form free response of an invented, undamped rotational spring, initially at rest."""
    omega = math.sqrt(SIM_STIFFNESS / SIM_INERTIA)
    angle = amplitude * math.cos(omega * t)
    return [angle, -amplitude * omega * math.sin(omega * t), -SIM_STIFFNESS * angle]


def simulated_window(parent, amplitude, partition):
    times = [i / 64 for i in range(HISTORY)]
    context, available = context_features("release wrist", 0, None, HISTORY - 1, 64)
    record = modality_record(parent, parent, parent, SIM_ID, [oscillator(t, amplitude) for t in times], times)
    return tensorize_observation({
        "sample_ids": [parent], "raw_parent_ids": [parent], "partition": partition,
        "task_id": SIM_ID, "clock_id": SIM_CLOCK, "alignment_id": SIM_ID, "pairing_id": parent,
        "times_s": [times], "valid_steps": [[True] * HISTORY],
        "context_values": [context], "context_available_at_s": [available], "modalities": {SIM_KIND: record},
    }, "float32")


def synthetic_check():
    """Run a fresh Transformer twice, varying only the supplied protocol context."""
    spec = specification(SIM_ID, SIM_CLOCK, SIM_ID, "J*q'' = -k*q", SIM_ID, 0.25)
    interface = ModalitySpec(SIM_KIND, SIM_FEATURES, SIM_UNITS, ("simulated_units",) * 3,
                             (None,) * 3, "single virtual rotational joint")
    interfaces = [interface] + [ModalitySpec(kind, ("absent",), ("unavailable",), ("declared_stored",),
                                             (None,), "unobserved") for kind in MODALITIES if kind != SIM_KIND]
    source = SourceSpec(SIM_ID, SIM_KIND, "synthetic", "ideal rotational spring", interface.frame,
                        SIM_FEATURES, SIM_UNITS, interface.unit_status, interface.calibration_ids,
                        ("simulated",) * 3, SIM_ID, SIM_ID, SIM_CLOCK, SIM_ID)
    freeze = ScientificFreeze(*([SIM_ID] * 8), frozenset({SIM_TRAIN}), frozenset({SIM_DEMO}),
                              frozenset({SIM_TRAIN}))
    invented = simulated_window(SIM_TRAIN, 0.4, "TRAIN")
    norm = fit_train_normalizer([invented], source, spec, freeze, "invented-spring-moments",
                                1e-6, "float32").normalizer
    model = HandArmLearner(spec, ModelSpec(8, 2, 1, 16, 0.0, "float32", 42, -8, 8),
                           interfaces, [source], {SIM_ID: norm}).eval()
    obs = simulated_window(SIM_DEMO, 0.2, "DEV")
    direction = DirectionSpec("synthetic-forward", "history-and-protocol", (SIM_KIND,), (SIM_KIND,),
                              {SIM_KIND: SIM_ID}, "not_a_neural_inverse")
    t = 0.5
    query = tensorize_query({"times_s": [[t]], "valid_steps": [[True]]})
    output = model.predict(obs, query, direction)[SIM_KIND].mean
    ablated = replace(obs, context_values=torch.zeros_like(obs.context_values))
    neutral = model.predict(ablated, query, direction)[SIM_KIND].mean
    return {"weights": "seeded random Transformer; no optimizer or checkpoint",
            "source": SIM_ID, "synthetic_normalizer_fit_parent": SIM_TRAIN,
            "inputs": list(obs.modalities), "prediction_shape": list(output.shape),
            "finite": bool(torch.isfinite(output).all()),
            "max_abs_change_removing_protocol_words_normalized": (output - neutral).abs().max().item(),
            "reference_at_0_5s": dict(zip(SIM_FEATURES, oscillator(t, 0.2), strict=True)),
            "parameters": {"inertia_kg_m2": SIM_INERTIA, "stiffness_Nm_per_rad": SIM_STIFFNESS},
            "fitted_model_updates": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("real", "synthetic"))
    p.add_argument("replay", nargs="?", type=Path)
    p.add_argument("--threads", default=1, choices=(1, 2), type=int)
    args = p.parse_args()
    route = configure_cpu_runtime(args.threads, 1, True)
    if args.mode == "synthetic":
        result = synthetic_check()
    else:
        if args.replay is None:
            p.error("real mode requires the frozen replay JSON path")
        obs, query, targets = replay_tensors(args.replay)
        target = targets["measured_motion"]
        result = {"partition": obs.partition, "paired_identity": obs.pairing_id,
                  "observed_cells": {k: int(v.observed.sum()) for k, v in obs.modalities.items()},
                  "last_history_row": round(obs.times_s[0, -1].item() * RATE),
                  "requested_target_row": round(query.grid.times_s.item() * RATE),
                  "actual_target_row": round(target.event_times_s.item() * RATE),
                  "target_encoder_deg_float32": target.record.values.tolist()[0][0],
                  "training_loss_weight": 0.0, "model_invocations": 0, "fitted_model_updates": 0}
    print(json.dumps({"cpu": route, "result": result}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
