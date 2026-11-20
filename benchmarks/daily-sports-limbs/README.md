# What will a walker’s leg sensor read next?

A person walks across a parking lot with a sensor strapped to each arm, each leg and the middle of their body (the torso). Each sensor is an accelerometer. Take the one on the left leg. Its reading changes as the leg speeds up, slows down or tilts relative to gravity. It measures along three directions, labelled X, Y and Z on the instrument. Can the past 16 readings from one sensor tell us what **that same sensor** will read 120 milliseconds later?

NeuroTranslate 0.0 is the computer model making the forecast. It learned from recordings of four walkers. Choose **Left leg** in the demo. For the first walker, 600 milliseconds into the recording, the X reading was −11.205. The model predicted −11.228 for 720 milliseconds. The sensor recorded −10.005. These are the units stored by the instrument. This walk was part of the model’s training. How well it predicts a new walker remains an open question.

## Open the local demo

You need Python 3.13 and the two software libraries listed in [requirements.txt](requirements.txt). Download or clone the repository and open a terminal in this folder. Use these two commands to install the libraries in your Python environment and open the demo.

```sh
python -m pip install -r requirements.txt
python serve.py
```

After installing the libraries, you can also start the demo with the launcher for your computer. Your browser opens a graph of the last 16 readings. Each open circle is a prediction. A square shows what the sensor actually recorded at that time. Change the body part to try the same model on another sensor. Press Ctrl+C in the terminal to close the demo. [Windows launcher](<Open on Windows.cmd>) · [macOS launcher](<Open on macOS.command>) · [Linux launcher](<Open on Linux.sh>)

## Try the command line

The examples come from that same parking-lot walk. The recorded run used NumPy 2.4.6 and PyTorch 2.14.1+cpu. These commands read the left leg and the right arm.

```sh
python predict.py left_leg examples/left_leg.json
python predict.py right_arm examples/right_arm.json
```

Choose `left_arm`, `right_arm`, `left_leg`, `right_leg` or `torso`, with the matching file in `examples/`. To try another recording sampled 25 times a second (25 Hz), supply 16 rows with all three readings from the selected body part. The sensor must face the same way and use the same scale and units. Include the placement and 16 integer timestamps in milliseconds. The input reader checks the placement and the 40 ms spacing. It cannot identify a misplaced or rotated sensor from those declarations. A camera image or a file of joint angles needs a different model.

The command prints the forecast, its time and two simpler predictions. One repeats the last reading (persistence). The other learns how much weight to give each past value while limiting the size of those weights (ridge regression). The model also estimates how widely readings might vary around each prediction, reported as a standard deviation. That estimate has yet to be checked on a new walker. The included examples contain the past readings only. A separate file gives the three recorded values that came next at the requested time, alongside the saved forecasts. [Recorded examples and measured targets](recorded-examples.json) · [What the game, camera and model each support](CAPABILITIES.md)

## Four walkers, two conditions

Four people walked in a parking lot and on a flat treadmill at 4 km/h. Each wore five sensor units. The model reads one sensor at a time. It rescales the numbers separately for each body part and uses separate input and output layers for each one. The layers between them learn from all five. Inputs and targets came from the same sensor in the same five-second clip. Each forecast used 16 samples spanning 600 ms, then predicted the reading three samples beyond the last observation.

How far did a prediction miss the reading? The table gives that distance averaged over all three directions and all predictions, in the sensor’s stored units (mean absolute error). Smaller is better within a row. There were 3,360 windows per row, all from the four people used for fitting. The five views cover the same 480 walking clips.

| Placement | Repeat last reading | Ridge | Shared model | Earlier right-arm model |
|---|---:|---:|---:|---:|
| Torso | 1.284 | **0.696** | 0.722 | — |
| Right arm | 1.165 | 0.869 | 0.806 | **0.668** |
| Left arm | 1.057 | 0.770 | **0.727** | — |
| Right leg | 3.150 | 1.967 | **1.891** | — |
| Left leg | 3.168 | 1.929 | **1.837** | — |

Only the left leg met the rule set before training: the shared model had to make smaller errors than every other method for each person. Averages across all four people hide reversals on the left arm and right leg. Ridge gave the lowest pooled error for the torso. The earlier right-arm model, fitted for that placement alone, gave the lowest pooled error for the right arm. All these comparisons use the recordings the model learned from. A test on a new person is still needed. [Results for every participant, activity and axis](results.json) · [Frozen protocol](protocol.json)

## Reproduce the fit

Use the original UCI archive and keep the neighbouring `daily-sports-arm` benchmark in place. It supplies the previous right-arm model and ridge coefficients. The loader verifies the original archive digest and opens only the walking files for p1 through p4. It leaves p5 through p8 outside this study. Choose a new, empty output directory. Before loading the data, the runner creates an exclusive intent file. An existing intent blocks a second run.

```sh
python test_limb.py
python train.py fit --threads 2 --archive daily+and+sports+activities.zip --out new-fit
```

Training adjusted 45,997 values inside the model (parameters) over 12 passes through the training set (epochs), for 3,180 updates in all. The code checks source, clip, time and placement before each update. Reloading the saved model reproduced every training prediction when the examples were processed in the original groups. A single-row call can differ slightly in the last decimal places because the CPU can select another numerical kernel.

Billur Barshan and Kerem Altun provided *Daily and Sports Activities*, DOI 10.24432/C5C59F, under CC BY 4.0. This study uses their recorded local accelerometer values. Any claim about a joint angle, neural activity, force, transfer to a new participant or clinical outcome requires evidence for that quantity. [UCI data and original archive](https://archive.ics.uci.edu/dataset/256/daily) · [Attribution](NOTICE.md)
