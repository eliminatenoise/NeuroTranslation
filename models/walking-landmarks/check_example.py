"""Check all six forecasts from the invented input, including missing-data handling."""
import json
from pathlib import Path
import numpy as np
from predict import MODELS, load_weights, predict

where = Path(__file__).resolve().parent
example = json.loads((where/"example.json").read_bytes())
expected = json.loads((where/"example-results.json").read_bytes())
weights = load_weights(where/"weights.npz")
for model in MODELS:
    observed = predict(example["markers_mm"], example["emg_rms_uv"], model, weights)
    np.testing.assert_allclose(observed, expected[model], rtol=1e-6, atol=.0001)
    absent = predict(example["markers_mm"],None,model,weights)
    if absent.shape != (6,3) or not np.isfinite(absent).all():
        raise ValueError("Missing electrical input failed.")
print("All six forecasts match the invented example within 0.0001 mm absolute plus 1e-6 relative tolerance.")
