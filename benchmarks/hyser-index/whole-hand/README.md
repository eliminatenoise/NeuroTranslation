[The studies](../../README.md) › Study 16 · One finger: the other four fingers

# The other four fingers helped the four test people and not the twelve the fit was made on

How much do the other fingers say about the next index reading? For the four test people of [study 14](../RESULTS.md), a straight-line fit on the index sensor's last 41 readings forecast its voltage 120 ms ahead with an average miss of **14.355 mV**. Given the same history from all five finger sensors, it missed by **14.161 mV**: 0.193 mV better on average, though better for only two of the four, with a range from 0.573 mV better to 0.187 mV worse. In the twelve people the fit was made on, the same change raised the average miss, from 16.854 to 16.915 mV. One group gained and the other did not, so the question stays open. The rule set before scoring asked for a gain against both the index history and a control from another trial; it got a split answer.

The main measure is the plain average miss (mean absolute error), in millivolts of the sensor's output; the measure that punishes large misses (root mean squared error) is shown beside it. A *straight-line fit* is a weighted sum of its inputs, here a ridge regression.

## Same target, different inputs

Every version saw the same index history, cutoffs and targets. The index-only fit takes 41 readings up to the cutoff. The five-finger fit adds 41 readings from each of the other four sensors in the same trial. The other-trial control swaps those four histories for the matching ones from the next trial of the same person and day, wrapping from trial 5 to trial 1: it keeps the time in the trial and the number of inputs, but its four added histories belong to a different press, which only an analysis after the fact can do. The compact fit replaces the four extra histories with each sensor's current reading and its straight-line trend over the same 41 readings.

The twelve fitting people gave 120 trials and 54,000 forecasts per version. Both days of the person being scored stayed out of the fit and of the choice of penalty. The final fits were made on all twelve and fixed before the four test people, already scored in study 14, were scored: 40 trials and 18,000 forecasts per version. Each person counts equally within a day, then the two days count equally. Every earlier index-only score was reproduced, on both measures, for both days together and each day alone. The four people set aside stay unopened. [The plan, fixed in advance](PROTOCOL.md) · [Study 14](../RESULTS.md)

| 12 fitting people (mV) | Average miss, day 1 | Day 2 | Both | Large misses, day 1 | Day 2 | Both |
|:--|--:|--:|--:|--:|--:|--:|
| Index history | 16.158 | 17.550 | 16.854 | 24.807 | 27.039 | 25.923 |
| Five finger histories | 16.246 | 17.584 | 16.915 | 24.708 | 27.020 | 25.864 |
| Other-trial control | 16.186 | 17.630 | 16.908 | 24.808 | 27.074 | 25.941 |
| Five sensors, compact | 16.337 | 17.574 | 16.955 | 24.869 | 26.927 | 25.898 |

| 4 test people (mV) | Average miss, day 1 | Day 2 | Both | Large misses, day 1 | Day 2 | Both |
|:--|--:|--:|--:|--:|--:|--:|
| Index history | 13.797 | 14.912 | 14.355 | 21.210 | 23.287 | 22.248 |
| Five finger histories | 13.477 | 14.845 | 14.161 | 20.629 | 22.720 | 21.674 |
| Other-trial control | 13.874 | 14.950 | 14.412 | 21.256 | 23.296 | 22.276 |
| Five sensors, compact | 13.481 | 14.897 | 14.189 | 20.764 | 22.878 | 21.821 |

In the paired comparisons below, a positive gain means the first forecast lowered the error. The brackets hold the middle 95% of averages when people are resampled. All values are worked out before rounding.

| First against second, both days | Average miss, fitting (mV) | Average miss, test (mV) | Large misses, fitting (mV) | Large misses, test (mV) |
|:--|--:|--:|--:|--:|
| Five histories against index | −0.062 [−0.344, +0.204] | +0.193 [−0.187, +0.573] | +0.059 [−0.283, +0.367] | +0.574 [+0.070, +1.077] |
| Five histories against other-trial control | −0.008 [−0.320, +0.278] | +0.251 [−0.123, +0.624] | +0.077 [−0.279, +0.391] | +0.601 [+0.104, +1.099] |
| Five histories against compact | +0.040 [−0.087, +0.145] | +0.028 [−0.080, +0.123] | +0.034 [−0.183, +0.230] | +0.147 [+0.016, +0.277] |
| Compact against index | −0.102 [−0.413, +0.228] | +0.166 [−0.119, +0.470] | +0.025 [−0.235, +0.274] | +0.427 [+0.054, +0.800] |
| Other-trial control against index | −0.054 [−0.084, −0.019] | −0.057 [−0.078, −0.037] | −0.018 [−0.052, +0.018] | −0.027 [−0.052, −0.009] |

The test people's result is stronger on the measure that punishes large misses: there, the ranges against the index history and against the other-trial control stay above zero. On the average miss they cross zero, and five histories helped only two of four test people against the index history. The compact fit gives up only 0.028 mV of the test people's average miss against the full histories while using 49 inputs instead of 205, though both still need all five sensors; the gap is small and its direction uncertain. [Results file, unrounded, with every paired summary by day](RESULTS.json)

## What it does not show

Four test people reused from study 14, fitting groups that overlap, and one fixed reassignment of trials for the control limit what these comparisons can show. These are voltages from one task in which the fingers press without moving; no instrument delay, force in newtons, mechanism linking the fingers, brain activity or control of a device was measured.

## Use the forecast

The Python reference takes a window of 41 voltage samples per channel, ending at the cutoff, and forecasts 120 ms ahead **in the released trace**. Hyser's benchmark filters forwards and backwards after loading the data, and the processing before release, and whether these voltages could have been available live, are not known. The weights file holds the three fits made on all twelve fitting people; the other-trial control exists only as its summary scores. [Inputs and Python use](PREDICTOR.md) · [The plan and the source's limits](PROTOCOL.md) · [Fitted weights](WEIGHTS.json)

Contains aggregate measurements and models derived from Jiang, X., Dai, C., Liu, X., & Fan, J. (2023), *Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings*, version 2.0.0, PhysioNet. [Dataset](https://doi.org/10.13026/hxan-pe94) · [Paper](https://doi.org/10.1109/TNSRE.2021.3082551) · [Open Data Commons Attribution 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/)
