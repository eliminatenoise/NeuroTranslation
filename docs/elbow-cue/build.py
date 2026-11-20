"""Build the offline elbow-cue experiment. Python 3.10+; standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
BASE = ["build.py", "LICENSE", "DATA-LICENCE.txt", "NOTICE.md", "README.md",
        "Open on Linux.sh", "Open on macOS.command", "Open on Windows.cmd",
        "src/page.html", "src/style.css", "src/predict.js", "src/chart.js", "src/app.js"]
SCIENCE = ["model.json", "scores.json", "protocol.json", "example.json", "example-results.json",
           "fit.py", "infer.py", "check_example.py", "ofner_source.py"]
INVENTORY = sorted(BASE + ["index.html"] + ["method/" + name for name in SCIENCE])


def render():
    assets = {"ELBOW_MODEL": "model", "ELBOW_SCORES": "scores", "ELBOW_EXAMPLE": "example"}
    lines = []
    for key, filename in assets.items():
        value = json.loads((ROOT / "method" / (filename + ".json")).read_bytes())
        lines.append("const " + key + "=" + json.dumps(value, separators=(",", ":"), allow_nan=False) + ";")
    lines.extend((ROOT / "src" / name).read_text(encoding="utf-8") for name in ["predict.js", "chart.js", "app.js"])
    script = "\n".join(lines)
    if "</script" in script.lower():
        raise ValueError("Embedded script end tag in source")
    page = (ROOT / "src/page.html").read_text(encoding="utf-8")
    return page.replace("/*__STYLE__*/", (ROOT / "src/style.css").read_text()).replace("/*__BUNDLE__*/", script)


def build(archive_path):
    (ROOT / "index.html").write_bytes(render().encode("utf-8"))
    manifest = "".join(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() + "  " + name + "\n" for name in INVENTORY)
    (ROOT / "SHA256SUMS").write_bytes(manifest.encode("utf-8"))
    if archive_path:
        if archive_path.resolve() in {(ROOT / name).resolve() for name in ["SHA256SUMS", *INVENTORY]}:
            raise ValueError("Choose a separate ZIP output file")
        with ZipFile(archive_path, "w") as archive:
            for name in sorted([*INVENTORY, "SHA256SUMS"]):
                member = ZipInfo("elbow-cue/" + name, (2026,1,1,0,0,0))
                member.create_system = 3
                executable = name in {"Open on Linux.sh", "Open on macOS.command"}
                member.external_attr = (0o100755 if executable else 0o100644) << 16
                archive.writestr(member, (ROOT / name).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Also write the deterministic portable archive here.")
    build(parser.parse_args().zip)
