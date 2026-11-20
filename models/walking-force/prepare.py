"""Verify the original downloads, rebuild the split, and unpack one partition."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

from plate_contacts import ContactTable

ARCHIVE_HASH="e11f0f85424e7630d32dbeb8b37bf78d470dcb34c0f461417671ce7d146eaec5"
SUPPLEMENT_HASH="37281bfdef06280d63019cb3008ea081f360f40d7a0cceb83293cc9aeae027d8"
MANIFEST_HASH="e0ccb1ae4a37c12d47c5e63ce3c9372efa212fa475275eef4dc40c2143aeda32"

def jsonbytes(obj):
    return (json.dumps(obj,indent=2)+"\n").encode()

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def manifest(archive):
    by_person=defaultdict(list)
    for m in archive.infolist():
        path=Path(m.filename)
        match=re.fullmatch(r"(\d+)_C2_(\d+)\.c3d",path.name)
        if match and match[1]==path.parent.name:
            by_person[match[1]].append((int(match[2]),m))
    if len(by_person)!=50:
        raise ValueError("source cohort mismatch")
    selected=[]
    for ordinal,person in enumerate(sorted(by_person),1):
        for repeat,m in sorted(by_person[person],key=lambda item:item[0])[:3]:
            selected.append({"name":m.filename,"size":m.file_size,"compressed_size":m.compress_size,
                             "crc32":f"{m.CRC:08x}","partition":"train" if ordinal<=30 else "assessment" if ordinal<=40 else "reserve",
                             "ordinal":ordinal,"repeat":repeat})
    result={"source":"10.6084/m9.figshare.7734767.v8",
            "directory_sha256":"07f351cffc52506899bdabb160e53927faec588a8ae17de7687cffe1bdbd6bc5",
            "rule":"First three available numeric C2 repeats per sorted source participant, ties invalid. No outcome-based substitutions. Ordinals 1–30 train, 31–40 assessment after fit seal, 41–50 reserve no reads; only ordinal 1 repeat 01 developmental access before method lock.",
            "selected":selected,"prior_single_repeat_plan_sha256":"f7e0b44abd615a557206cc1025c7df9dd1265c9a24e23ad266b063d6ac78b877"}
    if hashlib.sha256(jsonbytes(result)).hexdigest()!=MANIFEST_HASH:
        raise ValueError("rebuilt split mismatch")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("supplement",type=Path)
    p.add_argument("work",type=Path,help="private workspace outside the public package")
    p.add_argument("partition",choices=["train","assessment"])
    p.add_argument("--fit-seal",type=Path)
    a=p.parse_args()
    if a.partition=="assessment":
        if not a.fit_seal or not a.fit_seal.is_file() or len(json.loads(a.fit_seal.read_bytes()).get("weight_sha256",{}))!=7:
            p.error("complete and seal the seven fitted parameter sets before assessment")
    if sha(a.archive)!=ARCHIVE_HASH or sha(a.supplement)!=SUPPLEMENT_HASH:
        raise ValueError("original input hash mismatch")
    src=a.work/a.partition
    src.mkdir(parents=True,exist_ok=True)
    table=ContactTable(a.supplement)
    contact={}
    with zipfile.ZipFile(a.archive) as z:
        split=manifest(z)
        (a.work/"split.json").write_bytes(jsonbytes(split))
        for row in split["selected"]:
            if row["partition"]!=a.partition:
                continue
            dest=src/Path(row["name"]).name
            dest.write_bytes(z.read(row["name"]))
            contact[dest.name]=table.contacts(dest)
    (src/"contact-codes.json").write_bytes(jsonbytes(contact))
    print(len(contact),"C3D members in",a.partition)

if __name__=="__main__":
    main()
