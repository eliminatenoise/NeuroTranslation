"""Score the frozen Hyser index-finger forecasts on original Random-task WFDB files."""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

from calibration import calibrate
from hyser_index import Rows, TICKS, decode_predictors, force_history, predict_trial

BASE = Path(__file__).resolve().parent
DIGITS = ("thumb", "index", "middle", "ring", "little")
GRIDS = ("ED", "EP", "FD", "FP")
SAMPLES = {"force": (100, 2500, 5), "raw": (2048, 51200, 256)}


def read_signal(session, kind, trial):
    """Validate an original multiplexed format-16 record before scaling its counts."""
    import wfdb

    rate, frames, channels = SAMPLES[kind]
    stem = session / f"random_{kind}_sample{trial}"
    header = wfdb.rdheader(str(stem))
    filename = stem.name + ".dat"
    if (header.record_name != stem.name or header.n_sig != channels
            or header.fs != rate or header.sig_len != frames
            or header.file_name != [filename] * channels
            or header.fmt != ["16"] * channels or header.units != ["V"] * channels
            or any(n != 1 for n in header.samps_per_frame)
            or any(header.skew) or any(header.byte_offset)):
        raise ValueError(f"Unexpected WFDB source layout in {stem.name}.hea.")
    if kind == "force" and tuple(header.sig_name) != DIGITS:
        raise ValueError("Expected the five named Hyser force channels in their original order.")
    if kind == "raw":
        for i, grid in enumerate(GRIDS):
            expected = {f"{grid}-{x}-{y}" for x in range(1, 9) for y in range(1, 9)}
            if set(header.sig_name[64*i:64*(i+1)]) != expected:
                raise ValueError(f"The raw header does not identify the complete {grid} electrode grid.")
    if (session / filename).stat().st_size != frames * channels * 2:
        raise ValueError(f"Data length differs from the header for {filename}.")
    gain = np.asarray(header.adc_gain, dtype=np.float64)
    baseline = np.asarray(header.baseline, dtype=np.float64)
    if (np.any(~np.isfinite(gain)) or np.any(gain <= 0)
            or np.any(~np.isfinite(baseline))):
        raise ValueError(f"Invalid gain or baseline in {stem.name}.hea.")
    original = wfdb.rdrecord(str(stem), physical=False, return_res=16)
    counts = original.d_signal
    if (not np.array_equal(counts[0], header.init_value)
            or not np.array_equal(counts.sum(axis=0, dtype=np.int64) % 65536,
                                  np.asarray(header.checksum) % 65536)):
        raise ValueError(f"Initial sample or checksum mismatch for {filename}.")
    if kind == "force":
        channel = header.sig_name.index("index")
        counts, gain, baseline = counts[:, channel], gain[channel], baseline[channel]
    voltage = (counts.astype(np.float64) - baseline) / gain
    voltage[counts == -32768] = np.nan
    return voltage


def invented_trial(day, trial, with_emg):
    """Generate an illustrative trial locally; these signals are never used for study metrics."""
    phase = np.arange(2500) / 100
    force = 0.08 + 0.04 * np.sin(phase * (1.05 + day/20) + trial/4) + 0.02*np.cos(phase*2.1)
    if not with_emg:
        return force, None
    time = np.arange(51200)[:, None] / 2048
    group = np.arange(4)[None, :]
    wave = (0.0003 + 0.0001*np.sin(time*1.2 + trial/4 + group)) * np.sin(time*413 + group)
    return force, np.repeat(wave, 64, axis=1)


def load_trial(folder, day, trial, with_emg):
    if folder is None:
        return invented_trial(day, trial, with_emg)
    force = read_signal(folder, "force", trial)
    raw = read_signal(folder, "raw", trial) if with_emg else None
    return force, raw


def collect(folder, day, trials, with_emg, weights):
    """Keep only the small scoring vectors after each complete trial."""
    current, targets = [], []
    predictions = {"force": []}
    if with_emg:
        predictions["aligned"] = []
    force_fit = decode_predictors(weights)["force"]
    for number in trials:
        force, raw = load_trial(folder, day, number, with_emg)
        if raw is None:
            x = force_history(force, TICKS)
            rows = Rows(x, x[:, -1], np.empty(0), np.empty(0))
            forecast = {"force": force_fit.predict(rows)}
        else:
            forecast = predict_trial(raw, force, TICKS, weights)
        target = force[TICKS + 12]
        if not np.isfinite(target).all() or not all(np.isfinite(v).all() for v in forecast.values()):
            raise ValueError(f"Trial {number} has missing or nonfinite forecast inputs or targets.")
        current.append(force[TICKS])
        targets.append(target)
        for key, values in forecast.items():
            predictions[key].append(values)
        del raw
    return np.concatenate(current), np.concatenate(targets), {
        key: np.concatenate(v) for key, v in predictions.items()
    }


def session_name(folder):
    match = re.fullmatch(r"(subject\d{2})_session([12])", folder.name)
    if not match or not folder.is_dir():
        raise ValueError("Choose an original folder named subjectNN_session1 or subjectNN_session2.")
    return match[1], int(match[2])


def scores(forecast, truth):
    diff = forecast - truth
    return {"mae_v": float(np.mean(np.abs(diff))), "rmse_v": float(np.sqrt(np.mean(diff*diff)))}


def run(args):
    weights = json.loads((BASE / "predictors.json").read_text(encoding="utf-8"))
    eval_day = 2
    if args.example:
        if args.session or args.calibrate_from:
            raise ValueError("--example generates both sessions locally. Use separate commands for original data.")
    else:
        if not args.session:
            raise ValueError("Provide a session folder or use --example.")
        person, eval_day = session_name(args.session)
        if args.calibrate_from:
            first_person, first_day = session_name(args.calibrate_from)
            if person != first_person or first_day != 1 or eval_day != 2:
                raise ValueError("Calibration requires the same person's original session1 and session2 folders.")
    adapters = {}
    if args.example or args.calibrate_from:
        current, target, pooled = collect(args.calibrate_from, 1, range(1, 6), args.with_emg, weights)
        adapters = {key: calibrate(current, values, target) for key, values in pooled.items()}
    trials = [args.trial] if args.trial is not None else range(1, 6)
    current, target, pooled = collect(args.session, eval_day, trials, args.with_emg, weights)
    results = {}
    for key, values in pooled.items():
        result = {"shared": scores(values, target)}
        if key in adapters:
            result["own_day1"] = scores(adapters[key].predict(current, values), target)
            result["mae_gain_v"] = result["shared"]["mae_v"] - result["own_day1"]["mae_v"]
        results[key] = result
    return {"input": "invented example" if args.example else "original local recording",
            "scoring_day": eval_day, "trials": len(trials), "cutoffs": len(target),
            "day1_calibration_cutoffs": 2250 if adapters else 0, "target": "index sensor voltage at +120 ms",
            "models": results}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", type=Path, help="Original evaluation session folder.")
    parser.add_argument("--calibrate-from", type=Path, metavar="SESSION1", help="First-day folder for the same person.")
    parser.add_argument("--with-emg", action="store_true", help="Also load raw forearm records and score the aligned model.")
    parser.add_argument("--trial", type=int, choices=range(1, 6), help="Score one evaluation trial. Calibration always uses five.")
    parser.add_argument("--example", action="store_true", help="Run two invented sessions without opening a recording.")
    args=parser.parse_args()
    try:
        result=run(args)
    except (OSError, ValueError, TypeError, ImportError) as exc:
        parser.exit(2, f"Could not score the session. {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
