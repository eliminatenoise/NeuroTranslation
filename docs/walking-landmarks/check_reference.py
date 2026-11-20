"""Check the saved example using the source NumPy predictor and JSON weight arrays."""
import json
from pathlib import Path
import numpy as np
from reference_predict import MODELS, predict

DATA = Path(__file__).resolve().parent / "data"
read = lambda name: json.loads((DATA / name).read_text())
weights = {k: np.asarray(v) for k,v in read("weights.json").items()}
fixture = read("example.json")
saved = read("example-results.json")
for model in MODELS:
    y = predict(fixture["markers_mm"], fixture.get("emg_rms_uv"), model, weights)
    np.testing.assert_allclose(y, saved[model], atol=0.001, rtol=0)
print("All six Python outputs agree within 0.001 mm.")
