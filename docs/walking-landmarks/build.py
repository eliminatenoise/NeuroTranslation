"""Regenerate the offline page from its editable source and model bundle."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DATA = ROOT / "data"


def build():
    report = json.loads((DATA / "results.json").read_bytes())
    weights = json.loads((DATA / "weights.json").read_bytes())
    bundle = "const WALK_DATA=" + json.dumps(
        {"report": report, "weights": weights, "direction": json.loads((DATA / "direction-results.json").read_bytes())}, separators=(",", ":"), allow_nan=False
    ) + ";\n"
    scripts = ["example.js", "predict.js", "scene.js", "app.js"]
    bundle += "\n".join((SRC / script).read_text() for script in scripts)
    if "</script" in bundle.lower():
        raise ValueError("Embedded script contains an HTML end tag.")
    html = (SRC / "page.html").read_text().replace("/*__STYLE__*/", (SRC / "style.css").read_text())
    licence = base64.b64encode((ROOT / "DATA-LICENCE.txt").read_bytes()).decode("ascii")
    note = base64.b64encode((ROOT / "NOTICE.md").read_bytes()).decode("ascii")
    return html.replace("/*__BUNDLE__*/", bundle).replace("__SOURCE_LICENCE__", licence).replace("__NOTICE__", note)


def write_archive(destination):
    """Repack the release from its verified SHA256SUMS inventory."""
    manifest = ROOT / "SHA256SUMS"
    members = ["SHA256SUMS"]
    for line in manifest.read_text().splitlines():
        sha, name = line.split("  ", 1)
        source = ROOT / name
        if not source.resolve().is_relative_to(ROOT) or hashlib.sha256(source.read_bytes()).hexdigest() != sha:
            raise ValueError("Archive member failed verification: " + name)
        members.append(name)
    if destination.resolve() in {(ROOT / name).resolve() for name in members}:
        raise ValueError("Choose a ZIP path outside the listed release files.")
    with ZipFile(destination, "w") as archive:
        for name in sorted(members):
            entry = ZipInfo("walking-landmarks/" + name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            executable = name in ("Open on Linux.sh", "Open on macOS.command")
            entry.external_attr = (0o100755 if executable else 0o100644) << 16
            archive.writestr(entry, (ROOT / name).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--zip", type=Path, help="Rebuild the verified ZIP at this path.")
    args = cli.parse_args()
    (ROOT / "index.html").write_text(build())
    if args.zip:
        write_archive(args.zip)
