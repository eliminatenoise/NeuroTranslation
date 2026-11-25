# Muscle-only floor-plate impulse forecast

Baetens v2, Subject 1, Session 4, Recording 1. Use eight named right-leg EMG channels on the 1 kHz Vicon clock and the filtered 200 Hz Fz export from named floor plates C and D. Each 100 ms target sums the 20 strictly later samples from both plates, reverses the exported signs and multiplies by 0.005 s. The measured result is impulse through these two plates in N·s. Force, marker, pressure and activity-label values are absent from the forecast inputs. [Recording and metadata](https://doi.org/10.25452/figshare.plus.30294658.v2) · [Acquisition and processing](https://doi.org/10.1038/s41597-026-08739-2) · [Versioned author scripts](https://doi.org/10.5281/zenodo.17122076)

## Comparison

The original 1 kHz remote pulses define bouts. The activity order and repetition counts agree with the published roster. The author’s processed segments also used retrospective alignment and trimming. The roster’s availability and force-reliability flags restrict the tested population. For seven activity groups, use repetitions 1–3 for fitting and 4–5 for evaluation. Each history and target fits inside its bout. The 1,683 fitting and 1,096 evaluation windows use disjoint force samples. Forecasts were sealed before converting the later force values into outcomes. Average absolute error within each repetition, then average across repetitions with equal weight.

Each 20 ms EMG bin is centered within the bin. Divide its root mean square by the pooled root mean square of earlier available bins in the same history and apply `log(1 + ratio)`. Require three earlier available bins. Standardize each channel using fitting histories only. Use a masked zero for a missing value. Ridge uses a penalty of 0.01 on all coefficients except the intercept. The 32-wide, four-head attention model applies one shared block one or three times. The paired fits use three seeds, 48 full-batch AdamW updates per seed and matched initialization, order and loss. The reversal check reuses the three-pass weights and reverses the last seven bins.

| Forecast | Equal-repetition MAE (N·s) |
| --- | ---: |
| Fitted median | 9.087110 |
| Ridge | 14.834570 |
| One attention pass | 10.627218 |
| Three attention passes | 10.752295 |
| Three passes with the muscle history reversed | 10.649913 |

In a descriptive split, 901 evaluation windows had an absolute target of at most 1 N·s. For these windows, one-pass attention added 2.564 N·s to the primary error relative to the fitted median. Its gain on the other windows reduced that difference by 1.024 N·s. These contributions use the original equal-repetition weights. The benchmark covers one recorded person. The force export is an offline reference, with no measured live latency or test on a different person in this edition.

## Files and execution

`predict.py` accepts an NPZ file with `history` shaped `[windows, 10, 8]` and a `channels` array. Use `TibialisAnterior`, `GastrocnemiusMedialis`, `GastrocnemiusLateralis`, `VastusMedialis`, `VastusLateralis`, `RectusFemoris`, `Semitendinosus`, and `BicepsFemoris` in that order. Supply the relative RMS values after `log(1 + ratio)`. The program applies the stored training standardization. Use NaN for unavailable bins, including the first three in every window. `ENGINEERING-WEIGHTS.npz` uses plain numerical arrays. `RESULTS.json` gives the exact aggregate scores. `GENERATED-EXAMPLE.npz` supplies two invented histories. Run `python3 -B predict.py GENERATED-EXAMPLE.npz` on Linux or macOS, or `py -3 -B predict.py GENERATED-EXAMPLE.npz` on Windows. Inference reproduced every archived forecast on the tested Linux NumPy and CPU PyTorch build. [Simple guide](README.md)
