# Floor load from leg muscle signals

The decline treadmill study tests muscle-based forecasts on four people who walked at a steeper slope than the fitting group. It compares what the models learn from muscle readings alone and what changes when body mass and slope are supplied. The download includes both sets of compact forecasts and the earlier 5° test. [Decline treadmill results and saved models](decline-treadmill/)

A follow-up fitted the models on five people, then checked predictions on four further people from the same recording collection. [Follow-up results and downloads](participant-transfer/)

A forecast of zero was closer to the measurements than any of the learned forecasts for each of four new participants. The same forecast also had the lowest error in an earlier check on the person who supplied the training data. The models estimated force through two plates in a walkway. Most recorded windows had very little load on those plates.

## What was recorded

Electrodes on the skin of the right leg picked up small voltages as eight muscles worked. This type of recording is called electromyography, or EMG. It measures muscle activity. A separate pair of force plates measured the downward load on two parts of the walkway. A person could be moving or pushing against the floor elsewhere while these two plates measured very little. The records come from the Baetens gait collection. [Dataset and licence](https://doi.org/10.25452/figshare.plus.30294658.v2) · [Recording methods](https://doi.org/10.1038/s41597-026-08739-2)

The recorder took 1,000 muscle readings and 200 force readings per second. Each forecast used the previous 200 milliseconds of muscle activity to estimate the force through both plates over the following 100 milliseconds. The target adds 20 later readings from each plate, adjusts their sign to make upward ground force positive, and multiplies by the time between readings. The result is called **impulse**. It is measured in newton-seconds (N·s). For example, a steady force of 100 newtons for a tenth of a second gives an impulse of 10 N·s.

## How the comparison worked

The fit used 1,683 windows from one person, taken from the first three repetitions of each of seven activities. The first check used 1,096 windows from two later repetitions per activity by the same person. The follow-up kept the fitted models and their settings fixed and checked recordings from four other people. The choices were made from the published list of trials before reading force from those people.

The authors' processed files mark which activity and repetition each muscle recording came from. We matched short pieces from the beginning, middle and end of each labeled recording to the original muscle measurements. We checked that the first two pieces pointed to the same gap between a pair of original recorder button presses and that the late piece still fit the gap or its final press. The original buttons set the study boundaries. Only the earlier raw muscle signals entered a forecast. One slow-walking repetition had conflicting timing and was left out. All forecasts from the other 55 repetitions were saved before reading the selected force samples. [Author processing code](https://doi.org/10.5281/zenodo.17122076)

The models receive ten time bins that cover the 200 milliseconds. In each bin, we measure the size of voltage changes relative to the earlier bins in the same window. A logarithm limits the influence of very large ratios. To calculate a ratio we need three earlier bins, so the first three are marked unavailable. The program uses the scale learned from the training recordings for each muscle.

- **Zero forecast.** Find the middle observed impulse in the fitting data, giving each repetition equal weight. That value was zero. Use it for every window.
- **Fitted linear model.** Give each muscle reading a learned weight and add the weighted values. A setting of 0.01 discourages very large weights. This method is also called ridge regression.
- **One attention pass.** The model compares the time bins in a small block with 32 internal values per bin and four parallel comparisons. The block runs once.
- **Three attention passes.** The same kind of block runs three times, using the same weights on each pass. Both versions used the same three starting states. We trained each starting state separately for 48 updates. For each version, we averaged the three forecasts into one before scoring. The attention fits used 32-bit numbers and the linear fit used 64-bit numbers.
- **Three passes with the history reversed.** Use the saved three-pass model and give it the final seven time bins in reverse order. This checks how much the forecast benefits from seeing those readings in their recorded order.

## Results

Each number is the average size of a forecast's error in newton-seconds. Smaller values are better. We first averaged the windows within each repetition. Each repetition had equal weight within a person, and each new person had equal weight in the follow-up. This kept a long recording from deciding the result on its own.

| Forecast | Later repetitions from the first person | Four new participants |
| --- | ---: | ---: |
| Zero | **9.087** | **10.063** |
| Fitted linear model | 14.835 | 15.890 |
| One attention pass | 10.627 | 12.140 |
| Three attention passes | 10.752 | 12.120 |
| Three passes with the history reversed | 10.650 | 11.968 |

After scoring the forecasts, we grouped the windows by measured impulse. In the first check, 901 of 1,096 windows were within 1 N·s of zero. In the four-person check it was 3,407 of 4,245. Compared with the zero forecast, the one-pass model's errors on the near-zero windows added 3.064 N·s to the four-person average. Its improvement on the higher-load windows brought the average down by 0.987 N·s. Both amounts use the same weights as the table, so the one-pass error was 2.077 N·s higher overall. Reversing the history slightly reduced the three-pass error for all four people. The full per-person results are in `RESULTS.json`.

The findings cover recordings from one collection and use force readings filtered after recording. Other instruments, activities and live forecasts need their own measurements. The four-person follow-up checks how these exact models worked on new participants in the same collection.

## Run the example

1. Download and extract **EMG-Floor-Load.zip**. Use Python with NumPy and PyTorch installed. The download includes the saved weights.
2. Open `Launch Linux.sh`, `Launch macOS.command` or `Launch Windows.cmd` for your computer. On Linux, choose **Run in Terminal** if your file manager asks.
3. To run from a terminal inside the extracted folder, enter `python3 -B predict.py GENERATED-EXAMPLE.npz` on Linux or macOS. On Windows, enter `py -3 -B predict.py GENERATED-EXAMPLE.npz`.

Each command prints the five forecasts for two generated muscle histories. The table above comes from the recorded measurements.

To use your own prepared file, follow the example's NumPy file format. The `history` array has one row per forecast, with ten time bins and eight muscle readings in each bin. In the `channels` array, list tibialis anterior first, then gastrocnemius medialis, gastrocnemius lateralis, vastus medialis, vastus lateralis, rectus femoris, semitendinosus, and biceps femoris. The Technical guide gives the exact labels to put in the file. Supply the transformed ratios explained above. Use `NaN` to mark a missing value, including all readings in the first three bins. Run the same command with your file name in place of `GENERATED-EXAMPLE.npz`. [Download the ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/EMG-Floor-Load.zip) · [Technical guide](TECHNICAL.md)
