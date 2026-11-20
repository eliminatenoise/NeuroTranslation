"""Select single-performer KIT recordings from the June 2017 release; prepare one partition."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import numpy as np


DIRECTORY_SHA256 = "5818fa43431551c4edbd84d6afc88c639648cbb0d6db03df52da1447ddbcad43"
SOURCE_SIZE = 4159992190
JOINTS = [f"{side}{joint}_joint" for side in ("L","R")
          for joint in ("Sx","Sy","Sz","Ex","Ez","Hx","Hy","Hz","Kx","Ax")]
DETAIL = "https://motion-database.humanoids.kit.edu/details/motions/{}/"
ACTIONS = {"walk":("walk","walking"),"run":("run","running","jog","jogging"),
           "jump":("jump","jumping","hop","hopping"),"kick":("kick","kicking"),
           "throw":("throw","throwing"),"catch":("catch","catching"),
           "sit":("sit","sitting","sit down"),"stand":("stand","standing","stand up"),
           "lift":("lift","lifting"),"reach":("reach","reaching"),
           "turn":("turn","turning"),"dance":("dance","dancing"),
           "climb":("climb","climbing"),"push":("push","pushing"),"pull":("pull","pulling")}


def hashed(prefix,key):
    return hashlib.sha256((prefix+str(key)).encode()).hexdigest()


def write(data,path):
    path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False)+"\n")


def file_digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def archive(path):
    if path.stat().st_size != SOURCE_SIZE:
        raise ValueError("Unexpected KIT ZIP size")
    with path.open("rb") as f:
        f.seek(-22,2)
        end = f.read()
        length,pos = struct.unpack_from("<II",end,12)
        f.seek(pos)
        # The range reader's pinned directory is the central entries plus ordinary
        # end record. The full release also carries 76 bytes of ZIP64 trailer.
        if hashlib.sha256(f.read(length)+end).hexdigest()!=DIRECTORY_SHA256:
            raise ValueError("Wrong ZIP directory")
    return zipfile.ZipFile(path)


def detail(db_id,cache):
    cache.mkdir(exist_ok=True,parents=True)
    path = cache/f"{db_id}.html"
    if not path.exists():
        url = DETAIL.format(db_id)
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read(500_001)
            if len(raw)>500_000 or r.geturl().rstrip("/") != url.rstrip("/"):
                raise ValueError("Unexpected provider response")
        path.write_bytes(raw)
    raw = path.read_bytes()
    page = raw.decode()
    if f"Details Motion #{db_id}<" not in page:
        raise ValueError("Wrong recording detail page")
    def field(name):
        match = re.search(r"<b>"+name+r":</b></td>\s*<td>(.*?)</td>",page,re.S)
        if not match:
            raise ValueError(f"Missing {name} for {db_id}")
        return match[1]
    subjects = sorted(set(re.findall(r"/details/subjects/(\d+)/",field("Subjects"))))
    tags = sorted(set(html.unescape(x.strip()).lower() for x in
                      re.findall(r"</i>\s*([^<>]+?)\s*<br\s*/?>",field("Motions"))))
    return {"subjects":subjects,"tags":tags, "page_sha256":hashlib.sha256(raw).hexdigest()}


def inventory(z):
    # Only release metadata is opened. Ignore legacy CMU and mirror entries completely.
    rows = {}
    for name in sorted(z.namelist()):
        if not re.fullmatch(r"\d{5}_meta.json",name):
            continue
        key = name[:5]
        metadata = json.loads(z.read(name))
        source = metadata["source"]
        if source["institution"]["identifier"] != "kit" or source["database"]["identifier"] != "kit":
            continue
        dbid = str(source["database"]["motion_id"])
        if dbid=="13" or metadata["nb_annotations"] <1:
            continue
        # Some database records contain several files. One hash-selected annotated
        # file per database recording avoids counting siblings as independent clips.
        file_id = str(source["database"]["motion_file_id"])
        row = {"key":key, "native_motion":dbid,"native_file":file_id,
               "n_annotations":metadata["nb_annotations"],
               "raw_crc":z.getinfo(key+"_raw.c3d").CRC,
               "mmm_crc":z.getinfo(key+"_mmm.xml").CRC}
        if dbid not in rows or hashed("file-20261120",key) < hashed("file-20261120",rows[dbid]["key"]):
            rows[dbid] = row
    return sorted(rows.values(),key=lambda r:hashed("file-order-20261120",r["key"]))


def choose(z,cache):
    ordered = inventory(z)
    # Freeze a bounded inspection of catalogue records. No caption or trajectory serves as a filter.
    ordered = ordered[:240]
    with ThreadPoolExecutor(max_workers=3) as pool:
        details = list(pool.map(lambda r:detail(r["native_motion"],cache),ordered))
    grouped = defaultdict(list)
    all_crc = Counter(r["raw_crc"] for r in ordered)
    mmm_crc = Counter(r["mmm_crc"] for r in ordered)
    for r,d in zip(ordered,details):
        if len(d["subjects"])!=1 or all_crc[r["raw_crc"]] > 1 or mmm_crc[r["mmm_crc"]] > 1:
            continue
        tags = set(d["tags"])
        # Prefer the first documented broad movement tag. Unmapped clips retain the
        # full stable tag set as a source-defined category, without reading captions.
        action = next((a for a,variants in ACTIONS.items() if tags.intersection(variants)),None)
        if not action and tags:
            action = "tagset-"+hashed("catalogue-tags:", "|".join(sorted(tags)))[:16]
        if not action:
            continue
        g = "KIT"+d["subjects"][0]
        grouped[g].append({**r,"group":g,"performers":[g],"action":action,
                           "recording":"KIT-motion-"+r["native_motion"],
                           "families":["KIT-raw-"+str(r["raw_crc"]),"KIT-mmm-"+str(r["mmm_crc"])],
                           "page_sha256":d["page_sha256"]})
    eligible = sorted((g for g,rr in grouped.items() if len(rr)>=3 and g!="KIT4"),
                      key=lambda g:hashed("subject-split-20261120",g))
    if len(eligible)<5:
        raise ValueError(f"Too few independently indexed KIT subjects: {[(g,len(rr)) for g,rr in grouped.items()]}")
    n_res = max(1,len(eligible)//6)
    n_ass = max(2,len(eligible)//4)
    partition = dict.fromkeys(eligible[:n_res],"reserve")
    partition.update(dict.fromkeys(eligible[n_res:n_res+n_ass],"assessment"))
    partition.update(dict.fromkeys(eligible[n_res+n_ass:],"train"))
    if len(grouped.get("KIT4",[]))>=3:
        partition["KIT4"]="train"
    rows = []
    for g in sorted(partition):
        for r in grouped[g][:18]:
            rows.append({**r,"part":partition[g]})
    return {"release":"KIT Motion–Language 2017-06-22 native KIT only",
            "directory_sha256":DIRECTORY_SHA256,"scanned_unique_recordings":len(ordered),
            "available_counts":{g:len(grouped[g]) for g in sorted(grouped)},
            "rows":sorted(rows,key=lambda r:r["key"])}


def extract_mmm(raw,expected_subject,steps):
    motions = ET.fromstring(raw).findall("Motion")
    people = [m for m in motions if (m.get("name") or "").startswith("subject_id_")]
    if len(people)!=1 or people[0].get("name")!="subject_id_"+expected_subject:
        raise ValueError("Motion identity disagrees with source catalogue")
    m = people[0]
    joint_names=[j.attrib["name"] for j in m.findall("./JointOrder/Joint")]
    if len(joint_names)!=len(set(joint_names)):
        raise ValueError("Duplicate names in joint order")
    indices = [joint_names.index(n) for n in JOINTS]
    ts, root, angles = [],[],[]
    for f in m.findall("./MotionFrames/MotionFrame"):
        ts.append(float(f.findtext("Timestep")))
        position = [float(v) for v in f.findtext("RootPosition").split()]
        native = [float(v) for v in f.findtext("JointPosition").split()]
        if len(position)!=3 or len(native)!=len(joint_names):
            raise ValueError("Unexpected MMM coordinate count")
        root.append(position); angles.append([native[j] for j in indices])
    t = np.asarray(ts)
    r = np.asarray(root)
    if len(t)<2 or not np.isfinite(t).all() or not (np.diff(t)>0).all():
        raise ValueError("Invalid MMM timestamps")
    delta = r-r[0]
    # Radial distance from the start discards horizontal heading and absolute origin.
    x = np.column_stack([angles,np.linalg.norm(delta[:,:2],axis=1),delta[:,2]])
    if not np.isfinite(x).all():
        raise ValueError("Nonfinite coordinates")
    grid = np.linspace(t[0],t[-1],steps)
    return np.stack([np.interp(grid,t,col) for col in x.T],axis=1).astype(np.float32),len(t),float(t[-1]-t[0])


def prepare(z,manifest,part,out,steps):
    if part not in {"train","assessment"}:
        raise ValueError("Reserve cannot be prepared")
    out.mkdir(parents=True,exist_ok=True)
    receipts = []
    for row in manifest["rows"]:
        if row["part"]!=part:
            continue
        k=row["key"]
        data = z.read(k+"_mmm.xml")
        txt = z.read(k+"_annotations.json")
        captions = json.loads(txt)
        if not isinstance(captions,list) or len(captions)!=row["n_annotations"]:
            raise ValueError("Archive caption count disagrees with metadata")
        x,n,sec = extract_mmm(data,row["group"].removeprefix("KIT"),steps)
        np.save(out/(k+".npy"),x,allow_pickle=False)
        write(captions,out/(k+".json"))
        receipts.append({"key":k,"array":file_digest(out/(k+".npy")),"text":file_digest(out/(k+".json")),"frames":n,"duration_s":sec,"mmm_sha256":hashlib.sha256(data).hexdigest(),
                         "captions_sha256":hashlib.sha256(txt).hexdigest()})
    write(receipts,out/(part+"-records.json"))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase",choices=["manifest","train","assessment"])
    p.add_argument("--zip",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--local",required=True,type=Path)
    p.add_argument("--policy",type=Path,default=Path(__file__).with_name("policy.json"))
    args=p.parse_args()
    with archive(args.zip) as z:
        if args.phase=="manifest":
            if args.manifest.exists():
                raise ValueError("Refusing to overwrite frozen manifest")
            manifest = choose(z,args.local/"details")
            manifest["archive_sha256"] = file_digest(args.zip)
            manifest["preprocessing_sha256"] = file_digest(Path(__file__))
            manifest["ordered_channels"] = JOINTS+["root_horizontal_distance_from_start","root_vertical_offset"]
            write(manifest,args.manifest)
        else:
            manifest = json.loads(args.manifest.read_text())
            if manifest["preprocessing_sha256"] != file_digest(Path(__file__)) or manifest["archive_sha256"] != file_digest(args.zip):
                raise ValueError("Release archive or preprocessing changed after the manifest was frozen")
            prepare(z,manifest,args.phase,args.local/"data",
                    json.loads(args.policy.read_text())["motion_steps"])


if __name__=="__main__":
    main()
