"""One source-conditioned movement forecaster for five DSADS accelerometers."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import numpy as np
import torch

from aligned_forecast import AlignedQuery, AlignedTarget, ForecastRows
from broader_learner import (MODALITIES, DirectionSpec, HandArmLearner, ModelSpec,
                             ModalityBatch, ModalitySpec, Normalizer, ObservationBatch,
                             QueryBatch, SourceSpec, TaskSpec)

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
PLAN = json.loads(PROTOCOL.read_text())
PARTS = tuple(PLAN["channels_zero_based"])
MOTION = "measured_motion"
CLOCK = "DSADS-25Hz-file-local"
ALIGN = "DSADS-original-rows"
TASK = "same-unit-3-row-forecast"
BATCH = PLAN["optimizer"]["batch_size"]
TASK_SPEC = TaskSpec(TASK, CLOCK, ALIGN, "selected-unit-local-XYZ", "offline",
                     ("constant",), ("dimensionless",), ("task_constant",), ("design",),
                     BATCH, 16, 1, 0.600000000001, 0.119999999999, 0.120000000001)


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def source(part):
    if part not in PARTS:
        raise ValueError(f"Unknown body part {part!r}")
    return f"DSADS-{part}-accelerometer"


def direction(part):
    return DirectionSpec("same-unit-forecast", "same-placement-past-accelerometer-XYZ",
                         (MOTION,), (MOTION,), {MOTION: source(part)}, "not_a_neural_inverse")


def make_model(stats, parents):
    units = ("native accelerometer value",) * 3
    measured = ModalitySpec(MOTION, tuple("XYZ"), units, ("declared_stored",) * 3,
                            (None,) * 3, "selected unit's local frame")
    interfaces = [measured]
    for kind in MODALITIES:
        if kind != MOTION:
            interfaces.append(ModalitySpec(kind, ("unavailable",), ("unspecified",),
                                           ("declared_stored",), (None,), "unavailable"))
    sources, norms = [], {}
    for part in PARTS:
        name = source(part)
        sources.append(SourceSpec(name, MOTION, "human", part, f"{part} unit's local frame",
                                  tuple(f"{part}-{axis}" for axis in "XYZ"), units,
                                  measured.unit_status, measured.calibration_ids, ("measured",) * 3,
                                  "UCI 10.24432/C5C59F", "DSADS", CLOCK, ALIGN))
        norms[name] = Normalizer(tuple(stats[part]["center"]), tuple(stats[part]["scale"]),
                                 frozenset(parents), "TRAIN", f"TRAIN-{part}-XYZ")
    spec = ModelSpec(**PLAN["model"], persistence_residual_sources=tuple(source(p) for p in PARTS))
    return HandArmLearner(TASK_SPEC, spec, interfaces, sources, norms)


@dataclass(frozen=True)
class Events:
    part: str
    members: tuple
    rows: np.ndarray
    values: np.ndarray


def observation(part, members, cutoffs, values, partition):
    sid = source(part)
    cutoffs = np.asarray(cutoffs, dtype=np.int64)
    n = len(members)
    if cutoffs.shape != (n,) or values.shape != (n, 16, 3) or not np.isfinite(values).all():
        raise ValueError("Each source needs 16 complete finite XYZ readings")
    ids = tuple(f"{m}#{part}@{row}" for m, row in zip(members, cutoffs))
    times = torch.from_numpy((cutoffs[:, None] + np.arange(-15, 1)) / 25)
    tensor = torch.from_numpy(values.astype(np.float32))
    if not torch.isfinite(tensor).all():
        raise ValueError("Input is outside the finite float32 sensor range")
    past = ModalityBatch(sid, ids, members, sid, tensor, torch.ones_like(tensor, dtype=torch.bool),
                         times[..., None].expand_as(tensor))
    obs = ObservationBatch(ids, members, partition, TASK, CLOCK, ALIGN, sid, times,
                           torch.ones_like(times, dtype=torch.bool), torch.ones((n, 1)),
                           torch.zeros((n, 1), dtype=torch.float64), {MOTION: past})
    requested = torch.from_numpy((cutoffs[:, None] + 3) / 25)
    header = ForecastRows(ids, members, TASK, CLOCK, ALIGN, partition, sid, times[:, -1])
    return obs, AlignedQuery(header, QueryBatch(requested, torch.ones_like(requested, dtype=torch.bool)))


def targets(events):
    sid = source(events.part)
    cutoffs = events.rows - 3
    ids = tuple(f"{m}#{events.part}@{row}" for m, row in zip(events.members, cutoffs))
    header = ForecastRows(ids, events.members, TASK, CLOCK, ALIGN, "TRAIN", sid,
                          torch.from_numpy(cutoffs / 25))
    event_times = torch.from_numpy(events.rows[:, None] / 25)
    values = torch.tensor(events.values[:, None], dtype=torch.float32)
    record = ModalityBatch(sid, ids, events.members, sid, values,
                           torch.ones_like(values, dtype=torch.bool), event_times[..., None].expand_as(values))
    return {MOTION: AlignedTarget(header, record, event_times)}


def estimate(model, part, obs, query):
    d = model.predict(obs, query.grid, direction(part))[MOTION]
    stored = model.to_stored_units(MOTION, d)
    mean = stored.mean[:, 0].numpy().astype(np.float64)
    variance = stored.variance[:, 0].numpy().astype(np.float64)
    if not np.isfinite(mean).all() or not np.isfinite(variance).all() or (variance <= 0).any():
        raise ValueError("Forecast outside finite numeric range")
    return mean, variance


def load_checkpoint(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint["protocol_sha256"] != digest(PROTOCOL) or tuple(checkpoint["parts"]) != PARTS:
        raise ValueError("Checkpoint differs from its sensor or study definitions")
    for name, expected in checkpoint["model_sources"].items():
        if digest(HERE / name) != expected:
            raise ValueError(f"Model implementation changed: {name}")
    model = make_model(checkpoint["stats"], checkpoint["parents"])
    model.load_state_dict(checkpoint["weights"], strict=True)
    return model.eval(), checkpoint
