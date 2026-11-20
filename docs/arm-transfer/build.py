"""Build the offline reader from the bundled scientific files. Python 3.10+."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
APP = ["build.py", "README.md", "NOTICE.md", "CC0.txt", "CC-BY-4.0.txt", "index.html",
       "Open on Linux.sh", "Open on macOS.command", "Open on Windows.cmd",
       "src/page.html", "src/style.css", "src/charts.js", "src/app.js"]
SCIENCE = ["predict.py", "predict.js", "model.json", "example.json", "development-summary.json", "assessment-summary.json",
           "projection-manifest.json", "freeze.json", "PROTOCOL.md"]
EXECUTABLE = {"Open on Linux.sh", "Open on macOS.command"}


def read_data(name):
    return json.loads((ROOT / "method" / (name + ".json")).read_bytes())


def embedded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")


def build(archive):
    reports = {"development": read_data("development-summary"), "assessment": read_data("assessment-summary")}
    freeze = read_data("freeze")
    frozen_hash = hashlib.sha256((ROOT / "method/freeze.json").read_bytes()).hexdigest()
    for group, names in [("source", ("predict.py", "predict.js", "PROTOCOL.md")),
                         ("products", ("model.json", "example.json"))]:
        for name in names:
            actual = hashlib.sha256((ROOT / "method" / name).read_bytes()).hexdigest()
            if actual != freeze[group][name]:
                raise ValueError(name + " differs from the frozen study.")
    projection = read_data("projection-manifest")
    if projection["format"] != "cued-arm-public-projections-v1" or projection["freeze_sha256"] != frozen_hash or projection["model_sha256"] != freeze["products"]["model.json"]:
        raise ValueError("Projection manifest and frozen fit differ.")
    for name, report in reports.items():
        filename = name + "-summary.json"
        expected = projection["public_reports"][filename]
        if hashlib.sha256((ROOT / "method" / filename).read_bytes()).hexdigest() != expected["sha256"] or report["source_report_sha256"] != expected["source_report_sha256"]:
            raise ValueError(filename + " differs from the public projection manifest.")
        if report["projection_format"] != "cued-arm-cohort-v1" or report["freeze_sha256"] != frozen_hash:
            raise ValueError(name + " is not a cohort projection of the frozen study.")
    if reports["development"]["source_report_sha256"] != freeze["products"]["development.json"]:
        raise ValueError("Development summary and original fit differ.")
    content = (ROOT / "src/page.html").read_text(encoding="utf-8")
    for tag, value in [("__MODEL__", read_data("model")), ("__REPORTS__", reports), ("__EXAMPLE__", read_data("example"))]:
        if content.count(tag) != 1:
            raise ValueError("Missing or duplicated template field " + tag)
        content = content.replace(tag, embedded(value))
    (ROOT / "index.html").write_bytes(content.encode("utf-8"))
    public = sorted([*APP, *("method/"+name for name in SCIENCE)])
    checksums = "".join(hashlib.sha256((ROOT / name).read_bytes()).hexdigest()+"  "+name+"\n" for name in public)
    (ROOT / "SHA256SUMS").write_bytes(checksums.encode("utf-8"))
    if archive:
        files = sorted([*public, "SHA256SUMS"])
        if archive.resolve() in {(ROOT / name).resolve() for name in files}:
            raise ValueError("Choose a separate file for the archive.")
        with ZipFile(archive, "w") as out:
            for name in files:
                member = ZipInfo("arm-transfer/"+name, (2026, 1, 1, 0, 0, 0))
                member.create_system = 3
                member.external_attr = (0o100755 if name in EXECUTABLE else 0o100644) << 16
                out.writestr(member, (ROOT / name).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Also write a portable ZIP to this path.")
    build(parser.parse_args().zip)
