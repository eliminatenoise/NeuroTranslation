"""Check an already-authorized exported block without opening native signals."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def check(out, block):
    out = Path(out)
    audit = json.loads((out / f"{block}-audit.json").read_text())
    manifest = json.loads((out / "membership.json").read_text())
    trial_list = [r["trial"] for r in manifest if r["block"] == block]
    path = out / f"{block}.npz"
    with np.load(path, allow_pickle=False) as data:
        n = len(data["trial"])
        required = {"movement": (n, 5, 4), "cue": (n, 5, 7), "neural": (n, 5, 30),
                    "cv": (n, 3, 2), "y": (n, 2), "marker": (n, 5, 12),
                    "marker_valid": (n, 5, 12), "observed_direction": (n, 2), "unit_guide": (30, 2),
                    "original_trial": (len(trial_list),)}
        required.update({k: (n,) for k in ("trial", "epoch", "offset", "k", "donor")})
        assert set(required) == set(data.files)
        arrays = {k: data[k] for k in data.files}
    assert all(arrays[k].shape == shape for k, shape in required.items())
    assert arrays["original_trial"].tolist() == trial_list == [r["trial"] for r in audit["originals"]]
    assert arrays["unit_guide"][:, 1].min() > 0
    assert not (arrays["neural"] < 0).any() and arrays["neural"].dtype.kind in "iu"
    assert np.array_equal(np.isfinite(arrays["marker"]), arrays["marker_valid"])
    for key in ("movement", "neural", "cue", "y", "cv"):
        assert np.isfinite(arrays[key]).all()
    retained, excluded = 0, 0
    example_ids = []
    donor_cache = {}
    for trial in audit["originals"]:
        attempts = trial["attempts"]
        assert len(attempts) == 8
        assert [(a["epoch"], a["offset"]) for a in attempts] == [(e, h) for e in (0, 1) for h in (0, 5, 10, 15)]
        updates = {}
        for rec in attempts:
            row = rec["row"]
            if row is None:
                assert rec["reason"]
                excluded += 1
                continue
            assert rec["reason"] is None and row == retained
            tid, k, epoch, offset = (arrays[q][row] for q in ("trial", "k", "epoch", "offset"))
            assert (tid, k, epoch, offset) == (trial["trial"], rec["k"], rec["epoch"], rec["offset"])
            assert trial["start"] <= k - 20 and k + 10 <= trial["end"]
            ev = {key: vals[0] for key, vals in trial["events"].items()}
            assert k == ev["go" if epoch else "bump"] + offset
            if epoch == 0:
                assert k + 10 < min(ev["target"], ev["go"])
            assert ev["bump"] < min(ev["target"], ev["go"])
            cue = arrays["cue"][row]
            ends = np.arange(k - 16, k + 1, 4)
            for j, name in ((0, "bump"), (3, "target"), (6, "go")):
                flags = ends > ev[name]
                assert np.array_equal(cue[:, j], flags)
                if j in (0, 3):
                    angles = cue[:, j + 1:j + 3]
                    assert (angles[~flags] == 0).all()
                    assert (np.sum(angles[flags] ** 2, axis=1) == 1).all()
                    degree = arrays["observed_direction"][row, j // 3]
                    assert np.isfinite(degree) == bool(flags[-1])
                    if flags[-1]:
                        angle = np.arctan2(*angles[-1][::-1]) * 180 / np.pi
                        assert degree == angle % 360
            donor = arrays["donor"][row]
            key = (epoch, offset, tuple(cue[-1]))
            assert donor == donor_cache.get(key, -1)
            if donor >= 0:
                assert donor < row and arrays["trial"][donor] < tid
            updates[key] = row
            # Adjacent endpoint differences and the 40-ms CV can be recovered without raw data.
            mov = arrays["movement"][row]
            assert np.array_equal(mov[1:, :2] - mov[:-1, :2], mov[1:, 2:])
            assert np.array_equal(mov[-1, 2:] * 2.5, arrays["cv"][row, 0])
            example_ids.append([int(tid), int(k)])
            retained += 1
        donor_cache.update(updates)
    assert retained == n and retained + excluded == len(trial_list) * 8
    assert audit["summary"]["attempted"] == retained + excluded
    assert len(set(map(tuple, example_ids))) == n
    return dict(block=block, rows=n, originals=len(trial_list), excluded=excluded,
                donor_rows=int((arrays["donor"] >= 0).sum()),
                complete_marker_rows=int(arrays["marker_valid"].all(axis=(1, 2)).sum()),
                npz_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("block", choices=("train", "validation", "test"))
    args = parser.parse_args()
    print(json.dumps(check(args.directory, args.block), indent=2))
