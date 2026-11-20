"""Make a cohort report without linking individual outcomes across comparisons."""
import argparse
import hashlib
import json
from pathlib import Path


def project(raw, summary, freeze):
    original = raw.read_bytes()
    report = json.loads(original)
    keys = ("format","stage","n_people","n_trials","complete","methods","gates")
    aggregate = {k:report[k] for k in keys}
    aggregate["contrasts"] = {}
    for k,v in report["contrasts"].items():
        item = {name:value for name,value in v.items() if name!="paired_differences"}
        item["paired_differences_sorted"] = sorted(v["paired_differences"])
        aggregate["contrasts"][k] = item
    aggregate["underlying_report_sha256"] = hashlib.sha256(original).hexdigest()
    seal = json.loads(freeze.read_bytes())
    aggregate["freeze_sha256"] = hashlib.sha256(freeze.read_bytes()).hexdigest()
    aggregate["model_sha256"] = seal["product"]["model.json"]
    if report["stage"] == "fourth_run":
        if any(report[k]!=aggregate[k] for k in ("freeze_sha256","model_sha256")):
            raise ValueError("Assessment does not match the supplied freeze")
    elif seal["product"]["development.json"] != aggregate["underlying_report_sha256"]:
        raise ValueError("Development report differs from the frozen original")
    with summary.open("x",encoding="utf-8") as f:
        json.dump(aggregate,f,indent=2,allow_nan=False)
        f.write("\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw",type=Path)
    p.add_argument("summary",type=Path)
    p.add_argument("--freeze",type=Path,default=Path(__file__).resolve().parent/"freeze.json")
    a = p.parse_args()
    project(a.raw,a.summary,a.freeze)
