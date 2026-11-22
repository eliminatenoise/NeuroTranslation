# Forecast methods and recorded evaluation

## Input and measured outcome

A forecast takes 200 ms of upward force from two floor plates. Average each plate’s readings in ten consecutive 20 ms bins. Keep the bins in order from oldest to newest. Use plate 2 in the first column and plate 3 in the second. Force is in newtons, with upward counted as positive.

The outcome is force impulse over the next 100 ms. It is the sum of each later force reading multiplied by the time it covers, in newton-seconds (N·s). Each plate has its own forecast. The combined forecast adds the two plate forecasts.

## Three forecast rules

- **Recent force.** Carry each plate’s mean force from its last 20 ms bin forward for 100 ms.
- **Damped trend.** Fit a straight-line slope to the last five bins for each plate. Anchor the forecast at the last bin’s mean and midpoint. Let the slope decay with a 50 ms time constant. Add up the predicted force at 1 ms midpoints over the next 100 ms.
- **Damped trend with a learned correction.** Two fitted attention models use the same earlier force readings. Each estimates a correction to the trend’s impulse for each plate. The forecast adds their average only if the total force across the two plates averaged over the last 40 ms exceeds its first 40 ms average by more than 50 N. All other inputs return the damped-trend forecast exactly. The two saved fits use 32-bit floating-point weights (FP32).

## Fitting and test recordings

Four people supplied the fitting recordings. The predictor and comparison rules were fixed before the reserved readings were opened. A separate test assigned three people. Each recording had to pass a fixed force-calibration check using only the first 30 seconds on the shared recording clock. One person’s prefix had too few loaded samples on one plate. The two qualifying recordings supplied the scored forecasts.

The test used 300 ms steps after the calibration prefix. Each qualifying case used a 200 ms input history and the next 100 ms for the outcome. Input and outcome samples were disjoint across cases. The forecasts were saved and verified before their later outcomes were opened for scoring.

## Error on the same cases

For each case, take the absolute difference between the predicted and measured **sum of the two plates’ impulses**. Average within each person first, then average the two people’s scores.

| Forecast | All 230 cases (N·s) | 24 rising-load cases (N·s) |
| --- | ---: | ---: |
| Recent force | 2.86 | 7.59 |
| Damped trend | 2.69 | 6.82 |
| Damped trend plus attention correction | 2.36 | 3.65 |

The corrected forecast lowered combined impulse error relative to the damped trend for both people. The two methods produce the same estimates outside the rising-load group. The evaluation measures upward floor-plate impulse in two eligible recordings from one archive. Chair and rail loads require separate measurements. The offline browser uses invented histories. The original fitted weights and Python predictor are in the `model/` folder.

[Recording source and licence](DATASET-CREDITS.md)
