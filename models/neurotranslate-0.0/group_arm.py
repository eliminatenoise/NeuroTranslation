"""Forecast changes in three arm sensors using the multi-person development fit."""
import numpy as np
import cued_arm as arm

OFFSET = {"offset_free_linear":"cue_motion", "offset_free_shared":"shared_cue_motion"}
MODES = ("cue_median", *arm.MODES, *OFFSET, "calibrated_shared")


def parameters(weights, mode=None):
    """Use the existing arm computation with its separately fitted group parameters."""
    if "group_arm.cue_median" not in weights:
        raise ValueError("This checkpoint does not contain the group arm model.")
    view={**weights, **{"cued_arm."+k[len("group_arm."):]:v for k,v in weights.items()
                        if k.startswith("group_arm.")}}
    if mode in OFFSET:
        for suffix in ("mean","sd","coef","bias"):
            view["cued_arm."+OFFSET[mode]+"."+suffix]=weights["group_arm."+mode+"."+suffix]
    return view


def batch(mode, cue_ids, bins, config, weights, linear, encode):
    if mode == "cue_median":
        return weights["group_arm.cue_median"][cue_ids]
    return arm.batch(OFFSET.get(mode,mode), cue_ids, bins, config, parameters(weights,mode), linear, encode)


def calibration_matrix(summary):
    from knee.adapter import contains_boolean
    if not isinstance(summary,dict) or set(summary)!={"count","median_residual"}:
        raise ValueError("The correction requires a count and a 3-by-3 median residual for this cue.")
    count=summary["count"]
    if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=2**53-1:
        raise ValueError("Use a nonnegative integer trial count supported by both runtimes.")
    raw=summary["median_residual"]
    med=np.asarray(raw)
    if med.shape!=(3,3) or med.dtype.kind not in "fiu" or contains_boolean(raw) or not np.isfinite(med).all():
        raise ValueError("The median residual must contain nine finite numbers.")
    if count==0 and np.any(med):
        raise ValueError("Use zero residuals for a cue with no earlier examples.")
    return (count/(count+6))*med.astype(float)


def forecast(record,config,weights,linear,encode):
    if config.get("group_arm",{}).get("format")!=1 or record.get("mode") not in MODES:
        raise ValueError("Choose a group arm method supported by this checkpoint.")
    mode=record["mode"]
    if mode=="cue_median":
        if set(record)!={"domain","mode","cue"} or record.get("cue") not in arm.CUES:
            raise ValueError("The cue median uses only a supported right-arm instruction.")
        values=weights["group_arm.cue_median"][arm.CUES.index(record["cue"])]
        return {"mode":mode,"horizon_after_cutoff_s":list(arm.DELAYS),"channels":list(arm.CHANNELS),
                "change_native_units":values.tolist()}
    direct=dict(record)
    if mode=="calibrated_shared":
        profile=direct.pop("calibration",None)
        if not isinstance(profile,dict) or profile.get("model_id")!=config["group_arm"]["calibration_id"] or not isinstance(profile.get("by_cue"),dict):
            raise ValueError("Use an earlier-run calibration profile made with this group model.")
        cue=record.get("cue")
        if not isinstance(cue,str) or cue not in arm.CUES:raise ValueError("Select a supported cue.")
        correction=calibration_matrix(profile["by_cue"].get(cue))
        direct["mode"]="shared_cue_motion"
    if mode in OFFSET:direct["mode"]=OFFSET[mode]
    response=arm.forecast(direct,config,parameters(weights,mode),linear,encode)
    response["mode"]=mode
    if mode=="calibrated_shared":
        with np.errstate(over="ignore"):
            y=np.asarray(response["change_native_units"])+correction
        if not np.isfinite(y).all():raise ValueError("Calibrated forecast exceeds the numerical range.")
        response.update(mode=mode,change_native_units=y.tolist())
    return response


def summarize(residuals, cue_ids):
    """One earlier run: residuals are measured changes minus population forecasts."""
    output={}
    for i,task in enumerate(arm.CUES):
        own=residuals[cue_ids==i]
        output[task]={"count":len(own),"median_residual":(np.median(own,axis=0) if len(own) else np.zeros((3,3))).tolist()}
    return output
