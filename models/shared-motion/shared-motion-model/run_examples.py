"""Run both published examples, using the real checkpoint."""
from pathlib import Path
import json
import sys

try:
    from predict import forecast
except ModuleNotFoundError as exc:
    if exc.name != 'numpy':
        raise
    raise SystemExit("NumPy is required. Install it for this Python with: python -m pip install numpy")

here = Path(__file__).resolve().parent
case = json.loads((here/'reference-examples.json').read_text())
pred = forecast(case['x'], case['domain'], here/'shared-weights.npz')
if max(abs(a-b) for a,b in zip(pred,case['expected_cm'])) > 1e-7:
    sys.exit('Checkpoint output disagrees with the reference')
print("Five invented observations, one nominal quarter-second forecast.")
for d,v in zip(case['domain'],pred):
    print(f"{d}: {v:.6f} cm")
