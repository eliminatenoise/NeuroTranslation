"""Freeze tasks and physical ranges without accessing participant joint values."""
from pathlib import Path
import argparse
import hashlib
import json

import h5py
import numpy as np

COMMAND = [0.824322, 0.790062, 0.779997, 0.8, 0.779997,
           0.815649, 0.806884, 0.830053, 0.809816, 0.772362]
HERE = Path(__file__).resolve().parent

def select(archive):
    rows = []
    with h5py.File(archive) as source:
        assert sorted(source["Streaming"]) == [f"AB{i:02}" for i in range(1, 11)]
        for i, cmd in enumerate(COMMAND, 1):
            person = f"AB{i:02}"
            trial_path = f"Streaming/{person}/Tread/i0"
            trial = source[trial_path]
            events = trial["events"]
            labels = ["".join(map(chr, source[r][...].ravel()))
                      for r in events["tasks"][...].ravel()]
            assert labels.count("s0x8") == 1
            bounds = events["cutPoints"][:, labels.index("s0x8")]
            assert np.isfinite(bounds).all() and np.all(bounds == bounds.astype(int))
            first, last = map(int, bounds)
            # Interior common to both plausible frame-index conventions.
            lo, hi = first + 1, last - 1
            angle_names = [side + joint + "Angles" for joint in ("Knee", "Hip", "Ankle")
                           for side in ("R", "L")]
            shapes = [trial["jointAngles"][name].shape for name in angle_names]
            assert all(shape == shapes[0] for shape in shapes) and shapes[0][0] == 3
            assert 0 <= lo < hi <= shapes[0][1]
            cvel = events.get("VelProf/cvel")
            verified = cvel is not None
            if verified:
                cmd_stream = cvel[lo:hi, 0]
                assert len(cmd_stream) == hi-lo and (cmd_stream == 0.8).all()
            else:
                assert person == 'AB10'
            rows.append(dict(person=person, trial_path=trial_path, angle_names=angle_names,
                             full_trial_samples=shapes[0][1], task_label=labels[labels.index("s0x8")],
                             native_event_bounds=[first, last], zero_based_half_open=[lo, hi],
                             normalized_command_stream_verified=verified,
                             README_leg_length_adjusted_command_mps=cmd))
    return rows

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    rows = select(args.archive)
    with args.receipt.open("x") as out:
        json.dump(rows,out,indent=2)
        out.write("\n")
