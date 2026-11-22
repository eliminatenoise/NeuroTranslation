"""Forecast overground heel movement and measured floor-plate loads."""

import argparse
import json
import math
from pathlib import Path

from paired_plates import DELAYS_MS, attention_readouts, numeric, require, shape, sigmoid, vector


HERE = Path(__file__).resolve().parent
SIDES = ["left", "right"]
MODES = {
    "body-force": (True, True),
    "room-force": (False, True),
    "body-motion": (True, False),
}
WINDOW_BINS = 10
VELOCITY_WEIGHTS = [float((i - 4.5) * .1 / (.02 * 82.5)) for i in range(WINDOW_BINS)]


def number_or_missing(value):
    return value is None or numeric(value)


def coordinate_or_missing(value):
    return value is None or (isinstance(value, list) and len(value) == 3 and all(numeric(x) for x in value))


def setup_history(history, mode):
    require(history["side_order"] == SIDES, "Give the histories in left, right order.")
    times = history["bin_end_ms"]
    require(isinstance(times,list) and len(times)>=WINDOW_BINS and all(type(value) is int for value in times),
            "Give at least ten integer bin ends in milliseconds.")
    require(all(later-earlier==20 for earlier,later in zip(times,times[1:])),
            "Use exactly 20 milliseconds between bin ends.")
    body_frame,use_force = MODES[mode]
    count = len(times)
    heel = history["heel_xyz_mm"]
    shape(heel,2,count,"heel_xyz_mm")
    require(all(coordinate_or_missing(value) for side in heel for value in side),
            "Give an XYZ heel position or null at each bin end.")
    pelvis = history.get("pelvis_xyz_mm") if body_frame else None
    if body_frame:
        require(isinstance(pelvis,list) and len(pelvis)==count and all(coordinate_or_missing(value) for value in pelvis),
                "Give one XYZ position or null for the front pelvis midpoint at each bin end.")
    force=state=None
    if use_force:
        force,state=(history[field] for field in ("vertical_force_n","plate_state_by_bin"))
        shape(force,2,count,"vertical_force_n")
        shape(state,2,count,"plate_state_by_bin")
        require(all(number_or_missing(value) for side in force for value in side),
                "Give finite vertical force readings in newtons, or null if absent.")
        require(all(type(value) is int and 0<=value<=3 for side in state for value in side),
                "Use plate state 0, 1, 2 or 3.")
    return times,heel,pelvis,force,state


def read_history(history, mode):
    times,heel,pelvis,force,state = setup_history(history,mode)
    body_frame,use_force = MODES[mode]
    paired=[[],[]]
    admitted=[]
    newest=len(times)-1
    for lag in DELAYS_MS:
        end=newest-lag//20
        start=end-WINDOW_BINS+1
        if start<0:
            continue
        section=slice(start,end+1)
        h=[row[section] for row in heel]
        hips=pelvis[section] if pelvis is not None else None
        f=[row[section] for row in force] if use_force else None
        if any(value is None for side in h for value in side):
            continue
        if hips is not None and any(value is None for value in hips):
            continue
        if f is not None and any(value is None for side in f for value in side):
            continue
        admitted.append(lag)
        for side,foot in enumerate(h):
            force_columns=vector(f[side],state[side][end]) if use_force else [0.]*23
            if body_frame:
                foot=[[xyz[0]-hip[0],xyz[1]-hip[1],xyz[2]] for xyz,hip in zip(foot,hips)]
            motion=[value-foot[-1][axis] for axis,coord in enumerate(zip(*foot)) for value in coord]
            paired[side].append(force_columns+motion+[0.]*20)
    require(admitted and admitted[0]==0, "The current 200 ms needs complete readings for both feet and the chosen inputs.")
    drift=[0.,0.,0.]
    if body_frame:
        recent=pelvis[-WINDOW_BINS:]
        drift[:2]=[
            math.fsum((point[axis]-recent[-1][axis])*weight for point,weight in zip(recent,VELOCITY_WEIGHTS))
            for axis in (0,1)
        ]
    return times[-1],paired,admitted,drift


def predict(checkpoint, history, mode):
    require(mode in MODES and checkpoint["format"]=="overground_adaptive_v1" and checkpoint["lags_ms"]==DELAYS_MS,
            "The walking model or selected mode uses an unexpected format.")
    issue,paired,admitted,drift=read_history(history,mode)
    use_force=MODES[mode][1]
    base=checkpoint["weights"][mode]
    weights=base | {"lag":[base["lag"][DELAYS_MS.index(lag)] for lag in admitted]}
    for name in ("own.weight","other.weight"):
        weights[name]=[[value if i<53 and (i>=23 or use_force) else 0. for i,value in enumerate(row)]
                       for row in base[name]]
    result=[]
    for side,raw in zip(SIDES,attention_readouts(paired,checkpoint["normalizers"],weights)):
        physical=[value*scale+center for value,scale,center in zip(raw[1:],checkpoint["target_scale"],checkpoint["target_center"])]
        result.append({"side":side,"new_plate_load_probability":sigmoid(raw[0]),
            "signed_plate_impulse_newton_seconds":physical[0],
            "heel_displacement_xyz_millimetres":[axis+offset for axis,offset in zip(physical[1:],drift)]})
    return {"mode":mode,"issue_time_ms":issue,"forecast_horizon_ms":100,
            "companion_window_end_delays_ms":admitted,"predictions":result}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,help="Read a prepared walking history.")
    parser.add_argument("--mode",choices=tuple(MODES),default="body-force")
    args=parser.parse_args()
    try:
        payload=json.loads((HERE/"overground-heads.json").read_text(encoding="utf-8"))
        history=json.loads((args.input or HERE/"example-overground.json").read_text(encoding="utf-8"))
        result=predict(payload,history,args.mode)
        result["input_kind"]="user supplied" if args.input else "invented example"
        print(json.dumps(result,indent=2,allow_nan=False))
    except (OSError,TypeError,ValueError,KeyError,IndexError,OverflowError) as error:
        parser.exit(2,f"Unable to forecast. {error}\n")


if __name__=="__main__":
    main()
