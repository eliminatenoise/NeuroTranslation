"""Rebuild the offline data script, checksums and optional ZIP with the Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
FILES = [
    "index.html", "README.md", "NOTICE.md", "CC0.txt", "build.py",
    "Open on Linux.sh", "Open on macOS.command", "Open on Windows.cmd",
    "src/style.css", "src/app.js", "src/study.js", "src/predict.js",
    "method/weights.json", "method/parity.json", "method/development.json", "method/measured.json",
    "method/assessment.json", "method/protocol.md", "method/provenance.json",
]


def load(name):
    return json.loads((ROOT / name).read_bytes())


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def build(archive=None):
    sources = load("method/provenance.json")
    for filename, key in [("weights", "model_weights_sha256"), ("parity", "synthetic_fixtures_sha256"),
                          ("development", "public_development_projection_sha256"), ("assessment", "public_assessment_projection_sha256")]:
        if sha("method/" + filename + ".json") != sources[key]:
            raise ValueError(f"Changed scientific export: {filename}")
    payload = {name: load(f"method/{name}.json") for name in ["weights", "development", "assessment"]}
    compact = json.dumps(payload, allow_nan=False, ensure_ascii=True, separators=(",", ":"))
    (ROOT / "src/study.js").write_bytes(("const CERVICAL_STUDY = " + compact + ";\n").encode())
    (ROOT / "SHA256SUMS").write_bytes(("".join(f"{sha(name)}  {name}\n" for name in sorted(FILES))).encode())
    if archive:
        members = sorted([*FILES, "SHA256SUMS"])
        if archive.resolve() in {(ROOT / name).resolve() for name in members}:
            raise ValueError("Choose a separate ZIP destination.")
        with ZipFile(archive, "w") as out:
            for name in members:
                item = ZipInfo("cervical-forecast/" + name, (2026, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = (0o100755 if name.endswith((".sh", ".command")) else 0o100644) << 16
                out.writestr(item, (ROOT / name).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path)
    build(parser.parse_args().zip)
