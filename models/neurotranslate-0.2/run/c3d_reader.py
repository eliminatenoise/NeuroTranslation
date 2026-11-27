"""C3D reading for P2 (markers, analog channels, events and force platforms) on one clock.

Uses the pure-Python `c3d` package (0.6.0) for the binary layout; this module adds:
  - points as float64 [frames, points, 3] with invalid samples (residual -1) set to NaN, and a
    count of samples flagged as modelled (residual 0: filtered or gap-filled by the authors);
  - analog channels with ANALOG:SCALE, GEN_SCALE and OFFSET applied, as [frames * per_frame, ch];
  - force platform forces (types 2, 3 and 4) converted with CAL_MATRIX where given, baseline-zeroed
    over FORCE_PLATFORM:ZERO when that range is inside the file, and rotated into the laboratory
    frame from CORNERS. Steps that end before the end of the zero range are masked by the caller
    (zeroing uses those frames).
Time origin: the first stored frame. Point frame i is at i / point_rate; analog sample j at
j / analog_rate (the first analog sample of frame i is sample i * per_frame), so both share a clock.
"""
import io

import numpy as np

try:
    import c3d as _c3d
except ImportError:  # pragma: no cover
    _c3d = None


def _param(r, name):
    try:
        return r.get(name)
    except Exception:
        return None


def _strings(r, name):
    p = _param(r, name)
    if p is None:
        return []
    try:
        return [s.strip() for s in p.string_array.ravel().tolist()]
    except Exception:
        try:
            return [p.string_value.strip()]
        except Exception:
            return []


def _ints(r, name):
    p = _param(r, name)
    if p is None:
        return None
    if not p.dimensions:
        return np.array([p.int16_value])
    if p.num_elements == 0:
        return None
    return np.array(p.int16_array)


def _floats(r, name):
    p = _param(r, name)
    if p is None:
        return None
    if not p.dimensions:
        return np.array([p.float_value])
    if p.num_elements == 0:
        return None
    return np.array(p.float_array)


def read_c3d(data):
    if isinstance(data, (bytes, bytearray)):
        fh = io.BytesIO(data)
    else:
        fh = open(data, "rb")
    try:
        r = _c3d.Reader(fh)
        labels = [s.strip() for s in r.point_labels]
        alabels = [s.strip() for s in r.analog_labels]
        pr = float(r.point_rate)
        ar = float(r.analog_rate) if r.analog_used else 0.0
        apf = int(r.analog_per_frame) if r.analog_used else 0
        pts, ana = [], []
        for _, p, a in r.read_frames(copy=True):
            pts.append(p)
            if r.analog_used:
                ana.append(np.asarray(a, np.float64).T)
        P = np.stack(pts) if pts else np.zeros((0, len(labels), 5), np.float32)
        xyz = P[:, :, :3].astype(np.float64)
        invalid = P[:, :, 3] < 0
        xyz[invalid] = np.nan
        modelled = (P[:, :, 3] == 0) & ~invalid
        A = np.concatenate(ana, axis=0) if ana else np.zeros((0, len(alabels)))
        out = {
            "point_labels": labels, "point_rate": pr, "points": xyz,
            "point_invalid": invalid, "point_modelled": modelled,
            "point_units": (_strings(r, "POINT:UNITS") or [""])[0],
            "analog_labels": alabels, "analog_rate": ar, "analog_per_frame": apf, "analog": A,
            "analog_units": _strings(r, "ANALOG:UNITS"),
            "analog_descriptions": _strings(r, "ANALOG:DESCRIPTIONS"),
            "first_frame": int(r.first_frame), "frames": int(P.shape[0]),
            "events": _events(r),
            "force_platforms": _platforms(r, A, apf),
        }
        return out
    finally:
        fh.close()


def _events(r):
    labels = _strings(r, "EVENT:LABELS")
    ctx = _strings(r, "EVENT:CONTEXTS")
    p = _param(r, "EVENT:TIMES")
    if p is not None and not p.dimensions:
        p = None
    used = _ints(r, "EVENT:USED")
    n = int(used.ravel()[0]) if used is not None and used.size else len(labels)
    times = []
    if p is not None and p.num_elements:
        t = np.array(p.float_array).reshape(-1, 2) if np.array(p.float_array).ndim == 1 else np.array(p.float_array)
        if t.shape[-1] == 2:
            times = (t[:, 0] * 60.0 + t[:, 1]).tolist()
    ev = []
    for i in range(min(n, len(labels))):
        ev.append({"label": labels[i], "context": ctx[i] if i < len(ctx) else "",
                   "time_s": times[i] if i < len(times) else None})
    return ev


def _platforms(r, A, apf):
    used = _ints(r, "FORCE_PLATFORM:USED")
    if used is None or int(used.ravel()[0]) == 0 or A.shape[0] == 0:
        return []
    n = int(used.ravel()[0])
    types = _ints(r, "FORCE_PLATFORM:TYPE").ravel()[:n]
    chan_p = _param(r, "FORCE_PLATFORM:CHANNEL")
    ch = np.array(chan_p.int16_array)
    if ch.ndim == 1:
        ch = ch.reshape(n, -1)
    cal = _floats(r, "FORCE_PLATFORM:CAL_MATRIX")
    zero = _ints(r, "FORCE_PLATFORM:ZERO")
    corners = _floats(r, "FORCE_PLATFORM:CORNERS")
    if corners is not None:
        corners = corners.reshape(n, 4, 3) if corners.size == n * 12 else None
    plates = []
    for i in range(n):
        t = int(types[i])
        idx = [int(c) - 1 for c in ch[i] if int(c) > 0]
        x = A[:, idx].astype(np.float64)
        zr = None
        if zero is not None and zero.size >= 2:
            z0, z1 = int(zero.ravel()[0]), int(zero.ravel()[1])
            if z1 >= z0 >= 1 and (z1 * apf) <= x.shape[0]:
                zr = (z0, z1)
                base = np.nanmean(x[(z0 - 1) * apf:z1 * apf], axis=0)
                x = x - base
        if t == 4:
            if cal is None:
                plates.append({"type": t, "error": "type 4 without CAL_MATRIX"})
                continue
            nc = len(idx)
            c = np.array(cal)
            try:
                m = c.reshape(n, nc, nc)[i] if c.size == n * nc * nc else c.reshape(-1, nc, nc)[i]
            except ValueError:
                plates.append({"type": t, "error": "CAL_MATRIX shape"})
                continue
            # C3D stores the matrix column-major (Fortran order) per plate
            m = m.T
            fm = x @ m.T
            F = fm[:, :3]
        elif t == 2:
            F = x[:, :3]
        elif t == 3:
            if len(idx) < 8:
                plates.append({"type": t, "error": "type 3 with fewer than 8 channels"})
                continue
            F = np.stack([x[:, 0] + x[:, 1], x[:, 2] + x[:, 3], x[:, 4] + x[:, 5] + x[:, 6] + x[:, 7]], axis=1)
        else:
            plates.append({"type": t, "error": "unsupported type"})
            continue
        R = None
        if corners is not None:
            c = corners[i]
            ex = (c[0] + c[3]) - (c[1] + c[2])
            ey = (c[0] + c[1]) - (c[2] + c[3])
            if np.linalg.norm(ex) > 0 and np.linalg.norm(ey) > 0:
                ex = ex / np.linalg.norm(ex)
                ey = ey - ex * (ey @ ex)
                ey = ey / np.linalg.norm(ey)
                ez = np.cross(ex, ey)
                R = np.stack([ex, ey, ez], axis=1)  # columns: plate axes in lab coordinates
        F_lab = F @ R.T if R is not None else None
        plates.append({"type": t, "channels": idx, "zero_frames": zr, "force_plate_frame": F,
                       "force_lab": F_lab, "rotation_plate_to_lab": None if R is None else R.tolist()})
    return plates


def axis_map_from_points(labels, xyz, top, bottom):
    """Rotation (3x3, det +1) that maps the laboratory vertical (from the mean of the `top` landmarks
    minus the mean of the `bottom` landmarks) onto +Z. Returns (R, axis, sign, height_mm)."""
    ti = [labels.index(n) for n in top if n in labels]
    bi = [labels.index(n) for n in bottom if n in labels]
    if not ti or not bi:
        return None
    d = np.nanmean(np.nanmean(xyz[:, ti, :], axis=1) - np.nanmean(xyz[:, bi, :], axis=1), axis=0)
    ax = int(np.nanargmax(np.abs(d)))
    sgn = 1.0 if d[ax] > 0 else -1.0
    return rotation_for(ax, sgn), ax, sgn, float(abs(d[ax]))


def rotation_for(ax, sgn):
    up = np.zeros(3)
    up[ax] = sgn
    first = [k for k in range(3) if k != ax][0]
    e1 = np.zeros(3)
    e1[first] = 1.0
    e2 = np.cross(up, e1)
    return np.stack([e1, e2, up])  # rows: new x, new y, new z in old coordinates
