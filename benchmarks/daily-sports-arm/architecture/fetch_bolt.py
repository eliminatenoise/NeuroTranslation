"""Fetch the three public files for one exact immutable checkpoint, without executing remote code."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
import json

MODEL = "amazon/chronos-bolt-tiny"
REVISION = "a0e552de83495b5c28c14c71c374f3e33280b340"
WEIGHTS = "75068728d376d2bec670379eeef4bfb4d24c0cfe24d957451f8d19b447030a32"
CONFIG_BLOB = "d57acc2ef40d0a0d71be5ecdeeec067256b59cc8"
FILES = ("README.md", "config.json", "model.safetensors")


def fetch(folder):
    from hashlib import sha1
    folder.mkdir(parents=True, exist_ok=True)
    info_url = f"https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true"
    with urlopen(info_url, timeout=20) as stream:
        meta = json.load(stream)
    listed = {entry["rfilename"]: entry for entry in meta["siblings"]}
    if (meta["sha"], listed["model.safetensors"]["lfs"]["sha256"],
            listed["config.json"]["blobId"]) != (REVISION, WEIGHTS, CONFIG_BLOB):
        raise ValueError("Remote metadata differs from pinned release")
    for name in FILES:
        entry = listed[name]
        path = folder / name
        if path.exists():
            content = path.read_bytes()
        else:
            with urlopen(f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}", timeout=45) as stream:
                content = stream.read(entry["size"] + 1)
        if len(content) != entry["size"]:
            raise ValueError(f"Byte length differs for {name}")
        expected = entry["lfs"]["sha256"] if name == "model.safetensors" else entry["blobId"]
        actual = (sha256(content).hexdigest() if name == "model.safetensors" else
                  sha1(f"blob {len(content)}\0".encode() + content).hexdigest())
        if actual != expected:
            raise ValueError(f"Digest differs for {name}")
        if not path.exists():
            with path.open("xb") as out:
                out.write(content)
        print(name, len(content), sha256(content).hexdigest())


if __name__ == "__main__":
    fetch(Path(__file__).resolve().parent / ".bolt")
