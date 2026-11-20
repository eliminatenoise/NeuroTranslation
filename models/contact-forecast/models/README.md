# How many events will each electrode record next?

A macaque held a robotic handle. The robot pushed it before the reach cue appeared. Take the 200 milliseconds leading up to a forecast time. Given the handle's recent movement, counts from 26 electrodes in sensory cortex and cues already visible, how many events will each electrode record in the next 100 milliseconds?

The recorded answer is an integer at each contact. A forecast is an expected count and can be fractional. An expectation of 0.4 means an average of four events across ten comparable windows. The source labels the counted events “sort zero.” They are unsorted electrode events. The same contact number on two days identifies the same named electrode channel. The recording does not establish which individual neurons contributed on either day. [Original study](https://doi.org/10.7554/eLife.48198) · [Chowdhury, Glaser and Miller data, CC0](https://doi.org/10.5061/dryad.nk98sf7q7)

## Try one real recorded window

Install NumPy and run this from the models directory. The example is the first eligible training window. Its recorded answer, in contact order, is in `measured_count_100ms`.

```sh
python predict.py weights/all-17.json example.json
```

The command returns contact IDs and 26 expected counts. Exchange `all-17.json` for `count_cue-17.json` to omit movement, or for `all-poisson.json` to use a regularized regression with a positive mean. Each model has its own fit. The wrong-movement control keeps the full model and swaps in another trial's earlier motion. Only rows with an earlier match qualify.

## Read or supply a history

Keep the five tokens in chronological order, each summarizing four 10-ms samples. The native source indices are one-based. The forecast begins at sample k. The last input sample is k−1.

| JSON field | Measurements in one token |
| --- | --- |
| `movement_tokens_cm` | End horizontal and vertical handle position, then horizontal and vertical end-minus-start displacement, all in cm. The first and fourth sample times are 30 ms apart. |
| `count_tokens_40ms` | Counts on 26 contacts, in `contact_id` order. |
| `cues` | Bump seen, bump direction x/y, target seen, target direction x/y, go seen. Each flag is 0 or 1. A known cardinal direction has unit length. Unseen directions are zero. |
| `cue_elapsed_s` | Seconds since each visible bump, target or go event, in that order. An unseen event contributes zero. |
| `contact_id` | One ordered list of the 26 electrodes, shared by all five rows. |

Supply the complete input layout shown in `example.json`. The reader applies the fitted scales and the selected model's input mask. A training feature with no variation has no learned effect on a new phase. Six such fields were disabled here. They cover target visibility, both target direction components, go visibility and elapsed times since target and go. The training rows all preceded those events.

The six arm names are `all`, `count_cue`, `cue`, `movement`, `count` and `movement_cue`. The three Transformer fits for each arm are identified by seeds 17, 41 and 73. The six regression fits are deterministic. The primary comparison averages differences in scores across the three seeds after scoring each. The inputs and responses come from one animal over two consecutive recording days. Encoder measurements were filtered upstream, so a strictly earlier stored sample has a weaker timing guarantee than a strictly causal sensor.

## Rebuild the fits and forecasts

From the study directory containing `models` and `source`, use a clean output directory. A CPU build of PyTorch, NumPy and SciPy is sufficient for the methods. The reference fit used PyTorch 2.14.0 and NumPy 2.5.3. Compiled libraries and CPU kernels can affect the final floating-point digits. Source extraction checks the exact day, contact ordering, event windows and training arrays. The source README identifies the source members and their hashes. Extract the two MAT members of the public reaching dataset into a local directory named `data`. [Dataset](https://doi.org/10.5061/dryad.nk98sf7q7)

```sh
python source/extract.py train data/C_20170912_COactpas_TD.mat rebuilt/source
python source/training_archive.py rebuilt/source/train.npz rebuilt/train-for-fit.npz
python source/extract.py validation data/C_20170912_COactpas_TD.mat rebuilt/source
python models/train.py fit --data rebuilt/train-for-fit.npz --out rebuilt/models --device cpu --threads 1
python models/infer.py validation --data rebuilt/source/validation.npz --weights rebuilt/models --out rebuilt/predictions
python source/extract.py test data/C_20170913_COactpas_TD.mat rebuilt/source --release-test
python models/infer.py test --data rebuilt/source/test.npz --weights rebuilt/models --out rebuilt/predictions
```

For reproducibility on a shared machine set `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1` before invoking the commands. The fit creates 18 parameter files for the temporal Transformers and six for the Poisson regressions. See `PROTOCOL.md` for the learning settings and `REGRESSION-NUMERICS.md` for the training-only correction to the regression solver. The training index preserves row weights, trial IDs, contact IDs and the training means. Three permutation files give the exact order of rows in every optimization pass.

Each inference command writes two compressed NumPy archives. The Transformer arms have axes seed × window × contact. The regression arms have axes window × contact. Each carries the trial, anchor sample, phase, offset, direction and movement donor. Missing matching donors have ID −1 and their wrong-movement predictions are NaN. The other predictions are finite positive expectations. The code also computes every forecast a second way with NumPy and writes a numerical comparison alongside the archives.
