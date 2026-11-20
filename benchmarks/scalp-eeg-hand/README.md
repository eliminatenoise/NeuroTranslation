[The studies](../README.md) › Study 6 · Palm, first try: brain signal alone

# A clock placed the palm better than three scalp electrodes

One person's palm was tracked through 59 trials of a screen task, and every model was fitted on a second person. Knowing only when in the task each moment fell, that second person's average path placed the palm with an error of **7.383 mm**. A straight-line fit on scalp EEG from three electrodes missed by **7.514 mm**: 0.131 mm worse. Whichever one test trial is left out, the EEG fit stays behind both simple forecasts: by 0.093 to 0.148 mm behind the clock and by 0.085 to 0.113 mm behind the single average position. It failed the pass rule set for it before scoring, which asked it to beat both the clock and a single average position.

Every score here is the measure that punishes large misses (root mean squared error), in millimetres. EEG is electrical activity of the brain, picked up on the scalp. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small. This was a first trial: one right-hand recording from each of two people, in a constrained task. [IACKD data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/)

| Forecast for the test person | Measure that punishes large misses (mm) | Average signed error (mm) |
| --- | ---: | ---: |
| The fitting person's average position | 7.411 | +0.702 |
| The fitting person's average position at the same moment of the task | **7.383** | +0.702 |
| Straight-line fit on three EEG channels | 7.514 | +0.570 |
| The same fit, its forecasts moved to the next test trial | 7.420 | +0.570 |

The EEG fit had a lower squared error than the single average position on 20 of 59 trials, and than the timed average on 29. Moving its forecasts to the next trial keeps the clock and breaks the link between EEG and trial, and that did better than the real pairing. [Results on the exact grid](RESULT-EXACT-EVENT-GRID.json) · [Results on the recording's own grid](RESULT-NATIVE-GRID.json)

## Where the hand went

The person moves a ball on a screen by moving their hand. Sometimes the task sends the ball one way while the hand goes the other. The target is the Leap Motion tracker's estimate of the centre of the real palm, along its horizontal `x_mm` axis, right positive. The ball's screen position and the task labels stay out of the model, and all four instructed conditions are pooled. [IACKD release](https://doi.org/10.18112/openneuro.ds006840.v1.0.0)

The fit used 46 trials from sub-02. The test used all 59 released trials from sub-03, nine positions each. Only the fitting person's data set the feature averages and scales, the EEG fit's weights (with a penalty `alpha=10` that keeps them small), the single average position and the timed average. No method sees where the palm has been. The timed average knows when in the task each moment falls.

## The first plan had too few trials, so a second clock was fixed before fitting

Time the forecasts from the go cue and a problem appears. The recording stores a sample every 10 ms, and its sample grid can miss the cue by a few milliseconds. The first plan required samples on an exact grid counted from the cue. Nine of 46 fitting trials and two of 59 test trials qualified, and the plan's minimum of four trials per group stopped the fit.

Before fitting, a second analysis was fixed that starts the clock at the first stored sample at or after the cue, 0–9 ms after it. The forecasts are scored at +100, +150, …, +500 ms from that sample, so the real targets fall 100–509 ms after the cue. The two EEG averages for each target cover two 50 ms bins in a row at C3, Cz and C4, and the latest EEG sample is 10 ms before the target. The two tagged raw recording headers and the authors' processing and export support those three central channel names; the processed file itself carries no channel names. [Channel evidence](CHANNEL-EVIDENCE.json)

## What it does not show

One test person, one task, scored after the fact on exported recordings. The source filters the EEG in both directions in time, aligns trials using the trial start and later hit events, and smooths the palm positions with a filter that also looks forward, so the 10 ms lead exists only on the stored timeline: a live forecast would need recording and processing that use no later data. Whole trials were screened for artefacts and alignment before this study began, and eye, muscle, movement, cue and recording effects can still remain in scalp EEG. A third person, sub-06, was named as the reserve for this trial; only that person's description was read, the recording was never opened, and no confirming analysis exists. [Source processing and limits](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/)

## Run it yourself

Use Python 3.13 and run these commands from this folder. Save only the [sub-02 fitting MAT file](https://s3.amazonaws.com/openneuro.org/ds006840/derivatives/movement-execution/sub-02/ihc/sub-02_task-ihc_run-01_eeg_leap_R1.mat?versionId=NvfOJ7qC.nps5p0epkDlJwCdofpnsEAA) and the [sub-03 test MAT file](https://s3.amazonaws.com/openneuro.org/ds006840/derivatives/movement-execution/sub-03/ihc/sub-03_task-ihc_run-01_eeg_leap_R1.mat?versionId=78rZ0hRjITFljhBuCkcYX6Cwov148POd) beside it, under their original names. The program checks both SHA-256 values before reading either file. The recordings come from the CC0 release of Cai, Fu, Wang, Lu, Guo and Xu. [Source paths, hashes and citations](SOURCE.json)

```text
python -m pip install -r requirements.txt
python -m unittest -v
python run.py --train sub-02_task-ihc_run-01_eeg_leap_R1.mat --dev sub-03_task-ihc_run-01_eeg_leap_R1.mat --native-grid --output reproduced-native.json
```

Remove `--native-grid` and choose a new output name to repeat the exact-grid attempt: it records the trial counts and exits with status 2. Add `--check-source` to check the hashes, the HDF5 axes and the central electrode evidence without scoring. The result holds summary measurements only. The program was run on Linux.

## The plan

Both plans were fixed before fitting: [the plan on the exact grid](DESIGN.json) and [the plan on the recording's own grid](DESIGN-NATIVE-GRID.json). The first contains two copying errors: the dataset's number is `ds006840`, and the people it draws on are that dataset's own participants. The version, participant IDs and file checksums are in [SOURCE.json](SOURCE.json).

The next palm study gives the model the palm's own recent path: [Study 7 · Palm: brain signal on top of hand history](../scalp-eeg-palm-history/).
