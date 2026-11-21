"""Fetch the pinned, licensed rat data into a user-selected directory. CC0."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
PRIMARY = ("https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/"
           "3e43795adeb6c33b8302e952f45af03be5a71fb1/benchmarks/wtrack-neural-motion/recording/pairs")
ER1 = "https://dandiarchive.s3.amazonaws.com/blobs/df4/d52/df4d5256-1fcc-4517-a9af-b202f822a46d"
ETAG = "a4f80cf369b07b36b8ceb3399351aeef-448"
SIZE = 30009167808
BLOCK = 262144


def checked(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Source SHA-256 mismatch")
    return data


class VerifiedRanges(io.RawIOBase):
    """Read from the sparse NWB ranges the source adapter actually needs."""
    def __init__(self, session):
        self.session = session
        self.pos = 0
        self.blocks = {}
        self.hashes = json.loads((HERE/"er1-blocks.json").read_text())

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        position = (0, self.pos, SIZE)[whence] + offset
        if position < 0:
            raise ValueError("Negative file offset")
        self.pos = position
        return position

    def block(self, idx):
        expected = self.hashes[str(idx)]
        if idx not in self.blocks:
            first = idx * BLOCK
            last = min(first + BLOCK, SIZE) - 1
            req = {"Range": f"bytes={first}-{last}", "If-Match": f'"{ETAG}"'}
            with self.session.get(ER1, headers=req, timeout=40, stream=True) as response:
                if (response.status_code != 206 or response.headers.get("Content-Range") != f"bytes {first}-{last}/{SIZE}"
                        or response.headers.get("ETag", "").strip('"') != ETAG):
                    raise OSError("DANDI object, ETag or byte range differs from the verified release")
                self.blocks[idx] = checked(response.content, expected)
        return self.blocks[idx]

    def readinto(self, destination):
        out = memoryview(destination).cast("B")
        length = max(0, min(len(out), SIZE - self.pos))
        done = 0
        while done < length:
            index, offset = divmod(self.pos, BLOCK)
            block = self.block(index)
            n = min(length - done, len(block) - offset)
            if n <= 0:
                raise OSError("Truncated block")
            out[done:done+n] = block[offset:offset+n]
            self.pos += n
            done += n
        return length


def primary(session, destination):
    hashes = json.loads((HERE/"sources.json").read_text())["JS14"]
    for number, expected in hashes.items():
        group = "train"
        path = destination/group/f"trial-{int(number):03d}.npz"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            checked(path.read_bytes(), expected)
            continue
        url = f"{PRIMARY}/{group}/{path.name}"
        with session.get(url, timeout=40) as response:
            response.raise_for_status()
            path.write_bytes(checked(response.content, expected))


def external(session, destination):
    import h5py
    from prepare_er1 import extract
    hashes = json.loads((HERE/"sources.json").read_text())["ER1"]
    with VerifiedRanges(session) as source, h5py.File(source, "r") as nwb:
        extract(nwb, destination)
    for number, expected in hashes.items():
        checked((destination/f"trial-{int(number):03d}.npz").read_bytes(), expected)


def main():
    parser = argparse.ArgumentParser(description="Fetch the rat packets, retinal archive and turtle figure source; existing files are verified.")
    parser.add_argument("destination", type=Path)
    dest = parser.parse_args().destination
    dest.mkdir(exist_ok=True, parents=True)
    sources = json.loads((HERE/"sources.json").read_text())
    with requests.Session() as session:
        primary(session, dest/"js14")
        er = dest/"er1"
        if all((er/f"trial-{int(k):03d}.npz").exists() for k in sources["ER1"]):
            for n, expected in sources["ER1"].items():
                checked((er/f"trial-{int(n):03d}.npz").read_bytes(), expected)
        else:
            external(session, er)
        retina = sources["salamander"]
        url = ("https://raw.githubusercontent.com/EvolutionaryNeuralCodingLab/SpatiallySelectiveViewInvariance/"
               "b421ce0a62140a812e964cb027b97f979e98f049/spikes.mat")
        files = [(retina["name"], retina["full_original_file"], retina["verified_sha256"]),
                 ("spikes.mat",url,sources["turtle_mat_sha256"])]
        for name,url,sha in files:
            path = dest/name
            if path.exists():
                checked(path.read_bytes(),sha)
            else:
                with session.get(url,timeout=90) as response:
                    response.raise_for_status()
                    path.write_bytes(checked(response.content,sha))


if __name__ == "__main__":
    main()
