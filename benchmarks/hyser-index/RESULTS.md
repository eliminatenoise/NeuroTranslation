# The force history set a hard baseline

Press a finger against a fixed sensor and the voltage changes even when the finger barely moves. We asked whether surface EMG helps predict that voltage 120 ms ahead when the model already has 41 recent voltage readings. Force history alone gave lower average error when the two days were combined in the 12-person TRAIN assessment and the separate four-person DEV evaluation. On DEV, the force-history ridge averaged **14.355 mV** absolute error. Adding aligned EMG raised that average to **14.457 mV**.

| Input or rule | TRAIN MAE D1 (mV) | TRAIN MAE D2 (mV) | TRAIN MAE both (mV) | DEV MAE D1 (mV) | DEV MAE D2 (mV) | DEV MAE both (mV) | TRAIN RMSE both (mV) | DEV RMSE both (mV) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistence | 19.575 | 20.718 | 20.147 | 17.333 | 18.558 | 17.945 | 31.974 | 29.276 |
| Recent slope | 19.517 | 21.284 | 20.401 | 15.508 | 17.086 | 16.297 | 32.719 | 26.490 |
| Force history | 16.158 | 17.550 | 16.854 | 13.797 | 14.912 | 14.355 | 25.923 | 22.248 |
| Force history and aligned EMG | 16.459 | 17.927 | 17.193 | 14.012 | 14.903 | 14.457 | 26.201 | 22.295 |
| Force history and earlier EMG | 16.286 | 17.670 | 16.978 | 13.931 | 14.922 | 14.426 | 26.020 | 22.313 |
| Force history and same-phase EMG from another trial | 16.280 | 17.629 | 16.955 | 13.911 | 14.938 | 14.424 | 25.999 | 22.295 |

TRAIN used nested leave-one-person-out scoring. Each fold held out both days of that person and chose penalties using only the other people. The pooled TRAIN refit was locked before DEV, where the scale, penalties and coefficients stayed fixed. Each arm saw the same 54,000 scoring windows across 120 TRAIN trials and the same 18,000 windows across 40 DEV trials. Each scored person contributes equally. The combined result weights both days equally within person. The two columns are distinct evaluations and their difference does not track the same people over time.

## Did alignment matter?

The paired difference subtracts the aligned model’s mean absolute error from its comparator. A positive value favors aligned EMG. The ranges in brackets are the middle 95% of person-resampled averages, in mV.

| Aligned EMG versus | TRAIN gain (mV) | DEV gain (mV) |
| --- | ---: | ---: |
| Force history alone | −0.339 [−0.678, −0.070] | −0.103 [−0.321, +0.115] |
| EMG shifted 400 ms earlier | −0.215 [−0.539, +0.023] | −0.031 [−0.179, +0.117] |
| Same elapsed time in another trial | −0.238 [−0.585, +0.029] | −0.033 [−0.253, +0.201] |

Aligned EMG lowered MAE for four of 12 TRAIN people and two of four DEV people versus force history. On DEV Day 1, it increased error by 0.215 mV. On Day 2, it reduced error by 0.009 mV. The Day 2 paired interval runs from −0.107 to +0.151 mV. With four independent DEV people and correlated windows within each trial, these intervals describe variation in the observed cohort. They cannot establish the direction of an effect in a larger population. The two controls show how much similar EMG features can contribute after moving them away from the scored contraction. Together they give no evidence of a consistent gain from the aligned window in this experiment.

A second TRAIN analysis asks what happens when we can calibrate to the same person on the same day. Each forecast is scored on one trial, while fitting uses three other trials from that day and leaves out the trial that provides the phase control. In that setting, adding aligned EMG raises MAE from 17.043 to 17.316 mV but lowers RMSE from 26.180 to 25.851 mV. These metrics reflect different penalties for larger errors. This setting does not test next-day transfer or calibration in a new participant.

## What the clock measures

Hyser paired raw 2,048 Hz forearm surface EMG with 100 Hz finger force-transducer voltage. Its documented shared trigger anchors the two nominal grids. Raw EMG features use four fixed 100 ms bins with the final edge 20 ms before the forecast anchor. The force input spans 400 ms between its first and last readings, and the target is 12 ticks later in the same released force channel. The benchmark toolbox uses forward/reverse filtering, and the causal availability and exact upstream filtering of the released force are unverified. The 120 ms describes released-trace lookahead. Drift, end-to-end device latency and biological lead time were unmeasured.

This prediction task covers one recorded index sensor channel, adults with intact fingers, and the Hyser Random isometric task. The signal is expressed in sensor volts. Surface EMG measures muscle electrical activity. The four-person split is a development check. The reserved final cohort was untouched.

- [Frozen feature, split and scoring method](PROTOCOL.md)
- [Machine-readable scores, paired intervals, scope and source attribution](RESULTS.json)
- [Hyser 2.0.0 dataset](https://doi.org/10.13026/hxan-pe94), [protocol and benchmark paper](https://doi.org/10.1109/TNSRE.2021.3082551), [pinned author toolbox](https://github.com/Open-EXG/Toolbox-Hyser/tree/ec26459026bef12246dfb1658d05298ee5442457)
- Dataset terms and produced-work attribution follow [Open Data Commons Attribution 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/).
