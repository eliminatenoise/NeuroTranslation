[The studies](../../README.md) › Study 13 · Paced grip: a fit that changes with the cue

# The plain fit beat the fit that changes with the cue for all three people

Just before the cue says relax, a rising grip voltage could mean something different from a rise in the middle of a squeeze. A forecast was given six extra weights to express that difference. For the three test people of [study 11](../results-2026-11-19/), the plain straight-line fit on the sensor's full recent history forecast the voltage 120 ms ahead with an error of **0.3601 mV**; the fit allowed to differ between squeeze and rest missed by **0.3741 mV**, worse for all three. Against its own compact version, the one comparison in which only the squeeze-and-rest weights differ, the new fit had helped among the fitting people; on the test people it changed the error by 0.000482 mV, worse for two of the three. It failed the rule set for it before fitting. [The plan, posted before fitting](https://github.com/eliminatenoise/NeuroTranslation/blob/71c196dd10aabdc1b0fe2750b87a1df3f2edb96e/benchmarks/hygrip-force/cue-phase/PROTOCOL.md)

Every score here is the measure that punishes large misses (root mean squared error), worked out for each person and averaged, in millivolts of the sensor's output. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small.

| Forecast | Seven fitting people (mV) | Three test people (mV) |
| --- | ---: | ---: |
| Repeat the last voltage | 0.531851 | 0.516850 |
| Carry the recent change forward | 0.558423 | 0.496622 |
| The original fit on the sensor's history | **0.393763** | **0.360083** |
| A compact fit on a few summaries of that history | 0.410521 | 0.373600 |
| The compact fit, allowed to differ between squeeze and rest | 0.402769 | 0.374083 |

Each person counts equally, each trial equally within a person, and each forecast equally within its trial. The penalties were chosen on the fitting people (0.01 for the history fit and the compact fit, 0.1 for the fit that changes with the cue), so the fitting people's errors are flattered by that choice. The test people were then scored once with the fixed fits; they had already been scored in study 11. The three people set aside stayed unopened.

Against its own compact version, the squeeze-and-rest terms lowered the fitting people's error by 0.007752 mV (6 of 7 better, 95% range across people −0.017523 to +0.002020 mV) and raised the test people's by 0.000482 mV (1 of 3 better, range −0.011141 to +0.012105 mV). Against the original 27-input fit they raised the error by 0.009005 mV among the fitting people and 0.014000 mV among the test people, where none of the three did better (range −0.017095 to +0.045094 mV). The original fit had the lower error, but it differs in two ways: it forecasts the voltage directly and reads all 20 recent readings separately. Only the compact fit differs by the squeeze-and-rest terms alone, so that comparison is the one that tests them.

In the test people, the two stretches where the cue switched favoured the new fit over the original on average. They held 540 and 390 forecasts, against 5,505 during scheduled squeezing and 1,560 during scheduled rest. Those differences are descriptive, and every stretch comes from the same three people.

## What was measured

The target was the released voltage of the right-hand grip sensor in the HYGRIP task, sampled at 50 Hz. Every forecast used the same schedule of forecast moments and the target six samples later, 120 ms on the released clock. Every comparison uses the same 16,195 forecasts from 79 trials of the seven usable fitting people and the same 7,995 forecasts from 39 trials of the three test people. One of the eight assigned fitting runs was held back by the clock check on the fitting recordings, before any model was fitted (13 right-hand trials and 2,665 planned forecasts). Every forecast in the usable runs was scored. The earlier scores of the history fit, of repeating the voltage and of carrying the change forward were reproduced exactly, for each group and each stage of the cue. [HYGRIP descriptor](https://doi.org/10.3389/fnins.2020.00919) · [The earlier study, as it stood](https://github.com/eliminatenoise/NeuroTranslation/tree/6fcd4d79894f7844ece20108cdd3bc728f193f74/benchmarks/hygrip-force)

## What it does not show

A scheduled switch marks the intended stage of the cue; it is not an observation of the moment the screen or the hand actually switched. The unit is the released voltage, so there is no error in newtons and no claim about physical timing.

## The plan

The rule fixed before fitting asked for a lower average error than all four comparison forecasts in both groups, and for most people to improve against both fitted comparisons. The new fit failed and stays an experiment; the original 27-input fit remains the forecast to beat. The downloadable table holds the forecast counts behind each stage of the cue, the paired comparisons against all four forecasts and the fitting people's grid of penalties.

The recordings are HYGRIP, described by Pablo Ortega, Tong Zhao and A. Aldo Faisal and deposited under the MIT licence. Full credit: [docs/RIGHTS.md](../../../docs/RIGHTS.md).

[The plan](PROTOCOL.md) · [Results of the fitting people](TRAIN.json) · [Results of the test people](DEV.json) · [Download the comparison](HYGRIP-Cue-Phase-Aggregates.zip)
