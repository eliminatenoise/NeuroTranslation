"""Fit on three rat IDs. Score the three different preselected rat IDs once, with a past-trip control."""
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import hashlib
import json
import numpy as np

from predict import ROOT, REGIONS, OFFSETS, motion_features, neural_features, ridge_predict


def write(name, data):
    (ROOT/name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def input_record(r):
    return {k:r[k] for k in ("cutoff_s","prior_time_s","prior_xy_cm","unit_counts","regional_counts")}


def schedule(start, stop):
    elapsed = np.arange(2., stop-start, 2.)
    return elapsed[(start + elapsed + .25 + .05) <= stop-.25]


def read_rat(rat):
    selection = json.loads((ROOT/"source"/f"selection-{rat}.json").read_text())
    evidence = json.loads((ROOT/"source"/f"ranges-{rat}.json").read_text())
    source = ROOT/"packets"/f"{rat}.npz"
    if hashlib.sha256(source.read_bytes()).hexdigest() != evidence["packet_sha256"]:
        raise ValueError("Packet did not match its source digest")
    previous, rows, dispositions, exclusions = [], [], [], Counter()
    with np.load(source, allow_pickle=False) as arrays:
        units = arrays["unit_region"]
        sizes = [int(np.sum(units == region)) for region in REGIONS]
        if sizes != [selection["region_counts"][s] for s in REGIONS] or min(sizes) < 1:
            raise ValueError(f"Inconsistent regional unit counts for {rat}")
        for trip in selection["trips"]:
            ident, start, stop = trip["id"], trip["start_s"], trip["stop_s"]
            p = f"t{ident}_"
            ts, xy = arrays[p+"time_s"], arrays[p+"xy_cm"]
            frames = arrays[p+"camera_row"]
            cells = np.split(arrays[p+"spike_flat_s"], arrays[p+"spike_end"][:-1])
            time_by_region = [np.sort(np.concatenate([s for s,u in zip(cells,units,strict=True) if u == k]))
                              for k in REGIONS]
            elapsed = schedule(start, stop)
            counts = Counter()
            donors = []
            for dt in elapsed:
                c = start + dt
                tick = c + OFFSETS
                rates = np.stack([np.diff(np.searchsorted(s,tick,side="right")) for s in time_by_region], axis=1)
                donors.append((ident, float(dt), float(c), rates))
                if not previous:
                    counts["no_earlier_donor"] += 1
                    continue
                ix = np.searchsorted(ts, tick, side="right") - 1
                label = int(np.searchsorted(ts, c+.25, side="left"))
                if np.any(ix < 0):
                    reason = "missing_history"
                elif np.any(tick-ts[ix] > .075):
                    reason = "stale_history"
                elif label == len(ts):
                    reason = "missing_target"
                elif ts[label] - (c+.25) > .05:
                    reason = "late_target"
                elif np.any(np.diff(ts[ix[0]:label+1]) > .100):
                    reason = "camera_gap"
                elif not np.all(np.isfinite(xy[np.r_[ix,label]])):
                    reason = "nonfinite_xy"
                else:
                    reason = "retained"
                    did, _, donor_s, wrong = min(previous, key=lambda d: (abs(d[1]-dt),-d[0],d[1]))
                    assert donor_s < start and ts[ix[-1]] <= c < ts[label] < stop
                    rows.append(dict(rat=rat,trip=ident,cutoff_s=float(c),prior_time_s=ts[ix].tolist(),
                             prior_xy_cm=xy[ix].tolist(), prior_camera_rows=frames[ix].tolist(),
                             target_time_s=float(ts[label]),target_xy_cm=xy[label].tolist(),
                             target_camera_row=int(frames[label]),
                             target_cm=float(np.linalg.norm(xy[label]-xy[ix[-1]])), unit_counts=sizes,
                             regional_counts=rates.tolist(),donor_trip=did,donor_cutoff_s=donor_s,
                             donor_counts=wrong.tolist()))
                counts[reason] += 1
            previous.extend(donors)
            exclusions.update(counts)
            dispositions.append(dict(trip=ident,planned=len(elapsed),dispositions=dict(counts)))
    return rows, dict(by_trip=dispositions,total=dict(exclusions), region_units=sizes)


def arrays(rows):
    y = np.array([r["target_cm"] for r in rows])
    x = motion_features(*[np.asarray([r[k] for r in rows])
                          for k in ("cutoff_s","prior_time_s","prior_xy_cm")])
    units = np.array([r["unit_counts"] for r in rows])
    n, d = [neural_features(np.array([r[k] for r in rows]), units)
            for k in ("regional_counts","donor_counts")]
    return y, x, n, d


def weights(rows):
    rat_count = len({r["rat"] for r in rows})
    trips = {}
    n = Counter((r["rat"],r["trip"]) for r in rows)
    for rat, trip in n:
        trips[rat] = trips.get(rat,0)+1
    return np.array([1.0/(rat_count*trips[r["rat"]]*n[(r["rat"],r["trip"])]) for r in rows])


def fit(x, y, w):
    mean = np.average(x,axis=0,weights=w)
    scale = np.sqrt(np.average((x-mean)**2,axis=0,weights=w))
    scale[scale < 1e-8] = 1
    z = (x-mean)/scale
    base = np.average(y,weights=w)
    coef = np.linalg.solve((z.T*w)@z + .03*np.eye(z.shape[1]),(z.T*w)@(y-base))
    return dict(mean=mean.tolist(),scale=scale.tolist(),intercept=float(base),coefficient=coef.tolist())


def record_trace(example_rows, fitted):
    row = example_rows[0]
    rat, trip = row["rat"], row["trip"]
    sel = json.loads((ROOT/"source"/f"selection-{rat}.json").read_text())
    meta = next(t for t in sel["trips"] if t["id"] == trip)
    write("example-input.json",input_record(row))
    y,x,n,d = arrays(example_rows)
    predictions = {
        "speed_cm": (.25*x[:,3]).tolist(), "motion_cm":ridge_predict(fitted["motion"],x).tolist(),
        "combined_cm":ridge_predict(fitted["combined"],np.column_stack([x,n])).tolist(),
        "wrong_cm":ridge_predict(fitted["combined"],np.column_stack([x,d])).tolist()}
    anchors = []
    for i,r in enumerate(example_rows):
        anchors.append({**r, **{k:v[i] for k,v in predictions.items()}})
    with np.load(ROOT/"packets"/f"{rat}.npz") as data:
        p = f"t{trip}_"
        time,xy = data[p+"time_s"],data[p+"xy_cm"]
        cells = np.split(data[p+"spike_flat_s"],data[p+"spike_end"][:-1])
        edges = meta["start_s"] + .25*np.arange(1 + int(np.floor((meta["stop_s"]-meta["start_s"])/.25)))
        neural = []
        for region in REGIONS:
            s = np.sort(np.concatenate([t for t,u in zip(cells,data["unit_region"],strict=True) if u==region]))
            neural.append(np.diff(np.searchsorted(s,edges,"right")).tolist())
        write("trace.json",{"doi":"10.48324/dandi.000978/0.240511.0307","asset_id":sel["asset_id"],
              "rat":rat,"session":sel["session"],"epoch":sel["epoch"]["id"],"trip":meta,
              "frame":sel["spatial_frame"],"region_order":list(REGIONS),"unit_counts":row["unit_counts"],
              "camera_time_s":time.tolist(),"camera_xy_cm":[[float(v) if np.isfinite(v) else None for v in pair] for pair in xy],
              "camera_rows":data[p+"camera_row"].tolist(),"count_bin_edges_s":edges.tolist(),
              "spike_counts_by_region":neural,"forecast_anchors":anchors})


def main():
    proto = json.loads((ROOT/"protocol.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["fit","score"])
    args = parser.parse_args()
    rows, coverage = [], {}
    for rat in proto["train" if args.phase=="fit" else "test"]:
        rat_rows, coverage[rat] = read_rat(rat)
        if rat_rows:
            rows.extend(rat_rows)
    write("coverage-"+args.phase+".json",coverage)
    y,x,n,d = arrays(rows)
    combined = np.column_stack([x,n])
    if args.phase == "fit":
        w = weights(rows)
        fitted = dict(motion=fit(x,y,w),combined=fit(combined,y,w))
        write("weights.json",fitted)
        return
    fitted = json.loads((ROOT/"weights.json").read_text())
    pred = {"constant_speed":.25*x[:,3],"motion":ridge_predict(fitted["motion"],x),
            "combined":ridge_predict(fitted["combined"],combined),
            "earlier_trip":ridge_predict(fitted["combined"],np.column_stack([x,d]))}
    per_trip = {}
    for i,r in enumerate(rows):
        g = (r["rat"],r["trip"])
        per_trip.setdefault(g,[]).append(i)
    trip_table = []
    for (rat,trip), ids in per_trip.items():
        trip_table.append(dict(rat=rat,trip=trip,anchors=len(ids),**{
              k:float(np.abs(p[ids]-y[ids]).mean()) for k,p in pred.items()}))
    rat_table = []
    for rat in proto["test"]:
        records = [t for t in trip_table if t["rat"]==rat]
        if not records:
            continue
        rat_table.append(dict(rat=rat,trips=len(records),anchors=sum(t["anchors"] for t in records),
            **{k:float(np.mean([t[k] for t in records])) for k in pred}))
    macro = {k:float(np.mean([r[k] for r in rat_table])) for k in pred}
    for r in [*rat_table, macro]:
        r.update(motion_minus_combined=r["motion"]-r["combined"], earlier_minus_combined=r["earlier_trip"]-r["combined"])
    write("scores.json",dict(unit="cm MAE",by_rat=rat_table,equal_rat=macro,by_trip=trip_table,
          consistent_gain=all(r["motion_minus_combined"]>0 and r["earlier_minus_combined"]>0 for r in rat_table)
                and len(rat_table)==len(proto["test"])))
    with (ROOT/"predictions.csv").open("w",newline="") as f:
        out = csv.writer(f)
        out.writerow(["rat","trip","cutoff_s","target_time_s","donor_trip","donor_cutoff_s","target_cm",*pred])
        for i,r in enumerate(rows):
            out.writerow([r[k] for k in ("rat","trip","cutoff_s","target_time_s","donor_trip","donor_cutoff_s","target_cm")]
                         + [p[i] for p in pred.values()])
    first = rows[0]
    record_trace([r for r in rows if (r["rat"],r["trip"])==(first["rat"],first["trip"])], fitted)
    print(json.dumps(dict(by_rat=rat_table,equal_rat=macro),indent=2))


if __name__ == "__main__":
    main()
