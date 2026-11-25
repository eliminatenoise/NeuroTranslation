# Muscle-only floor-plate impulse forecast

Use eight named right-leg surface EMG channels at 1 kHz and the filtered 200 Hz vertical force export from plates C and D. Each forecast uses the 200 ms ending at its issue time. For the 100 ms target, sum 20 strictly later samples from each plate, reverse the exported signs and multiply by 0.005 s. The result is signed impulse through the two named plates in N·s. [Baetens v2 data and licence](https://doi.org/10.25452/figshare.plus.30294658.v2) · [Acquisition](https://doi.org/10.1038/s41597-026-08739-2)

## Fitting and evaluation

Fit on Subject 1, Session 4, Recording 1, repetitions 1–3 of seven activities (1,683 windows, 21 repetitions). Evaluate first on disjoint repetitions 4–5 (1,096 windows, 14 repetitions). Transfer the exact fitted models and scalers to Subjects 2–5, Session 1, Recording 1, using repetitions 4–5 of the same seven activities. The source catalogue's inclusion, muscle and reliable-force flags define eligibility.

In the follow-up, identify each trial by matching unique 32-sample eight-channel waveform anchors to the original recording. The first two anchors must lie between consecutive original fine-button presses. The final anchor must fall within that gap or its closing press. For one waveform the final block did not match uniquely. The unique block starting at 95% of the labeled segment verified the same interval. An offset-based match failed because the author processed endpoints were later than the raw edges. One slow walking repetition was excluded because its anchors did not establish a single accepted gap. The same 1 kHz raw hardware boundaries constrain the entire forecast and target window. The labels and complete waveform matches determine retrospective eligibility. Only past raw EMG enters the predictor. The 4,245 forecasts for 55 repetitions were saved before conversion of any of the new participants' force samples. [Source scripts](https://doi.org/10.5281/zenodo.17122076)

Center each 20 ms bin, divide its root mean square by the pooled root mean square of earlier valid bins within that history, then use `log(1 + ratio)`. Require three earlier bins. Standardize by channel using the fitting histories. Represent missing values by a zero with a separate missingness indicator. The ridge penalty is 0.01, with the intercept unpenalized. Each 32-wide, four-head attention model uses one shared block one or three times. The pairs start identically for each of three seeds and use the same order and 48 full-batch AdamW updates. Average the forecasts from the three independently trained seeds before scoring. Use float32 attention and float64 ridge. The reversal check reuses the three-pass weights and reverses the last seven bins.

## Error in N·s

Average the absolute error per repetition, then weight each repetition equally within a person and each person equally in the follow-up. Compare all five methods on identical windows. The follow-up had no missing or nonfinite targets among the issued rows.

| Forecast | First person, later repetitions | Four new participants |
| --- | ---: | ---: |
| Fitted median (zero) | **9.087110** | **10.063284** |
| Ridge | 14.834570 | 15.890140 |
| One attention pass | 10.627218 | 12.140362 |
| Three attention passes | 10.752295 | 12.120469 |
| Three passes, reversed history | 10.649913 | 11.967637 |

The fitted median had the lowest error for each new person. A descriptive division at absolute measured impulse ≤1 N·s includes 901 first-person windows and 3,407 follow-up windows. In the follow-up, one-pass attention added 3.064 N·s to average error through the near-zero windows and reduced it by 0.987 N·s through the larger-load windows. The reversed order lowered three-pass error for each new person. `RESULTS.json` records the participant scores and contributions. This is an offline comparison in one data collection, with filtered force and retrospective trial screening. The instruments cover two parts of the walkway.

## Run the package

`predict.py` expects an NPZ with `history` shaped `[windows, 10, 8]` and a `channels` array. Use `TibialisAnterior`, `GastrocnemiusMedialis`, `GastrocnemiusLateralis`, `VastusMedialis`, `VastusLateralis`, `RectusFemoris`, `Semitendinosus`, and `BicepsFemoris` in that order. Supply relative bin RMS after `log(1 + ratio)`. Use NaN for unavailable bins, including the first three. The script applies the stored scaling. `ENGINEERING-WEIGHTS.npz` contains numeric arrays.

Open `Launch Linux.sh`, `Launch macOS.command` or `Launch Windows.cmd` from the extracted ZIP. With NumPy and PyTorch available, run `python3 -B predict.py GENERATED-EXAMPLE.npz` on Linux and macOS or `py -3 -B predict.py GENERATED-EXAMPLE.npz` on Windows. The example has two generated inputs. [Download the ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/EMG-Floor-Load.zip) · [Simple guide](README.md)
