# How far will the back sensor turn in a tenth of a second?

Both planned four-person tests are incomplete. One person's two files label a row as a buffer, so the original four-component check stops. The following design and training notes describe the method fixed before those files were opened. [Eligibility and the three-person descriptive results](ASSESSMENT.md)

A volunteer walks, then stands still. A sensor strapped to the back records its orientation. Two patches of 32 electrodes record surface voltage near C4 and L2. Can the patches tell us how far the sensor will turn in the next tenth of a second, once we know how far it has already turned? The recordings come from Experiment 2 of the dataset by Gracia Laso and colleagues, version 2, licensed CC BY 4.0. The authors describe the two tasks, the sensor setup and the limits of surface recording. [Dataset and attribution](https://doi.org/10.5281/zenodo.19065545) · [Study](https://doi.org/10.1038/s41597-026-07592-7)

Each forecast uses the previous tenth of a second and the instruction in force at the cutoff. Ten successive 10 ms bins describe recent changes in orientation and voltage. The orientation sensor updates internally at 100 Hz. The file stores its readings alongside the electrode samples at 2,000 Hz. We verify the stored clock in each trial. We normalize the four orientation values before measuring the shortest angle between the orientations at the cutoff and 100 ms later. A left turn and a right turn of the same size have the same answer, in degrees.

The Transformer receives the ten bins at once. Two attention heads can weight earlier bins differently for each prediction. The final bin supplies a correction to a simple forecast that carries the previous tenth of a second’s angular change forward. Training adjusts the projection, positions, attention, feedforward layers and output together. Each run learns one scalar forecast. Generating a sequence of movements, interpreting a sentence or recovering the rotation of a particular joint would require different targets and evidence.

## What the comparisons measure

Four people supplied two development trials each. We fit on three people and tested on the fourth, rotating the held-out person through all four positions. We then fit a final set of coefficients on all four. The test of new people uses that final fit after the scoring rules and coefficients have been sealed. The first development trial had already been inspected when the protocol was written.

We fit four Transformers with the same architecture, seed, training order and number of updates. Each receives the task and motion. Three runs also receive the upper patch, the lower patch or both. A missing patch has its features set to zero after standardization in both training and scoring. The control for timing uses the trained two-patch model. It pairs each window with both voltage histories from a different time in the same person, trial and task. The donor's complete history and target interval must be disjoint from the recipient's. This control can draw on a later donor and serves only as an offline comparison.

A zero-turn forecast, the previous angle carried forward, a task-specific training median and a linear motion model supply four simpler comparisons. For each person, we combine their two trials, calculate the mean absolute error separately for walking and standing, then give the two errors equal weight. Each person contributes equally to the stage mean. The descriptive 95% intervals resample people, keeping each person’s paired results together. Four people give little resolution for conclusions about a wider population. Muscle activity, cardiac activity and motion artifact can all contribute to the recorded voltage. These measurements cannot identify a spinal neural generator. The earlier wrist-event voltage study involved different people and a different outcome. Its results stand separately.

## What happened in the four development folds

Adding both patches increased the person-balanced error from **0.271° to 0.302°**. The model using motion and task alone did better on all four people. The mean increase was 0.031°, with a descriptive person-resampling interval of 0.018° to 0.052°. Swapping in voltage from a different time gave an error of 0.299°. None of the five prespecified tests for an added benefit from correctly timed voltage passed. These results cover the four development people. The final coefficients are frozen for a separate four-person assessment.

Each task contributed 1,536 eligible targets across the eight recordings. All eligible histories and target endpoints passed the finite-sample checks. The table gives person-averaged mean absolute errors in degrees. A smaller number means the predicted angle was closer to the measured angle.

| Forecast | Standing | Walking | Balanced |
| --- | ---: | ---: | ---: |
| Zero turn | 0.263 | 1.236 | 0.750 |
| Previous 100 ms angle | 0.121 | 0.508 | 0.315 |
| Training median for the task | 0.212 | 0.508 | 0.360 |
| Linear model, motion and task | 0.129 | 0.425 | 0.277 |
| Transformer, motion and task | 0.126 | 0.416 | 0.271 |
| Transformer, upper patch added | 0.147 | 0.451 | 0.299 |
| Transformer, lower patch added | 0.125 | 0.422 | 0.274 |
| Transformer, both patches added | 0.162 | 0.442 | 0.302 |
| Both-patch model, different-time voltage | 0.158 | 0.440 | 0.299 |

## Reproduce a prediction

`model.json` contains coefficients for all four trained models, the training-set scaling factors, the linear and median baselines, and three synthetic reference cases. Those artificial inputs let a reader check an implementation without a volunteer’s recordings. `portable.py` performs inference with NumPy alone.

```python
import json
import numpy as np
from portable import predict

with open('model.json') as file:
    model = json.load(file)
x = np.asarray(model['parity']['tokens'])
print(predict(model, x, 'full'))  # degrees, one forecast per synthetic case
```

`extract.past_tokens` accepts 201 consecutive four-component orientations through the cutoff, 200 raw samples in µV from each of 32 upper and 32 lower electrodes through the same cutoff, and source task code 611 or 621. The voltage history starts one stored sample after the orientation history starts. The function returns ten rows. Each row has the angular change within the bin, the angular change since the history began, the walking indicator and three voltage features at each site. They are the across-electrode median of each electrode’s temporal standard deviation, the across-electrode median of the root-mean-square successive voltage difference, and the temporal standard deviation of the across-electrode median. Each voltage feature is transformed as `ln(1 + value_in_µV)`. The exported coefficients take these nine features in the order listed in `model.json`.

`protocol.json` fixes the split, preprocessing, controls and decision thresholds. `score.py` computes participant-balanced errors and tests those thresholds. `development.json` contains the aggregate development results. To repeat training with NumPy, SciPy and PyTorch, supply the eight selected development MAT files and their checked source receipts under `Sxx/trial-NN.mat` and `Sxx/trial-NN.source.json`. A receipt identifies the publisher archive, exact original member name and locally verified SHA256. When preparing these from the publisher’s full ZIP downloads, verify each full archive against the checksum on Zenodo before extracting the named member and recording its SHA256. The minimal receipt fields are `archive.name`, `member` and `member_sha256`. The input files remain with the source dataset. The development and assessment programs take separate paths.

```sh
python -B test_back_rotation.py
OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B fit.py PATH_TO_DEVELOPMENT --out NEW_OUTPUT --threads 1
```

The extraction and independent assessment programs require SciPy and NumPy. `assess.py` checks the specialist seal before scoring the designated four assessment people. Private person-level diagnostics and fold coefficients belong outside the public package. The published results contain aggregate errors and comparisons.
