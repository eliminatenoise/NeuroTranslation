"""Read only physically paired rows. Preserve participant/repeat nesting."""
from pathlib import Path
import hashlib
import json
import numpy as np

OFFSETS = [14, 24, 34, 44]
MUSCLES = ["R_tibialis_anterior", "R_soleus", "R_gastrocnemius_medialis",
           "R_vastus_medialis", "R_rectus_femoris", "R_semitendinosus",
           "R_gluteus_maximus", "R_gluteus_medius"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, allow_nan=False, separators=(",", ":")) + "\n")


def subset(d, index):
    return {k: v[index] for k, v in d.items()}


def weights(d):
    """Uniform person > repeat > row, independently for this cohort."""
    p, r = d["person"], d["repeat"]
    people = np.unique(p)
    w = np.zeros(len(p))
    for person in people:
        take = p == person
        repeats = np.unique(r[take])
        for repeat in repeats:
            mask = take & (r == repeat)
            w[mask] = 1 / (len(people) * len(repeats) * mask.sum())
    return w


def features(markers, emg, offsets):
    blocks = np.asarray(markers).reshape(-1, 4, 6, 2, 3)
    last = blocks[:, :, -1]
    displacement = last - blocks[:, :, 0]
    phase = np.broadcast_to(np.asarray(offsets).reshape(-1, 1, 1), last.shape[:2] + (1,))
    return np.concatenate([last[:, :, 0] - blocks[:, :1, 0, 0], last[:, :, 1] - last[:, :, 0],
                           displacement[:, :, 0], displacement[:, :, 1], last[:, :, 0, 2:3],
                           phase, np.log1p(emg)], axis=-1)


def xy(d):
    return (features(d["marker_mm"], d["emg_uv"], d["offset"]),
            np.column_stack((d["heel_delta_mm"], d["force_n"])))


def stats(d):
    x, y = xy(d)
    w = weights(d)
    xm = np.einsum("n,ntf->f", w, x) / 4
    xs = np.sqrt(np.einsum("n,ntf->f", w, (x - xm) ** 2) / 4)
    ym = w @ y
    ys = np.sqrt(w @ ((y - ym) ** 2))
    return {k: v.tolist() for k, v in zip(("xm", "xs", "ym", "ys"),
                 (xm, np.maximum(xs, 1e-6), ym, np.maximum(ys, 1e-6)))}


def inputs(d, norm, marker=False):
    x, y = xy(d)
    x = (x - norm["xm"]) / norm["xs"]
    if marker:
        x[:, :, 14:] = 0
    return x, (y - norm["ym"]) / norm["ys"]


def donors(d):
    take, donor = [], []
    for p in sorted(set(d["person"])):
        for off in OFFSETS:
            group = np.where((d["person"] == p) & (d["offset"] == off))[0]
            group = group[np.argsort(d["repeat"][group])]
            if len(group) > 1:
                take.extend(group)
                donor.extend(np.roll(group, -1))
    return np.array(take, int), np.array(donor, int)
