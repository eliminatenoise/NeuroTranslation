"""Download or verify one predefined group of Ofner right-arm execution recordings."""
import argparse
from pathlib import Path
import os
import tempfile
from urllib.request import Request, urlopen

from ofner_transfer import API, FILES, digests, filename

PEOPLE = {"fitting": range(1, 8), "assessment": range(8, 13)}


def check_file(path, expected):
    with path.open("rb") as source:
        size, md5, sha256 = digests(source)
    if (size, md5) != expected:
        raise ValueError(f"{path.name} differs from the publisher's size or MD5.")
    return sha256


def original(cache, person, run_number, check_only):
    name = filename(person, run_number)
    path = cache / name
    expected = FILES[person][run_number - 1]
    if path.exists() or check_only:
        return check_file(path, expected)
    lock = cache / (name + ".lock")
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise RuntimeError(f"{name} is locked. Check whether another download is running.") from exc
    temporary = None
    try:
        if path.exists():
            return check_file(path, expected)
        url = f"{API}/files/{name}/content?download=1"
        request = Request(url, headers={"Accept-Encoding": "identity"})
        with tempfile.NamedTemporaryFile(dir=cache, prefix=name + ".", delete=False) as target:
            temporary = Path(target.name)
            with urlopen(request, timeout=120) as response:
                if response.status != 200:
                    raise ValueError(f"{name} requires a complete HTTP response.")
                size, md5, sha256 = digests(response, target)
        if (size, md5) != expected:
            raise ValueError(f"{name} download differs from the publisher's size or MD5.")
        if path.exists():
            return check_file(path, expected)
        os.replace(temporary, path)
        return sha256
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=PEOPLE, help="fitting S1–S7 or separate assessment S8–S12")
    parser.add_argument("directory", type=Path, help="folder for the original GDF files")
    parser.add_argument("--check-only", action="store_true", help="verify existing files without network access")
    args = parser.parse_args()
    if not args.check_only:
        args.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    for person in PEOPLE[args.group]:
        for run_number in (1, 2, 3):
            sha = original(args.directory, person, run_number, args.check_only)
            print(f"{sha}  {filename(person, run_number)}", flush=True)


if __name__ == "__main__":
    main()
