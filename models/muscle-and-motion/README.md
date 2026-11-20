# Can one model forecast the muscle and the movement?

A scene tilts around someone standing or walking on a balance beam. Electrodes on both lower legs record small changes in voltage. Cameras track a marker near the base of the spine. Take the last 625 milliseconds from both instruments. What will the next eighth of a second look like?

One Transformer makes both forecasts. Two specialists get the same history and the same number of training updates apiece, but each answers just one question. Across 1,759 held-out rotations from six people, the specialists did slightly better on average. The shared model missed the eight muscle amplitudes by 9.50 µV and the marker path by 1.965 mm. The specialists missed by 9.45 µV and 1.940 mm. The experiment required the shared model to improve both forecasts. It failed that test.

## Run a forecast

Extract the entire archive. Open the launcher for your operating system or double-click [forecast.html](forecast.html). It runs from disk in a browser. The example history is invented. Switch between the shared model and the specialists, or change the posture and visual rotation. Watch the predicted voltages and the three coordinates change.

With Node.js, run the same forecast from a terminal.

```sh
node forecast.cjs synthetic-event.json joint
node forecast.cjs synthetic-event.json specialists
node test.cjs
```

To supply your own example, follow the shape and units in [synthetic-event.json](synthetic-event.json). Use finite numerical values sampled at 256 Hz. Provide 160 rows of eight surface voltages in microvolts, and 160 simultaneous rows of three sacrum coordinates in millimetres. Muscle columns run left then right, with tibialis anterior, soleus, medial gastrocnemius and peroneus longus on each side. Marker columns follow the source’s ML, SI and AP axis labels. Anatomical signs remain unresolved. Set `posture` to 0 for standing or 1 for walking, and `direction` to +1 for clockwise or −1 for counterclockwise visual rotation. The browser interface accepts a shared starting position because the model centres the marker history on its final observed position.

For a JavaScript application, load the local classic scripts `model.js` and `weights.js`. The [invented example](example.js) is an optional third script.

```js
const result = MuscleMotion.predict(MuscleMotionWeights, MuscleMotionExample, "joint");
console.log(result.future_rms_uv);  // Eight amplitudes over the next 32 samples, µV.
console.log(result.future_path_mm); // 32 XYZ displacements from the last observed point, mm.
```

The two signals cover exactly the same future interval. For muscle, RMS squares the 32 voltage samples, takes their mean, then the square root. It measures electrical amplitude. The movement forecast gives a point every 3.90625 ms. The recording passed through offline filters and resampling before this study. A score here describes an offline test on the qualifying recordings.

## How the forecasts were fitted

The published split assigned 18 people to development. All 18 contributed both standing and walking examples in both rotation directions. Each training batch sampled people equally, then posture, then rotation direction and finally an available event. The three development folds held out entire people. No assessment scores selected the architecture, training duration or settings. The six assessment people came from an older evaluation of walking and head movement in this dataset. Their standing recordings and the two linked target quantities here were new to this experiment. Another six people stayed in reserve.

Each 160-sample history becomes 20 blocks of eight samples. Each block contributes eight log-transformed muscle amplitudes, the marker’s three mean coordinates relative to its final recorded position, and the three coordinate changes from the first to last sample in the block. Two more inputs give posture and rotation direction. The model standardizes the first 14 features using development data, encodes all 16 features into 24 numbers, adds a learned position for each block, then applies a two-head self-attention layer and a 48-unit feed-forward layer. The last block can attend to the whole observed history.

The muscle head corrects a recent amplitude estimate. For each channel the starting value is its most recent 32-sample RMS plus 5% of that muscle’s development mean. The learned multiplier is `exp(clip(head, −3, 3))`, so the forecast stays nonnegative. For movement, the starting path continues the velocity from the final 16 observed intervals. The path head learns four XYZ corrections at samples 8, 16, 24 and 32. Linear interpolation fills in the intermediate corrections, starting at zero displacement at the cutoff. The test scores every future point. A sudden change between two learned anchors can be missed.

The shared model has 6,308 trainable parameters. The muscle specialist has 6,008 and the path specialist has 6,108. Each starts with the same overlapping weights, uses the same 61,440 sampled examples in the same order and takes 640 AdamW updates. The specialists together require 1,280 updates. The shared trunk receives gradients from mean absolute muscle error and mean three-dimensional path distance, each divided by a development scale before averaging. Both objectives contributed nonzero gradients at the first and final shared update. [Fitting implementation](fitting.py) · [Calibration and network](network.py) · [Development and resource counts](development-summary.json)

## What the recorded trials show

For every event the muscle score averages the eight absolute amplitude errors. The path score averages the three-dimensional distance at each of 32 instants. The final-point distance is a separate measurement. Within each person the two postures and two directions get equal weight; each event within a cell gets equal weight. People get equal weight in the final mean. The primary comparison resampled whole people together 5,000 times with seed 1419. It required the upper 97.5th-percentile bound for shared minus specialist error to fall below zero on both outcomes.

| Method | Muscle MAE (µV) | Mean path error (mm) | Final point error (mm) |
|---|---:|---:|---:|
| Shared Transformer | 9.499 | 1.965 | 4.224 |
| Two specialists | 9.453 | 1.940 | 4.186 |
| Hold muscle amplitude, repeat last path | 10.274 | 3.265 | 5.894 |
| Hold muscle amplitude, continue 16-interval velocity | 10.274 | 2.304 | 5.098 |
| Hold muscle amplitude, leave the marker still | 10.274 | 4.491 | 8.494 |

Shared minus specialist muscle error was +0.046 µV (95% interval −0.065 to +0.206). The corresponding path difference was +0.025 mm (+0.003 to +0.049). The shared model improved the respective outcome for two of six people in each comparison. The six participants limit precision. [Full scores, by posture, direction and muscle](assessment-summary.json)

A second test exchanged the observed leg voltages between two nonoverlapping events from the same person, posture, rotation direction and third of the session. The marker history and true future stayed with the original event. The shared forecast grew worse by 6.248 µV (95% interval 5.599 to 6.943) and 0.141 mm (0.098 to 0.186). All 1,759 events had a matched donor. The model uses the timing of observed muscle activity, including its recent RMS starting estimate. This swap does not isolate the learned attention layer or establish that electrical activity caused the recorded movement.

## Does training on walking help with standing?

The unchanged walking model made larger errors on 879 standing rotations. Updating the walking model on standing improved both predictions. To test what the walking start contributed, compare it to a model initialized from scratch and given the same standing updates. Both models received the feature and target scales learned from walking development data. Training on standing from a random start therefore still uses those walking summary statistics.

| Training | Muscle MAE (µV) | Mean path error (mm) |
|---|---:|---:|
| Walking only, applied unchanged | 5.370 | 2.528 |
| Walking then standing, update only the two heads | 4.508 | 0.672 |
| Walking then standing, update all weights | 4.442 | 0.667 |
| Random start, 640 standing updates | 4.542 | 0.674 |
| Random start, 1,280 standing updates | 4.587 | 0.690 |
| Mixed-posture primary model | 4.514 | 0.652 |

Full adaptation starts with 640 walking updates and takes another 640 on standing. Relative to 640 standing updates from scratch, its mean differences were −0.099 µV (95% interval −0.219 to +0.004) and −0.008 mm (−0.030 to +0.015). Both intervals include zero. Walking and standing occurred in a fixed source order and the analysis uses only events with valid future observations. The transfer experiment tests how well learnt weights carry between these two recording conditions. [Transfer weights](transfer-weights.json) · [All paired transfer contrasts](assessment-summary.json)

## Reproduce the study

Use [the source reconstruction instructions](source/README.md) to recover the original OpenNeuro recordings, verify their checksums, extract the two synchronized signals, apply the stated quality rules and rebuild the development and assessment arrays. The source reader has its own pinned dependencies. The local model was trained on Linux with Python 3.12, NumPy 2.5.3 and PyTorch 2.14.0. Use a separate model environment for this step. On Windows, use a Linux environment such as WSL for the frozen training script; the browser and Node.js forecast work directly on extracted files. Hardware and library builds can affect floating-point results.

```sh
python -m pip install -r requirements.txt
python reproduce.py fit /path/to/prepared /path/to/rebuilt-fit
python reproduce.py score /path/to/prepared /path/to/rebuilt-scores
```

The first command after installation checks the development arrays and their source receipts, fits all three grouped folds, reproduces the final shared model and specialists, trains the five walking-to-standing variants and reports weight hashes. The second checks the assessment arrays and scores the released weights. To score your regenerated weights directly, pass their paths to `assess.py` in the order shown by `python assess.py --help`. The score report includes per-muscle error and bias, three-axis mean path bias, endpoint error, posture and direction summaries and paired intervals. The observations and individual scores remain on the machine doing the reconstruction. [Data and reuse](NOTICE.md)
