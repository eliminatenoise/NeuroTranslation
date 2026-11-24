"""Predict the two archived hand coordinates 100 milliseconds ahead."""

import argparse
from hashlib import file_digest
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort


HERE = Path(__file__).resolve().parent
ARCHIVE_SHA256 = "3852799f85f662f1cacadb0d758ba8fa0dc6cca318f46c9b131978adf1baffb6"


def features(counts, available, rows):
    count = np.asarray(counts, dtype=np.float64)
    seen = np.asarray(available)
    mapping = np.asarray(rows, dtype=np.int64)
    if (mapping.ndim != 1 or not len(mapping) or count.shape != (10, len(mapping)) or
            seen.shape != count.shape or seen.dtype != bool or not np.isfinite(count).all() or
            np.any(count < 0) or np.any(count != np.floor(count)) or np.any(count[~seen]) or
            np.any((mapping < 0) | (mapping >= 192)) or not np.array_equal(rows, mapping)):
        raise ValueError("Supply ten bins of counts and Boolean observation flags per recorded unit.")
    x = np.zeros((1, 10, 384), dtype=np.float32)
    roots = np.sqrt(count)
    for row in np.unique(mapping):
        units = mapping == row
        n = seen[:, units].sum(axis=-1)
        x[0, :, row] = roots[:, units].sum(axis=-1) / np.maximum(n, 1)
        x[0, :, 192 + row] = n > 0
    return x


def generated_example():
    rows = np.r_[np.arange(0, 96, 2), np.arange(96, 192, 3)]
    ticks = np.arange(10)[:, None]
    counts = np.asarray((ticks + rows) % 4 > 1, dtype=np.int64)
    available = np.ones_like(counts, dtype=bool)
    return features(counts, available, rows)


def archive_input(filename, issue_ms):
    from pynwb import NWBHDF5IO

    with filename.open("rb") as stream:
        if file_digest(stream, "sha256").hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Use the exact MC Maze Medium behavior and ecephys archive linked in the guide.")
    with NWBHDF5IO(filename, "r", load_namespaces=True) as archive:
        file = archive.read()
        starts = np.rint(file.trials["start_time"].data[:] * 1000).astype(np.int64)
        stops = np.rint(file.trials["stop_time"].data[:] * 1000).astype(np.int64)
        possible = (issue_ms - 200 >= starts) & (issue_ms < stops)
        if int(possible.sum()) != 1:
            raise ValueError("Choose a timestamp with a full 200 ms history inside one archived trial.")
        units = file.units
        electrode = units["electrodes"]
        references = np.asarray(electrode.target.data[:], dtype=np.int64)
        one_each = np.diff(np.r_[0, np.asarray(electrode.data[:])])
        digits = np.asarray([str(value)[0] for value in units.id.data[:]])
        if (not np.all(one_each == 1) or not np.all((references >= 0) & (references < 96)) or
                set(digits) != {"1", "2"}):
            raise ValueError("Unexpected archive electrode assignments.")
        rows = references + 96 * (digits == "2")
        actual = np.asarray(file.electrodes["location"].data[:]).astype(str)
        if not np.array_equal(actual[rows], np.where(digits == "2", "M1", "PMd")):
            raise ValueError("Corrected electrode rows disagree with their recorded regions.")
        edges = (issue_ms - np.arange(200, -1, -20)) / 1000.
        start, stop = edges[:-1], edges[1:]
        counts = np.zeros((10, len(units)), dtype=np.int64)
        available = np.zeros_like(counts, dtype=bool)
        for index in range(len(units)):
            spikes = np.asarray(units["spike_times"][index])
            intervals = np.asarray(units["obs_intervals"][index])
            selected = np.searchsorted(intervals[:, 0], start, side="right") - 1
            visible = (selected >= 0) & (intervals[np.maximum(selected, 0), 1] >= stop)
            counts[:, index] = np.where(visible, np.searchsorted(spikes, stop) - np.searchsorted(spikes, start), 0)
            available[:, index] = visible
    return features(counts, available, rows)


def predict(window):
    settings = ort.SessionOptions()
    settings.intra_op_num_threads = settings.inter_op_num_threads = 1
    runtime = ort.InferenceSession(str(HERE / "model.onnx"), sess_options=settings,
                                   providers=["CPUExecutionProvider"])
    values = runtime.run(["positions_100mm"], {"history": window})[0]
    result = values[0].astype(np.float64) * 100.
    if result.shape != (2,) or not np.isfinite(result).all():
        raise ValueError("The model did not return two finite coordinates.")
    return result.tolist()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="JSON window with counts, available, and corrected_electrode_rows")
    source.add_argument("--archive", type=Path, help="the exact public MC Maze Medium behavior NWB file")
    p.add_argument("--issue-ms", type=int, help="archive timestamp in milliseconds")
    args = p.parse_args()
    if (args.archive is None) != (args.issue_ms is None):
        p.error("--archive and --issue-ms go together")
    if args.archive:
        window = archive_input(args.archive, args.issue_ms)
        label = "recorded cortical spikes"
    elif args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        window = features(data["counts"], data["available"], data["corrected_electrode_rows"])
        label = "supplied spike bins"
    else:
        window = generated_example()
        label = "generated spike bins"
    x, y = predict(window)
    print(json.dumps({"input": label, "forecast_ahead_ms": 100, "x_mm": x, "y_mm": y}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
