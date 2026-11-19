# Index-finger voltage forecast

Open `index.html` or use **Open Hyser on Windows**, **Open Hyser on macOS** or **Open Hyser on Linux** from the extracted ZIP. The reader starts with an invented trial. It runs both trained models locally. On a system with a graphical desktop, the dedicated launcher opens the reader in your default browser.

## Try a recording

1. Choose one original `random_dataset/subjectNN_sessionD` folder from the [Hyser 2.0.0 release](https://physionet.org/content/hd-semg/2.0.0/), or use the matching-files selector.
2. For each trial, use the paired `random_force_sample1.hea` and `.dat` files, changing the final number for trials 2 through 5. Add `random_raw_sample1.hea` and its `.dat` from the same participant, session and trial for the muscle-assisted forecast. The record names repeat across sessions. Keep the source folder together.
3. Select a trial, then move the cutoff with the slider or the arrow keys. **Reveal the later sensor reading** displays the sensor voltage twelve ticks after cutoff and each fitted model’s signed error.

The solid line gives the index sensor history. The diamond is the force-history forecast. A small square adds the forecast using forearm activity when a raw EMG pair is present. Revealing the target adds its open circle. The tables expose the individual voltage readings and RMS values from each 64-electrode grid. ED and EP denote the distal and proximal extensor grids. FD and FP denote the distal and proximal flexor grids. These are recording locations. They do not isolate individual muscles.

The reader checks record names, original sampling rates, channel labels, lengths, initial samples and WFDB checksums. Each signed 16-bit count is converted to volts with its own channel baseline and gain. Files you open remain on this device. To verify a download against the publisher’s cryptographic record, use the checksum list distributed by PhysioNet. No participant recording is included in the ZIP.

## How the two models performed

On 40 trials from four development participants, force history gave 14.35 mV mean absolute error. The model with aligned forearm EMG gave 14.46 mV. Two people improved and two did worse. Cross-validation on 12 training participants also favored the force-history model. Four final participants remain reserved. The downloadable forecasts use the shared fit from the training participants.

## What goes into a forecast

The force model uses 41 readings through cutoff, spaced 10 ms apart. Their first-to-last span is 400 ms. The second model adds the logarithm of surface-EMG RMS in four 100 ms bins ending 20 ms before cutoff. Each bin contributes activity from the four ordered electrode grids and their pooled energy. Both models predict a change from the current index-sensor voltage. The target is the released reading 120 ms later. The reader offers 450 cutoffs from 1.40 to 23.85 seconds in 50 ms steps. The trial edges and earlier-window controls are described in the [frozen protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/3e111e9f9bd0dde3ccb01317eb2a301dc57f27f7/benchmarks/hyser-index/PROTOCOL.md).

The systems shared a trigger when each task began. The authors describe filtering the force trace for their benchmark; the order and delay of any processing applied before the public force file was written remain unverified. These forecasts concern recorded sensor voltage. Their accuracy does not establish a live physiological lead or a force calibration in newtons.

Contains information from Jiang, Dai, Liu and Fan’s *Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings* (Hyser, PhysioNet 2.0.0), made available under the Open Data Commons Attribution License 1.0. [Source and citation](https://doi.org/10.13026/hxan-pe94) · [ODC-By 1.0](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [Acquisition study](https://doi.org/10.1109/TNSRE.2021.3082551)
