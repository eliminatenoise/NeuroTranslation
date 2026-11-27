"""HYGRIP v1 (figshare 12383639, MIT): the 7 eligible TRAIN groups /B /C /D /E /H /I /K.

Roster: the earlier source custody's TRAIN manifest (frozen role TRAIN for /B /C /D /E /H /I /K /N; /N is
withheld by the frozen timing gate) and the source admission that lists the allowed TRAIN paths. The
archive's sha256 is checked before HDF5 access. Only the literal group paths are opened (no root-key
enumeration, as the admission requires), so the development 3 and final 3 groups are never named or read.

Per group three device recordings on separate clocks, each with an 'events' attribute (time in seconds
on its own clock, label -1 rest/start/end, 0 left-hand Go, 1 right-hand Go):
  frc  one grip transducer channel, 50 Hz, signed volts as stored (uncalibrated)
  eeg  24 scalp channels around C3 and C4, 1 kHz, millivolts as stored
  emg  4 bilateral surface EMG channels, 1 kHz, millivolts, electrode positions not mapped
Pairing: the devices are aligned at Go markers. The inter-Go clock screen of the earlier design (|force
interval - EEG interval| <= 40 ms between consecutive Go markers) is recomputed here over every Go marker
of both hands. A trial enters only if both intervals touching its Go marker pass; right-hand trials of
the 7 groups passed it before, and left-hand trials enter only if they pass it now (protocol 4.2).
Recording = one Go trial: from its Go marker to the next event marker, each device's samples placed on
one 20 ms grid whose origin is that device's Go time. EEG and EMG share one clock (identical event times).
"""
import json
from pathlib import Path

import numpy as np

import common
import neural_common as nc

DATASET = "hygrip"
KIND = "person"
GROUPS = ["/B", "/C", "/D", "/E", "/H", "/I", "/K"]
SCREEN_MS = 40.0
# EEG is stored at a scale of about 1e-4 (stored unit), so float16 would put many low-pass values in its subnormal
# range (worst-case error 8.5% of a channel's SD in a trial run); the field group is kept in float32.
GROUP_DTYPES = {"field": np.float32}
ARCHIVE_SHA256 = "6819a18b13599c13a75ca5d36e65d7b6859534f548dbb2e626d31649cd990e88"
META = {
    "name": "HYGRIP", "doi": "10.6084/m9.figshare.12383639.v1", "species": "human", "sites": 1,
    "derived": False, "paired": True,
    "events_definition": "Go markers (one per tokenised trial; right- or left-hand cue onset)",
    "context": {"dataset": DATASET, "species": "human", "task": "cued isometric hand grip (10 x 1.55 s on, 0.55 s off per Go)",
                "body_plan": "human hand and forearm", "value_flag": "measured"},
    "streams": [
        {"group": "field", "kind": "eeg", "channels": 24, "rate_hz": 1000, "units": "mV (source, stored as 'milivolts')",
         "value_type": "measured", "rows": "learned per recording (positions named around C3 and C4, no 10-10 names)"},
        {"group": "emg", "kind": "surface_emg_unmapped", "channels": 4, "rate_hz": 1000, "units": "mV (source); log RMS per step",
         "value_type": "measured", "rows": "learned per recording (electrode positions not mapped)"},
        {"group": "force", "kind": "grip_transducer", "channels": 1, "rate_hz": 50, "units": "V (signed, uncalibrated)",
         "value_type": "measured"},
    ],
    "notes": ["Grip force is uncalibrated transducer voltage (no newton conversion; zero and polarity unverified).",
              "EEG magnitudes fit volts although the stored unit string is 'milivolts'; values are kept as stored.",
              "Each device's samples are placed relative to its own Go time; the EEG/EMG and force clocks are not "
              "otherwise resampled.", "The first 0.5 s of each trial has no field value (filter warm-up)."],
}


def _src(paths):
    return Path(paths["hygrip_source"])


def _manifest(paths):
    return json.loads((_src(paths) / "TRAIN-SOURCE-MANIFEST.json").read_text())


def roster(paths):
    m = _manifest(paths)
    grant_p = _src(paths).parent / "programme-update-91" / "hygrip-train-source-admission-r2.json"
    grant = json.loads(grant_p.read_text())
    parts = m["availability"]["participants"]
    withheld = m["availability"]["waveform_withheld_groups"]
    unit_roles = {g: v["frozen_role"] for g, v in parts.items()}
    units = sorted(g for g, v in parts.items() if v["frozen_role"] == "TRAIN" and g not in withheld)
    assert units == GROUPS and sorted(grant["allowed_groups_train"]) == sorted(GROUPS + withheld)
    return {"units": units, "unit_roles": unit_roles, "training_roles": ["TRAIN"],
            "rule": "frozen TRAIN groups of the HYGRIP design, eligible under its timing gate",
            "excluded": {"withheld_by_timing_gate": sorted(withheld),
                         "development_3_and_final_3": []},
            "extra": {"development_and_final_groups": "never named or opened (their paths are private; the HDF5 root "
                      "keys are not enumerated)"},
            "roster_files": [{"file": "HYGRIP TRAIN-SOURCE-MANIFEST.json (earlier source custody)",
                              "sha256": common.sha256_file(_src(paths) / "TRAIN-SOURCE-MANIFEST.json")},
                             {"file": "HYGRIP source admission r2 (allowed TRAIN paths)", "sha256": common.sha256_file(grant_p)}]}


def channels(paths):
    m = _manifest(paths)
    names = m["measurement"]["eeg_channels_in_source_order"]
    field = [dict(name="eeg:" + n, kind="eeg", units="log mV^2 (band power) / mV (low-pass)", source_units="mV",
                  rate_hz=1000, value_type="measured", modality="scalp EEG (field potential)", vocab=None,
                  row="per-recording", site=n) for n in names]
    emg = [dict(name="emg%d" % i, kind="surface_emg_unmapped", units="log mV (log RMS per 20 ms step)", source_units="mV",
                rate_hz=1000, value_type="measured", modality="surface EMG (muscle electrical activity, not a nerve recording)",
                vocab=None, row="per-recording", position="bilateral forearm, row-to-position map not documented")
           for i in range(4)]
    force = [dict(name="grip_volts", kind="grip_transducer", units="V (uncalibrated)", value_type="measured", rate_hz=50,
                  vocab=None, row="per-dataset")]
    return {"field": field, "emg": emg, "force": force}


def jobs(paths, units):
    return [(u, None) for u in units]


def _open(paths):
    import h5py
    arch = _src(paths) / "private" / "hygrip.h5"
    return h5py.File(arch, "r"), arch


def screen(force_ev, eeg_ev):
    """Inter-Go residuals (ms) between consecutive Go markers of both hands; returns per-Go pass flags."""
    fg = force_ev[force_ev[:, 1] >= 0]
    eg = eeg_ev[eeg_ev[:, 1] >= 0]
    assert len(fg) == len(eg) and np.array_equal(fg[:, 1], eg[:, 1]), "Go label sequences differ"
    res = 1000.0 * (np.diff(fg[:, 0]) - np.diff(eg[:, 0]))
    ok_int = np.abs(res) <= SCREEN_MS
    n = len(fg)
    ok = np.ones(n, bool)
    for i in range(n):
        if i > 0 and not ok_int[i - 1]:
            ok[i] = False
        if i < n - 1 and not ok_int[i]:
            ok[i] = False
    return fg, eg, res, ok


def process_unit(paths, unit, payload, shared):
    assert unit in GROUPS
    f, arch = _open(paths)
    with f:
        root_rate = {k: f.attrs.get(k + "_sfreq") for k in ("frc", "eeg", "emg")}
        grp = f[unit]
        frc, eeg, emg = grp["frc"], grp["eeg"], grp["emg"]
        fe, ee, me = frc.attrs["events"], eeg.attrs["events"], emg.attrs["events"]
        assert np.array_equal(ee, me), "EEG and EMG events differ"
        fs_f, fs_e = float(root_rate["frc"] or 50), float(root_rate["eeg"] or 1000)
        assert fs_f == 50 and fs_e == 1000 and float(root_rate["emg"] or 1000) == 1000
        F = frc[()].astype(np.float64)
        E = eeg[()].astype(np.float64)
        M = emg[()].astype(np.float64)
    assert F.shape[0] == 1 and E.shape[0] == 24 and M.shape[0] == 4 and E.shape[1] == M.shape[1]
    F, E, M = F.T, E.T, M.T
    fg, eg, res, ok = screen(fe, ee)
    # next event marker after each Go on each clock
    recs, metas, checks = [], [], {"inter_go_residuals_ms": np.round(res, 3).tolist(), "screen_pass": ok.tolist(),
                                   "go_labels": fg[:, 1].astype(int).tolist()}
    for gi in range(len(fg)):
        hand = "right" if fg[gi, 1] == 1 else "left"
        if not ok[gi]:
            continue
        tf, te = fg[gi, 0], eg[gi, 0]
        nf = fe[fe[:, 0] > tf][0, 0] if np.any(fe[:, 0] > tf) else F.shape[0] / fs_f
        ne = ee[ee[:, 0] > te][0, 0] if np.any(ee[:, 0] > te) else E.shape[0] / fs_e
        dur = min(nf - tf, ne - te, F.shape[0] / fs_f - tf, E.shape[0] / fs_e - te)
        S = common.n_steps_for(dur)
        rid = "%s_go%02d_%s" % (unit.strip("/"), gi + 1, hand)
        rec = nc.Rec(rid, unit, S)
        # EEG/EMG: samples from the Go time on, origin at the Go time
        i0 = int(np.ceil(te * fs_e - 1e-6))
        i1 = min(E.shape[0], i0 + int(np.ceil(dur * fs_e)) + 1)
        t0e = i0 / fs_e - te
        v, m = nc.field_features(E[i0:i1], fs_e, t0e, S)
        rec.put("field", v, m)
        lo, hi = common.step_bounds(i1 - i0, fs_e, t0e, S)
        v, m = common.emg_features(M[i0:i1], fs_e, lo, hi)
        rec.put("emg", v, m)
        j0 = int(np.ceil(tf * fs_f - 1e-6))
        j1 = min(F.shape[0], j0 + int(np.ceil(dur * fs_f)) + 1)
        t0f = j0 / fs_f - tf
        lo, hi = common.step_bounds(j1 - j0, fs_f, t0f, S)
        v, m = common.force_features(F[j0:j1], lo, hi)
        rec.put("force", v, m)
        recs.append(rec)
        metas.append({"source_files": {"hygrip.h5": ARCHIVE_SHA256}, "hdf5_paths": [unit + "/frc", unit + "/eeg", unit + "/emg"],
                      "task": "grip_" + hand, "condition": hand, "session": 1, "events": 1, "go_ordinal": gi + 1,
                      "duration_s": round(dur, 4), "force_go_s": float(tf), "eeg_go_s": float(te)})
    checks["trials_tokenised"] = len(recs)
    checks["nonfinite_samples"] = {"frc": int((~np.isfinite(F)).sum()), "eeg": int((~np.isfinite(E)).sum()),
                                   "emg": int((~np.isfinite(M)).sum())}
    checks["root_rates"] = {k: (float(v) if v is not None else None) for k, v in root_rate.items()}
    return recs, metas, checks, {}


def file_audit(paths, results):
    bad = [p for r in results for m in r["recordings"] for p in m["hdf5_paths"] if not p.startswith(r["unit"] + "/")]
    return {"pass": not bad and {r["unit"] for r in results} == set(GROUPS), "paths_outside_unit": bad,
            "groups_opened": sorted(r["unit"] for r in results)}


def source_file_summary(results):
    rows = sorted({(p, m["source_files"]["hygrip.h5"]) for r in results for m in r["recordings"] for p in m["hdf5_paths"]})
    return {"files": 1, "hdf5_paths": len(rows), "path_list_sha256": common.sha256_text(json.dumps(rows))}


def gates(paths, results, summary):
    arch_ok = common.sha256_file(_src(paths) / "private" / "hygrip.h5") == ARCHIVE_SHA256
    res = [abs(x) for r in results for x in r["checks"]["inter_go_residuals_ms"]]
    right = sum(1 for r in results for m in r["recordings"] if m["condition"] == "right")
    left = sum(1 for r in results for m in r["recordings"] if m["condition"] == "left")
    left_total = sum(1 for r in results for l in r["checks"]["go_labels"] if l == 0)
    return {
        "Q3_access": {"pass": arch_ok, "how": "local archive (sha256 checked before access); only the 7 literal TRAIN group "
                      "paths opened; root keys not enumerated"},
        "Q4_clock": {"pass": max(res) <= SCREEN_MS, "how": "devices aligned at Go markers; consecutive inter-Go interval "
                     "residuals (force clock minus EEG clock) recomputed over every Go marker of both hands",
                     "max_abs_residual_ms": round(max(res), 3), "threshold_ms": SCREEN_MS,
                     "right_hand_trials": right, "left_hand_trials_entered": left, "left_hand_trials_in_groups": left_total},
        "Q5_labels": {"pass": True, "how": "EEG and EMG kept in their stored unit (root attributes 'milivolts'), grip in "
                      "signed volts (uncalibrated); all measured; EMG is muscle activity, not a nerve recording",
                      "flag": "EEG per-channel standard deviations are about 1e-4 to 2e-4 in the stored unit, which fits "
                      "volts better than millivolts; EMG (about 0.01-0.03) fits millivolts. Values are kept as stored; "
                      "per-channel z-scores make the scale irrelevant to training, but no physical amplitude is claimed"},
        "Q6_causality": {"pass": True, "author_filtering": "release filter phase of every stream not documented (recorded as "
                         "unverified)", "our_features": "causal"},
    }
