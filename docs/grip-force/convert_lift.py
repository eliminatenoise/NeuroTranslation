"""Make one WAY-EEG-GAL recorded lift available for private, offline browser replay."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
from scipy.io import loadmat


EEG = "Fp1 Fp2 F7 F3 Fz F4 F8 FC5 FC1 FC2 FC6 T7 C3 Cz C4 T8 TP9 CP5 CP1 CP2 CP6 TP10 P7 P3 Pz P4 P8 PO9 O1 Oz O2 PO10".split()
EMG = ["Anterior Deltoid", "Brachoradial", "Flexor Digitorum", "Common Extensor Digitorum", "First Dorsal Interosseus"]
ISSUES = np.arange(120, 681, 20)
TRACKER_COLUMNS = np.array([[18 + j, 22 + j, 26 + j] for j in range(4)])


def require(test, message):
    if not test:
        raise ValueError(message)


def source_clock(values, hz):
    times = np.asarray(values, dtype=np.float64)
    require(times.ndim == 1 and times.size > 1 and np.isfinite(times).all()
            and np.allclose(np.diff(times), 1 / hz, rtol=0, atol=1e-8),
            f"Expected a complete {hz} Hz source clock.")
    return times


def checked_names(names):
    require(list(names["eeg"]) == EEG and list(names["emg"]) == EMG,
            "EEG or EMG channels differ from the released model order.")
    kin = list(names["kin"])
    require(len(kin) == 45 and kin[36:42] == ["IndLF", "ThuLF", "LF", "IndGF", "ThuGF", "GF"],
            "Expected the WAY grip and load force columns.")
    for j, columns in enumerate(TRACKER_COLUMNS, 1):
        require([kin[c] for c in columns] == [f"P{axis}{j} - position {axis} sensor {j}" for axis in "xyz"],
                "Motion tracker or axis order differs from the released study.")


def schedule(windows):
    # Block design is known before a lift. These stored condition names only verify the block.
    masses = {str(t["weight_id"]).strip().lower().replace(" ", "") for t in windows}
    surfaces = {str(t["surf_id"]).strip().lower() for t in windows}
    if len(windows) == 28 and masses == {"165g", "330g"} and surfaces == {"sandpaper", "silk"}:
        return "mixed"
    if len(windows) == 34 and masses == {"330g"} and surfaces == {"sandpaper", "suede", "silk"}:
        return "friction"
    if len(windows) == 34 and masses == {"165g", "330g", "660g"} and surfaces == {"sandpaper"}:
        return "weight"
    raise ValueError("Unknown WAY series schedule.")


def make_clip(ws, ordinal):
    checked_names(ws["names"])
    windows = ws["win"]
    require(1 <= ordinal <= len(windows), f"Trial number must be between 1 and {len(windows)}.")
    kind = schedule(windows)
    sample = windows[ordinal - 1]
    time = source_clock(sample["eeg_t"], 500)
    muscle_time = source_clock(sample["emg_t"], 4000)
    eeg, kin, emg = (np.asarray(sample[key]) for key in ("eeg", "kin", "emg"))
    require(eeg.shape == (len(time), 32) and kin.shape == (len(time), 45) and emg.shape == (len(muscle_time), 5),
            "Sensor rows do not match their clocks or channel counts.")
    led = float(sample["LEDon"])
    cue = int(np.argmin(np.abs(time - led)))
    require(np.isfinite(led) and abs(time[cue] - led) <= .001 + 1e-10, "Missing or off-grid go cue.")
    issue = cue + ISSUES
    targets = issue + 60
    require(issue[0] >= 199 and targets[-1] < len(time), "The trial must cover all 29 histories and later forces.")
    emg_ends = np.searchsorted(muscle_time, time[issue] + 1e-10, side="right") - 1
    require(emg_ends[0] >= 1599, "Insufficient EMG history.")
    slack = time[issue] - muscle_time[emg_ends]
    require(np.all(slack >= -1e-10) and np.all(slack < .00025 + 1e-10), "The EMG clock misses a cutoff.")
    history = slice(issue[0] - 199, issue[-1] + 1)
    m = slice(emg_ends[0] - 1599, emg_ends[-1] + 1)
    require(np.allclose(time[history] - time[cue], np.arange(-79, 681) / 500, rtol=0, atol=1e-8)
            and np.allclose(time[targets] - time[cue], (ISSUES+60) / 500, rtol=0, atol=1e-8),
            "Source alignment differs from the model's cue-relative clock.")
    # Keep later labels separate. No future force, pose or voltage enters a history window.
    arrays = {"main_s": time[history] - time[cue], "emg_s": muscle_time[m] - time[cue],
              "grip_n": -kin[history, 41], "load_n": kin[history, 38],
              "position": kin[history][:, TRACKER_COLUMNS], "eeg": eeg[history], "emg": emg[m],
              "later_grip_n": -kin[targets, 41], "later_time_s": time[targets] - time[cue]}
    require(all(np.isfinite(a).all() for a in arrays.values()), "A required signal or reference value is missing.")
    return {"format": "way-grip-trial-v1", "series_type": kind, "trial_number": ordinal,
            **{name: a.tolist() for name, a in arrays.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="An extracted windowed-series MATLAB file (WS_*.mat).")
    parser.add_argument("--trial", required=True, type=int, help="One-based trial number within this series.")
    parser.add_argument("--out", required=True, type=Path, help="New local JSON file to open in the forecast browser.")
    args = parser.parse_args()
    with args.source.open("rb") as source:
        require(source.read(20).startswith(b"MATLAB 5.0 MAT-file"), "Use an extracted WAY windowed-series MATLAB v5 file.")
        source.seek(0)
        contents = loadmat(source, variable_names=["ws"], simplify_cells=True)
    require("ws" in contents, "This MAT file has no win-series (ws) record.")
    clip = make_clip(contents["ws"], args.trial)
    data = json.dumps(clip, separators=(",", ":"), allow_nan=False).encode("utf-8")
    # Reserve this new path exclusively and leave existing recordings untouched.
    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(data)
    except BaseException:
        args.out.unlink(missing_ok=True)
        raise
    print(f"Wrote one local lift with 29 cutoffs to {args.out}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        raise SystemExit(str(error)) from error
