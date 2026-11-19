# Five finger histories beat one. Repeating the last reading had the smallest average miss.

A participant follows a prescribed finger combination. Can a model trained on freely chosen presses predict the index sensor 120 ms later? Across the 15 prescribed combinations, the five-history model lowered mean absolute error relative to index history alone in all 12 people whose Random recordings trained the weights. It also lowered error in all four people whose earlier Random recordings had been used only for development. But repeating the current index reading gave the smallest mean absolute error in both groups. The five-history model gave the smallest root mean squared error, which gives larger misses more weight.

The models, cutoff times, cue groups, outcome measures and analysis were fixed before scoring the N-DoF recordings. Each person contributed the first repetition of all 15 combinations on each of two days. The 12-person group contributed 360 trials and 162,000 cutoffs per method; the four-person group contributed 120 trials and 54,000 cutoffs. The second group’s N-DoF trials were new to this test. Those four people's Random-task scores had already informed the research question. All data come from the same Hyser cohort and apparatus. The four reserved final participants remain unopened. [Prespecified protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/45c1547a8b77a7f38394ff2d2a27735cfec8d75d/benchmarks/hyser-index/prescribed/PROTOCOL.md) · [Original study and task design](https://doi.org/10.1109/TNSRE.2021.3082551)

## Errors across all prescribed combinations

All entries are in millivolts of index-sensor output. First pool the scheduled windows for each person on each day. Average the two day scores for that person, then weight the people equally. The last-reading forecast has no learned coefficients.

| Forecast | MAE, 12 fit participants | RMSE, 12 fit participants | MAE, 4 outside the fit | RMSE, 4 outside the fit |
| --- | ---: | ---: | ---: | ---: |
| Last reading | 7.372 | 12.932 | 7.222 | 14.212 |
| Index history | 8.095 | 12.495 | 7.992 | 12.957 |
| Five histories | 7.894 | 12.172 | 7.802 | 12.655 |
| Five-sensor summary | 7.977 | 12.338 | 7.863 | 12.792 |

## When was the index finger cued?

Eight combinations asked for index-finger contraction. Seven prescribed other fingers. All five transducers kept recording in both cases. “Index uncued” describes the instruction, not an assumption of zero index voltage. The table reports matched MAE in mV, with the gain from five histories calculated before rounding. Positive gain means a smaller error than the index-history model. Brackets show the middle 95% of participant-resampled mean gains.

| People | Combinations | Last reading | Index history | Five histories | Five-sensor summary | Five vs index, mV [range] | People improved |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 fit | All 15 | 7.372 | 8.095 | 7.894 | 7.977 | +0.201 [+0.147, +0.255] | 12/12 |
| 12 fit | Index cued | 8.702 | 8.970 | 8.758 | 8.849 | +0.212 [+0.157, +0.267] | 12/12 |
| 12 fit | Index uncued | 5.851 | 7.095 | 6.906 | 6.981 | +0.189 [+0.126, +0.256] | 11/12 |
| 4 outside fit | All 15 | 7.222 | 7.992 | 7.802 | 7.863 | +0.190 [+0.124, +0.279] | 4/4 |
| 4 outside fit | Index cued | 8.562 | 8.951 | 8.743 | 8.815 | +0.208 [+0.125, +0.314] | 4/4 |
| 4 outside fit | Index uncued | 5.690 | 6.896 | 6.727 | 6.775 | +0.169 [+0.123, +0.238] | 4/4 |

Across all 15 combinations, the five-history forecast lowered RMSE relative to repeating the last reading in both cohorts. Among uncued trials alone, repeating the last reading also had the smallest RMSE in the 12-person group; the five-history forecast had the smallest RMSE in the four-person group. A comparison that reports only the learned models, or only one error measure, misses that distinction. Day-specific results and the remaining paired contrasts are available at full precision. [Aggregate results](RESULTS.json)

The input and target are released transducer voltages. The comparison leaves upstream filtering delay, live causal availability, the source of cross-finger correlation, and force in newtons unresolved. It does not estimate nerve activity, muscle force or the effect of commanding a device. No N-DoF samples updated the model weights or scaling. [Model inputs and coefficients](../whole-hand/PREDICTOR.md) · [Hyser 2.0.0](https://physionet.org/content/hd-semg/2.0.0/)

## Reproduce the two cohort summaries

The [Python scorer](../score_prescribed.py) includes the same four forecasts and paired summaries. Keep the `ndof_dataset` directory structure from Hyser 2.0.0 and verify the original files against PhysioNet's checksum index. From the directory containing `score_prescribed.py`, supply your local dataset path. This example selects only first repetitions. It prints cohort summaries and keeps individual session scores in memory.

```python
import hashlib
import json
from pathlib import Path
from score_prescribed import score_session, summarize_people

dataset = Path("/path/to/ndof_dataset")
people = sorted(
    (f"S{n:02d}" for n in range(1, 21)),
    key=lambda person: hashlib.sha256(
        f"hyser-random-index-20261119-v1/{person}".encode()
    ).hexdigest(),
)
for label, members in (("random_fit", people[:12]), ("previous_development", people[12:16])):
    days = [
        {day: score_session(dataset / f"subject{p[1:]}_session{day}") for day in (1, 2)}
        for p in members
    ]
    print(json.dumps({label: summarize_people(days)}, allow_nan=False))
```

The four reserved people are outside both selections. [Download the Python scorer](../downloads/Hyser-Crossday-Python.zip) · [Score a single combination](../SCORE-SESSION.md)

Contains information from Jiang, Dai, Liu and Fan’s Hyser 2.0.0, made available under the Open Data Commons Attribution License. [License](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [PhysioNet platform](https://doi.org/10.1038/s44360-026-00096-z)
