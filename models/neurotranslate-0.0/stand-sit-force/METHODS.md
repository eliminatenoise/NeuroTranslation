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

## Notre Dame replay method and results

Both feet rested on separate Kistler force plates during the chair recordings. The model histories and outcomes use signed upward force in newtons from the calibrated 1 kHz exports. The paper describes later force filtering in the analysis software. The replay uses the force before that step and reads the stored sample clock. It leaves out the cameras and the chair plates. Part of the chair rested outside the instrumented area.

We used three chair rises and three descents from each of nine people. A separate participant supplied the engineering check. The study began with every available record for those nine people. The replay issued a forecast every 300 milliseconds while enough samples remained, using the 200 prior samples and the 100 immediately following samples for separate input and outcome windows. The same 146 windows were scored for every method, including 70 during chair rises and 76 during descents. Rising and falling load refer to force changes in the earlier 200 milliseconds. Both phases can occur in either chair movement.

The two orderings of the compact correction and both Research Edition corrections were fixed before scoring. The Research Edition used the fixed transformer from the full FP32 comparison and two linear corrections fitted on four Utah development participants. One used only earlier windows whose total load changed by more than 50 N in either direction. It used the damped trend on steady-load windows. The other learned from all earlier development windows and applied its correction to every forecast. Forecasts were returned to recorded foot order before averaging the two estimates. Both models’ forecasts were stored and reproduced from earlier samples before any of the outcomes were decoded.

The error is the absolute difference between the predicted and measured sum of the two feet’s upward force impulses. Each person’s windows were averaged first, and each person counts equally in the result. The methods below use the same scoreable observations.

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) | 85 low-change windows (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Recent force | 2.130 | 1.521 | 2.770 | 2.115 |
| Damped trend | 1.731 | 1.282 | 2.260 | 1.761 |
| Compact correction, average of both orders | 1.805 | 1.610 | 2.260 | 1.761 |
| Research Edition, correction during changing loads | 1.679 | 1.501 | 1.938 | 1.761 |
| Research Edition, correction at every forecast | 1.709 | 1.262 | 2.193 | 1.745 |

Single-order forecasts

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) | 85 low-change windows (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Compact correction, left first | 1.796 | 1.551 | 2.260 | 1.761 |
| Compact correction, right first | 1.816 | 1.681 | 2.260 | 1.761 |
| Research Edition during changing loads, left first | 1.703 | 1.337 | 2.169 | 1.761 |
| Research Edition during changing loads, right first | 1.694 | 1.711 | 1.864 | 1.761 |
| Research Edition at every forecast, left first | 1.700 | 1.232 | 2.219 | 1.735 |
| Research Edition at every forecast, right first | 1.724 | 1.314 | 2.171 | 1.760 |

For the Research Edition correction during changing loads, the average prediction from both orders reduced overall error by 0.052 N·s against the damped trend. A 95% interval from 20,000 paired resamples of the nine participants ran from 0.006 to 0.106 N·s of improvement. The same correction had mean errors of 1.496 N·s during chair rises and 1.858 N·s during descents, compared with 1.584 and 1.878 N·s for the trend. The interval reflects variation across the people in this archive. Device-level time and unloaded calibration remain unverified for these short clips. [Recording methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12717423/) · [Dataset version 1](https://doi.org/10.7274/28689221.v1)

[Recording source and licence](DATASET-CREDITS.md)
