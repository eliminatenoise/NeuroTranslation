# Inspect recordings in the browser

To read a trace on its own clock, open **Inspect original samples** below it. Use the slider or arrow keys to see each stored timestamp and value. You can inspect recordings with different clocks this way. After aligning traces, choose **Show original samples** to return to those readings.

Open the [experimental data companion](https://eliminatenoise.github.io/NeuroTranslation/preview.html) to import JSON or CSV, inspect samples and their declared metadata, and align recordings that declare compatible subjects, recordings and clocks. The built-in example contains invented signals so you can try the controls without supplying a recording.

In **Palm replay**, import a trial JSON and choose **Compare estimates**. For an R1 trial, compare palm estimates with and without EEG. For an R2 trial, choose the inputs and compare the original model with the one calibrated on that person's R1. The sample table uses the same positions as the chart. You can download the full numerical results. [Prepare R1](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/scalp-eeg-palm-history#replay-a-recorded-trial) · [Prepare R2](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/scalp-eeg-personal-calibration#replay-a-second-recording)

Matching labels and clock names describe how the files relate. Establishing that two recordings were acquired together takes evidence from their original source.

The personal calibration comparison gives the errors on the second of two archived recordings after the first was used to adjust the model. Choose a participant to inspect their trial counts and compare hand history with and without EEG. [Explore the calibration results](https://eliminatenoise.github.io/NeuroTranslation/index.html#personal-calibration)

[Replay a wrist movement](wrist-replay/). Choose a wrist axis to compare measured study errors at six times after a target appeared. Open a locally converted development trial to see what each of the six fitted temporal models predicted.

Two downloadable experiments work with a different task. A wrist exoskeleton recorded two angles while participants moved a cursor. One study tests a temporal model with and without scalp EEG. The other asks what surface EMG adds to a linear forecast of the same movement. [Wrist forecasting model](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/wrist-pointing-temporal) · [Surface EMG study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/wrist-pointing-muscle)

Filtered or transformed recordings can declare `derived` as their origin. An input file can identify the original stream in its provenance. The metadata report flags a missing source declaration.

Move the **Aligned time** slider to put every trace at the same point on the declared clock. Each readout keeps the stream's unit, identifies original and resampled values and explains any gaps. Try 1.5 seconds in the example to see an interpolated displacement beside a missing force value.

The [build manifest](build-manifest.json) identifies the current browser build. See the [application source and usage](https://github.com/eliminatenoise/NeuroTranslation/tree/main/demo), [selected experimental papers](https://github.com/eliminatenoise/NeuroTranslation/tree/main/papers) and [historical unbuilt R11 manuscript source](https://github.com/eliminatenoise/NeuroTranslation/tree/main/papers/experimental/r11-source) for the wider research programme.

Project-owned code uses CC0. Recordings, references and separately supplied assets retain their own licences. [Code licence](LICENSE) · [Recording and asset rights](RIGHTS.md)

[Forecast a wrist turn with forearm EMG](wrist-forearm/). Open an original development ZIP, select a block and trial, and compare measured wrist angles with three forecasts. You can explore invented inputs without a file.

[Daily-activity wrist estimates](daily-wrist/) compare task and elapsed time with seven forearm channels. Invented examples can be adjusted; a compatible supplied JSON window is evaluated locally.

In a separate pinch-lift experiment, phase-matched EEG from another trial did slightly better than the correctly paired EEG at forecasting grip force. [Read the WAY-EEG-GAL comparison and download the desktop forecast](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/way-grip-force/)

[Open the grip-force forecast](grip-force/) to change the cutoff on an invented grip or import a compatible local JSON window. The four models forecast the same measured quantity 120 ms beyond the cutoff on the recording clock.
