"""Rebuild the source and weights ZIP from the declared public file inventory."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import zipfile

TOOLS = Path(__file__).resolve().parent
MODELS = TOOLS.parents[1] / "models"
PACKAGES = {
    "0.0": ("neurotranslate-0.0", "package-files.json", (2026, 11, 21, 0, 0, 0)),
    "0.1": ("neurotranslate-0.1", "package-files-0.1.json", (2026, 11, 22, 0, 0, 0)),
    "force-baselines": ("force-baselines", "package-files-force-baselines.json", (2026, 11, 22, 0, 0, 0)),
}


def contents(root, inventory):
    members = json.loads((TOOLS / inventory).read_text(encoding="utf-8"))
    if members != sorted(set(members)) or "SHA256SUMS" in members:
        raise ValueError("The inventory must contain each source member once.")
    data = {}
    for name in members:
        path = root / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.is_symlink() or not path.is_file():
            raise ValueError(name)
        data[name] = path.read_bytes()
    data["SHA256SUMS"] = "".join(hashlib.sha256(content).hexdigest() + "  " + name + "\n"
                                 for name, content in data.items()).encode()
    return data


def run(check=False, edition="0.0"):
    folder, inventory, timestamp = PACKAGES[edition]
    root = MODELS / folder
    destination = root.with_name(root.name + ".zip")
    data = contents(root, inventory)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name in sorted(data):
            row = zipfile.ZipInfo(f"{root.name}/{name}", timestamp)
            row.create_system = 3
            mode = 0o755 if name.endswith((".sh", ".command")) else 0o644
            row.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(row, data[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    if check:
        if (root / "SHA256SUMS").read_bytes() != data["SHA256SUMS"] or destination.read_bytes() != output.getvalue():
            raise SystemExit("Archive or SHA256SUMS differs. Rebuild it with pack.py.")
    else:
        (root / "SHA256SUMS").write_bytes(data["SHA256SUMS"])
        destination.write_bytes(output.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--edition", choices=PACKAGES, default="0.0")
    args = parser.parse_args()
    run(args.check, args.edition)
