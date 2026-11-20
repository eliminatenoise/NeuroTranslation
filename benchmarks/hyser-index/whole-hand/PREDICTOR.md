# Forecast the next index reading

The fitted predictors accept released Hyser Random force-transducer voltages on their native 100 Hz clock. Give the model 41 consecutive frames ending at the cutoff. The output is the forecast of the index transducer 12 ticks later, in volts. The 120 ms horizon describes the released trace. The acquisition and filtering history does not establish live causal availability or device delay.

Use rows in the publisher’s channel order `[thumb, index, middle, ring, little]` after converting counts to volts with each channel’s header gain and baseline. The same-trial forecasters were fitted on the 12 fitting people of study 14.

| Weight entry | Feature sequence | Width |
| --- | --- | ---: |
| `index_only` | Index readings from the oldest frame to the cutoff. | 41 |
| `aligned_five` | The index history followed by the thumb, middle, ring and little histories. Every 41-value block runs oldest first. | 205 |
| `aligned_summary` | The index history followed by eight values. For each of thumb, middle, ring and little, give the latest voltage then the least-squares slope across the 41 frames in V/tick. | 49 |

The retrospective other-trial control stays in the aggregate report. All three weight entries are ordinary same-trial forecasters. Each weight entry holds `alpha`, `mean`, `scale`, `intercept` and `coef`. Normalize each feature `x[i]` using its saved statistics. The output is

```text
index_at_cutoff + intercept + Σ coef[i] × (x[i] − mean[i]) / scale[i]
```

The weights file uses schema `hyser-finger-context-weights-v1` and experiment `hyser-random-finger-context-20261119-v1`. Its feature metadata and three model widths match the reference Python. With NumPy installed and weights alongside the module:

```python
import json
from pathlib import Path
from finger_context import predict

weights = json.loads(Path("WEIGHTS.json").read_text())
# voltage_frames is a 100 Hz NumPy array with five columns in publisher order.
# This passes exactly the history through the cutoff, so no truth reading is required.
cutoff = len(voltage_frames) - 1
index_voltage = predict(voltage_frames, [cutoff], weights, "aligned_five")[0]
```

The predictor expects finite voltages for the selected arm’s inputs, at least 41 frames and an integer cutoff. The index-only arm uses only the index column. Other models require all five. A standalone scoring run may of course have the later measured voltage available for comparison.

Contains models derived from Jiang, X., Dai, C., Liu, X., & Fan, J. (2023), *Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings*, version 2.0.0, PhysioNet. [Dataset](https://doi.org/10.13026/hxan-pe94) · [Paper](https://doi.org/10.1109/TNSRE.2021.3082551) · [Open Data Commons Attribution 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/)
