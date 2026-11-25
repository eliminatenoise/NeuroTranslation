# Decline treadmill muscle-to-load comparison

The lowest mean per-plate error was **21.966 N·s** for 200 ms with three attention passes, against **26.792** for the fitting median. The 1 s five-pass model had the lowest summed error at **19.300 N·s** against **30.324**. The 1 s affine model had the lowest event Brier score at **0.1326** against **0.2192**. [Simple edition](README.md) · [Exact scores and contrasts](RESULTS.json)

[Download the saved models and comparison](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/decline-treadmill/Decline-Treadmill.zip).

## Signal and sample clock

Use the C3D physical plate order. Each target is `−sum(Fz[t:t+200]) / 2000` in N·s, from the two calibrated Type-2 plate-local force columns. Positive values denote compression. The original acquisition rates are 1,259 Hz for EMG and 1,000 Hz for force. The C3D channels share a stored 2,000 Hz grid. At issue sample `t`, take the 20 100-sample bins of `[t−2020,t−20)`. Use `log10(max(RMS volts, 1e−6))` per muscle and bin. The 200 ms variants take the last four bins. Match each named author voltage trace to one signed native channel on an early one-second segment. Physical timing at the devices and anatomical foot identity remain unverified. [Author archive and licence](https://doi.org/10.35090/gatech/70296) · [Collection and clock methods](https://doi.org/10.1038/s41597-023-02840-6)

Use the author-marked `down5` interval of `incline_walk_1`. Issue on the 200-sample grid with full input and outcome support within the interval. Six participants supplied 1,060 fitting windows. Four distinct participants supplied 712 held keys. An earlier squat study used these same participants on another task. Seal the weights, predictions and target indices before interpreting the held force samples. The paired-load rule requires each plate to show at least one window above 1 N·s when the other plate is at or below 1, plus a peak above 10 N·s on each plate. One recording with 173 finite pairs failed the first requirement because Plate 1 exceeded 1 N·s throughout, including all 131 above-threshold Plate 2 windows. The primary comparison retained 539 windows from three participants.

## Matched models

The zero and median baselines output the participant-weighted fitting event rate for class probability. The affine models take flattened short or long histories. The attention model uses 32 channels inside the model, four heads, a 64-wide feed-forward layer and 20 learned time positions. The last hidden state after one, three or five passes gives both impulse and event outputs. Each attention variant has 9,924 parameters. Give each fitting participant equal weight and standardize the inputs from fitting data. Minimize absolute impulse error divided by the median fitting impulse strictly above 1 N·s, plus 0.25 binary cross-entropy. Use AdamW at 0.001, weight decay 0.0001, batch size 128 and 48 epochs for each of two seeds. Fitting and inference use FP32, then the program averages the two forecasts.

## Held results

Average the absolute impulse error and the event probability squared error within participant and plate, then average across plates and participants. The combined column scores the sum before taking the absolute error. For conditional errors, score each plate's cases above the threshold or at and below it, then average across plates and participants. All impulse errors are in N·s.

| Forecast | Plate 1 | Plate 2 | Mean | Combined | Probability score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Always predict zero force | 31.37 | 32.37 | 31.87 | 63.73 | 0.2192 |
| Typical load from fitting | 26.59 | 27.00 | 26.79 | 30.32 | 0.2192 |
| Linear fit, 200 ms | 29.29 | 27.13 | 28.21 | 21.15 | 0.2149 |
| Linear fit, 1 s | 24.41 | 28.88 | 26.65 | 43.37 | 0.1326 |
| Attention, 200 ms, 1 pass | 33.42 | 17.50 | 25.46 | 22.99 | 0.2260 |
| Attention, 200 ms, 3 passes | 29.24 | 14.70 | 21.97 | 22.45 | 0.2072 |
| Attention, 200 ms, 5 passes | 30.89 | 13.92 | 22.40 | 26.91 | 0.2003 |
| Attention, 1 s, 1 pass | 21.05 | 23.89 | 22.47 | 20.65 | 0.2170 |
| Attention, 1 s, 3 passes | 19.71 | 25.15 | 22.43 | 20.91 | 0.2291 |
| Attention, 1 s, 5 passes | 20.24 | 23.93 | 22.08 | 19.30 | 0.2184 |

Relative to the fitting median, three short passes changed mean per-plate error by **−4.826 N·s** `[−13.501, 1.478]` and lowered error for two of three people. Five short passes increased that error against three by **0.438 N·s** `[0.198, 0.787]` and lowered Brier error for three of three. Five long passes reduced summed error against the median by **11.024 N·s** `[5.853, 13.942]` and helped three of three. The long affine model reduced Brier error by **0.0866** and helped three of three. Ranges are percentile intervals from 20,000 paired participant resamples. Three recordings give a limited test of performance across people.

The retrospective sensitivity includes all 712 paired windows from four participants with equal weight. The 1 s five-pass and one-pass mean per-plate errors were **19.572** and **19.581 N·s**. The original 200 ms three-pass leader ranked fourth at **20.091 N·s**. The 200 ms affine model led combined impulse at **18.179 N·s**. The 1 s affine model still led event Brier score at **0.1482**. The sensitivity reuses the fixed forecasts and the same authorized outcome rows.

## Replay and prepare inputs

Open the extracted **Compare Results.html** to inspect the scores. Install NumPy with `python3 -m pip install numpy` on Linux and macOS or `py -3 -m pip install numpy` on Windows. Install PyTorch for the same interpreter. Use `sh "./Launch Linux.sh"` or `sh "./Launch macOS.command"` in a terminal, or `".\Launch Windows.cmd"` in Command Prompt. The example is generated. For prepared data, `predict.py` accepts `history` of shape `(N, 20, 16)` and `muscles` in the order in `MODEL.json`. Pass the file after `python3 predict.py` or `py -3 predict.py`. The extracted Linux package ran, and the macOS and Windows launchers were reviewed as source.

For the original C3D source, install `c3d` and SciPy to use `read_signal.py`. Call `open_trial`, `match_emg` with the same-trial author voltage CSV, `activity_bounds` with the up and down metadata and activity flag, and `windows` with the qualified bounds. Keep only its complete histories. The program's input contract and both physical plate columns are traceable to the source archive above. The included trained weights and project code use the package licence. [PyTorch installation](https://pytorch.org/get-started/locally/)
