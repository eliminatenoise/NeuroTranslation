# Score a Hyser session on your computer

The command compares the model’s forecast with the index sensor’s reading 120 ms later. Give it a second-day session to score the shared model. Add the same person’s first-day session to fit a personal correction and score both versions on the identical second-day readings. Five first-day trials fit an offset and a gain correction for each model. Those coefficients stay fixed throughout the second-day evaluation and are kept in memory for this run.

## Try it

Extract the Python scoring ZIP. In that directory, use a Python environment with NumPy and WFDB. The scorer was tested with WFDB 4.3.1.

```sh
python -m pip install -r requirements.txt
python score_session.py --example
```

The example generates two invented sessions. Its errors demonstrate the command and carry no information about the study’s accuracy.

## Score original recordings

Keep the original `random_dataset/subjectNN_session1` and `subjectNN_session2` directories from [Hyser 2.0.0](https://physionet.org/content/hd-semg/2.0.0/). Replace `NN` below with the same participant number in both paths.

```sh
python score_session.py random_dataset/subjectNN_session2
python score_session.py random_dataset/subjectNN_session2 --calibrate-from random_dataset/subjectNN_session1 --with-emg
```

The default uses the 100 Hz force-sensor records only. With `--with-emg`, include each corresponding 2,048 Hz raw EMG pair from the same original trial. Use `--trial 3`, for example, to score only trial 3 on the evaluation day. Calibration always uses all five first-day trials and all 2,250 prescribed cutoffs.

The scorer writes JSON to the terminal. MAE and RMSE are in sensor volts. `mae_gain_v` is the shared model’s MAE minus the calibrated model’s MAE. A positive number means the first-day correction lowered error on the supplied session. A command on one person cannot establish a population effect. The reference study also tests whether another person’s first day gives a similar change.

Folder names identify the participant and day. Use the names and grouping supplied with the original recordings. The program checks each record’s channel names, sample layout, declared units, lengths, initial values and WFDB checksums, then converts the ADC values to volts using its own channel gains and baselines. To check provenance, compare the original files with the checksum manifest from PhysioNet. The code operates locally and reads one trial at a time.

Contains information from Jiang, Dai, Liu and Fan’s Hyser 2.0.0 database, made available under the Open Data Commons Attribution License 1.0. [Dataset and citation](https://doi.org/10.13026/hxan-pe94) · [License](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [Acquisition study](https://doi.org/10.1109/TNSRE.2021.3082551)
