"""Extract consecutive native observations and identify strictly past donors."""

import io

import numpy as np

PERIOD = .01
TOL = 1e-7  # Seconds; far below a single 10 ms sample.
CUTOFFS = (200, 600, 1000, 1400, 1800, 2200, 2600)
HEADER = (
    "time[s];acc_x[m/s^2];acc_y[m/s^2];acc_z[m/s^2];"
    "acc_free_x[m/s^2];acc_free_y[m/s^2];acc_free_z[m/s^2];"
    "gyroscope_x[rad/s];gyroscope_y[rad/s];gyroscope_z[rad/s];"
    "magnetometer_x[au];magnetometer_y[au];magnetometer_z[au];"
    "quaternion_w;quaternion_x;quaternion_y;quaternion_z"
)
GALLERY_COLUMNS = ["time_s", "acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z",
                   "q_w", "q_x", "q_y", "q_z"]


def read_record(raw):
    with io.BytesIO(raw) as file:
        if file.readline().decode("ascii").strip() != HEADER:
            raise ValueError("Unrecognized measurement schema")
        # Empty numeric cells are unavailable. Malformed row width raises.
        return np.genfromtxt(file, delimiter=";", dtype=np.float64, ndmin=2, comments=None)


def measured_windows(data):
    if data.size == 0 or data.shape[1] != 17:
        raise ValueError("Missing native measurement rows or wrong source column count")
    relative = data[:, 0] - data[0, 0]
    finite_time = np.isfinite(relative)
    clock_order_ok = np.isfinite(relative[0]) and np.all(np.diff(relative[finite_time]) > 0)
    sensors = data[:, [7, 8, 9, 1, 2, 3]]
    valid, rejected = {}, {}
    for cutoff in CUTOFFS:
        start = cutoff / 1000 - 20 * PERIOD
        expected = start + np.arange(30) * PERIOD
        if not clock_order_ok:
            rejected[cutoff] = "ambiguous_time_origin_or_order"
            continue
        candidates = np.flatnonzero(finite_time & (np.abs(relative - start) <= TOL))
        if len(candidates) != 1:
            rejected[cutoff] = "missing_or_ambiguous_history_start"
            continue
        first = int(candidates[0])
        timestamps = relative[first:first + 30]
        if len(timestamps) < 30:
            rejected[cutoff] = "record_ends_before_last_outcome"
            continue
        if not np.all(np.abs(timestamps - expected) <= TOL) or not np.all(
            np.abs(np.diff(timestamps) - PERIOD) <= TOL
        ):
            rejected[cutoff] = "gap_or_off_grid_time"
            continue
        window = sensors[first:first + 30]
        if not np.isfinite(window[:20]).all():
            rejected[cutoff] = "nonfinite_sensor_history"
            continue
        if not np.isfinite(window[20:]).all():
            rejected[cutoff] = "nonfinite_sensor_outcome"
            continue
        valid[cutoff] = (timestamps[:20], window[:20, :3], window[:20, 3:],
                         window[20:, :3].mean(axis=0), window[20:, 3:].mean(axis=0))
    return relative, valid, rejected


def donor_rows(people, hands, targets, trials, cutoffs):
    latest, donors = {}, []
    for i, (p, h, t, r, c) in enumerate(zip(people, hands, targets, trials, cutoffs, strict=True)):
        key = p, h, t, c
        prior = latest.get(key)
        if prior is not None and trials[prior] >= r:
            raise ValueError("Recipient and donor must be in increasing native original order")
        donors.append(-1 if prior is None else prior)
        latest[key] = i
    return np.asarray(donors, dtype=np.int32)
