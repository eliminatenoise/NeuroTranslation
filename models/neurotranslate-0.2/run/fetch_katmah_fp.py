"""P1: Katmah et al. force-plate CSVs, identifiers 1-40 at 0.5 m/s only (PhysioNet r0ea-7161 v1.0.0).

PROTOCOL.json downloads_planned.P1_training: "Katmah force-plate CSVs, identifiers 1-40 at 0.5 m/s,
measured on one file first". Identifiers 41-52 (consumed knee test) and 53-59 (reserved) and the
0.75 and 1.0 m/s files are never requested. The publisher's SHA256SUMS.txt is read first and every
file must match its listed digest. One request per second per host; a 429 stops the run.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

BASE = "https://physionet.org/files/multimodal-gait-dataset/1.0.0/"
IDS = list(range(1, 41))
MAX_TOTAL_BYTES = 3_000_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    head = common.protocol_head(paths)
    out = Path(paths["raw"]) / "katmah"
    out.mkdir(parents=True, exist_ok=True)
    pacer = common.Pacer(1.05)
    try:
        sums = common.http_get(BASE + "SHA256SUMS.txt", pacer)
    except common.Stop429:
        sys.exit("429 on SHA256SUMS.txt: stopped")
    if sums["status"] != 200:
        sys.exit("SHA256SUMS.txt status %s" % sums["status"])
    (out / "SHA256SUMS.txt").write_bytes(sums["body"])
    common.log_download(paths, {"dataset": "katmah", "url": BASE + "SHA256SUMS.txt", "final_url": sums["final_url"],
                                "hosts": sums["hosts"], "range": None, "status": sums["status"],
                                "bytes": sums["bytes"], "sha256": sums["sha256"],
                                "purpose": "publisher digest list (metadata)"})
    listed = {}
    for line in sums["body"].decode().splitlines():
        p = line.split(None, 1)
        if len(p) == 2:
            listed[p[1].strip()] = p[0]
    names = ["Dataset/FP_Data/FP_S%d_0.5.csv" % i for i in IDS]
    missing = [n for n in names if n not in listed]
    first_bytes = None
    got = []
    for k, name in enumerate(names):
        if name in missing:
            continue
        dst = out / Path(name).name
        if dst.exists() and common.sha256_file(dst) == listed[name]:
            continue
        try:
            res = common.http_get(BASE + name, pacer, out_path=dst)
        except common.Stop429 as e:
            common.log_download(paths, {"dataset": "katmah", "url": BASE + name, "status": 429, "bytes": 0,
                                        "sha256": None, "note": "stopped on 429; no retry"})
            sys.exit(str(e))
        ok = res["status"] == 200 and res["sha256"] == listed[name]
        common.log_download(paths, {"dataset": "katmah", "url": BASE + name, "final_url": res["final_url"],
                                    "hosts": res["hosts"], "range": None, "status": res["status"],
                                    "bytes": res["bytes"], "sha256": res["sha256"],
                                    "publisher_sha256_match": ok, "identifier": IDS[k], "speed_m_s": 0.5,
                                    "raw_location": "RAM-backed temporary folder; deleted after tokenising"})
        if not ok:
            dst.unlink(missing_ok=True)
            sys.exit("digest or status mismatch for " + name)
        got.append(name)
        if first_bytes is None:
            first_bytes = res["bytes"]
            est = first_bytes * len(names)
            print(json.dumps({"measured_first_file_bytes": first_bytes, "estimated_total_bytes": est}))
            if est > MAX_TOTAL_BYTES:
                sys.exit("estimated size above the cap; stopped after the first file")
    common.atomic_write_json(out / "FETCH-RESULT.json", {"protocol_head": head, "fetched_now": got,
                                                         "not_listed_by_publisher": missing})
    print(json.dumps({"fetched_now": len(got), "not_listed": missing}))


if __name__ == "__main__":
    main()
