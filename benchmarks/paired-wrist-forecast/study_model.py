"""Place each available source on the same pointing-trial clock for the shared forecaster."""
import numpy as np
import torch

LEAD = 128
OFFSETS = np.array([384,512,640,768,896,1024])
from aligned_forecast import AlignedQuery, AlignedTarget, ForecastRows, validate_aligned_forecast
from broader_learner import (MODALITIES, GROUPS, DirectionSpec, HandArmLearner, ModalityBatch,
    ModalitySpec, ModelSpec, Normalizer, ObservationBatch, PhaseSpec, QueryBatch, ScientificFreeze,
    SourceSpec, TaskSpec, TrainingSession)

MOTION, EMG, EEG = "measured_motion", "myographic", "neural"
MODES = {"motion": (MOTION,), "emg": (MOTION, EMG), "full": (MOTION, EMG, EEG)}
SLICES = {MOTION: slice(0,2), EMG: slice(2,6), EEG: slice(6,14)}
IDS = {MOTION: "earlier-angle-change", EMG: "derived-bipolar-rms", EEG: "mean-scalp-voltage"}
TARGET = "future-two-axis-change"
PAIR = "wristmotion-v3-same-source-run-and-trial"
TASK = "wrist-pointing-250ms"
CLOCK = "cue-relative-512Hz"
ALIGN = "same-row-verified-encoder-and-edf"
CONTEXT = ("extension_anchor_z", "radial_anchor_z", *(f"cue_position_{offset}" for offset in OFFSETS))
SEED = 20261120
BATCH = 96
EPOCHS = 4
SPEC = TaskSpec(TASK, CLOCK, ALIGN, "right wrist two encoder axes", "available by offline cutoff",
                CONTEXT, ("TRAIN SD",)*2 + ("indicator",)*6, ("derived",)*8,
                ("10.6084/m9.figshare.29666735.v3",)*8, BATCH, 16, 1, .5, .25, .25)
NAMES = {MOTION: ("extension","radial"), EMG: tuple(f"M{i}L-minus-R_rms" for i in range(1,5)),
         EEG: ("C3","C1","Cz","C2","C4","CP3","CPz","CP4")}
UNITS = {MOTION:"deg", EMG:"uV", EEG:"uV"}
FRAMES = {MOTION:"right wrist extension and radial deviation positive",
          EMG:"right forearm electrode pairs", EEG:"scalp sites referenced to right ear"}


def make_model(norm, parents):
    interfaces, sources, norms = [], [], {}
    for kind, names in NAMES.items():
        n = len(names)
        interface = ModalitySpec(kind, names, (UNITS[kind],)*n, ("processed",)*n, (None,)*n, FRAMES[kind])
        interfaces.append(interface)
        source = SourceSpec(IDS[kind], kind, "human", FRAMES[kind], FRAMES[kind], names,
                            interface.units, interface.unit_status, interface.calibration_ids, ("derived",)*n,
                            "10.6084/m9.figshare.29666735.v3", PAIR, CLOCK, ALIGN)
        sources.append(source)
        cols = SLICES[kind]
        norms[IDS[kind]] = Normalizer(tuple(norm["bins_center"][cols].tolist()), tuple(norm["bins_scale"][cols].tolist()),
                                      frozenset(map(str,parents)), "TRAIN", "prior-ridge-bin-moments")
    interfaces.append(ModalitySpec("physics_generated", ("unobserved",), ("none",),
                                   ("simulated_units",), (None,), "absent"))
    angle = interfaces[0]
    sources.append(SourceSpec(TARGET, MOTION, "human", FRAMES[MOTION], angle.frame,
                              ("future_extension_change","future_radial_change"), angle.units,
                              angle.unit_status, angle.calibration_ids, ("derived",)*2,
                              "10.6084/m9.figshare.29666735.v3", PAIR, CLOCK, ALIGN))
    norms[TARGET] = Normalizer(tuple(norm["residual_center"].tolist()), tuple(norm["residual_scale"].tolist()),
                               frozenset(map(str,parents)), "TRAIN", "prior-ridge-target-change-moments")
    architecture = ModelSpec(24, 4, 1, 48, 0.0, "float32", SEED, -6, 6)
    return HandArmLearner(SPEC, architecture, interfaces, sources, norms)


def direction(mode):
    return DirectionSpec("forward-" + mode, mode, MODES[mode], (MOTION,), {MOTION:TARGET}, "not_a_neural_inverse")


def session(model, mode, parents, excluded, steps, seal):
    freeze = ScientificFreeze(seal, seal, "wristmotion-whole-subject", "fixed-four-epochs",
                              "persistence-matched-ridge-and-controls", "three-person-exploratory",
                              "participant-and-gaussian-descriptive", "matched-cpu-trial",
                              frozenset(map(str,parents)), frozenset(excluded), frozenset({PAIR}))
    phase = PhaseSpec("train", direction(mode), GROUPS, {MOTION:1.0}, .001, (.9,.999), 1e-8, .01,
                      1., steps, SEED, 0, 0.)
    return TrainingSession(model, phase, freeze)


def row_names(parents, ticks):
    return tuple(f"{p}/cutoff-{t}" for p,t in zip(parents,ticks,strict=True))


def pack(data, idx, mode, norm, switched=None, donor=None):
    rows = data.rows
    parents = tuple(data.parent[idx].tolist())
    cut = OFFSETS[rows.slot[idx]] - LEAD
    absolute = data.cue[idx] + cut
    samples = row_names(parents, absolute)
    # Time stamps describe bin acquisition. The absolute anchor is available only at the cutoff.
    ends = torch.from_numpy((cut[:,None] + np.arange(-240, 1, 16)[None,:]) / 512)
    history_end = ends[:,-1]
    part = "TRAIN" if data.role == "train" else "DEV"
    identity = ForecastRows(samples, parents, TASK, CLOCK, ALIGN, part, PAIR, history_end)
    records = {}
    for kind in MODES[mode]:
        objects = donor[idx] if kind == switched else idx
        values = torch.tensor(rows.bins[objects, :, SLICES[kind]], dtype=torch.float32)
        available = history_end[:,None].expand_as(ends) if kind == MOTION else ends
        records[kind] = ModalityBatch(IDS[kind], samples, parents, PAIR, values, torch.ones_like(values,dtype=torch.bool),
                                      available[:,:,None].expand_as(values))
    anchor_z = (rows.anchor[idx] - norm["anchor_center"]) / norm["anchor_scale"]
    context = torch.tensor(np.column_stack((anchor_z, np.eye(6)[rows.slot[idx]])), dtype=torch.float32)
    obs = ObservationBatch(samples, parents, part, TASK, CLOCK, ALIGN, PAIR, ends,
                           torch.ones_like(ends,dtype=torch.bool), context, history_end[:,None].expand_as(context), records)
    requests = torch.from_numpy((cut[:,None] + LEAD)/512)
    query = AlignedQuery(identity, QueryBatch(requests, torch.ones_like(requests,dtype=torch.bool)))
    labels = data.events
    label_parents = tuple(labels.parent[idx].tolist())
    label_ids = row_names(label_parents, labels.tick[idx] - LEAD)
    relative = labels.tick[idx] - labels.cue[idx]
    label_cut = torch.from_numpy((relative - LEAD)/512)
    event_times = torch.from_numpy(relative[:,None]/512)
    info = ForecastRows(label_ids,label_parents,TASK,CLOCK,ALIGN,part,PAIR,label_cut)
    residual = torch.tensor((labels.value[idx] - rows.anchor[idx])[:,None,:], dtype=torch.float32)
    measure = ModalityBatch(TARGET, label_ids, label_parents, PAIR, residual, torch.ones_like(residual,dtype=torch.bool),
                            event_times[:,:,None].expand_as(residual))
    return obs, query, {MOTION:AlignedTarget(info,measure,event_times)}


@torch.inference_mode()
def predict(model, data, mode, norm, switched=None, donor=None):
    model.eval()
    estimates, variances = [], []
    for start in range(0, len(data.parent), BATCH):
        idx = np.arange(start,min(start+BATCH,len(data.parent)))
        obs, query, targets = pack(data,idx,mode,norm,switched,donor)
        validate_aligned_forecast(SPEC,obs,query,targets,{MOTION:TARGET})
        distribution = model.predict(obs,query.grid,direction(mode))[MOTION]
        result = model.to_stored_units(MOTION,distribution)
        estimates.extend(result.mean[:,0,:].numpy().astype(np.float64) + data.rows.anchor[idx])
        variances.extend(result.variance[:,0,:].numpy().astype(np.float64))
    estimates, variances = np.array(estimates), np.array(variances)
    if not np.isfinite(estimates).all() or not np.isfinite(variances).all() or np.any(variances <= 0):
        raise ValueError("Forecast or variance outside the valid domain")
    return estimates, variances
