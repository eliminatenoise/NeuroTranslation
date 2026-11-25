# Predicting floor load from muscle signals

Two force plates in a walkway measured how hard a foot pressed on them. Eight sensors on one person’s right leg measured small voltages as the muscles worked. This experiment used the previous 200 milliseconds of muscle signals to predict the load on the plates over the next 100 milliseconds.

A fixed guess of zero had the smallest average error. After scoring, we split the windows using what the plates had measured. In 901 of the 1,096 windows the impulse was within 1 newton-second of zero. On the other windows, the one-pass attention model was closer to the measurement than the zero forecast. Its extra errors in the near-zero group outweighed that gain. A foot can be moving or pressing on the floor outside these two plates.

| Forecast | Mean absolute error |
| --- | ---: |
| Same fitted guess for every window | 9.087 N·s |
| Fitted linear model | 14.835 N·s |
| One attention pass | 10.627 N·s |
| Three attention passes | 10.752 N·s |
| Three passes with the muscle history reversed | 10.650 N·s |

A newton-second (N·s) measures force over time. Holding 100 newtons for a tenth of a second gives 10 newton-seconds. For each of seven activities, the fits used the first three repetitions and the check used the next two. Each of those 14 later repetitions contributed equally to the average error. This check used one person’s previously recorded session and the instrument’s filtered force readings. A different-person or live test would need its own measurements.

## Run the example

1. Download and extract **EMG-Floor-Load.zip**. Use Python with NumPy and PyTorch installed.
2. Open `Launch Linux.sh`, `Launch macOS.command` or `Launch Windows.cmd` for your computer. On Linux, choose **Run in Terminal** if the file manager asks. The launchers run two invented examples and print the five forecasts in newton-seconds.
3. To run the same examples from a terminal in the extracted folder, enter `python3 -B predict.py GENERATED-EXAMPLE.npz` on Linux or macOS. On Windows, enter `py -3 -B predict.py GENERATED-EXAMPLE.npz`.

The example inputs are invented. The score table above uses the recorded muscle and force data. See [Technical guide](TECHNICAL.md) for the recording, timing and input format. [Download the ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/EMG-Floor-Load.zip) · [Source data and attribution](https://doi.org/10.25452/figshare.plus.30294658.v2)
