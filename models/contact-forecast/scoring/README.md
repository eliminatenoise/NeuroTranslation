# Score the cortical count forecasts

The scorer compares each prediction with the number of events the recording actually contains at each of 26 electrodes during the next 100 ms. It keeps every eligible forecast window. When a comparison requires another trial's movement, all methods are scored again on the same windows with an earlier matching trial. Read the [scoring protocol](PROTOCOL.md) for the units, weights, donor matching and interval construction.

The [held-day report](test/RESULTS.md) covers the second recording day. The [development report](validation/RESULTS.md) covers a separate block of the first day. Each report directory includes the machine-readable scores, per-original scores, subgroup tables and exact donor rows.

## What changed when the model saw the handle?

On the next day's pushes, replacing the correct movement with motion from an earlier, otherwise matched trial made the full model's count forecasts slightly worse. Correct movement reduced Poisson deviance by 0.003184 per count observation (95% interval for the reduction 0.000713 to 0.006099). A model trained to use counts and cues alone came much closer. The full model's advantage over that comparison was 0.002610, with an interval ranging from a disadvantage of 0.001317 to an advantage of 0.006967. The experiment therefore leaves the incremental value of movement unresolved. All 2,436 paired windows came from the same 609 original push trials.

Absolute count error asks a different question. It measures how many events a prediction missed by, giving a miss of one event the same cost wherever it occurred. On that scale the full model missed by 1.039200 events per contact per 100 ms on average, 0.007575 more than counts and cues alone (95% interval 0.006349 to 0.008796). Its mean forecast was 0.957371 events against a measured mean of 1.172240.

| Matched pre-target pushes | Mean absolute count error | Poisson deviance |
|---|---:|---:|
| Full Transformer | 1.039200 | 1.987496 |
| Counts and cues Transformer | 1.031625 | 1.990106 |
| Full Transformer with another trial’s movement | 1.040133 | 1.990681 |
| Full Poisson regression | 1.201490 | 2.497408 |
| Cue-only Poisson regression | 1.018217 | 1.904994 |
| Training mean for the same contact | 1.091750 | 2.079917 |
| Copy the preceding count | 1.014873 | 11.118454 |

Copying the preceding count often came close in absolute terms. Across 63,336 contact windows, it predicted exactly zero 36,317 times. The contact subsequently recorded at least one event in 13,569 of those cases. Those cases give infinite Poisson deviance before applying the common positive floor. The table gives the floored result.

The two go-cue conditions pose another test. Training used only pushes before target appearance. On go cues after a push and on go cues without a push, counts and cues alone gave lower deviance than the full model. Full minus counts-and-cues was +0.018811 (95% interval +0.013514 to +0.023743) after a push and +0.019174 (+0.016659 to +0.021845) without one. These secondary results have pointwise intervals and come from the same animal and recording date as the primary test.

## Reproduce the calculation

Python 3.11 or later and NumPy are required. From the scoring directory, the following commands assume the source extractor has written its numerical files to `../source` and the model runner has written its two prediction files per split to `../models`. The training file is the first day's verified training archive. Both its original and reconstructed encodings are accepted after their contents pass the identity checks.

```sh
python -B test_score.py
python -B score.py --stage validation --train ../source/train.npz --source ../source --models ../models --output reproduced-validation
python -B score.py --stage test --train ../source/train.npz --source ../source --models ../models --release held-day-release.json --output reproduced-test
```

For source arrays reconstructed in a separate directory, pass its path to `--source` and supply `--metadata ../source`. The split and contact identity files are read from the metadata directory. The source NPZ, its matching QC report and the two prediction NPZs must use the same ordered trial windows. The returned hashes identify the input files actually scored. A rebuilt ZIP container can have a different file hash while retaining the same training arrays and scores.

## Read a result

For the primary comparison, open `test/summary.json` and select `phases.pre_target_bump.matched.contrasts`. Find `transformer_all-minus-transformer_count_cue` and `transformer_all-minus-transformer_wrong_movement`. Their `deviance` records give the difference in score, its 95% interval and the number of usable bootstrap draws. A negative difference favours the full model.

The `scores` entries give mean absolute error, deviance, measured mean count and predicted mean count. The `seeds` entries keep the three Transformer fits separate. The `assigned_timeline_sensitivity` entries repeat the paired calculations across the complete assigned trial sequence. The contact numbers in the tables are source channel labels.

The day-one constant forecast is the training mean for each contact. Persistence copies the count from the preceding 100 ms. On some windows a contact records events after the preceding count was zero. The `forecast_zero_counts` entries give these exact-zero denominators for each fitted seed or deterministic method. The deviance calculation uses a positive floor of one millionth of an event for every method.

The recordings were deposited by Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller under CC0. [Dataset](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original study](https://doi.org/10.7554/eLife.48198)
