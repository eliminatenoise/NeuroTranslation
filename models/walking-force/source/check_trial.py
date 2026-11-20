"""Compare two independent C3D readers on an explicitly chosen, staged trial."""
import argparse
import json
from pathlib import Path

import c3d
import ezc3d
import numpy as np


def compare_arrays(a, b):
    if a.shape != b.shape or not np.array_equal(np.isfinite(a), np.isfinite(b)):
        raise ValueError("Readers differ on shape or finite-sample mask")
    valid = np.isfinite(a)
    error = float(np.max(np.abs(a[valid] - b[valid]))) if valid.any() else None
    if error is not None and error > 1e-7:
        raise ValueError("Readers differ on decoded values")
    return error


def inspect_trial(path):
    trial = ezc3d.c3d(str(path), extract_forceplat_data=True)
    data, params = trial["data"], trial["parameters"]
    names = params["ANALOG"]["LABELS"]["value"]
    units = params["ANALOG"]["UNITS"]["value"]
    point_units = params["POINT"]["UNITS"]["value"]
    if point_units != ["mm"] or params["FORCE_PLATFORM"]["TYPE"]["value"].ravel().tolist() != [2, 2]:
        raise ValueError("Expected marker coordinates in mm and two type-2 force plates")
    with path.open("rb") as handle:
        reader = c3d.Reader(handle)
        analogs, markers, residuals = [], [], []
        for _, points, analog in reader.read_frames(check_nan=False):
            markers.append(points[:, :3])
            residuals.append(points[:, 3])
            analogs.append(analog.T)
        rates = (reader.point_rate, reader.analog_rate, reader.analog_per_frame)
        extent = [int(reader.first_frame), int(reader.last_frame)]
    if not rates == (100, 1500, 15):
        raise ValueError("Expected a 15:1 analog-to-point rate")
    xyz = data["points"][:3].transpose(2, 1, 0)
    decoded = data["analogs"][0].T
    residual = data["meta_points"]["residuals"][0].T
    if decoded.shape[0] != xyz.shape[0] * rates[2]:
        raise ValueError("Analog extent does not match the marker frame count")
    errors = {"markers_mm": compare_arrays(np.stack(markers), xyz),
              "analog_native_units": compare_arrays(np.vstack(analogs), decoded),
              "point_residual_mm": compare_arrays(np.stack(residuals), residual)}
    plate_rows = []
    for index, platform in enumerate(data["platform"], 1):
        label = f"Fz{index}"
        column = names.index(label)
        if units[column] != "N" or platform["unit_force"] != "N":
            raise ValueError("Plate channel must be expressed in N")
        corners = platform["corners"].T
        axis_x = corners[0] - corners[1]
        axis_y = corners[0] - corners[3]
        normal = np.cross(axis_x, axis_y)
        normal /= np.linalg.norm(normal)
        if not np.allclose(normal, [0.,0.,-1.], atol=1e-7):
            raise ValueError("Corner-defined plate normal differs from the verified setup")
        local_z = decoded[:, column]
        lab_up = platform["force"][2]
        err = compare_arrays(lab_up, -local_z)
        positive = lab_up[lab_up > 0]
        plate_rows.append({"plate": index, "corner_xyz_mm": corners.tolist(),
                           "unit": units[column], "local_z_axis_in_lab": normal.tolist(),
                           "error_inertial_z_versus_negated_local_N": err,
                           "zero_samples": int(np.sum(lab_up == 0)),
                           "finite_samples": int(np.isfinite(lab_up).sum()),
                           "positive_samples": int(positive.size),
                           "minimum_positive_N": float(positive.min()) if positive.size else None,
                           "maximum_positive_N": float(positive.max()) if positive.size else None})
    emg = {}
    for col, label in enumerate(names):
        if label.startswith("R_"):
            if units[col] != "V":
                raise ValueError("Unexpected electrical channel unit")
            signal = decoded[:, col]
            emg[label] = {"finite_samples": int(np.isfinite(signal).sum()),
                          "negative_samples": int(np.sum(signal < 0)), "positive_samples": int(np.sum(signal > 0))}
    return {"physical_first_last_frames_in_file": extent,
            "ezc3d_zero_based_first_last": [trial["header"]["points"][key] for key in ("first_frame", "last_frame")],
            "marker_frames": xyz.shape[0], "marker_hz": float(rates[0]), "analog_samples_per_channel": decoded.shape[0],
            "analog_hz": float(rates[1]), "samples_per_marker_frame": int(rates[2]), "point_units": point_units[0],
            "frame_residual_values_mm": np.unique(residual[np.isfinite(residual)]).tolist(),
            "reader_max_abs_differences": errors, "plate_checks": plate_rows, "stored_emg_V": emg}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selected_c3d", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_trial(args.selected_c3d), indent=2, allow_nan=False))
