"""Trial-local source fields for right-plate measurements in the C2 release."""
import numpy as np


MUSCLES = ("R_tibialis_anterior", "R_soleus", "R_gastrocnemius_medialis",
           "R_vastus_medialis", "R_rectus_femoris", "R_semitendinosus",
           "R_gluteus_maximus", "R_gluteus_medius")


def right_strike1_index(recording):
    events = recording["parameters"]["EVENT"]
    paired = zip(events["CONTEXTS"]["value"], events["LABELS"]["value"])
    indexes = [i for i, pair in enumerate(paired) if pair == ("Right", "Foot Strike1")]
    if len(indexes) != 1:
        raise ValueError("Exactly one Right Foot Strike1 annotation is required")
    stamp = events["TIMES"]["value"][:, indexes[0]]
    seconds = 60.0 * stamp[0] + stamp[1]
    rate = recording["header"]["points"]["frame_rate"]
    if rate != 100 or recording["header"]["points"]["first_frame"] != 0 or not np.isfinite(seconds):
        raise ValueError("Unexpected export clock or invalid event time")
    index = int(np.rint(seconds * rate))
    if not 0 <= index < recording["data"]["points"].shape[2]:
        raise ValueError("Right strike outside the recording")
    return index


def point_on_platform(xy, corners):
    """Inclusive convex polygon test in lab mm. CORNERS is the 3-by-4 C3D array."""
    polygon = np.asarray(corners, dtype=float).T
    xy = np.asarray(xy, dtype=float)
    if polygon.shape != (4, 3) or xy.shape != (2,) or not np.isfinite(polygon).all():
        raise ValueError("Invalid projected plate geometry")
    if np.ptp(polygon[:, 2]) > 0.1:
        raise ValueError("Expected a horizontal laboratory platform")
    if not np.isfinite(xy).all():
        return False
    vertices = polygon[:, :2]
    edges = np.roll(vertices, -1, axis=0) - vertices
    if np.any(np.linalg.norm(edges, axis=1) == 0):
        raise ValueError("Invalid repeated plate corner")
    turns = edges[:, 0] * np.roll(edges[:, 1], -1) - edges[:, 1] * np.roll(edges[:, 0], -1)
    if not (np.all(turns > 0) or np.all(turns < 0)):
        raise ValueError("Plate corners must bound a convex polygon")
    rel = xy - vertices
    sides = edges[:, 0] * rel[:, 1] - edges[:, 1] * rel[:, 0]
    return bool(np.all(sides >= 0) or np.all(sides <= 0))


def right_contact_geometry(recording, plate_number):
    if plate_number not in (1, 2):
        raise ValueError("A source-assigned plate number is required")
    index = right_strike1_index(recording)
    params, data = recording["parameters"], recording["data"]
    names = params["POINT"]["LABELS"]["value"]
    corners = params["FORCE_PLATFORM"]["CORNERS"]["value"][:, :, plate_number - 1]
    marker_valid = {}
    marker_inside = {}
    for label in ("R_FCC", "R_FM2"):
        if names.count(label) != 1:
            raise ValueError(f"Missing or duplicated marker {label}")
        column = names.index(label)
        xyz = data["points"][:3, column, index]
        residual = data["meta_points"]["residuals"][0, column, index]
        marker_valid[label] = bool(np.isfinite(xyz).all() and np.isfinite(residual) and residual >= 0)
        marker_inside[label] = marker_valid[label] and point_on_platform(xyz[:2], corners)
    return {"point_index": index, "marker_valid": marker_valid,
            "marker_inside": marker_inside, "both_on_plate": all(marker_inside.values())}


def right_emg_slice(recording, first_analog_sample, stop_analog_sample):
    """Return (samples × 8, valid samples × 8). Slice endpoints follow Python indexing."""
    params = recording["parameters"]["ANALOG"]
    labels, units = params["LABELS"]["value"], params["UNITS"]["value"]
    data = recording["data"]["analogs"][0]
    if not 0 <= first_analog_sample < stop_analog_sample <= data.shape[1]:
        raise ValueError("Invalid analog slice")
    result = np.full((stop_analog_sample - first_analog_sample, len(MUSCLES)), np.nan)
    for j, label in enumerate(MUSCLES):
        if label not in labels:
            continue
        channel = labels.index(label)
        if labels.count(label) != 1 or units[channel] != "V":
            raise ValueError("Invalid electrical channel identity or unit")
        result[:, j] = data[channel, first_analog_sample:stop_analog_sample]
    return result, np.isfinite(result)
