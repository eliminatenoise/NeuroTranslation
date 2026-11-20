"""Score frozen forecasts on an extracted split. Only group estimates are public."""
import argparse
import json
from pathlib import Path

from network import (configure, inputs, np, predictions, prepare, read_events, restore,
                     sha256, write_json)
from scoring import donors, extract_errors, grouped, paired, summarize


def evaluate(path, weights_path, transfer_path, report_path, private_path=None):
    data = read_events(path)
    arrays = inputs(data)
    w = json.loads(Path(weights_path).read_text())
    prepared = prepare(arrays,w["scale"],"cpu")
    fitted = {key:restore(value,key) for key,value in w["models"].items()}
    predicted = {key:predictions(model,prepared,w["scale"]) for key,model in fitted.items()}
    methods = {"joint":predicted["joint"],"specialists":(predicted["muscle"][0],predicted["path"][1])}
    leg,xyz = data["leg_uv"].astype(float),data["sacrum_mm"].astype(float)
    hold = np.sqrt((leg[:,-32:]**2).mean(1))
    repeated = xyz[:,-32:]-xyz[:,-33:-32]
    steps = np.arange(1,33)[None,:,None]
    methods.update(hold_repeat32=(hold,repeated),hold_stationary=(hold,np.zeros_like(repeated)),
                   hold_velocity16=(hold,(xyz[:,-1:]-xyz[:,-17:-16])*steps/16),
                   hold_velocity32=(hold,(xyz[:,-1:]-xyz[:,-33:-32])*steps/32))
    all_ids, ids = np.arange(len(leg)),np.flatnonzero(data["paired"])
    posture_ids = np.flatnonzero(data["posture_qualified"])
    scores, rows, priv = {}, {}, {}
    for key,(y,p) in methods.items():
        e = extract_errors(data,all_ids,y,p)
        scores[key],rows[key] = summarize(data,ids,e[ids])
        scores[key]["all_posture_qualified"] = {
            name:grouped(data,posture_ids,e[posture_ids],(s,))[0] for s,name in ((0,"stand"),(1,"walk"))}
        priv["error_"+key] = e
        if key in ("joint","specialists"):
            priv[key+"_rms"],priv[key+"_path"] = y,p
    contrast = {f"joint_minus_{key}":paired(rows["joint"],r) for key,r in rows.items() if key!="joint"}
    primary = contrast["joint_minus_specialists"]["differences"]
    passes = bool(primary and all(primary[k]["upper_97_5_one_sided"]<0
                                  for k in ("muscle_mae_uv","path_mean_distance_mm")))
    recipients,source = donors(data,ids)
    swapped = {**data, "leg_uv":data["leg_uv"][source],"sacrum_mm":data["sacrum_mm"][recipients],
               "posture":data["posture"][recipients], "direction":data["direction"][recipients]}
    swapped_rms,swapped_path = predictions(fitted["joint"],prepare(inputs(swapped),w["scale"],"cpu"),w["scale"])
    wrong_errors = extract_errors(data,recipients,swapped_rms,swapped_path)
    wrong,wrong_rows = summarize(data,recipients,wrong_errors)
    right,right_rows = summarize(data,recipients,priv["error_joint"][recipients])
    wrong_control = dict(swapped=wrong,factual_same_events=right,swapped_minus_factual=paired(wrong_rows,right_rows),
                         eligible_recipient_events=len(recipients),candidate_events=len(ids))
    priv.update(recipient_indices=recipients,donor_indices=source,wrong_event_errors=wrong_errors)
    tw = json.loads(Path(transfer_path).read_text())
    standing = ids[data["posture"][ids]==0]
    transfer_in = prepare([a[standing] for a in arrays],tw["scale"],"cpu")
    trans, transfer_rows = {}, {}
    for name,weights in tw["models"].items():
        y,p = predictions(restore(weights,"joint"),transfer_in,tw["scale"])
        err=extract_errors(data,standing,y,p)
        trans[name],transfer_rows[name]=grouped(data,standing,err,(0,))
        priv["transfer_error_"+name]=err
    trans["mixed"],transfer_rows["mixed"]=grouped(data,standing,priv["error_joint"][standing],(0,))
    transfer_stats = {f"{one}_minus_{two}":paired(transfer_rows[one],transfer_rows[two])
                      for one in ("walk","adapt_heads","adapt_full","mixed") for two in ("stand_640","stand_1280")}
    for a,b in (("adapt_full","walk"),("adapt_heads","walk"),("adapt_full","adapt_heads")):
        transfer_stats[a+"_minus_"+b]=paired(transfer_rows[a],transfer_rows[b])
    if private_path:
        np.savez_compressed(private_path, **priv,standing_indices=standing,
                            **{k:data[k] for k in ("person","posture","direction","event","cutoff","block","paired")})
    result = dict(primary_joint_advantage=passes,assessment_people_if_all_cells=len(rows["joint"][0]),
                  transformer_and_controls=scores,contrasts=contrast,wrong_event=wrong_control,
                  standing_transfer=dict(scores=trans,contrasts=transfer_stats),
                  inference="5000 paired whole-person bootstrap draws; 97.5th percentile upper bounds, joint minus specialist. Negative favours joint.",
                  weights_sha256=sha256(weights_path),transfer_weights_sha256=sha256(transfer_path))
    write_json(report_path,result)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("split","weights","transfer_weights","report"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--private-rows",type=Path)
    a=parser.parse_args()
    configure(1)
    evaluate(a.split,a.weights,a.transfer_weights,a.report,a.private_rows)
