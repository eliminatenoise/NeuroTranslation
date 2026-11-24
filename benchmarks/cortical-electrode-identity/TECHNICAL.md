# Hand displacement from fixed electrode identities

[Package overview](README.md) · [Simple edition](SIMPLE.md) · [Aggregate measurements](results.json)

## Recorded input and output

Predict the two-dimensional change in measured hand position from the issue time to 100 ms later. The input is a 200 ms history with ten 20 ms event-count bins for each of 96 primary motor cortex electrodes. The lower boundary uses the native timestamp 200 samples before issue. Half-open histories within each trial share no events. The archive links each channel to an electrode ID from 96 through 191. Values are unsorted voltage threshold crossings. Input excludes positions and task cues. A separate head predicts straight-line displacement distance. All outputs use millimetres. [Data and conversion](https://dandiarchive.org/dandiset/000070/0.261122.2046) · [Original electrode mapping](https://github.com/catalystneuro/shenoy-lab-to-nwb/blob/debff6465a6ca3bd3db7843578d88bff3fac5bf8/maze_task_unsorted/shenoymatdatainterface.py#L99-L118)

| Recording | Role | Trials | Forecast windows |
|---|---|---:|---:|
| 23 September 2010 | Fitting | 3,694 | 55,878 |
| 22 September 2010 | Development, final quarter | 586 | 7,767 |
| 20 September 2010 | Held evaluation | 3,404 | 44,701 |

Archived discard flags excluded 640 of 4,044 trials on the held day. The timing and coverage checks required 200 ms of history with complete channel observation and a measured target 100 ms later. All three recordings are from the same macaque. The held recording was acquired before the fitting recording. Forecasts were fixed before the held hand coordinates were read.

## Comparison

The ordered model adds eight learned electrode-weighted sums per time bin to the pooled activity features. Both feed a width-24 convolution and gated recurrent network with three shared refinement passes. The matched shuffled model has the same 10,251 parameters and randomizes complete electrode histories per example. The pooled control has 8,907 parameters. Another test gives the fitted ordered model three fixed wrong channel mappings at inference. The no-movement rule outputs zero.

Each arm used three matched seeds, FP32 arithmetic, 2,400 AdamW updates at 0.002, weight decay 0.001, batches of 128 and smooth L1 loss with beta 0.2 on outputs scaled by 100 mm. Each trial had equal sampling mass. Evaluation averages errors within trial and then weights the trials equally. The means also average over the fitted seeds and any specified replay seeds. The paired 95% intervals resample the same whole trials 4,000 times and describe variation within the recorded day.

| Method | Held vector | Held distance | Development vector | Development distance |
|---|---:|---:|---:|---:|
| Ordered electrodes | 4.65 | 3.11 | 8.59 | 7.31 |
| Pooled electrodes | 9.06 | 5.51 | 9.84 | 7.96 |
| Shuffled training and replay | 9.45 | 5.58 | 10.06 | 7.84 |
| Wrong mapping at inference | 17.13 | 11.84 | 25.67 | 19.61 |
| No movement | 9.23 | 9.23 | 8.33 | 8.33 |

Values are mean errors in millimetres. Vector error is the Euclidean difference of measured and predicted displacement. Distance error is the absolute error of the separate distance estimate. The held reduction against matched shuffling was 4.80 mm for vector error, with a paired 95% interval of 4.74 to 4.86 mm. The corresponding distance reduction was 2.48 mm, with an interval of 2.42 to 2.54 mm.

On the held recording the ordered model averaged 18.63 mm of vector error when measured movement was at least 20 mm. No movement averaged 49.47 mm there. Below 2 mm of measured movement, no movement averaged 0.34 mm and the ordered model averaged 1.06 mm. These secondary bands were specified after inspecting development and before opening held outcomes. The bins use the measured outcome and describe performance after the fact.

## Run the model

1. Extract the download and open its folder. Install the two pinned dependencies with `python3.12 -m pip install -r requirements.txt` on Linux or macOS, or `py -3.12 -m pip install -r requirements.txt` on Windows. The launchers use the same interpreter as these commands.
2. Run `./Open\ on\ Linux.sh`, `./Open\ on\ macOS.command`, or `Open on Windows.cmd` for your system. Running `python3.12 predict.py` on Linux or macOS or `py -3.12 predict.py` on Windows also runs the generated input. The Linux launcher was tested. The Windows and macOS scripts are included for their respective systems.
3. For recorded input, add `--input window.json --seed 20261124` to your direct Python command. Give the JSON file `electrode_ids` and `counts` arrays. Each ID from 96 through 191 appears once. Each corresponding row has ten nonnegative integer counts, oldest bin first. Use a complete observation window from the matching archive and electrode map. The script sorts the rows by ID.

The three included ONNX graphs give `x_change_mm`, `y_change_mm` and `distance_estimate_mm`. The generated example defaults to the first seed. The table averages the three separate fitted models. All exported forecasts matched their original values to within 0.000031 mm on both evaluated sets. The SafeTensors files hold the training weights. This experiment addresses a calibrated recording setup on one animal. The stable archive IDs do not identify individual neurons or establish shared electrode positions across subjects. Live operation and transfer to new animals were outside the evaluation. The package redistributes project code and weights under [CC0](LICENSE). The recordings are attributed to their [DANDI deposit](https://dandiarchive.org/dandiset/000070/0.261122.2046).
