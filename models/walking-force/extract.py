"""Turn the selected original C3Ds into windows on the stored clock."""
import argparse
import hashlib
import json
from pathlib import Path
import zlib

import ezc3d
import numpy as np

MARKERS = ["L_FCC", "L_FM2", "R_FCC", "R_FM2", "L_IAS", "R_IAS"]
MUSCLES = ["R_tibialis_anterior", "R_soleus", "R_gastrocnemius_medialis",
           "R_vastus_medialis", "R_rectus_femoris", "R_semitendinosus",
           "R_gluteus_maximus", "R_gluteus_medius"]


def original_windows(path, emg_unavailable=()):
    raw = ezc3d.c3d(str(path), extract_forceplat_data=True)
    par, data = raw["parameters"], raw["data"]
    def field(group, name):
        return par[group][name]["value"]
    points = field("POINT", "LABELS")
    analogs = field("ANALOG", "LABELS")
    units = field("ANALOG", "UNITS")
    if not (float(field("POINT","RATE")[0]) == 100 and float(field("ANALOG","RATE")[0]) == 1500
            and field("POINT","UNITS") == ["mm"]):
        raise ValueError("unqualified sampling rate or point unit")
    if any(analogs.count(k) != 1 or units[analogs.index(k)] != "N" for k in ("Fz1","Fz2")):
        raise ValueError("both original Fz channels in N required")
    corners = field("FORCE_PLATFORM", "CORNERS")
    platforms = data["platform"]
    if len(platforms) != 2 or corners.shape != (3,4,2) or np.ptp(corners[2]) > 0.1:
        raise ValueError("requires two calibrated horizontal plates at the same height")
    analog = data["analogs"][0]
    n = data["points"].shape[-1]
    if analog.shape[1] != n*15:
        raise ValueError("point-analog frame count mismatch")
    net = []
    for i,p in enumerate(platforms):
        z = -analog[analogs.index(f"Fz{i+1}")]
        calibrated = p["force"][2]
        if not np.allclose(z,calibrated,rtol=1e-6,atol=1e-4,equal_nan=True):
            raise ValueError("unqualified plate coordinate transform")
        if not np.any(np.isfinite(z) & (z != 0)):
            raise ValueError("absent or all-zero plate circuit is ambiguous")
        net.append(z)
    force = np.mean(np.sum(net,axis=0).reshape(n,15),axis=1)
    xyz = np.full((n,6,3), np.nan,dtype=np.float32)
    center = corners.mean(axis=(1,2))
    for col,label in enumerate(MARKERS):
        if label not in points:
            continue
        j = points.index(label)
        coordinates = (data["points"][:3,j].T-center)*.001
        good = (data["meta_points"]["residuals"][0,j] >= 0) & np.isfinite(coordinates).all(axis=1)
        xyz[good,col] = coordinates[good]
    emg = np.full((n,15,8),np.nan,dtype=np.float32)
    for j,label in enumerate(MUSCLES):
        if label in analogs and label not in emg_unavailable:
            q = analogs.index(label)
            if units[q] != "V":
                raise ValueError(f"unexpected EMG unit for {label}")
            emg[:,:,j] = analog[q].reshape(n,15)*1e6
    # Every electrical sample in a token ends by its marker frame's analog block.
    stop = n//3*3
    markers = xyz[2:stop:3]
    with np.errstate(invalid="ignore"):
        rms = np.sqrt(np.mean(emg[:stop].reshape(-1,45,8)**2,axis=1,dtype=np.float64))
    marker_valid = np.isfinite(markers).all(axis=2)
    emg_valid = np.isfinite(rms)
    tokens = np.concatenate((np.nan_to_num(markers).reshape(-1,18), marker_valid,
                             np.where(emg_valid,rms,0), emg_valid),axis=1).astype(np.float32)
    anchors = np.arange(23,n-10,3)
    if not len(anchors):
        raise ValueError("trial shorter than fixed history and target offset")
    histories = tokens[(anchors//3)[:,None] + np.arange(-7,1)[None,:]]
    good = np.isfinite(force[anchors+10])
    if not good.any():
        raise ValueError("no finite combined targets")
    return (histories[good],force[anchors[good]+10].astype("f4"),force[anchors[good]].astype("f4"),
            anchors[good],{"available_anchors":len(anchors),"missing_target_anchors":int((~good).sum()),
                           "input_tokens":len(tokens),"valid_marker_tokens":marker_valid.sum(axis=0).tolist(),
                           "valid_emg_tokens":emg_valid.sum(axis=0).tolist()})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partition",choices=["train","assessment"])
    parser.add_argument("source",type=Path,help="directory containing only the authorized source C3Ds")
    parser.add_argument("split",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--fit-seal",type=Path)
    parser.add_argument("--availability",type=Path,required=True,help="source Supplementary Table 2 contact codes by original basename")
    args=parser.parse_args()
    if args.partition == "assessment" and not (args.fit_seal and args.fit_seal.is_file()):
        parser.error("assessment extraction requires the completed fit seal")
    rows=json.loads(args.split.read_bytes())["selected"]
    if hashlib.sha256(args.split.read_bytes()).hexdigest() != "e0ccb1ae4a37c12d47c5e63ce3c9372efa212fa475275eef4dc40c2143aeda32":
        raise ValueError("unexpected source split")
    availability=json.loads(args.availability.read_bytes())
    arrays = {k:[] for k in ("x","y","previous","anchor","person","repeat")}
    audit=[]
    for r in rows:
        if r["partition"] != args.partition:
            continue
        name=Path(r["name"]).name
        entry={"file":name,"person":r["ordinal"],"repeat":r["repeat"]}
        audit.append(entry)
        flags=availability.get(name,{})
        entry["source_code"]=flags.get("code")
        if entry["source_code"] not in ("12","21"):
            entry["excluded"]="source lacks two distinct reliable plate assignments"
            continue
        path=args.source/name
        raw=path.read_bytes()
        if len(raw)!=r["size"] or f"{zlib.crc32(raw):08x}"!=r["crc32"]:
            raise ValueError(f"source integrity failed: {name}")
        entry["sha256"]=hashlib.sha256(raw).hexdigest()
        try:
            x,y,pr,a,q=original_windows(path,flags.get("invalid_emg",()))
        except ValueError as exc:
            entry["excluded"]=str(exc)
            continue
        entry.update(q)
        entry["rows"]=len(y)
        for k,v in zip(arrays,(x,y,pr,a,np.full(len(y),r["ordinal"]),np.full(len(y),r["repeat"]))):
            arrays[k].append(v)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(audit,indent=2)+"\n")
    if not arrays["y"]:
        raise ValueError("zero eligible trials")
    np.savez_compressed(args.output,**{k:np.concatenate(v) for k,v in arrays.items()})
    print(args.partition,len(audit),len(arrays["y"]),sum(map(len,arrays["y"])))

if __name__=="__main__":
    main()
