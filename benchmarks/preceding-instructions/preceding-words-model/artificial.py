"""Score an invented predictor input with the fitted ridge coefficients."""

import json

import numpy as np

from learn import design, inputs, raw_predict
from windows import HERE

spec = json.loads((HERE / "results/model.json").read_text())
coefs = np.asarray(
    json.loads((HERE / "results/weights.json").read_text())["motion_context_words"]
)
# Four invented observations in cm, oldest to newest. None comes from a person.
positions = np.array(
    [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 1.0, 0.0], [3.0, 2.0, 0.0]]
)
dt = np.array([0.5, 0.25, 0.25])
velocity = np.diff(positions, axis=0) / dt[:, None]
motion = np.r_[
    np.c_[velocity, np.linalg.norm(velocity, axis=1)].ravel(),
    np.linalg.norm(positions[-1] - positions[0]),
    np.zeros(4),
]
ctx = np.array([np.log1p(60.0), np.log1p(3.0), 1.0, 1.0])
row = {"motion": motion, "context": ctx, "task": "gopro", "tokens": ["turn"]}
res = {}
for label, terms in [("with_word", row["tokens"]), ("removed", [])]:
    features = inputs([{**row, "tokens": terms}], spec)
    res[label] = float(
        max(0.0, raw_predict(coefs, design(features, "motion_context_words"))[0])
    )
print(
    json.dumps(
        {
            "origin": "Deliberately invented example; no human source or measured future endpoint.",
            "task": row["task"],
            "retained_tokens": row["tokens"],
            "cutoff_s": 60.0,
            "completed_utterance_duration_s": 3.0,
            "forecast_horizon_s": 1.0,
            "motion": motion.tolist(),
            "context": ctx.tolist(),
            "estimates_cm": res,
        },
        indent=2,
        allow_nan=False,
    )
)
