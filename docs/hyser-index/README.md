# Index-finger voltage forecast

Extract the ZIP, then use **Open Hyser on Windows**, **Open Hyser on macOS** or **Open Hyser on Linux**. You can open `index.html` directly in a browser. The reader starts with an invented trial and runs on your device.

## Try a recording

1. Choose one original `random_dataset/subjectNN_sessionD` folder from the [Hyser 2.0.0 release](https://physionet.org/content/hd-semg/2.0.0/), or use the matching-files selector.
2. For each trial, use the paired `random_force_sample1.hea` and `.dat` files, changing the final number for trials 2 through 5. Add `random_raw_sample1.hea` and its `.dat` from the same participant, session and trial for the muscle-assisted forecast. The record names repeat across sessions. Keep the source folder together.
3. Select a trial, then move the cutoff with the slider or the arrow keys. **Reveal the later sensor reading** displays the sensor voltage twelve ticks after cutoff and each fitted model’s signed error.

The line traces the index sensor's recent voltage. A filled diamond marks the force-history forecast. A filled square marks the forecast that also uses forearm activity. The outlined diamond and square show the corresponding personalized forecasts. Reveal the later reading to add its circle. The tables show the individual voltage samples and the RMS from each 64-electrode grid. ED and EP are the distal and proximal extensor grids. FD and FP are the distal and proximal flexor grids. Each grid samples a region of the forearm.

The reader checks record names, sampling rates, channel order, lengths, initial samples and WFDB checksums. It subtracts the channel baseline from each signed 16-bit count, then divides by the channel gain to give volts. Files and fitted coefficients stay in memory on this page. The package contains the population weights and invented examples. To check your copy of the data against the publisher’s cryptographic record, use the checksum list distributed by PhysioNet.

## See what the other fingers were doing

Choose **Finger sensor context** and open a Random-task force pair, a session folder or the invented trial. Move the cutoff. The four smaller plots show the thumb, middle, ring and little finger sensor readings from 400 ms before cutoff through the cutoff itself, in volts on a shared scale. The table gives each sample and marks gaps.

The same mode opens Hyser’s prescribed N-DoF task. Open one `ndof_dataset/subjectNN_sessionD` folder or select complete force pairs such as `ndof_force_combination1_sample1.hea` and its matching `.dat`. The picker labels all available combinations (1 to 15), repetitions (1 or 2) and whether the instructions cued the index finger. A cue tells you what the participant was asked to do. An uncued index sensor can still record voltage. With loose files the browser can match stems, but the session is unknown. Keep each selection to one task and use the original folder to retain the session label.

If this copy includes the pooled finger-context models, the diamond compares an index-only forecast with the triangle's forecast from all five histories. The outlined amber circle uses the index history plus each other finger’s voltage at cutoff and a straight-line slope fitted over that finger’s last 41 readings. All three forecast the index sensor 120 ms after cutoff. A gap in another finger’s history leaves the index-only forecast available. A copy without those fitted weights displays the earlier force-history forecast and still shows all available sensor traces. This mode uses the force pair alone. The two-day fit remains in its own mode.

Click **Score trial** to see how those forecasts fare across the opened trial. Each model is compared with the later index reading at the same 450 cutoffs, from 1.40 to 23.85 seconds. The table gives mean absolute error (MAE), root mean squared error (RMSE) and the signed reduction in MAE from the index-history baseline, all in millivolts. Positive means the extra inputs lowered MAE. Negative means they raised it. The cutoff-level reveal is a separate control.

For N-DoF, the table also asks how well you would do by repeating the last index reading at every cutoff. The fitted forecasts use the same weights learned on the Random task. The cue stays out of their inputs. The browser checks the WFDB header, starting samples and per-channel sums. The [prescribed-task study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/hyser-index/prescribed) additionally verifies publisher SHA-256 hashes and compares participants using repetition 1. The browser scores only the selected trial, including repetition 2 when you choose it.

If any cutoff is missing a history sample or a later index reading, the reader counts the complete cutoffs and leaves the trial unscored. The [Random-task Python scorer](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/hyser-index) applies the same complete-trial rule with `--whole-hand`. Its `--example --whole-hand --trial 1` case uses the same invented voltages as this mode. Scores stay on this device and clear when you change trials, change modes or clear recordings. The pooled models may have seen the participant during fitting.

## Fit on one day and test on the other

**Try two invented days** runs the whole comparison using generated force traces. It fits the adjustment on five invented Day 1 trials and opens a different trial for Day 2. Reveal the later reading to see how the adjustment changed the trial’s errors.

1. Switch to **Personalize across two days** and choose one original `subjectNN_session1` folder. All five force pairs are required, with all 450 scheduled windows in each trial. The model can also adjust the surface EMG forecast when all five Day 1 raw pairs and their scheduled windows are available.
2. Choose the original `subjectNN_session2` folder for the same participant. The browser checks the folder labels, which the WFDB headers do not repeat. Keep the publisher’s filenames and folder layout. The labels alone cannot authenticate files that someone has renamed or copied. Use **Population models** for a set of loose files or a folder whose original labels are unavailable.
3. Click **Fit from Day 1**. Each model learns a voltage offset and a gain correction using only Day 1. The population weights stay fixed. Switch Day 2 trials freely once the fit is ready. Changing either source folder or leaving this mode discards the fit. **Clear recordings** clears both sources, cancels pending reads and fitting, and leaves you in two-day mode.
4. After checking the population and adjusted predictions, select **Reveal Day 2 reading and trial errors**. The selected cutoff gives signed error in volts. The table reports mean absolute error (MAE) and root mean squared error (RMSE) in millivolts for that Day 2 trial. Each comparison uses its own matched cutoffs and reports how many survived any missing force, target or EMG sample. A higher error means the adjustment made that trial’s forecast worse.

The Day 2 result answers a question about the opened trial. The participant may already be in the population fit, and selected cutoffs overlap in time. A trial result alone gives neither an independent-person evaluation nor a test of the timing of a live system.

## How the two models performed

On 40 trials from four development participants, force history gave 14.35 mV mean absolute error. The model with aligned forearm EMG gave 14.46 mV. Two people improved and two did worse. Cross-validation on 12 training participants also favored the force-history model. Four final participants remain reserved. The downloadable forecasts use the shared fit from the training participants.

The [cross-day study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/hyser-index/crossday) asks a different question. On 20 Day 2 trials from the same four development participants, force history averaged 14.912 mV of absolute error across people. Fitting to each person’s Day 1 raised this to 15.091 mV. Fitting to another person’s Day 1 raised it to 15.401 mV. With forearm EMG, the corresponding numbers were 14.903, 15.122 and 15.496 mV. These comparisons use two donor pairs. The reader defaults to the population models and lets you check how a local adjustment behaves on an individual trial.

## What goes into a forecast

The population force model uses 41 readings through cutoff, spaced 10 ms apart on the 100 Hz force clock. The second model adds the logarithm of surface EMG RMS in four 100 ms bins ending 20 ms before cutoff. It takes half-open intervals on the separate 2,048 Hz EMG clock. Each bin contributes the power from the four ordered electrode grids and a combined value. Both models predict a change from the current index sensor voltage. The target is the released reading 120 ms later. The reader offers 450 cutoffs from 1.40 to 23.85 seconds in 50 ms steps. The trial edges and timing controls are described in the [frozen protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/3e111e9f9bd0dde3ccb01317eb2a301dc57f27f7/benchmarks/hyser-index/PROTOCOL.md).

Let `c` be the current voltage, `p` the population forecast, and `y` the later Day 1 reading. Divide the population change `p − c` by its root mean square over Day 1 (minimum 10⁻¹² V) to give `q`. Solve for an offset `a` and gain coefficient `b` by minimizing the mean squared error in `y − p − a − bq` with the fixed penalty `0.1(a² + b²)`. On Day 2 use the same Day 1 scale in `p + a + bq`. Day 2 readings enter the score only after you reveal them.

The systems shared a trigger when each task began. The authors describe filtering the force trace for their benchmark; the order and delay of any processing applied before the public force file was written remain unverified. These forecasts concern recorded sensor voltage. Their accuracy does not establish a live physiological lead or a force calibration in newtons.

Contains information from Jiang, Dai, Liu and Fan’s *Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings* (Hyser, PhysioNet 2.0.0), made available under the Open Data Commons Attribution License 1.0. [Source and citation](https://doi.org/10.13026/hxan-pe94) · [ODC-By 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [Acquisition study](https://doi.org/10.1109/TNSRE.2021.3082551)
