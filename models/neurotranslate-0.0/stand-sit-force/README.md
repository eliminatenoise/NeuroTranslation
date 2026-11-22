# Stand and sit force forecast

1. Extract the ZIP and keep its files together.
2. Open `Open on Linux.sh` on Linux, `Open on macOS.command` on macOS or `Open on Windows.cmd` on Windows. You can also open `index.html` directly in a desktop browser. The preview runs offline.
3. Choose an invented force history. Compare the forecasts for the two floor plates.

Each forecast uses ten 20-millisecond averages from each plate. That is 200 milliseconds of force history in newtons (N). The output is the **upward force impulse over the next 100 milliseconds**, in newton-seconds (N·s). Impulse adds up force over time. The preview shows a forecast for each plate and their sum.

The first method carries forward the force averaged over the last 20 milliseconds. The second extends the recent trend and lets it level off. The third starts with that trend and adds a correction when the total force is rising. It checks whether the average total force over the last 40 milliseconds is more than 50 N above the average over the first 40 milliseconds. The correction is the average from two fitted attention models.

## Results on recorded stand-and-sit trials

Four people supplied the fitting data. Three other people were assigned to the test. Two passed a fixed check on the first 30 seconds of their recordings. The third had too few loaded samples on one plate during that check.

The methods used the same 230 cases, each with its own input and outcome samples. The table gives mean absolute error for the **combined upward impulse on the two floor plates**. Errors were averaged within each person first, so the two people count equally. Lower error is better.

| Forecast | All 230 cases (N·s) | 24 rising-load cases (N·s) |
| --- | ---: | ---: |
| Recent force | 2.86 | 7.59 |
| Damped trend | 2.69 | 6.82 |
| Damped trend plus attention correction | 2.36 | 3.65 |

The correction lowered the overall error relative to the damped trend for both people who were scored. The two methods give identical outputs in the 206 cases outside the rising-load group. These results describe the two eligible people in this dataset. The target covers upward force measured at the floor plates. Loads on the chair or rails require their own measurements.

## Run the predictor in Python

Use a Python environment with NumPy, PyTorch and safetensors. From the extracted folder, run the included example.

```sh
python model/predict.py example-rising.json
```

The input is a JSON array of ten `[plate 2, plate 3]` pairs in newtons, oldest first. The program loads the two saved 32-bit floating-point checkpoints. It returns a pair of impulse forecasts for each method, the rising-load flag, and the signed change in total load in newtons.

[Methods](METHODS.md) · [Data and licence credits](DATASET-CREDITS.md)
