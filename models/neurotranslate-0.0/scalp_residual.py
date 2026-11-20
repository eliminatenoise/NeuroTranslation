"""Correct a cued arm forecast using four early bins from supported instruments."""
import numpy as np
import cued_arm as arm

MODES=("still","cue_median","previous_shared","mechanics","scalp","eye","residual_scalp","joint")
FIT_MODES=MODES[3:]
SCALP={"scalp","residual_scalp","joint"}
EYE={"eye","residual_scalp","joint"}


def centered(a):
    return a-a[:,:2,:].mean(axis=1,keepdims=True)


def eye_residual(w, scalp, eyes):
    s=(scalp-w["scalp_residual.ocular.scalp_mean"])/w["scalp_residual.ocular.scalp_sd"]
    e=(eyes-w["scalp_residual.ocular.eye_mean"])/w["scalp_residual.ocular.eye_sd"]
    return s-e@w["scalp_residual.ocular.coef"]


def motion_features(bins,cfg,w,linear,encode):
    tokens,_=arm.tokens_and_anchor(bins)
    z=(tokens-w["group_arm.token.mean"])/w["group_arm.token.sd"]
    return np.column_stack((tokens.reshape(-1,24),encode(cfg,w,linear(w,"project",z))))


def features(mode,motion,scalp,eyes,w,*,donor=None):
    columns=[motion]
    if mode in ("eye","joint"):columns.append(eyes.reshape(len(motion),-1))
    if mode in ("scalp","residual_scalp","joint"):
        field=scalp if mode=="scalp" else eye_residual(w,scalp,eyes)
        if donor is not None:field=field[donor]
        columns.append(field.reshape(len(motion),-1))
    return np.column_stack(columns)


def batch(mode,ids,bins,scalp,eyes,cfg,w,linear,encode,*,donor=None):
    cube=w["group_arm.cue_median"][ids]
    if mode=="still":return np.zeros_like(cube)
    if mode=="cue_median":return cube
    if mode=="previous_shared":
        import group_arm
        return group_arm.batch("shared_cue_motion",ids,bins,cfg,w,linear,encode)
    motion=motion_features(bins,cfg,w,linear,encode)
    design=features(mode,motion,centered(scalp) if scalp is not None else None,
                    centered(eyes) if eyes is not None else None,w,donor=donor)
    key="scalp_residual."+mode+"."
    scaled=(design-w[key+"mean"])/w[key+"sd"]
    return cube+(scaled@w[key+"coef"]).reshape(-1,3,3)*w["group_arm.target_sd"]


def forecast(record,cfg,w,linear,encode):
    from knee.adapter import contains_boolean
    mode=record.get("mode")
    if cfg.get("scalp_residual",{}).get("format")!=1 or mode not in MODES:
        raise ValueError("Select a supported early-signal forecast.")
    required={"domain","mode"}
    ids=np.array([0])
    if mode!="still":
        required.add("cue")
        if record.get("cue") not in arm.CUES:raise ValueError("Select one of the seven visual task categories.")
        ids[0]=arm.CUES.index(record["cue"])
    shapes={}
    if mode not in ("still","cue_median"):shapes["bins"]=(4,6)
    if mode in SCALP:shapes["scalp_bins"]=(4,6)
    if mode in EYE:shapes["eye_bins"]=(4,3)
    if set(record)!=required|set(shapes):
        raise ValueError("Provide exactly the data required by this method: "+", ".join(sorted(required|set(shapes))))
    values={}
    for k,shape in shapes.items():
        raw=record[k];a=np.asarray(raw)
        if a.shape!=shape or a.dtype.kind not in "fiu" or contains_boolean(raw) or not np.isfinite(a).all():
            raise ValueError(f"{k} requires {shape[0]} rows of {shape[1]} finite numbers.")
        values[k]=a.astype(float)[None]
    with np.errstate(over="ignore", invalid="ignore"):
        y=batch(mode,ids,values.get("bins"),values.get("scalp_bins"),values.get("eye_bins"),cfg,w,linear,encode)[0]
    if not np.isfinite(y).all():raise ValueError("Instrument values exceed the numerical range.")
    return {"mode":mode,"channels":list(arm.CHANNELS),"horizon_after_cutoff_s":list(arm.DELAYS),"change_native_units":y.tolist()}
