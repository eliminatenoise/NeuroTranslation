[The studies](../../README.md) › Study 12 · Paced grip: muscle signal

# Forearm EMG lowered the grip forecast's average error, but helped one person in three

Given the cue and the grip sensor's recent voltage, a straight-line fit forecast the sensor's reading six samples (120 ms) ahead for the three test people of [study 11](../results-2026-11-19/) with an error of **0.3601 mV**. Given four channels of forearm EMG as well, it missed by **0.3455 mV**. That is lower on average, but only one of the three people did better, and the same fit given EMG from a different moment of the same trial did better still: 0.3427 mV, better than the timed EMG for all three.

Every score here is the measure that punishes large misses (root mean squared error), worked out for each person and averaged, in millivolts of the sensor's output. EMG is electrical activity of muscle, picked up on the skin: a recording of muscle, not of nerve.

| Error, averaged over people (mV) | Seven fitting people, each scored by a fit without them | Three test people, already scored in study 11 |
| --- | ---: | ---: |
| Cue timing and recent sensor voltage | 0.3938 | 0.3601 |
| The same, with forearm EMG timed to the forecast | 0.4095 | 0.3455 |
| The same, with scalp EEG added on top | 0.4229 | 0.4739 |

The moved-EMG control can use samples from later in the trial, which only an analysis after the fact can do. Its job is to test whether matching the muscle signal to the moment of the forecast matters, and here it did not. Two more timing controls agreed: against EMG from the next trial (0.3456 mV) and EMG ending earlier in the same trial (0.3463 mV), the timed EMG was ahead by less than 0.001 mV, better for two of the three people in each.

Neither the fitting people nor the test people met the rule set before scoring for an advantage that needs correctly timed EMG. Adding scalp EEG to the forecast that already had voltage and EMG raised the error for all three test people; the descriptive interval for that change ran from −0.229 to +0.486 mV. People, trials and forecast moments each counted equally at their level of the average. [Results of the fitting people](TRAIN.json) · [Results of the test people](DEV.json)

## What it does not show

The 79 fitting trials gave 16,195 shared forecast moments, and the 39 test trials gave 7,995. The three test people had already been scored in [study 11](../results-2026-11-19/); the three people set aside were not opened. The errors are in millivolts of the sensor's recorded output: a result in newtons, and the timing of a live system, remain open.

[Download the plan, the summary tables and an offline checker](HYGRIP-Muscle-Train-and-Dev-Aggregates.zip) · [HYGRIP source study](https://doi.org/10.3389/fnins.2020.00919) · [Original data deposit](https://doi.org/10.6084/m9.figshare.12383639.v1)
