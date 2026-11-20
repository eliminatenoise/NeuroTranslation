"""Fetch one verified Chowdhury recording without downloading the complete ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
CHUNK = 4 * 1024 * 1024


def sha256(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def fetch(date, dest):
    info = json.loads((HERE / "identities.json").read_bytes())
    member = info["sources"][date]
    dest.mkdir(parents=True, exist_ok=True)
    result = dest / member["file"]
    if result.exists():
        if result.stat().st_size == member["bytes"] and sha256(result) == member["sha256"]:
            return result
        raise ValueError(f"Existing {result} differs from the deposit")
    first, last = member["payload_inclusive"]
    if last - first + 1 != member["bytes"]:
        raise ValueError("Invalid byte extent")
    with NamedTemporaryFile(dir=dest, prefix=result.name + ".", suffix=".partial", delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            for start in range(first, last+1, CHUNK):
                end = min(last, start+CHUNK-1)
                expected = f"bytes {start}-{end}/{info['archive_bytes']}"
                req = Request(info["archive_url"], headers={"Range":f"bytes={start}-{end}", "Accept-Encoding":"identity"})
                with urlopen(req, timeout=90) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != expected:
                        raise ValueError("The server did not return the requested archive range")
                    raw = response.read(end-start+2)
                    if len(raw) != end-start+1:
                        raise EOFError("Incomplete archive range")
                    tmp.write(raw)
            tmp.flush()
            if sha256(temporary) != member["sha256"]:
                raise ValueError("Source digest mismatch")
        except BaseException:
            tmp.close()
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(result)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("date", choices=("2017-09-12", "2017-09-13"))
    cli.add_argument("destination", type=Path)
    args = cli.parse_args()
    print(fetch(args.date, args.destination))
