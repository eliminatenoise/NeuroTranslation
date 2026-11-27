"""P1 downloads of the neural part: ds003739 sessions 1-3 of the 18 development people and Ofner S1-S7
motor-execution runs 4-10, exactly as PROTOCOL.json downloads_planned.P1_training lists them.

  python fetch_neural.py --paths PATHS.json ds003739
  python fetch_neural.py --paths PATHS.json ofner

ds003739 (OpenNeuro 1.0.3): the file list comes from the pinned git catalogue of the dataset (commit
f15449b6..., tree 9aae84fa...), restricted to the 18 people of the visual-balance stage 'development'
(recomputed here from the published roster rule) and to the sessions that are not already local (the
local session of every development person is session 4). Only the .set and .fdt objects are fetched;
each must match the size and MD5 of its git-annex key. Sidecar text files are read from the catalogue's
git objects at P2 and are not downloaded. The assessment 6 and reserve 6 are never requested.

Ofner (Zenodo 834976): the record's file list is read once from the Zenodo API and compared with the
earlier catalogue; only motorexecution_subject{1..7}_run{4..10}.gdf are fetched and each must match the
publisher MD5 and size. S8-S12 runs 5-10 (consumed), S13-S15 (reserve) and motor-imagery runs are never
requested.

One request per second per host and one file at a time per host; a 429 stops the run without a retry.
Every request is logged in DOWNLOADS.json (URL, range, bytes, sha256, MD5).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

DS_COMMIT = "f15449b6aecb83044b49a1798955e8a212a68fc1"
DS_TREE = "9aae84faaa554e6cf79f569c22d40235c99c2158"
DS_S3 = "https://s3.amazonaws.com/openneuro.org/ds003739/"
DS_ROSTER_SALT = "balance-stance-20261121:"
OFNER_RECORD = "https://zenodo.org/api/records/834976"
OFNER_PEOPLE = range(1, 8)
OFNER_RUNS = range(4, 11)
MAX_RAW_BYTES = 30_000_000_000


def git(cat, *args):
    return subprocess.check_output(["git", "-C", str(cat), *args])


def ds_roster(people):
    """The visual-balance roster rule (stage lists from 30 BIDS participants)."""
    ordered = sorted(people, key=lambda n: int(n.split("-")[1]))
    pilot, rest = ordered[0], ordered[1:]
    rnd = sorted(rest, key=lambda n: hashlib.sha256((DS_ROSTER_SALT + n).encode()).hexdigest())
    return {"development": [pilot] + rnd[:17], "assessment": rnd[17:23], "reserve": rnd[23:29]}


def ds_tree(paths):
    cat = Path(paths["ds003739_cache"]) / "catalogue"
    if git(cat, "rev-parse", "HEAD", "HEAD^{tree}").decode().split() != [DS_COMMIT, DS_TREE]:
        raise SystemExit("ds003739 catalogue is not OpenNeuro 1.0.3")
    tree = {}
    for line in git(cat, "ls-tree", "-r", "HEAD").decode().splitlines():
        f, name = line.split("\t")
        mode, _kind, blob = f.split()
        tree[name] = (mode, blob)
    return cat, tree


def ds_plan(paths):
    cat, tree = ds_tree(paths)
    people = sorted({n.split("/")[0] for n in tree if re.fullmatch(r"sub-\d{3}/.*", n)})
    ros = ds_roster(people)
    dev_receipt = json.loads((Path(paths["ds003739_cache"]) / "development-files.json").read_text())
    if sorted(dev_receipt["selected"]) != sorted(ros["development"]):
        raise SystemExit("development roster differs from the published rule")
    local = {}
    for k in dev_receipt["files"]:
        p = k.split("/")
        if len(p) > 2:
            local.setdefault(p[0], set()).add(p[1])
    plan = []
    for person in sorted(ros["development"]):
        sessions = sorted({n.split("/")[1] for n in tree if n.startswith(person + "/") and n.count("/") >= 2})
        for ses in sessions:
            if ses in local.get(person, set()):
                continue
            for name, (mode, blob) in sorted(tree.items()):
                if not name.startswith("%s/%s/" % (person, ses)) or mode != "120000":
                    continue
                ptr = git(cat, "cat-file", "blob", blob).decode().split("/")[-1]
                m = re.fullmatch(r"MD5E-s(\d+)--([0-9a-f]{32})\.(fdt|set)", ptr)
                if not m:
                    raise SystemExit("unexpected annex key " + ptr)
                plan.append({"path": name, "person": person, "session": ses, "bytes": int(m[1]), "md5": m[2],
                             "annex_key": ptr, "git_blob": blob})
    excluded = sorted(set(ros["assessment"]) | set(ros["reserve"]))
    assert not any(p["person"] in excluded for p in plan)
    return plan, ros


def fetch_ds003739(paths, pacer):
    plan, ros = ds_plan(paths)
    total = sum(p["bytes"] for p in plan)
    print(json.dumps({"files": len(plan), "bytes": total, "people": len({p["person"] for p in plan})}))
    if total > MAX_RAW_BYTES:
        sys.exit("plan above the raw-space cap")
    out = Path(paths["raw"]) / "ds003739"
    done = 0
    for p in plan:
        dst = out / p["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size == p["bytes"]:
            h = hashlib.md5()
            with open(dst, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
            if h.hexdigest() == p["md5"]:
                done += 1
                continue
        url = DS_S3 + p["path"]
        try:
            res = common.http_get(url, pacer, out_path=dst, md5=True, timeout=300)
        except common.Stop429 as e:
            common.log_download(paths, {"dataset": "ds003739", "url": url, "status": 429, "bytes": 0, "sha256": None,
                                        "note": "stopped on 429; no retry"})
            dst.unlink(missing_ok=True)
            sys.exit(str(e))
        ok = res["status"] == 200 and res["bytes"] == p["bytes"] and res["md5"] == p["md5"]
        common.log_download(paths, {"dataset": "ds003739", "url": url, "final_url": res["final_url"],
                                    "hosts": res["hosts"], "range": None, "status": res["status"],
                                    "bytes": res["bytes"], "sha256": res["sha256"], "md5": res["md5"],
                                    "annex_key": p["annex_key"], "annex_md5_and_size_match": ok,
                                    "person": p["person"], "session": p["session"], "role": "development",
                                    "s3_version_id": res["headers"].get("x-amz-version-id"),
                                    "raw_location": "RAM-backed temporary folder; deleted after tokenising and the shard check"})
        if not ok:
            dst.unlink(missing_ok=True)
            sys.exit("size or MD5 mismatch for " + p["path"])
        done += 1
        if done % 10 == 0:
            print(json.dumps({"done": done, "of": len(plan)}), flush=True)
    common.atomic_write_json(out / "FETCH-RESULT.json", {"protocol_head": common.protocol_head(paths),
                                                         "files": len(plan), "bytes": total,
                                                         "development_people": sorted(ros["development"]),
                                                         "never_requested": {"assessment": ros["assessment"],
                                                                             "reserve": ros["reserve"]},
                                                         "plan": plan})
    print(json.dumps({"ds003739_done": done}))


def ofner_plan(record):
    plan = []
    for f in record["files"]:
        m = re.fullmatch(r"motorexecution_subject(\d+)_run(\d+)\.gdf", f["key"])
        if m and int(m[1]) in OFNER_PEOPLE and int(m[2]) in OFNER_RUNS:
            plan.append({"key": f["key"], "person": "S%d" % int(m[1]), "run": int(m[2]), "bytes": f["size"],
                         "md5": f["checksum"].split(":", 1)[1], "url": f["links"]["self"]})
    return sorted(plan, key=lambda p: (int(p["person"][1:]), p["run"]))


def fetch_ofner(paths, pacer):
    out = Path(paths["raw"]) / "ofner"
    out.mkdir(parents=True, exist_ok=True)
    try:
        rec = common.http_get(OFNER_RECORD, pacer, headers={"Accept": "application/json"})
    except common.Stop429 as e:
        sys.exit(str(e))
    common.log_download(paths, {"dataset": "ofner", "url": OFNER_RECORD, "final_url": rec["final_url"],
                                "hosts": rec["hosts"], "range": None, "status": rec["status"], "bytes": rec["bytes"],
                                "sha256": rec["sha256"], "purpose": "record file list and checksums (metadata)"})
    (out / "record.json").write_bytes(rec["body"])
    record = json.loads(rec["body"])
    plan = ofner_plan(record)
    earlier = ofner_plan(json.loads(Path(paths["ofner_catalogue"]).read_text()))
    same = [(p["key"], p["bytes"], p["md5"]) for p in plan] == [(p["key"], p["bytes"], p["md5"]) for p in earlier]
    total = sum(p["bytes"] for p in plan)
    print(json.dumps({"files": len(plan), "bytes": total, "same_as_earlier_catalogue": same}))
    if len(plan) != 49 or not same:
        sys.exit("Ofner plan differs from the protocol (49 files) or from the earlier catalogue")
    done = 0
    for p in plan:
        dst = out / p["key"]
        if dst.exists() and dst.stat().st_size == p["bytes"]:
            h = hashlib.md5()
            with open(dst, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
            if h.hexdigest() == p["md5"]:
                done += 1
                continue
        try:
            res = common.http_get(p["url"], pacer, out_path=dst, md5=True, timeout=300)
        except common.Stop429 as e:
            common.log_download(paths, {"dataset": "ofner", "url": p["url"], "status": 429, "bytes": 0, "sha256": None,
                                        "note": "stopped on 429; no retry"})
            dst.unlink(missing_ok=True)
            sys.exit(str(e))
        ok = res["status"] == 200 and res["bytes"] == p["bytes"] and res["md5"] == p["md5"]
        common.log_download(paths, {"dataset": "ofner", "url": p["url"], "final_url": res["final_url"],
                                    "hosts": res["hosts"], "range": None, "status": res["status"],
                                    "bytes": res["bytes"], "sha256": res["sha256"], "md5": res["md5"],
                                    "publisher_md5_and_size_match": ok, "person": p["person"], "run": p["run"],
                                    "role": "arm-transfer fitting person",
                                    "raw_location": "RAM-backed temporary folder; deleted after tokenising and the shard check"})
        if not ok:
            dst.unlink(missing_ok=True)
            sys.exit("size or MD5 mismatch for " + p["key"])
        done += 1
        print(json.dumps({"done": done, "of": len(plan), "file": p["key"]}), flush=True)
    common.atomic_write_json(out / "FETCH-RESULT.json", {"protocol_head": common.protocol_head(paths),
                                                         "files": len(plan), "bytes": total, "plan": plan})
    print(json.dumps({"ofner_done": done}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("dataset", choices=["ds003739", "ofner"])
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    pacer = common.Pacer(1.05)
    if a.plan_only:
        if a.dataset == "ds003739":
            plan, ros = ds_plan(paths)
            print(json.dumps({"files": len(plan), "bytes": sum(p["bytes"] for p in plan), "roster": ros}))
        return
    {"ds003739": fetch_ds003739, "ofner": fetch_ofner}[a.dataset](paths, pacer)


if __name__ == "__main__":
    main()
