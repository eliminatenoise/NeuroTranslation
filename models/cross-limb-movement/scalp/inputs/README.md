# Which lift does this scalp recording belong to?

Take a wrist movement and keep its measured muscle and marker history fixed. What changes if the forecaster sees the scalp voltage from that lift, the usual voltage measured in training, or the voltage from an earlier lift by the same person? A second experiment asks the same question about balance while standing or walking. Each recording stays with the study that made it. [WAY grasp-and-lift collection](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [Peterson and Ferris balance recordings](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)

Each movement has twenty short histories leading up to the forecast, each lasting 31.25 milliseconds. A signed mean tells us which way the voltage tended to lie relative to its recording reference. A root mean square tells us its amplitude. A third number records whether the site supplied a usable signal. The reader keeps those three numbers together for each site, in the order shown below. The cap layouts support a nominal location on the scalp. Electrical activity from multiple sources can reach that location. [BioSemi 128-channel coordinates](https://www.biosemi.com/download/Cap_coords_all.xls)

| Comparison | Balance contacts in model order | Available balance events / people | Wrist contacts in model order | Available lifts / people |
|---|---|---:|---|---:|
| Central scalp | D19, A1, B22 (C3, Cz, C4) | 5,179 / 18 | C3, Cz, C4 | 1,764 / 6 |
| Frontal scalp | C29, C16 (Fp1, Fp2) | 4,010 / 14 | Fp1, Fp2 | 1,764 / 6 |
| Eye | Right horizontal, left horizontal, left vertical | 5,179 / 18 | No separate recording | 0 / 0 |
| Neck muscle | Left neck, right neck | 5,179 / 18 | No separate recording | 0 / 0 |
| Earlier central history | Same available central contacts as the target | 4,963 / 18 | Same three central contacts | 1,602 / 6 |

A row counts when at least one listed site is available. Of the 5,179 balance events, D19 contributed 4,887 from 17 people, A1 contributed 3,713 from 13 and B22 contributed 4,330 from 15. C29 contributed 4,010 from 14 people and C16 contributed 2,885 from 10. Every listed wrist contact was available in all 1,764 lifts. A comparison requiring both frontal input and a matched earlier central history has 3,842 balance events from 14 people and 1,602 lifts from six. The accompanying check produces counts by study condition, site, person fold and mask pattern.

## Establish the clock before comparing trials

The wrist archive stores each lift on its own local clock. To compare two lifts, the reader uses the time since the numbered series began, recovered by adding the lift's start time to its local cutoff. The cutoff falls 400 ms after the light cue. The authors report up to 2 ms of uncertainty between the systems. Removing 2 ms at each edge of every interval leaves 13 or 14 samples per interval at 500 Hz, 273 measurements per contact across the 20 intervals. The reader keeps the signal in exported native amplitude units. The original EEGLAB utility documents a scale factor for the whole-series recording; calibration of the trial-window export remains unresolved. [Luciw, Jarocka and Edin, methods](https://doi.org/10.1038/sdata.2014.47)

The balance archive places the scalp, neck and eye signals on a 256 Hz session clock, measured in microvolts. Each interval contains eight samples. The cutoff falls 32 samples after the first grid point on or after the rotation event, 125 to just under 129 ms after logged onset. The authors aligned streams offline and applied downsampling, high-pass filtering, line-noise removal and common-median rereferencing. They also reviewed bad electrodes retrospectively. Earlier recorded sample indices alone cannot establish the latency or one-sided processing of a live decoder. [Peterson and Ferris, data and processing](https://doi.org/10.1016/j.dib.2021.107635)

The earlier-trial control keeps study, participant, native session, task or numbered series, rotation direction, ordinal third and all three central observation flags fixed. Each earlier trial can serve as a donor once. Its local history, prediction period and quality-check margin must end before the target's corresponding interval begins. The smallest gap between these reserved intervals was 1.961 seconds in the balance recordings and 4.972 seconds in the lifts. The first qualifying event in each group has no earlier match. The original movement readers also checked subsequent muscle or marker quality when screening trials, so all comparisons concern retrospectively eligible events. Exact integer-tick margins and the scale convention are in [DESIGN.md](DESIGN.md).

## Reproduce the inputs

Use Python 3.10 or later and NumPy. The tested environment used Python 3.12 and NumPy 2.5. Build the original development muscle-and-motion and paired-scalp archives using their source readers, and supply the development participant splits from the path-forecast experiment. The adapter checks typed array identities, channel names, masks and past sampling intervals. ZIP repackaging can change the compressed bytes while preserving those typed arrays. Source-file access and the computing environment still matter when rebuilding the measurements.

```sh
python reproduce_inputs.py --cohort joint/development.npz \
  --scalp paired/development.npz --splits splits-and-orders.npz --out private/inputs
python test_scalp_inputs.py --cohort joint/development.npz \
  --scalp paired/development.npz --splits splits-and-orders.npz -v
```

`support.npz` has one row per movement, five integer fields and one Boolean mask for each of the four contact groups. `support-counts.json` contains aggregate counts. `fold-scales.json` contains the study-specific training scale for every group, site and feature. Store row-level outputs with the source measurements.

| Field | Meaning |
|---|---|
| `row`, `fold` | Indices in the original joint archive and the held-participant fold |
| `donor` | Earlier matched global row, or −1 when no earlier row qualifies |
| `envelope_start`, `envelope_end` | Inclusive reserved endpoints in native series or session ticks |
| `central_mask`, `frontal_mask`, `eye_mask`, `neck_mask` | Three Boolean contact slots per row; unused slots are false |

The Python calls below use the joint row order. Within each training fold, each recorded site gets its own mean and population standard deviation, estimated across that study's available training intervals. A missing site contributes two zero values and a false observation flag. The reference comparison puts zero in the standardized amplitude slots while preserving every real flag. The result has shape `(rows, 20, 9)`.

```python
import numpy as np
from scalp_inputs import load_inputs, fit_normalizers, tokens

inputs = load_inputs("joint/development.npz", "paired/development.npz")
with np.load("splits-and-orders.npz", allow_pickle=False) as split:
    fold = split["fold"]
train, held = np.flatnonzero(fold != 0), np.flatnonzero(fold == 0)
scales = fit_normalizers(inputs, train)
aligned = tokens(inputs, scales, held, "central")
reference = tokens(inputs, scales, held, "central", mode="reference")
paired = held[inputs.donor[held] >= 0]
earlier = tokens(inputs, scales, paired, "central", mode="wrong")
same_rows = tokens(inputs, scales, paired, "central")
```

`normalize_values(values, mask, domain, scales, kind)` applies the same transformation to new source-shaped inputs. It expects signed means followed by RMS values in a `(rows, 20, 3, 2)` array and three Boolean flags per row. Domain 0 denotes balance and 1 denotes wrist. Each scale record uses `mean[site][feature]`, `scale[site][feature]` and `count[site]`, the number of observed training intervals. A zero training count for a site prevents applying it to an observed reading at that site. Scaling uses float64 arithmetic and stores model inputs as float32. No per-person or cross-study calibration follows from this transformation.
