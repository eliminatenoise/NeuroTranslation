"""Q1 licence check at P2: read each deposit's licence as served now and record sha256 digests.

For every dataset of this part of P2 the deposit's own metadata endpoint (or licence file) is read
once, the licence it declares is recorded with the sha256 of the exact bytes served, and the licence
text at the declared licence URL is read once per distinct URL and hashed. Metadata only: no
recording byte is requested. One request per second per host; a 429 stops the run.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

ALLOWED = ("CC0", "CC BY", "CC-BY", "ODC-BY", "ODC-By", "MIT", "CDLA-Permissive", "PDDL", "Creative Commons Attribution",
           "Open Data Commons Attribution", "Public Domain Dedication", "cc-by", "odc-by", "cc0")
DEPOSITS = {
    "gait120": {"kind": "figshare", "url": "https://api.figshare.com/v2/articles/27677016/versions/1"},
    "schreiber_moissenet": {"kind": "figshare", "url": "https://api.figshare.com/v2/articles/7734767/versions/8"},
    "moreira": {"kind": "figshare", "url": "https://api.figshare.com/v2/articles/14241812/versions/1"},
    "van_criekinge": {"kind": "figshare", "url": "https://api.figshare.com/v2/articles/24192480/versions/1"},
    "izmir": {"kind": "invenio", "url": "https://aperta.ulakbim.gov.tr/api/records/286866"},
    "katmah": {"kind": "physionet", "url": "https://physionet.org/files/multimodal-gait-dataset/1.0.0/LICENSE.txt"},
    "hyser": {"kind": "physionet", "url": "https://physionet.org/files/hd-semg/2.0.0/LICENSE.txt"},
    "cemhsey": {"kind": "zenodo", "url": "https://zenodo.org/api/records/15077957"},
}


def extract(kind, body):
    if kind == "physionet":
        text = body.decode("utf-8", "replace")
        first = text.strip().splitlines()[0] if text.strip() else ""
        return {"declared": first[:200], "licence_object_sha256": common.sha256_bytes(body), "licence_url": None}
    d = json.loads(body)
    if kind == "figshare":
        lic = d.get("license") or {}
        return {"declared": lic.get("name"), "licence_url": lic.get("url"),
                "licence_object": lic, "licence_object_sha256": common.sha256_text(json.dumps(lic, sort_keys=True)),
                "doi": d.get("doi"), "version": d.get("version"), "title": d.get("title")}
    if kind == "zenodo":
        md = d.get("metadata", {})
        lic = md.get("license") or md.get("rights") or {}
        return {"declared": lic.get("id") if isinstance(lic, dict) else str(lic), "licence_url": None,
                "licence_object": lic, "licence_object_sha256": common.sha256_text(json.dumps(lic, sort_keys=True)),
                "doi": d.get("doi") or md.get("doi"), "version": md.get("version"), "title": md.get("title")}
    if kind == "invenio":
        md = d.get("metadata", {})
        lic = md.get("license") or md.get("rights") or md.get("access_right_category") or {}
        return {"declared": lic.get("id") if isinstance(lic, dict) else str(lic), "licence_url": lic.get("url") if isinstance(lic, dict) else None,
                "licence_object": lic, "licence_object_sha256": common.sha256_text(json.dumps(lic, sort_keys=True)),
                "doi": md.get("doi"), "title": md.get("title")}
    raise ValueError(kind)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("datasets", nargs="*")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    out = Path(paths["licences"])
    out.mkdir(parents=True, exist_ok=True)
    pacer = common.Pacer(1.05)
    texts = {}
    for ds in (a.datasets or list(DEPOSITS)):
        dep = DEPOSITS[ds]
        try:
            res = common.http_get(dep["url"], pacer, headers={"Accept": "application/json"})
        except common.Stop429 as e:
            sys.exit(str(e))
        info = extract(dep["kind"], res["body"])
        lic_text = None
        lurl = info.get("licence_url")
        if lurl:
            if lurl not in texts:
                try:
                    t = common.http_get(lurl, pacer)
                    texts[lurl] = {"url": lurl, "final_url": t["final_url"], "status": t["status"],
                                   "bytes": t["bytes"], "sha256": t["sha256"]}
                except common.Stop429 as e:
                    sys.exit(str(e))
                except Exception as e:  # record, do not retry
                    texts[lurl] = {"url": lurl, "error": str(e)}
            lic_text = texts[lurl]
        declared = str(info.get("declared") or "")
        allowed = any(k.lower() in declared.lower() for k in ALLOWED)
        if dep["kind"] == "physionet":
            allowed = bool(re.search(r"(Creative Commons Attribution 4\.0|Open Data Commons Attribution)", res["body"].decode("utf-8", "replace")))
        rec = {"dataset": ds, "checked_at": common.now_iso(), "deposit_endpoint": dep["url"],
               "final_url": res["final_url"], "status": res["status"], "response_bytes": res["bytes"],
               "response_sha256": res["sha256"], "declared_licence": info.get("declared"),
               "licence_object": info.get("licence_object"), "licence_object_sha256": info.get("licence_object_sha256"),
               "licence_text": lic_text, "doi": info.get("doi"), "version": info.get("version"),
               "allowed_by_Q1": allowed}
        common.atomic_write_json(out / (ds + ".json"), rec)
        print(json.dumps({k: rec[k] for k in ("dataset", "declared_licence", "allowed_by_Q1", "response_sha256")}))


if __name__ == "__main__":
    main()
