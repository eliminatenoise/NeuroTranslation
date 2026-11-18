# Inspect recordings in the browser

To read a trace on its own clock, open **Inspect original samples** below it. Use the slider or arrow keys to see each stored timestamp and value. You can inspect recordings with different clocks this way.

Open the [experimental data companion](https://eliminatenoise.github.io/NeuroTranslation/preview.html) to import JSON or CSV, inspect samples and their declared metadata, and align recordings that declare compatible subjects, recordings and clocks. The built-in example contains invented signals so you can try the controls without supplying a recording.

The companion does not run a trained NeuroTranslate model or predict missing signals. It keeps file processing in your browser and has no endpoint for uploading recording contents. A matching label or clock name cannot establish that two observations were acquired together; import checks cannot authenticate data or grant permission to use them.

Filtered or transformed recordings can declare `derived` as their origin. An input file can identify the original stream in its provenance. The metadata report flags a missing source declaration.

Move the **Aligned time** slider to put every trace at the same point on the declared clock. Each readout keeps the stream's unit, identifies original and resampled values and explains any gaps. Try 1.5 seconds in the example to see an interpolated displacement beside a missing force value.

The [build manifest](build-manifest.json) identifies the current browser build. See the [application source and usage](https://github.com/eliminatenoise/NeuroTranslation/tree/main/demo), [selected experimental papers](https://github.com/eliminatenoise/NeuroTranslation/tree/main/papers) and [historical unbuilt R11 manuscript source](https://github.com/eliminatenoise/NeuroTranslation/tree/main/papers/experimental/r11-source) for the wider research programme.

Project-owned code uses [CC0 1.0](LICENSE). Recordings, references and separately supplied assets keep their own rights; see [RIGHTS.md](RIGHTS.md). Work on NeuroTranslation has resumed alongside NeuroSurge and Interoceptomics. The data companion retains its stated experimental limits; preview availability does not establish a trained model or completed biological interface.
