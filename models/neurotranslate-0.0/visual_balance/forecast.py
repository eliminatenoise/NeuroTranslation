"""Retrospective 125 ms sacrum and head forecast on the stored rotatewalk clock."""
from pathlib import Path
import json
import numpy as np

BASELINES = ("hold", "recent", "velocity", "cue_mean")
LEARNED = ("linear_motion", "motion_eyes", "motion_neck", "motion_legs", "linear_nuisance",
           "linear_full", "shared_nuisance", "shared_full", "shared_residual", "scalp_only", "masks_only")
USES_NUISANCE = ("motion_eyes", "motion_neck", "motion_legs", "linear_nuisance", "linear_full",
                 "shared_nuisance", "shared_full", "shared_residual")
USES_SCALP = ("linear_full", "shared_full", "shared_residual", "scalp_only")
USES_ENCODER = ("shared_nuisance", "shared_full", "shared_residual")


def movement(history):
    n = len(history)
    h = history.reshape(n, 8, 20, 6)
    z = history.reshape(n, 4, 40, 6)
    recent = (history[:, -1] - history[:, -33]).reshape(n, 6)
    features = [h[:, :, -1].reshape(n, -1), (h[:, :, -1] - h[:, :, 0]).reshape(n, -1)]
    features.extend((history[:, -1] - history[:, -1-k]).reshape(n, 6) for k in (16, 32, 64))
    return recent, np.column_stack(features), z[:, :, -1] - z[:, :, 0]


def observations(d):
    good = d["eeg_good"].reshape(-1, 16, 8).astype(bool)
    count = good.sum(axis=-1)
    def grouped(values):
        values = values.reshape(-1, 8, 16, 8)
        return np.where(good[:, None, :, :], values, 0).sum(axis=-1) / np.maximum(count[:, None], 1)
    scalp = np.concatenate((grouped(d["eeg_mean_uv"]), grouped(np.log1p(d["eeg_rms_uv"]))), axis=2)
    ng = d["nuisance_good"].astype(bool)
    nuisance = np.concatenate((d["nuisance_mean_uv"], np.log1p(d["nuisance_rms_uv"])), axis=2)
    return scalp, np.tile(count > 0, (1,2)), count/8., nuisance, np.tile(ng, (1,2)), ng


def standardized(values, good, fit):
    z = (values - fit["mean"]) / fit["sd"]
    return np.where(good[:,None,:], z, 0.)


def nuisance_predictors(z, mask):
    return np.concatenate((z, np.broadcast_to(mask[:,None,:], (*z.shape[:2], mask.shape[1]))), axis=-1)


def materialize(d, state, *, donor=None):
    recent, motion, tokens = movement(d["motion_mm"])
    scalp, sg, frac, nuisance, ng, mask = observations(d)
    if donor is not None:
        scalp, sg, frac = scalp[donor], sg[donor], frac[donor]
    eeg = standardized(scalp, sg, state["scalp_stats"])
    nz = standardized(nuisance, ng, state["nuisance_stats"])
    return {"recent":recent, "motion":motion, "tokens":tokens, "cue":d["direction"].reshape(-1,1),
            "scalp":eeg, "scalp_valid":sg, "fraction":frac, "nuisance":nz, "nuisance_mask":mask}


def design(mode, v, state, encoders):
    cue, frac = v["cue"], v["fraction"]
    if mode == "masks_only":
        return np.column_stack((cue, frac, v["nuisance_mask"]))
    if mode == "scalp_only":
        return np.column_stack((cue, frac, v["scalp"].reshape(len(cue), -1)))
    parts = [v["motion"], cue]
    if mode in USES_NUISANCE:
        subset = {"motion_eyes": [2,3,4], "motion_neck":[0,1], "motion_legs":list(range(5,13))}
        channels = subset.get(mode, list(range(13)))
        signal = v["nuisance"][:, :, channels + [i+13 for i in channels]]
        parts.extend((signal.reshape(len(cue), -1), v["nuisance_mask"][:, channels]))
    if mode in ("linear_nuisance", "linear_full", *USES_ENCODER):
        # Presence of a sensor can identify a session; keep this cue in the matched control as well.
        parts.append(frac)
        scalp = v["scalp"] if mode in USES_SCALP else np.zeros_like(v["scalp"])
        if mode == "shared_residual":
            fit = state["nuisance_regression"]
            pred = nuisance_predictors(v["nuisance"],v["nuisance_mask"]) @ fit["coef"] + fit["bias"]
            scalp = np.where(v["scalp_valid"][:,None,:], scalp-pred, 0.)
        parts.append(scalp.reshape(len(cue),-1))
    if mode in USES_ENCODER:
        from predict import encode, linear
        cfg, weights = encoders
        z = (v["tokens"] - state["token_mean"]) / state["token_sd"]
        parts.append(encode(cfg, weights, linear(weights, "project", z)))
    return np.column_stack(parts)


def predict(mode, v, d, state, encoders):
    shape = (-1, 2, 3)
    if mode == "hold":
        return np.zeros_like(v["recent"]).reshape(shape)
    if mode == "recent":
        return v["recent"].reshape(shape)
    if mode == "velocity":
        h = d["motion_mm"]
        return 2 * (h[:, -1] - h[:, -17])
    if mode == "cue_mean":
        return np.array([state["cue_mean"][str(int(q))] for q in v["cue"][:,0]]).reshape(shape)
    f = state["fits"][mode]
    x = design(mode, v, state, encoders)
    base = 0 if mode in ("masks_only","scalp_only") else v["recent"]
    correction = ((x-f["mean"])/f["sd"]) @ f["coef"] + f["bias"]
    return (correction + base).reshape(shape)


def numbers(record, key, shape, nonnegative=False):
    raw = np.asarray(record[key])
    if raw.shape != shape or raw.dtype.kind not in "iuf":
        raise ValueError(f"{key} needs a numerical array of shape {shape}.")
    value = raw.astype(float)
    if not np.isfinite(value).all() or (nonnegative and (value<0).any()):
        raise ValueError(f"{key} contains an invalid measurement.")
    return value[None]


def mask(record, key, width):
    raw = np.asarray(record[key])
    if raw.shape != (width,) or raw.dtype.kind not in "biu" or not np.isin(raw,[0,1]).all():
        raise ValueError(f"{key} needs {width} availability flags.")
    return raw.astype(bool)[None]


def forecast(record, state, encoders):
    mode=record.get("mode")
    if mode not in (*BASELINES,*LEARNED):
        raise ValueError("Choose a supported visual-balance forecast method.")
    direction=record.get("direction")
    if type(direction) is not str or direction not in ("clockwise","counterclockwise"):
        raise ValueError("Choose clockwise or counterclockwise visual rotation.")
    keys={"domain","mode","direction"}
    needs_motion=mode not in ("cue_mean","masks_only","scalp_only")
    needs_nuisance=mode in USES_NUISANCE
    needs_nmask=needs_nuisance or mode=="masks_only"
    needs_eeg=mode in USES_SCALP
    needs_emask=needs_eeg or mode in ("masks_only","linear_nuisance","shared_nuisance")
    if needs_motion:keys.add("motion_mm")
    if needs_nmask:keys.add("nuisance_good")
    if needs_emask:keys.add("eeg_good")
    if needs_nuisance:keys.update(("nuisance_mean_uv","nuisance_rms_uv"))
    if needs_eeg:keys.update(("eeg_mean_uv","eeg_rms_uv"))
    if set(record)!=keys:
        raise ValueError("Required fields for this method: "+", ".join(sorted(keys)))
    d={"direction":np.array([1 if direction=="clockwise" else -1]),
       "motion_mm":numbers(record,"motion_mm",(160,2,3)) if needs_motion else np.zeros((1,160,2,3))}
    if needs_motion:d["motion_mm"]=d["motion_mm"]-d["motion_mm"][:,-1:]
    for kind,width,signal_required,mask_required in (("eeg",128,needs_eeg,needs_emask),("nuisance",13,needs_nuisance,needs_nmask)):
        d[kind+"_good"]=mask(record,kind+"_good",width) if mask_required else np.zeros((1,width),bool)
        for stat in ("mean","rms"):
            k=kind+"_"+stat+"_uv"
            d[k]=numbers(record,k,(8,width),stat=="rms") if signal_required else np.zeros((1,8,width))
        if signal_required:
            mean,rms=d[kind+"_mean_uv"],d[kind+"_rms_uv"]
            if (d[kind+"_good"][:,None,:] & (abs(mean)>rms+1e-5*(1+rms))).any():
                raise ValueError("A good channel's RMS amplitude cannot be smaller than its absolute mean.")
    with np.errstate(all="ignore"):
        result=predict(mode,materialize(d,state),d,state,encoders)[0]
    if not np.isfinite(result).all():
        raise ValueError("Input exceeds the supported numerical range.")
    return {"mode":mode,"stored_horizon_ms":125,"source_axes":["mediolateral","superiorinferior","anteriorposterior"],
            "sacrum_delta_mm":result[0].tolist(),"head_delta_mm":result[1].tolist()}
