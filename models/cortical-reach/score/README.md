# Forecast the handle's next 100 milliseconds

Where will the handle move next? Its recent trajectory and the animal’s visible task cues gave a mean endpoint error of **0.4974 cm** on the later test trials. Giving the same Transformer the preceding area 2 spike counts increased error to **0.6044 cm**. This package reproduces the comparison on the single recorded session from macaque C, 12 September 2017. [Original recording](https://doi.org/10.5061/dryad.nk98sf7q7) · [Chowdhury, Glaser and Miller](https://doi.org/10.7554/eLife.48198)

## Run the calculation

Use Python 3.11 or later and NumPy. Follow the source directory’s README to prepare the three study files. From this score directory, run the following command. The two included forecast archives supply all three fitted Transformer seeds. Each output directory must be new. [Prepare the original session](../source/README.md)

```sh
python -B score.py --output reproduced
```

To fit the eight ridge models again from the first 324 assigned originals and check every coefficient, run this command. Two training originals lack an eligible event pair, leaving 322 for fitting. Limiting BLAS to one CPU thread reproduces the recorded execution setting.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B score.py --refit --output reproduced-refit
```

Use `--source PATH` for prepared files in another directory or `--weights FILE.npz` for an alternate copy of the eight published ridge models. To compare forecasts regenerated with the public fitting code, pass `--predictions ../fit/reproduced`. Both prediction archives must identify their source NPZ by SHA-256 and carry the original row identifiers in sequence. [Refit the Transformers](../fit/README.md)

## What enters the comparison

Each recipient contributes one 100-ms forecast from a 200-ms history. All six Transformer fits have their own predictions for seeds 17, 41 and 73. Their inputs are movement plus cue, spike counts plus cue, all three together, cue alone, movement alone and spike counts alone. For a seventh prediction, the combined model keeps the recipient's movement and cue but takes spikes from a different, earlier original with the same phase, event-relative offset and already-visible direction and cue state.

The matched test comparison contains 778 forecast windows from 105 originals. Of the 108 assigned originals, 106 supplied eligible measurements and 105 had at least one earlier match. We first average window errors within an original and epoch, then weight its represented epochs equally and give each represented original equal weight. Seed summaries average the three errors on the same rows. The primary error is the Euclidean distance between forecast and recorded displacement in cm. Positive movement-plus-cue minus joint error favours adding spikes. A 95% interval uses 5,000 circular moving-block resamples of eight consecutive original trials, including assigned trials without a matched window in the chronology. The held primary difference was −0.1070 cm, with a 95% interval of −0.1445 to −0.0755 cm. Wrong-trial minus correctly paired error was −0.0102 cm, with an interval of −0.0576 to 0.0300 cm. The timing comparison remains unresolved. These estimates describe one already processed recording. [Test results](test/RESULTS.md)

Each of the six input combinations also has an affine ridge fit. Two additional ridges combine movement and cue with either the five population firing rates or the 30 individual units’ mean rates across 200 ms. All eight use a fixed penalty of 0.01, train-only weighted means and population standard deviations, and an unpenalized intercept. The combined ridge has its own wrong-trial comparison. The four physical controls predict zero displacement or extend the observed velocity from the last 40, 100 or 200 ms. Together the stored results cover 20 methods. [Validation results](validation/RESULTS.md)

## Files and checks

- `original-ids.json` lists the original trial IDs in each fixed partition. `predictions/` contains the frozen six-branch and wrong-trial Transformer forecasts, row identifiers and seed order for validation and test.
- `train/ridge-weights.npz` holds all eight named sets of coefficients, intercepts, feature names, centers and scale divisors, plus the sorted unit guide and penalty. The in-browser combined ridge uses `portable/ridge.js` and `portable/ridge-all.json`.
- `validation/scores.json` and `test/scores.json` contain the complete published score tables, axis errors, biases, directions, per-seed effects, intervals and decisions. The accompanying compressed CSVs contain matched original-by-epoch means. The source-accounting files record exclusions from the original event and signal checks. The first held original, 499, has its own eight illustrative anchors in `test/first-original.json`.
- The driver writes fresh tables to the requested directory. It checks the rounded reports, every aggregate and seed entry, both decisions, every chronological interval and every original-by-epoch CSV row. `comparison.json` records the input hashes and check counts. Floating-point comparisons use an absolute tolerance of 1e−10, and row identities, labels, counts and decisions must match exactly.
