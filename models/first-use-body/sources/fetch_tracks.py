"""Download a pinned animal-recording panel and export native optical landmarks."""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen
import zipfile

import h5py
import numpy as np


INVENTORY=Path(__file__).resolve().with_name("source-inventory.json")
HERE=Path(".")

def digest(path, method="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, method).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def put(group, track_id, xy, seconds, frame, names, units, **meta):
    xy = np.asarray(xy, dtype=np.float32)
    seconds = np.asarray(seconds, dtype=np.float64)
    frame = np.asarray(frame, dtype=np.int64)
    assert xy.shape == (len(seconds), len(names), 2)
    assert np.isfinite(seconds).all() and np.all(np.diff(seconds) > 0)
    assert frame.shape == seconds.shape and np.all(np.diff(frame) > 0)
    good = np.isfinite(xy).all(axis=-1)
    xy[~good] = np.nan
    identifier = f"{group['id']}_t{track_id}"
    dest = HERE / "tracks" / group["split"] / (identifier + ".npz")
    dest.parent.mkdir(parents=True, exist_ok=True)
    arrays = meta.pop("extra_arrays", {})
    np.savez_compressed(dest, xy=xy, seconds=seconds, frame=frame, names=np.asarray(names), **arrays)
    dt = np.diff(seconds)
    return dict(id=identifier, path=str(dest.relative_to(HERE)), split=group["split"],
                group=group["id"], species=group["species"], phylum=group["phylum"],
                units=units, individual_id=meta.pop("individual_id"), group_scope="physical recording",
                source_url=group["url"], license=group["license"], sha256=digest(dest),
                frames=len(frame), frame_first=int(frame[0]), frame_last=int(frame[-1]), landmarks=len(names),
                seconds_first=seconds[0], seconds_last=seconds[-1], dt_s_min=dt.min(),
                dt_s_median=np.median(dt), dt_s_max=dt.max(), names=names,
                present_point_frames=int(good.sum()), missing_point_frames=int((~good).sum()),
                all_landmarks_missing_frames=int((~good.any(axis=1)).sum()), **meta)


def read_sleap(g, path):
    catalog = g["metadata"]
    with h5py.File(path) as f:
        desc = json.loads(f["metadata"].attrs["json"])
        assert len(desc["skeletons"]) == len(f["videos_json"]) == 1
        # Point rows follow the skeleton's local node order, not the global nodes table.
        names = [desc["nodes"][n["id"]]["name"] for n in desc["skeletons"][0]["nodes"]]
        video = json.loads(f["videos_json"][0])["backend"]["filename"]
        start, stop = map(int, re.search(r"@(\d+)-(\d+)\.mp4$", video).groups())
        fps = float(catalog["FPS"])
        frames = f["frames"][:]
        assert np.array_equal(frames["frame_idx"], np.arange(stop-start))
        assert np.array_equal(frames["frame_idx"], frames["frame_id"]) and np.all(frames["video"] == 0)
        instances = f["instances"][:]
        types = np.unique(instances["instance_type"])
        assert len(types) == 1 and int(types[0]) in (0, 1)
        predicted = int(types[0]) == 1
        points = f["pred_points" if predicted else "points"][:]
        assert (instances["point_id_end"]-instances["point_id_start"] == len(names)).all()
        tracks = [json.loads(s)[1] for s in f["tracks_json"][:]]
        assert np.array_equal(np.unique(instances["track"]), np.arange(len(tracks)))
        for i, label in enumerate(tracks):
            rows = instances[instances["track"] == i]
            index = rows["frame_id"].astype(int)
            assert len(np.unique(index)) == len(rows)
            block = points[rows["point_id_start"][:, None] + np.arange(len(names), dtype=np.uint64)]
            xy = np.full((len(frames), len(names), 2), np.nan, dtype=np.float32)
            coords = np.stack([block["x"], block["y"]], axis=-1)
            coords[~block["visible"]] = np.nan
            xy[index] = coords
            more = {}
            if predicted:
                conf = np.full(xy.shape[:2], np.nan, dtype=np.float32)
                conf[index] = block["score"]
                more["confidence"] = conf
            yield put(g, i, xy, frames["frame_idx"]/fps, frames["frame_idx"]+start,
                      names, "px", individual_id=label or "unnamed single track 0", original_video=video,
                      time_basis="Original clip frame index divided by official acquisition rate; zero is clip start.",
                      native_fps=fps, group_track_count=len(tracks),
                      identifier_scope="Within-video track; cross-recording identity unavailable.",
                      source_method=("SLEAP scored predictions" if predicted else
                                     "SLEAP continuous tracking example stored as label-type points. Source does not quantify manual editing or landmark error."),
                      confidence_available=predicted, source_credit=catalog["Credit"],
                      source_setup=catalog["Description"], dataset_px_per_mm=float(catalog["Resolution"].split()[0]),
                      dataset_image_size=catalog["Image size"], extra_arrays=more)


def read_locust(g, path):
    with zipfile.ZipFile(path) as z:
        for i, file in enumerate(sorted(z.namelist())):
            assert file.endswith(f"_id{i}.npz")
            with np.load(io.BytesIO(z.read(file)), allow_pickle=False) as native:
                frame = native["frame"].astype(np.int64)
                assert np.all(frame == native["frame"]) and np.all(np.diff(frame) > 0)
                point_ids = sorted(int(k[5:]) for k in native if k.startswith("poseX"))
                assert point_ids == list(range(7))
                xy = np.stack([np.column_stack((native[f"poseX{n}"], native[f"poseY{n}"])) for n in point_ids], axis=1)
                names = [f"pose{n}" for n in point_ids]
                meta = {"object_detection_confidence":native["detection_p"], "source_playback_seconds":native["time"]}
                yield put(g, i, xy, frame/5, frame, names, "px", individual_id=f"id{i}", original_video="locusts-noqr_20250117_5",
                          group_track_count=len(z.namelist()), native_fps=5, time_basis="Source video acquired at 5 Hz. TRex time/timestamp follows 30 Hz playback; source frame IDs divided by 5 preserve acquisition time.",
                          frame_absences=int(frame[-1]-frame[0]+1-len(frame)), identifier_scope="Within-video track only.",
                          source_method="TRex with 7-point YOLO pose; indexed native poseX/Y coordinates. No anatomical names inferred.",
                          source_credit="Angela Albi and Daniele Carlesso; Angela Albi, Tristan Walter and Daniele Carlesso (2025), doi:10.17617/3.7F5MGE",
                          source_setup="Five desert locusts in a 60 cm diameter arena.", extra_arrays=meta)


def read_worm(g, path):
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist()) == 1
        w = json.loads(z.read(z.namelist()[0]))
    assert len(w["data"]) == 1 and w["units"]["t"] == "seconds"
    assert w["units"]["x"] == w["units"]["y"] == "micrometers"
    row = w["data"][0]
    assert "ox" not in row and "oy" not in row and row["head"] == "L"
    xy = np.stack([np.asarray(row[k], dtype=np.float32) for k in ("x", "y")], axis=-1)
    seconds = np.asarray(row["t"], dtype=np.float64)
    assert np.all(np.diff(seconds)>0)
    fps = g["native_fps"]
    names = [f"midline_{j:02d}" for j in range(xy.shape[1])]
    names[0],names[-1] = "head","tail"
    yield put(g, 0, xy, seconds, np.arange(len(xy)), names, "um", individual_id=str(row["id"]),
              time_basis="Observed WCON t seconds. Frame field is WCON sample ordinal; no independent raw camera frame counter provided.",
              group_track_count=1, native_fps=fps, strain=g["strain"], original_video=g["filename"].removesuffix(".wcon.zip"),
              original_doi=g["doi"], identifier_scope="Single-worm experiment; WCON id is local; cross-day animal ID unavailable.",
              source_method="WormTracker video and Tierpsy segmentation. Ordered skeleton samples along the centreline. Adjacent indexes need not mark the same material point.",
              source_credit=g["credit"],
              source_setup=f"{w['metadata']['stage']} {w['metadata']['sex']}, {w['metadata']['media']}, {w['metadata']['food']}",
              source_head_orientation=row["head"])





def fetch(group, cache):
    ext=".slp" if group["kind"]=="sleap" else ".zip"
    path=cache/(group["id"]+ext)
    if path.exists():
        if digest(path)!=group["source_sha256"]:
            raise ValueError(f"Cached data differ from the source inventory: {path}")
        return path
    with tempfile.NamedTemporaryFile(dir=cache,delete=False) as pending:
        temp=Path(pending.name)
        try:
            with urlopen(group["url"],timeout=90) as source:
                shutil.copyfileobj(source,pending)
            pending.close()
            if digest(temp)!=group["source_sha256"]:
                raise ValueError(f"Download hash mismatch for {group['id']}")
            os.replace(temp,path)
        finally:
            if temp.exists():
                temp.unlink()
    return path


def main():
    global HERE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("bodyplan-data"))
    parser.add_argument("--cache",type=Path,help="Reuse a directory of hash-checked source files")
    parser.add_argument("--group",action="append",help="Fetch only this recording group (can be repeated)")
    opts=parser.parse_args()
    HERE=opts.output.resolve()
    HERE.mkdir(parents=True,exist_ok=True)
    cache=opts.cache.resolve() if opts.cache else HERE/"raw"
    cache.mkdir(parents=True,exist_ok=True)
    selected=json.loads(INVENTORY.read_text())["groups"]
    if opts.group:
        requested=set(opts.group)
        available={g["id"] for g in selected}
        if requested-available:
            parser.error("Unknown group(s): "+", ".join(sorted(requested-available)))
        selected=[g for g in selected if g["id"] in requested]
    output=HERE/"manifest.json"
    if output.exists():
        parser.error(f"Output manifest already exists at {output}; choose a new output directory.")
    result=[]
    for group in selected:
        path=fetch(group,cache)
        converter={"sleap":read_sleap,"wcon":read_worm,"trex":read_locust}[group["kind"]]
        for record in converter(group,path):
            record["source_sha256"]=group["source_sha256"]
            result.append(record)
        print(f"Converted {group['id']}",flush=True)
    write_json(output,{"records":result,"inventory_sha256":digest(INVENTORY)})


if __name__=="__main__":
    main()
