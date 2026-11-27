"""Q1 licence check at P2: read each deposit's licence as served now and record sha256 digests.

For every dataset the deposit's own metadata endpoint (or licence file) is read once and the licence it
declares is recorded with the sha256 of the exact bytes served. The declaration is normalised to an SPDX
identifier, and the plain-text legal code of that licence is read once per distinct URL and hashed (for a
PhysioNet deposit the deposit's own LICENSE.txt is the licence text). The deposit's DataCite record gives
the attribution details (creators, title, publisher, year, DOI) that the NOTICE of a release needs, with
the notice each licence asks for. Metadata only: no recording byte is requested. One request per second
per host (shared across processes); a 429 stops the run.

  python licences.py --paths PATHS.json [DATASET ...]
  python licences.py --paths PATHS.json --refresh-parts   # rewrite Q1 and the licence fields of the
                                                          # manifest parts from the stored records
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
    # neural part
    "ds003739": {"kind": "openneuro",
                 "url": "https://raw.githubusercontent.com/OpenNeuroDatasets/ds003739/1.0.3/dataset_description.json"},
    "ofner": {"kind": "zenodo", "url": "https://zenodo.org/api/records/834976"},
    "hygrip": {"kind": "figshare", "url": "https://api.figshare.com/v2/articles/12383639/versions/1"},
    "sabes": {"kind": "zenodo", "url": "https://zenodo.org/api/records/3854034"},
    "wtrack": {"kind": "dandi", "url": "https://api.dandiarchive.org/api/dandisets/000978/versions/0.240511.0307/"},
    "area2": {"kind": "dandi", "url": "https://api.dandiarchive.org/api/dandisets/000127/versions/0.220113.0359/"},
    "falcon_m1": {"kind": "dandi", "url": "https://api.dandiarchive.org/api/dandisets/000941/versions/0.241029.1405/"},
}
LICENCE_URLS = {"spdx:CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/legalcode.txt",
                "CC0": "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt"}
SPDX_TEXT = {"CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/legalcode.txt",
             "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt",
             "MIT": "https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT.txt"}
DATACITE = "https://api.datacite.org/dois/"
# the DOI each deposit is cited by (the deposit's own DOI where it states one)
DOIS = {"gait120": "10.6084/m9.figshare.27677016.v1", "schreiber_moissenet": "10.6084/m9.figshare.7734767.v8",
        "moreira": "10.6084/m9.figshare.14241812.v1", "van_criekinge": "10.6084/m9.figshare.24192480.v1",
        "izmir": "10.48623/aperta.286865", "katmah": "10.13026/r0ea-7161", "hyser": "10.13026/hxan-pe94",
        "cemhsey": "10.5281/zenodo.15077957", "ds003739": "10.18112/openneuro.ds003739.v1.0.3",
        "ofner": "10.5281/zenodo.834976", "hygrip": "10.6084/m9.figshare.12383639.v1",
        "sabes": "10.5281/zenodo.3854034", "wtrack": "10.48324/dandi.000978/0.240511.0307",
        "area2": "10.48324/dandi.000127/0.220113.0359", "falcon_m1": "10.48324/dandi.000941/0.241029.1405"}
NOTICE_RULE = {
    "CC-BY-4.0": "credit the creators, the title and the DOI, name CC BY 4.0 with a link to its legal code, and state "
                 "the changes made (CC BY 4.0 section 3(a))",
    "CC0-1.0": "no attribution is required; the source is credited as good practice",
    "ODC-By-1.0": "keep the licence notice and attribute the database as its makers ask (ODC-By 1.0 section 4.3), for "
                  "example: 'Contains information from TITLE (DOI), which is made available under the Open Data Commons "
                  "Attribution License v1.0'",
    "MIT": "include the copyright notice and the MIT permission notice in all copies or substantial portions",
}


def spdx_of(kind, info, body):
    """Normalise a deposit's declared licence to an SPDX identifier (None if it is not recognised)."""
    d = str(info.get("declared") or "").strip().lower()
    lo = info.get("licence_object")
    url = str(info.get("licence_url") or (lo.get("url") if isinstance(lo, dict) else "") or "").lower()
    if kind == "physionet":
        t = body.decode("utf-8", "replace")
        if "Open Data Commons Attribution License" in t or "ODC Attribution License" in t:
            return "ODC-By-1.0" if re.search(r"(v1\.0|1\.0)", t) else None
        if "Creative Commons Attribution 4.0 International Public License" in t:
            return "CC-BY-4.0"
        return None
    if d in ("cc0", "cc0-1.0", "cc0 1.0") or "publicdomain/zero/1.0" in url:
        return "CC0-1.0"
    if d in ("cc-by-4.0", "spdx:cc-by-4.0", "cc by 4.0") or (d == "cc by" and "licenses/by/4.0" in url):
        return "CC-BY-4.0"
    if d == "mit":
        return "MIT"
    return None


def datacite(doi, pacer):
    res = common.http_get(DATACITE + doi, pacer, headers={"Accept": "application/vnd.api+json"})
    a = json.loads(res["body"])["data"]["attributes"]
    return {"doi": a.get("doi"), "url": "https://doi.org/" + a.get("doi", doi),
            "title": (a.get("titles") or [{}])[0].get("title"),
            "creators": [c.get("name") for c in a.get("creators") or []],
            "publisher": a.get("publisher") if isinstance(a.get("publisher"), str) else (a.get("publisher") or {}).get("name"),
            "year": a.get("publicationYear"), "version": a.get("version"),
            "rights": [{"rights": r.get("rights"), "uri": r.get("rightsUri"), "spdx": r.get("rightsIdentifier")}
                       for r in a.get("rightsList") or []],
            "source": DATACITE + doi, "response_sha256": res["sha256"], "read_at": common.now_iso()}


def notice(spdx, att):
    """The notice text a release would carry for this source (filled from the DataCite record)."""
    if not att:
        return None
    who = "; ".join(att["creators"]) if att.get("creators") else "the creators"
    cite = "%s (%s). %s. %s. %s" % (who, att.get("year"), att.get("title"), att.get("publisher"), att.get("url"))
    out = {"citation": cite, "rule": NOTICE_RULE.get(spdx)}
    if spdx == "MIT":
        out["copyright_line"] = "Copyright (c) %s %s" % (att.get("year"), who)
        out["copyright_line_source"] = "formed from the deposit's creators and publication year (the deposit states no "\
                                       "separate copyright line)"
    if spdx == "ODC-By-1.0":
        out["attribution_statement"] = ("Contains information from %s (%s), which is made available under the Open Data "
                                        "Commons Attribution License v1.0." % (att.get("title"), att.get("url")))
    return out


def q1_gate(lic):
    """The Q1 record of a manifest part, built from a stored licence record."""
    return {"pass": bool(lic["allowed_by_Q1"]), "declared": lic["declared_licence"], "spdx": lic.get("spdx"),
            "deposit_endpoint": lic["deposit_endpoint"], "response_sha256": lic["response_sha256"],
            "licence_object_sha256": lic.get("licence_object_sha256"), "licence_text": lic.get("licence_text"),
            "attribution": lic.get("attribution"), "notice": lic.get("notice"), "checked_at": lic["checked_at"]}


def refresh_parts(paths):
    """Rewrite Q1 and the licence fields of every manifest part from the stored licence records."""
    out = []
    for f in sorted(Path(paths["manifest_parts"]).glob("*.json")):
        part = json.loads(f.read_text())
        lf = Path(paths["licences"]) / (part["dataset"] + ".json")
        if not lf.exists():
            continue
        lic = json.loads(lf.read_text())
        part["licence"] = lic.get("spdx") or lic["declared_licence"]
        part["licence_as_declared"] = lic["declared_licence"]
        q = part.setdefault("qualification", {})
        q["Q1_licence"] = q1_gate(lic)
        order = ["Q1_licence", "Q2_role", "Q3_access", "Q4_clock", "Q5_labels", "Q6_causality"]
        part["qualification"] = {k: q[k] for k in order if k in q}
        if all(k in part["qualification"] for k in order):
            part["qualified"] = all(g["pass"] for g in part["qualification"].values())
        common.atomic_write_json(f, part)
        out.append((part["dataset"], part["licence"], (lic.get("licence_text") or {}).get("sha256")))
    return out


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
    if kind == "dandi":
        lic = d.get("license") or []
        name = lic[0] if lic else None
        return {"declared": name, "licence_url": LICENCE_URLS.get(name), "licence_object": lic,
                "licence_object_sha256": common.sha256_text(json.dumps(lic, sort_keys=True)),
                "doi": d.get("doi"), "version": d.get("version"), "title": d.get("name")}
    if kind == "openneuro":
        name = d.get("License")
        return {"declared": name, "licence_url": LICENCE_URLS.get(name), "licence_object": {"License": name},
                "licence_object_sha256": common.sha256_text(json.dumps({"License": name}, sort_keys=True)),
                "doi": d.get("DatasetDOI"), "version": "1.0.3", "title": d.get("Name")}
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
    ap.add_argument("--refresh-parts", action="store_true")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    if a.refresh_parts:
        for row in refresh_parts(paths):
            print(json.dumps(row))
        return
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
        spdx = spdx_of(dep["kind"], info, res["body"])
        lic_text = None
        lurl = SPDX_TEXT.get(spdx)
        if dep["kind"] == "physionet":
            lic_text = {"url": dep["url"], "final_url": res["final_url"], "status": res["status"], "bytes": res["bytes"],
                        "sha256": res["sha256"], "what": "the deposit's own LICENSE.txt (the licence text)"}
        elif lurl:
            if lurl not in texts:
                try:
                    t = common.http_get(lurl, pacer)
                    texts[lurl] = {"url": lurl, "final_url": t["final_url"], "status": t["status"],
                                   "bytes": t["bytes"], "sha256": t["sha256"]}
                except common.Stop429 as e:
                    sys.exit(str(e))
                except Exception as e:  # record, do not retry
                    texts[lurl] = {"url": lurl, "error": str(e)}
            lic_text = dict(texts[lurl], what="plain-text legal code of " + spdx)
        try:
            att = datacite(DOIS[ds], pacer) if ds in DOIS else None
        except common.Stop429 as e:
            sys.exit(str(e))
        except Exception as e:  # record, do not retry
            att = {"doi": DOIS.get(ds), "error": str(e)}
        declared = str(info.get("declared") or "")
        allowed = any(k.lower() in declared.lower() for k in ALLOWED)
        if dep["kind"] == "physionet":
            allowed = bool(re.search(r"(Creative Commons Attribution 4\.0|Open Data Commons Attribution)", res["body"].decode("utf-8", "replace")))
        rec = {"dataset": ds, "checked_at": common.now_iso(), "deposit_endpoint": dep["url"],
               "final_url": res["final_url"], "status": res["status"], "response_bytes": res["bytes"],
               "response_sha256": res["sha256"], "declared_licence": info.get("declared"),
               "licence_object": info.get("licence_object"), "licence_object_sha256": info.get("licence_object_sha256"),
               "licence_text": lic_text, "doi": info.get("doi"), "version": info.get("version"),
               "spdx": spdx, "attribution": att, "notice": notice(spdx, att) if att and "error" not in att else None,
               "allowed_by_Q1": allowed and spdx is not None}
        common.atomic_write_json(out / (ds + ".json"), rec)
        print(json.dumps({k: rec[k] for k in ("dataset", "declared_licence", "spdx", "allowed_by_Q1", "response_sha256")}
                         | {"text_sha256": (lic_text or {}).get("sha256"), "creators": len((att or {}).get("creators") or [])}))


if __name__ == "__main__":
    main()
