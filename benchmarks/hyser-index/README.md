# Forecasting the index-finger sensor

Give the model 400 ms of recent index-finger voltage and ask what the sensor will read twelve ticks later. Across both recording days in the four-person development set, the force-history model gave **14.35 mV** mean absolute error. Adding aligned forearm surface EMG gave **14.46 mV**. Two participants improved and two did worse. Four other participants remain reserved by the study design.

[Open the interactive trial reader](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) · [Download the reader for Windows, macOS or Linux](downloads/Hyser-Index-Voltage-Reader.zip) · [Results, days and timing controls](RESULTS.md) · [Frozen protocol](PROTOCOL.md)

## Use the model

The browser opens the original Random-task WFDB files without sending them anywhere. Use a force pair alone, or include the matching raw forearm recording from the same person, day and trial. Loading the invented example needs no recording.

For Python, the [reference implementation](hyser_index.py) uses NumPy. Supply the 25-second trial as a 51,200 × 256 raw forearm array in header-scaled volts and a length-2,500 array of the named index force channel in volts. `predict_trial(raw, force, TICKS, weights)` uses the two shared fits in [predictors.json](predictors.json) and returns voltages for the requested cutoffs. [The scoring code](study.py) contains the person-held-out and known-person comparisons. The [aggregate record](RESULTS.json) includes the uncertainty estimates and both days. Individual recordings are available from the source database.

Contains information from Jiang, Dai, Liu and Fan’s Hyser 2.0.0 database, made available under the Open Data Commons Attribution License 1.0. [PhysioNet](https://doi.org/10.13026/hxan-pe94) · [License](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [Original study](https://doi.org/10.1109/TNSRE.2021.3082551)

## Can yesterday’s recording help today?

A separate experiment compares the shared forecast with two adjustments, one fitted on the same person’s first day and one fitted on a different person’s first day. Both are evaluated on the same second-day voltages. The four development participants had already been scored in the original Hyser study. [Read the prospective calibration protocol](crossday/PROTOCOL.md).
