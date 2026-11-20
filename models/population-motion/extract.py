"""Read eligible intervals, verify units and export only the preselected within-trip recordings."""
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np

from catalogue import ROOT, save
from ranges import PinnedRanges


def text(value):
    return value.decode() if isinstance(value, bytes) else str(value)


def inspect(f, rat, pin):
    subject = text(f["general/subject/subject_id"][()])
    assert subject == f"JDS-SingleDay-{rat}"
    assert f["session_start_time"][()] == f["timestamps_reference_time"][()]
    spatial = f["processing/behavior/Position/SpatialSeries"]
    assert spatial["timestamps"].attrs["unit"] == "seconds"
    assert spatial["data"].attrs["unit"] == "centimeters; centimeters/second"
    assert spatial["data"].attrs["conversion"] == 1 and spatial["data"].attrs["offset"] == 0
    assert "row1:xpos row2:ypos row3:velocity" in spatial.attrs["comments"]
    assert len(spatial["timestamps"]) == len(spatial["data"])
    tr = f["intervals/trials"]
    ids, starts, ends = (tr[k][:] for k in ("id", "start_time", "stop_time"))
    assert len(set(ids)) == len(ids) and np.all(np.isfinite([starts, ends]))
    assert np.all(starts < ends) and np.all(ends[:-1] <= starts[1:])
    ep = f["intervals/epoch intervals"]
    count_by_epoch = []
    chosen = None
    for row in np.argsort(ep["start_time"][:], kind="stable"):
        start, end = ep["start_time"][row], ep["stop_time"][row]
        contained = np.flatnonzero((starts >= start) & (ends <= end))
        eid = int(ep["id"][row])
        count_by_epoch.append({"epoch":eid,"n_complete":len(contained)})
        if chosen is None and len(contained) >= 16:
            chosen = contained[:16]
            epoch = dict(id=eid, row=int(row), start_s=float(start), stop_s=float(end))
    if chosen is None:
        raise ValueError(f"{rat} has no epoch with 16 complete trips")
    units = f["units"]
    erows = units["electrodes"][:]
    uids = units["id"][:]
    assert len(np.unique(uids)) == len(uids) == len(erows) == len(units["spike_times_index"])
    assert "electrodes_index" not in units, "Ragged electrode table needs explicit unit mapping"
    assert "obs_intervals" not in units, "Inspect supplied observation intervals before analysis"
    ets = f[units["electrodes"].attrs["table"]]
    names, locations, groups = (ets[k][:] for k in ("group_name", "location", "group"))
    records = []
    for urow, (uid, erow) in enumerate(zip(uids, erows, strict=True)):
        assert 0 <= erow < len(ets["id"])
        obj = f[groups[erow]]
        group = text(names[erow])
        electrode_region, group_region = text(locations[erow]), text(obj.attrs["location"])
        matched = group.lower() == obj.name.split("/")[-1].lower() and electrode_region == group_region
        region = electrode_region if matched and electrode_region in ("CA1","PFC") else None
        records.append(dict(unit_row=urow, unit_id=int(uid), electrode_row=int(erow),
                            electrode_group=group, electrode_region=electrode_region,
                            linked_group=obj.name, group_region=group_region, used_region=region))
    counts = Counter(row["used_region"] or "unassigned" for row in records)
    return dict(subject=subject, asset_id=pin["asset_id"], session=text(f["general/session_id"][()]),
                spatial_frame=text(spatial["reference_frame"][()]), total_units=len(uids), region_counts=dict(counts),
                units=records, epoch=epoch, complete_trips_by_epoch=count_by_epoch,
                trips=[dict(id=int(ids[i]), row=int(i), start_s=float(starts[i]), stop_s=float(ends[i]))
                       for i in chosen])


def packet(f, sel, rat):
    trips = sel["trips"]
    a, b = trips[0]["start_s"], trips[-1]["stop_s"]
    spatial = f["processing/behavior/Position/SpatialSeries"]
    times = spatial["timestamps"]
    lo, hi = bisect_right(times, a), bisect_left(times, b)
    t, xy = times[lo:hi], spatial["data"][lo:hi,:2]
    assert len(t) > 0 and a < t[0] <= t[-1] < b and np.all(np.diff(t) > 0)
    assert (lo == 0 or times[lo-1] <= a) and (hi == len(times) or times[hi] >= b)
    units = f["units"]
    st = units["spike_times"]
    unit_end = units["spike_times_index"][:].astype(int)
    assert unit_end[-1] == len(st) and np.all(np.diff(unit_end,prepend=0) >= 0)
    events, indices, region_per_unit = [], [], []
    for unit, lower, upper in zip(sel["units"], np.r_[0,unit_end[:-1]], unit_end, strict=True):
        if unit["used_region"] is None:
            continue
        i = bisect_right(st, a, int(lower), int(upper))
        j = bisect_left(st, b, i, int(upper))
        values = st[i:j]
        assert np.all(np.isfinite(values)) and np.all(np.diff(values)>=0)
        assert len(values) == 0 or a < values[0] <= values[-1] < b
        assert (i == lower or st[i-1] <= a) and (j == upper or st[j] >= b)
        indices.append(i)
        events.append(values)
        region_per_unit.append(unit["used_region"])
    all_arrays = {"unit_region":np.asarray(region_per_unit)}
    for trip in trips:
        ta, tb = trip["start_s"], trip["stop_s"]
        l, h = np.searchsorted(t, ta, "right"), np.searchsorted(t, tb, "left")
        sub = [(np.searchsorted(x,ta,"right"),np.searchsorted(x,tb,"left")) for x in events]
        k = f"t{trip['id']}_"
        all_arrays.update({k+"camera_row":np.arange(lo+l, lo+h), k+"time_s":t[l:h], k+"xy_cm":xy[l:h],
            k+"spike_flat_s":np.concatenate([x[l:h] for x,(l,h) in zip(events,sub,strict=True)]),
            k+"spike_end":np.cumsum([h-l for l,h in sub]),
            k+"spike_source_bounds":np.array([(n+l,n+h) for n,(l,h) in zip(indices,sub,strict=True)])})
    out = ROOT / "packets" / f"{rat}.npz"
    out.parent.mkdir(exist_ok=True)
    np.savez_compressed(out, **all_arrays)
    return hashlib.sha256(out.read_bytes()).hexdigest()


def main():
    if not __debug__:
        raise ValueError("Use Python without -O to preserve source integrity checks")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rat")
    parser.add_argument("--cache",type=Path, required=True)
    parser.add_argument("--metadata-only",action="store_true")
    args = parser.parse_args()
    rat = args.rat
    pin = json.loads((ROOT/"source/catalogue.json").read_text())["members"][rat]
    evidence = ROOT/"source"/f"ranges-{rat}.json"
    prior = json.loads(evidence.read_text())["blocks"] if evidence.is_file() else {}
    with PinnedRanges(args.cache,pin,prior) as raw, h5py.File(raw, "r") as f:
        selected = inspect(f,rat,pin)
        save(ROOT/"source"/f"selection-{rat}.json",selected)
        if not args.metadata_only:
            if not all(selected["region_counts"].get(r,0) for r in ("CA1","PFC")):
                print(f"{rat}: one or both regions absent; excluded")
                return
            digest = packet(f, selected, rat)
            save(evidence, dict(asset_id=pin["asset_id"], packet_sha256=digest,
                        block_size=raw.block, blocks=dict(sorted(raw.digests.items(),key=lambda kv:int(kv[0])))))
        print(rat, selected["epoch"]["id"], selected["region_counts"], len(raw.digests), raw.network_bytes)


if __name__ == "__main__":
    main()
