"""Check the row identities and event times of a supervised forecast before its update.

Use aligned_forecast_step when the data producer supplies independent query and
target metadata. The direct TrainingSession.step API relies on the caller to check
alignment. Obtain target event times from the target source in the declared clock.
Copying query times onto labels cannot establish when those labels were measured.
"""

from dataclasses import dataclass
from typing import Mapping

import torch
from torch import Tensor

from broader_learner import (
    ModalityBatch, ObservationBatch, QueryBatch, TaskSpec, TrainingSession,
    check_grid, cpu_tensor, identity_tuple, require,
)


@dataclass(frozen=True)
class ForecastRows:
    """Ordered source-window identities and last valid history times in seconds."""

    sample_ids: tuple[str, ...]
    raw_parent_ids: tuple[str, ...]
    task_id: str
    clock_id: str
    alignment_id: str
    partition: str
    pairing_id: str
    history_end_s: Tensor

    def __post_init__(self) -> None:
        for field in ("sample_ids", "raw_parent_ids"):
            object.__setattr__(self, field, identity_tuple(getattr(self, field), field))

    def check(self, observation: ObservationBatch, history_end_s: Tensor, name: str) -> None:
        for field in ("sample_ids", "raw_parent_ids", "task_id", "clock_id",
                      "alignment_id", "partition", "pairing_id"):
            require(getattr(self, field) == getattr(observation, field),
                    f"{name} {field} differs from the observation")
        cpu_tensor(self.history_end_s, torch.float64, name + " history_end_s")
        require(torch.equal(self.history_end_s, history_end_s),
                name + " history_end_s differs from the observation")


@dataclass(frozen=True)
class AlignedQuery:
    rows: ForecastRows
    grid: QueryBatch


@dataclass(frozen=True)
class AlignedTarget:
    """Event seconds are [row, step] or [row, step, feature] on the target clock.

    Each observed cell must correspond to the requested instant. Unobserved cells
    may carry NaN. The record retains its separate available_at_s processing times.
    """

    rows: ForecastRows
    record: ModalityBatch
    event_times_s: Tensor


def validate_aligned_forecast(task: TaskSpec, observation: ObservationBatch,
                              query: AlignedQuery, targets: Mapping[str, AlignedTarget],
                              target_source_ids: Mapping[str, str]) -> None:
    """Check a batch without changing the model, its optimizer or its update count."""
    require((observation.task_id, observation.clock_id, observation.alignment_id)
            == (task.task_id, task.clock_id, task.alignment_id),
            "Observation task, clock or alignment differs from the declared task")
    require(type(observation.pairing_id) is str and bool(observation.pairing_id),
            "Supervised alignment requires an observation pairing identity")
    batch, _ = check_grid(observation.times_s, observation.valid_steps,
                          task.max_context_steps, "history")
    require(batch <= task.max_batch and len(observation.sample_ids) == batch
            and len(set(observation.sample_ids)) == batch and len(observation.raw_parent_ids) == batch,
            "History row identities or batch size differ from the declared grid")
    last = observation.valid_steps.sum(dim=1, keepdim=True) - 1
    history_end_s = observation.times_s.gather(1, last).squeeze(1)
    query.rows.check(observation, history_end_s, "Query")

    grid = query.grid
    shape = check_grid(grid.times_s, grid.valid_steps, task.max_query_steps, "query")
    require(shape[0] == batch, "Query row count differs from the observation")
    horizon = (grid.times_s - history_end_s[:, None])[grid.valid_steps]
    require(bool(((horizon >= task.minimum_horizon_s) & (horizon <= task.maximum_horizon_s)).all()),
            "Query horizon outside the declared forecast range")
    require(bool(targets) and set(targets).issubset(target_source_ids),
            "Supervised alignment requires declared targets")
    has_observed_target = False
    for kind, target in targets.items():
        target.rows.check(observation, history_end_s, kind)
        record = target.record
        require((record.sample_ids, record.raw_parent_ids, record.pairing_id)
                == (target.rows.sample_ids, target.rows.raw_parent_ids, target.rows.pairing_id),
                kind + " value rows differ from the target metadata")
        require(record.source_id == target_source_ids[kind], kind + " target source differs")
        mask = record.observed
        cpu_tensor(mask, torch.bool, kind + " observed")
        require(mask.ndim == 3 and mask.shape[:2] == shape
                and mask.shape == record.values.shape == record.available_at_s.shape,
                kind + " target dimensions differ from the query or value record")
        require(not bool((mask & ~grid.valid_steps[..., None]).any()),
                kind + " has an observed target on query padding")
        times = target.event_times_s
        cpu_tensor(times, torch.float64, kind + " event_times_s")
        if times.shape == shape:
            times = times[..., None].expand_as(mask)
        require(times.shape == mask.shape, kind + " target event grid has the wrong shape")
        requested = grid.times_s[..., None].expand_as(mask)
        observed_times = times[mask]
        has_observed_target |= observed_times.numel() > 0
        require(torch.equal(observed_times, requested[mask]),
                kind + " target event time differs from the requested query")
    require(has_observed_target, "No observed target events in the supervised batch")


def aligned_forecast_step(session: TrainingSession, observation: ObservationBatch,
                          query: AlignedQuery, targets: Mapping[str, AlignedTarget]) -> dict:
    """Submit one checked train/fine-tune batch to its existing session."""
    require(session.phase.kind in ("train", "fine_tune"), "Expected a supervised learning phase")
    targets = dict(targets)
    validate_aligned_forecast(session.model.task, observation, query, targets,
                              session.phase.direction.target_source_ids)
    records = {kind: target.record for kind, target in targets.items()}
    return session.step(observation, targets=records, query=query.grid)
