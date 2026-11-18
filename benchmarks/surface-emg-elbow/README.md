# Can surface EMG track an elbow angle across two people?

Bring your hand to your mouth five times. The elbow bends each time. Electrodes on the skin record the muscles’ electrical activity, while cameras follow markers on the arm. Could a model fitted on one person use the muscle recording to follow the other person’s elbow?

The fixed ridge model missed by **58.24° mean absolute error** on the held-out development recording. A single angle, the training-set mean, missed by **25.10°**. An average trajectory keyed to the recorded movement onset missed by **26.37°** and gave the lowest root-mean-square error. The ridge lost to both on every development repetition.

| Recording | Scored frames | Surface EMG ridge MAE / RMSE | Training mean MAE / RMSE | Onset template MAE / RMSE |
| --- | ---: | ---: | ---: | ---: |
| HS01. Left dominant arm, in sample | 2,591 | 21.41° / 26.24° | 34.72° / 36.82° | 4.51° / 7.96° |
| HS02. Right dominant arm, held-out development | 1,980 | 58.24° / 62.36° | 25.10° / 34.95° | 26.37° / 30.77° |

Participant and arm side changed together, so this comparison cannot explain the error by either one. The two baselines also answer different questions. The training mean uses no information about the development recording. The template is given its movement onset and uses the elapsed time to look up an angle learned from HS01. There was no duration matching or trajectory adjustment on HS02.


![Pooled elbow-angle root mean squared error in degrees. Training and development respectively: surface EMG ridge 26.2 and 62.4, training mean 36.8 and 35.0, onset trajectory 8.0 and 30.8.](elbow-angle-error.png)

## What went into each prediction

Both files come from Lucchetti and colleagues’ upper-limb dataset. We used all five marked hand-to-mouth movements in each file. The predictors are twelve channels of raw surface electromyography (EMG) in millivolts. The reference is the authors’ elbow flexion angle, stored as `ElbowFlx` in degrees with the source sign and joint coordinate system. To obtain this angle, the authors first processed the camera marker trajectories with a zero-phase 10 Hz low-pass filter and spline filling of short missing stretches. They then estimated the joint angle from the resulting coordinates. [Dataset paper and methods](https://doi.org/10.1038/s41597-025-06174-3)

For each angle frame at time *t*, compute the root-mean-square voltage per muscle channel over the inclusive interval from *t* − 90 ms to *t* − 40 ms. This turns a short stretch of alternating voltages into one amplitude per channel. The model learns how to weight those amplitudes using ridge regression with a fixed penalty of 0.01 on mean squared error. The scaling, coefficients and intercept all come from HS01. The onset template averages the eligible HS01 angles at each elapsed frame, interpolates internal gaps and holds the nearest endpoint outside its observed range. No HS02 row needed that endpoint rule.

The paper describes synchronized acquisition at 1,000 Hz for EMG and 125 Hz for the optical system. The analysis assumes equal origins within each stored task and maps each angle frame to the corresponding nominal EMG position at the 8:1 ratio. The HS01 and HS02 task array lengths differ from an exact 8:1 ratio by +28 and −69 EMG samples, respectively. All selected event bounds fit in both arrays. The nominal 40 ms lead describes the stored index mapping. A physical offset, drift, recording delay or time when the processed angle would be available online was not measured here.

The archive’s optically derived movement events determine which frames enter the score. Ridge receives only EMG amplitudes for those frames. Of 2,651 candidate HS01 frames and 2,040 HS02 frames, 60 in each file lacked sufficient in-movement history. There were zero missing target values in the selected movements. The pooled scores above weight all scored frames equally. [RESULT.json](RESULT.json) includes counts, errors by repetition, and averages over repetitions. Five repetitions from one development participant cannot establish population performance. HS03 is reserved and its recording was never opened.

## Run the comparison

Download the two original version-1 `.mat` files from Figshare and keep their filenames. They are distributed by the authors under CC BY 4.0. This companion uses them without modification and ships only code and aggregate results. [HS01](https://doi.org/10.6084/m9.figshare.28596026.v1) · [HS02](https://doi.org/10.6084/m9.figshare.28596038.v1) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

From this folder, put `HS01.mat` and `HS02.mat` in a folder called `data`. Use Python 3.14, as in the recorded Linux run.

**macOS or Linux**

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python run.py --hs01 data/HS01.mat --hs02 data/HS02.mat --output reproduced.json
```

**Windows PowerShell**

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
.venv\Scripts\python.exe run.py --hs01 data/HS01.mat --hs02 data/HS02.mat --output reproduced.json
```

The runner checks each file hash before reading the MATLAB structure. It writes JSON with the metrics and runtime details. Choose a new output filename to run it again. `python -m unittest -v test_baseline` in the environment runs the synthetic checks without the data files. Native execution was verified on Linux. The Windows and macOS commands use the same program and have not been run on those systems.

The fixed study plan is in [DESIGN.json](DESIGN.json) and the data IDs, role assignments and checksums are in [ASSETS.json](ASSETS.json). The released runner uses the terms **train reference** and **development** in its output and reports CPU affinity on systems that expose it. The original run and the released runner use the same numerical implementation.

To redraw the figure from the supplied aggregate results, install Matplotlib and run `python plot_baseline.py RESULT.json elbow-angle-error.png`.
