"""Check of the area2 boundary scan (datasets/area2.py, _count_before) on synthetic spike trains; reads no data.

For 400 sorted series (Poisson trains at 0.5-60 Hz, a train whose rate rises 100-fold 9.7 s before the cut, a
train that starts after the cut and a train that ends before it) the scan must return the same index as
numpy.searchsorted and read at most one value at or after the cut.

  python check_area2_scan.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from datasets import area2  # noqa: E402

CUT = 1809.676


def series(rng, kind, T=3000.0):
    if kind == 0:
        t = np.cumsum(rng.exponential(1 / rng.uniform(0.5, 60), size=int(T * 80)))
    elif kind == 1:
        a = np.cumsum(rng.exponential(1 / 2.0, size=4000))
        b = 1800 + np.cumsum(rng.exponential(1 / 200.0, size=4000))
        t = np.sort(np.r_[a[a < 1800], b])
    elif kind == 2:
        t = 1900 + np.cumsum(rng.exponential(0.1, size=1000))
    else:
        t = np.cumsum(rng.exponential(0.05, size=20000))
        t = t[t < 1800]
    return t[t < T]


def main():
    rng = np.random.default_rng(20261128)
    worst, equal = 0, True
    for i in range(400):
        t = series(rng, i % 4)
        probes = [0]
        e = area2._count_before(t, 0, len(t), CUT, probes)
        equal &= e == int(np.searchsorted(t, CUT, side="left"))
        worst = max(worst, probes[0])
    out = {"cases": 400, "index_equal_to_searchsorted": bool(equal), "max_values_read_at_or_after_cut": worst}
    print(json.dumps(out))
    sys.exit(0 if equal and worst <= 1 else 1)


if __name__ == "__main__":
    main()
