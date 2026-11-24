# Hand-movement forecast on a third recording day

[Simple report](SIMPLE.md) · [Full measurements and intervals](results.json) · [Original package](../README.md)

The published blend had the lowest overall endpoint error on the September 10, 2010 recording. It averaged 3.225 mm, compared with 3.355 mm for the reach-weighted blend, 4.632 mm for the unblended models and 6.111 mm for staying put. The published coefficient file remains the package default.

## Forecast and calibration

The fixed models read 200 ms of past threshold crossings from the same ordered 96 primary motor cortex electrodes in ten 20 ms bins. They forecast the planar change in hand position and a separate straight-line distance over the next 100 ms. The three original FP32 weight sets are from commit `45be8c3554ea3d0f1270a30f7a0c2cbcde895211`. The two blends multiply each forecast by a value from zero to one. The six features, sigmoid rule and standardization are the same as in the [original technical guide](../TECHNICAL.md).

Fit the alternative using the same 52,468 windows from September 20 and the final quarter of September 22. Allocate half the objective to the original trial weighting and half to windows with at least 20 mm of measured displacement. Each half weights the two days equally, then the contributing trials equally and the included windows within a trial equally. Use FP64 full-batch L-BFGS, up to 100 iterations with four starts, the original 0.01 mm smoothing term and the original penalty of 0.05 mm per squared slope. Freeze all September 10 forecasts before reading the held hand coordinates. [DANDI 000070](https://dandiarchive.org/dandiset/000070)

## Measured comparison

Endpoint error is the distance from the predicted ending position to the measured one. Distance error compares the separate straight-line distance prediction with measured displacement magnitude. Both are in millimetres. Rows are divided by measured displacement after scoring. The means weight trials equally within each row and average the errors across the three seeds.

| Measured movement | Windows | Trials | Stay put | Original | Published blend | Reach-weighted blend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All | 45,324 | 2,911 | 6.111 / 6.111 | 4.632 / 3.538 | 3.225 / 2.113 | 3.355 / 2.082 |
| Under 2 mm | 33,954 | 2,911 | 0.309 / 0.309 | 2.159 / 2.439 | 0.441 / 0.387 | 0.674 / 0.575 |
| 2 to under 10 mm | 5,694 | 2,622 | 3.694 / 3.694 | 5.937 / 4.991 | 3.858 / 3.165 | 4.171 / 3.045 |
| 10 to under 20 mm | 1,082 | 1,003 | 14.591 / 14.591 | 12.798 / 8.442 | 11.228 / 8.133 | 10.945 / 7.061 |
| At least 20 mm | 4,594 | 2,911 | 51.733 / 51.733 | 19.406 / 8.581 | 21.270 / 12.182 | 20.571 / 11.010 |

Each pair gives endpoint error followed by distance error. Against the published blend, reach weighting increased overall endpoint error by 0.130 mm, with a paired 95% interval of 0.120 to 0.140 mm. It lowered overall distance error by 0.030 mm, with a paired interval of 0.017 to 0.044 mm. Endpoint error rose by 0.233 mm for movement under 2 mm and fell by 0.699 mm for movement of at least 20 mm. For movements of at least 20 mm, the original unblended models had the lowest errors on both measures.

The intervals resample the same trials 4,000 times and describe this held day. The animal is the same as in calibration. Transfer to new animals, different electrode layouts and live control remains unverified.

## Compare the rules on the same input

Download and extract the [original package](../Cortical-Movement-Blend.zip) in two folders. Follow its [Simple guide](../SIMPLE.md) to install the dependencies. Keep the first copy as downloaded. Save the [experimental coefficients](REACH-WEIGHTED.json) as `BLEND.json` in the second folder. Open the launcher for your system in each folder to compare the included generated example. For your own prepared electrode counts, pass the same `--input window.json` to both copies using the command in the original guide. The two copies use the same three model files.
