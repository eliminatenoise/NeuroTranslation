# Inspect recordings in the browser

Open the [experimental data companion](https://eliminatenoise.github.io/NeuroTranslation/preview.html) to import JSON or CSV, inspect samples and their declared metadata, and align recordings that declare compatible subjects, recordings and clocks. The built-in example contains invented signals so you can try the controls without supplying a recording.

The companion does not run a trained NeuroTranslate model or predict missing signals. It keeps file processing in your browser and has no endpoint for uploading recording contents. A matching label or clock name cannot establish that two observations were acquired together; import checks cannot authenticate data or grant permission to use them.

The existing R5 static build is preserved here, with its [build manifest](build-manifest.json). [Application source and usage](https://github.com/eliminatenoise/NeuroTranslation/tree/main/demo) describe its limits. The [R9 rendered papers](https://github.com/eliminatenoise/NeuroTranslation/tree/main/papers) and [R11 experimental manuscript source](https://github.com/eliminatenoise/NeuroTranslation/tree/main/papers/experimental/r11-source) develop the wider research programme. The companion is a data inspection tool, not evidence that the proposed model or biological interface has been completed.

Project-owned code uses [CC0 1.0](LICENSE). Recordings, references and separately supplied assets keep their own rights; see [RIGHTS.md](RIGHTS.md). Development remains paused while work focuses on NeuroSurge. Publishing this existing preview does not resume training or feature development.
