# Forecast a pinch

Open the [browser reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) or extract the [offline ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/cemhsey-pinch/downloads/CEMHSEY-Pinch-Reader.zip). The ZIP contains a Windows, macOS and Linux launcher, the same browser reader, and a Python converter. Opening `index.html` directly also works.

Choose **Try an invented pinch** to explore the controls without a recording. Move the cutoff with the arrow keys. The green line shows earlier force readings and the orange dot shows the forecast 24 force ticks later. Reveal the later reading to compare them. **Score this trial** separately reveals MAE and RMSE for the 592 scheduled cutoffs. Those scores concern the selected trial alone.

## Choose the weights

The model label identifies the active weights. The public download starts with fits trained entirely on invented signals. The study results describe separately fitted models evaluated on original recordings. A private study bundle, where provided, identifies its bundled weights as the study model. To evaluate your own fitted weights in either reader, choose **Load a fitted model from this computer**. Switching models clears the previous reveal and error table.

The Python folder includes the same fitting method. For your own data, put one original two-finger, 30% target MAT file path per line in a text file. Supply both repetitions for each person on the same selected days. Run this command from the Python folder and load the resulting local JSON into the reader:

```sh
python fit_local.py --trial-list trials.txt --timing-mode nominal_release_index --output "my-fit.json"
```

Use `--fit "my-fit.json"` with either scoring command below to use the same local model. Keep the model and its training files in your private folder.

## One original recording

The model was prepared for the two-finger pad-to-pad pinch on the P200 dynamometer, under the 30% target condition. Use an original CEMHSEY GRASP Level-5 MATLAB trial with `data_force` and, for the paired forecast, `data_sEMG`. Force is on the release’s normalized scale for that participant, day and grasp. The dynamometer measures one combined force between the two digits.

In the extracted ZIP, use the `python` folder with a compatible local Python environment. Install its listed dependencies if necessary.

```sh
python -m pip install -r requirements.txt
python trial_io.py --input "trial.mat" --output "private-trial.json" --timing-mode nominal_release_index
```

Choose the resulting JSON packet in the browser. If you omit the timing flag the converter uses the force record alone. Use a private local folder and a new file name for each output. A packet contains sampled force readings and, in paired mode, compact summaries of forearm activity. It is intended for local use. The browser reads the file on the device.

To use the same pooled forecasts in a terminal, run either command from the same Python directory.

```sh
python score_packet.py "private-trial.json" --issue 1660
python score_packet.py "private-trial.json" --score
```

An issue tick is a force-sensor index from 60 to 5,970 in steps of ten. The first command gives the model estimates for one index. The second returns the errors for all 592 matched cutoffs.

## Measurement and attribution

A force tick is 5 ms on the 200 Hz record. The EMG grid is 2,048 Hz. Each pair of streams belongs to the same stored trial. The analysis takes a common nominal starting index and uses EMG windows ending 100 ms before the issue index on that nominal schedule. Cross-device offset, drift and physical availability remain unmeasured. The dynamometer target does not identify one finger’s contribution.

The reported experimental predictors and aggregate scores use GRASP data from Yang and colleagues’ CEMHSEY release. The public demonstration coefficients and example trace use invented data. The user-selected trial stays separate from the freely distributed model and invented demonstration. [Study, prespecified comparison and results](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/cemhsey-pinch) · [Acquisition paper](https://doi.org/10.1038/s41597-025-05733-y) · [Part I](https://doi.org/10.5281/zenodo.15077957) · [Part II](https://doi.org/10.5281/zenodo.15070187) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
