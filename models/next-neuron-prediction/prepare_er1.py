"""Extract only the predeclared ER1 transfer trials from the original NWB. CC0."""
import argparse
import hashlib
from pathlib import Path

import h5py
import numpy as np

ASSET = "b6425692-0f32-4087-8412-aebcfc37cd96"
SHA256 = "508f7f4e5c1ef2b49373aef815bc64e6591ed7889407a3d57089d38dd4e2dba4"
SUBJECT = "JDS-SingleDay-ER1"


def extract(nwb, destination):
    if nwb["general/subject/subject_id"][()].decode() != SUBJECT:
        raise ValueError("Wrong recording")
    trials, units = nwb["intervals/trials"], nwb["units"]
    ids = units["id"][:]
    ends = units["spike_times_index"][:].astype(np.int64)
    if "obs_intervals" in units:
        raise ValueError("This recording has observation intervals; handle them before replay")
    interval_ids = trials["id"][:10]
    starts, stops = (trials[name][:10] for name in ("start_time", "stop_time"))
    if (len(ids) < 2 or len(np.unique(ids)) != len(ids) or len(ends) != len(ids)
            or np.any(np.diff(ends) < 0) or ends[-1] != len(units["spike_times"])):
        raise ValueError("Invalid recording unit table")
    if (not np.array_equal(interval_ids, np.arange(10)) or not np.all(np.isfinite(starts))
            or not np.all(np.isfinite(stops)) or np.any(starts >= stops)
            or np.any(starts[1:] < stops[:-1])):
        raise ValueError("Unexpected source trial table")
    # Read only this field. It is a concatenation of independent, sorted local-unit streams.
    # Vectorized contiguous I/O avoids hundreds of remote binary-search range probes.
    all_times = units["spike_times"][:]
    by_unit = np.split(all_times, ends[:-1])
    if any(not np.all(np.isfinite(t)) or np.any(np.diff(t) < 0) for t in by_unit):
        raise ValueError("Missing or unordered timestamp")
    destination.mkdir(parents=True, exist_ok=True)
    for i, start, stop in zip(interval_ids, starts, stops, strict=True):
        blocks = [t[t.searchsorted(start, "right"):t.searchsorted(stop, "left")] for t in by_unit]
        np.savez_compressed(destination / f"trial-{i:03d}.npz", trial_id=i, start_s=start,
                            stop_s=stop, unit_id=ids, spike_time_s=np.concatenate(blocks),
                            spike_end=np.cumsum([len(b) for b in blocks]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nwb", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    with args.nwb.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != SHA256:
            raise ValueError("The provided ER1 NWB does not match the released source")
    with h5py.File(args.nwb, "r") as nwb:
        extract(nwb, args.destination)
