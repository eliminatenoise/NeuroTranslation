"""Recreate a trained forecast for one observed September 7 reach."""
import json
from pathlib import Path

import numpy as np

from forecast import predict

here = Path(__file__).resolve().parent
read = lambda name: json.loads((here/name).read_bytes())
m = read("fits.json")["populations"]["primary"]
e = read("example.json")
last = np.array(e["last_pose"])
slope = (last - e["pose_k_minus_5"])/4
base = np.r_[last,slope,e["primary_history_counts"],e["cue_at_k"]]
updated = np.r_[base,np.array(e["displacement"])-10*slope]
rate = predict(m["update"], updated[None,:])[0]
np.testing.assert_allclose(rate,e["populations"]["primary"]["update"],rtol=1e-12)
for c,val,y in zip(m["contacts"],rate,e["populations"]["primary"]["observed_count"],strict=True):
    print(f"Contact {c:2d}   forecast {val:6.3f}   observed {int(y)}")
