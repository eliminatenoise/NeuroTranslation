# Five sensors helped on DEV. TRAIN kept the index baseline.

How much can the other fingers tell us about the next index reading? In four previously studied Hyser participants, a ridge model that saw all five force-transducer histories lowered mean absolute error from **14.355 mV to 14.161 mV**. In the 12-person TRAIN assessment, adding the four histories raised mean absolute error from **16.854 mV to 16.915 mV**. Both evaluations forecast the same released index voltage 12 ticks ahead on a 100 Hz grid. The extra readings helped on average in one cohort. The wider uncertainty and the opposite result in TRAIN leave the primary question open.

## Same target, different inputs

Every arm saw the same index history, cutoffs and targets. The index-only ridge takes 41 readings through the cutoff. The five-history ridge adds 41 readings from each of the other four sensors in the same trial. The other-trial control replaces those four histories with the corresponding histories from the next trial, wrapping from trial 5 to trial 1 within that person and day. The control preserves elapsed trial time and the number of inputs. Its four added histories belong to a different contraction, so it serves as an offline comparison. The compact model replaces the four extra histories with each sensor’s current reading and its linear trend over those same 41 readings.

The 12 TRAIN participants contributed 120 trials and 54,000 windows per arm. Both days of each held person stayed outside fitting and penalty selection. We fit the final models across TRAIN and locked them before scoring the four previously studied DEV participants. DEV contributed 40 trials and 18,000 windows per arm. Each person receives equal weight within each day, then both days receive equal weight. Across both evaluations, we reproduced every prior index baseline MAE and RMSE for both days and each day separately. FINAL remains reserved. [Prespecified protocol](PROTOCOL.md) · [Earlier index study](../README.md)

| Model | TRAIN MAE day 1 | Day 2 | Both | TRAIN RMSE day 1 | Day 2 | Both |
|:--|--:|--:|--:|--:|--:|--:|
| Index history | 16.158 | 17.550 | 16.854 | 24.807 | 27.039 | 25.923 |
| Five aligned histories | 16.246 | 17.584 | 16.915 | 24.708 | 27.020 | 25.864 |
| Other-trial control | 16.186 | 17.630 | 16.908 | 24.808 | 27.074 | 25.941 |
| Five sensors, compact summary | 16.337 | 17.574 | 16.955 | 24.869 | 26.927 | 25.898 |

| Model | DEV MAE day 1 | Day 2 | Both | DEV RMSE day 1 | Day 2 | Both |
|:--|--:|--:|--:|--:|--:|--:|
| Index history | 13.797 | 14.912 | 14.355 | 21.210 | 23.287 | 22.248 |
| Five aligned histories | 13.477 | 14.845 | 14.161 | 20.629 | 22.720 | 21.674 |
| Other-trial control | 13.874 | 14.950 | 14.412 | 21.256 | 23.296 | 22.276 |
| Five sensors, compact summary | 13.481 | 14.897 | 14.189 | 20.764 | 22.878 | 21.821 |

Errors are in mV of released transducer output. For each paired comparison, positive means the focus model lowered error. Brackets show the middle 95% of resampled averages with the person as the resampling unit. The tables use unrounded results.

| Focus versus comparator, both days | TRAIN MAE gain (mV) | DEV MAE gain (mV) | TRAIN RMSE gain (mV) | DEV RMSE gain (mV) |
|:--|--:|--:|--:|--:|
| Five histories versus index | −0.062 [−0.344, +0.204] | +0.193 [−0.187, +0.573] | +0.059 [−0.283, +0.367] | +0.574 [+0.070, +1.077] |
| Five histories versus other-trial control | −0.008 [−0.320, +0.278] | +0.251 [−0.123, +0.624] | +0.077 [−0.279, +0.391] | +0.601 [+0.104, +1.099] |
| Five histories versus compact summary | +0.040 [−0.087, +0.145] | +0.028 [−0.080, +0.123] | +0.034 [−0.183, +0.230] | +0.147 [+0.016, +0.277] |
| Compact summary versus index | −0.102 [−0.413, +0.228] | +0.166 [−0.119, +0.470] | +0.025 [−0.235, +0.274] | +0.427 [+0.054, +0.800] |
| Other-trial control versus index | −0.054 [−0.084, −0.019] | −0.057 [−0.078, −0.037] | −0.018 [−0.052, +0.018] | −0.027 [−0.052, −0.009] |

The DEV result is stronger for RMSE, which gives large errors more weight. Its resampled ranges for the comparisons with index and other-trial inputs stay above zero. For MAE, the ranges cross zero, and five aligned histories helped only two of four DEV people against index history. The compact model gives up only 0.028 mV of average DEV MAE compared with full histories while using 49 features instead of 205. Both models still require all five sensors. The observed gap is small and the uncertainty leaves their relative performance open. Four reused people, overlapping TRAIN fits and one fixed trial reassignment limit what these comparisons can establish. [Unrounded results and all day-level paired summaries](RESULTS.json)

## Use the predictor

The Python reference takes a past-only window of 41 voltage samples per supplied channel. It forecasts 120 ms ahead **in the released trace**. Hyser’s benchmark applies forward/reverse filtering after loading the data. The processing upstream of the release and causal availability of those voltages remain unverified. These are voltages from one isometric task. We measured no instrument delay, force in newtons, mechanism of finger coupling, neural activity or closed-loop performance in this experiment. The exported weights contain three pooled TRAIN models. The other-trial control is available through its aggregate scores. [Inputs and Python usage](PREDICTOR.md) · [Frozen rule and source limits](PROTOCOL.md) · [Pooled weights](WEIGHTS.json)

Contains aggregate measurements and models derived from Jiang, X., Dai, C., Liu, X., & Fan, J. (2023), *Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings*, version 2.0.0, PhysioNet. [Dataset](https://doi.org/10.13026/hxan-pe94) · [Paper](https://doi.org/10.1109/TNSRE.2021.3082551) · [Open Data Commons Attribution 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/)
