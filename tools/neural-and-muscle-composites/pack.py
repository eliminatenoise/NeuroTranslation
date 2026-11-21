"""Build or verify the portable study archive against its explicit member list."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL = REPO / "models/neural-and-muscle-composites"
SITE = REPO / "docs/neural-and-muscle-composites"
PACK = SITE / "study.zip"

def main(check):
    entries = json.loads((HERE/"package-files.json").read_bytes())
    if len(entries)!=len(set(entries)) or any(Path(f).is_absolute() or ".." in Path(f).parts for f in entries):
        raise ValueError("Archive member list contains duplicate or invalid paths")
    files = {}
    for name, source in entries.items():
        folder = {"models":MODEL,"docs":SITE}[source]
        path = folder/name
        if path.is_symlink() or not path.is_file():
            raise ValueError(name)
        files[name] = path.read_bytes()
    files["SHA256SUMS"] = "".join(f"{sha256(data).hexdigest()}  {name}\n" for name,data in sorted(files.items())).encode()
    if not check:
        with ZipFile(PACK,"w",compression=ZIP_DEFLATED,compresslevel=6) as archive:
            for name,data in sorted(files.items()):
                info = ZipInfo(name,(2026,11,21,0,0,0))
                info.compress_type = ZIP_DEFLATED
                info.create_system = 3
                mode = 0o755 if name.endswith((".sh",".command")) else 0o644
                info.external_attr = (0o100000|mode)<<16
                archive.writestr(info,data)
    with ZipFile(PACK) as archive:
        if len(archive.namelist())!=len(files) or sorted(archive.namelist())!=sorted(files) or archive.testzip():
            raise ValueError("Archive inventory differs")
        for name,data in files.items():
            if archive.read(name)!=data:
                raise ValueError(f"Archived bytes differ for {name}")
    print(f"{len(files)} verified archive members")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    main(parser.parse_args().check)
