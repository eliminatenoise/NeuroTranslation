"""Apply the separately registered one-deposited-time sensitivity after strict preparation."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from fetch import MEMBERS, ROOT, check
from prepare import TrialError, describe_failure, table, trial_windows, vector, write_json
from summarize import data_summary, sha


def trigger_check(rec, hz):
    tm, potential, ev = (vector(rec, k) for k in ("time","PotMem","spiketimes"))
    ticks = np.rint((ev-tm[0])*hz).astype(np.int64)
    half = int(np.floor(.0015*hz+.5))
    offsets = np.floor(np.array([0,.0037,.0061,.0123])*hz+.5).astype(np.int64)
    peri = np.arange(-half, half+1)
    ticks = ticks[(ticks >= half) & (ticks+offsets[-1]+half < len(potential))]
    if not len(ticks) or not half:
        return {"matched_events":0, "contributes":False, "reason":"no matched finite segments"}
    segments = potential[ticks[:,None,None]+offsets[None,:,None]+peri[None,None,:]]
    segments = segments[np.isfinite(segments).all(axis=(1,2))]
    output = {"matched_events": len(segments), "native_hz":hz, "offset_samples": offsets.tolist(),
              "window_samples_each_side":half, "contributes": len(segments)>=10}
    if len(segments):
        segments -= segments.mean(axis=2, keepdims=True)
        curve = segments.mean(axis=0)
        amplitudes = np.ptp(curve, axis=1)
        output.update(offset_amplitudes=amplitudes.tolist(),
                      peak_to_peak_excess_over_largest_shift=float(amplitudes[0]-max(amplitudes[1:])),
                      raw_trigger_min=float(curve[0].min()),raw_trigger_max=float(curve[0].max()),
                      raw_trigger_min_latency_ms=float(peri[curve[0].argmin()]*1000/hz),
                      raw_trigger_max_latency_ms=float(peri[curve[0].argmax()]*1000/hz))
    return output


def examine(group, path, out):
    proof = check(path, MEMBERS[path.name])
    assert group["integrity"] == proof
    contents = loadmat(path,variable_names=["info","proc_data"],squeeze_me=True,struct_as_record=False)
    info = contents["info"]
    trials = np.atleast_1d(contents["proc_data"]).ravel(order="F")
    labels = np.atleast_1d(info.trial_type).ravel(order="F")
    trial_checks, extra_rows, extra_masks = [], [], []
    for i, rec in enumerate(trials):
        if "time_PotMem" in rec._fieldnames:
            continue
        entry = dict(afferent=group["afferent"],prefix=group["prefix"],trial=i+1,
                     rows=0,eligible=False,clock_route="one_deposited_time")
        trial_checks.append(entry)
        try:
            if str(info.affname)!=entry["afferent"] or len(labels)!=len(trials):
                raise TrialError("identity or trial-label cardinality mismatch")
            label = labels[i]
            if not isinstance(label, (str,np.str_)) or not label.strip():
                raise TrialError("missing source trial label")
            entry.update(trial_type=str(label),protocol_class="repeated ramp-release"
                         if label=="triangle_series" else "ramp-hold-release variant")
            rows, mask = trial_windows(rec, entry, out, single_time=True)
            entry["timing_ok"] = True
            entry["voltage_corroboration"] = trigger_check(rec, entry["time"]["hz"])
            mask["afferent"] = np.repeat(entry["afferent"], len(mask["valid"]))
            mask["trial"] = np.full(len(mask["valid"]),i+1,dtype=np.int32)
            extra_rows.append(rows)
            extra_masks.append(mask)
        except TrialError as err:
            entry.update(timing_ok=False, timing_error=str(err))
            describe_failure(rec, entry)
    tested = [t["voltage_corroboration"]["peak_to_peak_excess_over_largest_shift"] for t in trial_checks
              if t.get("voltage_corroboration",{}).get("contributes")]
    timing_pass = all(t["timing_ok"] for t in trial_checks)
    voltage_pass = len(tested)>=min(2,len(trial_checks)) and len(tested)>0 and np.median(tested)>0 and sum(x>0 for x in tested)>len(tested)/2
    admitted = bool(timing_pass and voltage_pass)
    gate = {"candidate_trials":len(trial_checks),
            "native_single_axis_hz":sorted({t["time"]["hz"] for t in trial_checks if "time" in t}),
            "max_abs_event_grid_error_s":max((t.get("max_event_seconds_grid_error_s",0.) for t in trial_checks),default=None),
            "matched_voltage_events":sum(t.get("voltage_corroboration",{}).get("matched_events",0) for t in trial_checks),"timing_failures":sum(not t["timing_ok"] for t in trial_checks),
            "voltage_contributing_trials":len(tested),"voltage_wins":sum(x>0 for x in tested),
            "voltage_median_excess":float(np.median(tested)) if tested else None,
            "voltage_member_gate":bool(voltage_pass),"timing_member_gate":timing_pass,"admitted":admitted}
    for entry in trial_checks:
        if admitted:
            entry["eligible"] = entry["rows"]>0
            if not entry["eligible"]:
                entry["reason"]="no span of six complete valid bins"
        else:
            entry["candidate_rows_before_member_gate"]=entry["rows"]
            entry["rows"]=0
            entry["candidate_target_spikes_before_member_gate"]=entry.get("target_spikes",0)
            entry["target_spikes"]=0
            entry["reason"]=entry.get("timing_error","single-time member corroboration or all-trial timing gate failed")
        group["trials"][entry["trial"]-1]=entry
    return gate, extra_rows if admitted else [], extra_masks if admitted else []


def ordered_merge(strict_path, additional, out):
    with np.load(strict_path,allow_pickle=False) as base:
        strict = dict(base)
    joint = table([strict]+additional)
    order = np.lexsort((joint["bin_index"],joint["trial"],joint["afferent"]))
    for k in joint:
        joint[k]=joint[k][order]
    tmp=out.with_suffix(".tmp.npz")
    np.savez_compressed(tmp,**joint)
    tmp.replace(out)
    return joint


def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("--directory",type=Path,default=ROOT/"private"/"members")
    args.add_argument("--strict-output",type=Path,default=ROOT/"private")
    args.add_argument("--output",type=Path,default=ROOT/"private"/"sensitivity")
    args=args.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    groups=json.loads((args.strict_output/"trial-qc.json").read_text())
    rows,masks,gates=[],[],{}
    for group in groups:
        missing = [t for t in group["trials"] if t.get("excluded_source_diagnostics",{}).get("time_PotMem",{}).get("available") is False]
        if not missing:
            continue
        gate,extra_rows,extra_masks=examine(group,args.directory/group["member"],out)
        gates[group["afferent"]]=gate
        rows.extend(extra_rows)
        masks.extend(extra_masks)
        print(group["afferent"],gate,flush=True)
    merged=ordered_merge(args.strict_output/"windows.npz",rows,out/"windows.npz")
    ordered_merge(args.strict_output/"bin-mask.npz",masks,out/"bin-mask.npz")
    write_json(out/"trial-qc.json",groups)
    trials=[t for g in groups for t in g["trials"]]
    result={"source_freeze":sha(ROOT/"SOURCE-FREEZE.json"),"additional_freeze":sha(ROOT/"SINGLE-CLOCK-SENSITIVITY.json"),
            "scope":"Original two-clock windows plus windows of members passing the separate one-deposited-time source gates. Named time only where archived; no independently deposited electrical clock for the sensitivity additions.",
            "metadata_checks":json.loads((ROOT/"QC-SUMMARY.json").read_text())["metadata_checks"],
            "overall":data_summary(trials),"prefixes":{str(pr):data_summary([t for t in trials if t["prefix"]==pr]) for pr in (0,1,4)},
            "members":{g["afferent"]:data_summary(g["trials"]) for g in groups},"source_gates":gates,
            "window_clock_routes":{str(k):int(v) for k,v in zip(*np.unique(merged["clock_route"],return_counts=True))},
            "excluded_trials":[dict(afferent=t["afferent"],trial=t["trial"],reason=t["reason"]) for t in trials if not t["eligible"]],
            "output_sha256":{n:sha(out/n) for n in ("windows.npz","bin-mask.npz","trial-qc.json")}}
    assert sum(t["rows"] for t in trials)==len(merged["y_count"])
    write_json(ROOT/"SENSITIVITY-QC-SUMMARY.json",result)


if __name__=="__main__":
    main()
