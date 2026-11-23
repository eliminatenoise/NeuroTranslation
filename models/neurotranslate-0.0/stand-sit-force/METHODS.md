# Forecast methods and recorded evaluation

## Input and measured outcome

A forecast takes 200 ms of upward force from two floor plates. Average each plate’s readings in ten consecutive 20 ms bins. Keep the bins in order from oldest to newest. Use plate 2 in the first column and plate 3 in the second. Force is in newtons, with upward counted as positive.

The outcome is force impulse over the next 100 ms. It is the sum of each later force reading multiplied by the time it covers, in newton-seconds (N·s). Each plate has its own forecast. The combined forecast adds the two plate forecasts.

## Three forecast rules

- **Recent force.** Carry each plate’s mean force from its last 20 ms bin forward for 100 ms.
- **Damped trend.** Fit a straight-line slope to the last five bins for each plate. Anchor the forecast at the last bin’s mean and midpoint. Let the slope decay with a 50 ms time constant. Add up the predicted force at 1 ms midpoints over the next 100 ms.
- **Damped trend with a learned correction.** Two fitted attention models use the same earlier force readings. Each estimates a correction to the trend’s impulse for each plate. The forecast adds their average only if the total force across the two plates averaged over the last 40 ms exceeds its first 40 ms average by more than 50 N. All other inputs return the damped-trend forecast exactly. The two saved fits use 32-bit floating-point weights (FP32).

## Fitting and test recordings

Four people supplied the Utah fitting recordings. The predictor and comparison rules were fixed before the reserved readings were opened. A separate test assigned three people. Each recording had to pass a fixed force-calibration check using only the first 30 seconds on the shared recording clock. One person’s prefix had too few loaded samples on one plate. The two qualifying recordings supplied the scored forecasts.

The test used 300 ms steps after the calibration prefix. Each qualifying case used a 200 ms input history and the next 100 ms for the outcome. Input and outcome samples were disjoint across cases. The forecasts were saved and verified before their later outcomes were opened for scoring.

## Error on the same cases

For each case, take the absolute difference between the predicted and measured **sum of the two plates’ impulses**. Average within each person first, then average the two people’s scores.

| Forecast | All 230 cases (N·s) | 24 rising-load cases (N·s) |
| --- | ---: | ---: |
| Recent force | 2.86 | 7.59 |
| Damped trend | 2.69 | 6.82 |
| Damped trend plus attention correction | 2.36 | 3.65 |

The corrected forecast lowered combined impulse error relative to the damped trend for both people. The two methods produce the same estimates outside the rising-load group. The evaluation measures upward floor-plate impulse in two eligible recordings from one archive. Chair and rail loads require separate measurements. The offline browser uses invented histories. The original fitted weights and Python predictor are in the `model/` folder.

## Leeds archival replay

The replay applied the saved Utah forecaster to the calibrated force exports from 402 Leeds chair trials across 134 people. Each forecast used ten 20 ms averages per plate from the 200 ms before its forecast time. The next 100 ms of measured force gave the outcome. On the stored force clock, forecast times were 300 ms apart. Each case used its own history and outcome samples.

The Utah model expects two plates in a fixed column order. The documentation leaves the correspondence between numbered Leeds plates and Utah input columns unresolved. The replay therefore tested plate 1 then 2 and the reverse order, using both mappings fixed in advance. It returned predictions to the original Leeds plate numbers to score impulse against the measurements. Both mappings appear in the results, and neither was selected. The model weights stayed fixed.

The common set had 6,739 scored windows. Of these, 892 passed the same rising-load check used in Utah. Each case gives an absolute error for the sum of the two plates’ upward impulse. Errors are averaged within each person first, then people count equally within each column.

| Forecast | All 6,739 windows (N·s) | 892 rising-load windows (N·s) |
| --- | ---: | ---: |
| Recent force | 2.837 | 6.835 |
| Damped trend | 2.099 | 4.567 |
| Damped trend plus correction, plate 1 then 2 | 2.105 | 4.749 |
| Damped trend plus correction, plate 2 then 1 | 2.117 | 4.853 |

Compared with the damped trend, the correction gave 60 people a lower overall error and 74 people a higher overall error in each plate order. For 53 people the correction lowered error under both orders. Another 14 had lower error in one order and higher error in the other. The damped trend had lower mean error than the correction overall and in the rising-load group for both orders.

The archive authors low-pass filtered the exported force signals. The replay follows the stored time order. The filter’s time direction and the availability of original force samples at forecast time on live equipment remain unverified. These scores describe the Leeds archive. The Utah results above cover the separate Utah test. [Leeds acquisition and export methods](https://www.nature.com/articles/s41597-026-06925-w) · [University of Leeds dataset](https://doi.org/10.5518/1701)

[Recording source and licence](DATASET-CREDITS.md)
