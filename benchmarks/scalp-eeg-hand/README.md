# Can three scalp electrodes improve a palm-position estimate?

On the development recording, a clock beat the EEG model. A template that averages training movements at the same points in the task reached **7.383 mm RMSE**. The model using earlier EEG samples reached **7.514 mm**. This is one right-hand recording from each of two participants in a constrained screen task. It gives us a comparison we can check in millimetres. [IACKD data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/)

## Where the hand went

The participant moves a ball by moving their hand. The task sometimes sends the ball one way while the hand goes the other. We score the Leap Motion estimate of the physical palm centre, using its horizontal `x_mm` coordinate with right positive. The ball's screen coordinate and task labels stay out of the model. All four instructed conditions are pooled. [IACKD release](https://doi.org/10.18112/openneuro.ds006840.v1.0.0)

Measure time from the go cue and a second problem appears. The recording stores a sample every 10 ms, but its sample grid can miss the cue by a few milliseconds. Our first design required a match to the exact event-relative grid. Nine of 46 training trials and two of 59 development trials qualified. The four-trial minimum per role stopped the fit.

Before fitting, we froze a separate analysis that starts the clock at the first stored sample at or after the cue. That sample was 0–9 ms after the cue. We score at +100, +150, …, +500 ms from the stored anchor, placing the actual targets 100–509 ms after the cue. The two EEG averages for each target cover successive 50 ms bins at C3, Cz and C4, with the latest stored EEG sample 10 ms before the target. The two tagged raw run headers and the authors' preprocessing and export support those central channel identities. The derivative itself carries no channel names. [Channel source evidence](CHANNEL-EVIDENCE.json)

## What the baselines beat

The fit used 46 trials from sub-02. The development comparison used all 59 released trials from sub-03, nine positions each. Only training data determine the feature means and scales, ridge coefficients (`alpha=10`), constant baseline and time template. Every method predicts without prior measured palm coordinates. The time template gets to know when in the task the sample falls.

| Development prediction | RMSE (mm) | Mean signed error (mm) |
| --- | ---: | ---: |
| Mean training position | 7.411 | +0.702 |
| Training position template by time | **7.383** | +0.702 |
| Ridge from three EEG channels | 7.514 | +0.570 |
| Same ridge with EEG paired to the next development trial | 7.420 | +0.570 |

The ridge had lower mean squared error than the constant on 20 of 59 trials and lower error than the template on 29. Dropping any one development trial still left the ridge behind both baselines. Moving the predictions to the next trial preserved the clock and broke the trial correspondence. That control also had lower RMSE than the intact ridge. The errors describe these trials in one development recording. [Exact-grid disposition](RESULT-EXACT-EVENT-GRID.json) · [Native-grid results](RESULT-NATIVE-GRID.json)

The 10 ms separation is a property of the exported timeline. Real-time prediction would require a causal acquisition and preprocessing chain. The source pipeline filters EEG in both time directions, fits alignment using trial-start and later hit events, and smooths palm coordinates with a zero-phase filter. Whole-epoch artifact and alignment selection precede the pilot. Eye, muscle, movement, cue and recording effects can remain in scalp EEG. This test addresses one model's offline error during voluntary movement. Intent, neural mechanism, online control and clinical performance each require separate evidence. [Source processing and limitations](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/)

## Run the comparison

Use Python 3.13 and run these commands from the companion directory. Save only the [sub-02 training MAT file](https://s3.amazonaws.com/openneuro.org/ds006840/derivatives/movement-execution/sub-02/ihc/sub-02_task-ihc_run-01_eeg_leap_R1.mat?versionId=NvfOJ7qC.nps5p0epkDlJwCdofpnsEAA) and the [sub-03 development MAT file](https://s3.amazonaws.com/openneuro.org/ds006840/derivatives/movement-execution/sub-03/ihc/sub-03_task-ihc_run-01_eeg_leap_R1.mat?versionId=78rZ0hRjITFljhBuCkcYX6Cwov148POd) beside it with their original names. The CLI checks both SHA-256 values before parsing either file. The recording files come from Cai, Fu, Wang, Lu, Guo and Xu's CC0 release. [Source paths, hashes and citations](SOURCE.json)

```text
python -m pip install -r requirements.txt
python -m unittest -v
python run.py --train sub-02_task-ihc_run-01_eeg_leap_R1.mat --dev sub-03_task-ihc_run-01_eeg_leap_R1.mat --native-grid --output reproduced-native.json
```

Remove `--native-grid` and choose a new output name to reproduce the exact-grid disposition. That mode records the trial counts and exits with status 2. Add `--check-source` to check hashes, HDF5 axes and the central electrode evidence without scoring. The result has aggregate measurements only. This companion was executed on Linux. [Frozen exact-grid design](DESIGN.json) · [Frozen native-grid design](DESIGN-NATIVE-GRID.json)

The frozen event-time design contains two transcription errors. The study accession is `ds006840`, and its source population consists of study participants. The version, participant IDs and file checksums are recorded in [SOURCE.json](SOURCE.json).
