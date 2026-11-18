# Can a palm model learn your movement from one recording?

The first recording gives the model examples of where this person's right palm actually went. The second recording asks whether those examples buy any accuracy. We start from a model trained on three other people and use the first right-hand recording, R1, to adjust its final linear coefficients. We then score those saved adjustments on the corresponding R2 recording for each of three new people. R1 and R2 are distinct archive recordings in that release order. Their labels give no elapsed time or evidence of separate days. [IACKD data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/) · [OpenNeuro release](https://doi.org/10.18112/openneuro.ds006840.v1.0.0)

## What the second recording showed

Calibration lowered the combined model's equal-person root-mean-square error from **1.849 to 1.700 mm**. The palm-only model improved by about the same amount and reached **1.691 mm**. Adding EEG after matched calibration raised error by 0.0085 mm. The paired increase was between 0.0012 and 0.0126 mm across the three people.

| R2 method | Time and past palm (mm) | Time, past palm and EEG (mm) |
| --- | ---: | ---: |
| Frozen training model | 1.839 | 1.849 |
| Correct the average error | 1.825 | 1.841 |
| Correct the error at each offset | 1.833 | 1.848 |
| Adjust slopes and offset intercepts | 1.691 | 1.700 |
| Same slope and intercept fit with EEG from the next trial | — | 1.694 |

The full adjustment improved over the frozen combined model for all three people and on 121 of 176 trials. Its gain over the offset-only correction was 0.148 mm in the equal-person comparison. Removing any one person left a combined-model reduction of 0.091 to 0.184 mm. Pooling every position instead of weighting people equally gave a 0.149 mm reduction and a 0.0086 mm increase from adding EEG. The next-trial EEG control also had slightly lower error than real trial pairing in two of three people. This rotation keeps time and palm together and can change the task condition paired with EEG. These comparisons describe this split and these six EEG features, with no inference about the wider population or what other features could contribute. [Full paired errors, controls and sensitivity](RESULT.json)

| Participant | R1 eligible / released | R2 eligible / released | R2 calibration change, EEG model (mm) | R2 change from adding EEG with matched calibration (mm) |
| --- | ---: | ---: | ---: | ---: |
| sub-13 | 57 / 57 | 58 / 58 | −0.284 | +0.0012 |
| sub-14 | 59 / 59 | 59 / 60 | −0.069 | +0.0106 |
| sub-15 | 60 / 60 | 59 / 59 | −0.109 | +0.0126 |

The fit used 176 R1 trials and 1,584 positions. The R2 score used another 176 trials and 1,584 positions. One sub-14 R2 trial fell outside the frozen clock tolerance and was excluded for every method. Every eligible trial contributed nine positions. The target times ranged from 200 to 609 ms after cue disappearance across the six recordings. [Counts and clock ranges](RESULT.json)

## What changes between R1 and R2

Every method gets nine target positions 200 to 600 ms after the first finite palm reading at or after the cue. The optical target is the author's estimate of the actual palm centre along the device's horizontal axis, in millimetres. The model sees palm position 100 ms before the target and backward velocity calculated from the 100 and 150 ms samples. The EEG version also sees two five-sample means from C3, Cz and C4, with its last sample at the same nominal 100 ms lead. The rules for missing rows and trial eligibility are shared across methods. [Frozen timing and feature definitions](frozen_cohort/DESIGN.json)

First we ask how far the original model misses each R1 target. One control corrects its average miss. Another corrects the average miss separately at each of the nine offsets. The last fit can also change how strongly the inputs affect the prediction. Ridge regression penalizes those slope changes with the same fixed 0.01 penalty for both models, using the original training scales and the same R1 trials. Each person gets their own corrections. The evaluation command reads those coefficients and scores R2 without fitting. The two commands can run with completely separate input directories. [Frozen calibration design](DESIGN.json) · [Base model](frozen_cohort/MODEL-STATE.json)

These are measured movements in a screen-feedback experiment, with both congruent and reversed mappings between hand and cursor. The 100 ms gap is on the released clock. The archive's retrospective EEG processing, optical smoothing and alignment, and joint quality checks leave the timing of live signal availability unresolved. The model extracts the same three named scalp channels as the original benchmark. The source headers report 31 raw channels for these new recordings and 29 for the original cohort, so the wider recording montage can affect the published EEG processing even when the input names match. Practice, recording changes and task mix can contribute to a difference between R1 and R2. The experiment observes one fixed pair per person. [Recording and processing methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13287794/) · [Original method code](https://github.com/Boketto1/IACKD/tree/c0b595de7571c7e04abae7477c61d0b92b5702cd) · [Pinned source records](SOURCE.json)

The original cue grid remains a separate result. Its earliest targets needed optical history before the released palm track provided it, and the analysis stopped without a fit. This experiment keeps the independently checked post-observation grid and its saved model. The original training, development and reserved recordings never enter these two commands. [Six-person cue grid and retained no-fit](frozen_cohort/ORIGINAL-CUE-RESULT.json)

## Replay a second recording

Open a trial to see what calibration changed at nine specific positions. The converter ZIP includes a small Python program, source metadata, and Windows, macOS and Linux launchers. Extract it, then open its README for the three pinned R2 recording downloads and the setup command for your system. The first trial from sub-13 is one complete example. [Download the R2 converter](NeuroTranslation-IACKD-R2-Converter.zip) · [Open the browser replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay)

In the browser choose **Import a trial**, select your local JSON, then **Compare estimates**. Select hand history alone or hand history plus EEG to see tracked position alongside the fixed and personally calibrated estimates. The table of errors uses the same positions for all four models. The full-trial check matches the archived clock and four source signals. A clipped window can describe the rows you supplied. Only a complete, eligible trial has the support used in the published study.

## Run it

Use Python 3.13 and install the pinned requirements in a virtual environment. The launchers forward the same arguments as `python run.py`. Open a terminal in this folder. On Linux use `./Run-Linux.sh`, on macOS use `./Run-macOS.command`, or on Windows use `Run-Windows.cmd` from Command Prompt. With no arguments, each launcher opens the command help. Set `PYTHON` to the virtual environment's Python path if it is outside your shell's active environment.

```sh
python -m pip install -r requirements.txt
python -m unittest -v
python fetch_inputs.py --role CALIBRATION --output ../iackd-r1
python run.py calibrate --input ../iackd-r1 --output ../new-state.json
python fetch_inputs.py --role EVALUATION --output ../iackd-r2
python run.py evaluate --input ../iackd-r2 --state ../new-state.json --state-sha256 YOUR_CALIBRATION_SHA256 --output ../new-result.json
```

Replace `YOUR_CALIBRATION_SHA256` with the hash printed by `calibrate`. The study selects only the six file versions described in `SOURCE.json`. The downloader verifies the returned version, byte length and SHA-256. Both commands require an unused output path and check the exact input hashes again. The archive stays with OpenNeuro. The experiment outputs model corrections, error summaries and support counts. End-to-end execution was verified on Linux. [Calibration coefficients](CALIBRATION-STATE.json) · [OpenNeuro release and license](https://doi.org/10.18112/openneuro.ds006840.v1.0.0)
