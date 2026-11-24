# Hand movement from individual electrode readings

[Package overview](README.md) · [Technical edition](TECHNICAL.md) · [Aggregate measurements](results.json)

## What the model predicts

This NeuroTranslate model estimates how far and in which direction a hand will move in the next tenth of a second. It reads measurements from the primary motor cortex, a brain area involved in movement. A recording electrode reports when the voltage crosses a threshold. Each channel gives counts of those events from one electrode. The model sees which channel supplied each count. An electrode can pick up activity from more than one neuron.

In each example the model reads 200 milliseconds of activity before the forecast. That time is divided into ten bins of 20 milliseconds each. The input has 96 rows, one for each electrode in the archive numbered 96 through 191. Each row gives the count from the oldest bin through the most recent. The model gets no hand positions or task cues. It predicts the horizontal and vertical changes in the measured hand position in millimetres. It separately learns to estimate straight-line travel distance. Since the model learns that third answer separately, it can differ from the length of the predicted horizontal and vertical movement. [Recordings](https://dandiarchive.org/dandiset/000070/0.261122.2046) · [How the archive identifies electrodes](https://github.com/catalystneuro/shenoy-lab-to-nwb/blob/debff6465a6ca3bd3db7843578d88bff3fac5bf8/maze_task_unsorted/shenoymatdatainterface.py#L99-L118)

## Three recordings from the same animal

All examples come from a rhesus macaque recorded on different days. Fitting uses examples with measured answers so the model can learn. Development uses a separate part of the archive to inspect the model's behaviour. Held evaluation means the measured answers stay closed until the forecasts have been saved. The held recording in this study was made three days before the fitting recording.

| Recording | How it was used | Trials | Forecast windows |
|---|---|---:|---:|
| 23 September 2010 | Fit the models | 3,694 | 55,878 |
| 22 September 2010 | Compare forecasts during development, final quarter only | 586 | 7,767 |
| 20 September 2010 | Score fixed forecasts on a separate recording day | 3,404 | 44,701 |

The archive marked 640 of the 4,044 September 20 trials for exclusion. A usable example had to contain a complete 200 ms record from every electrode and a measured hand position exactly 100 ms after the forecast. The start of each history uses the exact source time 200 samples earlier. A voltage crossing exactly at a shared edge belongs to the next history, so adjacent histories do not count it twice.

## What changed between the models

The pooled model uses averages and the amount of variation across the 96 channels. Swapping their labels leaves nearly the same pooled readings. The ordered model adds eight learned ways of weighing the electrode readings separately in each time bin. A computer program reads short time sequences, looks across successive readings and refines its internal estimate three times. It stores 24 numbers at each step. The ordered model has 10,251 adjustable values and the pooled model has 8,907.

The matched shuffled model has the same 10,251 adjustable values as the ordered one. It receives the entire ten-bin history for each electrode, but those histories are shuffled independently for each example in training and during replay. The total activity is preserved. A separate test uses an ordered model that was fitted normally, then connects histories to the wrong channels using three fixed patterns. The simplest comparison always predicts the same ending position as the starting position.

Each of the three learned versions was fitted three times. For each matched run, the models started with the same random seed and received the same draw of recorded examples. Each step took 128 examples and the learning program made 2,400 updates. It used 32-bit floating-point arithmetic, the AdamW adjustment method, a learning rate of 0.002 and a weight decay of 0.001. The smooth L1 rule measures prediction differences and softens the influence of large misses. Its transition was set to 0.2 after dividing outputs by 100 mm.

## Accuracy on the held and development recordings

Vector error measures how far apart the estimated and measured ending points are. It increases for a wrong direction or a wrong distance. Distance error compares just the separately estimated length of the movement with the length the hand actually moved. Each trial contributes equally to the result, even if it contains fewer windows. The values also average over the three separate models and the appropriate shuffle replays.

| Method | Held vector | Held distance | Development vector | Development distance |
|---|---:|---:|---:|---:|
| Keep each electrode's own readings | 4.65 | 3.11 | 8.59 | 7.31 |
| Combine activity across electrodes | 9.06 | 5.51 | 9.84 | 7.96 |
| Shuffle readings during training and replay | 9.45 | 5.58 | 10.06 | 7.84 |
| Use the wrong connections when making a forecast | 17.13 | 11.84 | 25.67 | 19.61 |
| Assume the hand stays put | 9.23 | 9.23 | 8.33 | 8.33 |

All errors are in millimetres. On the held recording, keeping each electrode's readings in place reduced ending-position error by an average of 4.80 mm compared with the same-sized model trained and replayed with shuffled readings. Drawing the same trials for both methods 4,000 times gave a paired 95% interval of 4.74 to 4.86 mm for that difference. The travel-distance errors differed by 2.48 mm, with an interval of 2.42 to 2.54 mm. These ranges describe how the difference varied among trials from that day. On the development recording, assuming the hand stayed put gave the lowest ending-position error.

We added a breakdown by actual movement size after reading development and before reading the held outcomes. For movements of at least 20 mm in the held recording, the ordered model's average ending-position error was 18.63 mm. Assuming no movement gave 49.47 mm of error in those same cases. For movement under 2 mm, assuming no movement averaged 0.34 mm and the ordered model averaged 1.06 mm. A forecast cannot know the actual movement ahead of time. Those groups help explain the result after the recording is scored.

## Install and run the example

1. Extract the download and open the folder in a terminal. Install Python 3.12 if needed. On Linux or macOS, run `python3.12 -m pip install -r requirements.txt`. On Windows, run `py -3.12 -m pip install -r requirements.txt`. This installs both libraries for the same version of Python that the launcher will use.
2. Run the launcher for your system. From a Linux terminal, run `./Open\ on\ Linux.sh`. From a macOS terminal, run `./Open\ on\ macOS.command`. On Windows, open `Open on Windows.cmd`. You can also run the program directly with `python3.12 predict.py` on Linux or macOS or `py -3.12 predict.py` on Windows. The Linux launcher was checked in the evaluated setup. The other launchers are supplied for their respective systems.
3. The first run uses generated counts. The output gives `x_change_mm`, `y_change_mm` and `distance_estimate_mm`. The first two show the forecast movement in millimetres along each axis. The third gives the estimated travel distance. The example uses the first trained model. You can choose one of three trained models using `--seed`.
4. To use your own prepared archive counts, run `python3.12 predict.py --input window.json --seed 20261124` on Linux or macOS. On Windows, use `py -3.12` in place of `python3.12`. In `window.json`, the `electrode_ids` list must contain each number from 96 through 191 once. Each row of `counts` corresponds to the electrode at the same place in that list. Give ten whole numbers per row, all zero or greater, oldest bin first. Use a complete window from the matching setup and electrode map. The program puts the rows in the correct order using their IDs.

The download includes three ready-to-run ONNX graphs and the three sets of training weights stored in the SafeTensors format. The exported results matched the original forecasts to within 0.000031 mm on both evaluated sets. The comparison table gives the average across those models. This is a measured comparison on one calibrated animal. The study leaves new animals, new electrode positions and live use to separate tests. The project code and weights use [CC0](LICENSE). The original recordings and their attribution are provided by the [DANDI deposit](https://dandiarchive.org/dandiset/000070/0.261122.2046).
