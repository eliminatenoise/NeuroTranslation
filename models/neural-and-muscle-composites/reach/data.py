"""Read already reconstructed Chowdhury et al. area-2 archives."""
import hashlib
import json
from pathlib import Path

import numpy as np

PROTOCOL = json.loads(Path(__file__).with_name("protocol.json").read_text())
CONTACTS = PROTOCOL["contacts"]


def read_archive(directory, split, sensor='handle'):
    path = Path(directory) / (split + ".npz")
    with path.open("rb") as f:
        assert hashlib.file_digest(f, "sha256").hexdigest() == PROTOCOL["sources"]["archives_sha256"][split]
    with np.load(path, allow_pickle=False) as a:
        k = a["k"][:, None]
        np.testing.assert_array_equal(a["history_rows"], k + np.arange(-20, 0))
        np.testing.assert_array_equal(a["movement_rows"], k + np.arange(10))
        assert list(a["pose_labels"][-2:]) == ["handle_x", "handle_y"]
        guide = a["all_guide"]
        def pool(key):
            raw = a[key]
            out = []
            for contact in CONTACTS:
                mask = guide[:, 0] == contact
                assert sum(mask & (guide[:, 1] == 0)) == 1
                selected = raw[:, :, mask]
                bad = ((~np.isfinite(selected)) | (selected < 0) | (selected != np.floor(selected))).any(axis=2)
                counts = selected.astype(np.float64).sum(axis=2)
                counts[bad] = np.nan
                out.append(counts)
            raw_counts = np.stack(out, axis=2)
            return raw_counts.reshape(len(k), -1, 5, len(CONTACTS)).sum(axis=2)
        c, y = pool("all_history"), pool("all_concurrent")
        if sensor == "hand":
            assert list(a["pose_labels"][:3]) == ["Marker_1_"+dim for dim in "xyz"]
            columns, units = slice(0,3), 100.0
        elif sensor == "handle":
            columns, units = slice(-2,None), 1.0
        else:
            raise ValueError("Unknown movement sensor")
        xy = a["pose"][:, :, columns]*units
        segments = xy.reshape(len(k), 4, 5, xy.shape[-1])
        p = np.concatenate((segments[:, :, -1], segments[:, :, -1] - segments[:, :, 0]), axis=-1)
        m = a["movement"][:, [4, 9], columns]*units
        valid = np.ones(len(k), dtype=bool)
        for array in [xy, m, c, y]:
            valid &= np.isfinite(array).all(axis=(1, 2))
        velocity = xy[:, -1] - xy[:, -6]
        arrays = dict(pose=p, counts=c, movement=m, neural=y,
                      velocity=velocity[:, None] * np.array([1, 2])[None, :, None],
                      **{key:a[key] for key in ["block", "workspace", "original", "ordinal", "k"]})
        return {key: val[valid] for key, val in arrays.items()}


def earlier_donors(a):
    previous = {}
    donors = np.full(len(a["k"]), -1, dtype=int)
    for i in np.argsort(a["k"], kind="stable"):
        key = (a["block"][i], a["workspace"][i], a["ordinal"][i])
        old = previous.get(key)
        if old is not None:
            assert a["original"][i] != a["original"][old] and a["k"][old] + 9 < a["k"][i]
            donors[i] = old
        previous[key] = i
    return donors


def make_scales(train):
    def moments(x, axes):
        return (x.mean(axis=axes, keepdims=True), np.maximum(x.std(axis=axes, keepdims=True), 1e-5))
    scales = {}
    for key in ("pose","counts","movement","neural"):
        axes = (0,1) if key in ("pose","counts") else 0
        scales[key+"_mean"], scales[key+"_std"] = moments(train[key], axes)
    return scales


def norm(x, key, scales):
    return ((x-scales[key+"_mean"])/scales[key+"_std"]).astype(np.float32)
