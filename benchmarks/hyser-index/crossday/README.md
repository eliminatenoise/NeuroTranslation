# Yesterday’s calibration did little for the next day

A person presses the same finger against the same kind of sensor on two different days. Could the first day’s readings help us forecast the second? In a twelve-person Hyser assessment, the person’s own Day 1 calibration lowered Day 2 mean absolute error by 0.021 mV with force history and 0.076 mV with force history plus forearm surface EMG. Both ranges from resampling donor pairs crossed zero. In a separate reuse of four development participants, the unchanged shared forecast had the lowest mean absolute error in both arms.

| Day 2 evaluation | Inputs | Shared forecast (mV) | Own Day 1 (mV) | Someone else’s Day 1 (mV) |
| --- | --- | ---: | ---: | ---: |
| TRAIN, 12 people | Force history | 17.610 | 17.589 | 17.726 |
| TRAIN, 12 people | Force history + aligned EMG | 17.871 | 17.794 | 17.913 |
| DEV reuse, 4 people | Force history | 14.912 | 15.091 | 15.401 |
| DEV reuse, 4 people | Force history + aligned EMG | 14.903 | 15.122 | 15.496 |

These are person-weighted mean absolute errors. Each person provided five labeled trials on Day 1 and five scoring trials on Day 2, with 450 windows per trial. The twelve TRAIN participants provided 60 trials and 27,000 windows on each day. The four DEV participants provided 20 trials and 9,000 windows on each day. Day 1 supplies calibration labels. Day 2 gives an identical scoring set for all three forecasts in each arm.

## Whose calibration helps?

A calibration can come from the right person and still make a forecast worse. On the reused DEV records, using someone’s own Day 1 reduced error relative to using the paired donor by 0.310 mV with force history and 0.375 mV with aligned EMG. Applying either calibration still yielded higher average absolute error than leaving the shared model alone. Force-history root mean squared error changed from 23.287 to 23.280 mV with own calibration, a small change on a metric that weights larger errors more heavily, with a paired range of −0.150 to +0.164 mV.

| Comparison, positive favors own calibration | TRAIN gain (mV) | DEV reuse gain (mV) |
| --- | ---: | ---: |
| Force history, own versus shared | +0.021 [−0.276, +0.455] | −0.180 [−0.188, −0.171] |
| Force history, own versus paired donor | +0.138 [+0.043, +0.238] | +0.310 [+0.102, +0.518] |
| Aligned EMG, own versus shared | +0.076 [−0.279, +0.495] | −0.219 [−0.258, −0.180] |
| Aligned EMG, own versus paired donor | +0.119 [−0.006, +0.326] | +0.375 [+0.166, +0.583] |

The brackets give the middle 95% of resampled pair averages. A pair’s members served as one another’s donor, so both move together in the resampling. TRAIN used six such pairs and overlapping base-fit populations. DEV had just two pairs and reused Day 2 records scored in the initial R106 study. The ranges describe those observations. Four reserved FINAL participants remain unopened. The paired control gives a reason to keep asking whose labels matter, while the shared forecast produced lower mean absolute error on these development records.

## What changed in the model?

The original forecast estimated where the recorded index sensor voltage would be in 120 ms. The adapter learns two numbers from Day 1: a voltage offset and a gain correction on the forecast change from the current reading. It shrinks both numbers toward zero with a fixed ridge penalty of 0.1. On Day 2, the base and the two numbers stay fixed. The paired donor goes through the same math with the same number of labeled trials.

For each TRAIN pair, the shared base learned from both days of ten other people and picked its ridge penalty within those ten. This keeps both people in the comparison outside the shared fit. The earlier R106 TRAIN evaluation left one person out of each fit and recorded Day 2 mean absolute errors of 17.550 mV for force history and 17.927 mV with aligned EMG. These are separate historical scores from eleven-person bases. On DEV, the shared model is exactly the published R106 twelve-person TRAIN fit and reproduces the published Day 2 reference.

The target is released voltage from the index force transducer during Hyser’s isometric Random task in adults with intact fingers. The 120 ms comes from the nominal released sampling grid. The causal availability of the distributed force signal and its upstream processing remain unverified. Drift and real-time device latency were unmeasured. Surface EMG here measures muscle electrical activity. This experiment evaluates an offline single-channel voltage forecast in one task.

[Design and calibration equation](PROTOCOL.md) · [Machine-readable results and paired diagnostics](RESULTS.json)

Contains aggregate results derived from Hyser 2.0.0, published by Xinyu Jiang, Chenyun Dai, Xiangyu Liu and Jiahao Fan and made available by PhysioNet under ODC-By 1.0. [Dataset](https://doi.org/10.13026/hxan-pe94) · [Protocol paper](https://doi.org/10.1109/TNSRE.2021.3082551) · [Dataset license](https://physionet.org/content/hd-semg/view-license/2.0.0/)

[Score your own original session folders](../SCORE-SESSION.md) · [Download the local Python scorer](../downloads/Hyser-Crossday-Python.zip) · [Reference scoring implementation](../crossday_study.py).

[Open the interactive Hyser reader](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) and choose **Personalize across two days**. Pick first-day and second-day folders, or try the two invented days. [Download the offline reader](../downloads/Hyser-Index-Voltage-Reader.zip).
