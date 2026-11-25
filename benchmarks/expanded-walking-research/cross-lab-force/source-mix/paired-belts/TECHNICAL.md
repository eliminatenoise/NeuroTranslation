# Matched-size two-belt impulse forecasts

The Research Edition's changing-force readout reached **7.862 N·s** mean per-belt error with 150 fitting windows from two labs, compared with **8.262** from one lab and **7.957** with 222 windows from both labs. These are held-participant results for the left/right allocation. All three fits kept the full model's combined impulse estimate. [Simple edition](README.md) · [Exact scores](RESULTS.json) · [Download the viewer and readouts](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/expanded-walking-research/cross-lab-force/source-mix/paired-belts/Two-Belt-Force.zip)

## Measurement and forecast

On the stored 1 kHz force grid, let `t` count samples from the first recorded sample. Use ten 20-sample means from `[t−200,t)` in physical left/right belt order. The target `sum(Fz[t:t+100]) / 1000` is the signed belt-normal impulse in N·s for each belt. Read the original QTM plate-local channel. The file-format check uses Jin participant 01, fitting uses 02–06, and the held test uses 07–15. Each test participant supplies 30 equally spaced issue times from 30 to 320 s in the tied-belt trial with the feedback display off. We saved the forecasts and the positions of all 27,000 participant/time rows before reading the 54,000 belt-force values used for scoring. [Test data](https://doi.org/10.5281/zenodo.16970717) · [Recording methods](https://doi.org/10.1038/s41598-026-46937-5)

Persistence scales the most recent 20 ms mean by 0.1 s. The trend uses the slope of the five latest means and a 50 ms exponential decay. The physical combination uses the trend sum and persistence difference. The frozen 24-layer Research Edition runs three passes through its recurring middle layers in FP32. Its changing-force readout applies a correction when the absolute total-force change between the means of the first two and last two bins exceeds 50 N. This selects 230 windows. The other readout corrects every window. Evaluate both orders and restore left/right identity before averaging. The evaluated checkpoint and fixed force head are identified in `READOUTS.json`.

## Fitting and comparison

Let `s₀` be the trend sum, `d₀` the persistence difference, and `s₁,d₁` the sum and difference from the frozen Research Edition. Set `s = s₀ + wₛ(s₁ − s₀)` and `d = d₀ + w_d(d₁ − d₀)`, then recover the belts as `(s + d)/2` and `(s − d)/2`. Fit `wₛ` first by absolute error on combined impulse. With `wₛ` fixed, fit `w_d` by absolute error on the individual belts. Give each fitting participant equal mass across their windows. Take the weighted median of the zero-error points clipped to [0, 1]. Each point is weighted by its window's share of that mass times the absolute forecast change from the full correction.

Keep all 150 Jin windows for the one-lab fit. For the equal-size mix, keep 16, 16, 16, 15 and 15 evenly spaced windows from the five people, including the first and last at integer-rounded-down positions, and add the 72 earlier windows from two people. The larger fit uses all 222. Both fitted mixing conditions use the same decoder outputs. The earlier archive measures laboratory vertical force at 1.2 kHz. The Jin archive measures belt-normal force at 1 kHz. The equal-size comparison holds the window count fixed while varying subjects, equipment, force axes and walking conditions together. [Earlier fitting data](https://doi.org/10.6084/m9.figshare.19718500.v1) · [Earlier study methods](https://doi.org/10.1038/s41597-022-01817-1)

## Held-participant results

For errors `eL,eR`, the mean belt loss is `(|eL| + |eR|)/2` and the combined loss is `|eL + eR|`. Average each loss over windows within a participant, then give all nine participant means equal weight.

| Method | Left (N·s) | Right (N·s) | Mean belt (N·s) | Combined (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Persistence | 8.231 | 8.729 | 8.480 | 7.017 |
| Damped trend | 8.137 | 8.535 | 8.336 | 6.988 |
| Physical sum and difference | 8.292 | 8.845 | 8.569 | 6.988 |
| Frozen changing-force readout | 8.092 | 8.432 | 8.262 | 6.763 |
| Frozen all-window readout | 8.074 | 8.472 | 8.273 | 6.958 |
| One lab, changing force | 8.092 | 8.432 | 8.262 | 6.763 |
| One lab, all windows | 8.074 | 8.472 | 8.273 | 6.958 |
| Two labs, same size, changing force | **7.635** | **8.090** | **7.862** | 6.763 |
| Two labs, same size, all windows | 7.652 | 8.131 | 7.892 | 6.958 |
| Two labs, all data, changing force | 7.742 | 8.172 | 7.957 | 6.763 |
| Two labs, all data, all windows | 7.753 | 8.213 | 7.983 | 6.958 |

Paired 95% intervals use 20,000 participant resamples. Relative to one lab, the equal-size mix changes mean belt error by **−0.400 N·s** [−0.553, −0.235] for changing force and **−0.381** [−0.563, −0.189] for all windows. Each change favours eight of nine participants. Left and right improve for nine and eight respectively in the changing-force comparison. Relative to the equal-size mix, the larger fit changes mean belt error by **+0.095** [0.038, 0.143] and **+0.091** [0.020, 0.154]. All total weights are one. The changing-force decoder reduces combined error relative to the trend for nine of nine participants. The results describe the nine held people on this recorded force-only protocol.

## Replay and fit

The extracted **Compare Results.html** displays recorded scores without a server. Python 3 and the matching launcher run `apply_readouts.py` with the two generated cases in `EXAMPLE.json`. Pass a JSON file as an argument to apply `READOUTS.json` to your own persistence, trend and two frozen decoder estimates, all in N·s and left/right order. For re-fitting, call `fit_readouts.fit_blend(hold, trend, decoder, measured, participant)` with NumPy and provide matched `N × 2` arrays and `N` participant labels. The Linux launcher and Chromium menus were run. The macOS and Windows launchers were reviewed as source.

The released code and fitting coefficients use CC0. Jin et al. distribute original recordings under CC BY 4.0. Van der Zee and Kuo distribute the additional fitting data under CC0. [Test source](https://doi.org/10.5281/zenodo.16970717) · [Additional fitting source](https://doi.org/10.6084/m9.figshare.19718500.v1)
