"""Build a private, input-only EEG cache from two development-only archival cohorts."""

import argparse
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from scipy.io import loadmat

KEYS = (
    "person",
    "domain",
    "session",
    "event",
    "direction",
    "block",
    "cutoff",
    "cutoff_s",
)
WAY = ["C3", "Cz", "C4", "FC1", "FC2", "CP1", "CP2", "Fp1", "Fp2"]
BANKS = [f"{b}{i}" for b in "ABCD" for i in range(1, 33)]
CONTROLS = [
    "L_neck_emg",
    "R_neck_emg",
    "R_horizontal_eog",
    "L_horizontal_eog",
    "L_vertical_eog",
]
ARMS = [
    "Anterior Deltoid",
    "Brachoradial",
    "Flexor Digitorum",
    "Common Extensor Digitorum",
    "First Dorsal Interosseus",
]
TASKS = ("rotatestand", "rotatewalk")
COHORT = "a11706a31bb049fcd84c81264cfbdc5497205602ceb67c0f7a69fbbf906f7590"
WAY_CAT = "44888d8fadf479edab3a97176b76340512ba030ae04acbcfe0162ccb33a5b977"
BALANCE_FILES = "4ba83d6e8588f70074511f04f85fe1c3d739d499f54c22b95ac944737e1d0cc3"
COMMIT = "f15449b6aecb83044b49a1798955e8a212a68fc1"
TOL = 1e-8
MISSING, SOURCE_BAD, NONFINITE, FLAT = 1, 2, 4, 8


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bound(path, expected):
    require(digest(path) == expected, f"changed source {path.name}")
    return path


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def table(text):
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def geometry(rate):
    # A 32 kHz common integer grid represents the two rates and every requested edge.
    tick = 32000 // rate
    guard = 64 if rate == 500 else 0
    offsets = np.arange(-math.ceil(0.625 * rate), 1)
    ticks = offsets * tick
    support = offsets[(ticks > -20000 + guard) & (ticks <= -guard)]
    bins = []
    for left in range(-20000, 0, 1000):
        bins.append(
            np.flatnonzero(
                (support * tick > left + guard)
                & (support * tick <= left + 1000 - guard)
            )
        )
    counts = np.array([len(b) for b in bins])
    first = support[[b[0] for b in bins]]
    last = support[[b[-1] for b in bins]]
    return support, np.concatenate(bins), counts, first, last


def summarize(raw, base_reason, columns, rate, geo):
    # raw contains observed values only for present, source-admitted columns.
    support, take, counts, _, _ = geo
    reason = base_reason.copy()
    require(raw.shape == (len(support), len(columns)), "unexpected history shape")
    if len(columns):
        nonfinite = ~np.isfinite(raw).all(axis=0)
        different = raw[1:] != raw[:-1]
        steps = np.arange(1, len(raw))[:, None]
        latest_change = np.maximum.accumulate(np.where(different, steps, 0), axis=0)
        constant = np.any(steps - latest_change >= math.ceil(0.125 * rate), axis=0)
        reason[columns] |= (
            nonfinite.astype(np.uint8) * NONFINITE | constant.astype(np.uint8) * FLAT
        )
    good = reason == 0
    usable = good[columns]
    mean = np.zeros((20, len(reason)), dtype=np.float32)
    rms = np.zeros_like(mean)
    if usable.any():
        hist = raw[take][:, usable].astype(np.float64)
        starts = np.r_[0, np.cumsum(counts)[:-1]]
        mean[:, good] = np.add.reduceat(hist, starts, axis=0) / counts[:, None]
        rms[:, good] = np.sqrt(
            np.add.reduceat(hist * hist, starts, axis=0) / counts[:, None]
        )
    require(np.isfinite(mean).all() and np.isfinite(rms).all(), "float32 cache range")
    return mean, rms, reason


def columns_for(selected, names, accepted):
    reason = np.array(
        [
            MISSING
            if s not in names
            else SOURCE_BAD
            if names.index(s) not in accepted
            else 0
            for s in selected
        ],
        dtype="u1",
    )
    columns = np.flatnonzero(reason == 0)
    return reason, columns, [names.index(selected[j]) for j in columns]


def init(keys, domain, names, geo):
    rows = np.flatnonzero(keys["domain"] == domain)
    n = len(rows)
    return {
        "rows": rows,
        "names": np.asarray(names),
        "mean": np.zeros((n, 20, len(names)), dtype="f4"),
        "rms": np.zeros((n, 20, len(names)), dtype="f4"),
        "reason": np.zeros((n, len(names)), dtype="u1"),
        "bin_samples": geo[2],
        "bin_first_offset": geo[3],
        "bin_last_offset": geo[4],
        "source_ordinal": np.zeros(n, dtype="i4"),
        "source_session": np.zeros(n, dtype="i4"),
        "source_anchor": np.zeros(n, dtype="i8"),
        "latest_minus_cutoff_s": np.zeros(n),
        "source_issue_s": np.zeros(n),
        "original_event_tick": np.zeros(n),
    }


def index_rows(keys, store):
    return {
        (str(keys["person"][i]), int(keys["session"][i]), int(keys["event"][i])): j
        for j, i in enumerate(store["rows"])
    }


def way_data(paths, keys, audit):
    geo = geometry(500)
    store = init(keys, 1, WAY, geo)
    addr = index_rows(keys, store)
    cat = json.loads(bound(paths.way_catalogue, WAY_CAT).read_bytes())
    people = cat["stages"]["development"]
    require(len(set(people)) == len(people) == 6, "development roster")
    seen = set()
    for p in people:
        spec = cat["archives"][str(p)]
        z = bound(paths.way / f"P{p}.zip", spec["sha256"])
        require(z.stat().st_size == spec["bytes"], "WAY archive size")
        with zipfile.ZipFile(z) as pkg:
            members = [
                a
                for a in pkg.infolist()
                if re.fullmatch(rf"WS_P{p}_S\d+\.mat", Path(a.filename).name)
            ]
            info = {Path(a.filename).name: a for a in members}
            require(len(info) == len(members) == 9, "numbered WAY members")
            for src in spec["members"]:
                s = src["series"]
                member = info[src["filename"]]
                raw = pkg.read(member)
                require(
                    member.file_size == src["bytes"]
                    and hashlib.sha256(raw).hexdigest() == src["sha256"],
                    "WAY member",
                )
                ws = loadmat(
                    io.BytesIO(raw), variable_names=["ws"], simplify_cells=True
                )["ws"]
                del raw
                labels = list(ws["names"]["eeg"])
                require(
                    len(labels) == len(set(labels)) == 32
                    and (ws["participant"], ws["series"]) == (p, s),
                    "WAY recording identity",
                )
                require(
                    list(ws["names"]["emg"]) == ARMS
                    and [ws["names"]["kin"][i] for i in (21, 25, 29)]
                    == [f"P{a}4 - position {a} sensor 4" for a in "xyz"],
                    "WAY paired stream identity",
                )
                reason, columns, source = columns_for(
                    WAY, labels, set(range(len(labels)))
                )
                wins = ws["win"]
                require(len(wins) == src["trial_count"], "WAY count")
                audit["way_members"].append(
                    {
                        "person": p,
                        "session": s,
                        "design": src["design"],
                        "original": len(wins),
                        "archive_sha256": spec["sha256"],
                        "member": src["filename"],
                        "sha256": src["sha256"],
                        "labels": labels,
                        "absent": [WAY[j] for j in np.flatnonzero(reason)],
                    }
                )
                for event, trial in enumerate(wins, 1):
                    key = (f"way:P{p:02d}", s, event)
                    if key not in addr:
                        continue
                    j = addr[key]
                    i = store["rows"][j]
                    cue = float(trial["LEDon"])
                    issue = cue + 0.4
                    grid = trial["eeg_t"]
                    # Search by documented cadence from the first local timestamp; no post-cutoff signal access.
                    k = round((issue - float(grid[0])) * 500)
                    require(
                        k + geo[0][0] >= 0
                        and k < len(grid)
                        and abs(float(grid[k]) - issue) < TOL
                        and abs(float(grid[k - 200]) - cue) < TOL
                        and np.max(abs(grid[k + geo[0]] - issue - geo[0] / 500)) < TOL,
                        "WAY trial clock",
                    )
                    absolute = float(trial["trial_start_time"]) + issue
                    require(
                        abs(absolute - keys["cutoff_s"][i]) < TOL
                        and round(absolute * 500) == keys["cutoff"][i]
                        and keys["direction"][i] == 0
                        and min(2, 3 * (event - 1) // len(wins)) == keys["block"][i],
                        "WAY joint row anchor",
                    )
                    require(
                        trial["eeg"].shape == (len(grid), len(labels))
                        and trial["kin"].shape == (len(grid), 45)
                        and trial["emg"].shape == (len(trial["emg_t"]), 5),
                        "WAY stream shape",
                    )
                    # Confirm the 4 kHz stream uses the same stored issue event, without reading EMG samples.
                    e = round((issue - float(trial["emg_t"][0])) * 4000)
                    require(
                        0 <= e < len(trial["emg_t"])
                        and abs(float(trial["emg_t"][e]) - issue) < TOL,
                        "WAY electrical issue mismatch",
                    )
                    y = trial["eeg"][np.ix_(k + geo[0], source)]
                    store["mean"][j], store["rms"][j], store["reason"][j] = summarize(
                        y, reason, columns, 500, geo
                    )
                    store["source_ordinal"][j], store["source_session"][j] = event, s
                    store["source_anchor"][j], store["source_issue_s"][j] = k, issue
                    store["original_event_tick"][j] = cue * 500
                    store["latest_minus_cutoff_s"][j] = (
                        float(grid[k + geo[4][-1]]) - issue
                    )
                    seen.add(j)
    require(
        len(seen) == len(addr) == len(store["rows"]), "WAY lost or duplicated groups"
    )
    store["good"] = store["reason"] == 0
    return store


def git_source(catalogue, name):
    data = subprocess.check_output(
        ["git", "-C", str(catalogue), "show", f"{COMMIT}:{name}"]
    )
    return data, hashlib.sha256(data).hexdigest()


def coords(catalogue, prefix, channels, eeg):
    t, ts = git_source(catalogue, prefix + "electrodes.tsv")
    doc, ds = git_source(catalogue, prefix + "coordsystem.json")
    entries = table(t.decode("utf-8-sig"))
    bylabel = {row["name"]: row for row in entries}
    meta = json.loads(doc)
    require(len(bylabel) == len(entries), "duplicate native coordinates")
    matches, missing, disagreed = 0, [], []
    standard = sorted(set(WAY) & set(bylabel))
    for c in eeg["chanlocs"]:
        if c["labels"] not in BANKS:
            continue
        label = c["labels"]
        if label not in bylabel or any(bylabel[label][a] == "n/a" for a in "xyz"):
            missing.append(label)
            continue
        try:
            values = np.array([c[a] for a in "XYZ"], dtype=float)
            xyz = np.array([bylabel[label][a] for a in "xyz"], dtype=float)
        except (TypeError, ValueError):
            disagreed.append(label)
            continue
        if values.shape == (3,) and np.max(abs(xyz - values)) <= 0.0050001:
            matches += 1
        else:
            disagreed.append(label)
    has = eeg.get("chaninfo", {}).get("filecontent", [])
    native_file_labels = [
        str(l).split()[0] for l in np.atleast_1d(has) if str(l).strip()
    ]
    cap = eeg["etc"].get("desc", {}).get("cap", {})
    return {
        "electrode_table_sha256": ts,
        "coordinate_metadata_sha256": ds,
        "metadata": meta,
        "electrode_fields": list(entries[0]),
        "scheme": str(cap.get("labelscheme", "unspecified")),
        "channel_table_literal_name_overlap": sorted(set(WAY) & set(channels)),
        "electrode_table_literal_name_overlap": standard,
        "embedded_location_file_literal_name_overlap": sorted(
            set(WAY) & set(native_file_labels)
        ),
        "table_and_header_same_numeric_XYZ_within_table_rounding": matches,
        "coordinates_missing": missing,
        "coordinates_disagree": disagreed,
    }


def balance_data(paths, keys, audit):
    geo = geometry(256)
    selected = BANKS + CONTROLS
    store = init(keys, 0, selected, geo)
    addr = index_rows(keys, store)
    receipt = json.loads(
        bound(paths.balance / "development-files.json", BALANCE_FILES).read_bytes()
    )
    require(
        receipt["stage"] == "development"
        and receipt["commit"] == COMMIT
        and len(receipt["selected"]) == 18
        and not receipt["catalogue_omissions"],
        "balance stage",
    )
    catalogue = paths.balance / "catalogue"
    files = receipt["files"]
    seen = set()
    for p in receipt["selected"]:
        for posture, task in enumerate(TASKS):
            match = [
                k
                for k in files
                if k.startswith(p + "/")
                and f"_task-{task}_" in k
                and k.endswith("_eeg.fdt")
            ]
            require(len(match) == 1, "ambiguous balance run")
            prefix = match[0][: -len("eeg.fdt")]
            native_session = int(re.search(r"/ses-(\d+)/", prefix)[1])
            paths_in = {}
            for suffix in (
                "eeg.fdt",
                "eeg.set",
                "channels.tsv",
                "eeg.json",
                "events.tsv",
                "events.json",
            ):
                k = prefix + suffix
                f = bound(paths.balance / "raw" / k, files[k]["sha256"])
                require(f.stat().st_size == files[k]["bytes"], "balance file size")
                paths_in[suffix] = f
            table_ch = table(paths_in["channels.tsv"].read_text(encoding="utf-8-sig"))
            side = json.loads(paths_in["eeg.json"].read_bytes())
            ee = loadmat(paths_in["eeg.set"], simplify_cells=True)
            eeg = ee.get("EEG", ee)
            names = [r["name"] for r in table_ch]
            n, ch = int(eeg["pnts"]), int(eeg["nbchan"])
            require(
                len(names) == ch == len(set(names))
                and eeg["trials"] == 1
                and eeg["data"] == paths_in["eeg.fdt"].name
                and paths_in["eeg.fdt"].stat().st_size == n * ch * 4
                and eeg["srate"] == side["SamplingFrequency"] == 256
                and abs(side["RecordingDuration"] - n / 256) < TOL
                and np.max(abs(eeg["times"] - np.arange(n) * (1000 / 256))) < TOL,
                "balance clock and size",
            )
            require(
                [(c["labels"], c["type"], c["units"]) for c in eeg["chanlocs"]]
                == [(r["name"], r["type"], r["units"]) for r in table_ch],
                "balance identities",
            )
            for label in selected:
                if label in names:
                    kind = (
                        "EEG"
                        if label in BANKS
                        else ("EMG" if label.endswith("_emg") else "EOG")
                    )
                    require(
                        table_ch[names.index(label)]["type"] == kind
                        and table_ch[names.index(label)]["units"] == "microV",
                        "balance type/unit",
                    )
            ids = np.atleast_1d(eeg["etc"]["good_chans"])
            require(
                np.isfinite(ids).all()
                and (np.floor(ids) == ids).all()
                and len(set(ids)) == len(ids)
                and ids.min() >= 1
                and ids.max() <= ch,
                "balance author mask",
            )
            reason, columns, source = columns_for(
                selected, names, set(ids.astype(int) - 1)
            )
            data = np.memmap(paths_in["eeg.fdt"], mode="r", dtype="<f4", shape=(n, ch))
            events_meta = json.loads(paths_in["events.json"].read_bytes())
            require(events_meta["onset"]["Units"] == "second", "balance onset unit")
            bids = [
                r
                for r in table(paths_in["events.tsv"].read_text(encoding="utf-8-sig"))
                if r["value"] in ("rotate_cw", "rotate_ccw")
            ]
            set_events = [
                r
                for r in eeg["event"]
                if str(r["type"]).startswith(("M_on_CW_", "M_on_CCW_"))
            ]
            require(len(bids) == len(set_events), "rotation count")
            coord = coords(catalogue, prefix, names, eeg)
            qc = {
                "person": p,
                "task": task,
                "source_session": native_session,
                "original": len(bids),
                "reference": side["EEGReference"],
                "software_filters": side["SoftwareFilters"],
                "missing": [selected[k] for k in np.flatnonzero(reason & MISSING)],
                "author_bad": [
                    selected[k] for k in np.flatnonzero(reason & SOURCE_BAD)
                ],
                "source_sha256": {s: files[prefix + s]["sha256"] for s in paths_in},
                "coords": coord,
                "accepted_clock_max_error_samples": 0.0,
                "received_rows": 0,
            }
            for event, (b, ev) in enumerate(zip(bids, set_events, strict=True), 1):
                key = (f"balance:{p}", posture, event)
                if key not in addr:
                    continue
                j = addr[key]
                i = store["rows"][j]
                d = 1 if b["value"] == "rotate_cw" else -1
                code = (
                    "M_on_"
                    + ("CW" if d == 1 else "CCW")
                    + ("_WVZ" if posture else "_SVZ")
                )
                tick, st, on = (
                    float(b["sample"]),
                    float(ev["latency"]) - 1,
                    float(b["onset"]) * 256,
                )
                err = max(abs(tick - st), abs(tick - on))
                c = math.ceil(tick) + 32
                u = int(ev["urevent"]) - 1
                require(
                    st >= 0
                    and 0 <= u < len(eeg["urevent"])
                    and ev["type"] == eeg["urevent"][u]["type"] == code
                    and b["trial_type"] == "stimulus"
                    and float(b["duration"]) == 0.5
                    and err <= 0.01
                    and math.ceil(tick) == math.ceil(st) == math.ceil(on)
                    and c == keys["cutoff"][i]
                    and abs(c / 256 - keys["cutoff_s"][i]) < TOL
                    and d == keys["direction"][i]
                    and keys["block"][i] == min(2, 3 * (event - 1) // len(bids)),
                    "balance event or joint anchor",
                )
                require(c + geo[0][0] >= 0 and c < n, "balance history bounds")
                y = data[np.ix_(c + geo[0], source)]
                store["mean"][j], store["rms"][j], store["reason"][j] = summarize(
                    y, reason, columns, 256, geo
                )
                store["source_session"][j], store["source_ordinal"][j] = (
                    native_session,
                    event,
                )
                (
                    store["source_anchor"][j],
                    store["source_issue_s"][j],
                    store["original_event_tick"][j],
                ) = c, c / 256, tick
                qc["accepted_clock_max_error_samples"] = max(
                    qc["accepted_clock_max_error_samples"], err
                )
                qc["received_rows"] += 1
                seen.add(j)
            audit["balance_sessions"].append(qc)
    require(
        len(seen) == len(addr) == len(store["rows"]), "balance lost or duplicate groups"
    )
    store["good"] = store["reason"] == 0
    return store


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("cohort", "balance", "way", "way-catalogue", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument(
        "--jobs",
        type=int,
        choices=(1, 2),
        default=1,
        help="Simultaneous source readers",
    )
    paths = ap.parse_args()
    with np.load(bound(paths.cohort, COHORT), allow_pickle=False) as z:
        keys = {k: z[k] for k in KEYS}
    require(
        len(set(zip(keys["person"], keys["session"], keys["event"], strict=True)))
        == len(keys["person"])
        and np.array_equal(np.unique(keys["domain"]), [0, 1]),
        "duplicate or incorrect joint groups",
    )
    audit = {"way_members": [], "balance_sessions": []}
    out = dict(keys)
    with ThreadPoolExecutor(max_workers=paths.jobs) as pool:
        readers = {
            "way": pool.submit(way_data, paths, keys, audit),
            "balance": pool.submit(balance_data, paths, keys, audit),
        }
        for name, reader in readers.items():
            for k, v in reader.result().items():
                out[name + "_" + k] = v
    paths.out.mkdir(parents=True, exist_ok=True)
    tmp = paths.out / "development.partial.npz"
    np.savez_compressed(tmp, **out)
    tmp.replace(paths.out / "development.npz")
    dump(paths.out / "source-audit.json", audit)


if __name__ == "__main__":
    main()
