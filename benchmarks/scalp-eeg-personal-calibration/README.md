[The studies](../README.md) › Study 8 · Palm: adjusted on the person's first recording

# One earlier recording of a person improved the palm forecast for all three

The palm model of [study 7](../scalp-eeg-palm-history/), fitted on three other people, was adjusted on each new person's first right-hand recording and then scored on their second. Unadjusted, the version with scalp EEG forecast the palm's sideways position 100 ms ahead with an error of **1.849 mm**. Adjusted, it missed by **1.700 mm**: 0.150 mm better, for each of the three people, by 0.069 to 0.284 mm. The version without EEG improved by about as much, to 1.691 mm. So once adjusted, EEG still added nothing: it raised the error by 0.0085 mm.

Every score here is the measure that punishes large misses (root mean squared error), in millimetres, with each person counting equally. EEG is electrical activity of the brain, picked up on the scalp. The two recordings are separate files, first and second in the archive's release order (its labels R1 and R2). Their labels give no time between them and no sign that they were made on different days. [IACKD data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/) · [OpenNeuro release](https://doi.org/10.18112/openneuro.ds006840.v1.0.0)

| Forecast on the second recording | Time and past palm (mm) | Time, past palm and EEG (mm) |
| --- | ---: | ---: |
| The model as fitted on other people | 1.839 | 1.849 |
| Correct its average error | 1.825 | 1.841 |
| Correct its average error at each of the nine moments | 1.833 | 1.848 |
| Adjust its weights and its intercept at each moment | 1.691 | 1.700 |
| The same adjustment, given EEG from the next trial | — | 1.694 |

The full adjustment beat the unadjusted EEG model for all three people and on 121 of 176 trials. It gained 0.148 mm over correcting the error at each moment. Leaving out any one person leaves a gain of 0.091 to 0.184 mm. Counting every position equally instead of every person gives a 0.149 mm gain, and 0.0086 mm more error from adding EEG. EEG from the next trial did slightly better than the real pairing for two of the three people; that control keeps time and palm together and can change the task condition paired with the EEG. [All paired errors, controls and checks](RESULT.json)

| Person | First recording: trials usable / released | Second recording: trials usable / released | Change from the adjustment, EEG model (mm) | Change from adding EEG after the adjustment (mm) |
| --- | ---: | ---: | ---: | ---: |
| sub-13 | 57 / 57 | 58 / 58 | −0.284 | +0.0012 |
| sub-14 | 59 / 59 | 59 / 60 | −0.069 | +0.0106 |
| sub-15 | 60 / 60 | 59 / 59 | −0.109 | +0.0126 |

The adjustment used 176 trials and 1,584 positions from the first recordings; the score used another 176 trials and 1,584 positions from the second. One trial of sub-14's second recording fell outside the clock tolerance fixed in advance and was left out of every method. Every usable trial gave nine positions. The targets fell 200 to 609 ms after the cue disappeared, across the six recordings. [Counts and clock ranges](RESULT.json)

## What the adjustment changes

Every method forecasts nine positions, 200 to 600 ms after the first palm reading at or after the cue. The target is the authors' estimate of the centre of the real palm along the tracker's horizontal axis, in millimetres. The model sees the palm position 100 ms before the target and the speed worked out backwards from the readings 100 and 150 ms before it. The EEG version also sees two five-sample averages from C3, Cz and C4, whose last sample has the same 100 ms lead. The rules for missing rows and usable trials are the same for every method. [Timing and feature definitions, fixed in advance](frozen_cohort/DESIGN.json)

Every correction starts from how far the original model missed on the first recording. One control corrects its average miss. Another corrects the average miss separately at each of the nine moments. The full adjustment can also change how strongly each input moves the forecast; a fixed penalty of 0.01, the same for both models, holds those changes back, using the original scaling and the same trials of the first recording. Each person gets their own corrections. The scoring command reads those saved corrections and scores the second recording without fitting anything, and the two commands can run on completely separate input folders. [The adjustment plan, fixed in advance](DESIGN.json) · [The model from study 7](frozen_cohort/MODEL-STATE.json)

## What it does not show

These are movements in a screen task with feedback, where the hand and the cursor sometimes move the same way and sometimes opposite ways. The 100 ms is on the released clock: the archive processed the EEG after the fact, smoothed and aligned the palm trace and ran its own quality checks, so when the signals would be available live is unknown. The source headers list 31 raw EEG channels for these recordings and 29 for study 7's, so the same three channel names may not have been processed the same way. Practice, changes in the recording and the mix of task conditions can each explain part of the difference between the first and second recording, and each person gives one pair. No group was set aside for this study.

Study 7's first, cue-timed plan stopped without a fit: its earliest targets needed tracker readings from before the released palm trace began. This study keeps study 7's later timing, which was checked independently, and its saved model. No recording of sub-01 to sub-12 enters the two commands under **Score it again**: they read only the first and second recordings of sub-13, sub-14 and sub-15. [Study 7's first plan on six people, and its recorded result: no fit](frozen_cohort/ORIGINAL-CUE-RESULT.json)

## The plan

The plan sets no pass threshold and picks no winner. [The adjustment plan](DESIGN.json) · [Saved corrections](CALIBRATION-STATE.json)

## Replay a second recording

Open a trial to see what the adjustment changed at nine positions. The converter ZIP holds a small Python program, the source metadata, and launchers for Windows, macOS and Linux. Extract it and open its README for the three pinned downloads of the second recordings and the setup command for your system. The first trial of sub-13 is one complete example. [Download the converter for the second recordings](NeuroTranslation-IACKD-R2-Converter.zip) · [Open the browser replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay)

In the page, choose **Import a trial**, select your JSON file, then **Compare estimates**. Pick hand history alone or hand history with EEG to see the tracked position beside the unadjusted and the personally adjusted forecasts. The table of errors uses the same positions for all four models. A complete, usable trial is checked against the archived clock and the four source signals, as in the study; a clipped stretch shows only the rows you supplied.

## Score it again

Use Python 3.13 and install the pinned packages in a virtual environment. The launchers pass on the same arguments as `python run.py`. Open a terminal in this folder: on Linux use `./Run-Linux.sh`, on macOS `./Run-macOS.command`, and on Windows `Run-Windows.cmd` from Command Prompt. With no arguments, each launcher shows the command help. Set `PYTHON` to the virtual environment's Python if it is not your shell's active one.

```sh
python -m pip install -r requirements.txt
python -m unittest -v
python fetch_inputs.py --role CALIBRATION --output ../iackd-r1
python run.py calibrate --input ../iackd-r1 --output ../new-state.json
python fetch_inputs.py --role EVALUATION --output ../iackd-r2
python run.py evaluate --input ../iackd-r2 --state ../new-state.json --state-sha256 YOUR_CALIBRATION_SHA256 --output ../new-result.json
```

Replace `YOUR_CALIBRATION_SHA256` with the hash that `calibrate` prints. The study takes only the six file versions listed in `SOURCE.json`; the downloader checks each one's version, size and SHA-256. Both commands need an unused output path and check the exact input hashes again. The archive stays with OpenNeuro; the study writes corrections, error summaries and counts of usable data. The whole run was checked on Linux. [Pinned source records](SOURCE.json) · [OpenNeuro release and licence](https://doi.org/10.18112/openneuro.ds006840.v1.0.0) · [Recording and processing methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/) · [The authors' method code](https://github.com/Boketto1/IACKD/tree/c0b595de7571c7e04abae7477c61d0b92b5702cd)
