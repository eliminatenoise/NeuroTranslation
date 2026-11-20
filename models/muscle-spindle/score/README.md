# Forecast scoring and Poisson reader

The target is the number of author-detected spikes in one future 20 ms bin of a single rat group Ia sensory axon during imposed passive muscle stretch. Five completed bins provide tendon force, actuator displacement, their within-bin backward rates and spike count. Force and position remain in archived units. The source is the empirical recording deposit accompanying Blum et al. (2020). [Article](https://doi.org/10.7554/eLife.55177) · [CC0 data](https://doi.org/10.5061/dryad.vdncjsxsw)

The original fold plan excludes an entire filename prefix from fitting and normalization. The available strict and expanded populations were each missing at least one required prefix. In the separately registered exploratory fallback, each fold excludes one entire afferent member (aff004, aff015 or aff017). These three afferents share prefix 0. Every number in the macro score gives each prefix equal weight, each member of that prefix equal weight and each trial of that member equal weight. For the available analysis the range spans three held afferents from one prefix. Their correspondence to independently identified animals is unresolved. The author-selected archive omits some low-count or poorly discriminated stretches.

## Reproduce

Use Python 3 with NumPy and SciPy to read the source and fit outputs supplied by the associated study. Set BLAS and OpenMP thread counts for the local machine. Run these commands from the scoring directory. The first three scripts take explicit input and output paths.

```sh
python poisson.py WINDOWS.npz OUTPUT_FOLDER --population strict
python auxiliary.py WINDOWS.npz TRAIN-ROW-SAMPLES.npz OUTPUT_FOLDER --population strict
python evaluate.py OUTPUT_FOLDER/poisson-oof.npz TRANSFORMER-OOF.npz OUTPUT_FOLDER/auxiliary-oof.npz OUTPUT_FOLDER
python test_score.py
```

Use `--population strict-afferent` on the original two-clock window file to reproduce the separately registered exploratory analysis. Use `--population mixed-clock` and a separate output directory for the conditional single-deposited-time analysis. The original three-prefix protocol requires all three filename groups to pass the original two-clock source gate. Its status file records any unreachable group.

The `models` section of `summary.json` contains full-support and common-lag-support metrics by model, seed and held prefix. In the original plan the macro `all` entry averages the held prefixes. In the explored single-prefix population this average gives each of the three individually held afferents equal weight. The `member` entries retain each held afferent. `mean` under a seeded method averages separately scored losses across three fits. `bias` is forecast minus observed count. The observed/forecast ratio uses weighted means, with a null ratio when forecast is zero. The `gates` section retains each prespecified test. Differences are first model minus comparator, so negative deviance or MAE favors the first model.

| Output | Contents |
| --- | --- |
| group-scores.csv.gz | Macro, prefix, member and trial scores including predictions, observations and calibration |
| paired-differences.csv.gz | Difference in deviance and native count MAE within each matched level |
| calibration-bins.csv.gz | Fixed expected-count bins, weighted observations and forecasts, actual windows and hierarchical weight fraction, by seed and prefix plus macro. The companion member-calibration-bins.csv.gz provides separate held-afferent bins |
| coefficients.json | Fold-training scalers, five independent input subsets, GLM intercepts, coefficients and optimizer diagnostics |
| auxiliary-coefficients.json | Combined GLMs fit with equal-afferent weights and exact seed-specific sampled window frequencies |
| poisson-oof.npz, auxiliary-oof.npz | Row-keyed held forecasts in source order, indexed by prefix, afferent, trial and target bin |
| PREREGISTRATION.md, AUXILIARY.md | Frozen primary protocol and additional training-weight comparison |

The mean count in calibration bins is conditional on membership in that predicted bin. The full-group observed/forecast ratio and signed bias measure calibration of the average. A small aggregate bias can coexist with substantial within-group or within-bin errors. Common-lag comparisons retain only rows with a disjoint 100 ms mechanics history ending precisely five bins earlier in the same trial. This is an offline test of lagged predictive information.

## Replay one fitted GLM

`read_counts.py` uses only the Python standard library. Provide a JSON array with one or more windows, each shaped five bins by five channels. Each bin holds the within-bin means of force and position, the two backward rates in archived units per second, and its nonnegative integer spike count. Array order is oldest to newest. The output is one nonnegative expected count per input window.

```sh
python read_counts.py coefficients.json windows.json --held aff015 --mode all
```

The reported architecture comparison originally gives the Transformer equal-afferent sampling and the primary GLM equal-prefix training weight. Two auxiliary combined GLMs separately use all training windows with equal-afferent weights, or the exact 19,200 sampled training observations of each Transformer seed/fold with multiplicity. The sampled GLM standardizes on its observed multiset, while the Transformer standardizes on the training fold with equal-afferent weights. Optimizer, ridge penalty, gradient steps, precision and parameterization also differ. The auxiliary comparisons supplement the original comparison. The experiment does not isolate architecture as the sole cause of any difference.

The strict and mixed-clock status files retain both three-prefix failures. No pair of three-prefix fits exists to compare on a common sample. The exploratory fold instead compares all models on the same strict observations and preserves the correct mechanical and electrical clock arrays.
