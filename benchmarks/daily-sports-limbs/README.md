# Five places to forecast the next reading

Pick the sensor on a walker’s left leg. Give NeuroTranslate 0.0 its last 16 readings. What will the accelerometer read 120 milliseconds later? Switch to the right arm and ask the same question. One checkpoint handles both arms, both legs and the torso. Each forecast stays in the local axes of the sensor you chose.

## Try it

The examples are real readings from the first parking-lot walking segment used for training. From this folder, use an environment with Python 3.13, NumPy and CPU PyTorch. The recorded run used NumPy 2.4.6 and PyTorch 2.14.1+cpu.

```sh
python -m pip install -r requirements.txt
python predict.py left_leg examples/left_leg.json
python predict.py right_arm examples/right_arm.json
```

Choose `left_arm`, `right_arm`, `left_leg`, `right_leg` or `torso`, with the matching file in `examples/`. To use another comparable 25 Hz recording, supply 16 complete XYZ rows in the same placement, local axes, scale and units. Include the placement and 16 integer timestamps in milliseconds. The input reader checks the placement and the 40 ms spacing. It cannot identify a misplaced or rotated sensor from those declarations. A camera image or a file of joint angles needs a different model.

The command prints the forecast, the time it addresses, and what persistence and ridge predict for those same axes. It also reports the model’s estimated standard deviation. Its uncertainty on a new walker remains untested. The included examples contain the past readings only. A separate file gives the three recorded values that came next at the requested time, alongside the saved forecasts. [Recorded examples and measured targets](recorded-examples.json) · [What the game, camera and model each support](CAPABILITIES.md)

## Four walkers, two conditions

Four people walked in a parking lot and on a flat treadmill at 4 km/h. Each wore five sensor units. The model saw one unit at a time, and each unit had its own normalization, input and output layers. The network in between learnt from all five. Inputs and targets came from the same sensor in the same five-second clip. Each forecast used 16 samples spanning 600 ms, then predicted the reading three samples beyond the last observation.

The table gives mean absolute error across XYZ in each sensor’s stored units. Lower is better within a row. There were 3,360 windows per row, all from the four people used for fitting. The five views cover the same 480 walking clips.

| Placement | Repeat last reading | Ridge | Shared model | Earlier right-arm model |
|---|---:|---:|---:|---:|
| Torso | 1.284 | **0.696** | 0.722 | — |
| Right arm | 1.165 | 0.869 | 0.806 | **0.668** |
| Left arm | 1.057 | 0.770 | **0.727** | — |
| Right leg | 3.150 | 1.967 | **1.891** | — |
| Left leg | 3.168 | 1.929 | **1.837** | — |

Only the left leg met the rule set before training: the shared model had to beat each available comparator for each person. Pooled averages hide reversals on the left arm and right leg. Ridge gave the lowest pooled error for the torso. The earlier right-arm model, fitted for that placement alone, gave the lowest pooled error for the right arm. Every comparison here uses TRAIN recordings. We have yet to test this checkpoint on a new person. [Results for every participant, activity and axis](results.json) · [Frozen protocol](protocol.json)

## Reproduce the fit

Use the original UCI archive and keep the neighbouring `daily-sports-arm` benchmark in place. It supplies the previous right-arm model and ridge coefficients. The loader verifies the original archive digest and opens only the walking files for p1 through p4. It leaves p5 through p8 outside this study. The runner creates a fit intent in the output directory before loading the data and refuses to reuse that directory.

```sh
python test_limb.py
python train.py fit --threads 2 --archive daily+and+sports+activities.zip --out new-fit
```

The frozen model has 45,997 parameters and ran for 12 epochs, 3,180 optimizer updates in all. The code checks source, clip, time and placement before each update. Reopening the checkpoint reproduced every stored TRAIN prediction on the original batch layout. A single-row call can differ slightly in the last decimal places because the CPU can select another numerical kernel.

Billur Barshan and Kerem Altun provided *Daily and Sports Activities*, DOI 10.24432/C5C59F, under CC BY 4.0. This study uses their recorded local accelerometer values. Any claim about a joint angle, neural activity, force, transfer to a new participant or clinical outcome requires evidence for that quantity. [UCI data and original archive](https://archive.ics.uci.edu/dataset/256/daily) · [Attribution](NOTICE.md)
