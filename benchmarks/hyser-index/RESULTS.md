[The studies](../README.md) › Study 14 · One finger: muscle signal

# Forearm EMG added nothing to the finger sensor's own history

Press a finger against a fixed sensor and its voltage changes even when the finger barely moves. For four test people, a straight-line fit on the sensor's last 41 readings forecast its voltage 120 ms ahead with an average miss of **14.355 mV**, both days together. With the forearm's surface EMG added, it missed by **14.457 mV**: 0.103 mV worse, with two people better and two worse. The twelve people the fit was made on, each scored by a fit made without them, said the same: the sensor's history alone did better. Repeating the last reading missed by 17.945 mV.

The main measure is the plain average miss (mean absolute error), in millivolts of the sensor's output; the dataset gives no conversion to newtons. The last two columns of the table give the measure that punishes large misses (root mean squared error). EMG is electrical activity of muscle, picked up on the skin: a recording of muscle, not of nerve. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small.

| Forecast (mV) | 12 fitting people, day 1 | Day 2 | Both days | 4 test people, day 1 | Day 2 | Both days | Large misses, fitting people | Large misses, test people |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Repeat the last reading | 19.575 | 20.718 | 20.147 | 17.333 | 18.558 | 17.945 | 31.974 | 29.276 |
| Carry the recent change forward | 19.517 | 21.284 | 20.401 | 15.508 | 17.086 | 16.297 | 32.719 | 26.490 |
| The sensor's history | 16.158 | 17.550 | 16.854 | 13.797 | 14.912 | 14.355 | 25.923 | 22.248 |
| The sensor's history and EMG timed to the forecast | 16.459 | 17.927 | 17.193 | 14.012 | 14.903 | 14.457 | 26.201 | 22.295 |
| The sensor's history and EMG from 400 ms earlier | 16.286 | 17.670 | 16.978 | 13.931 | 14.922 | 14.426 | 26.020 | 22.313 |
| The sensor's history and EMG from the same moment of another trial | 16.280 | 17.629 | 16.955 | 13.911 | 14.938 | 14.424 | 25.999 | 22.295 |

Each fitting person was scored by a fit that left out both of their days and chose its penalties on the other people only. The fit on all twelve was then fixed, scaling, penalties and weights, before the test people were scored. Every version was scored on the same 54,000 forecasts from 120 trials of the fitting people and the same 18,000 forecasts from 40 trials of the test people. Each person counts equally, and the two days count equally within a person. The fitting and test columns are separate groups of people, so their difference does not follow anyone over time.

## Timing made no difference

The paired gain below is the comparison's average miss minus that of EMG timed to the forecast: a positive number favours timed EMG. The brackets hold the middle 95% of averages when people are resampled, in mV.

| Timed EMG against | Gain, 12 fitting people (mV) | Gain, 4 test people (mV) |
| --- | ---: | ---: |
| The sensor's history alone | −0.339 [−0.678, −0.070] | −0.103 [−0.321, +0.115] |
| EMG from 400 ms earlier | −0.215 [−0.539, +0.023] | −0.031 [−0.179, +0.117] |
| EMG from the same moment of another trial | −0.238 [−0.585, +0.029] | −0.033 [−0.253, +0.201] |

Against the sensor's history alone, timed EMG lowered the average miss for 4 of 12 fitting people and 2 of 4 test people. In the test people it made day 1 worse by 0.215 mV and day 2 better by 0.009 mV, with a range for day 2 from −0.107 to +0.151 mV. Four people, with forecasts that are correlated within a trial, are too few to say which way the effect would go in anyone else. EMG moved 400 ms earlier, or taken from the same moment of another trial, did slightly better than EMG timed to the forecast in both groups: the timing carried no gain.

A second analysis of the fitting people asked what happens when the fit can be adjusted to the same person on the same day. Each forecast is scored on one trial, fitted on three other trials from that day, leaving out the trial that supplies the timing control. There, adding timed EMG raised the average miss from 17.043 to 17.316 mV but lowered the measure that punishes large misses from 26.180 to 25.851 mV; the two measures weigh large misses differently. This setting tests neither the next day nor a new person.

## The 120 ms is a distance along the released trace

Hyser recorded raw forearm EMG at 2,048 Hz beside the finger sensors' voltage at 100 Hz, and a shared trigger ties the two clocks together. The EMG features use four fixed 100 ms bins whose last edge is 20 ms before the moment of the forecast. The force input spans 400 ms from first to last reading, and the target is 12 samples later on the same released force channel. The dataset's toolbox filters forwards and backwards in time, and whether the released force could have been available live, and how it was filtered upstream, are not known. Drift, the delay of the devices and any lead time in the body were not measured.

## What it does not show

One index sensor channel, adults with intact fingers, one task in which the fingers press without moving (Hyser's Random task), in sensor volts. The four test people are scored again in studies 15 to 17, so they are no longer a fresh test; the four people set aside were not touched.

- [The plan: features, split and scoring, fixed before scoring](PROTOCOL.md)
- [Results file: scores, paired ranges, scope and source attribution](RESULTS.json)
- [Hyser 2.0.0 dataset](https://doi.org/10.13026/hxan-pe94), [protocol and benchmark paper](https://doi.org/10.1109/TNSRE.2021.3082551), [the authors' toolbox, pinned](https://github.com/Open-EXG/Toolbox-Hyser/tree/ec26459026bef12246dfb1658d05298ee5442457)
- Contains information from Jiang, Dai, Liu and Fan's Hyser 2.0.0 database, made available under the [Open Data Commons Attribution License 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/).
