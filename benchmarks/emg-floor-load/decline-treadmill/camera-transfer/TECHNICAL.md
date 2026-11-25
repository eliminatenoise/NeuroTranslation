# External treadmill evaluation of the pelvis-motion forecast

[Download the model, offline viewer and example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/decline-treadmill/camera-transfer/Pelvis-Motion-Forecast.zip) · [Simple edition](README.md) · [Exact scores](RESULTS.json)

The frozen 5° downhill Georgia Tech model transferred to the Lee and Lee uphill recordings. Mean absolute error for combined belt-normal impulse fell from **9.170 to 5.116 N·s** relative to static projected body weight, a **44.2%** reduction. All 11 walkers improved at both grades. The cohort contained 22 recordings and 3,014 matched issues. [Georgia Tech recordings](https://doi.org/10.35090/gatech/70296) · [Lee and Lee recordings](https://doi.org/10.5281/zenodo.19632046)

| Method | Both grades | Near 5% grade | Near 10% grade |
| --- | ---: | ---: | ---: |
| Current camera history | 5.116 | 4.900 | 5.332 |
| Static projected body weight | 9.170 | 8.566 | 9.774 |
| Camera history shifted back 1 s | 15.964 | 14.753 | 17.175 |
| Pelvis-normal acceleration estimate | 12.608 | 12.309 | 12.907 |

Errors are in N·s. Paired camera-minus-static error was −4.054 N·s, with a 95% participant bootstrap interval of [−5.178, −3.038]. Camera minus shifted history was −10.848 N·s, with interval [−13.380, −8.226]. Each grade contributes 1,507 windows. [Grade-specific contrasts and uncertainty](RESULTS.json)

## Recorded inputs and reference force

Georgia Tech fitting used 1,060 windows from six walkers at a 5° decline. Person-weighted ridge regression predicted two normalized belt impulses. Within fitting, person-disjoint folds selected the penalty before the final fit on all six. The external test applied the original centre, scale, coefficients and intercept without adaptation. The exact weight and source identities are in the model manifest. [Earlier movement comparison](https://github.com/eliminatenoise/NeuroTranslation/blob/1e1433f2ee0e8a0b3c511b3d01844e12eda7f092/benchmarks/emg-floor-load/decline-treadmill/MOVEMENT-RESULTS.json) · [Model manifest](MODEL.json)

Evaluate `Walking_4KPH_5` and `Walking_4KPH_10` for S02–S12 in `C3D.zip` at Zenodo 19632046. Exclude S01 from scoring. Both S01 recordings qualify the geometry and compression sign, with measured angles of 2.902° and 5.721°. Use both sets of belt corners to determine angle and axes for each test recording. Read one positive mass from `SUBJECTS:MASS`. Earlier programme use involved these participants’ level walks. The present lock fixes the new incline recordings. [Lee and Lee data](https://doi.org/10.5281/zenodo.19632046) · [Lee and Lee methods](https://doi.org/10.1038/s41597-026-07595-4) · [Georgia Tech methods](https://doi.org/10.1038/s41597-023-02840-6)

On the stored 100 Hz grid, issue at zero-based offsets 2,130 through 3,490, step 10. Use one current history from issue minus 21 through minus 1 and one history shifted back 100 frames. Require valid `LASI` and `RASI` positions throughout both histories. Rotate the midpoint to anatomical left, backward and outward normal axes. Interpolate across earlier samples to 40 positions from −205 to −10 ms at 200 Hz. Average ten groups of four and subtract the first average from each of the other nine. Apply the frozen readout to the resulting 27 coordinates.

The static reference is $0.1mg\cos\theta$, with recorded mass $m$, $g=9.80665\ \mathrm{m/s^2}$ and the mean angle $\theta$ across both belts. Multiply the sum of the two normalized model outputs by this reference. The acceleration diagnostic adds $0.1ma_n$ to the static reference, estimating $a_n$ with a trailing quadratic fit to the 40 normal positions. Calculate the target as $-\sum(F_{z,1}+F_{z,2})/1000$ over the 100 samples per belt in $[t,t+0.1\ \mathrm{s})$. Use both calibrated source normal channels and retain the signed offsets. Georgia used side-by-side belts and Lee used front and rear belts. The score concerns their sums.

## Comparison and scope

Freeze all predictions and ordered target coordinates before decoding force. Score only common finite outcomes. Average absolute error within each participant-grade pair, then weight grades equally within person and weight people equally. Require 100 usable windows per grade and at least eight paired people. Resample whole participants 10,000 times with seed 20261125. The preset criterion is met when both upper 95% bounds for paired differences are below zero. All 11 people and all 22 recordings qualified. An independent implementation reproduced the scores from the same 602,800 force values. The stored optical tracks may include gap filling. Live capture latency, other movement tasks and separate limb loads remain questions for direct measurement.

## Run the saved model

Open **Compare Results.html** from the extracted ZIP for the offline grade comparison. Open a terminal in the extracted folder for inference. On Linux or macOS, install with `python3 -m pip install -r requirements.txt` and run `sh "./Run on Linux.sh"` or `sh "./Run on macOS.command"`. In Windows Command Prompt, install with `py -3 -m pip install -r requirements.txt` and run `".\Run on Windows.cmd"`. If `py` is absent, the Windows launcher uses `python`. Install with `python -m pip install -r requirements.txt` in that case.

The default input is invented. Append a quoted filename to the launcher command to use your own JSON file. Follow the example’s 21-frame, 100 Hz, two-marker input in metres, using left, backward and away-from-belt axes. Specify mass in kilograms and slope in degrees. The launcher verifies the saved weights and returns static and predicted impulse in N·s for the next 100 ms. Linux was run and all three launcher sources were checked.

Project-authored code, text and coefficients are CC0 to the extent of our rights. The independently published source data are CC BY 4.0. [Project licence](LICENSE) · [Georgia Tech data](https://doi.org/10.35090/gatech/70296) · [Lee and Lee data](https://doi.org/10.5281/zenodo.19632046)
