# Predicting treadmill force from pelvis motion

[Download the model, offline viewer and example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/decline-treadmill/camera-transfer/Pelvis-Motion-Forecast.zip) · [Technical edition](TECHNICAL.md) · [Exact scores](RESULTS.json)

A model fitted on downhill walking at Georgia Tech forecast the combined load on two treadmill belts during uphill walking in a second laboratory. Its average error was **5.12 newton-seconds**, compared with **9.17** from body weight alone. That is about **44% less error**. The forecast improved on the body-weight rule for all **11 people**, at both slopes. We used the original model weights for all 3,014 forecasts in the new test. [Georgia Tech recordings](https://doi.org/10.35090/gatech/70296) · [Lee and Lee recordings](https://doi.org/10.5281/zenodo.19632046)

## What the model predicts

The treadmill measures the push on each belt. We use the part of that push at right angles to the sloping surface. We add the force readings from both belts over the next tenth of a second and multiply by the time between readings. This quantity is **impulse**, measured in newton-seconds (N·s). A force of 500 newtons held for a tenth of a second gives 50 N·s. The error is the distance between the forecast and the measured impulse.

The original treadmill had belts side by side. The second laboratory had one belt in front of the other. We add both belt forecasts and both measurements before comparing them. An error on one belt can offset an error on the other, so these scores describe their combined load. [Georgia Tech methods](https://doi.org/10.1038/s41597-023-02840-6) · [Lee and Lee methods](https://doi.org/10.1038/s41597-026-07595-4)

## How the predictions differed

| Forecast | Both grades | Near 5% grade | Near 10% grade |
| --- | ---: | ---: | ---: |
| Recent pelvis motion | 5.12 | 4.90 | 5.33 |
| Body weight alone | 9.17 | 8.57 | 9.77 |
| Pelvis motion from one second earlier | 15.96 | 14.75 | 17.17 |
| Mechanical estimate from pelvis acceleration | 12.61 | 12.31 | 12.91 |

All entries are average absolute error in N·s. Body weight alone gives the same answer at every forecast time in one recording. It uses the walker’s recorded mass and the measured slope. The one-second-earlier forecast applies the same camera model to an older segment. Its higher error shows that the timing of the motion mattered here. The last row uses a simple force calculation that treats acceleration at the skin markers as an estimate of how the body’s mass accelerates.

Across the two grades, the camera forecast reduced each person’s error relative to the body-weight rule by **4.05 N·s on average**. To see how much the result depends on the people in this group, we drew groups of 11 from the same 11 people, with repeats allowed, 10,000 times. We kept each person’s predictions at both slopes together. The middle 95% of the reductions ranged from **3.04 to 5.18 N·s**. The reduction against the one-second-earlier forecast was **10.85 N·s**, with a range from **8.23 to 13.38**. The planned criterion required at least eight people who qualified at both grades and a range entirely above zero against both references. All 11 qualified. [Exact scores and separate uncertainty estimates by grade](RESULTS.json)

## How the test worked

We fitted the original model using 1,060 examples from six people at a 5° decline. The fit gave every person the same weight. It learned a multiplier for each small change in pelvis position, with a penalty to keep individual multipliers from becoming too large. The amount of the penalty came from trying forecasts on fitting participants left out of each fit. Then we fitted once on all six and saved those numbers. [Earlier model and movement comparison](https://github.com/eliminatenoise/NeuroTranslation/blob/1e1433f2ee0e8a0b3c511b3d01844e12eda7f092/benchmarks/emg-floor-load/decline-treadmill/MOVEMENT-RESULTS.json)

For the new test, 11 people each walked at four kilometres per hour on two inclines. The labels 5 and 10 refer to grades close to 5% and 10%. A grade of 10% rises about ten centimetres per metre of horizontal travel. We checked the recorded belt corners and force direction using two walks from a separate person before the test. Those two checks measured angles of about 2.90° and 5.72°. Each test forecast uses its own recording’s measured slope. Earlier work used level walks from the same Lee and Lee participants. This test uses their preassigned uphill recordings.

The camera stored 100 positions per second for two points on the front of the pelvis. We average the two points and record the midpoint motion from left to right, forward and back, and toward and away from the belt. Each forecast uses the 21 camera frames immediately before it. The last one is ten milliseconds before the forecast begins. The original model expects more closely spaced readings, so we add midpoints between the earlier samples, then average 40 values into ten time groups. The input is how the last nine group averages moved from the first one. We convert the model’s answer to N·s using body mass and slope.

We scheduled a forecast every tenth of a second at 137 fixed times in each recording. Each method had the same input and force requirements. Every forecast qualified here, giving 1,507 at each grade. We saved all forecasts and verified which force samples to read before calculating the errors. A separate calculation used those same 602,800 force values and reproduced the scores. Each reported error gives the two grades equal weight for a person, then gives every person equal weight. A person needed at least 100 usable forecasts per grade to enter the combined comparison.

## Run the model

1. Download and extract the ZIP. Open **Compare Results.html** from the extracted folder to switch between grades in a browser. The viewer works offline.
2. To run a forecast, open a terminal in the extracted folder. On Linux and macOS, install NumPy with `python3 -m pip install -r requirements.txt`. Run `sh "./Run on Linux.sh"` on Linux or `sh "./Run on macOS.command"` on macOS. In Windows Command Prompt, install with `py -3 -m pip install -r requirements.txt`, then run `".\Run on Windows.cmd"`. If Windows has `python` but no `py` launcher, install with `python -m pip install -r requirements.txt` instead.
3. The launcher checks the saved weights and forecasts from invented input in **Example camera frames.json**. We ran the Linux launcher and checked the macOS and Windows launcher source. To forecast from your own prepared recording, append its quoted filename to the launch command. Use the same fields as the example. Supply 21 earlier frames at 100 Hz, each with two three-dimensional positions in metres. Align the coordinates left, backward and away from the belt surface. Include measured body mass in kilograms and measured belt angle in degrees. The output gives the static estimate and the predicted combined impulse over the next 100 ms, both in N·s.

The camera positions in this study are stored tracks that may contain filled-in gaps. The timing describes those stored frames. A live camera would have to demonstrate its own time delay, visibility and forecast accuracy. The test measured combined belt load during one treadmill task. Other movements and separate limb forces need separate comparisons.

Project-authored code, text and coefficients are available under CC0 to the extent of our rights. The Georgia Tech and Lee and Lee data are distributed by their authors under CC BY 4.0. [Project licence](LICENSE) · [Georgia Tech data and licence](https://doi.org/10.35090/gatech/70296) · [Lee and Lee data and licence](https://doi.org/10.5281/zenodo.19632046)
