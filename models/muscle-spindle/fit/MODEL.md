# How many spikes come next?

A muscle spindle senses stretch. Blum and colleagues recorded the electrical spikes of one sensory nerve fibre at a time as a machine stretched a rat's muscle. They also recorded the pull at the tendon and the position of the machine. Give this model the past tenth of a second. It estimates how many detected spikes fall in the next 20 milliseconds. A prediction of 1.4 is an expected count. The recording itself contains a whole number of spikes. [Blum et al., eLife (2020)](https://doi.org/10.7554/eLife.55177) · [Original measurements, CC0](https://doi.org/10.5061/dryad.vdncjsxsw)

## What the recordings showed

Holding out one sensory fibre at a time gave 16,262 forecasts over 94 trials. The combined model missed the next count by 0.435 spikes per 20 ms on average, with equal weight for each fibre and its trials. The model given only earlier spikes did better at 0.387. The mechanics-only model averaged 0.668. Adding tendon force and actuator position therefore did not improve this comparison over spike history alone.

Timing still mattered to the combined model. In the 15,792 windows with an earlier match from the same trial, substituting mechanics from 100 ms earlier raised the combined model's mean absolute error from 0.448 to 0.569 spikes per 20 ms. The actual preceding spike history stayed fixed. These figures average errors over three training seeds.

## Run one forecast

Supply five rows, oldest first. Each covers one completed 20 ms bin. Each row gives the mean tendon force, mean actuator position, change in force per second, change in position per second, and number of detected spikes. Calculate each change from the first and last samples *within that bin*, dividing by the actual time between those samples. Retain the signs and units of the archived force and position. Every input must be finite. Spike counts must be whole numbers from zero through the largest exactly representable JavaScript integer.

From this directory, run the recorded example with any current Python 3 interpreter. It needs only the standard library.

```sh
python predict.py strict-afferent/checkpoints/aff015-seed1641-all.json strict-afferent/history-example.json
```

For a browser page opened directly from disk, load `predict.js` as a classic script. Pass a parsed checkpoint and the five raw bins to `SpindleCount.predictCount(model, history)`. The same function is available as the named export `predictCount` in `predict.mjs`. Keep its sibling `predict.js` alongside it. The model and examples can be embedded in the page by its author. Once loaded, the calculation uses no network connection. The returned number is the expected spike count for 20 ms.

The fixed demonstration model learned from aff004 and aff017. Its test recording, aff015, provided no weights, input scales or training windows. The first trial of aff015 had been inspected while checking the source. All three recordings belong to filename group 0. Each of the 45 checkpoints contains its own weights, scales and active input list. The names `history`, `mechanics`, `all`, `force` and `position` identify the signals used. Give each one a complete five-column history. The reader applies its stored mask.

## Rebuild the fits

Follow the source reader's instructions to fetch and validate the nine development recordings and rebuild the windows for the population you intend to study. The original two-clock population uses `../source/private/windows.npz`. The separate mixed-clock sensitivity population uses `../source/private/sensitivity/windows.npz`. See `POPULATIONS.md` for the difference. Preserve the two reserved recordings unopened. Install NumPy and PyTorch for fitting and Node.js for the cross-language check. The source reader also uses SciPy. Use a fresh output directory. The relative paths below assume this file is in the fit directory and the source reader is its sibling.

```sh
python -B train_afferent.py fit --data ../source/private/windows.npz --out rebuilt --threads 1
python -B train_afferent.py refit --data ../source/private/windows.npz --out rebuilt/refit --threads 1
python -B verify.py --split afferent --data ../source/private/windows.npz --out rebuilt --refit rebuilt/refit
```

The first command holds out each complete afferent recording in turn, fits five input combinations at three fixed random seeds and writes the held forecasts to `oof.npz`. It also saves all 45 sets of fitted weights and the exact 19,200 training row draws for each afferent fold and seed. The independent refit command repeats the fixed demonstration fit from its initial weights. The check looks for exact refit agreement on the same runtime, validates the leave-recording-out split and the time-shifted control, and compares both standalone readers against PyTorch on held and synthetic examples. Small floating-point discrepancies are expected across libraries. The accepted bound for the standalone readers is 0.00003 spikes per 20 ms.

`PROTOCOL.json` records the original architecture, optimization and prefix splits. `AFFERENT-FALLBACK.md` records the exploratory split used here. Inside each fitted population folder, `fixtures.json` includes synthetic inputs and held measured examples. `aff015-trial1.csv` gives the selected trial's observed counts and five seed-1641 forecasts on its original clock. The last column uses tendon and actuator measurements from 100 ms earlier in the same trial, keeping the detected spike history at its true time. A blank marks a missing earlier window. `verification.json` gives the tested row counts and numerical agreement.

The experiment supplies offline forecasts for passive stretches in these recordings. Filenames identify groups and individual sensory recordings. The original study reports five healthy rats, but no verified crosswalk assigns every filename to a separate rat. All three eligible strict recordings came from the same filename group. The held comparisons measure transfer between these recordings within that group. Active human movement and prospective operation require their own measurements.
