"""Build task-specific corrections from an earlier local run with measured outcomes."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import cued_arm as arm
import group_arm as group
import predict
from knee.adapter import contains_boolean


def calibrate(records,checkpoint):
    if not isinstance(records,list) or not records:
        raise ValueError("Supply a list of earlier trials with a cue, four bins, and measured changes.")
    cfg,weights=predict.read_checkpoint(checkpoint)
    residuals=[];ids=[]
    for i,row in enumerate(records,1):
        if not isinstance(row,dict) or set(row)!={"cue","bins","observed_change_native_units"}:
            raise ValueError(f"Trial {i} needs a cue, bins and observed_change_native_units.")
        raw=row["observed_change_native_units"]
        actual=np.asarray(raw)
        if actual.shape!=(3,3) or actual.dtype.kind not in "fiu" or contains_boolean(raw) or not np.isfinite(actual).all():
            raise ValueError(f"Trial {i} needs three finite observed changes at each of three future times.")
        rec={"domain":"group_arm_change","mode":"shared_cue_motion","cue":row["cue"],"bins":row["bins"]}
        expected=group.forecast(rec,cfg,weights,predict.linear,predict.encode)["change_native_units"]
        difference=actual-np.asarray(expected)
        if not np.isfinite(difference).all():raise ValueError(f"Trial {i} exceeds the numerical range.")
        residuals.append(difference);ids.append(arm.CUES.index(row["cue"]))
    return {"model_id":cfg["group_arm"]["calibration_id"],
            "by_cue":group.summarize(np.stack(residuals),np.array(ids))}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trials",type=Path)
    parser.add_argument("--checkpoint",type=Path,default=HERE.parent/"movement-weights.npz")
    args=parser.parse_args()
    try:
        print(json.dumps(calibrate(json.loads(args.trials.read_bytes()),args.checkpoint),indent=2,allow_nan=False))
    except (ValueError,TypeError) as error:
        parser.exit(2,str(error)+"\n")
