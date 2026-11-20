[The studies](../../README.md) › Study 15 · One finger: next-day adjustment

# A correction fitted on the first day helped one of four people on the second

A person presses the same finger against the same kind of sensor on two days. Can the first day's readings improve the forecast on the second? For the four test people of [study 14](../RESULTS.md), the shared forecast of the index sensor 120 ms ahead missed by **14.912 mV** on day 2. Corrected on the person's own day 1, it missed by **15.091 mV**: 0.180 mV worse, and better for one person of four. With forearm EMG in the forecast the result was the same: the unchanged shared forecast had the smallest average miss.

In the twelve people the shared fit was made on, the same correction went the other way, a little. The person's own day 1 lowered the day-2 average miss by 0.021 mV with the sensor's history alone (17.610 to 17.589 mV, better for 4 of 12) and by 0.076 mV with EMG added. Both ranges cross zero.

Every score here is the plain average miss (mean absolute error), in millivolts of the sensor's output, with each person counting equally. EMG is electrical activity of muscle, picked up on the skin: a recording of muscle, not of nerve.

| Scored on day 2 | Inputs | Shared forecast (mV) | Corrected on own day 1 (mV) | Corrected on someone else's day 1 (mV) |
| --- | --- | ---: | ---: | ---: |
| 4 test people, already scored in study 14 | The sensor's history | 14.912 | 15.091 | 15.401 |
| 4 test people, already scored in study 14 | The sensor's history and timed EMG | 14.903 | 15.122 | 15.496 |
| 12 fitting people | The sensor's history | 17.610 | 17.589 | 17.726 |
| 12 fitting people | The sensor's history and timed EMG | 17.871 | 17.794 | 17.913 |

Each person gave five labelled trials on day 1 and five scored trials on day 2, with 450 forecasts per trial: 60 trials and 27,000 forecasts each day from the twelve fitting people, 20 trials and 9,000 forecasts each day from the four test people. Day 1 supplies the corrections; day 2 is the same scoring set for all three forecasts in each row.

## Whose day 1 matters

A correction can come from the right person and still make a forecast worse. In the four test people, the person's own day 1 beat the paired donor's by 0.310 mV with the sensor's history and 0.375 mV with EMG, and either correction still left a larger average miss than leaving the shared model alone. On the measure that punishes large misses (root mean squared error), the own-day correction moved the history forecast from 23.287 to 23.280 mV, with a paired range of −0.150 to +0.164 mV.

| Gain, positive favours the own-day correction | 12 fitting people (mV) | 4 test people (mV) |
| --- | ---: | ---: |
| The sensor's history: own day 1 against the shared forecast | +0.021 [−0.276, +0.455] | −0.180 [−0.188, −0.171] |
| The sensor's history: own day 1 against the paired donor's | +0.138 [+0.043, +0.238] | +0.310 [+0.102, +0.518] |
| Timed EMG: own day 1 against the shared forecast | +0.076 [−0.279, +0.495] | −0.219 [−0.258, −0.180] |
| Timed EMG: own day 1 against the paired donor's | +0.119 [−0.006, +0.326] | +0.375 [+0.166, +0.583] |

The brackets hold the middle 95% of resampled pair averages. The two people of a pair served as each other's donor, so they move together in the resampling. The fitting people formed six such pairs, with overlapping groups behind their shared fits; the test people formed only two pairs, and their day-2 records had already been scored in study 14. So the four-person ranges are a range across two pairs, not across people, and they describe these records only. The donor comparison gives a reason to keep asking whose labels matter; the shared forecast still had the smaller average miss on these records.

## What the correction is

The original forecast estimated where the index sensor's recorded voltage would be in 120 ms. The correction learns two numbers from day 1: a voltage offset and a gain on the forecast's change from the current reading. A fixed ridge penalty of 0.1 pulls both towards zero. On day 2 the shared forecast and the two numbers stay fixed. The donor correction goes through the same arithmetic with the same number of labelled trials.

For each pair of fitting people, the shared forecast was fitted on both days of ten other people and chose its penalty within those ten, so both people of the pair stay outside the fit. Study 14 had scored the fitting people with one person left out of each fit, and recorded day-2 average misses of 17.550 mV for the sensor's history and 17.927 mV with EMG; those are separate, earlier scores from fits on eleven people. For the test people, the shared forecast is exactly study 14's fit on all twelve fitting people, and it reproduces study 14's published day-2 score.

## What it does not show

The target is the released voltage of the index sensor during Hyser's Random task, in which the fingers press without moving, in adults with intact fingers. The 120 ms comes from the nominal released sampling grid: whether the released force could have been available live, how it was processed upstream, drift and the delay of a live device are not known. Surface EMG measures the electrical activity of muscle. The study covers a forecast of one voltage channel, after the fact, in one task. The four people set aside were not opened.

[The plan and the correction's equation](PROTOCOL.md) · [Results file with the paired checks](RESULTS.json)

Contains aggregate results derived from Hyser 2.0.0, published by Xinyu Jiang, Chenyun Dai, Xiangyu Liu and Jiahao Fan and made available by PhysioNet under ODC-By 1.0. [Dataset](https://doi.org/10.13026/hxan-pe94) · [Protocol paper](https://doi.org/10.1109/TNSRE.2021.3082551) · [Dataset license](https://physionet.org/content/hd-semg/view-license/2.0.0/)

## Try it

[Score your own original session folders](../SCORE-SESSION.md) · [Download the local Python scorer](../downloads/Hyser-Crossday-Python.zip) · [Reference scoring code](../crossday_study.py)

[Open the interactive Hyser reader](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) and choose **Personalize across two days**. Pick a first-day and a second-day folder, or try the two invented days. [Download the offline reader](../downloads/Hyser-Index-Voltage-Reader.zip)
