"""Download prespecified AnkleImage Task 3 members and extract original tracker knots.

Requires NumPy and SciPy. Source data and attribution are described in RIGHTS.md.
Only the named geometry variables required by each original tracker layout are decoded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

import numpy as np
from scipy.io import loadmat, whosmat

ROOT = "https://ftp.ebi.ac.uk/biostudies/fire/S-BIAD/482/S-BIAD1482/Files/ScientificData/Task%203"
PHASES = {"development": tuple(f"A{i:02d}" for i in range(1, 5)),
          "assessment": tuple(f"A{i:02d}" for i in range(5, 9))}
PILOT_SHA = "505b10295bb76e8f7808e673d8a1473d2c129bde6fbf9e2fc12c879cb52297d0"
HEADERS = ["TIME", "FASCICLE LENGTH", "PENNATION ANLE"]
TOL_TIME = 1e-9
TOL_ANGLE = 2e-12
MAX_BYTES = 100 * 1024 * 1024


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def atomic_json(target, obj):
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False) as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")
    os.replace(f.name, target)


class SchemaError(ValueError):
    pass


def require(condition, problem):
    if not condition:
        raise SchemaError(problem)


def obtain(person, trial, base, reuse):
    mat = base.with_suffix(".mat")
    download = base.with_suffix(".download.json")
    filename = f"{person}_echo_emg_angle_PA_FL_trial{trial}.mat"
    url = f"{ROOT}/Sub_{person}/{filename}"
    if download.exists() and mat.exists():
        r = json.loads(download.read_text())
        require(r["url"] == url and sha(mat) == r["sha256"] and
                mat.stat().st_size == r["bytes"], "Cached original differs from receipt.")
        return mat, r
    if mat.exists() or download.exists():
        raise ValueError(f"Partial cache entry needs its original receipt verified: {base}")
    base.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=base.parent, delete=False) as f:
        partial = Path(f.name)
        try:
            if reuse is not None and person == "A01" and trial == 1:
                require(sha(reuse) == PILOT_SHA, "Pilot source digest changed.")
                with reuse.open("rb") as original:
                    shutil.copyfileobj(original, f)
                method = "Previously downloaded original, checked against the pilot SHA256."
                etag, length, final = '"4e68cf-6273a85d243c0"', 5138639, url
            else:
                with urllib.request.urlopen(url, timeout=90) as response:
                    final, etag = response.url, response.headers.get("ETag")
                    require(final == url, "Unexpected source redirect.")
                    size = response.headers.get("Content-Length")
                    length = None if size is None else int(size)
                    require(length is None or 0 < length <= MAX_BYTES, "Unexpected source size.")
                    for chunk in iter(lambda: response.read(262144), b""):
                        f.write(chunk)
                        require(f.tell() <= MAX_BYTES, "Member exceeds the selected-file size bound.")
                method = "HTTPS GET of the exact public archive member."
            f.flush()
            n = partial.stat().st_size
            require(n > 0 and (length is None or n == length), "Incomplete source transfer.")
            digest = sha(partial)
            if person == "A01" and trial == 1:
                require(digest == PILOT_SHA, "Previously reviewed source has changed.")
            r = dict(person=person, trial=trial, member=f"Task 3/Sub_{person}/{filename}",
                     url=url, final_url=final, bytes=n, http_content_length=length,
                     etag=etag, sha256=digest, acquisition=method)
            os.replace(partial, mat)
            atomic_json(download, r)
        finally:
            partial.unlink(missing_ok=True)
    return mat, r


def decode_strings(array):
    labels = []
    for item in np.asarray(array).flat:
        v = np.asarray(item)
        require(v.dtype.kind in "US" and v.size == 1, "Unexpected tracker label representation.")
        labels.append(str(v.item()))
    return labels


def describe_table(obj):
    require(obj.shape == (1, 1) and obj.dtype.names is not None, "Expected a scalar MATLAB struct.")
    names = list(obj.dtype.names)
    require(set(names) == {"data", "textdata", "colheaders"}, f"Tracker fields differ: {names}")
    table = obj[0, 0]
    data = table["data"]
    headers = decode_strings(table["colheaders"])
    text = decode_strings(table["textdata"])
    detail = dict(fields=names, shape=list(data.shape), data_dtype=str(data.dtype),
                  textdata_shape=list(table["textdata"].shape), textdata=text,
                  colheaders_shape=list(table["colheaders"].shape), colheaders=headers)
    require(headers == HEADERS and text == headers, f"Tracker column schema differs: {detail}")
    require(data.ndim == 2 and data.shape[1] == 3 and data.dtype == np.dtype("float64"),
            f"Unsupported tracker numeric table: {detail}")
    require(len(data) >= 2 and np.isfinite(data).all(), "Short or nonfinite tracker table.")
    return data, detail


def vector(array, name, n):
    require(array.ndim == 2 and 1 in array.shape and array.size == n and
            array.dtype == np.dtype("float64") and np.isfinite(array).all(),
            f"{name} is not a finite source vector for the {n} paired tracker rows: {array.shape}")
    return array.reshape(-1)


def reconstruction_errors(curve, first, second):
    """Compare each specified expansion to the complete published geometry curve."""
    require(curve.size == (len(first) - 1) * 10, "Unsupported dense geometry length.")
    x = np.arange(curve.size) / 10
    return {label: float(np.max(np.abs(curve - np.interp(x, np.arange(len(v)), v))))
            for label, v in (("first", first), ("second", second), ("mean", (first + second) / 2))}


def interpolation_test(v):
    """Error of the closest of ten possible coarser piecewise-linear source grids."""
    errors = []
    for phase in range(10):
        coarse = np.arange(phase, len(v), 10)
        x = np.arange(coarse[0], coarse[-1] + 1)
        errors.append(float(np.max(np.abs(v[x] - np.interp(x, coarse, v[coarse])))))
    return min(errors)


def qualify(mat):
    inventory = {name: (shape, kind) for name, shape, kind in whosmat(mat)}
    if all(inventory.get(k) == ((1, 1), "struct") for k in ("A", "B")):
        pair = ("A", "B")
        length_name = "fascicle_length1" if "fascicle_length1" in inventory else "fascicle_length"
        angle_name = "PA1" if "PA1" in inventory else "PA"
        fields = [*pair, length_name, angle_name]
    elif all(inventory.get(k) == ((1, 1), "struct") for k in ("A1", "A2")):
        pair = ("A1", "A2")
        length_name, angle_name = "fascicle_length1", "PA1"
        fields = [*pair, length_name, angle_name, "fascicle_length2", "PA2", "FL", "PA"]
    elif inventory.get("A1") == ((1, 1), "struct") and "A2" not in inventory:
        pair = ("A1",)
        length_name, angle_name = "fascicle_length1", "PA1"
        fields = [*pair, length_name, angle_name, "FL", "PA"]
    else:
        structs = [k for k, v in inventory.items() if v[1] == "struct"]
        raise SchemaError(f"Expected known native tracking structs. Found struct names {structs}.")
    missing = sorted(set(fields) - set(inventory))
    require(not missing, f"Missing native geometry variables for {pair}: {missing}")
    m = loadmat(mat, variable_names=fields, squeeze_me=False)
    a, ad = describe_table(m[pair[0]])
    tables = {pair[0]: ad}
    if len(pair) == 2:
        b, tables[pair[1]] = describe_table(m[pair[1]])
        require(a.shape == b.shape and np.array_equal(a[:, 0], b[:, 0]),
                "Source table rows cannot be paired exactly on TIME.")
    t = a[:, 0].copy()
    dt = np.diff(t)
    require(np.all(dt > 0), "Source rows do not increase strictly.")
    step = float(np.median(dt))
    grid = np.rint(dt / step)
    require(np.all(grid >= 1) and np.all(np.abs(dt - grid * step) <= TOL_TIME),
            "Tracking times depart from the local nominal interval by a non-integer multiple.")
    segment = np.r_[0, np.cumsum(grid != 1)].astype("<i8")
    n = len(t)
    length = vector(m[length_name], length_name, n)
    pa = vector(m[angle_name], angle_name, n)
    length_err = float(np.max(np.abs(length - a[:, 1])))
    require(length_err == 0, f"Native first-track length does not match {length_name}: {length_err}")
    identity = {"length": f"{length_name} = {pair[0]}.data(:,2)",
                "maximum_absolute_residual_mm": length_err}
    if pair == ("A", "B"):
        errors = {"plus": float(np.max(np.abs(pa - np.rad2deg(a[:, 2] + b[:, 2])))),
                  "minus": float(np.max(np.abs(pa - np.rad2deg(a[:, 2] - b[:, 2]))))}
        valid = [name for name, error in errors.items() if error <= TOL_ANGLE]
        require(len(valid) == 1, f"One signed decomposition of the source PA is required; errors {errors}.")
        sign = "+" if valid[0] == "plus" else "-"
        identity.update(angle=f"{angle_name} = rad2deg(A.data(:,3) {sign} B.data(:,3))",
                        source_angle_decomposition_errors_deg=errors, maximum_absolute_residual_deg=errors[valid[0]])
    else:
        extra = {}
        if len(pair) == 2:
            other_length = vector(m["fascicle_length2"], "fascicle_length2", n)
            other_pa = vector(m["PA2"], "PA2", n)
            require(np.array_equal(other_length, b[:, 1]), "Second track and numbered length disagree.")
            shared_term_error = float(np.max(np.abs(pa - other_pa - np.rad2deg(a[:, 2] - b[:, 2]))))
            require(shared_term_error < TOL_ANGLE, "The two native fascicles do not reproduce the common orientation term.")
            extra = {"FL": other_length, "PA": other_pa}
            identity["common_orientation_difference_residual_deg"] = shared_term_error
        first_track_errors = {}
        for label, first in (("PA", pa), ("FL", length)):
            curve = vector(m[label], label, 10 * (n - 1))
            if label in extra:
                first_track_errors[label] = reconstruction_errors(curve, first, extra[label])
            else:
                expanded = np.interp(np.arange(len(curve)) / 10, np.arange(n), first)
                first_track_errors[label] = {"first": float(np.max(np.abs(curve - expanded)))}
            require(first_track_errors[label]["first"] < TOL_ANGLE, f"Published {label} does not reproduce track 1.")
        identity.update(angle="PA1 is the first tracked fascicle's source angle. Published PA reproduces it by tenfold linear interpolation.",
                        reference_orientation="Separate orientation of the reference sheet is unavailable.",
                        dense_field_reconstruction_max_errors=first_track_errors)
    if n >= 9000:
        interpolation = {"length_mm": interpolation_test(length), "angle_deg": interpolation_test(pa)}
        require(interpolation["length_mm"] > 2e-6 and interpolation["angle_deg"] > np.rad2deg(2e-6),
                f"The long native tables may be rounded tenfold interpolations: {interpolation}")
        identity["smallest_max_error_of_ten_possible_interpolation_phases"] = interpolation
    out = {"length_mm": length, "angle_deg": pa, "tracking_row": np.arange(1, n + 1, dtype="<i8"),
           "tracker_time": t, "segment_id": segment}
    details = {"variables_requested": fields, "tables": tables,
               "exports": {name: list(m[name].shape) for name in fields[len(pair):]},
               "n": n, "paired_time_labels_exact": True if len(pair) == 2 else None, "chronology": "Source row order, strictly increasing TIME.",
               "tracker_time": {"first": float(t[0]), "last": float(t[-1]), "nominal_step": float(round(step, 12)),
                                "min_step": float(dt.min()), "max_step": float(dt.max()),
                                "discontinuities_before_one_based_row": (np.flatnonzero(grid != 1) + 2).tolist(),
                                "interpretation": "Original tracking TIME label. Physical acquisition time unverified."},
               "frame_identity": ("Matching TIME in both native tables." if len(pair) == 2 else "One native TIME-labelled tracker table. Cross-table comparison is unavailable.") + " tracking_row is the one-based source ordinal. Independent acquisition frame numbers are absent.",
               "units": {"length_mm": "Source length export in study Table 3 units (millimetres).",
                         "angle_deg": "Source pennation export in degrees; Table 3 and member-specific orientation/curve identities.",
                         "calibration": "Released UltraTrack units only. Independent physical phantom or participant-specific scale verification is unavailable."},
               "identity": identity,
               "array_sha256": {k: hashlib.sha256(np.asarray(v, dtype=v.dtype.newbyteorder("<")).tobytes()).hexdigest() for k, v in out.items()},
               "array_hash_encoding": "One-dimensional little-endian float64 or int64 C-order bytes, excluding headers."}
    return out, details


def process(person, trial, dest, reuse, expected):
    base = dest / person / f"trial-{trial}"
    mat, orig = obtain(person, trial, base, reuse)
    if expected:
        ref = expected[(person, trial)]
        require(orig["sha256"] == ref["sha256"] and orig["bytes"] == ref["bytes"], "Original differs from manifest.")
    npz = base.with_suffix(".knots.npz")
    receipt = base.with_suffix(".source.json")
    common = {**orig, "dataset": "10.6019/S-BIAD1482", "data_licence": "CC BY 4.0",
              "article": "10.1038/s41597-024-04285-x", "program_sha256": sha(Path(__file__)),
              "schema_version": 2}
    try:
        out, details = qualify(mat)
    except SchemaError as exc:
        require(not npz.exists(), "An earlier derivative already exists for this unsupported schema.")
        atomic_json(receipt, {**common, "qualified": False, "reason": str(exc)})
        print(f"{person} {trial}: unsupported: {exc}", flush=True)
        return False
    if expected:
        require(details["array_sha256"] == ref["array_sha256"], "Knot arrays differ from manifest.")
    with tempfile.NamedTemporaryFile(dir=base.parent, delete=False) as f:
        np.savez(f, **out)
    os.replace(f.name, npz)
    atomic_json(receipt, {**common, **details, "qualified": True, "npz_sha256": sha(npz)})
    print(f"{person} {trial}: qualified {details['n']} source rows", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=PHASES)
    parser.add_argument("--cache", type=Path, default=Path(".cache/fascicle-study"))
    parser.add_argument("--person", help="Restrict the named phase to one of its prespecified people.")
    parser.add_argument("--trial", type=int, choices=[1, 2])
    parser.add_argument("--reuse-pilot", type=Path, help="Exact previously acquired A01 trial 1 file.")
    parser.add_argument("--manifest", type=Path, help="Verify original and numeric SHA256 against this published manifest.")
    args = parser.parse_args()
    people = PHASES[args.phase]
    if args.person:
        if args.person not in people:
            parser.error("Person outside the selected phase.")
        people = (args.person,)
    entries = {}
    if args.manifest:
        entries = {(r["person"], r["trial"]): r for r in json.loads(args.manifest.read_text())["members"]}
    outcomes = [process(p, trial, args.cache, args.reuse_pilot, entries) for p in people
                for trial in ([args.trial] if args.trial else [1, 2])]
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
