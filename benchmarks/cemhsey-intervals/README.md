# How wide should the pinch forecast be?

A point forecast gives you one force reading to expect. How often does the gauge land close to that number? We test two bands around the same forecast. One uses errors from across the pinch. The other uses errors from the same part of the cue, such as the ramp or the steady hold. Both aim to include 90% of later readings.

The point models were already fitted. Eight recordings from four people set the band widths. Eight different recordings from two other people test how much they cover and how wide they have to be. The interval score charges for both width and misses, so drawing a very wide band carries a cost. Each 30-second trial contributes 592 overlapping forecasts. We report how the bands behave on these two people. [Study design](PROTOCOL.md) · [Input commitments](DESIGN.json) · [Original acquisition study](https://doi.org/10.1038/s41597-025-05733-y) · [Interval score, equation 43](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

## What happened on the eight evaluation trials?

For the five-grid point forecast, one fixed width covered 4,476 of 4,736 later readings (94.5%). Letting the width change with the cue covered 4,502 (95.1%). The phase-based band was narrower, covered at least as many readings and lowered the interval score on these two people.

| Point forecast | Band width set by | Later readings inside | Coverage | Mean width | Mean interval score |
| --- | --- | ---: | ---: | ---: | ---: |
| Current force carried forward | All cutoffs | 4,493 / 4,736 | 94.9% | 0.0289 | 0.0332 |
| Current force carried forward | Matching cue phase | 4,499 / 4,736 | 95.0% | 0.0254 | 0.0290 |
| Force history and cue | All cutoffs | 4,466 / 4,736 | 94.3% | 0.0220 | 0.0260 |
| Force history and cue | Matching cue phase | 4,494 / 4,736 | 94.9% | 0.0215 | 0.0247 |
| Force, cue and five EMG grids | All cutoffs | 4,476 / 4,736 | 94.5% | 0.0221 | 0.0260 |
| Force, cue and five EMG grids | Matching cue phase | 4,502 / 4,736 | 95.1% | 0.0216 | 0.0248 |

Release was the difficult part of the cue. Every band fell below its 90% target there. The phase-based band around the five-grid forecast covered 704 of 800 release readings (88.0%), despite its higher coverage over the whole trial.

Width and interval score are in fractions of maximum voluntary contraction. Both include the same forecast cutoffs. A smaller score reflects the combined cost of width and misses. The target coverage was 90%. Rounding the widths for display can hide small differences. The comparison uses the unrounded means. [Full numerical results](RESULTS.json) · [Explore by cue phase or recording day](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/)

Each trial spans the same 30-second cue. A band can miss at many adjacent cutoffs during one excursion of the gauge. Four calibration participants and two evaluation participants do not establish population coverage, online timing, or simultaneous coverage of an entire trace. [Original recording study](https://doi.org/10.1038/s41597-025-05733-y) · [Interval score, equation 43](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

[Download the 48 pooled and phase-based comparisons, including the fraction below and above each band](../../docs/cemhsey-intervals/metrics.csv).
