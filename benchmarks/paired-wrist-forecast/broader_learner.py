"""Hand/arm learner with an opt-in persistence residual for self-forecasts.

This module has no file loader, CLI, model download, checkpoint writer or RL
objective. Root owns later source/dependency/data/runtime/scientific admission.
Contract identifiers below are consistency fields, never native authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from contextlib import contextmanager
from threading import RLock
import math
from types import MappingProxyType
from typing import Mapping, Sequence

import torch
from torch import Tensor, nn


MODALITIES = ("neural", "myographic", "measured_motion", "physics_generated")
GROUPS = ("encoders", "source_embeddings", "context", "fusion", "temporal",
          "forecast_decoder", "heads")
UNIT_STATUS = ("declared_stored", "processed", "simulated_units", "calibrated_physical")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def positive_int(value: int, name: str) -> None:
    require(type(value) is int and value > 0, name + " must be a positive integer")


def finite_number(value: float, name: str) -> None:
    require(type(value) in (int, float) and math.isfinite(value), name + " must be finite")


def freeze_tuple_fields(instance, names: Sequence[str]) -> None:
    for name in names:
        value = getattr(instance, name)
        require(type(value) in (list, tuple), name + " must be a sequence, not a string")
        object.__setattr__(instance, name, tuple(value))


def identity_tuple(value, name: str) -> tuple[str, ...]:
    require(type(value) in (list, tuple) and bool(value)
            and all(type(item) is str and item for item in value), name + " requires explicit string IDs")
    return tuple(value)


_CPU_RNG_LOCK = RLock()


@contextmanager
def _seeded_cpu_rng(seed: int):
    """Save, seed and restore only the default CPU RNG; no device discovery.

    Public CPU get/set state APIs and an explicit CPU Generator are used. This
    lock serializes this module's CPU RNG regions, not unrelated external draws.
    Root retains isolated-process/coordinated-caller qualification ownership.
    """
    with _CPU_RNG_LOCK:
        saved = torch.get_rng_state()
        primary = None
        try:
            generator = torch.Generator(device="cpu")
            generator.manual_seed(seed)
            torch.set_rng_state(generator.get_state())
            yield
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                torch.set_rng_state(saved)
            except BaseException as restoration:
                if primary is None:
                    raise
                # Retain both actual failures; restoration must not erase primary.
                raise BaseExceptionGroup("CPU RNG operation and restoration failed",
                                         [primary, restoration]) from None


@dataclass(frozen=True)
class ModalitySpec:
    modality: str
    feature_names: tuple[str, ...]
    units: tuple[str, ...]
    unit_status: tuple[str, ...]
    calibration_ids: tuple[str | None, ...]
    frame: str

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("feature_names", "units", "unit_status", "calibration_ids"))

    def validate(self) -> None:
        require(self.modality in MODALITIES, "Unknown modality")
        c = len(self.feature_names)
        require(c > 0 and len(set(self.feature_names)) == c, "Unique feature names required")
        require(all(type(n) is str and n for n in self.feature_names), "Empty feature name")
        require(len(self.units) == len(self.unit_status) == len(self.calibration_ids) == c,
                "Per-feature units/status/calibration lengths differ")
        require(all(type(u) is str and u for u in self.units), "Units must be explicit")
        require(bool(self.frame), "Frame must be explicit")
        for status, calibration in zip(self.unit_status, self.calibration_ids):
            require(status in UNIT_STATUS, "Unknown unit status")
            if status == "calibrated_physical":
                require(type(calibration) is str and bool(calibration),
                        "Physical calibration requires its separate evidence identity")
            else:
                require(calibration is None, "Uncalibrated features must not carry a calibration ID")


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    modality: str
    organism: str
    anatomy: str
    frame: str
    feature_names: tuple[str, ...]
    units: tuple[str, ...]
    unit_status: tuple[str, ...]
    calibration_ids: tuple[str | None, ...]
    provenance: tuple[str, ...]
    release: str
    lineage_id: str
    clock_id: str
    alignment_id: str

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("feature_names", "units", "unit_status", "calibration_ids", "provenance"))

    def validate(self, modality: ModalitySpec | None = None) -> None:
        require(self.modality in MODALITIES, "Unknown source modality")
        if modality is not None:
            require(self.modality == modality.modality, "Source/modality mismatch")
        ModalitySpec(self.modality, self.feature_names, self.units, self.unit_status,
                     self.calibration_ids, self.frame).validate()
        for name in ("source_id", "organism", "anatomy", "frame", "release",
                     "lineage_id", "clock_id", "alignment_id"):
            require(type(getattr(self, name)) is str and bool(getattr(self, name)),
                    "Source field missing: " + name)
        # Different sources within a family keep their native declared feature
        # meanings. A learned projection is not an anatomical/physical conversion.
        require(len(self.provenance) == len(self.feature_names), "Per-feature provenance required")
        require(all(p in ("measured", "derived", "simulated") for p in self.provenance),
                "Unknown feature provenance")
        if self.modality == "physics_generated":
            require(all(p == "simulated" for p in self.provenance),
                    "Fitted measurements cannot be relabelled physics-generated")
        if self.modality == "measured_motion":
            require(all(p in ("measured", "derived") for p in self.provenance),
                    "Simulated motion belongs to a declared physics contribution")
        for provenance, status in zip(self.provenance, self.unit_status):
            require(not (provenance == "simulated" and status == "calibrated_physical"),
                    "Simulation is not a physical measurement calibration")
            require(provenance != "simulated" or status == "simulated_units",
                    "Simulated features must retain simulated-unit status")


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    clock_id: str
    alignment_id: str
    mechanics_contract_id: str
    availability_contract_id: str
    context_feature_names: tuple[str, ...]
    context_units: tuple[str, ...]
    context_provenance: tuple[str, ...]
    context_source_ids: tuple[str, ...]
    max_batch: int
    max_context_steps: int
    max_query_steps: int
    max_history_duration_s: float
    minimum_horizon_s: float
    maximum_horizon_s: float

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("context_feature_names", "context_units",
                                   "context_provenance", "context_source_ids"))

    def validate(self) -> None:
        for name in ("task_id", "clock_id", "alignment_id", "mechanics_contract_id",
                     "availability_contract_id"):
            require(type(getattr(self, name)) is str and bool(getattr(self, name)),
                    "Missing task contract: " + name)
        require(len(self.context_feature_names) > 0, "Task/mechanics context must be declared")
        require(len(set(self.context_feature_names)) == len(self.context_feature_names),
                "Duplicate context feature")
        require(len(self.context_feature_names) == len(self.context_units)
                and all(self.context_units), "Context units missing")
        require(len(self.context_feature_names) == len(self.context_provenance)
                == len(self.context_source_ids) and all(self.context_source_ids),
                "Context provenance/source identities required")
        require(all(p in ("measured", "derived", "simulated", "task_constant")
                    for p in self.context_provenance), "Unknown context provenance")
        for name in ("max_batch", "max_context_steps", "max_query_steps"):
            positive_int(getattr(self, name), name)
        for name in ("max_history_duration_s", "minimum_horizon_s", "maximum_horizon_s"):
            finite_number(getattr(self, name), name)
        require(self.max_history_duration_s > 0 and self.minimum_horizon_s >= 0
                and self.maximum_horizon_s >= self.minimum_horizon_s,
                "Invalid declared time bounds")


@dataclass(frozen=True)
class ModelSpec:
    width: int
    heads: int
    temporal_layers: int
    feedforward_width: int
    dropout: float
    precision: str
    initialization_seed: int
    log_variance_min: float
    log_variance_max: float
    persistence_residual_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("persistence_residual_sources",))

    def validate(self) -> None:
        ids = self.persistence_residual_sources
        require(all(type(sid) is str and sid for sid in ids) and len(ids) == len(set(ids)),
                "Persistence residual sources must be unique explicit source IDs")
        for name in ("width", "heads", "temporal_layers", "feedforward_width"):
            positive_int(getattr(self, name), name)
        require(self.width % self.heads == 0, "Width must be divisible by attention heads")
        require(self.precision in ("float32", "float64"), "Explicit float32/float64 required")
        require(type(self.initialization_seed) is int and 0 <= self.initialization_seed < 2**63,
                "Invalid initialization seed")
        finite_number(self.dropout, "dropout")
        require(0 <= self.dropout < 1, "Invalid dropout")
        finite_number(self.log_variance_min, "log_variance_min")
        finite_number(self.log_variance_max, "log_variance_max")
        require(self.log_variance_min < self.log_variance_max, "Invalid log-variance bounds")
        limits = torch.finfo(dtype_for(self.precision))
        require(self.log_variance_min >= math.log(limits.tiny)
                and self.log_variance_max < math.log(limits.max) - math.log(2),
                "Log-variance bounds exceed the declared dtype's exponential range")


@dataclass(frozen=True)
class Normalizer:
    center: tuple[float, ...]
    scale: tuple[float, ...]
    fit_parent_ids: frozenset[str]
    fit_partition: str
    normalization_id: str

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("center", "scale"))
        object.__setattr__(self, "fit_parent_ids", frozenset(self.fit_parent_ids))

    def validate(self, channels: int) -> None:
        require(len(self.center) == len(self.scale) == channels, "Normalizer shape mismatch")
        require(self.fit_partition == "TRAIN" and bool(self.fit_parent_ids),
                "Normalizer must identify TRAIN-only fit parents")
        require(bool(self.normalization_id), "Normalizer identity missing")
        for center, scale in zip(self.center, self.scale):
            finite_number(center, "center")
            finite_number(scale, "scale")
            require(scale > 0, "Positive scale required; constant features need an explicit policy")


@dataclass(frozen=True)
class ModalityBatch:
    source_id: str
    sample_ids: tuple[str, ...]
    raw_parent_ids: tuple[str, ...]
    pairing_id: str | None
    values: Tensor
    observed: Tensor
    available_at_s: Tensor

    def __post_init__(self) -> None:
        object.__setattr__(self, "sample_ids", identity_tuple(self.sample_ids, "sample_ids"))
        object.__setattr__(self, "raw_parent_ids", identity_tuple(self.raw_parent_ids, "raw_parent_ids"))
        require(self.pairing_id is None or (type(self.pairing_id) is str and bool(self.pairing_id)),
                "Pairing ID must be an explicit string or null")


@dataclass(frozen=True)
class ObservationBatch:
    sample_ids: tuple[str, ...]
    raw_parent_ids: tuple[str, ...]
    partition: str
    task_id: str
    clock_id: str
    alignment_id: str
    pairing_id: str | None
    times_s: Tensor
    valid_steps: Tensor
    context_values: Tensor
    context_available_at_s: Tensor
    modalities: Mapping[str, ModalityBatch]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sample_ids", identity_tuple(self.sample_ids, "sample_ids"))
        object.__setattr__(self, "raw_parent_ids", identity_tuple(self.raw_parent_ids, "raw_parent_ids"))
        object.__setattr__(self, "modalities", MappingProxyType(dict(self.modalities)))
        require(self.pairing_id is None or (type(self.pairing_id) is str and bool(self.pairing_id)),
                "Pairing ID must be an explicit string or null")


@dataclass(frozen=True)
class QueryBatch:
    times_s: Tensor
    valid_steps: Tensor


@dataclass(frozen=True)
class DirectionSpec:
    direction_id: str
    information_set_id: str
    inputs: tuple[str, ...]
    targets: tuple[str, ...]
    target_source_ids: Mapping[str, str]
    inverse_interpretation: str

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("inputs", "targets"))
        object.__setattr__(self, "target_source_ids", MappingProxyType(dict(self.target_source_ids)))

    def validate(self) -> None:
        require(bool(self.direction_id) and bool(self.information_set_id),
                "Direction and available-information identities required")
        require(bool(self.inputs) and bool(self.targets), "Empty input or target set")
        for group in (self.inputs, self.targets):
            require(len(set(group)) == len(group) and all(k in MODALITIES for k in group),
                    "Invalid direction modalities")
        require(set(self.target_source_ids) == set(self.targets)
                and all(type(s) is str and s for s in self.target_source_ids.values()),
                "Each target needs its exact declared source/head identity")
        if "neural" in self.targets:
            require(self.inverse_interpretation == "conditional_nonunique_recorded_features",
                    "Reverse features are not a unique neural inverse or sensory writing")
        else:
            require(self.inverse_interpretation == "not_a_neural_inverse",
                    "Explicit output interpretation required")


@dataclass(frozen=True)
class ScientificFreeze:
    freeze_id: str
    source_manifest_id: str
    split_id: str
    batch_order_id: str
    comparisons_id: str
    threshold_domain_id: str
    uncertainty_id: str
    resource_lease_id: str
    train_parent_ids: frozenset[str]
    excluded_parent_ids: frozenset[str]
    allowed_pairing_ids: frozenset[str]

    def __post_init__(self) -> None:
        for name in ("train_parent_ids", "excluded_parent_ids", "allowed_pairing_ids"):
            value = getattr(self, name)
            require(not isinstance(value, str), name + " requires explicit identities")
            object.__setattr__(self, name, frozenset(value))

    def validate(self) -> None:
        for name in ("freeze_id", "source_manifest_id", "split_id", "batch_order_id",
                     "comparisons_id", "threshold_domain_id", "uncertainty_id", "resource_lease_id"):
            require(type(getattr(self, name)) is str and bool(getattr(self, name)),
                    "Scientific freeze field missing: " + name)
        require(bool(self.train_parent_ids), "TRAIN parent scope required")
        require(not (self.train_parent_ids & self.excluded_parent_ids), "Partition overlap")
        require(all(type(s) is str and s for group in
                    (self.train_parent_ids, self.excluded_parent_ids, self.allowed_pairing_ids) for s in group),
                "Freeze parent/pairing identities must be strings")
        # These IDs cannot authenticate rights, an independent review or a native lease.


@dataclass(frozen=True)
class PhaseSpec:
    kind: str
    direction: DirectionSpec
    trainable_groups: tuple[str, ...]
    loss_weights: Mapping[str, float]
    learning_rate: float
    adam_betas: tuple[float, float]
    adam_epsilon: float
    weight_decay: float
    max_gradient_norm: float
    max_updates: int
    step_seed: int
    mask_seed: int
    masking_probability: float

    def __post_init__(self) -> None:
        freeze_tuple_fields(self, ("trainable_groups", "adam_betas"))
        object.__setattr__(self, "loss_weights", MappingProxyType(dict(self.loss_weights)))

    def validate(self) -> None:
        require(self.kind in ("pretrain", "train", "fine_tune"), "Unknown learning phase")
        self.direction.validate()
        require(bool(self.trainable_groups) and len(set(self.trainable_groups)) == len(self.trainable_groups)
                and all(g in GROUPS for g in self.trainable_groups), "Explicit trainable groups required")
        require(set(self.loss_weights) == set(self.direction.targets), "Exact target weights required")
        for weight in self.loss_weights.values():
            finite_number(weight, "loss weight")
            require(weight > 0, "Loss weights must be positive")
        for name in ("learning_rate", "adam_epsilon", "max_gradient_norm"):
            finite_number(getattr(self, name), name)
            require(getattr(self, name) > 0, name + " must be positive")
        finite_number(self.weight_decay, "weight_decay")
        require(self.weight_decay >= 0, "Negative weight decay")
        require(len(self.adam_betas) == 2 and all(0 <= b < 1 for b in self.adam_betas),
                "Invalid AdamW betas")
        for beta in self.adam_betas:
            finite_number(beta, "AdamW beta")
        positive_int(self.max_updates, "max_updates")
        for seed in (self.step_seed, self.mask_seed):
            require(type(seed) is int and 0 <= seed < 2**63 - self.max_updates,
                    "Seed/update range invalid")
        finite_number(self.masking_probability, "masking_probability")
        if self.kind == "pretrain":
            require(0 < self.masking_probability < 1, "Pretraining needs an explicit masking probability")
            require(set(self.direction.targets).issubset(self.direction.inputs),
                    "Denoising targets must come from the observed source modalities")
            require("forecast_decoder" not in self.trainable_groups,
                    "Unused forecast decoder must stay frozen during reconstruction")
        else:
            require(self.masking_probability == 0, "No implicit masking augmentation during supervised phases")


@dataclass(frozen=True)
class Distribution:
    mean: Tensor
    log_variance: Tensor
    source_id: str


@dataclass(frozen=True)
class PersistenceDistribution(Distribution):
    # Keep the difference separate from the level. A small correction can vanish
    # when added to a large normalized anchor, even with finite operands.
    last_stored: Tensor
    supported: Tensor
    normalized_change: Tensor


@dataclass(frozen=True)
class StoredUnitDistribution:
    mean: Tensor
    variance: Tensor
    units: tuple[str, ...]
    unit_status: tuple[str, ...]
    calibration_ids: tuple[str | None, ...]
    interpretation: str = "model_conditional_variance_not_calibrated_biological_uncertainty"


def dtype_for(precision: str) -> torch.dtype:
    require(precision in ("float32", "float64"), "Unsupported precision")
    return torch.float64 if precision == "float64" else torch.float32


def configure_cpu_runtime(intraop_threads: int, interop_threads: int,
                          deterministic_algorithms: bool) -> dict[str, int | bool]:
    """Explicit future fresh-process setup, never called on import.

    Root qualifies placement, aggregate process resources and whole invocation.
    These framework settings neither establish resource enforcement nor a gain.
    """
    positive_int(intraop_threads, "intraop_threads")
    positive_int(interop_threads, "interop_threads")
    require(type(deterministic_algorithms) is bool, "Determinism must be explicit")
    torch.set_num_threads(intraop_threads)
    torch.set_num_interop_threads(interop_threads)
    torch.use_deterministic_algorithms(deterministic_algorithms)
    return {"intraop_threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()}


def cpu_tensor(value: Tensor, dtype: torch.dtype, name: str) -> None:
    require(isinstance(value, Tensor) and value.device.type == "cpu" and value.dtype == dtype,
            name + " must use the declared CPU dtype")


def check_grid(times: Tensor, valid: Tensor, maximum_steps: int, name: str) -> tuple[int, int]:
    cpu_tensor(times, torch.float64, name + " times")
    cpu_tensor(valid, torch.bool, name + " valid")
    require(times.ndim == 2 and times.shape == valid.shape, name + " grid shape mismatch")
    b, t = times.shape
    require(b > 0 and 0 < t <= maximum_steps, name + " grid outside declared bounds")
    require(bool(valid[:, 0].all()), name + " requires nonempty right-padded sequences")
    require(not bool((valid[:, 1:] & ~valid[:, :-1]).any()), name + " contains padding holes")
    require(bool(torch.isfinite(times[valid]).all()), name + " has nonfinite observed times")
    pair = valid[:, 1:] & valid[:, :-1]
    require(bool(((times[:, 1:] - times[:, :-1])[pair] > 0).all()),
            name + " observed times must increase strictly")
    return b, t


class TimeFeatures(nn.Module):
    def __init__(self, width: int, dtype: torch.dtype):
        super().__init__()
        # Seconds remain explicit. This is a trainable time basis, not implicit resampling.
        self.net = nn.Sequential(nn.Linear(3, width, device="cpu", dtype=dtype),
                                 nn.GELU(), nn.Linear(width, width, device="cpu", dtype=dtype))

    def forward(self, relative_seconds: Tensor) -> Tensor:
        return self.net(torch.stack((relative_seconds, torch.sin(relative_seconds),
                                     torch.cos(relative_seconds)), dim=-1))


class ForecastDecoder(nn.Module):
    def __init__(self, width: int, heads: int, hidden: int, dropout: float, dtype: torch.dtype):
        super().__init__()
        self.time = TimeFeatures(width, dtype)
        self.attention = nn.MultiheadAttention(width, heads, dropout=dropout,
                                              batch_first=True, device="cpu", dtype=dtype)
        self.norm1 = nn.LayerNorm(width, device="cpu", dtype=dtype)
        self.ff = nn.Sequential(nn.Linear(width, hidden, device="cpu", dtype=dtype), nn.GELU(),
                                nn.Dropout(dropout), nn.Linear(hidden, width, device="cpu", dtype=dtype))
        self.norm2 = nn.LayerNorm(width, device="cpu", dtype=dtype)

    def forward(self, relative_query: Tensor, context: Tensor, memory: Tensor, valid: Tensor) -> Tensor:
        query = self.time(relative_query) + context[:, None, :]
        attended, _ = self.attention(query, memory, memory, key_padding_mask=~valid,
                                     need_weights=False)
        hidden = self.norm1(query + attended)
        return self.norm2(hidden + self.ff(hidden))


class HandArmLearner(nn.Module):
    """Four-interface sequence learner; no default dimensions or admitted payload."""

    def __init__(self, task: TaskSpec, model: ModelSpec, modalities: Sequence[ModalitySpec],
                 sources: Sequence[SourceSpec], normalizers: Mapping[str, Normalizer]):
        super().__init__()
        self._phase_lock = RLock()
        self._phase_owner = None
        task.validate()
        model.validate()
        require(len(modalities) == 4 and {m.modality for m in modalities} == set(MODALITIES),
                "All four typed interfaces must be declared; observations may be absent")
        self.task, self.spec, self.dtype = task, model, dtype_for(model.precision)
        self.modalities = MappingProxyType({m.modality: m for m in modalities})
        for modality in modalities:
            modality.validate()
        require(bool(sources) and len({s.source_id for s in sources}) == len(sources),
                "Unique declared source identities required")
        self.sources = MappingProxyType({s.source_id: s for s in sources})
        require(set(model.persistence_residual_sources).issubset(self.sources),
                "Undeclared persistence residual source")
        for source in sources:
            require(source.modality in self.modalities, "Unknown source modality")
            source.validate(self.modalities[source.modality])
            require(source.clock_id == task.clock_id and source.alignment_id == task.alignment_id,
                    "No implicit alignment or clock conversion")
        self.source_indices = MappingProxyType({s: i for i, s in enumerate(sorted(self.sources))})
        self.source_keys = MappingProxyType({s: "source_" + str(i) for s, i in self.source_indices.items()})
        require(set(normalizers).issubset(self.sources), "Unknown normalizer source")
        self.normalizers = MappingProxyType(dict(normalizers))
        for source_id, norm in normalizers.items():
            norm.validate(len(self.sources[source_id].feature_names))
        # Initialization RNG is isolated from the caller; no training occurs here.
        with _seeded_cpu_rng(model.initialization_seed):
            self.encoders = nn.ModuleDict({
                self.source_keys[sid]: nn.Sequential(
                    nn.Linear(2 * len(source.feature_names), model.width, device="cpu", dtype=self.dtype),
                    nn.GELU(), nn.LayerNorm(model.width, device="cpu", dtype=self.dtype),
                    nn.Linear(model.width, model.width, device="cpu", dtype=self.dtype))
                for sid, source in self.sources.items()})
            self.source_embeddings = nn.Embedding(len(sources), model.width, device="cpu", dtype=self.dtype)
            self.context = nn.Sequential(
                nn.Linear(len(task.context_feature_names), model.width, device="cpu", dtype=self.dtype),
                nn.GELU(), nn.LayerNorm(model.width, device="cpu", dtype=self.dtype))
            self.fusion = nn.MultiheadAttention(model.width, model.heads, dropout=model.dropout,
                                               batch_first=True, device="cpu", dtype=self.dtype)
            self.history_time = TimeFeatures(model.width, self.dtype)
            layer = nn.TransformerEncoderLayer(
                model.width, model.heads, model.feedforward_width, model.dropout,
                activation="gelu", batch_first=True, norm_first=True, device="cpu", dtype=self.dtype)
            self.temporal = nn.TransformerEncoder(layer, model.temporal_layers, enable_nested_tensor=False)
            self.forecast_decoder = ForecastDecoder(model.width, model.heads,
                                                     model.feedforward_width, model.dropout, self.dtype)
            self.heads = nn.ModuleDict({
                self.source_keys[sid]: nn.Sequential(nn.Linear(model.width, model.width, device="cpu", dtype=self.dtype),
                                    nn.GELU(), nn.Linear(model.width, 2 * len(m.feature_names),
                                                         device="cpu", dtype=self.dtype))
                for sid, m in self.sources.items()})
            self.residual_heads = None
            if model.persistence_residual_sources:
                self.residual_heads = nn.ModuleDict()
                for sid in model.persistence_residual_sources:
                    head = nn.Linear(model.width, len(self.sources[sid].feature_names),
                                     device="cpu", dtype=self.dtype)
                    nn.init.zeros_(head.weight)
                    nn.init.zeros_(head.bias)
                    self.residual_heads[self.source_keys[sid]] = head
        self.eval()

    def group_modules(self) -> Mapping[str, tuple[nn.Module, ...]]:
        heads = (self.heads,) if self.residual_heads is None else (self.heads, self.residual_heads)
        return {"encoders": (self.encoders,), "source_embeddings": (self.source_embeddings,),
                "context": (self.context,), "fusion": (self.fusion,),
                "temporal": (self.history_time, self.temporal),
                "forecast_decoder": (self.forecast_decoder,), "heads": heads}

    def _normalizer(self, source_id: str) -> tuple[Tensor, Tensor]:
        require(source_id in self.normalizers, "No TRAIN-fitted normalizer for " + source_id)
        norm = self.normalizers[source_id]
        center = torch.tensor(norm.center, dtype=self.dtype, device="cpu")
        scale = torch.tensor(norm.scale, dtype=self.dtype, device="cpu")
        require(bool(torch.isfinite(center).all()) and bool(torch.isfinite(scale).all())
                and bool((scale > 0).all()), "Normalizer not representable in declared precision")
        return center, scale

    def _check_modality(self, kind: str, record: ModalityBatch, shape: tuple[int, int],
                        valid: Tensor, cutoff: Tensor | None,
                        identity: ObservationBatch) -> None:
        require(kind in self.modalities and record.source_id in self.sources, "Undeclared source")
        require(self.sources[record.source_id].modality == kind, "Wrong source observation set")
        require((record.sample_ids, record.raw_parent_ids, record.pairing_id)
                == (identity.sample_ids, identity.raw_parent_ids, identity.pairing_id),
                "Modality row/order/pairing identity mismatch")
        expected = (*shape, len(self.sources[record.source_id].feature_names))
        cpu_tensor(record.values, self.dtype, kind + " values")
        cpu_tensor(record.observed, torch.bool, kind + " observed")
        cpu_tensor(record.available_at_s, torch.float64, kind + " availability")
        require(record.values.shape == record.observed.shape == record.available_at_s.shape == expected,
                kind + " record shape mismatch")
        require(not bool((record.observed & ~valid[..., None]).any()), "Observed cell on padded step")
        require(bool(torch.isfinite(record.values[record.observed]).all()), "Nonfinite observed value")
        require(bool(torch.isfinite(record.available_at_s[record.observed]).all()),
                "Explicit finite availability required")
        if cutoff is not None:
            require(not bool((record.observed & (record.available_at_s > cutoff[:, None, None])).any()),
                    "An input becomes available after the context cutoff")

    def _check_observation(self, obs: ObservationBatch, direction: DirectionSpec) -> Tensor:
        direction.validate()
        shape = check_grid(obs.times_s, obs.valid_steps, self.task.max_context_steps, "history")
        b, _ = shape
        require(b <= self.task.max_batch, "Batch exceeds declared bound")
        require(len(obs.sample_ids) == len(obs.raw_parent_ids) == b
                and len(set(obs.sample_ids)) == b and all(obs.sample_ids) and all(obs.raw_parent_ids),
                "Sample/raw-parent identities required")
        require(obs.partition in ("TRAIN", "DEV", "CONFIRM"), "Unknown partition")
        require((obs.task_id, obs.clock_id, obs.alignment_id)
                == (self.task.task_id, self.task.clock_id, self.task.alignment_id),
                "Task/clock/alignment mismatch")
        require(set(obs.modalities).issubset(direction.inputs), "Undeclared or privileged input modality")
        require(bool(obs.modalities), "No observed source")
        if len(obs.modalities) > 1:
            require(type(obs.pairing_id) is str and bool(obs.pairing_id),
                    "Unpaired corpora must not be fused as a measured recording")
        last = obs.valid_steps.sum(dim=1) - 1
        cutoff = obs.times_s.gather(1, last[:, None]).squeeze(1)
        require(bool(((cutoff - obs.times_s[:, 0]) <= self.task.max_history_duration_s).all()),
                "History exceeds frozen context duration")
        k = len(self.task.context_feature_names)
        cpu_tensor(obs.context_values, self.dtype, "context")
        cpu_tensor(obs.context_available_at_s, torch.float64, "context availability")
        require(obs.context_values.shape == obs.context_available_at_s.shape == (b, k),
                "Context shape mismatch")
        require(bool(torch.isfinite(obs.context_values).all())
                and bool(torch.isfinite(obs.context_available_at_s).all()), "Nonfinite context")
        require(bool((obs.context_available_at_s <= cutoff[:, None]).all()),
                "Context feature not available at forecast cutoff")
        seen = torch.zeros(b, dtype=torch.bool, device="cpu")
        for kind, record in obs.modalities.items():
            self._check_modality(kind, record, shape, obs.valid_steps, cutoff, obs)
            seen |= record.observed.reshape(b, -1).any(dim=1)
            self._normalizer(record.source_id)
        require(bool(seen.all()), "Each sample needs an actual available input observation")
        return cutoff

    def _memory(self, obs: ObservationBatch, direction: DirectionSpec) -> tuple[Tensor, Tensor, Tensor]:
        cutoff = self._check_observation(obs, direction)
        b, t = obs.times_s.shape
        context = self.context(obs.context_values)
        tokens, absent = [], []
        for kind in MODALITIES:
            if kind not in obs.modalities:
                tokens.append(torch.zeros((b, t, self.spec.width), dtype=self.dtype, device="cpu"))
                absent.append(torch.ones((b, t), dtype=torch.bool, device="cpu"))
                continue
            record = obs.modalities[kind]
            center, scale = self._normalizer(record.source_id)
            safe = torch.where(record.observed, record.values, center)
            normalized = (safe - center) / scale
            token = self.encoders[self.source_keys[record.source_id]](
                torch.cat((normalized, record.observed.to(self.dtype)), dim=-1))
            index = torch.full((b, t), self.source_indices[record.source_id],
                               dtype=torch.long, device="cpu")
            tokens.append(token + self.source_embeddings(index))
            absent.append(~record.observed.any(dim=-1))
        # A valid task-context token prevents all-masked attention at missing data steps.
        tokens.append(context[:, None, :].expand(-1, t, -1))
        absent.append(torch.zeros((b, t), dtype=torch.bool, device="cpu"))
        keys = torch.stack(tokens, dim=2).reshape(b * t, 5, self.spec.width)
        padding = torch.stack(absent, dim=2).reshape(b * t, 5)
        query = context[:, None, :].expand(-1, t, -1).reshape(b * t, 1, self.spec.width)
        fused, _ = self.fusion(query, keys, keys, key_padding_mask=padding, need_weights=False)
        relative = torch.where(obs.valid_steps, obs.times_s - cutoff[:, None], 0).to(self.dtype)
        hidden = fused.reshape(b, t, self.spec.width) + self.history_time(relative)
        causal = torch.triu(torch.ones((t, t), dtype=torch.bool, device="cpu"), diagonal=1)
        memory = self.temporal(hidden, mask=causal, src_key_padding_mask=~obs.valid_steps)
        return memory, context, cutoff

    def _outputs(self, hidden: Tensor, direction: DirectionSpec) -> dict[str, Distribution]:
        outputs = {}
        for kind in direction.targets:
            source_id = direction.target_source_ids[kind]
            require(source_id in self.sources and self.sources[source_id].modality == kind,
                    "Output source/head does not match target family")
            self._normalizer(source_id)
            mean, log_variance = self.heads[self.source_keys[source_id]](hidden).chunk(2, dim=-1)
            outputs[kind] = Distribution(mean, log_variance.clamp(
                self.spec.log_variance_min, self.spec.log_variance_max), source_id)
        return outputs

    def reconstruct(self, corrupted: ObservationBatch, direction: DirectionSpec) -> dict[str, Distribution]:
        memory, _, _ = self._memory(corrupted, direction)
        return self._outputs(memory, direction)

    def _apply_persistence_residual(self, observation: ObservationBatch, direction: DirectionSpec,
                                    hidden: Tensor, outputs: dict[str, Distribution]) -> None:
        # _memory has validated row identities, padding, increasing history times
        # and availability of every observed input at this row's forecast cutoff.
        if (self.residual_heads is None or len(direction.inputs) != 1
                or direction.inputs != direction.targets):
            return
        kind = direction.inputs[0]
        record = observation.modalities[kind]
        prediction = outputs[kind]
        key = self.source_keys[prediction.source_id]
        if record.source_id != prediction.source_id or key not in self.residual_heads:
            return

        steps = torch.arange(record.values.shape[1], device=record.values.device)[None, :, None]
        last = torch.where(record.observed, steps, -1).amax(dim=1)
        supported = last >= 0
        last_value = record.values.gather(1, last.clamp_min(0)[:, None, :]).squeeze(1)
        center, scale = self._normalizer(prediction.source_id)
        # Gather needs an index even when no observation exists. Discard that
        # placeholder before arithmetic and use the ordinary mean on that feature.
        last_stored = torch.where(supported, last_value, center)[:, None, :]
        anchor = (last_stored - center) / scale
        require(bool(torch.isfinite(anchor).all()), "Persistence not representable in declared precision")
        change = self.residual_heads[key](hidden)
        supported = supported[:, None, :]
        mean = torch.where(supported, anchor + change, prediction.mean)
        outputs[kind] = PersistenceDistribution(mean, prediction.log_variance, prediction.source_id,
                                                last_stored, supported, change)

    def forecast(self, observation: ObservationBatch, query: QueryBatch,
                 direction: DirectionSpec) -> dict[str, Distribution]:
        # There is deliberately no target-value argument on this method.
        memory, context, cutoff = self._memory(observation, direction)
        b, _ = check_grid(query.times_s, query.valid_steps, self.task.max_query_steps, "query")
        require(b == len(observation.sample_ids), "Query batch mismatch")
        horizon = query.times_s - cutoff[:, None]
        require(bool((horizon[query.valid_steps] >= self.task.minimum_horizon_s).all())
                and bool((horizon[query.valid_steps] <= self.task.maximum_horizon_s).all()),
                "Query horizon outside frozen available-time domain")
        relative = torch.where(query.valid_steps, horizon, 0).to(self.dtype)
        hidden = self.forecast_decoder(relative, context, memory, observation.valid_steps)
        outputs = self._outputs(hidden, direction)
        self._apply_persistence_residual(observation, direction, hidden, outputs)
        return outputs

    def forward(self, observation: ObservationBatch, query: QueryBatch,
                direction: DirectionSpec) -> dict[str, Distribution]:
        return self.forecast(observation, query, direction)

    def to_stored_units(self, kind: str, prediction: Distribution) -> StoredUnitDistribution:
        require(prediction.source_id in self.sources
                and self.sources[prediction.source_id].modality == kind, "Output source mismatch")
        center, scale = self._normalizer(prediction.source_id)
        spec = self.sources[prediction.source_id]
        cpu_tensor(prediction.mean, self.dtype, "predicted mean")
        cpu_tensor(prediction.log_variance, self.dtype, "predicted log variance")
        require(prediction.mean.shape == prediction.log_variance.shape
                and prediction.mean.shape[-1] == len(spec.feature_names), "Prediction shape mismatch")
        mean = prediction.mean * scale + center
        if isinstance(prediction, PersistenceDistribution):
            mean = torch.where(prediction.supported,
                               torch.addcmul(prediction.last_stored, prediction.normalized_change, scale),
                               mean)
        # Combine in log space in the declared dtype: exp(logvar)*scale**2
        # can lose a representable result through an intermediate zero/infinity.
        stored_log_variance = prediction.log_variance + 2 * scale.log()
        limits = torch.finfo(self.dtype)
        minimum_log = math.log(limits.tiny) + math.log(limits.eps)
        maximum_log = math.log(limits.max)
        require(bool(torch.isfinite(stored_log_variance).all())
                and bool((stored_log_variance >= minimum_log).all())
                and bool((stored_log_variance <= maximum_log).all()),
                "Stored variance is outside the declared dtype's positive range")
        variance = stored_log_variance.exp()
        require(bool(torch.isfinite(mean).all()) and bool(torch.isfinite(variance).all())
                and bool((variance > 0).all()),
                "Stored-unit output is nonfinite or variance is unrepresentable")
        return StoredUnitDistribution(mean, variance,
                                      spec.units, spec.unit_status, spec.calibration_ids)

    def to_physical(self, kind: str, prediction: Distribution) -> StoredUnitDistribution:
        require(prediction.source_id in self.sources
                and self.sources[prediction.source_id].modality == kind, "Output source mismatch")
        require(all(s == "calibrated_physical" for s in self.sources[prediction.source_id].unit_status),
                "Stored/processed unit labels do not establish physical calibration")
        return self.to_stored_units(kind, prediction)

    def predict(self, observation: ObservationBatch, query: QueryBatch,
                direction: DirectionSpec) -> dict[str, Distribution]:
        """Frozen-mode prediction; caller supplies the separately admitted model."""
        with self._phase_lock:
            owner = self._phase_owner
            require(owner is None or owner.state not in ("INITIALIZING", "ATTEMPTED", "HOLD_UNKNOWN"),
                    "An active or unknown training mutation holds frozen prediction")
            require(all(not module.training for module in self.modules()),
                    "Call model.eval() after ending adaptation; no training/inference mode mixture")
            with torch.no_grad():
                outputs = self.forecast(observation, query, direction)
                for prediction in outputs.values():
                    require(bool(torch.isfinite(prediction.mean[query.valid_steps]).all())
                            and bool(torch.isfinite(prediction.log_variance[query.valid_steps]).all()),
                            "Nonfinite prediction")
                require(all(not module.training for module in self.modules()),
                        "Model mode changed during frozen prediction")
                return outputs


@dataclass(frozen=True)
class NormalizerFit:
    normalizer: Normalizer
    observed_scalars_per_feature: tuple[int, ...]
    floored_scale_per_feature: tuple[bool, ...]
    minimum_scale: float


def fit_train_normalizer(observations: Sequence[ObservationBatch], source: SourceSpec, task: TaskSpec,
                         freeze: ScientificFreeze, normalization_id: str,
                         minimum_scale: float, precision: str) -> NormalizerFit:
    """Offline TRAIN population moments, with stable batch-combined computation.

    The explicit scale floor is a frozen preprocessing choice, not a performance
    threshold. No absent feature receives an invented fitted statistic. This
    includes only the separately allowed TRAIN fit scope; target processing may
    have latency. It does not qualify any value for online input. _check_observation
    independently enforces input availability at the forecast cutoff. Counts are
    scalar occurrences; the caller freezes duplicate/overlap weighting policy.
    """
    source.validate()
    task.validate()
    freeze.validate()
    finite_number(minimum_scale, "minimum_scale")
    require(minimum_scale > 0 and bool(observations), "Finite TRAIN observations and scale floor required")
    c = len(source.feature_names)
    count = torch.zeros(c, dtype=torch.int64, device="cpu")
    mean = torch.zeros(c, dtype=torch.float64, device="cpu")
    m2 = torch.zeros_like(mean)
    parents: set[str] = set()
    for obs in observations:
        require(obs.partition == "TRAIN" and obs.task_id == task.task_id
                and obs.clock_id == task.clock_id and obs.alignment_id == task.alignment_id,
                "Normalizer task/partition/alignment mismatch")
        observed_parents = frozenset(obs.raw_parent_ids)
        require(observed_parents and observed_parents.issubset(freeze.train_parent_ids)
                and not observed_parents.intersection(freeze.excluded_parent_ids),
                "Normalizer cannot fit evaluation or excluded parents")
        shape = check_grid(obs.times_s, obs.valid_steps, task.max_context_steps, "normalizer history")
        require(shape[0] <= task.max_batch, "Normalizer batch exceeds declared bound")
        require(len(obs.sample_ids) == len(obs.raw_parent_ids) == shape[0]
                and len(set(obs.sample_ids)) == shape[0], "Normalizer row identity/count mismatch")
        if source.modality not in obs.modalities:
            continue
        record = obs.modalities[source.modality]
        if record.source_id != source.source_id:
            continue
        require(source.clock_id == task.clock_id and source.alignment_id == task.alignment_id,
                "Normalizer source alignment mismatch")
        require((record.sample_ids, record.raw_parent_ids, record.pairing_id)
                == (obs.sample_ids, obs.raw_parent_ids, obs.pairing_id), "Normalizer row identity mismatch")
        cpu_tensor(record.values, dtype_for(precision), "normalizer values")
        cpu_tensor(record.observed, torch.bool, "normalizer observed")
        cpu_tensor(record.available_at_s, torch.float64, "normalizer availability")
        require(record.values.shape == record.observed.shape == record.available_at_s.shape == (*shape, c),
                "Normalizer record shape mismatch")
        require(not bool((record.observed & ~obs.valid_steps[..., None]).any()),
                "Normalizer observation on padding")
        require(bool(torch.isfinite(record.values[record.observed]).all())
                and bool(torch.isfinite(record.available_at_s[record.observed]).all()),
                "Nonfinite normalizer observation")
        mask = record.observed
        values = record.values.to(torch.float64)
        batch_count = mask.sum(dim=(0, 1))
        batch_mean = torch.where(mask, values, 0).sum(dim=(0, 1)) / batch_count.clamp_min(1)
        residual = torch.where(mask, values - batch_mean, 0)
        batch_m2 = residual.square().sum(dim=(0, 1))
        total = count + batch_count
        delta = batch_mean - mean
        mean = mean + delta * batch_count / total.clamp_min(1)
        m2 = m2 + batch_m2 + delta.square() * count * batch_count / total.clamp_min(1)
        count = total
        parents.update(observed_parents)
    require(bool((count > 0).all()), "No fitted statistic for one or more features")
    scale = (m2 / count).clamp_min(0).sqrt()
    floored = scale < minimum_scale
    scale = scale.clamp_min(minimum_scale)
    require(bool(torch.isfinite(mean).all()) and bool(torch.isfinite(scale).all()), "Nonfinite moments")
    normalizer = Normalizer(tuple(mean.tolist()), tuple(scale.tolist()), frozenset(parents),
                            "TRAIN", normalization_id)
    normalizer.validate(c)
    return NormalizerFit(normalizer, tuple(count.tolist()), tuple(floored.tolist()), minimum_scale)


def masked_nll(model: HandArmLearner, predictions: Mapping[str, Distribution],
               targets: Mapping[str, ModalityBatch], valid_steps: Tensor,
               weights: Mapping[str, float], identity: ObservationBatch
               ) -> tuple[Tensor, dict, float]:
    require(set(targets).issubset(predictions), "Unexpected target modality")
    require(set(predictions).issubset(weights), "Undeclared output weight")
    total, active_weight, report = None, 0.0, {}
    for kind in weights:
        if kind not in targets or kind not in predictions:
            report[kind] = {"observed_scalars": 0, "absent_target": 1}
            continue
        prediction = predictions[kind]
        record = targets[kind]
        model._check_modality(kind, record, tuple(valid_steps.shape), valid_steps, None, identity)
        mask = record.observed & valid_steps[..., None]
        count = int(mask.sum().item())
        if count == 0:
            report[kind] = {"observed_scalars": 0, "absent_target": 1}
            continue
        require(record.source_id == prediction.source_id, "Target is from a different source/head")
        center, scale = model._normalizer(record.source_id)
        safe = torch.where(mask, record.values, center)
        residual = torch.where(mask, prediction.mean - ((safe - center) / scale), 0)
        if isinstance(prediction, PersistenceDistribution):
            # Comparing two rounded normalized levels can erase the entire
            # learning signal. Compare changes before adding back either level.
            supported = mask & prediction.supported
            target_stored = torch.where(supported, record.values, prediction.last_stored)
            stored_difference = target_stored - prediction.last_stored
            # Opposite large finite levels may overflow on subtraction even
            # when their difference in normalized units is representable.
            target_change = torch.where(torch.isfinite(stored_difference), stored_difference / scale,
                                        target_stored / scale - prediction.last_stored / scale)
            residual = torch.where(supported, prediction.normalized_change - target_change, residual)
        mean, logvar = prediction.mean[mask], prediction.log_variance[mask]
        require(bool(torch.isfinite(mean).all()) and bool(torch.isfinite(logvar).all()),
                "Nonfinite model output")
        # Full Gaussian NLL in TRAIN-normalized coordinates; no physical calibration claim.
        loss = (0.5 * (residual[mask].square() * (-logvar).exp()
                      + logvar + math.log(2 * math.pi))).mean()
        require(bool(torch.isfinite(loss)), "Nonfinite objective")
        weighted = loss * weights[kind]
        total = weighted if total is None else total + weighted
        active_weight += weights[kind]
        report[kind] = {"observed_scalars": count, "nll_mean": float(loss.detach().item()),
                        "weight": weights[kind], "absent_target": 0,
                        "source_id": prediction.source_id}
        # Descriptive counts/errors are not an uncertainty estimate or acceptance test.
        feature_count = mask.sum(dim=(0, 1))
        feature_mse = residual.square().sum(dim=(0, 1)) / feature_count.clamp_min(1)
        require(bool(torch.isfinite(feature_mse).all()), "Nonfinite per-feature error")
        spec = model.sources[prediction.source_id]
        report[kind]["per_feature"] = [
            {"feature": name, "observed_scalars": int(n), "units": units, "unit_status": status,
             "normalized_rmse": math.sqrt(float(mse)) if n else None,
             "stored_unit_rmse": math.sqrt(float(mse)) * float(s) if n else None}
            for name, n, mse, s, units, status in zip(
                spec.feature_names, feature_count.tolist(), feature_mse.detach().tolist(),
                scale.tolist(), spec.units, spec.unit_status)]
        require(all(item["stored_unit_rmse"] is None or math.isfinite(item["stored_unit_rmse"])
                    for item in report[kind]["per_feature"]), "Stored-unit error overflow")
    require(total is not None and active_weight > 0, "No supervised target cells")
    return total / active_weight, report, active_weight


def mask_pretraining(observation: ObservationBatch, phase: PhaseSpec, seed: int
                     ) -> tuple[ObservationBatch, dict[str, ModalityBatch], dict[str, Tensor]]:
    generator = torch.Generator(device="cpu").manual_seed(seed)
    inputs, targets, masks = dict(observation.modalities), {}, {}
    for kind in phase.direction.targets:
        if kind not in observation.modalities:
            continue
        record = observation.modalities[kind]
        draw = torch.rand(record.observed.shape, generator=generator, device="cpu",
                          dtype=torch.float64) < phase.masking_probability
        withheld = record.observed & observation.valid_steps[..., None] & draw
        # The same original target tensor is never supplied to the encoder as observed.
        inputs[kind] = replace(record, observed=record.observed & ~withheld)
        targets[kind] = replace(record, observed=withheld)
        masks[kind] = withheld
    require(any(bool(m.any()) for m in masks.values()), "No cells sampled; no automatic redraw")
    return replace(observation, modalities=inputs), targets, masks


class TrainingSession:
    """One exclusively owned phase; a newer phase invalidates the old handle.

    The caller must persist intent before use and retain raw failures/checkpoints.
    In-memory ownership is not a durable once ledger or native execution receipt.
    """

    def __init__(self, model: HandArmLearner, phase: PhaseSpec, freeze: ScientificFreeze):
        phase.validate()
        freeze.validate()
        for norm in model.normalizers.values():
            require(norm.fit_parent_ids.issubset(freeze.train_parent_ids)
                    and not (norm.fit_parent_ids & freeze.excluded_parent_ids),
                    "Normalizer exposure outside frozen TRAIN")
        self.model, self.phase, self.freeze = model, phase, freeze
        self._phase_identity, self._freeze_identity = phase, freeze
        self.completed_steps = 0
        self.state = "INITIALIZING"
        self.failure: BaseException | None = None
        self.invalidated_by = None
        with model._phase_lock:
            previous = model._phase_owner
            require(previous is None or previous.state in ("READY", "EXHAUSTED", "HOLD_INTEGRITY"),
                    "An attempted/unknown phase cannot be silently replaced")
            # Preflight the complete layout before changing flags, modes or gradients.
            groups = model.group_modules()
            require(set(groups) == set(GROUPS), "Parameter group registry changed")
            self._group_signature = self._layout_signature(groups)
            self._model_parameters = tuple(model.parameters())
            self._model_modules = tuple(model.modules())
            expected_modes = {id(module): (module, False) for module in self._model_modules}
            expected_flags, parameters, seen_modules, assigned = [], [], set(), set()
            for group, roots in groups.items():
                trainable = group in phase.trainable_groups
                for root in roots:
                    for module in root.modules():
                        require(id(module) not in seen_modules, "Overlapping module groups")
                        seen_modules.add(id(module))
                        expected_modes[id(module)] = (module, trainable)
                    for parameter in root.parameters():
                        require(id(parameter) not in assigned, "Overlapping parameter groups")
                        assigned.add(id(parameter))
                        expected_flags.append((parameter, trainable))
                        if trainable:
                            parameters.append(parameter)
            require(assigned == {id(v) for v in self._model_parameters}, "Unassigned model parameter")
            require(seen_modules == {id(v) for v in self._model_modules if v is not model},
                    "Unassigned or replaced model module")
            require(bool(parameters), "No trainable parameters")
            self.parameters = tuple(parameters)
            self._expected_parameter_ids = tuple(id(v) for v in parameters)
            self._expected_modes = tuple(expected_modes.values())
            self._expected_flags = tuple(expected_flags)
            if previous is not None:
                previous.state = "INVALIDATED"
                previous.invalidated_by = self
            model._phase_owner = self
            try:
                model.eval()
                for group, roots in groups.items():
                    for root in roots:
                        root.train(group in phase.trainable_groups)
                for parameter, trainable in self._expected_flags:
                    parameter.requires_grad_(trainable)
                self._assert_model_integrity()
                for parameter in self._model_parameters:
                    parameter.grad = None
                self.optimizer = torch.optim.AdamW(
                    self.parameters, lr=phase.learning_rate, betas=phase.adam_betas,
                    eps=phase.adam_epsilon, weight_decay=phase.weight_decay)
                self._optimizer_identity = self.optimizer
                self._assert_integrity()
                self.state = "READY"
            except BaseException as error:
                self.failure = error
                self.state = "HOLD_UNKNOWN"
                raise

    @staticmethod
    def _layout_signature(groups) -> tuple:
        return tuple((group, tuple(id(root) for root in roots),
                      tuple(id(parameter) for root in roots for parameter in root.parameters()))
                     for group, roots in groups.items())

    def _assert_model_integrity(self) -> None:
        require(self.model._phase_owner is self, "Stale training phase no longer owns the model")
        require(self.phase is self._phase_identity and self.freeze is self._freeze_identity,
                "Phase/freeze identity changed")
        require(tuple(id(v) for v in self.model.parameters())
                == tuple(id(v) for v in self._model_parameters), "Model parameters replaced")
        require(tuple(id(v) for v in self.model.modules())
                == tuple(id(v) for v in self._model_modules), "Model modules replaced")
        require(self._layout_signature(self.model.group_modules()) == self._group_signature,
                "Actual parameter group layout changed")
        require(tuple(id(v) for v in self.parameters) == self._expected_parameter_ids,
                "Session parameter membership changed")
        require(all(module.training is expected for module, expected in self._expected_modes),
                "Actual train/eval modes differ from the owned phase")
        require(all(parameter.requires_grad is expected for parameter, expected in self._expected_flags),
                "Actual requires_grad flags differ from the owned phase")

    def _assert_integrity(self) -> None:
        self._assert_model_integrity()
        require(self.optimizer is self._optimizer_identity, "Optimizer identity changed")
        groups = self.optimizer.param_groups
        require(len(groups) == 1, "Optimizer groups changed")
        actual = groups[0]
        require(tuple(id(v) for v in actual["params"]) == self._expected_parameter_ids,
                "Optimizer parameters differ from the owned phase")
        require(actual["lr"] == self.phase.learning_rate
                and tuple(actual["betas"]) == self.phase.adam_betas
                and actual["eps"] == self.phase.adam_epsilon
                and actual["weight_decay"] == self.phase.weight_decay,
                "Optimizer hyperparameters differ from the frozen phase")

    def step(self, observation: ObservationBatch, targets: Mapping[str, ModalityBatch] | None = None,
             query: QueryBatch | None = None) -> dict:
        with self.model._phase_lock:
            require(self.state == "READY", "Session held, stale or exhausted; no replay")
            try:
                self._assert_integrity()
            except BaseException as error:
                # No learning mutation has begun; preserve this actual preflight failure.
                self.failure = error
                self.state = "HOLD_INTEGRITY"
                raise
            require(self.completed_steps < self.phase.max_updates, "Finite update allowance exhausted")
            require(observation.partition == "TRAIN", "Fitting is TRAIN-only")
            parents = frozenset(observation.raw_parent_ids)
            require(bool(parents) and parents.issubset(self.freeze.train_parent_ids)
                    and not (parents & self.freeze.excluded_parent_ids), "Training partition/exposure mismatch")
            if observation.pairing_id is not None:
                require(observation.pairing_id in self.freeze.allowed_pairing_ids, "Unqualified pairing ID")
            if self.phase.kind != "pretrain":
                require(type(observation.pairing_id) is str
                        and observation.pairing_id in self.freeze.allowed_pairing_ids,
                        "Supervised source/target pairing must be explicitly frozen")
                require(targets is not None and query is not None, "Supervised targets/query missing")
            else:
                require(targets is None and query is None, "Pretraining does not accept external paired labels")
            step_index = self.completed_steps
            self.state = "ATTEMPTED"
            # After this point any exception is retained, ambiguous updates are never retried.
            try:
                self.model._check_observation(observation, self.phase.direction)
                self.optimizer.zero_grad(set_to_none=True)
                with _seeded_cpu_rng(self.phase.step_seed + step_index):
                    if self.phase.kind == "pretrain":
                        corrupted, truth, masks = mask_pretraining(
                            observation, self.phase, self.phase.mask_seed + step_index)
                        # Unpaired pretraining does not require fictitious normalizers/labels
                        # for the other three absent interfaces.
                        require(all(self.phase.direction.target_source_ids[k] == v.source_id
                                    for k, v in truth.items()), "Pretraining source/head mismatch")
                        reconstruction_direction = replace(
                            self.phase.direction, targets=tuple(truth),
                            target_source_ids={k: v.source_id for k, v in truth.items()},
                            inverse_interpretation=("conditional_nonunique_recorded_features"
                                                    if "neural" in truth else "not_a_neural_inverse"))
                        predictions = self.model.reconstruct(corrupted, reconstruction_direction)
                        valid = observation.valid_steps
                    else:
                        truth, masks = targets, {}
                        predictions = self.model.forecast(observation, query, self.phase.direction)
                        valid = query.valid_steps
                    loss, by_modality, denominator = masked_nll(
                        self.model, predictions, truth, valid, self.phase.loss_weights, observation)
                    loss.backward()
                    self._assert_integrity()
                    norm = torch.nn.utils.clip_grad_norm_(self.parameters, self.phase.max_gradient_norm,
                                                         error_if_nonfinite=True)
                    require(any(p.grad is not None for p in self.parameters), "No gradient path")
                    self._assert_integrity()
                    self.optimizer.step()
                    self._assert_integrity()
                    require(all(bool(torch.isfinite(p).all()) for p in self.model.parameters()),
                            "Nonfinite parameter after update")
                self.completed_steps += 1
                self.state = "EXHAUSTED" if self.completed_steps == self.phase.max_updates else "READY"
                return {"phase": self.phase.kind, "freeze_id": self.freeze.freeze_id,
                        "direction_id": self.phase.direction.direction_id,
                        "information_set_id": self.phase.direction.information_set_id,
                        "completed_step_index": step_index, "completed_steps": self.completed_steps,
                        "local_state": self.state, "trainable_groups": self.phase.trainable_groups,
                        "loss": float(loss.detach().item()), "per_modality": by_modality,
                        "active_weight_denominator": denominator,
                        "gradient_norm_before_clip": float(norm.detach().item()),
                        "mask_seed": self.phase.mask_seed + step_index if masks else None,
                        "withheld_masks": masks,
                        "qualification": "local_update_only_no_scientific_or_native_acceptance"}
            except BaseException as error:
                self.failure = error
                self.state = "HOLD_UNKNOWN"
                raise


def _array(value, depth: int, boolean: bool = False) -> None:
    """Validate ordinary array leaf types before torch can coerce them."""
    if depth:
        require(type(value) in (list, tuple) and len(value) > 0, "Nonempty ordinary array required")
        for part in value:
            _array(part, depth - 1, boolean)
    elif boolean:
        require(type(value) is bool, "Masks must contain actual booleans")
    else:
        require(type(value) in (int, float), "Numeric array requires actual numbers, not booleans/strings")


def tensorize_modality(record: Mapping, precision: str) -> ModalityBatch:
    """Consume caller-owned ordinary records; never read a file or infer alignment."""
    _array(record["values"], 3)
    _array(record["observed"], 3, boolean=True)
    _array(record["available_at_s"], 3)
    return ModalityBatch(
        source_id=record["source_id"],
        sample_ids=identity_tuple(record["sample_ids"], "sample_ids"),
        raw_parent_ids=identity_tuple(record["raw_parent_ids"], "raw_parent_ids"),
        pairing_id=record["pairing_id"],
        values=torch.tensor(record["values"], dtype=dtype_for(precision), device="cpu"),
        observed=torch.tensor(record["observed"], dtype=torch.bool, device="cpu"),
        available_at_s=torch.tensor(record["available_at_s"], dtype=torch.float64, device="cpu"))


def tensorize_observation(record: Mapping, precision: str) -> ObservationBatch:
    _array(record["times_s"], 2)
    _array(record["valid_steps"], 2, boolean=True)
    _array(record["context_values"], 2)
    _array(record["context_available_at_s"], 2)
    return ObservationBatch(
        sample_ids=identity_tuple(record["sample_ids"], "sample_ids"),
        raw_parent_ids=identity_tuple(record["raw_parent_ids"], "raw_parent_ids"),
        partition=record["partition"], task_id=record["task_id"], clock_id=record["clock_id"],
        alignment_id=record["alignment_id"], pairing_id=record["pairing_id"],
        times_s=torch.tensor(record["times_s"], dtype=torch.float64, device="cpu"),
        valid_steps=torch.tensor(record["valid_steps"], dtype=torch.bool, device="cpu"),
        context_values=torch.tensor(record["context_values"], dtype=dtype_for(precision), device="cpu"),
        context_available_at_s=torch.tensor(record["context_available_at_s"], dtype=torch.float64, device="cpu"),
        modalities={kind: tensorize_modality(value, precision)
                    for kind, value in record["modalities"].items()})


def tensorize_query(record: Mapping) -> QueryBatch:
    _array(record["times_s"], 2)
    _array(record["valid_steps"], 2, boolean=True)
    return QueryBatch(torch.tensor(record["times_s"], dtype=torch.float64, device="cpu"),
                      torch.tensor(record["valid_steps"], dtype=torch.bool, device="cpu"))


def tensorize_targets(record: Mapping, precision: str) -> dict[str, ModalityBatch]:
    return {kind: tensorize_modality(value, precision) for kind, value in record.items()}
