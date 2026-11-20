# NeuroTranslator, the browser app

This folder is the source of NeuroTranslator, the project's browser app, at [eliminatenoise.github.io/NeuroTranslation/index.html](https://eliminatenoise.github.io/NeuroTranslation/index.html).

The app does three things with the recordings you give it. It shows each one on its own clock. It lines several up on a shared clock. And it replays a palm trial against the fitted models of the two palm studies.

Your files stay in the browser. The app has nowhere to send them.

Its name is close to that of NeuroTranslate 0.0, the general model this project is building, but the model is not in the app; it has [a folder of its own](../models/neurotranslate-0.0/).

## Build and test

```
npm test
npm run build
```

`npm test` runs the checks on invented data. `npm run build` writes `dist/`: an `index.html`, its scripts and data under names that carry the build's hash, and a manifest. Serve that folder over HTTP. The app has no dependencies, so there is nothing to install.

## Give it a file

**JSON.** Download the example from the app to see a complete file. It holds `schemaVersion: 1`, one `dataset` object and a `streams` list. The dataset says what was recorded: an ID, a name, the organism, the subject, the recording, the task, the clock (`timebase`), where it came from, its licence, and whether it was used to fit a model or held back to test one (`split`). Each stream gives an ID, its kind (`modality`), a label, a unit, an origin, timestamps in seconds and values. A value may be `null` where the source has none.

**CSV.** Two columns, `time,value`, with time in seconds. You type the rest into the import form, and you choose the kind of signal and its origin yourself.

A stream's kind is `neural`, `muscle`, `displacement` or `mechanics`. EMG is `muscle`. A neural stream may say where it was recorded: `brain`, `spinal`, `peripheral`, `autonomic` or `visceral`. Leave that out if you do not know it.

These are kinds of measurement. They are not the four kinds of training data in [the project's README](../README.md): a simulated stream is marked by its origin, which comes next.

A stream's origin is `measured`, `derived` (computed from a recording, such as filtered EMG), `inferred` (a model's output) or `simulated` (a simulator's output). The origin travels with every sample into every export. To tie a derived stream to the recording it came from, name the parent in `policyMetadata.provenance.derivedFrom`; [docs/METADATA.md](docs/METADATA.md) gives the format.

The app checks that a file is well formed. It cannot check that what the file says is true.

## Look at the samples as they were stored

Open **Inspect original samples** under a trace. The slider steps through one stream at a time, at the timestamps the file holds, so uneven gaps look uneven. A gap in the source reads **Missing in source**. If the recordings are lined up, choose **Show original samples** first.

## Line recordings up

Two recordings can share a timeline only if they declare the same organism, the same subject, the same recording and the same clock. Recordings of different people do not become simultaneous because the tasks look alike. A file that leaves the organism or the subject unknown can be inspected, not lined up.

Choose a step, the longest gap you will allow, and nearest-sample or straight-line interpolation. The result covers only the stretch that all the recordings share. A missing sample stays missing, a gap longer than your limit stays a gap, and nothing is extended past the ends. Units are kept as they came.

Move **Aligned time** to read every trace at one instant, with its unit and whether the value was stored, interpolated or missing. In the built-in example, try 1.5 seconds: the force is missing in the source, and the displacement is interpolated between its neighbours.

The limits keep the browser responsive: 5 MiB per file and in total, 64 streams, 50,000 input samples, 5,000 points on the shared timeline, 500,000 aligned values.

## Check what a file declares

**Metadata checks**, beside the traces, lists what each stream says about its measurement, its unit, its clock, who it was recorded from and where it came from, and marks what is missing or contradicts itself. The built-in example leaves some of this out on purpose, so that you can see what a gap looks like.

A licence written in a file is a claim, not a permission. Matching subject names or clock names show how two files say they are related. They do not show that the recordings were made together.

**Export samples + checks** saves `neurotranslator-inspection.json`: the files as you gave them, with the report. Files saved before the app took its name are called `neurotranslate-0.0-inspection.json` and say "NeuroTranslate 0.0" inside; the renaming changed nothing else in the format.

## Replay a palm trial

Choose **Import a trial**, open a trial prepared from the palm dataset (IACKD), and choose **Compare estimates**. The chart starts at the first tracked palm position at or after the cue. Everything on it is in millimetres, along one axis of the tracker.

A trial from a person's **first recording** compares two forecasts: time and hand history, and the same with scalp EEG added. [Prepare one](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/scalp-eeg-palm-history#replay-a-recorded-trial).

A trial from a person's **second recording** compares each model as fitted on other people with the same model adjusted on that person's first recording. **Model inputs for the chart and sample table** switches between hand history alone and hand history with EEG. **Read sample values** gives the numbers behind the chart, and **Download trial results** saves all four estimates, with the reason for any that is missing. [Prepare one](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/scalp-eeg-personal-calibration#replay-a-second-recording).

The error shown for one trial and the error a study publishes are averages over different things, so do not set them side by side. [The second study's results, person by person](https://eliminatenoise.github.io/NeuroTranslation/index.html#personal-calibration) give each of its three people equal weight.

All of this is replay of recordings that were processed after the fact. Nothing in the app is live.

## What the app is not

It does not turn one kind of signal into another. Its built-in example is invented numbers, labelled as invented wherever they appear, and is there to show the controls. It holds no recordings: its dataset cards link to the archives.

The app's own code is dedicated to the public domain under [CC0 1.0](LICENSE). The recordings it reads belong to the people who made them: [RIGHTS.md](RIGHTS.md).
