"""P1: Gait120 development people, non-SitToStand TRC and MOT members, by ranged reads.

PROTOCOL.json downloads_planned.P1_training: "Gait120 development non-SitToStand TRC and MOT
members, 426,500,000 bytes, figshare 27677016, ranged member reads from 11 archives".

What is fetched, per development person of the frozen chair-rise roster (role 'development'):
  MotionCapture/<task>/TRC/... for every task except SitToStand, and MotionCapture/Static/TRC
  MotionCapture/<task>/MOT/... (plate force) for LevelWalking and StandToSit
  JointAngle/<task>/... (OpenSim joint angles) for every task except SitToStand
Nothing of S001-S010 (figshare file 53167640) and nothing of a validation or confirmation person is
requested: each request covers a run of consecutive archive members that all belong to one
development person and are all wanted, checked against the archive's central directory before any
request is made. Each member is inflated only after its local header name, method and sizes match
the central directory, and kept only if its CRC-32 matches.

Central directories come from the 11 archive tails already on disk (earlier range reads); every
response must be HTTP 206 with the exact Content-Range and archive size of the roster record.
At most one request per second per host; a 429 stops the run with no retry.
"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

EXCLUDED_FILE_ID = 53167640  # S001-S010, evaluation set E1: never requested


def parse_central_directory(b):
    i = b.rfind(b"PK\x05\x06")
    j = b.rfind(b"PK\x06\x06")
    cd_size, = struct.unpack("<I", b[i + 12:i + 16])
    cd_off, = struct.unpack("<I", b[i + 16:i + 20])
    if j >= 0:
        cd_size, = struct.unpack("<Q", b[j + 40:j + 48])
        cd_off, = struct.unpack("<Q", b[j + 48:j + 56])
    p = (j if j >= 0 else i) - cd_size
    if p < 0:
        raise ValueError("tail does not hold the whole central directory")
    out = []
    while b[p:p + 4] == b"PK\x01\x02":
        meth, = struct.unpack("<H", b[p + 10:p + 12])
        crc, csize, usize = struct.unpack("<III", b[p + 16:p + 28])
        n, e, c = struct.unpack("<HHH", b[p + 28:p + 34])
        lho, = struct.unpack("<I", b[p + 42:p + 46])
        name = b[p + 46:p + 46 + n].decode("utf-8")
        extra = b[p + 46 + n:p + 46 + n + e]
        q = 0
        while q < len(extra):
            hid, hl = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:
                vals = list(struct.unpack("<" + "Q" * (hl // 8), extra[q + 4:q + 4 + (hl // 8) * 8]))
                vi = 0
                if usize == 0xFFFFFFFF:
                    usize = vals[vi]; vi += 1
                if csize == 0xFFFFFFFF:
                    csize = vals[vi]; vi += 1
                if lho == 0xFFFFFFFF:
                    lho = vals[vi]; vi += 1
            q += 4 + hl
        out.append({"name": name, "crc32": crc, "csize": csize, "usize": usize, "lho": lho, "method": meth})
        p += 46 + n + e + c
    return out, cd_off, cd_size


def wanted(name, dev):
    p = name.split("/")
    if len(p) < 4 or p[0] not in dev or not p[-1].lower().endswith((".trc", ".mot")):
        return False
    if p[1] == "MotionCapture":
        return p[2] != "SitToStand" and (p[3] == "TRC" or (p[3] == "MOT" and p[2] in ("LevelWalking", "StandToSit")))
    if p[1] == "JointAngle":
        return p[2] != "SitToStand"
    return False


def build_plan(paths):
    g = Path(paths["gait120_intake"])
    roster = json.loads((g / "ROSTER.json").read_bytes())
    dev = set(roster["roles"]["development"])
    assert len(dev) == 66
    _, alloc = common.protocol_files(paths)
    alloc_units = {r["unit"] for r in alloc["inner_folds"]["gait120"]["rows"]}
    assert alloc_units == dev, "ALLOCATION.json gait120 units differ from the roster's development role"
    excluded_people = set(roster["roles"]["validation"]) | set(roster["roles"]["confirmation"]) | {
        "S%03d" % i for i in range(1, 11)}
    assert not (dev & excluded_people)
    runs, members, tails = [], [], []
    for rec in roster["records"]:
        fid = rec["file_id"]
        assert fid != EXCLUDED_FILE_ID
        tail = g / "index" / ("%d.tail" % fid)
        tb = tail.read_bytes()
        tails.append({"file_id": fid, "tail_sha256": common.sha256_bytes(tb), "tail_bytes": len(tb)})
        m, cd_off, cd_size = parse_central_directory(tb)
        m.sort(key=lambda x: x["lho"])
        for k, x in enumerate(m):
            x["end"] = m[k + 1]["lho"] if k + 1 < len(m) else cd_off
        cur = None
        for x in m:
            if not wanted(x["name"], dev):
                cur = None
                continue
            person = x["name"].split("/")[0]
            x["person"] = person
            members.append(dict(x, file_id=fid))
            if cur is not None and cur["person"] == person and cur["end"] == x["lho"]:
                cur["end"] = x["end"]
                cur["members"].append(x["name"])
            else:
                cur = {"file_id": fid, "archive_bytes": rec["member_bytes"], "archive": rec["file_name"],
                       "person": person, "start": x["lho"], "end": x["end"], "members": [x["name"]]}
                runs.append(cur)
        # every byte of every run belongs to wanted members of one development person
        byname = {x["name"]: x for x in m}
        for r in runs:
            if r["file_id"] != fid:
                continue
            inside = [x for x in m if r["start"] <= x["lho"] < r["end"]]
            assert sorted(x["name"] for x in inside) == sorted(r["members"])
            assert all(x["name"].split("/")[0] == r["person"] and x["name"].split("/")[0] in dev for x in inside)
            assert all(byname[n]["name"].split("/")[0] not in excluded_people for n in r["members"])
    return runs, members, tails


def extract(blob, start, members_by_name, names, out_root):
    out = []
    for name in names:
        x = members_by_name[name]
        p = x["lho"] - start
        sig, ver, flag, meth, mt, md, crc, cs, us, n, e = struct.unpack("<4s5H3I2H", blob[p:p + 30])
        if sig != b"PK\x03\x04":
            raise ValueError("no local header for " + name)
        lname = blob[p + 30:p + 30 + n].decode("utf-8")
        if lname != name or meth != x["method"]:
            raise ValueError("local header mismatch for " + name)
        d0 = p + 30 + n + e
        data = blob[d0:d0 + x["csize"]]
        if len(data) != x["csize"]:
            raise ValueError("short member " + name)
        if meth == 8:
            raw = zlib.decompressobj(-15).decompress(data, x["usize"] + 1)
        elif meth == 0:
            raw = data
        else:
            raise ValueError("method %d" % meth)
        if len(raw) != x["usize"] or (zlib.crc32(raw) & 0xFFFFFFFF) != x["crc32"]:
            raise ValueError("size or CRC mismatch for " + name)
        dst = out_root / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)
        out.append({"name": name, "crc32": "%08x" % x["crc32"], "bytes": len(raw),
                    "sha256": common.sha256_bytes(raw)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--member-regex", help="re-fetch only the wanted members whose name matches, one range per member")
    ap.add_argument("--purpose", help="reason recorded with every request of this run (for example a re-fetch)")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    head = common.protocol_head(paths)
    runs, members, tails = build_plan(paths)
    if a.member_regex:
        import re
        rx = re.compile(a.member_regex)
        sel = []
        for r in runs:
            for name in r["members"]:
                if rx.search(name):
                    x = next(m for m in members if m["name"] == name and m["file_id"] == r["file_id"])
                    sel.append(dict(r, start=x["lho"], end=x["end"], members=[name]))
        runs = sel
    raw = Path(paths["raw"]) / "gait120"
    (raw / "ranges").mkdir(parents=True, exist_ok=True)
    plan = {"protocol_head": head, "runs": len(runs), "members": len(members),
            "bytes": sum(r["end"] - r["start"] for r in runs),
            "member_compressed_bytes": sum(x["csize"] for x in members), "tails": tails}
    print(json.dumps({k: v for k, v in plan.items() if k != "tails"}))
    common.atomic_write_json(raw / ("PLAN-%s.json" % ("refetch" if a.member_regex else "full")),
                             dict(plan, member_regex=a.member_regex, run_list=[{k: v for k, v in r.items()} for r in runs]))
    if a.plan_only:
        return
    by_name = {x["name"]: x for x in members}
    pacer = common.Pacer(1.05)
    done = 0
    for r in runs:
        if (raw / "STOP-429.json").exists():
            sys.exit("stopped earlier on 429")
        tag = "%d_%d_%d" % (r["file_id"], r["start"], r["end"])
        sidecar = raw / "ranges" / (tag + ".done.json")
        if sidecar.exists():
            continue
        url = "https://api.figshare.com/v2/file/download/%d" % r["file_id"]
        rng = "bytes=%d-%d" % (r["start"], r["end"] - 1)
        tmp = raw / "ranges" / (tag + ".part")
        attempt = 0
        while True:
            attempt += 1
            try:
                res = common.http_get(url, pacer, headers={"Range": rng}, out_path=tmp, timeout=300)
                break
            except common.Stop429 as e:
                common.atomic_write_json(raw / "STOP-429.json", {"when": common.now_iso(), "url": url,
                                                                 "range": rng, "error": str(e)})
                common.log_download(paths, {"dataset": "gait120", "url": url, "range": rng, "status": 429,
                                            "bytes": 0, "sha256": None, "note": "stopped on 429; no retry"})
                sys.exit("429: stopped")
            except Exception as e:  # network error or 5xx: at most two more tries
                if attempt >= 3:
                    raise
                print("retry after error:", e, file=sys.stderr)
                pacer.wait("backoff")  # spacing only
        cr = res["headers"].get("Content-Range") or res["headers"].get("content-range")
        want_cr = "bytes %d-%d/%d" % (r["start"], r["end"] - 1, r["archive_bytes"])
        if res["status"] != 206 or cr != want_cr or res["bytes"] != r["end"] - r["start"]:
            tmp.unlink(missing_ok=True)
            raise SystemExit("unexpected response %s %s (want %s), %d bytes" % (res["status"], cr, want_cr, res["bytes"]))
        blob = tmp.read_bytes()
        got = extract(blob, r["start"], by_name, r["members"], raw / "members")
        common.log_download(paths, {
            "dataset": "gait120", "url": url, "final_url": res["final_url"], "hosts": res["hosts"],
            "range": rng, "status": res["status"], "content_range": cr, "bytes": res["bytes"],
            "sha256": res["sha256"], "archive": r["archive"], "figshare_file_id": r["file_id"],
            "person": r["person"], "members": len(got), "member_crc32_checked": True,
            "raw_location": "RAM-backed temporary folder; range blob deleted after members were checked",
            **({"purpose": a.purpose} if a.purpose else {})})
        tmp.unlink()
        common.atomic_write_json(sidecar, {"range": rng, "sha256": res["sha256"], "bytes": res["bytes"],
                                           "members": got})
        done += 1
        if a.limit and done >= a.limit:
            break
    print(json.dumps({"ranges_fetched_now": done}))


if __name__ == "__main__":
    main()
