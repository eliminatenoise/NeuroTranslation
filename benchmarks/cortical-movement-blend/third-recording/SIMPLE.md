# Hand-movement forecast on a third recording day

[Technical report](TECHNICAL.md) · [Full measurements and intervals](results.json) · [Original package](../README.md)

The published NeuroTranslate blend gave the closest average estimate of where the hand would finish on this recording day. Its average error was 3.225 millimetres. The new blend, which learns with extra weight on bigger movements, averaged 3.355 millimetres. The published blend is still the rule that comes with the download.

## What goes into each forecast

The recording follows one animal reaching with its hand. During each reach, 96 electrodes in the part of the brain involved in moving the arm recorded electrical activity. The program looks back 200 milliseconds from one point in the recording. It counts the events from each electrode in ten blocks of 20 milliseconds, keeping the same electrode order each time.

The original three models each estimate how far and in what direction the hand will move in the next 100 milliseconds. Each also makes a separate estimate of the straight-line distance between start and end. Both blends use the same three models with their original 32-bit numbers. A blend can shorten the predicted change by multiplying it by a number from zero to one. Zero leaves the hand at its last position. One keeps the original forecast in full. Six inputs describe the recent electrode counts and how large and consistent the three original forecasts are. Both blends use that same information and the same way of putting the inputs on a common scale. [Original technical guide](../TECHNICAL.md)

## How the reach-weighted rule learned

The two rules use 52,468 examples from September 20 and the last quarter of September 22. The new rule gives half the weight to all the original examples and half to the examples where the hand moved at least 20 millimetres. Each day has equal weight. Within each part of the fit, each contributing trial also has equal weight. This keeps a long trial from dominating by supplying more measurements.

The fit uses 64-bit numbers. For the reach-weighted rule, the computer starts the calculation four ways, allows up to 100 updates each time and keeps the best fit. Both rules use the same small smoothing value of 0.01 mm and the same penalty for large coefficients, 0.05 mm times the square of each slope. The penalty limits how much a change in any one input can change the adjustment.

The comparison uses a separate recording from September 10, 2010. It has 45,324 forecast times from 2,911 trials. The program saved all forecasts before reading the measured hand positions for this day. Scoring then compared each saved forecast with where the hand actually ended up. All three recording days come from the same animal. [DANDI 000070](https://dandiarchive.org/dandiset/000070)

## What the errors measure

**Endpoint error** measures how far the predicted ending point is from the measured ending point. It counts a mistake in direction even when the forecast is the right length. **Distance error** compares the separate distance forecast with the straight-line distance the hand actually covered. For example, two forecasts can predict the same length while pointing in opposite directions. They can have the same distance error and very different endpoint errors.

Each table cell shows endpoint error first and distance error second, both in millimetres. The trial averages give each trial equal weight. Each forecast uses earlier electrode readings. The movement groups are formed during scoring from the later hand measurements. A trial can contribute to more than one group because the hand can move a little in one part and much farther in another.

| How far the hand really moved | Windows | Trials | Stay put | Original | Published blend | Reach-weighted blend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All movements | 45,324 | 2,911 | 6.111 / 6.111 | 4.632 / 3.538 | 3.225 / 2.113 | 3.355 / 2.082 |
| Under 2 mm | 33,954 | 2,911 | 0.309 / 0.309 | 2.159 / 2.439 | 0.441 / 0.387 | 0.674 / 0.575 |
| 2 to under 10 mm | 5,694 | 2,622 | 3.694 / 3.694 | 5.937 / 4.991 | 3.858 / 3.165 | 4.171 / 3.045 |
| 10 to under 20 mm | 1,082 | 1,003 | 14.591 / 14.591 | 12.798 / 8.442 | 11.228 / 8.133 | 10.945 / 7.061 |
| At least 20 mm | 4,594 | 2,911 | 51.733 / 51.733 | 19.406 / 8.581 | 21.270 / 12.182 | 20.571 / 11.010 |

Giving larger reaches more weight lowered the new blend’s endpoint error by 0.699 mm on movements of at least 20 mm compared with the published blend. The original models still did best in that group. At times when the hand moved less than 2 mm, staying put worked best and the reach-weighted blend lost 0.233 mm against the published blend.

Across the full day, reach weighting raised endpoint error by 0.130 mm and lowered distance error by 0.030 mm. We redrew whole trials 4,000 times and compared the same draws for both rules. The middle 95% of those comparisons put the increase in endpoint error between 0.120 and 0.140 mm and the improvement in distance error between 0.017 and 0.044 mm. These ranges describe variation among trials on this day. A different animal, different electrodes and a live movement system still need their own tests.

## Try both blends

1. Download the [original package](../Cortical-Movement-Blend.zip) and extract it twice, with each copy in its own folder.
2. Follow the [original Simple guide](../SIMPLE.md) to install the dependencies. Keep the first copy as downloaded. In the second folder, replace `BLEND.json` with the [experimental coefficient file](REACH-WEIGHTED.json), using the filename `BLEND.json`.
3. Open the launcher for your system in each folder. Both copies start with the same generated example, so you can compare the two forecasts on exactly the same input. For prepared electrode counts, the original guide explains how to choose a file using `--input window.json`.
