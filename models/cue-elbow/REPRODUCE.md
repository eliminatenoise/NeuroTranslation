# Reproduce the elbow forecast

## Use the fitted models

Choose the launcher for Windows, macOS or Linux. It runs in a terminal with Python 3.10 or newer and opens the invented example in this folder. No data download or Python package installation is needed for that example. A command-line equivalent is shown below. If macOS requires confirmation for a downloaded file, run the script in Terminal using the system's normal security settings.

```sh
python infer.py
python infer.py --input example.json --method cue_mechanics_c3
python check_example.py
```

Each estimate is signed change in the elbow sensor's native units between two eight-sample medians. Positive means increasing sensor output. Anatomical direction and physical amplitude require calibration. To change inputs, copy example.json and edit the cue and the four numbers per channel. The array order is oldest to newest. Set cue to `flexion` or `extension`. The file contains four elbow medians, four EEG means and four eye means. All six methods run by default. A single selected method reads only its required input fields. The shifted-pairing control exists only in the offline trial comparison.

With NumPy installed, `python infer.py --backend numpy` uses NumPy for the standardized linear prediction. `python check_example.py --backend numpy` checks its output against the same six saved numbers.

## Refit from original recordings

Install NumPy in a Python 3.10+ environment. The reference fit used NumPy 2.5.5 and Python 3.13.15. The fetch step takes about 270 MB. Choose empty directories for originals and refit outputs. Keep the original recordings outside the material you distribute.

```sh
python ofner_source.py fetch ../ofner-execution-cache
python ofner_source.py verify ../ofner-execution-cache
python fit.py --cache ../ofner-execution-cache --out ../elbow-refit
python check_rebuild.py ../elbow-refit
```

The local [channel and event table](codebook.json) gives both publisher and header labels. The acquisition script verifies the official v1 record, the selected filenames, byte counts, publisher MD5s and recorded SHA-256 digests. The read path checks the header, sample rates, encoding, scale, clock and channel order before accessing native windows. Fitting consumes only the two elbow cue classes in execution runs 1, 2 and 3 of S1. The fit script stops on a count, boundary, signal or protocol mismatch. No trial array or individual prediction is written.

The refit produces model.json and scores.json. Compare both with the shipped copies. Low-level floating-point implementations can differ in their last digits. The check compares floating-point leaves with absolute and relative tolerance of 1e-10, and checks integer counts, types, text, list lengths and keys exactly. SHA256SUMS records the delivered bytes.

## Calculate the features

Let `t` be the zero-based cue tick on the 512 Hz event clock. The last permitted input is tick `t+128`. The EEG segment begins at `t−127` and ends at `t+128`, both included. The four bins contain 64 samples each. Compute their arithmetic means from C3, one-based channel 28. For an eye-channel control, compute the same four means for channels 62, 63 and 64 and average the channels within each bin. The authors' table and the GDF header disagree on which outside eye channel is left or right. Averaging treats them symmetrically and can cancel activity of opposite polarity.

The elbow sensor is channel 93. Take the last 32 samples ending at `floor((t+128)/8)` on its 64 Hz clock. Split them into four groups of eight, oldest first. Take each median. The target is the median of the eight samples ending at `floor((t+512)/8)` minus the fourth input median. The two elbow endpoints have the same sampling phase because they are 48 elbow samples apart. A sample on the elbow clock can precede its requested tick by as much as seven EEG ticks. There is no interpolation or post-cutoff filtering.

The mechanical model takes the extension indicator, the fourth elbow median, and the last three successive changes ordered newest first. The C3 model adds three signal features, each a later bin mean minus the first. The eye comparison substitutes the corresponding three eye features. Each fit subtracts its training feature means, divides by its training population standard deviations, centres the target at its training mean and solves ridge regression with penalty 6. The score for standardized input vector `z` is `intercept + z · weights`. All ridge weights and scales are in model.json. Two simpler baselines predict zero change or the training median for the given cue.

The attention comparison centres four C3 means at the first bin. It divides them by the training root mean square across all four centred bins, clips each to [−4, 4] and compares each with the last bin by multiplication. The fixed recency offsets are −0.75, −0.5, −0.25 and 0. Exponentiating and normalizing those four scores gives the weights for a weighted average of the clipped bins. One pooled value joins the mechanical features in the same ridge fit. Twenty-four training trials per fold support this deliberately small architecture comparison. The attention weights vary with the input. Only the common training scale and the linear prediction head are fitted.

The scoring control takes each fitted C3 model and gives it another trial's C3 means at evaluation. It substitutes the **next** flexion trial within the same held run for a flexion trial, and likewise for extension, wrapping at the last trial in each group. Mechanics, targets and cue stay with the recipient. The donor can occur later in the recording. This deliberately broken pairing tests whether the correct trial's EEG matters to the fitted model. It is unavailable as a real-time input.
