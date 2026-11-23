# Stand and sit force forecast

[Technical edition](METHODS.md) · [Simple edition](SIMPLE.md) · [Data and licence credits](DATASET-CREDITS.md)

1. Extract the ZIP and keep its files together.
2. Open `Open on Linux.sh` on Linux, `Open on macOS.command` on macOS or `Open on Windows.cmd` on Windows. You can also open `index.html` directly in a desktop browser. The preview runs offline.
3. Choose an invented force history. Compare the forecasts for the two floor plates.

Each forecast uses ten 20-millisecond averages from each plate. That is 200 milliseconds of force history in newtons (N). The output is the **upward force impulse over the next 100 milliseconds**, in newton-seconds (N·s). Impulse adds up force over time. The preview shows a forecast for each plate and their sum.

The first method carries forward the force averaged over the last 20 milliseconds. The second extends the recent trend and lets it level off. The third starts with that trend and adds a correction when the total force is rising. It checks whether the average total force over the last 40 milliseconds is more than 50 N above the average over the first 40 milliseconds. The correction is the average from two fitted attention models.

## Results on recorded stand-and-sit trials

Four people supplied the Utah fitting data. Three other people were assigned to the Utah test. Two passed a fixed check on the first 30 seconds of their recordings. The third had too few loaded samples on one plate during that check.

The methods used the same 230 cases, each with its own input and outcome samples. The table gives mean absolute error for the **combined upward impulse on the two floor plates**. Errors were averaged within each person first, so the two people count equally. Lower error is better.

| Forecast | All 230 cases (N·s) | 24 rising-load cases (N·s) |
| --- | ---: | ---: |
| Recent force | 2.86 | 7.59 |
| Damped trend | 2.69 | 6.82 |
| Damped trend plus attention correction | 2.36 | 3.65 |

The correction lowered the overall error relative to the damped trend for both people who were scored. The two methods give identical outputs in the 206 cases outside the rising-load group. These results describe the two eligible people in this dataset. The target covers upward force measured at the floor plates. Loads on the chair or rails require their own measurements.

## Leeds replay on recorded chair trials

The same saved model was run on 402 Leeds chair trials from 134 people. The replay kept the model weights fixed and used 6,739 forecast windows, including 892 with rising force. The results cover combined upward impulse on the two floor plates. The calculation averages each person’s absolute errors first so each person counts equally.

Both plate orders were fixed before replay. The last two rows show the same correction with the two Leeds plates fed to the model in opposite orders.

| Forecast | All 6,739 windows (N·s) | 892 rising-load windows (N·s) |
| --- | ---: | ---: |
| Recent force | 2.837 | 6.835 |
| Damped trend | 2.099 | 4.567 |
| Damped trend plus correction, plate 1 then 2 | 2.105 | 4.749 |
| Damped trend plus correction, plate 2 then 1 | 2.117 | 4.853 |

The damped trend had lower mean error than the correction in both plate orders, across all windows and in the rising-load group. In each order, the correction gave lower overall error for 60 people and higher error for 74 compared with the trend.

The Leeds replay used exported force readings that had been low-pass filtered to reduce rapid changes. The filter’s time direction and the availability of the original readings on live hardware remain unverified. [Leeds study and methods](https://www.nature.com/articles/s41597-026-06925-w) · [University of Leeds dataset](https://doi.org/10.5518/1701)

## Notre Dame chair-rise and descent replay

Nine people each supplied three recordings of standing up from a chair and three of sitting down. A separate person supplied the engineering check. Each foot was on its own force plate, with 1,000 calibrated readings per second. The replay used the force exported before the study’s later software filter.

All methods forecast the next 100 milliseconds from the same 200 milliseconds of earlier force. The compact model in this download adds a learned correction when earlier load rises. The separate Research Edition test compared a correction that applies when earlier load rises or falls with one that applies every time. For both models, the averages below give equal weight to the forecasts from the two input orders, left foot first and right foot first.

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) |
| --- | ---: | ---: | ---: |
| Recent force | 2.130 | 1.521 | 2.770 |
| Damped trend | 1.731 | 1.282 | 2.260 |
| Compact correction, average of both orders | 1.805 | 1.610 | 2.260 |
| Research Edition, correction during changing loads | 1.679 | 1.501 | 1.938 |
| Research Edition, correction at every forecast | 1.709 | 1.262 | 2.193 |

The Research Edition correction during changing loads had the lowest overall mean error. Its advantage over the damped trend was 0.052 N·s across the nine people. Error fell for five people overall and eight during falling load. The same method had higher mean error during rising load. The compact correction also had higher overall mean error than the damped trend in either plate order.

These results describe 54 short recordings from one archive. Live sensor timing remains unverified. [Notre Dame dataset](https://doi.org/10.7274/28689221.v1) · [Recording methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12717423/)

## Run the predictor in Python

Use a Python environment with NumPy, PyTorch and safetensors. From the extracted folder, run the included example.

```sh
python model/predict.py example-rising.json
```

The input is a JSON array of ten `[plate 2, plate 3]` pairs in newtons, oldest first. The program loads the two saved 32-bit floating-point checkpoints. It returns a pair of impulse forecasts for each method, the rising-load flag, and the signed change in total load in newtons.
