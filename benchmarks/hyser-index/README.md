[The studies](../README.md) › Studies 14 to 17 · One finger

# The finger sensor's own history was the forecast to beat

Give a model 400 ms of the index-finger sensor's recent voltage and ask what it will read 120 ms later. On both recording days of four test people, a straight-line fit on that history missed by **14.355 mV**. With the forearm's surface EMG added, it missed by **14.457 mV**: two people did better and two worse. Four more people were set aside when the dataset was split, and their recordings are unopened.

The main score in these four studies is the plain average miss (mean absolute error), in millivolts of the sensor's output; the dataset gives no conversion to newtons. Some tables also give the measure that punishes large misses (root mean squared error). EMG is electrical activity of muscle, picked up on the skin: a recording of muscle, not of nerve. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small.

- [Study 14 · One finger: muscle signal](RESULTS.md): the result in full, with both days and the timing controls.
- [Study 15 · One finger: next-day adjustment](crossday/README.md): a correction fitted on the person's first day and scored on their second. On the four test people the unchanged shared forecast stayed ahead with and without EMG, though a correction from the person's own first day beat one taken from another person's.
- [Study 16 · One finger: the other four fingers](whole-hand/README.md): the other four finger sensors lowered the average error from 14.355 to 14.161 mV in the four test people, though for only two of them, and raised it from 16.854 to 16.915 mV in the twelve people the fit was made on.
- [Study 17 · One finger: new task](prescribed/README.md): on prescribed finger combinations, five finger histories beat one, and simply repeating the last index reading beat both on the average miss. The five-history fit had the smallest error on the measure that punishes large misses.

[Open the interactive trial reader](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) · [Download the reader for Windows, macOS or Linux](downloads/Hyser-Index-Voltage-Reader.zip) · [The plan](PROTOCOL.md)

## Use the model

The reader opens the dataset's original Random-task files (WFDB format) without sending them anywhere. Use a force pair alone, or add the matching raw forearm recording from the same person, day and trial. The invented example needs no recording. In the reader, **Finger sensor context** shows the other fingers up to the cutoff, and **Score trial** compares the three forecasts of study 16 across all 450 cutoffs of the trial you opened, or the four forecasts of study 17 on a prescribed-combination trial.

For Python, the [reference code](hyser_index.py) uses NumPy. Give it the 25-second trial as a 51,200 × 256 array of raw forearm EMG in volts, scaled by its header, and a 2,500-sample array of the named index force channel in volts. `predict_trial(raw, force, TICKS, weights)` uses the two shared fits in [predictors.json](predictors.json) and returns voltages for the cutoffs you ask for. [The scoring code](study.py) holds the comparisons on people left out of the fit and on people inside it. The [results file](RESULTS.json) has the ranges and both days. The recordings themselves come from the source database. [Score original session folders with Python](SCORE-SESSION.md) · [The five-finger models' inputs and weights](whole-hand/PREDICTOR.md) · [The plan for the new task](prescribed/PROTOCOL.md)

Contains information from Jiang, Dai, Liu and Fan’s Hyser 2.0.0 database, made available under the Open Data Commons Attribution License 1.0. [PhysioNet](https://doi.org/10.13026/hxan-pe94) · [License](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [Original study](https://doi.org/10.1109/TNSRE.2021.3082551)
