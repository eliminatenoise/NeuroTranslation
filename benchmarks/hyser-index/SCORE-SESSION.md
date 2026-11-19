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

## Compare all five finger sensors

How much does the index finger tell us on its own? Add `--whole-hand` to compare three fixed models on exactly the same index readings. One sees 41 index readings, spanning 400 ms. A second sees the same history from each of the five fingers. A third keeps the full index history and uses just the latest reading and the slope for each of the other four fingers. All three predict the index sensor voltage 120 ms later.

```sh
python score_session.py --example --whole-hand --trial 1
python score_session.py random_dataset/subjectNN_session2 --whole-hand
```

The five channels share one force record per trial. This comparison uses that record alone, with each channel converted to volts using its own header calibration. The JSON reports MAE and RMSE for each model and the change in MAE when all five histories are available. A positive change means that adding the other fingers lowered the error on the supplied recording. Run the EMG and personal-calibration comparisons separately.

## Score a prescribed finger combination

During the N-DoF task the participant follows a prescribed combination. In the Random task the participant chooses the fingers. The same three frozen models accept either task's five force-sensor voltages. The inferred quantity is still the later reading of the index transducer.

Open the extracted Python scorer directory. Give this command one original `ndof_dataset/subjectNN_sessionD` folder. With no further options it reads the first repetition of all 15 combinations. The result includes separate errors for the eight combinations that cue the index finger and the seven that leave it uncued. Both groups contain measured index-sensor voltage.

```sh
python score_prescribed.py ndof_dataset/subjectNN_session1
python score_prescribed.py ndof_dataset/subjectNN_session1 --combination 3 --repetition 1
```

For the second command, the two required files are `ndof_force_combination3_sample1.hea` and `ndof_force_combination3_sample1.dat`. The reader checks their recorded layout, calibration and WFDB checksums. For provenance, compare the original files with the SHA-256 index supplied by PhysioNet. The command prints MAE and RMSE in volts for the last reading, index history, five histories, and the compact five-sensor forecast. Errors from one session cannot establish a population effect. [Dataset and terms](https://physionet.org/content/hd-semg/2.0.0/)

Contains information from Jiang, Dai, Liu and Fan’s Hyser 2.0.0 database, made available under the Open Data Commons Attribution License 1.0. [Dataset and citation](https://doi.org/10.13026/hxan-pe94) · [License](https://physionet.org/content/hd-semg/view-license/2.0.0/) · [Acquisition study](https://doi.org/10.1109/TNSRE.2021.3082551)
