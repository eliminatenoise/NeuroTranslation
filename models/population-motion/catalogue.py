"""Bind selected recordings to the published DANDI release and its object fingerprints."""
from pathlib import Path
import json
import requests

ROOT = Path(__file__).resolve().parent
API = "https://api.dandiarchive.org/api"
VERSION = f"{API}/dandisets/000978/versions/0.240511.0307"


def save(path, value):
    data = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path.exists() and path.read_text() != data:
        raise ValueError(f"Recorded evidence differs for {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)


def get(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    protocol = json.loads((ROOT / "protocol.json").read_text())
    release = get(VERSION + "/")
    assert release["license"] == ["spdx:CC-BY-4.0"] and release["doi"] == protocol["doi"]
    assert release["access"][0]["status"] == "dandi:OpenAccess"
    members = get(VERSION + "/assets/?page_size=100")
    assert members["count"] == len(members["results"]) == 9 and members["next"] is None
    pins = {}
    for rat, binding in protocol["asset_mapping"].items():
        member = next(a for a in members["results"] if a["path"] == binding["path"])
        assert all(member[k] == v for k, v in binding.items())
        asset = get(f"{API}/assets/{member['asset_id']}/")
        assert asset["contentSize"] == member["size"] and asset["path"] == member["path"]
        assert asset["access"][0]["status"] == "dandi:OpenAccess"
        pins[rat] = dict(**binding, sha256=asset["digest"]["dandi:sha2-256"],
                         etag=asset["digest"]["dandi:dandi-etag"],
                         url=next(u for u in asset["contentUrl"] if u.startswith("https://dandiarchive.s3")))
    save(ROOT/"source/catalogue.json", {"doi":release["doi"],"source":VERSION+"/",
         "citation":release["citation"],"license":release["license"],"members":pins})


if __name__ == "__main__":
    main()
