"""Verify the published WAY grip-force preview and its ZIP contents."""

import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile


BENCHMARK = Path(__file__).resolve().parent


def verify_bytes(data, entry, name):
    if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Contents differ from the manifest: {name}")


def verify():
    manifest = json.loads((BENCHMARK / "SOURCE.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        name = entry["path"]
        verify_bytes((BENCHMARK / name).read_bytes(), entry, name)

    package = manifest["package"]
    expected = {entry["path"]: entry for entry in package["members"]}
    with ZipFile(BENCHMARK / package["path"]) as archive:
        names = archive.namelist()
        if len(names) != len(expected) or set(names) != expected.keys():
            raise ValueError("ZIP contents differ from the manifest")
        for member in archive.infolist():
            entry = expected[member.filename]
            if member.file_size != entry["bytes"]:
                raise ValueError(f"Unexpected ZIP member size: {member.filename}")
            verify_bytes(archive.read(member), entry, member.filename)
    print(f"Verified {len(manifest['files'])} files and {len(expected)} ZIP members.")


if __name__ == "__main__":
    try:
        verify()
    except (OSError, ValueError, KeyError, BadZipFile) as error:
        raise SystemExit(str(error)) from error
