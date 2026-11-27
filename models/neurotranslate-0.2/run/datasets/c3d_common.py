"""Tokens from one C3D recording: markers (kin), named EMG analog channels (emg) and plate forces (force).

All streams of a C3D file share one clock (points at point_rate, analog at analog_rate = point_rate x
per_frame). Markers are rotated by the dataset's fixed axis map so that the laboratory vertical is +Z;
the map is re-derived on every recording from pelvis and foot landmarks and any disagreement is
recorded. Plate forces are rotated from plate to laboratory axes (FORCE_PLATFORM:CORNERS), then by the
same axis map, and given the ground-reaction sign (vertical positive while loaded), checked per file.
"""
import numpy as np

import common
import c3d_reader
import vocab

AX = "xyz"


def add_marker_channels(chans, natives, scheme, dataset):
    """Add kin channels name_x/_y/_z for each native marker label; returns {native: [i_x, i_y, i_z]}."""
    out = {}
    for nat in natives:
        lm, key = vocab.landmark_key(nat, scheme)
        idx = []
        for a in AX:
            idx.append(chans.add("kin", "%s_%s" % (nat, a), kind="marker", units="mm", value_type="measured",
                                 filtering="author-filtered or gap-filled (see Q6)", landmark=lm,
                                 vocab=(key + ":" + a) if key else None, axis=a,
                                 row="shared" if key else "dataset:%s:%s" % (dataset, nat)))
        out[nat] = idx
    return out


def add_emg_channels(chans, items, dataset, fs):
    """items: [(channel name, side, muscle text)]."""
    out = {}
    for name, side, muscle in items:
        key = vocab.muscle_key(side, muscle) if muscle else None
        out[name] = chans.add("emg", name, kind="surface_emg", units="log V (log RMS per 20 ms step)",
                              value_type="measured", source_units="V", rate_hz=fs, modality="surface EMG "
                              "(muscle electrical activity, not a nerve recording)", muscle=muscle, side=side,
                              vocab=key, row="shared" if key else "dataset:%s:%s" % (dataset, name))
    return out


def add_plate_channels(chans, n_plates, units="N"):
    out = {}
    for p in range(n_plates):
        out[p] = [chans.add("force", "plate%d_%s" % (p + 1, a), kind="plate_force", units=units,
                            value_type="measured", frame="laboratory, vertical +Z, ground reaction on the person",
                            vocab="force:plate%d:%s" % (p + 1, a), axis=a) for a in AX]
    return out


def tokenise(data, chans, rec_id, unit, spec, meta):
    """spec: marker_idx {native: [i,i,i]}, scheme, R (3x3 dataset axis map), emg {analog label: channel index},
    plates {plate number (0-based): [i,i,i]} or None, top/bottom landmark natives for the axis re-check."""
    d = c3d_reader.read_c3d(data)
    pr = d["point_rate"]
    F = d["frames"]
    dur = F / pr
    S = common.n_steps_for(dur)
    rec = common.Recording(rec_id, unit, S, meta)
    checks = {"frames": F, "point_rate": pr, "analog_rate": d["analog_rate"], "analog_per_frame": d["analog_per_frame"]}
    # clock: analog samples must be exactly frames x per_frame
    na = d["analog"].shape[0]
    checks["analog_samples_equal_frames_x_per_frame"] = (na == F * d["analog_per_frame"]) if na else None
    if na:
        checks["analog_rate_equals_point_rate_x_per_frame"] = abs(d["analog_rate"] - pr * d["analog_per_frame"]) < 1e-6
    labels = d["point_labels"]
    strip = [l.split(":")[-1] for l in labels]
    R = np.asarray(spec["R"])
    am = c3d_reader.axis_map_from_points(strip, d["points"], spec["top"], spec["bottom"])
    if am is not None:
        checks["vertical_axis_from_landmarks"] = {"axis": am[1], "sign": am[2], "height_mm": round(am[3], 1),
                                                  "agrees_with_dataset_map": bool(np.allclose(am[0], R))}
    # markers
    xyz = d["points"] @ R.T
    lo, hi = common.step_bounds(F, pr, 0.0, S)
    present_markers = []
    for nat, idx in spec["marker_idx"].items():
        if nat not in strip:
            continue
        j = strip.index(nat)
        val, msk = common.kin_features(xyz[:, j, :], lo, hi)
        rec.put("kin", idx, val, msk, chans.n("kin"))
        present_markers.append(nat)
    checks["markers_present"] = len(present_markers)
    checks["marker_samples_invalid_fraction"] = round(float(d["point_invalid"].mean()), 5) if F else None
    checks["marker_samples_modelled_fraction"] = round(float(d["point_modelled"].mean()), 5) if F else None
    # EMG
    if spec.get("emg") and na:
        ar = d["analog_rate"]
        alo, ahi = common.step_bounds(na, ar, 0.0, S)
        cols, idx = [], []
        for lab, ci in spec["emg"].items():
            if lab in d["analog_labels"]:
                cols.append(d["analog_labels"].index(lab))
                idx.append(ci)
        if cols:
            x = d["analog"][:, cols]
            val, msk = common.emg_features(x, ar, alo, ahi)
            rec.put("emg", idx, val, msk, chans.n("emg"))
        checks["emg_channels_present"] = len(cols)
    # plates
    if spec.get("plates") is not None and na:
        ar = d["analog_rate"]
        alo, ahi = common.step_bounds(na, ar, 0.0, S)
        signs = []
        for p, plate in enumerate(d["force_platforms"]):
            if p not in spec["plates"] or plate.get("force_lab") is None:
                continue
            Fl, nbad = common.mask_implausible_force(plate["force_lab"] @ R.T)
            loaded = np.abs(Fl[:, 2]) > 50.0
            sgn = 1.0
            if loaded.sum() > 10 and np.nanmedian(Fl[loaded, 2]) < 0:
                sgn = -1.0
            Fl = Fl * sgn
            val, msk = common.force_features(Fl, alo, ahi)
            if plate.get("zero_frames"):
                z_end_s = plate["zero_frames"][1] / pr
                msk[: int(np.ceil(z_end_s / common.STEP_S - 1e-9))] = False
            rec.put("force", spec["plates"][p], val, msk, chans.n("force"))
            signs.append({"plate": p + 1, "type": plate["type"], "sign_applied": sgn, "samples_above_10kN_masked": nbad,
                          "loaded_samples": int(loaded.sum()), "zero_frames": plate.get("zero_frames")})
        checks["plates"] = signs
    events = d["events"]
    m = dict(meta)
    m.update({"duration_s": round(dur, 4), "events": len(events),
              "event_labels": sorted({e["label"] for e in events})})
    return rec, m, checks
