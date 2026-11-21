"""Join past scalp voltage to the original qualified balance records on a single clock."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

PROTOCOL = json.loads(Path(__file__).with_name("protocol.json").read_bytes())
SITES = ("D19", "A1", "B22")
TASKS = ("rotatestand", "rotatewalk")
LAGS = np.array([8, 16, 32, 64])
FIELDS = ("person", "event", "posture", "direction", "block", "cutoff")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()


def typed_digest(archive):
    h = hashlib.sha256()
    for key in sorted(archive.files):
        x = archive[key]
        dtype = x.dtype.newbyteorder("<")
        h.update(canonical([key, dtype.str, list(x.shape)]) + b"\n")
        h.update(x.astype(dtype, copy=False).tobytes(order="C"))
    return h.hexdigest()


def table(file):
    with file.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_session(source, receipt, person, posture):
    task = TASKS[posture]
    manifest = receipt["files"]
    matches = [key for key in manifest if key.startswith(person + "/") and
               f"_task-{task}_" in key and key.endswith("eeg.fdt")]
    check(len(matches) == 1, "ambiguous posture session")
    prefix = matches[0][:-len("eeg.fdt")]
    files = {}
    for suffix in ("eeg.set", "eeg.fdt", "channels.tsv", "events.tsv", "eeg.json"):
        key = prefix + suffix
        path = source / "raw" / key
        with path.open("rb") as f:
            check(hashlib.file_digest(f, "sha256").hexdigest() == manifest[key]["sha256"],
                  "original recording file differs")
        files[suffix] = path
    header = loadmat(files["eeg.set"], simplify_cells=True)
    header = header.get("EEG", header)
    rows = table(files["channels.tsv"])
    sidecar = json.loads(files["eeg.json"].read_bytes())
    check(header["srate"] == sidecar["SamplingFrequency"] == 256 and header["trials"] == 1,
          "source clock")
    names = [r["name"] for r in rows]
    check(len(set(names)) == len(names) == header["nbchan"] and
          [(r["name"], r["type"], r["units"]) for r in rows] ==
          [(r["labels"], r["type"], r["units"]) for r in header["chanlocs"]], "channel identity")
    good = set(np.asarray(header["etc"]["good_chans"], dtype=int) - 1)
    sites = []
    for name in SITES:
        index = names.index(name) if name in names else -1
        if index >= 0:
            check((rows[index]["type"], rows[index]["units"]) == ("EEG", "microV"), "scalp units")
        sites.append(index if index in good else -1)
    n, ch = int(header["pnts"]), len(names)
    check(header["data"] == files["eeg.fdt"].name and files["eeg.fdt"].stat().st_size == n*ch*4,
          "FDT geometry")
    data = np.memmap(files["eeg.fdt"], dtype="<f4", mode="r", shape=(n, ch))
    rotations = [e for e in table(files["events.tsv"]) if e["value"] in ("rotate_cw", "rotate_ccw")]
    original = [e for e in header["event"] if str(e["type"]).startswith(("M_on_CW_", "M_on_CCW_"))]
    check(len(original) == len(rotations), "event count")
    return rotations, original, header["urevent"], sites, data


def prepare(source, stage):
    receipt = json.loads((source / f"{stage}-files.json").read_bytes())
    check(hashlib.sha256(canonical(receipt)).hexdigest() == PROTOCOL["canonical_receipts"][stage],
          "wrong source selection")
    check(receipt["stage"] == stage and len(receipt["selected"]) == {"assessment":6,"development":18}[stage]
          and not receipt["catalogue_omissions"], "participant roster")
    with np.load(source / f"{stage}.npz", allow_pickle=False) as archive:
        check(typed_digest(archive) == PROTOCOL["typed_archives"][stage], "changed source rows")
        a = {key:archive[key] for key in archive.files}
    check(a["paired"].all() and set(a["person"]) == set(receipt["selected"]), "paired cohort")
    check(len(set(zip(*(a[k] for k in ("person", "posture", "event"))))) == len(a["person"]), "duplicate event")
    n = len(a["person"])
    scalp = np.zeros((n, 5, 3, 2))
    present = np.zeros((n, 3), dtype=bool)
    for person in receipt["selected"]:
        for posture in (0, 1):
            rows = np.flatnonzero((a["person"] == person) & (a["posture"] == posture))
            rotations, original, source_events, sites, data = load_session(source, receipt, person, posture)
            for i in rows:
                ordinal = int(a["event"][i])
                ev, native = rotations[ordinal-1], original[ordinal-1]
                direction = 1 if ev["value"] == "rotate_cw" else -1
                code = "M_on_" + ("CW" if direction == 1 else "CCW") + ("_WVZ" if posture else "_SVZ")
                source_idx = int(native["urevent"]) - 1
                check(0 <= source_idx < len(source_events) and native["type"] == source_events[source_idx]["type"] == code
                      and ev["trial_type"] == "stimulus" and float(ev["duration"]) == .5, "source event")
                ticks = np.array([float(ev["sample"]), float(native["latency"])-1, float(ev["onset"])*256])
                cutoff = int(a["cutoff"][i])
                check(max(abs(ticks-ticks[0])) <= .01 and (np.ceil(ticks)+32 == cutoff).all() and
                      int(a["direction"][i]) == direction and
                      int(a["block"][i]) == min(2, 3*(ordinal-1)//len(rotations)), "misaligned inputs")
                for k, site in enumerate(sites):
                    if site < 0:
                        continue
                    trace = data[cutoff-159:cutoff+1, site].astype(np.float64)
                    edges = np.flatnonzero(np.r_[True, np.diff(trace) != 0, True])
                    if not np.isfinite(trace).all() or max(np.diff(edges)) >= 32:
                        continue
                    bins = trace.reshape(5, 32)
                    scalp[i, :, k, 0] = bins.mean(axis=1)
                    scalp[i, :, k, 1] = np.log1p(np.sqrt((bins**2).mean(axis=1)))
                    present[i, k] = True
    pos = a["sacrum_mm"].astype(np.float64)
    check((pos[:, -1] == 0).all(), "sacrum origin")
    muscles = a["leg_uv"].astype(np.float64).reshape(n, 5, 32, 8)
    rms = np.sqrt((muscles**2).mean(axis=2))
    endpoint = (pos[:, -1:, :] - pos[:, -1-LAGS, :]) * (32/LAGS[None, :, None])
    out = {key:a[key] for key in FIELDS}
    out.update(scalp=scalp, present=present, leg=np.log1p(rms), position=pos[:, 7::8, :],
               physics=endpoint, previous_rms=rms[:, -1], y_leg=a["future_rms_uv"],
               y_path=a["future_path_mm"])
    keep = present.any(axis=1)
    out = {key:value[keep] for key,value in out.items()}
    for person in receipt["selected"]:
        rows = out["person"] == person
        check(len(set(zip(out["posture"][rows], out["direction"][rows]))) == 4, "person lost a cell")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("development", "assessment"))
    parser.add_argument("source", type=Path)
    parser.add_argument("private_output", type=Path)
    args = parser.parse_args()
    result = prepare(args.source, args.stage)
    np.savez_compressed(args.private_output, **result)
    print(json.dumps({"rows":len(result["event"]), "people":len(np.unique(result["person"])),
                      "posture_counts":np.bincount(result["posture"]).tolist(),
                      "events_with_each_site":result["present"].sum(axis=0).tolist()}))
