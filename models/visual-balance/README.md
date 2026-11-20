# The next 125 milliseconds of a walk

A walker sees the visual field rotate. Cameras and electrodes are already recording. At the end of the observation, can scalp voltage help forecast where the head and sacrum are about to move?

Open the launcher for your operating system, or open `forecast.html` directly in a browser. The first example is synthetic. The two choices under **Fitted model** run separate trained models on that same example. You can load your own event with **Open an event JSON on this device**. Forecasts run locally and report the change from the last observed position, in millimetres.

## Six people walked outside the fit

The assessment retained 880 of 894 recorded visual rotations. Each of the six people contributes equally to the errors below.

| Input to the forecast | Sacrum error | Head error |
| --- | ---: | ---: |
| Scalp recorded at the same event | 7.798 mm | 7.175 mm |
| Separately fitted model without scalp voltage | 7.668 mm | 7.123 mm |
| Scalp recorded at a different event | 7.840 mm | 7.278 mm |

Withholding scalp voltage gave the lowest average errors for both markers. For the head, substituting a different event's scalp voltage increased error by 0.103 mm against the correct event under the primary donor order. The adjusted upper bound for correct minus wrong was −0.038 mm. One of the two alternative donor orders brought that upper bound above zero. Neither marker met the requirement to beat both controls. These six walkers provide limited precision. [Assessment errors and uncertainty](assessment-summary.json)

A secondary comparison on the same 880 events asked how the full Transformer compared with the fitted linear model that also received scalp voltage. Mean errors fell by 0.788 mm at the sacrum (two-sided 95% interval for Transformer minus linear, −1.903 to −0.098) and by 0.618 mm at the head (−1.569 to +0.032). These differences measure the effect of changing architectures. The scalp-withholding fit addresses the value of the scalp input itself. [Paired architecture comparisons](linear-comparison.json)

## What the model sees

One event contains 160 samples of marker positions at 256 Hz, ending roughly 125–129 ms after the logged rotation onset. The model reads eight successive groups of 20 samples. Each group carries both markers' final positions and changes, the direction shown in the display, and mean and root-mean-square voltage from the scalp, eyes, neck and lower legs. The target is the next 32 samples of marker displacement. The outputs are sacrum first and head second, each in mediolateral, superior–inferior and anteroposterior source-axis order. The signs follow the instruments' coordinate system.

In `synthetic-event.json`, `motion_mm` is 160 × 2 × 3, centred on each marker's final sample. `direction` is +1 for clockwise and −1 for counterclockwise. The eight-bin EEG arrays have 128 channels, A1–A32 through D1–D32. The eight-bin nuisance arrays have two neck channels, three eye channels and eight leg channels. The left and right neck channels come first, then right horizontal, left horizontal and left vertical eye channels. The eight leg channels follow the extractor's named order. Each electrode has a Boolean availability mask. A good channel can read zero. A bad channel contributes nothing to means, scales or projected voltages. The fitted models receive no explicit mask indicator. [Named channel order](source/extract.py)

Only training people set the scales. Each supplying person has equal weight for each feature. The model takes the logarithm of one plus RMS voltage in µV, keeps signed means, and clips standardized inputs to ±6. Within each 32-site acquisition bank, it retains a constant and a cosine-weighted voltage summary for each statistic, normalized by the observed coefficients' Euclidean norm. This gives 16 scalp values per time bin. The numbered banks identify recording channels. Their labels alone cannot localize a cortical source.

The Transformer embeds 55 features per bin in 24 dimensions. Three attention heads read the eight time bins. A 48-unit feed-forward layer and a linear map of the motion history contribute to both predictions. The six shared outputs correct the displacement obtained by repeating the last 32-sample movement. There are 7,134 trainable parameters. Each model uses 240 AdamW updates with batches of 96 events. Each item draws a training person uniformly, then an event from that person.

Both fits use the same initial state, person-balanced training draws, masks, architecture and parameter budget. Sixteen input slots contain copies of 12 motion and four nuisance features. In the full model, each of these slots also carries 0.35 times the corresponding scalp summary. In the second fit the common features occupy all 16 slots on their own. Every column can train in either model. Dependence between duplicated columns in the second fit limits how literally one can interpret equal parameter counts as equal information.

## What would count as an improvement?

The first comparison asks whether the full fit beats the fit without scalp voltage. The second keeps the full model fixed and substitutes another event's scalp values and availability from the same person, direction and third of the walk. Each donor comes from a separate, non-overlapping event. The primary order uses the next event and wraps around. Two shuffled orders test sensitivity to the donor choice.

For each marker, average three-dimensional endpoint error over events within each person, then over people equally. Negative paired differences favour the full fit. Both control comparisons for a marker must have a one-sided 98.75th-percentile participant-bootstrap upper bound below zero. A joint claim needs all four bounds below zero. The result files also give ordinary two-sided 95% intervals, signed axis bias, direction-specific error, two alternate donors and a separate estimate on rows adjacent to tracking exclusions. Resampling events would give spurious precision.

The development scores hold each person out of model fitting in one of three folds. The released weights then use all qualifying development people. Electrode artefact, optical interpolation, the head-mounted display and uncertainty about the exact light-onset time limit interpretation. A forecast of a stored marker change cannot identify a neural command or demonstrate physical feedback. [Development results](development-summary.json) · [Six-person assessment](assessment-summary.json)

## Run the fit or the scorer

1. Use the source guide to download, extract and verify the versioned recordings in a local directory. Keep the source-reader environment separate if its dependencies differ. It produces a private NPZ and quality report for each split. [Source instructions](source/README.md)
2. Install the model dependencies in a fresh Python environment with `python -m pip install -r requirements.txt`. The archived fit used Python 3.14, NumPy 2.5.3 and PyTorch 2.14.0 on CPU with two PyTorch threads. The browser needs none of these.
3. From this directory run `python reproduce.py fit prepared rebuilt` to repeat the grouped fits, save the privately identified out-of-fold predictions, and regenerate `rebuilt/weights.json`. Run `python export.py rebuilt/weights.json rebuilt/weights.js` to emit the browser asset.
4. Run `python reproduce.py score prepared scored` to apply the released weights to the assessment cohort and regenerate the paired-control, interval and sensitivity tables. The scorer checks the typed source arrays and the public weight seal. Keep the generated event-level predictions and participant records local.
5. For one compatible event use `python model.py weights.json synthetic-event.json`. The dependency-free JavaScript equivalent is `VisualWalkForecast.predict(event, VisualWalkWeights.full)` after loading `visual-walk.js` and `weights.js`. Pass `VisualWalkWeights.no_scalp` for the separately fitted comparison. The synthetic inputs in `VisualWalkForecast.example(phase,direction)` are generated locally. Six numerical fixtures in `synthetic-reference.json` give the PyTorch forecasts.

Peterson and Ferris collected and released the source measurements. [Recording attribution and rights](NOTICE.md)
