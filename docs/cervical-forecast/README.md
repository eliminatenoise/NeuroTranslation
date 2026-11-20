# Forecast a neck electrode reading

Extract the whole ZIP. Open **index.html** or use **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. Keep the folders next to the page. The reader runs offline in a browser. Its links to the original research need a connection.

A recorded pulse marks time zero. In the experiment, one skin electrode picked up voltage over the median nerve at the armpit and another measured neck voltage. The fitted models ask whether the early arm reading helps predict the later change in neck voltage. This experiment has no movement measurement.

## Try the model

Choose **Armpit · Biceps**. Move the voltage slider and watch the two forecasts. Only one model gets the armpit signal. Switch to **Neck · SC6** and change the same early window. Both models now receive the changed dot. The dot table gives an accessible text version of the chart. You can also select the dot by time, enter a voltage directly or change the event’s place in the run. Restore example returns every input to its initial value.

Each dot averages five samples over half a millisecond. The reader starts with invented values around each fitting-group channel mean. The slider covers three training standard deviations on either side. Typing a value can take the example further beyond the fitting data. The models return a voltage for the supplied inputs. The study has no measured outcome for invented combinations.

## What the numbers mean

The predicted neck voltage change uses 12 to <14 ms after the pulse minus the average from −15 to <−10 ms. The early input ends before +8 ms. All electrodes share a 10 kHz clock but keep their own voltage references. The armpit electrode is labelled Biceps in the source even though the study used it for a surface nerve recording.

In development, each fold left out one of four people and fitted to the other three. All 320 events contributed to the four validation folds. The full Transformer’s mean absolute error was 18.200 µV, compared with 19.696 µV without the armpit reading. Fitting with the armpit signal from a different event gave 16.994 µV. A linear model without that channel scored 8.756 µV. The comparison failed the prespecified development criterion for a benefit from correctly paired armpit readings. Surface voltages can share noise, stimulus effects and distant electrical activity. A forecast cannot trace a signal’s path through the spinal cord. [Protocol](method/protocol.md) · [Development results](method/development.json)

On the six new people (480 events), the Transformer's average error was 23.283 µV with the armpit reading and 24.670 µV without. Giving the same fitted Transformer a different event’s armpit reading yielded 22.359 µV. Only one of six people had lower error with the correctly paired signal in both comparisons. Repeating the last neck voltage change gave 8.087 µV. The separate robust linear fit scored 9.646 µV with the armpit signal and 7.773 µV without it. Both families fell short of their prespecified incremental-signal criteria. This is one acquisition study. [New-person assessment](method/assessment.json)

A separate earlier check measured +1.70225 µV over eight events from one person. It used a shorter neck baseline. This participant also contributed to model development. [Recorded aggregate](method/measured.json)

## Inspect or rebuild

The page reads local scripts so it works from an extracted folder without a server. The JavaScript predictor accepts sixteen rows of five half-millisecond means. Its `toTokens` function converts 50 baseline rows and 30 early rows of raw microvolt readings into that representation. The event index is zero based, 0–79. Each synthetic parity case includes both expected PyTorch predictions and the tolerance in microvolts.

To regenerate the bundled data script, checksums and archive from this folder with Python 3, run `python build.py --zip ../cervical-forecast-offline.zip`. On systems with sha256sum, run `sha256sum -c SHA256SUMS` to verify the extracted files. [Weights](method/weights.json) · [Browser inference](src/predict.js) · [Synthetic parity cases](method/parity.json) · [Source hashes](method/provenance.json) · [Credits and licence](NOTICE.md)
