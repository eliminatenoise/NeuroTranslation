# Stand and sit force forecast — Technical edition

The offline preview uses the last 200 ms of upward force from two floor plates to forecast each plate’s impulse over the next 100 ms. Impulse is force integrated over time, in newton-seconds (N·s). The browser shows three methods, including a compact NeuroTranslate 0.0 attention model. The separate Research Edition appears in the recorded comparisons below.

## Run the released predictor

1. Extract the ZIP and keep its files together. Open `Open on Linux.sh`, `Open on macOS.command` or `Open on Windows.cmd` on the matching operating system. You can also open `index.html` directly in a desktop browser. The browser runs offline.
2. Choose **Steady load**, **Rising load** or **Falling load**. The presets use invented force histories. The chart plots earlier force at the 20 ms bin midpoints. The forecast table shows each plate’s impulse and their sum.
3. Edit the ten force pairs to try a prepared history. Each box needs a finite number. Choose an example to restore all ten rows. If the scripts fail to load, keep `weights.js` and `predict.js` with `index.html` and reopen it.

For the command line, use Python with NumPy, PyTorch and safetensors installed. From the extracted folder, run the included example.

```sh
python model/predict.py example-rising.json
```

To use your own data, replace the example filename in the command. Use a plain-text JSON file containing a list of ten `[plate 2, plate 3]` pairs. Put the oldest pair first and use calibrated vertical force in newtons (N), with upward positive. Keep the two saved weights files, called checkpoints, with the Python code in `model/`. The output lists `persistence`, `dampedTrend` and `attention` have one impulse per plate in the original column order, in N·s. `loadChangeN` is the signed change in average combined force, in N. `rising` is the correction flag. Add the two numbers in a forecast list to get its combined impulse.

The file `example-rising.json` has a change of 260 N and activates the compact correction. Its latest pair is `[300, 375]` N. Carrying it forward gives 30.00 and 37.50 N·s, a combined 67.50 N·s. With the same file’s ten pairs entered in the browser, the damped trend gives 73.93 N·s combined and its corrected forecast gives 66.37 N·s combined, rounded to two decimals. These are forecasts for the invented input.

## Signal windows and measured target

Define `t = 0` as the forecast time. Average each plate’s preceding force readings into ten consecutive 20 ms bins from −200 ms to 0 ms. Each bin includes its start and excludes its end. The first bin is `[−200, −180)` ms and the last is `[−20, 0)` ms. The outcome is the next interval `[0, 100)` ms. At 1,000 samples per second each bin holds 20 readings and the future interval holds 100.

For a plate sampled at a uniform interval `Δt`, measured impulse is `Σ F[k] × Δt` over the samples in the future interval. At 1,000 samples per second, `Δt = 0.001 s`. The result depends on both the force and the duration. Add the two plate impulses for the combined target. The test measures upward force on the two floor plates. Chair and rail loads require separate measurements.

## Reference forecasts

**Recent force.** Carry the last 20 ms mean `F_last` through the next tenth of a second. The impulse forecast is `F_last × 0.1 s` for each plate.

**Damped trend.** Fit a straight line to the last five means, at −90, −70, −50, −30 and −10 ms. Least squares chooses the line that minimizes the sum of squared differences from the observed values. With times in seconds, centre those times by subtracting their mean. Calling the resulting times `c`, the slope is `b = Σ(c × F) / Σ(c²)`, in N/s. Anchor the forecast at `F_last` at the last bin midpoint `t_last = −0.01 s`. For each future time `t`, the predicted force is `F_last + b × τ × (1 − exp(−(t − t_last) / τ))`, where `τ = 0.05 s`. Sum the 100 forecasts at 1 ms midpoints `t = (k + 0.5) × 0.001 s` for `k = 0` through `99`, multiplying each by `0.001 s`. The slope decays with time while the predicted force approaches a level.

## Compact attention correction

Add the two force channels and compare their average in the last two bins with their average in the first two. Define `Δ = last 40 ms mean − first 40 ms mean`. The compact model corrects the trend only when `Δ > 50 N`. A value below −50 N is falling. A value from −50 to +50 N inclusive is low-change. The compact forecast is exactly the damped trend in both falling and low-change windows. These groups use the past force history and can occur during either chair movement.

Both fits use the same input scaling. Subtract the checkpoints’ two per-plate centres and divide by their two per-plate scales. The centres are approximately `[297.91076, 159.76071]` N and the scales are `[230.35035, 131.79498]` N. A linear layer forms each of 32 values by multiplying the two scaled inputs by learned weights, summing those products and adding a learned offset. Sine and cosine values mark each bin’s position in time. The last bin helps set the weight given to each bin and to an extra learned list of values. This extra list is called the null vector. The attention calculation makes nonnegative weights that sum to one, then combines transformed values from the lists in a weighted sum. Four such calculations run in parallel, each with eight values.

The block adds the attention result to its input. It next subtracts the mean of the resulting values, divides by the square root of their variance plus a small positive constant, and applies a learned multiplier and offset to each value. This is layer normalization. The block sends that result through a layer 64 values wide. ReLU sets negative intermediate values to zero. The block converts back to 32 values, adds the input of that step back in, and repeats the normalization. Its output layer gives two numbers, one per plate. Each full saved checkpoint has 11,618 parameters including the optional branch for six tracked markers. The marker inputs are all marked missing in this release, so that branch adds zero. The browser evaluates the force-only calculation using the same two saved fits.

The correction estimates the measured impulse minus the damped-trend forecast. The two fits started from seeds 2731 and 4119. A seed sets the starting random choices in a training run. Average the two dimensionless outputs per plate, multiply by 25 N·s, and add to the trend. The saved weights use 32-bit floating point (FP32). The browser and Python use the same model and input rules, with different arithmetic implementations.

## Separate Research Edition correction

A transformer uses attention to combine input values with different weights. The Notre Dame comparison used the fixed transformer from the full FP32 Research Edition. Three passes convert the same earlier force bins into a 2,304-value representation. The transformer stayed fixed. Two linear readouts, or fits from that representation to the two impulse residuals, used four earlier Utah development participants. Here the residual means the measured impulse minus the damped trend for the same plate.

The readouts use ridge regression, which fits linear weights with a penalty of 0.25. Within each fit, each person contributes equal total weight. The input features are centred by their weighted mean and divided by their weighted population standard deviation. A scale at or below `1e-12` is replaced with 1 before division. The scaled features are divided by `√2304 = 48`. A fitted intercept, a constant added to the linear prediction, is exempt from the penalty.

- **Changing-load correction.** Fit on 647 Utah development windows with `|Δ| > 50 N`. Apply the correction only on windows passing that rule, including both rising and falling load. Return the damped trend at either exact boundary and throughout the low-change range.
- **Correction at every forecast.** Fit on all 2,822 admitted Utah development windows. Add the result at every forecast, including low-change windows.

The offline ZIP runs the compact predictor. The Research Edition scores describe a separate comparison with its two fixed readouts.

## Error and comparison rules

Compute `|predicted combined impulse − measured combined impulse|` for each case. The combined impulse is the sum across plates before taking the absolute error. Average the errors within each person, then average the person means equally. This is the equal-person mean absolute error (MAE) in N·s. Compute it separately within each reported subset. All methods use the same eligible cases within a comparison. Lower error is better.

### Utah reserved test

Four people supplied the fitting data. Three other people were assigned to the test. A fixed force-calibration check used only the first 30 s of each test recording on the shared clock. Two people qualified. One had too few loaded samples on one plate during that check. Forecasts were 300 ms apart after the prefix, leaving disjoint history and outcome samples across cases. Forecasts were saved and verified before opening the later outcomes for scoring.

| Forecast | All 230 cases (N·s) | 24 rising-load cases (N·s) |
| --- | ---: | ---: |
| Recent force | 2.86 | 7.59 |
| Damped trend | 2.69 | 6.82 |
| Damped trend plus attention correction | 2.36 | 3.65 |

The compact correction reduced overall mean error for both scored people. It gives exactly the same impulses as the trend in the 206 non-rising cases. These scores cover the two qualifying people from this archive.

### Leeds archived chair trials

The fixed compact model scored 6,739 windows from 402 chair trials of 134 people, including 892 rising windows. On the stored force clock, forecasts were 300 ms apart and used their own 200 ms history and 100 ms outcome. The documentation did not establish a match between the Leeds plate numbering and Utah input columns. Both orders were fixed in advance. Each forecast was returned to Leeds plate order for scoring. The replay reports both orders separately.

| Forecast | All 6,739 windows (N·s) | 892 rising-load windows (N·s) |
| --- | ---: | ---: |
| Recent force | 2.837 | 6.835 |
| Damped trend | 2.099 | 4.567 |
| Damped trend plus correction, plate 1 then 2 | 2.105 | 4.749 |
| Damped trend plus correction, plate 2 then 1 | 2.117 | 4.853 |

Damped trend gave lower mean error than either corrected order overall and during rising load. In each order, the correction lowered overall error for 60 people and raised it for 74 relative to the trend. It lowered error for 53 people in both orders. For 14 people, it lowered error in one order and raised it in the other. The replay used low-pass filtered force exports, in which fast changes had been reduced. The direction of the filter in time and availability of original readings at the time of a live forecast remain unverified. [Acquisition and export methods](https://www.nature.com/articles/s41597-026-06925-w) · [University of Leeds dataset](https://doi.org/10.5518/1701)

### Notre Dame archived chair rises and descents

The replay used all 54 available short recordings from nine people, three rises and three descents each. A separate person supplied the engineering check. Each foot was on its own Kistler force plate. The replay took calibrated, signed upward force in N from 1,000 samples per second on the stored clock. It used the force exported before the study’s later software filter, with cameras and chair plates excluded. Part of the chair sat outside the instrumented area.

Forecasts were 300 ms apart while enough samples remained for 200 earlier and 100 later samples. The same 146 windows were scored for every method, including 70 during chair rises and 76 during descents. From the earlier load change, 23 were rising, 38 falling and 85 low-change. These force groups describe the earlier 200 ms, separately from the direction of the chair movement.

The compact correction and both Research Edition readouts ran in two preselected input orders, left foot first and right foot first. Each forecast was returned to recorded foot order. For the primary comparison, average the two forecasts per foot before making the combined impulse and scoring it. The second table retains the individual orders. Both models’ forecasts were saved and reproduced using earlier samples before the later outcomes were decoded.

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) | 85 low-change windows (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Recent force | 2.130 | 1.521 | 2.770 | 2.115 |
| Damped trend | 1.731 | 1.282 | 2.260 | 1.761 |
| Compact correction, average of both orders | 1.805 | 1.610 | 2.260 | 1.761 |
| Research Edition, correction during changing loads | 1.679 | 1.501 | 1.938 | 1.761 |
| Research Edition, correction at every forecast | 1.709 | 1.262 | 2.193 | 1.745 |

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) | 85 low-change windows (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Compact correction, left first | 1.796 | 1.551 | 2.260 | 1.761 |
| Compact correction, right first | 1.816 | 1.681 | 2.260 | 1.761 |
| Research Edition during changing loads, left first | 1.703 | 1.337 | 2.169 | 1.761 |
| Research Edition during changing loads, right first | 1.694 | 1.711 | 1.864 | 1.761 |
| Research Edition at every forecast, left first | 1.700 | 1.232 | 2.219 | 1.735 |
| Research Edition at every forecast, right first | 1.724 | 1.314 | 2.171 | 1.760 |

The Research Edition correction during changing loads had the lowest overall mean error. It reduced error by 0.052 N·s against damped trend, with lower overall error in five of nine people and lower falling-load error in eight. Its mean rising-load error was higher than trend. The compact correction raised mean overall error in either plate order.

Resampling pairs of scores from the same people 20,000 times gave a 95% interval from 0.006 to 0.106 N·s of improvement for the Research Edition changing-load correction. For chair rises and descents, the method scored 1.496 and 1.858 N·s, respectively, and the trend scored 1.584 and 1.878 N·s. The interval reflects variation across the nine people in this archive. Phase and order breakdowns reuse the same recordings. Device-level timing, unloaded calibration and live availability remain unverified on the short clips. [Recording methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12717423/) · [Dataset version 1](https://doi.org/10.7274/28689221.v1)

## Data sources and reuse

- **Utah stand-up and sit-down recordings.** Grace Hunt, K. Bo Foreman, Tommaso Lenzi, Lukas Gabert and Colby Hansen (2024). The comparison uses averaged upward force on two floor plates and reports aggregate errors. [Figshare dataset, version 2](https://doi.org/10.6084/m9.figshare.26282872.v2)
- **Leeds chair trials.** Dataset by David Lunn, Enrico de Pieri, Graham Chapman, Stephen Ferguson and Anthony Redmond (2025). David E. Lunn, Enrico De Pieri, Graham J. Chapman, Morten E. Lund, Stephen J. Ferguson and Anthony C. Redmond describe acquisition and processing (2026). The replay averages the released vertical force and reports aggregate errors. [University of Leeds dataset](https://doi.org/10.5518/1701) · [Scientific Data methods article](https://www.nature.com/articles/s41597-026-06925-w)
- **Notre Dame chair recordings.** Mohsen Alizadeh Noghani, Sebastian Green and Edgar Bolivar Nieto. The replay uses calibrated force exports, averages the earlier readings for each foot, and reports aggregate errors. [Dataset version 1](https://doi.org/10.7274/28689221.v1) · [Recording and processing methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12717423/)

The original data releases use Creative Commons Attribution 4.0 International. The project’s code, fitted weights and documentation are dedicated to the public domain under CC0 1.0. The preview examples use invented readings. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)
