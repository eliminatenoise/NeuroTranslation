"""Reproduce the narrowly selected optical traces. Requires numpy, requests, h5py, HTTP fsspec."""
import argparse
import bz2
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading
import time

import fsspec
import h5py
import numpy as np
import requests

BASE = Path(__file__).resolve().parent
ROSTER = BASE / "roster.json"
SEAL = "363469c9d6c7d81144c172e8ed8a17b5594d90b366c44564d34c5cfb83bb73e5"
ROI_PATH = "processing/ophys/Dff_Z0/DffUnitResponses_Z0"
WORM_URL = "https://wormwideweb.org/activity/api/data/download/atanas_kim_2023-{}/"
LOCAL = threading.local()
WINDOW_S = 180.0
MAX_ROIS = 32


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def session():
    if not hasattr(LOCAL, "http"):
        LOCAL.http = requests.Session()
    return LOCAL.http


def get_worm(entry):
    url = WORM_URL.format(entry["id"])
    with session().get(url, stream=True, timeout=(10, 45)) as res:
        res.raise_for_status()
        compressed = res.raw.read(16 * 1024**2 + 1)
    if len(compressed) > 16 * 1024**2:
        raise ValueError("Unexpected per-animal download size")
    # The author export concatenates separate bzip2 streams.
    pending = compressed
    source = bytearray()
    while pending:
        decoder = bz2.BZ2Decompressor()
        source.extend(decoder.decompress(pending, max_length=80 * 1024**2 - len(source)))
        if not decoder.eof or len(source) >= 80 * 1024**2:
            raise ValueError("Unexpected expanded size")
        pending = decoder.unused_data
    j = json.loads(source)
    m = j["metadata"]
    assert m["uid"] == entry["id"] and m["source_filename"] == entry["source_file"]
    assert m["paper_id"] == "atanas_kim_2023" and m["checksum_h5"] == entry["source_sha256"]
    clock = np.asarray(j["timing"]["timestamp_confocal"], dtype="<f8")
    assert clock.ndim == 1 and len(clock) == j["timing"]["max_t"]
    assert np.isfinite(clock).all() and (np.diff(clock) > 0).all()
    # The export's timestamps and recorded mean interval are in seconds.
    # Some archival acquisitions have a substantial midpoint break. The source
    # rate describes active imaging; the actual timestamps retain every gap.
    assert np.isclose(np.median(np.diff(clock)), j["timing"]["mean_timestep"], atol=0.05)
    clock_zero = float(clock[0])
    elapsed = clock - clock[0]
    take = int(np.searchsorted(elapsed, WINDOW_S, side="left"))
    traces = j["gcamp"]["trace_array_original"]
    k = min(MAX_ROIS, len(traces))
    assert len(traces) == m["n_neuron"] and all(len(v) == len(clock) for v in traces[:k])
    x = np.array([v[:take] for v in traces[:k]], dtype="<f8").T.copy()
    return elapsed[:take], x, {
        "source_url": url, "format": "Authors' per-recording JSON export of HDF5",
        "compressed_sha256": sha(compressed), "compressed_bytes": len(compressed),
        "returned_json_sha256": sha(source), "upstream_h5_sha256_in_export": m["checksum_h5"],
        "response": "gcamp/trace_array_original", "unit": "source fluorescence intensity",
        "clock_source": "timing/timestamp_confocal in seconds",
        "source_start_s": clock_zero, "source_frames": len(clock), "source_rois": len(traces),
        "recorded_mean_interval_s": float(j["timing"]["mean_timestep"]),
    }


def fetch_fish(entry):
    url = entry["source_url"]
    api = "https://api.dandiarchive.org/api/assets/" + entry["asset_id"] + "/"
    native = session().get(api, timeout=25)
    native.raise_for_status()
    a = native.json()
    assert a["digest"]["dandi:sha2-256"] == entry["source_sha256"]
    assert a["contentSize"] == entry["source_bytes"] and url in a["contentUrl"]
    assert a["path"] == entry["source_file"] and a["access"][0]["status"] == "dandi:OpenAccess"
    assert a["wasAttributedTo"][0]["identifier"].split("_")[0] == entry["id"]
    fs = fsspec.filesystem("http", skip_instance_cache=True)
    # Index only HDF5 metadata and the indicator/clock scalar. No acquisition datasets are indexed.
    with fs.open(url, "rb", block_size=16384, cache_type="blockcache",
                 cache_options={"maxblocks": 32}) as reader, h5py.File(reader, "r") as f:
        g = f[ROI_PATH]
        assert g.attrs["description"] == "CaImAn Dff for plane 0"
        assert g.attrs["neurodata_type"] == "RoiResponseSeries"
        ds = g["data"]
        assert ds.chunks is None and ds.compression is None and ds.id.get_offset() is not None
        assert ds.dtype.str == "<f8" and ds.attrs["unit"] == "deltaF/F0"
        assert float(ds.attrs.get("conversion", 1)) == 1 and float(ds.attrs.get("offset", 0)) == 0
        assert g["starting_time"].attrs["unit"] == "seconds" and "timestamps" not in g
        rate = float(g["starting_time"].attrs["rate"])
        start = float(g["starting_time"][()])
        assert np.isfinite(start) and np.isfinite(rate) and rate > 0
        indicator = f["general/optophysiology/Z0_0/indicator"].asstr()[()]
        assert "GCaMP6s" in indicator
        frames, cols = ds.shape
        assert len(g["rois"]) == cols
        offset = int(ds.id.get_offset())
    t = np.arange(frames, dtype="<f8") / rate
    t = t[:np.searchsorted(t, WINDOW_S, side="left")]
    assert len(t) < 1500 and len(t) > 0
    k = min(MAX_ROIS, cols)
    nbytes = k * 8

    def get_row(i):
        first = offset + i * cols * 8
        last = first + nbytes - 1
        with session().get(url, headers={"Range": f"bytes={first}-{last}"},
                           stream=True, timeout=(10, 35)) as res:
            if res.status_code != 206 or res.headers.get("Content-Range") != f"bytes {first}-{last}/{entry['source_bytes']}":
                raise ValueError("Archive returned unexpected range")
            b = res.raw.read(nbytes + 1)
            if len(b) != nbytes:
                raise ValueError("Archive row size changed")
            return b

    with ThreadPoolExecutor(max_workers=8) as pool:
        data = b"".join(pool.map(get_row, range(len(t))))
    x = np.frombuffer(data, dtype="<f8").reshape(len(t), k)
    return t, x, {
        "source_url": url, "format": "NWB ROI response series; exact contiguous byte ranges, one per row",
        "source_sha256_from_archive": entry["source_sha256"], "source_bytes": entry["source_bytes"],
        "range_data_bytes": len(data), "ranges": len(t), "source_data_offset_bytes": offset,
        "source_row_stride_bytes": 8 * cols, "source_whole_object_rehashed": False,
        "source_frames": frames, "source_rois": cols,
        "response": ROI_PATH + "/data", "plane": "Z0", "unit": "deltaF/F0",
        "clock_source": ROI_PATH + "/starting_time (seconds), rate attribute (Hz)",
        "rate_hz": rate, "source_start_s": start, "indicator": indicator,
    }


def extract(entry, output):
    started = time.monotonic()
    fn = fetch_fish if entry["species"] == "Danio rerio" else get_worm
    t, x, info = fn(entry)
    assert t[0] == 0 and np.all(np.diff(t) > 0) and np.max(t) < WINDOW_S
    assert x.ndim == 2 and x.shape[0] == t.size and 0 < x.shape[1] <= MAX_ROIS
    fields = {"time_s": t, "fluorescence": x, "roi_index": np.arange(x.shape[1], dtype="<i8")}
    path = output / entry["filename"]
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        np.savez(handle, **fields)
    tmp.replace(path)
    return {
        "id": entry["id"], "group": entry["group"], "species": entry["species"],
        "role": entry["role"], "filename": entry["filename"],
        "sha256": sha(path.read_bytes()), "shape": list(x.shape),
        "fields_sha256_c_order_le": {k: sha(v.tobytes(order="C")) for k,v in fields.items()},
        "nonfinite_elements": int(np.count_nonzero(~np.isfinite(x))), "start_s": float(t[0]),
        "last_s": float(t[-1]), "dt_median_s": float(np.median(np.diff(t))),
        "dt_min_s": float(np.diff(t).min()), "dt_max_s": float(np.diff(t).max()),
        "seconds_elapsed": round(time.monotonic() - started, 3), **info,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("role", choices=("train", "held"))
    p.add_argument("--approval", type=Path, help="Custodian's post-freeze held authorization record")
    args = p.parse_args()
    assert sha(ROSTER.read_bytes()) == SEAL
    roster = json.loads(ROSTER.read_text())
    if args.role == "held":
        if not args.approval:
            p.error("Held scoring requires the collector's post-fit dated authorization record")
        auth = json.loads(args.approval.read_text())
        assert auth["authorization"] == "held ROI slices only" and auth["roster_sha256"] == SEAL
        f = Path(auth["fit_manifest_path"])
        assert len(auth["fit_manifest_sha256"]) == 64 and sha(f.read_bytes()) == auth["fit_manifest_sha256"]
        assert auth["ids"] == [a["id"] for a in roster["held"]]
    output = BASE / "private" / args.role
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    receipts = []
    for entry in roster[args.role]:
        result = extract(entry, output)
        receipts.append(result)
        print(entry["id"], result["shape"], "verified", flush=True)
    write_json(BASE / (args.role + "-manifest.json"), {
        "roster_sha256": SEAL, "extractor_sha256": sha(Path(__file__).read_bytes()),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "private_directory": "private/" + args.role, "records": receipts,
    })


if __name__ == "__main__":
    main()
