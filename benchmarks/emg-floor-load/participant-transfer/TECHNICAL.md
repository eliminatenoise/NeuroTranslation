# Right-leg EMG and 100 ms floor-plate impulse

[Simple edition](README.md) · [Exact results](RESULTS.json) · [Download the saved models](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/participant-transfer/Floor-Load-Transfer.zip)

In four participants excluded from fitting, the direct three-pass model reached 10.1623 N·s mean absolute impulse error. The constant zero forecast reached 9.8719 N·s. Three passes reduced direct-model error for every participant in both evaluations. The conditional models' mean errors matched the zero forecast to two decimal places.

## Inputs and outcome

Use the eight original surface electromyography (EMG) channels at 1,000 Hz. Center each 20 ms bin, divide its root mean square by the pooled root mean square of earlier valid bins in the same 200 ms history, and apply `log(1 + ratio)`. Require three earlier bins and keep the first three unavailable. Standardize each channel with statistics from fitting histories. Encode missing entries as zero after standardization, with a separate availability feature. [Data and CC0 licence](https://doi.org/10.25452/figshare.plus.30294658.v2) · [Acquisition](https://doi.org/10.1038/s41597-026-08739-2)

The signed target is `−sum(Fz_C + Fz_D) / 200` over the 20 samples from each plate strictly after issue and within the next 100 ms. A positive event is `impulse > 1 N·s`. The offline label uses the authors' filtered export. Predictor inputs contain earlier EMG only. The predicted quantity describes load on plates C and D, which cover part of the walkway.

## Splits and chronology

Use five whole-participant folds among Subjects 1–5, fitting each model, scale and reference rate on the other four. The 7,024 development forecasts reuse previously studied recordings. Fit all frozen methods on Subjects 1–5 and evaluate separately on Subjects 6–9, Session 1, Recording 1, repetitions 4–5 of seven activities. Of 56 nominated repetitions, the source catalogue excludes two and the original button clock excludes one whose waveform matches fail to identify a unique interval. The 53 remaining repetitions give 4,515 issued and scored forecasts, with 90,300 distinct time rows at 200 Hz. Freeze the pooled weights before forecasting the new histories and save all forecasts before reading the evaluated force values. Match processed EMG anchors to the raw EMG and button clock to identify the full input and outcome intervals. [Author processing code](https://doi.org/10.5281/zenodo.17122076)

## Fitting and inference

- Reference methods use zero impulse or ridge regression on flattened entries and availability flags. The ridge penalty is 0.01 with an unpenalized intercept. Both predict the training event frequency, with equal weights by participant and by repetition within each participant.
- The attention block has width 32, four heads, a 64-wide feed-forward layer and ten learned positions. The one-pass and three-pass networks have the same number of parameters and use shared block weights across repeats. The direct head learns a median and an event probability, using scaled absolute error at weight 0.5 and binary cross-entropy at weight 0.25.
- A conditional head, linear or attention, learns the same event probability and active-state quantiles at `(0.025, 0.1, 0.25, 0.5, 0.75, 0.9)` through weighted quantile loss on `y > 1 N·s`. Renormalize case weights within these above-threshold rows. Use 257 weighted empirical quantiles on `y ≤ 1 N·s` from fitting data. If a seed predicts event probability `p ≤ 0.5`, use the lower distribution at quantile `0.5 / (1 − p)`. Otherwise, sort the six predicted quantiles, interpolate at `1 − 0.5 / p` and floor the result at 1 N·s. Interpolation uses flat tails beyond the fitted quantile levels.
- Each of the five learned neural or conditional methods uses two independent fits (seeds 20261125 and 20261126), with 48 full-batch AdamW updates per fit and learning rate 0.001. Scale targets by the weighted training median of `y > 1 N·s`, floored at 1 N·s. Fit the neural weights in FP32 and ridge in float64. Average the two point forecasts and their probabilities before scoring.

## Results

Average absolute impulse error and squared probability error (Brier score) within a repetition, then weight repetitions equally per participant and participants equally. Subset errors use repetitions with relevant support. The five-person set has 1,322 positive events. The four-person set has 750 and has 926 impulses below −1 N·s, all from Subject 7. Retain these signed observations in the primary scores. Their cause was not established.

| Method | Development MAE (N·s) | New-participant MAE (N·s) | Development MAE, y > 1 (N·s) | New-participant MAE, y > 1 (N·s) | Development Brier | New-participant Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Zero | 9.8115 | 9.8719 | 52.1102 | 56.7651 | 0.15529 | 0.14176 |
| Ridge | 15.9918 | 16.4487 | 43.4600 | 48.0555 | 0.15529 | 0.14176 |
| Direct, one pass | 10.5022 | 10.5165 | 51.0133 | 55.7207 | 0.15148 | 0.13958 |
| Direct, three passes | 10.2626 | 10.1623 | 51.9462 | 56.6056 | 0.15401 | 0.14133 |
| Conditional linear | 9.8115 | 9.8719 | 52.1102 | 56.7651 | 0.15506 | 0.14070 |
| Conditional, one pass | 9.8115 | 9.8719 | 52.1102 | 56.7651 | 0.15176 | 0.13963 |
| Conditional, three passes | 9.8115 | 9.8719 | 52.1102 | 56.7651 | 0.15390 | 0.14123 |

The direct three-pass method improved over zero on one new participant. All methods had zero event recall at `p > 0.5`. The only prediction above 0.5 was one false positive from the new-participant direct one-pass model. The conditional three-pass method always returned zero impulse. The prospective conditional one-pass method made three nonzero forecasts with magnitudes up to 0.012 N·s. The result covers new participants in one study using offline filtered outcomes. Live force and other devices require separate evaluation.

## Run the saved models

The ZIP includes the pooled fits and a generated two-row `EXAMPLE.npz`. With Python 3, NumPy and PyTorch, use the matching launcher or run `python3 -B predict.py EXAMPLE.npz` from the extracted folder (`py -3` on Windows). For a prepared input, provide a float `history` array of shape `(N, 10, 8)` containing `log(1 + ratio)` before standardization, which the program applies. Use `NaN` for unavailable bins. Provide a `channels` array with the exact strings and order in `EXAMPLE.npz`. Preserve missing first three bins and at least one measured entry per history. Pass `--threads` to change the default one CPU thread. Output gives impulse in N·s and probability of `y > 1 N·s` for each method. The example passed a Linux CPU run with NumPy 2.5.3 and PyTorch 2.14.1. macOS and Windows launchers were inspected as source.
