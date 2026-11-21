"""Forecast one recorded training reach with Python and NumPy."""
import json
from pathlib import Path
import numpy as np
from replay import predict

example=json.loads(Path(__file__).with_name("example.json").read_text())
p,c,h=[np.asarray([example[k]]) for k in ("pose","cue","pooled_counts_4x37")]
forecasts=predict(p,c,h)[0]
np.testing.assert_allclose(forecasts,example["expected_displacements"],rtol=1e-9,atol=1e-10)
print("Horizon     predicted hand displacement XYZ (mm)    measured hand displacement XYZ (mm)")
for i,(pred,actual) in enumerate(zip(forecasts,np.array(example["measured_displacements"]))):
    print(f"{(i+1)*10:>3} ms    ",np.round(1000*pred[:3],2),"   ",np.round(1000*actual[:3],2))
