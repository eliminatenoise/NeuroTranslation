"""Convert one right-hand trial from the original HYGRIP HDF5 release into a local JSON replay."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
import re

import h5py
import numpy as np

ARCHIVE_SHA256 = "6819a18b13599c13a75ca5d36e65d7b6859534f548dbb2e626d31649cd990e88"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def hard_child(parent, name):
    require(isinstance(parent.get(name, getlink=True), h5py.HardLink),
            f"Expected a stored HDF5 object for {name}.")
    return parent[name]


def markers(dataset, rate, channels):
    require(isinstance(dataset, h5py.Dataset) and not dataset.is_virtual and not dataset.external
            and dataset.ndim == 2 and dataset.shape[0] == channels and dataset.dtype == np.dtype("<f8"),
            "The requested signal differs from the source layout.")
    entries = dataset.attrs["events"]
    require(entries.ndim == 2 and entries.shape[1] == 2 and len(entries) >= 5
            and np.isfinite(entries).all(), "Invalid event table.")
    times = [Fraction(float(value)) for value in entries[:, 0]]
    labels = entries[:, 1]
    require(np.isin(labels, [-1, 0, 1]).all()
            and np.flatnonzero(labels == -1).tolist() == [0, len(labels) - 2, len(labels) - 1]
            and all(a < b for a, b in zip(times, times[1:]))
            and all(0 <= t * rate < dataset.shape[1] for t in times[1:-2]),
            "The task markers do not match the source protocol.")
    return times, labels


def clipped_span(dataset, start, stop, lower, upper):
    begin = max(0, start, lower)
    end = min(dataset.shape[1], stop, upper)
    require(begin < end, "The trial has no signal inside the checked task bounds.")
    data = dataset[:, begin:end]
    require(np.isfinite(data).all(), "The selected signal contains missing samples.")
    return begin, data.tolist()


def convert(source, participant, ordinal):
    require(re.fullmatch(r"[A-Z]", participant) is not None and ordinal >= 1,
            "Use a single participant group letter and a positive right-hand trial number.")
    group = hard_child(source, participant)
    require(isinstance(group, h5py.Group), "Participant group is absent.")
    force, eeg = hard_child(group, "frc"), hard_child(group, "eeg")
    require(source.attrs["frc_sfreq"] == 50 and source.attrs["eeg_sfreq"] == 1000
            and decode(source.attrs["frc_units"]) == "volts"
            and decode(source.attrs["eeg_units"]) == "milivolts",
            "Unexpected device sampling rate or unit.")
    names = [decode(name) for name in source.attrs["scalp_chan_name"]]
    require(len(set(names)) == len(names) == 24, "Unexpected scalp channel dictionary.")
    ft, fl = markers(force, 50, 1)
    et, el = markers(eeg, 1000, 24)
    require(np.array_equal(fl, el), "Force and scalp marker labels disagree.")
    offsets = [b - a for a, b in zip(ft[1:-2], et[1:-2])]
    require(all(abs(b-a) <= Fraction(1, 25) for a, b in zip(offsets, offsets[1:])),
            "This run exceeds the 40 ms inter-Go clock limit.")
    right = np.flatnonzero(fl == 1)
    require(ordinal <= len(right), "The requested right-hand trial is outside this recording.")
    pos = int(right[ordinal - 1])
    fg, eg = ft[pos], et[pos]
    first = floor(50 * fg + Fraction(1, 2)) + 20
    last = first + 5 * 204
    fstop = min(force.shape[1], ceil(50*min(ft[pos + 1], fg + 21)))
    f0, voltage = clipped_span(force, first - 19, last + 2, ceil(50*fg), fstop)
    if last + 6 < fstop:
        # No forecast uses the four samples between the last two target ticks.
        final = float(force[0, last + 6])
        require(np.isfinite(final), "The final target is missing.")
        voltage[0].extend([None] * (last + 6 - f0 - len(voltage[0])))
        voltage[0].append(final)
    # A prior task may occupy the first 21 seconds after its own Go. Only the
    # subsequent rest can contribute to the current trial's earliest EEG history.
    rest = et[pos - 1] if pos == 1 else et[pos - 1] + 21
    eeg_shift = floor(1000*(eg - fg - Fraction(1, 50)))
    e0, scalp = clipped_span(eeg, first*20 + eeg_shift - 399, last*20 + eeg_shift + 1,
                             ceil(1000*rest), ceil(1000*min(et[pos + 1], eg + 21)))
    return {"format": "hygrip-right-trial-v1", "forceGoSeconds": float(fg),
            "forceStartIndex": f0, "forceV": voltage[0], "eeg": {
                "goSeconds": float(eg), "startIndex": e0, "channelNames": names, "mV": scalp}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--participant", required=True, help="A single group letter in your source archive.")
    parser.add_argument("--right-trial", required=True, type=int, help="One-based chronological right-hand trial.")
    parser.add_argument("--output", required=True, type=Path, help="New private JSON file. Existing files are preserved.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose an unused output filename.")
    try:
        with args.archive.open("rb") as stream:
            h = sha256()
            for block in iter(lambda: stream.read(4 << 20), b""):
                h.update(block)
            require(h.hexdigest() == ARCHIVE_SHA256, "Supply the unchanged original hygrip.h5 release.")
            stream.seek(0)
            with h5py.File(stream, "r") as source:
                data = convert(source, args.participant, args.right_trial)
        # Serialize before creating the file. Do not include any participant label in the JSON.
        encoded = json.dumps(data, allow_nan=False, separators=(",", ":"))
        import os
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write(encoded)
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Could not convert this trial. {exc}\n")
    print(f"Saved one local trial to {args.output}")


if __name__ == "__main__":
    main()
