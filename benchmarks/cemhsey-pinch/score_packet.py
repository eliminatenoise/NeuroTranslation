"""Forecast a later CEMHSEY force reading from a local compact trial packet."""
import argparse
import json
import hashlib
from pathlib import Path

import numpy as np

from pinch import ISSUE_TICKS, PACKET_FORMAT, PROTOCOL_PATH, phase_features, predict_rows, sha256, validate_fit


def read_packet(path, fit):
    with path.open("rb") as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("Choose a compact trial packet smaller than 2 MiB.")
    packet = json.loads(data)
    if (not isinstance(packet, dict) or packet.get("format") != PACKET_FORMAT or
            packet.get("protocol_sha256") != sha256(PROTOCOL_PATH) or
            packet.get("timing_mode") not in ("force_only", "nominal_release_index")):
        raise ValueError("The packet does not match this protocol.")
    rows = packet.get("rows")
    if not isinstance(rows, list) or len(rows) != len(ISSUE_TICKS):
        raise ValueError("The packet must contain all 592 issue ticks.")
    paired = packet["timing_mode"] == "nominal_release_index"
    def finite(x):
        return type(x) in (float, int) and np.isfinite(float(x))
    for tick, row in zip(ISSUE_TICKS, rows):
        if (not isinstance(row, dict) or "measured_target" not in row or "emg_summaries" not in row or
                type(row.get("issue_tick")) is not int or
                row["issue_tick"] != tick or not finite(row.get("force_now")) or
                not isinstance(row.get("force_deltas"), list) or len(row["force_deltas"]) != 4 or
                not all(finite(x) for x in row["force_deltas"])):
            raise ValueError(f"Invalid force inputs at tick {tick}.")
        emg = row.get("emg_summaries")
        if (paired and (not isinstance(emg, list) or len(emg) != 4 or not all(finite(x) for x in emg)
                        or not (0 <= emg[0] <= emg[1] and 0 <= emg[2] <= emg[3]))) or (
                not paired and emg is not None):
            raise ValueError(f"Invalid forearm summaries at tick {tick}.")
        if row.get("measured_target") is not None and not finite(row["measured_target"]):
            raise ValueError(f"Invalid later reading at tick {tick}.")
    return rows, paired and "history_phase_paired_emg" in fit["models"]


def forecasts(fit, rows, paired):
    ticks = np.array([row["issue_tick"] for row in rows])
    force = np.array([[row["force_now"], *row["force_deltas"]] for row in rows], dtype=float)
    phase = phase_features(ticks)
    both = np.column_stack((force, phase))
    inputs = {"phase": phase, "history": force, "history_phase": both}
    if paired:
        inputs["history_phase_paired_emg"] = np.column_stack((both, [row["emg_summaries"] for row in rows]))
    return {"persistence": force[:, 0], **{
        name: predict_rows(fit["models"][name], x, force[:, 0]) for name, x in inputs.items()
    }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="Private JSON packet produced by trial_io.py.")
    parser.add_argument("--fit", type=Path, default=Path(__file__).with_name("BUNDLED-FIT.json"),
                        help="Use a local pooled-fit JSON instead of the weights bundled with this reader.")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--issue", type=int, help="Native force tick (60, 70, …, 5970); defaults to 1660.")
    choice.add_argument("--score", action="store_true", help="Compare all forecasts with all 592 later readings.")
    args = parser.parse_args()
    try:
        with args.fit.open("rb") as stream:
            data = stream.read(128 * 1024 + 1)
        if len(data) > 128 * 1024:
            raise ValueError("Choose a compact fitted model under 128 KiB.")
        fit = json.loads(data)
        validate_fit(fit)
        rows, paired = read_packet(args.packet, fit)
        if args.score:
            if any(r.get("measured_target") is None for r in rows):
                raise ValueError("Trial scoring requires all 592 targets.")
            pred = forecasts(fit, rows, paired)
            truth = np.array([r["measured_target"] for r in rows])
            output = {"cutoffs": len(rows), "units": "normalized force", "scores": {}}
            for name, values in pred.items():
                error = values - truth
                output["scores"][name] = {"mae": float(np.abs(error).mean()),
                                          "rmse": float(np.sqrt(np.square(error).mean()))}
        else:
            issue = 1660 if args.issue is None else args.issue
            if issue not in ISSUE_TICKS:
                raise ValueError("Use force ticks from 60 to 5970 at intervals of 10.")
            predictions = forecasts(fit, [rows[(issue - 60) // 10]], paired)
            output = {"issue_tick": issue, "target_tick": issue + 24,
                      "units": "normalized force",
                      "forecasts": {name: float(value[0]) for name, value in predictions.items()}}
        origin = "locally supplied model"
        if args.fit.resolve() == Path(__file__).with_name("BUNDLED-FIT.json").resolve():
            metadata = json.loads(Path(__file__).with_name("BUNDLED-MODEL-INFO.json").read_bytes())
            if hashlib.sha256(data).hexdigest() != metadata.get("sha256"):
                raise ValueError("The bundled fit differs from its model description.")
            origin = metadata["description"]
        output["model_source"] = origin
        content = json.dumps(output, indent=2, allow_nan=False)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, ImportError) as exc:
        parser.exit(2, f"Could not use this trial. {exc}\n")
    print(content)


if __name__ == "__main__":
    main()
