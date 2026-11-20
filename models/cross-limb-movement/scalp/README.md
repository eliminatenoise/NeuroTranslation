# Can three scalp electrodes improve a movement forecast?

A light tells someone to reach for an object. A camera tracks the wrist, and electrodes on the arm record electrical activity in the muscles. From the last 625 milliseconds, how accurately can we predict the next 125? This experiment gives one model the additional voltage recorded at three scalp positions. A second model gets the average values from its training group and the same flags telling it which electrodes were available.

For the six people held out of training in the wrist study, the measured scalp history increased average whole-path error from 3.91 to 4.12 mm. A second study measured eight leg muscles and a marker on the sacrum while people stood or walked on a beam. There the scalp history reduced average leg muscle error from 11.3846 to 11.3703 µV. Sacrum-path error increased from 2.6674 to 2.6992 mm. One of the four prespecified outcomes passed its directional threshold. These two offline comparisons give no basis for adding the scalp inputs as a general improvement across both movements. Scalp voltages mix multiple electrical sources, and the original recordings were processed offline. [Balance experiment](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Reach-and-lift experiment](https://doi.org/10.1038/sdata.2014.47)

## Try a forecast

The two commands below run the same mathematical wrist example in JavaScript and Python. Use Node.js 20 or later for the first. The Python implementation uses NumPy and PyTorch. Each returns 13 named muscle amplitudes, with unavailable muscles set to null, and 32 positions relative to the marker at cutoff. Each position has three coordinates in millimetres in the original study frame. Balance muscle amplitude is in microvolts. Wrist muscle amplitude retains the study export's units.

```sh
node predict.mjs model-central.json synthetic-wrist-central.json
python -B predict.py model-central.json synthetic-wrist-central.json
node predict.mjs model-reference.json synthetic-wrist-central.json
```

The single-file checkpoints use training seed 1641 and participant fold 0. Compare central and reference on the same example. For forehead, eye or neck checkpoints, choose the synthetic example with the same sites. The wrist recordings have forehead electrodes. They have no dedicated eye or neck channels. All supplied example inputs are invented. The wrist examples use muscle amplitudes around 0.01 in the exported units, the order of magnitude measured in the fitting group. To call the model in a browser, import `predict` from `inference.mjs` and pass it the parsed checkpoint and event objects. Use `export_checkpoint.py` to select any of the 45 fitted models.

```sh
python -B export_checkpoint.py 3917 2 central chosen-model.json
node predict.mjs chosen-model.json synthetic-balance-central.json
```

## Which numbers go into the model?

Each example includes a study and task, availability flags for the 13 muscle slots, twenty bins of observed muscle activity, twenty three-axis marker positions relative to the last position, the age of each marker sample and the preceding 125-ms muscle amplitude. Three electrical sites each add the signed mean and root mean square of their native voltages, in that order, for every bin. Store these values as `scalp_values[20][3][2]`. Set `scalp_mask[3]` to three booleans. Fill an unavailable site's pair with zeros in every bin. One or more sites must be present to use a measured electrical branch. Read the named sites, missing-value rules and source timing at the end of this paragraph. [Electrical input definitions](electrode-inputs.md)

The three central slots are C3, Cz, C4 on the wrist-study cap and D19, A1, B22 on the balance cap. Inside each fitting fold, subtract the mean and divide by the population standard deviation of the available training histories, separately for each study, site and feature. Insert an observed flag alongside each pair. This makes nine values per time bin. A learned projection adds these values to the original movement and muscle token before the Transformer compares the twenty time points. The primary unchanged-mask reference supplies zero for each standardized measurement. Its six measurement columns cannot vary. Both networks store 4,068 fitted coefficients. Counts of nonzero gradients can differ.

## Repeat the fits

Obtain the movement and scalp development caches from the two published source readers. Keep all participant files, held predictions and private run outputs in your own data directory. Set `MOVEMENT_SOURCE` to the published cross-limb model directory, `MOVEMENT` to the movement development NPZ, and `SCALP` to the paired scalp development NPZ. From this model directory, set `MOVEMENT_SOURCE=..` when using the repository checkout. The first command rebuilds the original and single-study comparisons from the published model source. If you have already generated those three held-seed files, the fold checkpoints and split design with the original reader, supply that run to the second command. The replay verifies numerical source, weight, draw, fold and prediction identities and reruns held inference from every comparator checkpoint. [Movement reader](../source/README.md) · [Paired scalp reader](source/README.md) · [Scoring and uncertainty](scoring/README.md) · [Original model and comparison code](https://github.com/eliminatenoise/NeuroTranslation/tree/c1db07f44229da9fb042a4d38ed6e4ba292d8013/models/cross-limb-movement)

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python -B build_comparators.py --source "$MOVEMENT_SOURCE" --base "$MOVEMENT" --out previous-run
python -B replay.py --base "$MOVEMENT" --scalp "$SCALP" --prior previous-run --out scalp-run
```

Each fold keeps every recording of a person together. The three training seeds are 1641, 2718 and 3917. Each learned branch takes 384 steps. Every step pairs the same 24 balance events with the same 24 wrist events. The reference, central, frontal, eye and neck branches have identical architecture and common starting weights. Eye and neck slots are missing in the wrist half of their training batches. Their held comparisons use balance only. The wrong-trial comparison uses the trained central weights and inserts an earlier, nonoverlapping history with the same central-site flags from another event in the same recorded condition. Missing donor matches stay out of that comparison.

The three returned `oof-seed-*.npz` files contain one held forecast per eligible row and method. Each method supplies `_rms` with 13 muscle slots, `_path` with 32 three-axis positions, and `_support` with one eligibility flag per row. Unavailable predictions are NaN for the whole row. Within an eligible forecast an unrecorded muscle is zero. Numerical identities refer to this recorded implementation with NumPy 2.5.3 and PyTorch 2.14.0, 3 CPU threads and one interop thread. Other numerical backends can differ. A mismatch from the archived comparator is reported explicitly.
