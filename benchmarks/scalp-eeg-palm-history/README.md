[The studies](../README.md) › Study 7 · Palm: brain signal on top of hand history

# Scalp EEG made the palm forecast worse for all three people

Three people moved a hand in a screen task. A straight-line fit made on three other people, given the time in the task and where the palm had been and how fast it was moving, forecast the palm's sideways position 100 ms ahead with an error of **1.093 mm**. With EEG from three scalp channels added, it missed by **1.223 mm**: 0.131 mm worse, and worse for each of the three. EEG from the next trial did better than the right EEG, at 1.203 mm. Repeating the last position missed by 4.439 mm.

Every score here is the measure that punishes large misses (root mean squared error), in millimetres, with each person counting equally: the square root of the average of the three people's mean squared errors. EEG is electrical activity of the brain, picked up on the scalp. A *straight-line fit* is a weighted sum of its inputs, here a ridge regression.

| Forecast for the three test people | Error (mm) |
| --- | ---: |
| Elapsed time, past palm position and speed | 1.093 |
| Elapsed time, past palm position and speed, and scalp EEG | 1.223 |
| The same EEG model, given EEG from the next trial | 1.203 |
| Carry the recent palm speed forward in a straight line | 1.150 |
| Repeat the last palm position | 4.439 |
| The fitting people's average palm position | 21.568 |
| Their average path by elapsed time | 21.575 |
| Elapsed time and scalp EEG | 21.830 |
| The same elapsed-time EEG model, given EEG from the next trial | 21.125 |

All 337 released trials qualified. The three test people supplied 173 trials and 1,557 scored positions, and every method was scored on those same positions. The three people's increases with EEG were 0.170, 0.030 and 0.166 mm. EEG did lower the squared error on 72 of the 173 trials, 31 of 58 for sub-10, but larger errors on other trials pulled each person's score up. Leaving out one test person at a time gives increases from 0.109 to 0.167 mm. On the plain average miss (mean absolute error), carrying the speed forward beat the fitted model, 0.667 against 0.706 mm; on the measure that punishes large misses it lost. [Errors by person, by moment and by trial](RESULT.json)

![Paired dot plot of root mean squared error in millimetres. Adding EEG raised error for sub-10 by 0.170, sub-11 by 0.030 and sub-12 by 0.166. Error with the three people weighted equally rose from 1.093 to 1.223 mm.](cohort-comparison.png)

## What each model sees

The elapsed-time model knows which of nine scheduled moments is being forecast. The past-palm model adds the tracked position 100 ms before the target and the speed worked out backwards from it and the position 150 ms before the target. The EEG model adds two five-sample averages at each of C3, Cz and C4, whose last sample is also 100 ms before the target. In the next-trial control only the EEG moves, to the next usable trial of the same person; the timing and the past palm stay with the original trial. The move can change the trial's task condition.

The fits use the three fitting recordings, an intercept with no penalty at each of the nine moments, and a fixed penalty of 0.01 that keeps the weights on the scaled inputs small. No test target shaped any weight, scale or penalty. The released right-hand files carry no channel labels; the headers and channel tables of the same runs name C3, Cz and C4, and the documented export order and the constant width of the processed files support the match. Some released trial counts differ from the raw event tables; this study uses the authors' paired processed trials. [Input versions, metadata and channel evidence](SOURCE.json) · [Fitted model](MODEL-STATE.json)

## Where the clock starts

The first plan tied the forecasts to the moment the cue disappeared, event 14. To forecast its first target, 100 ms after the cue's row in the recording, the model needed palm readings at the cue's row and 50 ms before it. Every released trial lacked at least one of them. The rule that all inputs be present excluded all 337 trials, so there was no fit and no score. [The first plan](original-cue-window/DESIGN.json) · [Its recorded no-fit](original-cue-window/RESULT.json)

The one alternative was written down before any fit from scalp to palm. It starts each trial at the first stored palm position at or after the cue's row. That first reading came 0–16 ms after the nominal cue across all six recordings, and 0–9 ms in the three test recordings. The nine targets run from +200 to +600 ms after it, in 50 ms steps. The oldest EEG and palm inputs for the first target come 10 and 50 ms after it. So the stored target times fall 200–616 ms after the cue across the six recordings. The written feature description carries over a sentence from the first plan that allows palm rows before the start; the alternative's own clock and lag rule gives the rows used here. [The alternative and its exact input rules](DESIGN.json)

The tracker estimates the centre of the real palm. The released archive aligns and smooths that trace, and its EEG processing can use later values. The first stored position is where the released palm trace becomes available to this analysis: the cue disappearing, the first available position and the start of the real movement are three different moments. The 100 ms is exact in the stored arrays; the physical or live delay was never measured. [IACKD data descriptor](https://doi.org/10.1038/s41597-026-07146-x) · [The authors' methods and code](https://github.com/Boketto1/IACKD/tree/c0b595de7571c7e04abae7477c61d0b92b5702cd)

## What it does not show

These three recordings give no sign that these EEG features lower the error in this fixed comparison, made after the fact. The archive is a constrained task with feedback on a screen, and its signals can carry cue, motion, eye and muscle effects. The original dataset recruited 15 healthy right-handed university students aged 23–27, 11 of them men; this study uses one right-hand run from each of six of them. Other people, other tasks, other EEG features, brain mechanisms and live decoding remain open. No group was set aside for this study: sub-01 to sub-06 were barred from it, and the files name no reserve. [Participants and task](https://doi.org/10.1038/s41597-026-07146-x)

## The plan

The main comparison was fixed in advance, with no pass threshold, and the plan calls the result exploratory. [The plan](DESIGN.json) · [Hashes of the plan, code and source, fixed before scoring](PRESCORE-LOCK.json)

## Replay a recorded trial

Get one of the six right-hand R1 MAT files from its versioned address in the source table, or run the fetch command below. Extract the converter ZIP and keep its `metadata/` folder and `source-lock.json` beside the script. From the extracted `public-converter` folder, convert the first released trial of sub-10:

```sh
python -m pip install -r requirements.txt
python mat_to_companion.py --mat ../iackd-data/sub-10_task-ihc_run-01_eeg_leap_R1.mat --trial 1 --output sub-10-trial-01.json
```

Change the MAT path to your data folder; on Windows, use `py` if that is how you start Python. The converter checks the input file's name, size and SHA-256, and keeps the whole stored trial with its missing tracker readings. The ZIP holds the converter and the source metadata; the recording comes from OpenNeuro. [Download the converter](NeuroTranslation-IACKD-R1-Converter.zip) · [Versioned source files](SOURCE.json)

In **Palm replay**, click **Import a trial**, choose your JSON and confirm. Select the recording and click **Compare estimates**. The page plots the tracked palm beside the forecasts of both fitted models. **Read sample values** gives the time and position behind each mark, and **Download trial results** saves the forecasts, with the model's identity, on your computer. One recording gives its own error; the result above combines the three test people. Keep the recording and the export on your computer. [Open the palm replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay)

## Score it again

Use Python 3.13 in a virtual environment on Windows, macOS or Linux, install the pinned packages and work from this folder. The check here ran on Linux. The download command asks OpenNeuro's public storage for six versioned files, then checks each one's version, size and SHA-256. Keep the source files in a local data folder.

```sh
python -m pip install -r requirements.txt
python fetch_inputs.py --output ../iackd-data
python -m unittest -v
python run.py --input ../iackd-data --output ../availability-run
python original-cue-window/run.py --input ../iackd-data --output ../original-cue-run
```

Choose new output folder names each time. The cue-window run writes its no-fit result and exits with status 2. The main comparison writes `RESULT.json`, the fitted `MODEL-STATE.json` and the details of the run. A separately written analysis reached the same decision on which trials qualify and checked 2,454 numbers from the fits and results. This folder holds summary errors and model weights; the dataset stays with its original host. [Independent check](INDEPENDENT-CHECK.json) · [OpenNeuro ds006840 v1.0.0, CC0](https://doi.org/10.18112/openneuro.ds006840.v1.0.0)

To redraw the figure from the same summary results, run the figure script from this folder:

```sh
python -m pip install matplotlib==3.11.2
python plot_results.py --input RESULT.json --output cohort-comparison.png
```
