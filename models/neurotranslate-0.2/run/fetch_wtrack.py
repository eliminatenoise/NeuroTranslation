"""P1: W-track (DANDI 000978, version 0.240511.0307) spike times and position by HDF5 byte ranges.

  python fetch_wtrack.py --paths PATHS.json ER1 JS15 JS17 JS14

ER1, JS15 and JS17 (the population study's 'Train' rats) give their whole recordings; JS14 gives only
the data recorded before the start of trip 79. Only these arrays are read: the epoch and trial tables'
start and stop times, the units table (id, spike_times_index, spike_times, electrodes) with the
electrodes table's location and group name, and the Position SpatialSeries data (columns x and y; the
stored speed column is read with them because rows are contiguous, then dropped) and timestamps.
No continuous voltage is requested. JS21, JS34, KL8 (consumed) and both ZT2 files (closed) are never
requested.

JS14's cut: trip 79 starts where trip 78 stops (6440.2994 s; both times come from the trials table).
The published W-track study manifest (benchmarks/wtrack-neural-motion/recording/manifest.json) gives,
for trip 78, the first camera row and, per unit, the first flat spike index at or after the end of
trip 78; these are the cut indices. Before the HDF5 file is opened the whole byte intervals of the three
data arrays are forbidden (their offsets were read from object headers); after the cut indices are
checked against the file, only the parts after the cut stay forbidden. Every allowed part is read by
exact byte ranges, so no byte recorded from trip 79 on is transferred.

Asset identity: the DANDI asset metadata is read first and its size, ETag and sha256 must equal the
pins below (the population study's catalogue and the W-track study's range reader). Every range
request carries If-Match with the ETag. One request per second per host; a 429 stops the run.
Outputs (RAM-backed raw folder): wtrack/<rat>.npz and wtrack/<rat>-RECEIPT.json.
"""
import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import http_ranges  # noqa: E402

PINS = {
    "ER1": {"asset_id": "b6425692-0f32-4087-8412-aebcfc37cd96", "size": 30009167808,
            "etag": "a4f80cf369b07b36b8ceb3399351aeef-448",
            "sha256": "508f7f4e5c1ef2b49373aef815bc64e6591ed7889407a3d57089d38dd4e2dba4"},
    "JS14": {"asset_id": "4b7c7959-04b3-4817-8f96-1af6f41888c1", "size": 28291364968,
             "etag": "ca822b7303cf85d5d7172f85db8799e1-422",
             "sha256": "6b8cf8ce3bbe34374e10a8a310592d1ae9762b20554569bc3c45fcfecdcf67b6"},
    "JS15": {"asset_id": "8fae63eb-84c2-4f7c-8a13-acb0832178f9", "size": 33642353128,
             "etag": "108956c255c51c0d759ec31084ac3c93-502",
             "sha256": "512ff29a08d0822eaa5811e5f64f076fce43a2d409167c436e9a6f25681febe9"},
    "JS17": {"asset_id": "f1f51660-4c23-4b61-a6bd-64d817d141e5", "size": 35702063632,
             "etag": "cac9ba24f16fde0818cb738947f2028e-533",
             "sha256": "6a6d39429758f746fae16b5ca1977a5084d8df0bcf8f7623dc8e9b536ca755be"},
}
SPIKES = "units/spike_times"
POS = "processing/behavior/Position/SpatialSeries/data"
POS_T = "processing/behavior/Position/SpatialSeries/timestamps"
# JS14 data-array byte intervals from the object headers (offset, storage bytes)
JS14_REGIONS = {SPIKES: (28276672000, 14692968), POS: (14130431016, 12035064), POS_T: (14142468128, 4011688)}
JS14_CUT_TRIAL = 79


def manifest_cut(paths):
    m = Path(paths["run_worktree"]) / "benchmarks" / "wtrack-neural-motion" / "recording" / "manifest.json"
    man = json.loads(m.read_text())
    t78 = [r for r in man["arrays"] if r["trial_id"] == 78][0]
    return {"manifest_sha256": common.sha256_file(m), "trial78_stop_s": t78["stop_s"],
            "camera_cut_row": t78["camera_bounds"][1], "spike_cut": [b[1] for b in t78["spike_bounds"]]}


def asset_url(paths, rat, pacer):
    pin = PINS[rat]
    url = "https://api.dandiarchive.org/api/assets/%s/" % pin["asset_id"]
    r = common.http_get(url, pacer, headers={"Accept": "application/json"})
    common.log_download(paths, {"dataset": "wtrack", "url": url, "final_url": r["final_url"], "hosts": r["hosts"],
                                "range": None, "status": r["status"], "bytes": r["bytes"], "sha256": r["sha256"],
                                "rat": rat, "purpose": "asset metadata (digests, size, content URL)"})
    md = json.loads(r["body"])
    ok = (md["contentSize"] == pin["size"] and md["digest"].get("dandi:dandi-etag") == pin["etag"]
          and md["digest"].get("dandi:sha2-256") == pin["sha256"])
    if not ok:
        raise SystemExit("asset metadata of %s differs from the pins" % rat)
    s3 = [u for u in md["contentUrl"] if "s3.amazonaws.com" in u]
    return s3[0], md


def layout(h, name):
    d = h[name]
    if d.chunks is not None or d.compression is not None or d.dtype.byteorder not in ("<", "=", "|"):
        raise SystemExit("%s is not a contiguous little-endian array" % name)
    return d.id.get_offset(), d.id.get_storage_size(), d.shape, d.dtype


def read_array(f, off, dtype, first, stop, row_shape=()):
    item = np.dtype(dtype).itemsize * int(np.prod(row_shape) if row_shape else 1)
    if stop <= first:
        return np.zeros((0,) + tuple(row_shape), dtype)
    b = f.read_range(off + first * item, off + stop * item)
    a = np.frombuffer(b, dtype=np.dtype(dtype).newbyteorder("<"))
    return a.reshape((-1,) + tuple(row_shape)).astype(dtype)


def strings(ds):
    return [x.decode() if isinstance(x, bytes) else str(x) for x in ds[:]]


def fetch(paths, rat, pacer):
    pin = PINS[rat]
    url, md = asset_url(paths, rat, pacer)
    forbid = []
    if rat == "JS14":
        forbid = [(o, o + n) for o, n in JS14_REGIONS.values()]
    f = http_ranges.RangeFile(paths, url, pin["size"], pin["etag"], "wtrack", rat, pacer=pacer, forbid=forbid,
                              budget_bytes=2_500_000_000)
    try:
        _extract(paths, rat, pin, url, f)
    finally:
        f.close()  # writes every pending request record, also after an error


def _extract(paths, rat, pin, url, f):
    rec = {"rat": rat, "asset": pin, "url": url, "protocol_head": common.protocol_head(paths), "arrays": {}}
    with h5py.File(f, "r") as h:
        assert h["general/subject/subject_id"][()].decode().endswith(rat)
        lay = {n: layout(h, n) for n in (SPIKES, POS, POS_T)}
        if rat == "JS14":
            for n, (o, sz) in JS14_REGIONS.items():
                assert lay[n][0] == o and lay[n][1] == sz, ("JS14 layout changed", n)
        ep = h["intervals/epoch intervals"]
        epochs = {"id": ep["id"][:].astype(np.int64), "start": ep["start_time"][:], "stop": ep["stop_time"][:]}
        ep_cols = sorted(ep.keys())
        epochs["tags"] = None
        if "tags" in ep and "tags_index" in ep:
            flat, ix = strings(ep["tags"]), ep["tags_index"][:].astype(np.int64)
            epochs["tags"] = ["|".join(flat[a:b]) for a, b in zip(np.r_[0, ix[:-1]], ix)]
        tr = h["intervals/trials"]
        trials = {"id": tr["id"][:].astype(np.int64), "start": tr["start_time"][:], "stop": tr["stop_time"][:]}
        tr_cols = sorted(tr.keys())
        u = h["units"]
        unit_id = u["id"][:].astype(np.int64)
        index = u["spike_times_index"][:].astype(np.int64)
        erow = u["electrodes"][:].astype(np.int64)
        etab = h[u["electrodes"].attrs["table"]]
        loc = strings(etab["location"])
        gname = strings(etab["group_name"])
        region = [loc[r] for r in erow]
        group = [gname[r] for r in erow]
        sp_off, sp_size, sp_shape, sp_dt = lay[SPIKES]
        po_off, po_size, po_shape, po_dt = lay[POS]
        pt_off, pt_size, pt_shape, pt_dt = lay[POS_T]
        assert index[-1] == sp_shape[0] and po_shape[0] == pt_shape[0] and po_shape[1] == 3
        starts = np.r_[0, index[:-1]]
        if rat == "JS14":
            cut = manifest_cut(paths)
            t79 = trials["start"][trials["id"] == JS14_CUT_TRIAL][0]
            t78s = trials["stop"][trials["id"] == JS14_CUT_TRIAL - 1][0]
            assert t78s == cut["trial78_stop_s"] == t79, "trip 78 must end where trip 79 starts"
            ends = np.array(cut["spike_cut"], np.int64)
            assert len(ends) == len(unit_id) and np.all(starts <= ends) and np.all(ends <= index)
            prow = int(cut["camera_cut_row"])
            assert 0 < prow <= po_shape[0]
            allowed_spikes = [(sp_off + 8 * a, sp_off + 8 * b) for a, b in zip(starts, ends)]
            new_forbid = [(sp_off + 8 * b, sp_off + 8 * c) for b, c in zip(ends, index) if c > b]
            new_forbid += [(po_off + 24 * prow, po_off + po_size), (pt_off + 8 * prow, pt_off + pt_size)]
            f.set_forbidden(new_forbid)
            rec["cut"] = dict(cut, trip79_start_s=float(t79), rule="data recorded before the start of trip 79",
                              forbidden_intervals=len(new_forbid))
        else:
            ends = index.copy()
            prow = po_shape[0]
            allowed_spikes = [(sp_off + 8 * a, sp_off + 8 * b) for a, b in zip(starts, ends)]
        # spike times: exact ranges per unit (merged where consecutive)
        times, kept = [], []
        for ui, (a, b) in enumerate(zip(starts, ends)):
            t = read_array(f, sp_off, "<f8", int(a), int(b))
            if len(t) > 1 and not np.all(np.diff(t) >= 0):
                raise SystemExit("unsorted spike times %s unit %d" % (rat, ui))
            times.append(t)
            kept.append(len(t))
        st = np.concatenate(times) if times else np.zeros(0)
        xyz = read_array(f, po_off, "<f8", 0, prow, (3,))
        pt = read_array(f, pt_off, "<f8", 0, prow)
        if len(pt) > 1 and not np.all(np.diff(pt) > 0):
            raise SystemExit("position timestamps not increasing for %s" % rat)
        if rat == "JS14":
            t79 = rec["cut"]["trip79_start_s"]
            assert (len(st) == 0 or st.max() < t79) and pt.max() < t79
            keep_tr = trials["stop"] <= t79
            trials = {k: v[keep_tr] for k, v in trials.items()}
            keep_ep = epochs["start"] < t79
            epochs = {k: (v[keep_ep] if isinstance(v, np.ndarray) else ([x for x, kk in zip(v, keep_ep) if kk] if v else v))
                      for k, v in epochs.items()}
        sp_attrs = {k: (v.decode() if isinstance(v, bytes) else (v.tolist() if hasattr(v, "tolist") else v))
                    for k, v in h[POS].attrs.items() if k in ("unit", "conversion", "offset", "resolution")}
        comments = h["processing/behavior/Position/SpatialSeries"].attrs.get("comments")
        ref = h["processing/behavior/Position/SpatialSeries/reference_frame"][()] \
            if "reference_frame" in h["processing/behavior/Position/SpatialSeries"] else None
        rec.update({"epoch_columns": ep_cols, "trial_columns": tr_cols, "units": len(unit_id),
                    "position_attrs": sp_attrs, "position_comments": comments.decode() if isinstance(comments, bytes) else comments,
                    "reference_frame": ref.decode() if isinstance(ref, bytes) else ref,
                    "session_start_time": h["session_start_time"][()].decode(),
                    "timestamps_reference_time": h["timestamps_reference_time"][()].decode()})
    out = Path(paths["raw"]) / "wtrack"
    out.mkdir(parents=True, exist_ok=True)
    arrays = {"unit_id": unit_id, "unit_region": np.array(region), "unit_group": np.array(group),
              "spike_times": st, "spike_ends": np.cumsum(kept).astype(np.int64),
              "pos_t": pt, "pos_xy": xyz[:, :2].copy(), "epoch_id": epochs["id"], "epoch_start": epochs["start"],
              "epoch_stop": epochs["stop"], "trial_id": trials["id"], "trial_start": trials["start"],
              "trial_stop": trials["stop"]}
    if epochs.get("tags"):
        arrays["epoch_tags"] = np.array(epochs["tags"])
    np.savez(out / (rat + ".npz"), **arrays)
    rec["arrays"] = {k: {"shape": list(v.shape), "sha256": common.sha256_bytes(np.ascontiguousarray(v).tobytes())}
                     for k, v in arrays.items() if v.dtype.kind in "fiu"}
    rec.update({"requests": f.requests, "network_bytes": f.network_bytes, "spikes": int(len(st)),
                "position_rows": int(len(pt)), "file_sha256": common.sha256_file(out / (rat + ".npz"))})
    common.atomic_write_json(out / (rat + "-RECEIPT.json"), json.loads(json.dumps(rec, default=str)))
    print(json.dumps({"rat": rat, "units": len(unit_id), "spikes": int(len(st)), "position_rows": int(len(pt)),
                      "requests": rec["requests"], "network_bytes": rec["network_bytes"]}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("rats", nargs="*", choices=sorted(PINS))
    ap.add_argument("--audit-js14", action="store_true", help="check every logged JS14 range against the held intervals")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    if a.audit_js14:
        audit_js14(paths)
        return
    pacer = common.Pacer(1.05)
    for rat in a.rats:
        try:
            fetch(paths, rat, pacer)
        except common.Stop429 as e:
            sys.exit(str(e))



def audit_js14(paths):
    """Check every logged JS14 range request against the byte intervals recorded from trip 79 on.

    Reads only the units' spike_times_index (with the whole data arrays forbidden) to rebuild each unit's
    held interval, then compares all JS14 ranges in DOWNLOADS.json. Writes wtrack/JS14-RANGE-AUDIT.json."""
    pacer = common.Pacer(1.05)
    pin = PINS["JS14"]
    url, _ = asset_url(paths, "JS14", pacer)
    f = http_ranges.RangeFile(paths, url, pin["size"], pin["etag"], "wtrack", "JS14 range audit (index only)",
                              pacer=pacer, forbid=[(o, o + n) for o, n in JS14_REGIONS.values()])
    try:
        with h5py.File(f, "r") as h:
            index = h["units/spike_times_index"][:].astype(np.int64)
    finally:
        f.close()
    cut = manifest_cut(paths)
    sp_off, _ = JS14_REGIONS[SPIKES]
    po_off, po_size = JS14_REGIONS[POS]
    pt_off, pt_size = JS14_REGIONS[POS_T]
    prow = cut["camera_cut_row"]
    held = [(sp_off + 8 * c, sp_off + 8 * i) for c, i in zip(cut["spike_cut"], index) if i > c]
    held += [(po_off + 24 * prow, po_off + po_size), (pt_off + 8 * prow, pt_off + pt_size)]
    log = json.loads(Path(paths["downloads_json"]).read_text())["downloads"]
    rows = [x for x in log if x.get("dataset") == "wtrack" and str(x.get("object", "")).startswith("JS14")
            and x.get("range") and x.get("bytes")]
    hits = []
    for x in rows:
        a, b = (int(v) for v in x["range"].split("=")[1].split("-"))
        for ha, hb in held:
            if a < hb and ha < b + 1:
                hits.append({"range": x["range"], "object": x["object"], "held": [ha, hb], "overlap_bytes": min(b + 1, hb) - max(a, ha)})
    out = {"checked_at": common.now_iso(), "js14_ranges_checked": len(rows), "held_intervals": len(held),
           "overlaps": hits, "note": "the probe's overlap (position rows after the cut, before the offsets were known) is "
           "recorded in INCIDENTS.json; every other JS14 range must have no overlap"}
    out["overlaps_outside_probe"] = [h_ for h_ in hits if h_["object"] != "JS14 metadata probe"]
    common.atomic_write_json(Path(paths["raw"]) / "wtrack" / "JS14-RANGE-AUDIT.json", out)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items() if k != "note"}))


if __name__ == "__main__":
    main()
