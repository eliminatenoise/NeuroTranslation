# Transfer to a treadmill force dataset

Linear extrapolation from the last two force means had the lowest impulse error, **9.64445 N·s**. Three passes led the frozen NeuroTranslate settings at **10.69183 N·s** and beat the linear reference for two of eight people. One pass had the lowest new-load probability error at **0.06997673**, an absolute reduction of **0.00078077** against the fitted event rate. Its event error was lower for all eight people. [Exact scores](results.json) · [Simple edition](SIMPLE.md)

## Data and forecasts

We used eight previously untested participants from Krumm and colleagues at the published 4 km/h setting. The early `run01` reconstruction precedes activity segmentation and force filtering. Walk A covers camera frames 45,001–90,000 and force ticks 180,000–359,999 on the zero-based 1,000 Hz clock. The two vertical force channels were converted to signed upward newtons from the plate geometry. Each row represents a belt. [Study, Tables 1 and 2](https://doi.org/10.1038/s41597-026-07445-3) · [Archive](https://doi.org/10.17605/OSF.IO/KCQTF)

We fixed one forecast time per seven-second interval across 24 intervals for each participant, with both belts issued together. All 384 belt histories contained ten 20 ms means from the last 200 ms. An earlier 800 ms contributed only to the event state. The six surface muscle-voltage channels were unavailable. All five configurations used the same 547-update checkpoint fitted on separate walking recordings with force and muscle voltage. Only the number of passes through the middle 12 decoder layers changed. [Schedule definition and scoring data](results.json) · [Training data](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Checkpoint](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)

The constant-force control held the most recent mean. The linear control extrapolated the last two means from the center of the final bin. Both used the event frequency estimated from the fitting data. A third control combined constant force with zero event probability. All predictions were sealed before later force was requested. A telemetry read failed at shutdown after the worker saved the complete packet and logged its digest. The worker exit and sealed forecasts were independently checked.

## Error on matched rows

Impulse sums the next 100 signed samples and divides by 1,000. For a new load, the belt first reaches a quiet state after 20 samples within ±10 N. Loading starts at a crossing of 20 N confirmed by 20 consecutive samples at or above 20 N. A start within 100 ms can use readings through +119 ms for confirmation. The event metric is mean squared probability error, also called Brier error. We averaged within issue times and participants before giving each of the eight participants equal weight. All 384 rows qualified for impulse. At the forecast time, 71 had unknown loading state and ten had a crossing still awaiting confirmation. The remaining 303 event rows contained 22 distinct onsets and 281 negatives.

| Method | Mean absolute impulse error (N·s) | New-load Brier error |
| --- | ---: | ---: |
| Constant force and fitted event rate | 11.18824 | 0.07075751 |
| Linear force trend and fitted event rate | **9.64445** | 0.07075751 |
| Constant force and zero event probability | 11.18824 | 0.07495471 |
| NeuroTranslate, 1 pass | 11.00871 | **0.06997673** |
| NeuroTranslate, 3 passes | 10.69183 | 0.07072176 |
| NeuroTranslate, 5 passes | 10.85810 | 0.07177581 |
| NeuroTranslate, 7 passes | 10.75955 | 0.07165146 |
| NeuroTranslate, 9 passes | 10.72045 | 0.07155924 |

Three passes beat constant force for six of eight people. On the 303 rows eligible for both endpoints, the linear reference remained first for impulse at 9.31074 N·s. Nine passes led the model settings on that subset at 10.28250 N·s. One pass retained the lowest event error. This test covers short forecasts with measured belt histories at one treadmill speed. The earlier final test stayed sealed, and we made no changes to the trained checkpoint. [Earlier validation with both measurement types](../pass-count/TECHNICAL.md)
