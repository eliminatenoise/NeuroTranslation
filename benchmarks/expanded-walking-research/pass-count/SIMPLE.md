# Five pass counts for the Research Edition

A follow-up on the same nine walks compares two, three and four passes. [Read the follow-up](near-three/SIMPLE.md)

Three passes gave the lowest error when forecasting how much force would build up on the floor over the next tenth of a second. Five passes did slightly better at estimating the chance that a plate would start taking load. Both results come from the same nine recorded walks.

## What a pass does

The model reads a fifth of a second of muscle voltages and force measured underfoot. The voltages measure electrical activity in the muscles. The floor plates measure the force between the person and the ground. The model makes two predictions for the next tenth of a second. One is how much vertical force accumulates during that time. The other is the probability of a plate starting to take load.

The model has 24 layers. The middle 12 can repeat, taking information from their preceding pass. One pass goes through the middle once. Nine passes run that same middle section nine times. Each setting used the same saved weights. Those weights were fitted at three passes, so this comparison measures what happens when we change the number of passes during use.

## The comparison

Twelve people supplied the data used to fit the weights. We used recordings from three other people for this comparison. Half of the six people assigned to validation had all six named muscle recordings and usable force data. Each qualifying person contributed three walks. Each person counted equally in the results. We used 432 sets of readings to check force. Of these, 427 also supported the check for new loading. A new load occurred in 18 of those forecast windows, covering eight distinct loading events. These are the same validation walks used in the earlier comparison. The reserved final test remains unopened. [Recorded data](https://doi.org/10.6084/m9.figshare.24192480.v1)

The simple reference assumes that force stays at the last measured value for the next tenth of a second. It estimates the chance of new loading using the people in the fitting group. The force error below measures the average absolute miss in accumulated force, in newton-seconds. The new-load score squares the difference between the forecast probability and what happened. For both columns, lower is better.

| Method | Error in accumulated force | New-load probability error |
| --- | ---: | ---: |
| Simple reference | 3.237 N·s | 0.039950 |
| One pass | 3.557 N·s | 0.039181 |
| Three passes | **2.895 N·s** | 0.038625 |
| Five passes | 3.118 N·s | **0.038593** |
| Seven passes | 3.097 N·s | 0.038762 |
| Nine passes | 3.099 N·s | 0.038907 |

Three led the force comparison. Five passes improved the probability score over three by about 0.000032. This is a small difference on three people. The preview uses three passes as its starting example. The results apply to this set of validation recordings. [All aggregate scores](results.json)

## Reusing early calculations

The first part of a nine-pass run does the same work as the start of a shorter run. For this comparison we saved the internal state at each requested pass and finished each forecast from that point. At three chosen forecast times, this gave exactly the same predictions as running each of the five pass counts separately. The median time for all five predictions at those times fell from 5.22 seconds to 2.10 seconds with four CPU threads. Across the 215 pairs after the first, the shared run took a median of 2.14 seconds per pair. Both timings start with the weights already loaded. All 432 three- and five-pass predictions also matched the earlier saved results exactly.

The experiment uses the existing Expanded Walking checkpoint. The release includes an invented example and explains how to obtain the separate base model. [Setup and checkpoint](../SIMPLE.md) · [Technical edition](TECHNICAL.md)
