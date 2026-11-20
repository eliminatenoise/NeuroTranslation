# The website

This folder is served as [eliminatenoise.github.io/NeuroTranslation](https://eliminatenoise.github.io/NeuroTranslation/START.html). Everything in it runs in the browser. A recording you open is read on your own computer and goes nowhere.

| Page | What it is |
| --- | --- |
| [`START.html`](https://eliminatenoise.github.io/NeuroTranslation/START.html) | The start page. The finding so far, invented examples to try, and a list that matches each open dataset to the page that reads it. |
| [`index.html`](https://eliminatenoise.github.io/NeuroTranslation/index.html) | The app. It shows a recording on its own clock, lines several recordings up on a shared clock, and replays a palm trial against the fitted palm models. |
| Fourteen folders, from `cemhsey-arrays/` to `wrist-replay/` (excluding the other readers listed below) | The study readers of the numbered table, one per folder. Each reads a recording of the kind one study used and runs that study's forecasts on it, or shows the study's results. |
| [`hand-search/`](https://eliminatenoise.github.io/NeuroTranslation/hand-search/) | Type a sentence and find the moment of a recorded hand movement it describes, with the fitted models of [a newer study](../benchmarks/hand-language-retrieval/). Its [`forecast.html`](https://eliminatenoise.github.io/NeuroTranslation/hand-search/forecast.html) forecasts how far a wrist moves in the second after an instructor stops speaking ([its study](../benchmarks/preceding-instructions/)). |
| [`shared-motion/`](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/) | The general model's shared fit, which forecasts how far a tracked wrist or rat moves in about a quarter of a second, and the two angles of a wrist from its movement, with forearm and scalp signals if they are given, with or without a correction from four forearm signals ([the model](../models/README.md)). |
| [Five finger forecasts](https://eliminatenoise.github.io/NeuroTranslation/finger-signals/) | Try the one-person glove model on invented signal histories and see what adding a cortical recording did in the recorded trials. |
| [Four-second knee forecasts](https://eliminatenoise.github.io/NeuroTranslation/knee-stride/) | Follow one knee through an earlier stride, predict its next bend and reveal the later recorded angles. Compare task-trained and shared models. |
| [`gait-rhythm/`](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/) | Compare dominant leg-muscle and knee-angle rhythms for 11 walks, or calculate the spectra from compatible local recordings. [Offline reader and study](../models/gait-rhythm.zip) |
| [`papers/walking-rhythm/`](https://eliminatenoise.github.io/NeuroTranslation/papers/walking-rhythm/) | The four-page supplement on the knee-angle forecast and walking rhythms. [PDF](papers/walking-rhythm/gait-clocks.pdf) |
| [`knee-motion/`](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/) | Inspect a two-knee forecast 15 stored frames ahead, compare it with the recorded angles from a verified local file, or try the supplied invented example. [Offline viewer and model](../models/knee-motion.zip) |
| [`stride/`](https://eliminatenoise.github.io/NeuroTranslation/stride/) | Give the model half a second of a measured walk or run. It predicts the next 0.60 seconds at 18 points on the body. Turn the figure, follow one foot and reveal where its markers landed. |
| [`population-motion/`](https://eliminatenoise.github.io/NeuroTranslation/population-motion/) | Step through one recorded trip and compare how far a rat moved with forecasts that use its earlier movement alone or also use firing from two brain regions. |
| [`word-motion/`](https://eliminatenoise.github.io/NeuroTranslation/word-motion/) | Type **walk** or **run** to generate a short stride. Rotate the 18 body points and compare them with a measured training example. |
| [`whole-body/`](https://eliminatenoise.github.io/NeuroTranslation/whole-body/) | Three recorded whole-body movements, a scoop, a jump and a hop, to turn in 3D. No model runs on them. |
| [`papers/current/`](https://eliminatenoise.github.io/NeuroTranslation/papers/current/) | The four papers, to read online. |
| [`papers/language-and-observed-movement/`](https://eliminatenoise.github.io/NeuroTranslation/papers/language-and-observed-movement/language-and-movement.html) | A separate four-page supplement on finding a recorded movement from words, with its PDF and source. |
| `launchers/` | Desktop shortcuts to the app. |
| `preview.html` | An old address. It forwards to the start page. |

The app is built from [`demo/`](../demo/README.md). Change it there and rebuild; do not edit the built files here. [`build-manifest.json`](build-manifest.json) names the build this folder holds.

Offline copies of the readers are listed in [LAUNCHERS.md](../LAUNCHERS.md); `hand-search/`, `shared-motion/`, `whole-body/` and `word-motion/` each open offline as a single saved page, with launchers in their folders. The stride and three-rat downloads also include offline viewers and launchers. The numbers behind them are on [the studies page](../benchmarks/README.md). Who made each recording, and under which licence: [RIGHTS.md](RIGHTS.md).
