# Compare two hand movement forecasts

[Package overview](README.md) · [Technical guide](TECHNICAL.md) · [Measurements](results.json)

## The input and the two answers

This NeuroTranslate example takes recent readings from electrodes in the part of the brain involved in movement. It estimates where a hand will end up 100 milliseconds later and how far it will travel. The prediction gives the change in X and Y from where the hand is now. There is also a separate estimate of travel distance. The computer learned that last answer separately, so it can differ from the length of the X and Y prediction.

The input is 200 milliseconds of brain activity, divided into ten pieces of 20 milliseconds each. An electrode reports an event when the voltage crosses a set threshold. The program sees the number of events in each piece for each electrode. The archive numbers the 96 electrodes in this group from 96 to 191. Give the counts in time order. Exact sample timestamps set the start and end of the history. An event exactly at the end is available for a later window, so adjoining histories avoid counting it twice. The program uses a complete recording window from this electrode array. [Data in DANDI](https://dandiarchive.org/dandiset/000070/0.261122.2046) · [Original models](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/cortical-electrode-identity)

## The mixing rule

Three original models were fitted on September 23. Each makes its own forecast from the same electrode activity. The blend reduces each forecast toward zero by multiplying it by the same number. A weight of one leaves a forecast as it was. A weight of zero makes the hand stay where it is. A weight of one half cuts the predicted X change, Y change and distance in half.

Six readings help the program choose that number. It looks at the length of the three predicted movements, their separate estimates of distance, and whether the directions agree. The agreement number compares the length of the average prediction with the average length of the three predictions. A small added value of 0.000001 mm keeps that division defined even when the three lengths are zero. The program also uses average activity in the latest 60 milliseconds, the change from the first 60 milliseconds, and how much the latest 60 milliseconds of activity varies from one electrode to another. The model takes a log of one plus each rate or length where specified in the technical guide. That keeps large values from dominating the fit.

The program compares each reading with the average and spread measured during calibration. It limits the resulting standardized values to the range −5 to 5. A curve called a sigmoid then turns the weighted sum into a number between zero and one. You can read the learned weights, averages and scales in `BLEND.json`.

The mixing rule learned from 52,468 examples taken from September 20 and the final quarter of September 22. Each date had the same weight, followed by equal weight for the trials within each date. Within a trial, all its selected examples counted equally. The program used 64-bit arithmetic to fit this small rule. It looked for a smaller average ending-position error, used a 0.01 mm adjustment in the error formula to make optimization smoother, and discouraged large coefficients with a penalty of 0.05 times the sum of their squares. It tried three starting points for the same fitting method, called L-BFGS, and kept the best calibration result. The three original models kept their 32-bit weights. The forecast itself has no access to measured hand position.

## What happened on the recordings

The two August dates come from the same animal and were recorded before the training and calibration dates. All forecasts on each day were saved before opening the exact hand positions used to check them. Each trial gets equal weight in the results. The table averages the errors from the three models. The ending-position score measures how far the forecast end fell from the real end. The distance score measures the error in how far the hand moved, taken from the model's separate estimate. All errors are in millimetres.

| Held recording | Trials | Windows | Endpoint, original | Endpoint, blend | Endpoint, stay put | Distance, original | Distance, blend | Distance, stay put |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 19 August 2010 | 3,126 | 39,297 | 14.61 | 8.19 | 7.89 | 13.24 | 6.20 | 7.89 |
| 12 August 2010 | 3,038 | 46,102 | 8.47 | 5.00 | 6.65 | 7.72 | 3.60 | 6.65 |

The blend reduced both errors compared with the original forecasts on both days. It reduced ending-position error below the stay-put forecast on August 12. On August 19 its ending-position error was 0.29 mm higher than staying put. Drawing whole trials again 4,000 times gave a 95% interval from 0.19 to 0.40 mm for that difference. The interval describes the variation in trials from that day.

When the hand travelled at least 20 mm, the original forecast gave smaller ending-position errors than the blend. On August 19 the original averaged 24.01 mm and the blend averaged 25.51 mm in those cases. On August 12 the corresponding averages were 21.38 and 23.42 mm. When the hand moved less than 2 mm, staying put averaged 0.40 mm and 0.32 mm on the two days. The blend averaged 4.36 mm and 1.21 mm. These groups come from the measured movement after the forecast, so the program cannot switch forecasts by looking at the group in advance. These findings apply to the recorded tasks on the same calibrated animal. Using the method on a new person, animal or recording system requires its own evaluation.

## Run the generated example or prepared counts

1. Extract the ZIP and open the folder in a terminal. Install Python 3.12 if needed. On Linux or macOS, run `python3.12 -m pip install -r requirements.txt`. On Windows, run `py -3.12 -m pip install -r requirements.txt`. This installs the two libraries for the same Python version used by the launcher.
2. Open `Open on Linux.sh`, `Open on macOS.command` or `Open on Windows.cmd` for your system. You can also run `python3.12 predict.py` on Linux or macOS, or `py -3.12 predict.py` on Windows. The first run uses invented counts so that it can work without the recording. The Linux launcher and every saved forecast on both held recordings were replayed. The other two launchers are included for their respective systems.
3. For a prepared recording window, add `--input window.json` to the direct Python command. In that file, `electrode_ids` lists every number from 96 to 191 once. The matching row of `counts` holds ten whole numbers, all zero or greater, with the oldest first. Use a full observed window from the matching electrodes. The program sorts the counts by their IDs.

The result shows the fraction retained in `blend_weight`. For each of the three fitted models it prints the original X and Y movement and distance, then the blended versions of the same answers. All three models can run from the included ONNX files. Their original training weights are in SafeTensors files, and the mixer's smaller set of learned numbers is in `BLEND.json`. The package's code and weights use [CC0](LICENSE). The recordings remain available with their original attribution at [DANDI](https://dandiarchive.org/dandiset/000070/0.261122.2046).
