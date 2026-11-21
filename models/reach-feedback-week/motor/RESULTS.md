# Did the electrodes improve next week's movement forecast?

The hand was harder to predict when the model received cortical counts. Across the ten forecast times, adding counts raised the mean hand error by 0.47 mm in the first workspace and 0.88 mm in the second. For the elbow, adding counts raised the error in the first workspace and lowered it in the second. In both workspaces, the nonlinear model's interval for its own counts versus another trial's counts included zero for every measured body region. The prespecified hand-and-elbow transfer criterion failed.

The measurements came from the same macaque's September 7 and September 14 reaching sessions. The model learned only from September 7. The cameras and handle encoder supplied the movement against which its later forecasts were checked. The electrodes recorded cortex during movement. Both sensory-related and motor-related activity could contribute. [Data](https://doi.org/10.5061/dryad.nk98sf7q7) · [Source study](https://doi.org/10.7554/eLife.48198)

## How much did the forecast change?

Each difference subtracts the named control's trajectory error from the three-seed ensemble's error averaged across the ten forecast times. A negative difference favours actual counts. The brackets contain the 95% paired moving-block interval. The individual-seed range gives the smallest and largest paired differences when each of the three component models is used alone. Euclidean distance is nonlinear, so the ensemble can fall outside that range.

| Workspace | Region and units | Actual minus pose and cues | Individual-seed range | Actual minus earlier trial's counts | Individual-seed range |
|---|---|---:|---:|---:|---:|
| 1 | hand mm | +0.468 [+0.298, +0.645] | +0.519 to +1.073 | -0.101 [-0.253, +0.058] | -0.219 to +0.019 |
| 1 | elbow mm | +0.371 [+0.229, +0.507] | +0.396 to +0.514 | +0.018 [-0.049, +0.101] | -0.030 to +0.008 |
| 1 | handle cm | +0.028 [+0.011, +0.040] | +0.020 to +0.059 | -0.004 [-0.013, +0.005] | -0.017 to +0.004 |
| 2 | hand mm | +0.882 [+0.718, +1.037] | +0.138 to +1.622 | +0.002 [-0.114, +0.131] | -0.116 to +0.128 |
| 2 | elbow mm | -0.189 [-0.280, -0.097] | -0.170 to +0.071 | -0.028 [-0.094, +0.027] | -0.122 to +0.031 |
| 2 | handle cm | -0.053 [-0.065, -0.037] | -0.051 to +0.013 | +0.005 [-0.002, +0.011] | -0.001 to +0.006 |

## What did the simpler forecasts do?

Each cell gives mean trajectory error / error at 100 ms. All methods use the same trials here. The stationary forecast holds the last position. The velocity forecast continues the slope between the first and last of the five most recent recorded positions.

| Workspace | Forecast | Hand (mm) | Elbow (mm) | Handle (cm) |
|---|---|---:|---:|---:|
| 1 | Actual counts | 3.859 / 7.327 | 2.578 / 4.092 | 0.329 / 0.617 |
| 1 | Pose and cues | 3.391 / 6.549 | 2.207 / 3.702 | 0.302 / 0.583 |
| 1 | Earlier trial’s counts | 3.960 / 7.526 | 2.559 / 4.092 | 0.333 / 0.635 |
| 1 | Frozen pose/cue Transformer | 3.640 / 6.668 | 2.387 / 3.814 | 0.336 / 0.633 |
| 1 | Linear correction with counts | 3.849 / 7.704 | 2.520 / 4.076 | 0.325 / 0.628 |
| 1 | Linear pose/cue correction | 3.466 / 6.880 | 2.243 / 3.757 | 0.298 / 0.577 |
| 1 | Linear correction with earlier counts | 3.972 / 7.850 | 2.511 / 4.095 | 0.333 / 0.636 |
| 1 | Constant velocity | 2.670 / 5.355 | 3.500 / 6.815 | 0.554 / 1.266 |
| 1 | Stationary | 3.689 / 6.166 | 4.017 / 6.183 | 0.839 / 1.304 |
| 2 | Actual counts | 4.383 / 8.015 | 3.108 / 5.272 | 0.319 / 0.526 |
| 2 | Pose and cues | 3.501 / 6.532 | 3.297 / 5.655 | 0.372 / 0.605 |
| 2 | Earlier trial’s counts | 4.381 / 8.038 | 3.136 / 5.302 | 0.315 / 0.516 |
| 2 | Frozen pose/cue Transformer | 4.032 / 7.460 | 3.082 / 5.197 | 0.313 / 0.496 |
| 2 | Linear correction with counts | 4.294 / 8.070 | 3.044 / 5.212 | 0.320 / 0.517 |
| 2 | Linear pose/cue correction | 4.081 / 8.197 | 3.056 / 5.502 | 0.314 / 0.487 |
| 2 | Linear correction with earlier counts | 4.277 / 8.030 | 3.019 / 5.161 | 0.320 / 0.519 |
| 2 | Constant velocity | 4.751 / 9.441 | 3.376 / 6.690 | 0.341 / 0.765 |
| 2 | Stationary | 5.281 / 8.402 | 3.597 / 5.728 | 0.644 / 1.051 |

The linear correction's hand forecasts in workspace 1 benefited from using the current trial's counts in place of an earlier trial's counts. Its 95% block interval for that difference was −0.238 to −0.016 mm. This comparison concerns the linear correction and one of the two workspaces.

## Which reaches counted?

Training used 519 windows from 198 trials. On September 14, 201 windows from 111 trials in workspace 1 and 292 from 163 trials in workspace 2 had complete position, target and spike histories. The earlier-trial comparison retained 197 windows from 109 trials in workspace 1 and 288 windows from 161 in workspace 2. The first eligible trial at each cue ordinal in each block and workspace had no earlier donor. Only the second and third go cues qualified as forecast starts on this test day. All eight dropped windows are identifiable in the raw forecast output.

Average each trial's eligible windows before averaging trials. For uncertainty, draw groups of eight consecutive trials within each physical recording block and workspace, retaining every assigned trial's slot even when it carries no eligible window. The roster contains 241 and 268 trials in the two workspaces, plus three whose workspace was unknown. Both physical blocks begin their trial numbering at one. These intervals describe trial variation within this one animal and test day.

An earlier diagnostic used only September 7. New copies of the base models and corrections were trained on the first 320 windows from 120 trials, then tested on the final 199 windows from 78 different trials. On the 196 windows with an earlier donor, the count model beat the wrong-count control for hand and elbow. The pose-and-cue correction was more accurate for both. These earlier checks chose no settings for the September 14 forecast.

Every individual 10–100 ms horizon, both interval methods, natural and matched support, and all three seeds' errors are in [scores.json](scores.json). Individual-seed paired differences are in [seed-contrasts.json](seed-contrasts.json). [Replay and refit instructions](README.md)
