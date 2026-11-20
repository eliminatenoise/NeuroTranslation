"""Regression check for strict time boundaries, missingness and wrong-word controls."""

import json
import time

import numpy as np

from learn import fit, predictions
from windows import last_observation, measure_recording

clock = np.arange(211) / 30
assert last_observation(clock, clock[47] + 1.0) == 77
xyz = np.zeros((len(clock), 2, 3))
xyz[:, 1, 0] = clock / 10
flags = np.ones((len(clock), 2), dtype=bool)
hand = {
    "xyz": xyz,
    "t": clock,
    "ticks": np.arange(len(clock), dtype=np.int64) * 333333,
    "active": np.ones(len(clock), dtype=bool),
    "valid": flags.copy(),
    "tracked": flags.copy(),
}
base = {
    "end": 2.0,
    "start": 1.5,
    "id": 1,
    "tokens": ["left"],
    "confidence_status": "unrated",
}
rec = {"recording": "r0", "group": "g0", "task": "a"}
rows, flow = measure_recording(rec, [base, dict(base, id=2)], hand)
assert len(rows) == 1 and flow["duplicate_cutoff"] == 1
r = rows[0]
assert (
    abs(r["y"] - 10) < 1.0e-9 and abs(r["cv"] - 10) < 1.0e-9 and min(r["lead"]) > 0.24
)
hand["tracked"][clock > r["cutoff"], 1] = False
missing, flow = measure_recording(rec, [base], hand)
assert (
    not missing
    and flow["past_eligible"] == 1
    and flow["missing_future_observation"] == 1
)
rng = np.random.default_rng(279)
samples = []
for i in range(60):
    samples.append(
        dict(
            r,
            record="r" + str(i % 6),
            group="g" + str(i % 6),
            id=i,
            task="ab"[i % 2],
            tokens=("left",) if i % 4 < 2 else ("right",),
            motion=rng.normal(size=17),
            y=float(i % 5 + 1),
        )
    )
start = time.perf_counter()
spec, weights = fit(samples)
pred, matched = predictions(samples, spec, weights, samples)
assert (
    matched.all()
    and np.all(np.isfinite(pred["ridge_substituted"]))
    and not spec["attention_admitted"]
)
assert np.all(np.asarray(pred["ridge_substituted"]) >= 0)
print(
    json.dumps(
        {
            "fit_predict_s": time.perf_counter() - start,
            "prediction_sum": float(pred["motion_context_words"].sum()),
            "strict_fixture": "pass",
        }
    )
)
