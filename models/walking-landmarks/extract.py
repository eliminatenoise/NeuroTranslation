"""Read one fixed source partition on the stored C3D clock."""
import argparse
import hashlib
import json
from pathlib import Path
import zlib

import ezc3d
import numpy as np
from predict import MARKERS, MUSCLES, tokens

HERE = Path(__file__).resolve().parent
SPLIT = "e0ccb1ae4a37c12d47c5e63ce3c9372efa212fa475275eef4dc40c2143aeda32"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def past_event(raw, anchors):
    fields = raw["parameters"]["EVENT"]
    times = fields["TIMES"]["value"]
    events = []
    for i, (side, label) in enumerate(zip(fields["CONTEXTS"]["value"], fields["LABELS"]["value"])):
        tag = "strike" if label.startswith("Foot Strike") else "off" if label == "Foot Off" else None
        if side in ("Left","Right") and tag:
            frame = int(np.rint(100 * (60*times[0,i] + times[1,i])))
            events.append((frame, side + "_" + tag))
    labels, bins = [], []
    for anchor in anchors:
        frame, label = max((p for p in events if p[0] <= anchor), default=(0, "start"))
        labels.append(label)
        bins.append((anchor-frame)//5)
    return np.array(labels, dtype="U16"), np.array(bins, dtype=int)


def one_trial(path):
    raw = ezc3d.c3d(str(path))
    par, data = raw["parameters"], raw["data"]
    def field(group, name):
        return par[group][name]["value"]
    if (field("POINT","UNITS") != ["mm"] or field("POINT","RATE")[0] != 100 or
            field("ANALOG","RATE")[0] != 1500 or raw["header"]["points"]["first_frame"] != 0):
        raise ValueError("Unexpected point unit, rate or start frame")
    n = data["points"].shape[-1]
    if data["analogs"].shape[-1] != 15*n:
        raise ValueError("Unexpected point/analog clock lengths")
    names = field("POINT","LABELS")
    xyz = np.full((n,8,3), np.nan)
    for j, key in enumerate(MARKERS):
        if key not in names:
            continue
        if names.count(key) != 1:
            raise ValueError(f"Duplicate {key}")
        k = names.index(key)
        pos = data["points"][:3,k].T
        residual = data["meta_points"]["residuals"][0,k]
        good = np.isfinite(residual) & (residual >= 0) & np.isfinite(pos).all(axis=1)
        xyz[good,j] = pos[good]
    frames = np.arange(4, n, 5)
    sample = frames[:,None]*15 + np.arange(-52,8)
    names, units = field("ANALOG","LABELS"), field("ANALOG","UNITS")
    rms = np.full((len(frames),8), np.nan)
    for j, key in enumerate(MUSCLES):
        if key not in names:
            continue
        k = names.index(key)
        if names.count(key) != 1 or units[k] != "V":
            raise ValueError(f"Ambiguous or non-voltage {key}")
        volt = data["analogs"][0,k,sample]
        rms[:,j] = 1e6*np.sqrt(np.mean(volt**2,axis=1))
    anchors = np.arange(39,n-20,5)
    history = xyz[anchors[:,None]+np.arange(-39,1)]
    emg = rms[(anchors//5)[:,None]+np.arange(-7,1)]
    target = xyz[anchors+20,:6] - xyz[anchors,:6]
    labels, bins = past_event(raw, anchors)
    return dict(x=tokens(history, emg), y=target, anchor=anchors, phase=labels, phase_bin=bins), n


def extract(root, partition, out, seal, digest):
    manifest = root/"split-three.json"
    if sha(manifest) != SPLIT:
        raise ValueError("Original source split mismatch")
    if partition == "assessment":
        if not seal or not digest or sha(seal) != digest:
            raise ValueError("Assessment requires sealed fit and its SHA-256")
        meta = json.loads(seal.read_bytes())
        if meta["protocol_sha256"] != sha(HERE/"protocol.json") or meta["weights_sha256"] != sha(seal.parent/"weights.npz"):
            raise ValueError("Fitted weights or protocol changed")
    selected = [r for r in json.loads(manifest.read_bytes())["selected"] if r["partition"] == partition]
    parts = []
    for row in selected:
        path = root/partition/Path(row["name"]).name
        data = path.read_bytes()
        if len(data) != row["size"] or f"{zlib.crc32(data):08x}" != row["crc32"]:
            raise ValueError("Source integrity mismatch")
        arrays, n = one_trial(path)
        count = len(arrays["anchor"])
        parts.append(dict(**arrays, person=np.full(count,row["ordinal"]), repeat=np.full(count,row["repeat"]),
                          record_frames=np.full(count,n)))
    result = {key:np.concatenate([part[key] for part in parts]) for key in parts[0]}
    np.savez_compressed(out, **result)
    print(json.dumps({"partition":partition, "people":len(set(result["person"])), "trials":len(selected),
                      "cutoffs":len(result["anchor"]), "valid_targets":np.isfinite(result["y"]).all(axis=-1).sum(axis=0).tolist()}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("partition", choices=["train","assessment"])
    p.add_argument("out", type=Path)
    p.add_argument("--fit-seal", type=Path)
    p.add_argument("--fit-seal-sha256")
    a = p.parse_args()
    extract(a.root, a.partition, a.out, a.fit_seal, a.fit_seal_sha256)
