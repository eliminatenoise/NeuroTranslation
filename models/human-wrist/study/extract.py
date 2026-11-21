"""Select annotated right-wrist events from NWB metadata, then copy earlier or future values."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import zlib

import h5py
import numpy as np

from archive import ASSETS, Source
from chunk_index import require, root_address, lookup

CONTACTS = [0, 9, 18, 27, 36, 45, 54, 63]
JOINTS = ["R_Wrist", "R_Elbow", "R_Shoulder", "L_Wrist", "L_Elbow", "L_Shoulder"]
ELECTRIC = "acquisition/ElectricalSeries"
STREAMS = [ELECTRIC] + ["processing/behavior/Position/" + j for j in JOINTS]
ALLOWED = {
    "talk",
    "talking",
    "tv",
    "watch tv",
    "watching tv",
    "computer",
    "phone",
    "computer/phone",
    "eat",
    "eating",
    "other activity",
    "active",
    "inactive",
}


def allowed(label):
    return all(
        part.strip().lower() in ALLOWED
        for part in label.replace("|", ";").replace(",", ";").split(";")
    )


def select(h, day):
    origins = [h[k].asstr()[()] for k in ("session_start_time", "timestamps_reference_time")]
    start = datetime.fromisoformat(origins[0]).astimezone(timezone.utc)
    require(
        origins[0] == origins[1] and start.time().isoformat() == "00:00:00",
        "Unsupported NWB clock origin",
    )
    require(
        hashlib.sha256(h["identifier"][()]).hexdigest()
        == ASSETS[str(day)]["nwb_identifier_sha256"],
        "Unexpected NWB recording identifier",
    )
    events = h["processing/behavior/ReachEvents"]
    require(
        events.attrs["description"].lower() == "r_wrist"
        and events["timestamps"].attrs["resolution"] == 0.002,
        "Unexpected event definition",
    )
    times = events["timestamps"][:]
    paired = h["intervals/reaches/start_time"][:]
    ep = h["intervals/epochs"]
    labels, starts, ends = ep["labels"].asstr()[:], ep["start_time"][:], ep["stop_time"][:]
    require(len(times) == len(paired), "Unequal independent event clocks")
    limit = 16 * 3600 if day == 3 else 24 * 3600
    rows = []
    strata = [0] * 6
    for t, i in sorted((float(t), i) for i, t in enumerate(times) if np.isfinite(t)):
        if (
            not 0.5 <= t < limit - 0.5
            or not np.isfinite(paired[i])
            or abs(t - paired[i]) > 0.002 + 1e-10
        ):
            continue
        lo, hi, block = t - 0.5, t + 0.5, int(t // 120)
        if (
            lo < 120 * block
            or hi > 120 * (block + 1)
            or (rows and (rows[-1][2] == block or t - rows[-1][1] < 30))
        ):
            continue
        hits = sorted(np.flatnonzero((starts < hi) & (ends > lo)), key=lambda j: starts[j])
        if not hits or not all(allowed(labels[j]) for j in hits):
            continue
        cover = lo
        for j in hits:
            if starts[j] > cover:
                break
            cover = max(cover, ends[j])
        if cover < hi:
            continue
        s = int(t // 14400)
        if day == 4 and strata[s] >= 12:
            continue
        ec, pose = [
            int((Decimal(str(t)) * hz).to_integral_value(rounding=ROUND_CEILING))
            for hz in (500, 30)
        ]
        if day == 3 and (
            ((ec - 1) // 84375 + 1) * 84375 > limit * 500
            or ((pose + 14) // 5063 + 1) * 5063 > limit * 30
        ):
            continue
        rows.append((i, t, block, ec, pose))
        strata[s] += 1
    require(
        len(rows) == (60 if day == 3 else 58), "Frozen source selection does not match this asset"
    )
    return rows


def montage(h):
    region = h[ELECTRIC + "/electrodes"]
    table = h[region.attrs["table"]]
    rows = region[:]
    group = table["group_name"].asstr()[:][rows]
    require(
        table.name == "/general/extracellular_ephys/electrodes"
        and np.array_equal(np.flatnonzero(group == "GRID"), np.arange(64))
        and np.array_equal(rows[CONTACTS], CONTACTS)
        and np.array_equal(table["id"][:][rows][CONTACTS], CONTACTS),
        "Unexpected electrode region, ID or group",
    )
    keys = ("x", "y", "z", "good")
    return [
        hashlib.sha256(np.ascontiguousarray(table[k][:][rows][CONTACTS]).tobytes()).hexdigest()
        for k in keys
    ]


def materialize(day, stage, path, private, cap_mib, workers):
    with Source(day, path, private, cap_mib) as src, h5py.File(src, "r") as h:
        rows = select(h, day)
        contact_hashes = montage(h)
        n = len(rows)
        out = dict(
            native_event_row=np.array([r[0] for r in rows], dtype="<i8"),
            onset_s=np.array([r[1] for r in rows], dtype="<f8"),
            source_block=np.array([r[2] for r in rows], dtype="<i8"),
        )
        if stage in ("train", "inputs"):
            out.update(
                ecog_uv=np.empty((n, 250, 8), "<f4"),
                prior_pose_px=np.empty((n, 15, 6, 2), "<f8"),
                electrode_id=np.array(CONTACTS, dtype="<i8"),
                region_table_row=np.array(CONTACTS, dtype="<i8"),
            )
        if stage in ("train", "targets"):
            out["future_wrist_px"] = np.empty((n, 2, 2, 2), "<f8")
        jobs = defaultdict(list)
        chunks = {}
        for stream_id, name in enumerate(STREAMS):
            is_voltage = stream_id == 0
            w = 84375 if is_voltage else 5063
            ds = h[name + "/data"]
            clk = h[name + "/starting_time"]
            dtype = np.dtype("<f4" if is_voltage else "<f8")
            require(
                ds.dtype == dtype
                and ds.chunks == (w, 1)
                and ds.compression == "gzip"
                and ds.shape == ((43200000, 94) if is_voltage else (2592000, 2))
                and ds.compression_opts == 4
                and ds.id.get_create_plist().get_nfilters() == 1
                and clk[()] == 0
                and clk.attrs["rate"] == (500 if is_voltage else 30)
                and clk.attrs["unit"] == "seconds"
                and ds.attrs.get("offset", 0) == 0
                and (
                    ds.attrs["unit"] == "volts" and ds.attrs["conversion"] == 1e-6
                    if is_voltage
                    else ds.attrs["unit"] == "meters" and np.isnan(ds.attrs["conversion"])
                ),
                "Unexpected NWB series encoding",
            )
            root = root_address(src, ds)
            cols = CONTACTS if is_voltage else [0, 1]

            def plan(a, b, dest):
                for base in range(a // w * w, b, w):
                    lo, hi = max(a, base), min(b, base + w)
                    for j, col in enumerate(cols):
                        key = (stream_id, base, col)
                        if key not in chunks:
                            addr, size = lookup(src, root, base, col)
                            require(
                                0 < size <= w * dtype.itemsize + 1024,
                                "Unexpected compressed length",
                            )
                            chunks[key] = (addr, size, w, dtype)
                        jobs[key].append((lo - base, hi - lo, dest[lo - a : hi - a, j]))

            for i, (_, _, _, ie, ip) in enumerate(rows):
                if stage != "targets":
                    if is_voltage:
                        plan(ie - 250, ie, out["ecog_uv"][i])
                    else:
                        plan(ip - 15, ip, out["prior_pose_px"][i, :, stream_id - 1])
                if stage != "inputs" and stream_id in (1, 4):
                    for j, frame in enumerate((ip + 7, ip + 14)):
                        plan(
                            frame,
                            frame + 1,
                            out["future_wrist_px"][i, j : j + 1, (stream_id - 1) // 3],
                        )

        def copy(key):
            addr, size, width, dtype = chunks[key]
            decompressor = zlib.decompressobj()
            raw = decompressor.decompress(src.fetch(addr, addr + size), width * dtype.itemsize + 1)
            require(
                len(raw) == width * dtype.itemsize
                and decompressor.eof
                and not decompressor.unused_data
                and not decompressor.unconsumed_tail,
                "Invalid native gzip chunk",
            )
            view = np.frombuffer(raw, dtype=dtype)
            for pos, count, dest in jobs[key]:
                dest[:] = view[pos : pos + count]

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for _ in pool.map(copy, jobs):
                pass
    return out, contact_hashes
