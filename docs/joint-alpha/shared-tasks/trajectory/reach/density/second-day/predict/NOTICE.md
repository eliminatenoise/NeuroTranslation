# Recording and model

The dataset is by Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller. Chowdhury collected and processed the records in Miller’s laboratory. A camera followed one mark on the hand and another near the elbow. The example contains 20 successive times from macaque C's 7 September 2017 recording, all from a trial used for training. Each output is a forecast of how far a marker may move from its last recorded position.

The browser runs the autoregressive transformer fitted with research seed 1117 on cue-timed and regularly spaced histories from 72 trials. It first computes a fitted linear path. The transformer samples a correction for one of the four times, then uses that correction when it samples the next one. The interactive preview uses one trained fit. The published comparison used two fixed seeds and also evaluated diffusion and simple baselines.

The model takes eight position readings per time. Its 37 unused brain-signal fields are always masked. The native camera estimates were smoothed and aligned. Earlier estimates can depend on nearby later frames, and the handle data were filtered in both directions. The 20, 50, 70 and 100 millisecond times describe the processed recordings. The different-day test covered the same macaque. [Published comparison](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/shared-tasks/trajectory/reach/density/second-day/)

The source offers the readings under CC0. The browser model, interface and this package are also available under CC0. Read [CC0 1.0](CC0-1.0.txt) for the terms. [Recording archive](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original research article](https://doi.org/10.7554/eLife.48198)
