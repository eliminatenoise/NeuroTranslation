# Reproduce the wrist comparison

Open **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh** for the offline results. Each launcher opens the included HTML page with the system browser. Scoring the stored recordings requires Python, NumPy and CPU PyTorch. The original run used Python 3.13.15, NumPy 2.4.6 and PyTorch 2.14.1+cpu. In a separate Python environment install the versions in `requirements.txt`, using the CPU build of PyTorch for your system.

## Try the shape of a prediction

From the extracted folder, run the following command. It uses invented angles and illustrative weights. The last measured angles are 2° and −1°; adding example changes of 0.25° and −0.50° gives 2.25° and −1.50°. This checks the model interface.

```sh
python -B reproduce.py example
```

## Rebuild the measured result

Obtain the six named ZIP files from the original source and put them together in a local `archives` directory. The filenames, Figshare file IDs, byte counts and SHA-256 values are in `study.json`. Keep each ZIP intact. Use an empty output directory on a local filesystem supporting hard links. The commands below write derived subject tables, fitted models and individual predictions into your own `work` directory. Keep those outputs under the original data terms. [Original dataset, version 3](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Six source-file identities](study.json) · [Rights](NOTICE.md)

```sh
python -B reproduce.py prepare --archives archives --work work
python -B reproduce.py fit --work work
python -B reproduce.py score --work work
```

The first command checks the six archives by hash. For the sixteen electrical channels it verifies electrode names, units, storage layout and state markers. It then compares the original two encoder columns, word for word, in the electrical and motion tracks. The resulting feature and target tables must match the combined digest of the original study's 11,274 rows. The second command creates 27 distinct convolutional networks and 12 linear corrections. The third checks the complete fit inventory and prints the aggregate results. Your detailed local numerical output is `work/scores.json`; compare its equal-person, per-axis and cue-time scores with the included aggregate `results.json`. Dependency and numerical-backend changes may change the final digits. An interrupted fit leaves a named intent beside its checkpoint; preserve evidence and inspect the affected fit before repeating work.

The portable extraction code reproduced the complete original feature and target table on Linux. Saved study weights were used to verify the portable predictor and scoring calculations without repeating the real training run. The training functions and fold sequence match the reviewed study source. Native Windows and macOS runs have not been observed.

## What goes into one row?

Take targets at 384, 512, 640, 768, 896 and 1,024 stored ticks after the movement cue. At 512 Hz these target times span 0.75 through 2.00 seconds. Stop the input 128 ticks before each target and read the 256 ticks ending there. Divide the window into sixteen groups of sixteen ticks. For each group, take its two mean encoder angles relative to the last measured angles. Subtract the R electrode from the L electrode in each forearm pair M1 to M4, then take the square root of the mean squared difference within the group. Each electrical feature is in microvolts. Append the two last absolute angles and six indicators for the requested cue offset. The cue specifies time. Target direction and scalp values supply no predictor features. The source reports a nominal encoder update frequency of 100 Hz.

Require one complete trial to contain all six valid target and history windows. Preserve its source block, trial, cue, slot and target row. One of 48 planned task blocks was absent, leaving 1,880 recorded trials. One trial had an invalid encoder measurement. Every forecast and control uses the same 1,879 trials. Eligibility includes the original shared finite-value checks for the recorded electrical channels.

## Fit without using the held person

1. Hold out one person. Use the other five for all learned quantities. The network normalizes each input channel across all history bins and fitting rows. It separately normalizes the two absolute angles and the measured target-minus-anchor change, using fitting-row means and population standard deviations. Replace any exact zero standard deviation with one.
2. Fit a motion network and a joint motion-and-EMG network. Each applies two one-dimensional convolutions, each of width 16 with three-sample kernels and rectified activations. Flatten the result, append the two normalized absolute angles and the six timing flags, apply a 32-unit rectified layer and predict the two changes. Both models use seed 17 and begin with zero predicted change in degrees. Train for 30 epochs with AdamW, learning rate 0.001, weight decay 0.0001, batch size 128, squared error, equal sampled-person probability and equal row probability within person. The two networks use the same seeded batch order. Restore the measured anchor before scoring.
3. For each of the five fitting people, obtain a motion-only prediction from a four-person network that excluded them and the outer held person. Across all six outer folds, fifteen unique four-person fits produce these inner predictions. Fit two ridge regressions to their remaining errors in degrees. Each uses 32 flattened angle means, the two last angles and the six timing indicators. The EMG regression adds 64 amplitudes in chronological order. Standardize each continuous feature column using only the five fitting people. Give each person equal total weight. Add a penalty of 0.01 times the sum of squared continuous coefficients to the weighted mean squared error. Use six unpenalized time intercepts, with no separate intercept. At outer evaluation, add the predicted correction to the five-person motion forecast.
4. For the wrong-trial control keep the held motion, anchor, cue time and target. Draw a full EMG window from one of the five fitting people with the same block and slot. For a zero-based source trial number j, pick fitting person j modulo the number with that block, in original person order. Within that person's sorted eligible trial list pick position (j+1) modulo the list length. The other control uses the held row's own EMG bins in reverse time order. Apply both to the fitted correction and joint network. Only the EMG changes.
5. Compute each person's mean squared error separately for the two wrist axes, giving every complete trial and each of its six target times equal weight. Average the twelve mean squares and take the square root. The primary comparison is the error change when EMG is added to the motion-only correction. Report both corrections against the original motion CNN. Dropping one person's scores from this summary measures influence; it leaves the fitted models unchanged. All six participants contributed to earlier method development. Confirmation would require a separately reserved cohort.

[Exact model fitting](models.py) · [Eligibility and features](features.py) · [Controls and scoring](score.py) · [All aggregate results](results.json)

The original plan for the six-person comparison is included verbatim so its checksum can be checked against `study.json`. [Prespecified study protocol](protocol.md)
