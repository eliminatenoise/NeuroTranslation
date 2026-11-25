# Floor load from leg muscle recordings

[Download the models and example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/participant-transfer/Floor-Load-Transfer.zip) · [Technical edition](TECHNICAL.md) · [Exact results](RESULTS.json)

We used electrical recordings from eight right-leg muscles to predict how much load two plates in a walkway would measure over the next tenth of a second. On four people the models had never seen, the best direct prediction missed by **10.16 newton-seconds** on average. Guessing zero missed by **9.87 newton-seconds**. A separate approach that first estimated the chance of a larger load also gave forecasts close to zero.

## The measurements

Electrodes on the skin pick up small voltages as nearby muscles work. This recording is called electromyography, or EMG. The electrodes recorded 1,000 readings per second, and the two plates recorded 200 readings per second. The models used muscle recordings alone. An unloaded plate can occur while someone is standing or moving on another part of the floor. [Baetens dataset and licence](https://doi.org/10.25452/figshare.plus.30294658.v2) · [Recording methods](https://doi.org/10.1038/s41597-026-08739-2)

Each forecast uses the previous 200 milliseconds. We split that history into ten bins and measure the size of the voltage changes in each bin relative to the earlier bins. We subtract the mean of each bin before measuring its size, so a steady voltage contributes little. A logarithm reduces the influence of large ratios. The first three bins have too little earlier history to calculate the ratio, so they are marked missing. The model sees the resulting numbers and knows which entries are missing.

The target is the sum of the force from plates C and D over the next 100 milliseconds. We add 20 future readings from each plate, reverse the recorded sign to express upward ground force as positive, and multiply by the time between readings. The result is called **impulse**. A steady 100-newton force for a tenth of a second gives 10 newton-seconds (N·s). The archived force measurements were filtered after recording and are used to score the predictions.

## The tests

In the first test, each person took a turn as the one held out. The models learned from the other four people and predicted the held-out person's plate readings. This produced 7,024 forecast windows. All five people had contributed recordings to earlier project experiments. The model learned the scales and settings it could fit from its four training participants each time.

For the second test, we fitted the same methods on all five people. We saved the weights before using muscle recordings from four further people, and saved all 4,515 predictions before reading their force samples. We had planned to use the fourth and fifth repetitions of seven activities for each person. The authors' catalogue excluded two of the 56 repetitions. In one more, the labeled muscle recording did not match a unique gap between the original recorder button presses. The remaining 53 repetitions had matching recording intervals and complete force targets. [Author processing code](https://doi.org/10.5281/zenodo.17122076)

## The seven forecasts

- **Zero** always forecasts zero impulse. **Linear fit** adds the muscle readings and their availability flags after multiplying them by learned weights. Both use the training frequency as their chance of a reading above 1 N·s, counting every training person equally and every repetition equally within a person.
- **Direct, one pass** and **Direct, three passes** learn the middle of the possible impulse readings and the chance of exceeding 1 N·s. An attention block lets each time bin use information from the others. Three passes run the same block three times, with the same weights each time.
- **Load first** estimates the chance of exceeding 1 N·s and a range of impulse values on either side of that cutoff. It then picks the middle of those possible values, allowing for their different chances. Below the cutoff it uses readings from the training set. Above it, a fitted model estimates six points across the range. The linear, one-pass and three-pass versions use the same rule.

Each learned attention or load-first method was fitted twice from different starting weights, with 48 updates per fit. We averaged the two forecasts and scored each method on the same windows. We averaged errors within a repetition, then gave each repetition equal weight within a person and each person equal weight. In the columns for readings above 1 N·s, only repetitions and people with such a reading contribute.

## Forecast errors

Each number gives the average size of the error in N·s. Smaller numbers are better.

| Forecast | Five known people, all windows | Four new people, all windows | Five known people, above 1 N·s | Four new people, above 1 N·s |
| --- | ---: | ---: | ---: | ---: |
| Zero | **9.81** | **9.87** | 52.11 | 56.77 |
| Linear fit | 15.99 | 16.45 | **43.46** | **48.06** |
| Direct, one pass | 10.50 | 10.52 | 51.01 | 55.72 |
| Direct, three passes | 10.26 | 10.16 | 51.95 | 56.61 |
| Load first, linear | **9.81** | **9.87** | 52.11 | 56.77 |
| Load first, one pass | **9.81** | **9.87** | 52.11 | 56.77 |
| Load first, three passes | **9.81** | **9.87** | 52.11 | 56.77 |

Three passes reduced the direct forecast's overall error for each of the nine separately scored people. They improved on zero for one of the four new people. The linear fit came closest on the stronger positive readings and had the largest error across all windows. The load-first methods had the same average error as zero to the precision shown in the table. The load-first three-pass version returned zero on every window in both tests. On the four new people, the load-first one-pass version returned nonzero values on three windows, up to 0.012 N·s in size.

Of the 7,024 windows for known participants, 1,322 were above 1 N·s. Of the 4,515 windows for new participants, 750 were above it. The new test also had 926 readings below −1 N·s, all from one participant. The measurements are signed and all of those readings count in the error. A reading at or below 1 N·s therefore includes negative as well as near-zero readings. The study did not determine the cause of that recording's negative readings.

We also checked each forecast's chance of exceeding 1 N·s. We squared the distance between the probability and what happened, using 1 if the reading exceeded 1 N·s and 0 otherwise. The lower the score, the closer the probabilities were to the observed readings.

| Forecast | Probability error on five known people | Probability error on four new people |
| --- | ---: | ---: |
| Zero or linear fit | 0.15529 | 0.14176 |
| Direct, one pass | **0.15148** | **0.13958** |
| Direct, three passes | 0.15401 | 0.14133 |
| Load first, linear | 0.15506 | 0.14070 |
| Load first, one pass | 0.15176 | 0.13963 |
| Load first, three passes | 0.15390 | 0.14123 |

With a rule that calls a load only above 50% probability, every method missed all of the above-threshold windows. One direct forecast went above 50% on a window that stayed at or below 1 N·s. The small improvement in probability scores applies at the reported probabilities. These experiments used one recording collection, the same two-plate setup and stored readings. Live forecasts and transfer to another recording setup still need their own tests.

## Run the example

1. Download and extract **Floor-Load-Transfer.zip**. Open the extracted folder. Install Python 3 with NumPy and PyTorch. The saved weights are included.
2. Open `Launch Linux.sh`, `Launch macOS.command` or `Launch Windows.cmd` for your system. On Linux, choose **Run in Terminal** if your file manager asks. From a terminal in the extracted folder, use `python3 -B predict.py EXAMPLE.npz` on Linux or macOS, or `py -3 -B predict.py EXAMPLE.npz` on Windows.
3. Read the `impulse` and `load_probability` sections in the output. Each has two results per method, one for each generated input in `EXAMPLE.npz`. The impulse is in N·s. Each probability is a number between 0 and 1. The example uses invented muscle traces to show how the program works. The tables above use recorded measurements.

To supply your own **prepared** inputs, make a NumPy `.npz` file with `history` and `channels` arrays. `history` needs one row per forecast, with ten time bins and eight muscle values per bin. Enter the log-adjusted ratios described above. The program applies the scales learned in training. Use `NaN` for missing values and for all of the first three bins. Copy the eight muscle names and their order from the example's `channels` array. The technical edition gives the exact calculation for each bin. The package was run on Linux. The macOS and Windows launchers were checked as source. [Input specification](TECHNICAL.md#run-the-saved-models)
