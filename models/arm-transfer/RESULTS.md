# Forecasts for five new people

The final model learned from 882 eligible trials from S1–S7. It then made forecasts on 630 trials from 5 other people, S8–S12, without any fine-tuning or calibration. The last input was available a quarter-second after the visual cue. The targets were later changes in the elbow, forearm and glove instruments.

A lower score means a closer forecast. Each instrument and forecast horizon enters on its own fitting scale. Each person counts equally, whatever the number of trials. The development column changes its seven training-fold scales across folds. The separate assessment uses the one final set of fitting scales.

| Method | Seven development people, held out in turn | Five new people, fixed model |
| --- | ---: | ---: |
| Trainable Transformer | 0.4519 | 0.4933 |
| Matched MLP | 0.5047 | 0.5500 |
| Cue and history ridge | 0.4571 | 0.5026 |
| Mean change for each cue | 0.4099 | 0.4672 |
| No change | 0.4415 | 0.4888 |
| Transformer without cue | 0.5202 | 0.5524 |
| MLP without cue | 0.5814 | 0.6321 |
| Ridge without cue | 0.5262 | 0.5567 |
| Overall training mean | 0.4653 | 0.5069 |
| Transformer given each wrong cue | 0.6448 | 0.6668 |
| MLP given each wrong cue | 0.7017 | 0.7290 |
| Ridge given each wrong cue | 0.6484 | 0.6818 |
| Mean for each wrong cue | 0.6325 | 0.6738 |

## How often did the Transformer win?

Each line compares forecasts on exactly the same five people. A negative difference favors the Transformer. The interval resamples whole participants 10,000 times. With five people it is an exploratory description. The study required at least a 5% lower mean error and lower error for every person for a consistent advantage.

| Comparison | Average paired difference | Exploratory 95% interval | People with lower error | Criterion |
| --- | ---: | ---: | ---: | --- |
| No change | 0.0045 | -0.0181 to 0.0212 | 1/5 | missed |
| Mean change for each cue | 0.0261 | 0.0034 to 0.0567 | 1/5 | missed |
| Cue and history ridge | -0.0093 | -0.0196 to 0.0063 | 4/5 | missed |
| Matched MLP | -0.0567 | -0.0734 to -0.0406 | 5/5 | met |
| Transformer without cue | -0.0591 | -0.0783 to -0.0399 | 5/5 | met |
| Transformer given each wrong cue | -0.1735 | -0.2146 to -0.1369 | 5/5 | met |

The cue-contribution criterion was met. The attention comparison against ridge and the matched MLP was missed. The combined comparison against the cue alone and persistence was missed.

Across the assessment cohort, 100 of 630 histories contained at least one native input outside the observed fitting range. All eligible histories remained in the comparison.

## Error in native instrument units

Each cell below reports the Transformer followed by the cue-only mean. Every pair uses the same people and trials. The three instruments have different scales. The sensor headers do not provide calibrated degrees or an anatomical sign.

| Time after cutoff | Elbow (Transformer / cue) | Forearm (Transformer / cue) | Index glove (Transformer / cue) |
| --- | ---: | ---: | ---: |
| 0.5 s | 0.0518 / 0.0525 | 0.0190 / 0.0178 | 0.0011 / 0.0011 |
| 1 s | 0.1749 / 0.1714 | 0.4016 / 0.3553 | 0.0063 / 0.0062 |
| 1.5 s | 2.5636 / 2.2076 | 2.8856 / 2.1587 | 0.0398 / 0.0406 |

The index-glove target change was constant at all three horizons in 0 of 15 assessment runs. A constant device reading can reflect little movement, sensor behavior or both. All eligible trials counted.

The downloadable summaries give errors for each instrument, horizon, cue and method, the coverage of the two cohorts, and sorted differences between methods on the same participants. Each contrast sorts its differences independently. No data from S13–S15 entered this study. [Assessment](assessment-summary.json) · [Development](development-summary.json) · [Original file inventory](training-inventory.json) · [Frozen procedure](PROTOCOL.md) · [Source recording](https://doi.org/10.5281/zenodo.834976)
