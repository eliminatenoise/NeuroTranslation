"""Retrieve and verify one fixed FingerFlex development prefix at a time."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
from urllib.request import Request, urlopen
import zlib

import numpy as np

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "source-manifest.json"
PEOPLE = ("bp", "cc", "ht", "jc", "jp")
IDS = dict(zip(("D01", "D02", "D03", "D04", "D05"), PEOPLE))
ARCHIVE = "https://stacks.stanford.edu/file/druid:zk881ps0522/fingerflex.zip"
CATALOG = "https://purl.stanford.edu/zk881ps0522.json"
ARCHIVE_SIZE = 580522436
ARCHIVE_SHA1 = "83acfe25c27da197db0feaf742d9c5f3f9ee99bf"
SELECTION_SHA256 = "adb035242a082cd5a2f286bca63b5bd7c23a92d2889c019fd034420042c36f16"
MANIFEST_SHA256 = "c951741fff2de1ce863ff820c97401371db64535a81941ce148183231425e195"
BP_LEGACY_CROP = "57ea209841127b6cc04f2c03f8f6146f01b3e0235d169365d009cf3f9c643e9c"
VARIABLES = ("ecog", "flex", "cue", "region_code")


def sha_file(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def participant(person):
    person = IDS.get(person, person)
    if person not in PEOPLE:
        raise ValueError("This reader supports only the five fixed development people.")
    return person


def entry(person):
    person = participant(person)
    if sha_file(HERE / "selection.json") != SELECTION_SHA256:
        raise ValueError("Development selection changed.")
    if sha_file(MANIFEST) != MANIFEST_SHA256:
        raise ValueError("Source manifest changed.")
    return json.loads(MANIFEST.read_text())["members"][person]


def digest_arrays(arrays):
    return {name: {"dtype": str(arr.dtype), "shape": list(arr.shape),
                   "sha256_c_order": hashlib.sha256(np.ascontiguousarray(arr)).hexdigest()}
            for name, arr in arrays.items()}


def glove_ticks(flex):
    """Find a phase only on calibration, verify each changed digit across its prefix."""
    phases = []
    for digit in range(5):
        col = flex[:, digit]
        changes = np.flatnonzero(col[1:] != col[:-1]) + 1
        early = np.unique(changes[changes < 80000] % 40)
        if early.size != 1 or np.any(changes % 40 != early[0]):
            raise ValueError("Cannot verify a single original 25 Hz block phase.")
        phases.append(int(early[0]))
    if len(set(phases)) != 1:
        raise ValueError("Glove channels disagree on their stored grid.")
    return np.arange(phases[0], len(flex), 40, dtype=np.int64)


def catalog_check():
    with urlopen(CATALOG, timeout=60) as response:
        obj = json.load(response)
    record, = [f for g in obj["structural"]["contains"] for f in g["structural"]["contains"]
               if f["filename"] == "fingerflex.zip"]
    if (obj["version"] != 11 or record["size"] != ARCHIVE_SIZE or
        record["access"]["download"] != "world" or
        {"type": "sha1", "digest": ARCHIVE_SHA1} not in record["hasMessageDigests"] or
        obj["access"]["license"] != "https://creativecommons.org/licenses/by-sa/4.0/legalcode" or
        obj["access"]["useAndReproductionStatement"] != json.loads(MANIFEST.read_text())["catalog_privacy"]):
        raise ValueError("The repository identity or use conditions changed.")


def ranged(start, end):
    spec = f"{start}-{end}"
    req = Request(f"{ARCHIVE}?range={spec}", headers={"Range": "bytes=" + spec,
                  "Accept-Encoding": "identity"})
    with urlopen(req, timeout=120) as r:
        if r.status != 206 or r.headers.get("Content-Range") != f"bytes {spec}/{ARCHIVE_SIZE}":
            raise IOError("The repository did not honor the exact partial request.")
        data = r.read(end - start + 2)
    if len(data) != end - start + 1:
        raise IOError("Incomplete partial response.")
    return data


def download(person, row):
    catalog_check()
    member = row["member"]
    name = f"fingerflex/data/{person}/{person}_fingerflex.mat".encode()
    offset = member["local_header_offset"]
    header = ranged(offset, offset + 30 + len(name) - 1)
    if header[:4] != b"PK\x03\x04" or header[30:] != name or member["name"] != name.decode():
        raise ValueError("Unexpected archive member.")
    name_len, extra = struct.unpack_from("<HH", header, 26)
    start, end = member["start"], member["end"]
    if (struct.unpack_from("<H", header, 8)[0] != 8 or name_len != len(name) or
        start != offset + 30 + len(name) + extra):
        raise ValueError("Unexpected compression method or member offset.")
    compressed = ranged(start, end)
    if hashlib.sha256(compressed).hexdigest() != member["compressed_sha256"]:
        raise ValueError("Compressed member changed.")
    raw = zlib.decompress(compressed, -15)
    if (len(raw) != member["size"] or f"{zlib.crc32(raw):08x}" != member["crc32"] or
        hashlib.sha256(raw).hexdigest() != member["sha256"]):
        raise ValueError("MATLAB member changed.")
    return io.BytesIO(raw)


def crop_mat(mat, row):
    from scipy.io import loadmat, whosmat
    variables = {k: shape for k, shape, _ in whosmat(mat)}
    n, c = variables["data"]
    end = min(40 * (3 * n // 200) - 4000, row["admitted_end"])
    if ((n, c) != (row["release_rows"], row["contacts"]) or end != row["admitted_end"] or
        variables["flex"] != (n, 5) or variables["cue"] != (n, 1) or
        int(np.prod(variables["elec_regions"])) != c):
        raise ValueError("Unexpected MAT dimensions or prefix boundary.")
    if hasattr(mat, "seek"):
        mat.seek(0)
    data = loadmat(mat, variable_names=["data", "flex", "cue", "elec_regions"])
    return {"ecog": data["data"][:end], "flex": data["flex"][:end],
            "cue": data["cue"][:end, 0], "region_code": data["elec_regions"].reshape(-1)}


def read_bp_prefix(path, end):
    if sha_file(path) != BP_LEGACY_CROP:
        raise ValueError("Unrecognised prior bp crop.")
    with np.load(path, allow_pickle=False) as arc:
        if set(arc.files) != set(VARIABLES):
            raise ValueError("Unexpected prefix fields.")
        return {k: arc[k] if k == "region_code" else arc[k][:end] for k in VARIABLES}


def cache_path(person, cache_dir):
    person = participant(person)
    return Path(cache_dir) / f"{person}-development.npz"


def validate(arrays, row):
    if set(arrays) != set(VARIABLES) or digest_arrays(arrays) != row["crop_arrays"]:
        raise ValueError("Development array identity failed.")
    ticks = glove_ticks(arrays["flex"])
    if ticks.size != row["glove_ticks"] or int(ticks[0]) != row["phase_ms"]:
        raise ValueError("Stored glove timing disagrees with this person's receipt.")
    return ticks


def prepare(person, cache_dir, *, mat_path=None, bp_prefix=None):
    """Fetch only this member unless given an existing exact local source."""
    person = participant(person)
    row = entry(person)
    if bp_prefix is not None and (person != "bp" or mat_path is not None):
        raise ValueError("The historical prefix applies only to bp.")
    dest = cache_path(person, cache_dir)
    if dest.exists():
        load_development(person, cache_dir)
        return dest
    if bp_prefix is not None:
        arrays = read_bp_prefix(bp_prefix, row["admitted_end"])
    else:
        if mat_path is not None:
            if sha_file(mat_path) != row["member"]["sha256"]:
                raise ValueError("Local source member failed its SHA-256 check.")
            mat = Path(mat_path)
        else:
            mat = download(person, row)
        arrays = crop_mat(mat, row)
    validate(arrays, row)
    dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as f:
        temp = Path(f.name)
    try:
        with temp.open("wb") as f:
            np.savez(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return dest


def load_development(person, cache_dir):
    """Private read-only 1 ms counts and cues. time_ms indexes real nominal glove ticks."""
    row = entry(person)
    with np.load(cache_path(person, cache_dir), allow_pickle=False) as arc:
        if set(arc.files) != set(VARIABLES):
            raise ValueError("Unexpected cached variables.")
        arrays = {k: arc[k] for k in VARIABLES}
    ticks = validate(arrays, row)
    for arr in (*arrays.values(), ticks):
        arr.setflags(write=False)
    return dict(voltage=arrays["ecog"], target=arrays["flex"], cue=arrays["cue"],
                region=arrays["region_code"], time_ms=ticks, coverage=row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("person", choices=(*PEOPLE, *IDS))
    parser.add_argument("--cache-dir", type=Path, required=True)
    local = parser.add_mutually_exclusive_group()
    local.add_argument("--mat", type=Path, help="Exact original MATLAB member")
    local.add_argument("--bp-prefix", type=Path, help="Exact previously prepared bp prefix")
    args = parser.parse_args()
    path = prepare(args.person, args.cache_dir, mat_path=args.mat, bp_prefix=args.bp_prefix)
    print(f"Verified private prefix for {participant(args.person)}, {sha_file(path)}.")
