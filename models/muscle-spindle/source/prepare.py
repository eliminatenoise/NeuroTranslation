"""Construct the preregistered same-trial windows from the nine original MAT files."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from fetch import FREEZE, MEMBERS, ROOT, check

BIN = 0.020
TOL = 1e-8
TRACE = "aff015-trial1-native.npz"


class TrialError(ValueError):
    """A structural or clock problem invalidating a trial."""


def write_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def vector(rec, key):
    data = np.asarray(getattr(rec, key, None))
    if data.ndim > 1 or data.dtype.kind not in "fiu":
        raise TrialError(f"missing or non-real-vector {key}")
    return data.reshape(-1).astype(np.float64, copy=False)


def clock(rec, key, least, meta):
    times = vector(rec, key)
    if times.size < 2 or not np.isfinite(times).all():
        raise TrialError(f"nonfinite or short {key}")
    steps = np.diff(times)
    if not (steps > 0).all():
        raise TrialError(f"nonincreasing {key}")
    step = float(np.median(steps))
    per_bin = round(BIN / step)
    if per_bin < least:
        raise TrialError(f"insufficient clock resolution {key}")
    hz = per_bin / BIN
    residual = float(np.max(np.abs((times - times[0]) - np.arange(times.size) / hz)))
    meta[key] = {"samples": len(times), "start_s": float(times[0]), "last_s": float(times[-1]),
                 "median_step_s": step, "samples_per_bin": per_bin, "hz": hz,
                 "max_abs_lattice_error_s": residual}
    if residual > TOL:
        raise TrialError(f"irregular or incompatible {key} lattice ({residual:.12g}s)")
    return times, per_bin


def finite_range(a):
    finite = a[np.isfinite(a)]
    if not len(finite):
        return {"nonfinite": int(a.size), "range": None, "flat": None}
    lo, hi = float(finite.min()), float(finite.max())
    return {"nonfinite": int(a.size - finite.size), "range": [lo, hi], "flat": lo == hi}


def event_indices(rec, v, hz, meta, allow_indices=True):
    e = vector(rec, "spiketimes")
    meta["event_count"] = len(e)
    if not np.isfinite(e).all() or not np.all(np.diff(e) > 0):
        raise TrialError("nonfinite, duplicate or unordered event times")
    seconds_ok = bool(np.all((e >= v[0] - TOL) & (e <= v[-1] + TOL)))
    second_tick = np.zeros(len(e), dtype=np.int64)
    if seconds_ok and len(e):
        second_tick = np.rint((e-v[0])*hz).astype(np.int64)
        seconds_ok = bool(np.all((second_tick >= 0) & (second_tick < len(v))))
        if seconds_ok:
            residual = float(np.max(np.abs(v[second_tick] - e)))
            meta["max_event_seconds_grid_error_s"] = residual
            seconds_ok = residual <= TOL
    integer_ok = allow_indices and len(e) >= 2 and bool(np.all((e >= 1) & (e <= len(v)) & (e == np.floor(e))))
    if integer_ok:
        integer_tick = e.astype(np.int64) - 1
        try:
            isi = vector(rec, "ISI")
            integer_ok = isi.shape == (len(e)-1,) and np.allclose(isi, np.diff(v[integer_tick]), rtol=0, atol=TOL)
        except TrialError:
            integer_ok = False
    if seconds_ok and integer_ok and not np.array_equal(second_tick, integer_tick):
        raise TrialError("ambiguous event indices versus seconds")
    if seconds_ok:
        ticks = second_tick
        meta["event_coordinates"] = "seconds on electrical sample times" if len(e) else "empty numerical event vector"
    elif integer_ok:
        ticks = integer_tick
        meta["event_coordinates"] = "MATLAB 1-based electrical indices confirmed by archived ISI"
    else:
        raise TrialError("event coordinates fail seconds and independently checked integer-index interpretations")
    if not np.all(np.diff(ticks) > 0):
        raise TrialError("duplicate event ticks on the native electrical clock")
    expected_isi = np.diff(v[ticks])
    for name, linked, atol, rtol in [("ISI", expected_isi, TOL, 0),
                                      ("firing_rate", 1/expected_isi, 1e-7, 1e-7)]:
        try:
            stored = vector(rec, name)
            if stored.shape != linked.shape:
                meta[name] = {"ok": False, "stored": len(stored), "expected": len(linked)}
            elif not np.isfinite(stored).all():
                meta[name] = {"ok": False, "error": "nonfinite ancillary field"}
            else:
                meta[name] = {"ok": bool(np.allclose(stored, linked, rtol=rtol, atol=atol)),
                              "max_abs_error": float(np.max(np.abs(stored-linked), initial=0))}
        except TrialError as exc:
            meta[name] = {"ok": False, "error": str(exc)}
    return ticks


def trial_windows(rec, meta, out, single_time=False):
    m, nm = clock(rec, "time", 2, meta)
    meta["mechanics_matches_readme"] = (nm == (200 if meta["prefix"] == 4 else 40))
    if single_time:
        if "time_PotMem" in rec._fieldnames:
            raise TrialError("single-time sensitivity cannot replace a deposited electrical clock")
        v, nv = m, nm
        meta["electrical_time_basis"] = "one deposited time; no separately stored electrical clock"
    else:
        v, nv = clock(rec, "time_PotMem", 1, meta)
    route = "one_deposited_time" if single_time else "two_clock"
    meta["clock_route"] = route
    hv = nv / BIN
    offset = round((m[0]-v[0])*hv)
    origin_error = float(abs(m[0] - (v[0] + offset/hv)))
    meta.update(mechanics_origin_electrical_tick=offset, origin_alignment_error_s=origin_error)
    if origin_error > TOL:
        raise TrialError("mechanics origin off electrical lattice")
    f, p, a = (vector(rec, key) for key in ("Force", "Length", "PotMem"))
    if not (len(m) == len(f) == len(p) and len(v) == len(a)):
        raise TrialError("source clocks and sampled signal lengths differ")
    meta["signals"] = {k: finite_range(x) for k, x in [("Force", f), ("Length", p), ("PotMem", a)]}
    ticks = event_indices(rec, v, hv, meta, allow_indices=not single_time)
    if single_time:
        meta["event_coordinates"] = ("absolute seconds on one deposited time axis" if len(ticks)
                                     else "empty numerical event vector on one deposited time axis")
        if not all(meta[k]["ok"] for k in ("ISI","firing_rate")):
            raise TrialError("single-time archive interval or rate mismatch")
    if meta["afferent"] == "aff015" and meta["trial"] == 1:
        np.savez_compressed(out / TRACE, time=m, time_PotMem=v, Force=f, Length=p,
                            PotMem=a, spiketimes=v[ticks], source_spiketimes=vector(rec, "spiketimes"))
    nbin = (len(m)-1) // nm  # require observed sample at the right edge
    idx = np.arange(nbin, dtype=np.int32)
    starts = offset + idx.astype(np.int64)*nv
    support = (starts >= 0) & (starts+nv < len(v))
    force = f[:nbin*nm].reshape(nbin, nm)
    pos = p[:nbin*nm].reshape(nbin, nm)
    mm = m[:nbin*nm].reshape(nbin, nm)
    good_m = np.isfinite(force).all(1) & np.isfinite(pos).all(1)
    # Prefix sums avoid resampling the potential; use exact in-bounds source spans.
    bad_v = np.concatenate(([0], np.cumsum(~np.isfinite(a), dtype=np.int64)))
    good_v = np.zeros(nbin, dtype=bool)
    sel = starts[support]
    good_v[support] = bad_v[sel+nv] == bad_v[sel]
    valid = good_m & support & good_v
    edges = offset + np.arange(nbin+1, dtype=np.int64)*nv
    counts = np.diff(np.searchsorted(ticks, edges, side="left")).astype(np.int32)
    # Count conservation includes native events before/after full mechanical bins.
    before = int(np.searchsorted(ticks, edges[0], side="left"))
    after = len(ticks) - int(np.searchsorted(ticks, edges[-1], side="left"))
    if before + int(counts.sum()) + after != len(ticks):
        raise TrialError("event assignment failed conservation")
    last = np.stack((force[:, -1], pos[:, -1]), axis=1)
    first = np.stack((force[:, 0], pos[:, 0]), axis=1)
    with np.errstate(invalid="ignore"):
        slopes = (last-first) / (mm[:, -1]-mm[:, 0])[:, None]
        means = np.stack((force.mean(1), pos.mean(1)), axis=1)
    tokens = np.column_stack((last, slopes, counts))
    # Sum six Boolean bins without rollover or padding. Empty/short trials remain inventoried.
    if nbin >= 6:
        target = np.flatnonzero(np.lib.stride_tricks.sliding_window_view(valid, 6).all(axis=1)) + 5
    else:
        target = np.array([], dtype=np.int64)
    hist = target[:, None] + np.arange(-5, 0, dtype=np.int64)
    meta.update(complete_mechanics_bins=nbin, trailing_native_intervals=(len(m)-1) % nm,
                candidate_windows=max(0, nbin-5), valid_bins=int(valid.sum()), rows=len(target),
                bins_missing_electrical_coverage=int((~support).sum()),
                bins_nonfinite_mechanics=int((~good_m).sum()), bins_nonfinite_potential=int((support & ~good_v).sum()),
                spikes_before_full_bins=before, spikes_after_full_bins=after, spikes_in_full_bins=int(counts.sum()),
                target_spikes=int(counts[target].sum()))
    rows = {"X": tokens[hist], "mech_mean": means[hist], "y_count": counts[target],
            "current_mech": last[target-1], "y_delta": last[target]-last[target-1],
            "bin_index": idx[target], "cutoff_s": m[target*nm], "clock_route": np.repeat(route,len(target))}
    for k, dtype in [("trial", np.int32), ("prefix", np.int8), ("afferent", str), ("trial_type", str)]:
        rows[k] = np.repeat(np.asarray(meta[k], dtype=dtype), len(target))
    mask = {"bin_index": idx, "electrical_coverage": support, "finite_mechanics": good_m,
            "finite_potential_covered": good_v, "valid": valid, "count": counts, "clock_route": np.repeat(route,nbin)}
    return rows, mask


def describe_failure(rec, entry):
    """Describe source fields even when clock failure precludes any eligible bin."""
    diag = {"field_names": list(getattr(rec, "_fieldnames", []))}
    for key in ("time", "time_PotMem", "Force", "Length", "PotMem", "spiketimes", "ISI", "firing_rate"):
        try:
            arr = vector(rec, key)
        except TrialError as exc:
            diag[key] = {"available": False, "reason": str(exc)}
            continue
        item = {"available": True, "samples": len(arr), **finite_range(arr)}
        diag[key] = item
        if key == "spiketimes":
            entry["event_count"] = len(arr)
            item["strict_increase"] = bool(np.all(np.diff(arr) > 0))
        if key in ("time", "time_PotMem") and len(arr) > 1 and np.isfinite(arr).all():
            d = np.diff(arr)
            item.update(first_s=float(arr[0]), last_s=float(arr[-1]), step_range_s=[float(d.min()), float(d.max())],
                        median_step_s=float(np.median(d)), nonpositive_steps=int(np.sum(d <= 0)))
    # Neither these coordinate diagnostics nor matching vector lengths qualify a missing clock.
    if "event_coordinates" not in entry:
        entry["event_coordinates"] = "unverified; native clock or structural QC failed"
    if "signals" not in entry:
        entry["signals"] = {k: {s:diag[k][s] for s in ("nonfinite", "range", "flat")}
                            for k in ("Force", "Length", "PotMem") if diag[k]["available"]}
    entry["excluded_source_diagnostics"] = diag


def read_one(path, out):
    name = path.name
    aff = name.split("_")[0]
    proof = check(path, MEMBERS[name])
    contents = loadmat(path, variable_names=["info", "proc_data"], squeeze_me=True, struct_as_record=False)
    info = contents["info"]
    recorded = str(getattr(info, "affname", ""))
    trials = np.atleast_1d(contents["proc_data"]).ravel(order="F")
    labels = np.atleast_1d(getattr(info, "trial_type", None)).ravel(order="F")
    group = {"member": name, "afferent": aff, "recorded_affname": recorded,
             "source_date": str(getattr(info, "date", "")), "prefix": int(aff[3]),
             "integrity": proof, "stored_trials": len(trials), "label_count": len(labels), "trials": []}
    rows, masks = [], []
    for i, rec in enumerate(trials):
        entry = {"afferent": aff, "trial": i+1, "prefix": group["prefix"], "eligible": False, "rows": 0}
        group["trials"].append(entry)
        try:
            if aff != recorded or len(trials) != len(labels):
                raise TrialError("internal identity or trial-label cardinality mismatch")
            label = labels[i]
            if not isinstance(label, (str, np.str_)) or not label.strip():
                raise TrialError("unknown or empty trial label")
            entry.update(trial_type=str(label), protocol_class="repeated ramp-release"
                         if label == "triangle_series" else "ramp-hold-release variant")
            r, mask = trial_windows(rec, entry, out)
            mask["afferent"] = np.repeat(aff, len(mask["valid"]))
            mask["trial"] = np.full(len(mask["valid"]), i+1, dtype=np.int32)
            rows.append(r)
            masks.append(mask)
            if entry["rows"]:
                entry["eligible"] = True
            else:
                entry["reason"] = "no span of six consecutive complete valid bins"
        except TrialError as err:
            entry["reason"] = str(err)
            describe_failure(rec, entry)
    return group, rows, masks


def table(parts):
    return {key: np.concatenate([part[key] for part in parts], axis=0) for key in parts[0]}


def build(directory, out):
    out.mkdir(parents=True, exist_ok=True)
    groups, rows, masks = [], [], []
    for name in sorted(MEMBERS):
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing registered member: {path}")
        group, r, m = read_one(path, out)
        groups.append(group)
        rows.extend(r)
        masks.extend(m)
        print(name, group["stored_trials"], sum(t["rows"] for t in group["trials"]), flush=True)
    if not rows:
        raise ValueError("No source trial passed structural validation")
    allrows = table(rows)
    for name, parts in [("bin-mask", table(masks)), ("windows", allrows)]:
        tmp = out / (name+".tmp.npz")
        np.savez_compressed(tmp, **parts)
        tmp.replace(out / (name+".npz"))
    write_json(out / "trial-qc.json", groups)
    return groups, allrows


if __name__ == "__main__":
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--directory", type=Path, default=ROOT/"private"/"members")
    arg.add_argument("--output", type=Path, default=ROOT/"private")
    args = arg.parse_args()
    build(args.directory, args.output)
