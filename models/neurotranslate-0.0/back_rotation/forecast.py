"""Use frozen shared movement features to forecast a back-mounted sensor's rotation."""
import numpy as np

TASKS = {"standing":611,"walking":621}
COLS = {"motion":(0,1),"upper":(0,1,2,3),"lower":(0,1,4,5),"full":(0,1,2,3,4,5)}
METHOD = {"linear_motion":"motion","shared_motion":"motion","shared_upper":"upper","shared_lower":"lower",
          "linear_full":"full","shared_full":"full","random_full":"full"}
MODES=("zero","recent","task_median",*METHOD)


def numeric_weights(mapping):
    return {k:np.asarray(v,dtype=np.float64) for k,v in mapping.items()}


def design(mode,x,anchor,task,fit,model,config,w,linear,encode):
    selected=COLS[METHOD[mode]]
    z=np.zeros_like(x,dtype=np.float64)
    z[:,:,selected]=(np.log1p(x[:,:,selected])-np.asarray(fit["bin_mean"])[list(selected)])/np.asarray(fit["bin_sd"])[list(selected)]
    sections=[z.reshape(len(x),24),np.log1p(anchor)[:,None],(task==621)[:,None]]
    if not mode.startswith("linear"):
        backbone=numeric_weights(model["random_encoder"]) if mode=="random_full" else w
        sections.append(encode(config,backbone,linear(backbone,"project",z)))
    return np.column_stack(sections)


def batch(mode,x,anchor,task,model,config,w,linear,encode):
    if mode=="zero":return np.zeros(len(anchor))
    if mode=="recent":return anchor.copy()
    if mode=="task_median":return np.where(task==621,model["task_medians"]["621"],model["task_medians"]["611"])
    fit=model["fits"][mode]
    matrix=design(mode,x,anchor,task,fit,model,config,w,linear,encode)
    norm=(matrix-fit["mean"])/fit["sd"]
    log_prediction=np.log1p(anchor)+fit["intercept"]+norm@fit["coef"]
    return np.expm1(np.clip(log_prediction,0,np.log1p(180.)))


def checked_scalar(v):
    if isinstance(v,bool) or not isinstance(v,(float,int)) or not 0<=v<=180:raise ValueError("Use an angle from 0 to 180 degrees.")
    return float(v)


def forecast(record,model,config,w,linear,encode):
    mode=record.get("mode")
    if not isinstance(mode,str) or mode not in MODES:raise ValueError("Choose a supported back rotation method.")
    keys={"domain","mode"}
    needs_task=mode not in ("zero","recent")
    needs_anchor=mode not in ("zero","task_median")
    if needs_task:keys.add("task")
    if needs_anchor:keys.add("recent_angle_deg")
    if mode in METHOD:keys.add("bins")
    if record.keys()!=keys:raise ValueError("Expected only: "+", ".join(sorted(keys)))
    task=record.get("task","standing")
    if not isinstance(task,str) or task not in TASKS:raise ValueError("Choose walking or standing.")
    anchor=checked_scalar(record.get("recent_angle_deg",0))
    x=np.zeros((1,4,6))
    if mode in METHOD:
        cols=COLS[METHOD[mode]]; raw=record["bins"]
        if not isinstance(raw,list) or len(raw)!=4 or not all(isinstance(row,list) and len(row)==len(cols) for row in raw):
            raise ValueError(f"Supply four chronological rows of {len(cols)} numbers.")
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or v<0 for row in raw for v in row):
            raise ValueError("Bin features must be nonnegative numbers.")
        try:a=np.asarray(raw,dtype=np.float64)
        except OverflowError as e:raise ValueError("Number exceeds supported range.") from e
        if not np.isfinite(a).all() or (a[:,0]>180).any() or (a[:,1]>9000.0001).any():
            raise ValueError("Bin readings are outside the numerical or angular range.")
        x[0][:,cols]=a
    y=batch(mode,x,np.array([anchor]),np.array([TASKS[task]]),model,config,w,linear,encode)
    if not np.isfinite(y[0]):raise ValueError("Input exceeds the supported numerical range.")
    return {"mode":mode,"sensor":"back-mounted orientation sensor","horizon_seconds":0.10,"unsigned_rotation_deg":float(y[0])}
