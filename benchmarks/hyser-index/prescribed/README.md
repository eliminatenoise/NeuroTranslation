[The studies](../../README.md) › Study 17 · One finger: new task

# On a new task, five finger histories beat one, and repeating the last reading beat both

The finger forecasts of studies [14](../RESULTS.md) and [16](../whole-hand/README.md) were fitted on freely chosen presses. Here the same people followed prescribed finger combinations instead. For the four test people, the fit on the index sensor's own history forecast its voltage 120 ms ahead with an average miss of **7.992 mV**; the fit on all five finger histories missed by **7.802 mV**, better for all four. But simply repeating the last index reading missed by 7.222 mV, less than either. On the measure that punishes large misses, the order flips: the five-history fit was best and repeating the last reading worst. The twelve people whose free presses the models were fitted on gave the same pattern, 12 of 12 better with five histories.

The main measure is the plain average miss (mean absolute error), in millivolts of the sensor's output; the measure that punishes large misses is root mean squared error. A study that reports only the fitted models, or only one of the two measures, would miss this.

The models, cutoffs, cue groups, measures and analysis were fixed before any prescribed-combination recording was scored. Each person gave the first repetition of all 15 combinations on each of two days. The twelve fitting people gave 360 trials and 162,000 cutoffs per forecast; the four test people gave 120 trials and 54,000. The four test people's prescribed-combination trials were new to this test, though their free-press scores had already shaped the question. All the data come from the same Hyser group and apparatus. The four people set aside remain unopened. [The plan, fixed before scoring](https://github.com/eliminatenoise/NeuroTranslation/blob/45c1547a8b77a7f38394ff2d2a27735cfec8d75d/benchmarks/hyser-index/prescribed/PROTOCOL.md) · [Original study and task design](https://doi.org/10.1109/TNSRE.2021.3082551)

## Across all 15 combinations, repeating the last reading had the smallest average miss

All entries are in millivolts of the index sensor's output. The forecasts of each person on each day are pooled, the two days averaged for that person, and the people weighted equally. Repeating the last reading has no fitted weights.

| Forecast | Average miss, 12 fitting people | Large misses, 12 fitting people | Average miss, 4 test people | Large misses, 4 test people |
| --- | ---: | ---: | ---: | ---: |
| Repeat the last reading | 7.372 | 12.932 | 7.222 | 14.212 |
| Index history | 8.095 | 12.495 | 7.992 | 12.957 |
| Five finger histories | 7.894 | 12.172 | 7.802 | 12.655 |
| Five sensors, compact | 7.977 | 12.338 | 7.863 | 12.792 |

## Five histories beat one whether or not the index finger was cued

Eight combinations asked for the index finger to press; seven asked for other fingers. All five sensors kept recording either way, so "index not cued" describes the instruction, not a voltage of zero. The table gives the matched average miss in mV, with the gain from five histories worked out before rounding; a positive gain means a smaller miss than the index-history fit. The brackets hold the middle 95% of mean gains when people are resampled.

| People | Combinations | Repeat the last reading | Index history | Five histories | Five sensors, compact | Five against index, mV [range] | People better |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 fitting | All 15 | 7.372 | 8.095 | 7.894 | 7.977 | +0.201 [+0.147, +0.255] | 12/12 |
| 12 fitting | Index cued | 8.702 | 8.970 | 8.758 | 8.849 | +0.212 [+0.157, +0.267] | 12/12 |
| 12 fitting | Index not cued | 5.851 | 7.095 | 6.906 | 6.981 | +0.189 [+0.126, +0.256] | 11/12 |
| 4 test | All 15 | 7.222 | 7.992 | 7.802 | 7.863 | +0.190 [+0.124, +0.279] | 4/4 |
| 4 test | Index cued | 8.562 | 8.951 | 8.743 | 8.815 | +0.208 [+0.125, +0.314] | 4/4 |
| 4 test | Index not cued | 5.690 | 6.896 | 6.727 | 6.775 | +0.169 [+0.123, +0.238] | 4/4 |

Across all 15 combinations the five-history fit scored lower than repeating the last reading on the measure that punishes large misses, in both groups. On the combinations where the index finger was not cued, repeating the last reading scored lowest on that measure in the twelve fitting people, and the five-history fit in the four test people. The results for each day and the other paired comparisons are in the [results file](RESULTS.json), at full precision.

## What it does not show

The input and the target are released sensor voltages. The delay of upstream filtering, whether the signals could have been available live, where the link between fingers comes from, and the force in newtons stay open. No prescribed-combination sample changed the models' weights or scaling. [Model inputs and weights](../whole-hand/PREDICTOR.md) · [Hyser 2.0.0](https://physionet.org/content/hd-semg/2.0.0/)

## Score the two groups again

The [Python scorer](../score_prescribed.py) holds the same four forecasts and paired summaries. Keep the `ndof_dataset` folder structure of Hyser 2.0.0 and check the original files against PhysioNet's checksum index. From the folder holding `score_prescribed.py`, give the path of your local copy of the dataset. This example takes only first repetitions, prints the group summaries and keeps each session's scores in memory.

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

The code's two labels are the twelve fitting people (`random_fit`) and the four test people (`previous_development`); the four people set aside fall outside both. [Download the Python scorer](../downloads/Hyser-Crossday-Python.zip) · [Score a single combination](../SCORE-SESSION.md)

Contains information from Jiang, Dai, Liu and Fan’s Hyser 2.0.0, made available under the Open Data Commons Attribution License 1.0. [License](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [PhysioNet platform](https://doi.org/10.1038/s44360-026-00096-z)
