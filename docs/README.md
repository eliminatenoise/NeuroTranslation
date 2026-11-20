# The website

This folder is served as [eliminatenoise.github.io/NeuroTranslation](https://eliminatenoise.github.io/NeuroTranslation/START.html). Everything in it runs in the browser. A recording you open is read on your own computer and goes nowhere.

| Page | What it is |
| --- | --- |
| [`START.html`](https://eliminatenoise.github.io/NeuroTranslation/START.html) | The start page. The finding so far, invented examples to try, and a list that matches each open dataset to the page that reads it. |
| [`index.html`](https://eliminatenoise.github.io/NeuroTranslation/index.html) | The app. It shows a recording on its own clock, lines several recordings up on a shared clock, and replays a palm trial against the fitted palm models. |
| Fourteen folders, from `cemhsey-arrays/` to `wrist-replay/` | The study readers, one per folder. Each reads a recording of the kind one study used and runs that study's forecasts on it, or shows the study's results. |
| [`papers/current/`](https://eliminatenoise.github.io/NeuroTranslation/papers/current/) | The four papers, to read online. |
| `launchers/` | Desktop shortcuts to the app. |
| `preview.html` | An old address. It forwards to the start page. |

The app is built from [`demo/`](../demo/README.md). Change it there and rebuild; do not edit the built files here. [`build-manifest.json`](build-manifest.json) names the build this folder holds.

Offline copies of the readers are listed in [LAUNCHERS.md](../LAUNCHERS.md). The numbers behind them are on [the studies page](../benchmarks/README.md). Who made each recording, and under which licence: [RIGHTS.md](RIGHTS.md).
