# HYGRIP voltage forecast

Squeeze a grip transducer and its voltage changes. This preview asks what voltage it will read six ticks later. At 50 Hz, that's 120 ms. The browser runs three fixed models trained on seven eligible HYGRIP participants. One uses cue timing, one adds recent transducer readings, and one adds a window of scalp EEG. The default example is invented.

## Open it

- Windows — double-click **Open HYGRIP on Windows.cmd**.
- macOS — open **Open HYGRIP on macOS.command**.
- Linux — run **Open HYGRIP on Linux.sh** or open it with your file manager.
- You can also open **index.html** directly in a modern browser on any of the three systems.

Keep the files together. The example starts when the page opens. Use **Save example JSON** for a complete example and **Open a window JSON file** to select a prepared window from your computer. The page processes the window locally on the CPU. It uses no service, installer or network connection. Its citation links open external sites only when selected.

## Prepare a real window

Use the same right-hand, cued power-grip protocol and a compatible local sample grid. Go begins a scheduled 21 s trial of ten cycles, each with 1.55 s on and 0.55 s off. Every supplied sample must come from the lawful window of that same trial, including the verified rest period for pre-Go EEG samples. Keep data restricted to the intended people and use. The app can check units by contract, lengths, finite values, the scheduled issue index and the EEG endpoint. It cannot verify the sensor, permission, trial, montage or physical synchronization from numbers in a JSON file.

| JSON field | Expected value |
| --- | --- |
| version | 1 |
| forceGoSeconds | Local Go timestamp on the 50 Hz force device, in seconds |
| issueForceIndex | Zero-based force-grid issue index. Round Go × 50 to the nearest index with ties up. Add 20, 25, 30 and so on through 1040 to choose an issue. |
| forceV | Twenty contiguous signed voltage samples in the released V scale, oldest first, through the issue index |
| eeg | Optional. Omit the entire field to run the cue, force and analytic branches. |
| eeg.goSeconds | Local Go timestamp on the 1 kHz EEG device, in seconds |
| eeg.endIndex | Zero-based last EEG sample at or before EEG Go + (force issue index / 50 − force Go) − 0.020 s |
| eeg.channelNames | The exact 24 scalp channel names in the released order, as shown in the invented example |
| eeg.mV | 24 arrays of 400 contiguous finite released scalp readings in millivolts, oldest first, through the EEG end index |

Inputs use zero-origin device times. Supply no future readings or symmetric filters calculated from outside the approved input. In the benchmark, local Go markers place samples on matched release-relative timelines. A discrepancy greater than 40 ms between adjacent Go intervals holds the full run. This single-window app cannot repeat that metadata audit. Verify the clocks and source boundaries before preparing a window.

## Read the result

The number is a prediction of signed *voltage*. Calibration to newtons and true physical synchronization remain unverified. The 20 ms exclusion margin is a study-design choice and the 120 ms horizon does not measure live system latency.

| Forecast | TRAIN selection folds (V) | First DEV (V) |
| --- | ---: | ---: |
| Timing alone | 0.000854152 | 0.000889869 |
| Force history and timing | 0.000393763 | 0.000360083 |
| Force history, timing, and aligned EEG | 0.000417955 | 0.000461331 |
| Trial-rotated EEG control | 0.000402970 | 0.000422755 |
| Earlier EEG control | 0.000415367 | 0.000384986 |

The table reports mean participant RMSE. Each TRAIN fold scored one of seven source-eligible participants and fit the other six. These folds also selected penalties. All predictors used the same 16,195 rows from 79 right-hand trials. One of eight assigned TRAIN runs failed the clock gate.

On 19 November 2026, the frozen models were scored on 7,995 common rows from 39 right-hand trials in the three reserved DEV participants. Aligned EEG raised mean error against all three predeclared comparators in both phases. In DEV, adding aligned EEG raised RMSE against force history by 0.000101248 V on average, with an increase in all three participants. The two-sided exact sign-test p-value was 0.25. The descriptive 95% interval ran from −0.000276644 to +0.000479140 V. FINAL remains reserved.

The browser runs the versions fit on all seven eligible TRAIN runs. The earlier and rotated EEG controls appear as aggregate results, with no control weights in this package.

## Attribution and custody

Study by Pablo Ortega, Tong Zhao and A. Aldo Faisal. The preview contains fitted aggregate parameters, original inference code and an invented example. It contains no participant samples, identifiers, role arrays, archive bytes, author code or author illustrations. The article is CC BY and the original Figshare v1 dataset declares MIT. [Peer-reviewed article](https://doi.org/10.3389/fnins.2020.00919), [original data deposit](https://doi.org/10.6084/m9.figshare.12383639.v1).

## Replay one recorded grip

The plot draws the 20 input readings through cutoff. Choose a forecast to place its diamond six ticks ahead. In a trial, revealing the later reading adds an open circle at the same time. Open **Read the 20 sensor values** for exact time offsets and voltage readings.

The trial slider follows one cued right-hand grip at 100 ms steps. At each cutoff, the frozen model sees the last 20 force readings and, when supplied, 400 past samples from each of 24 scalp channels. **Reveal the later reading** shows the voltage six force ticks later and each fitted forecast's signed error in volts. The invented trial demonstrates the controls with force alone. Both the file and its predictions stay on your device.

To read a recording from [the HYGRIP release](https://doi.org/10.6084/m9.figshare.12383639.v1), download the original `hygrip.h5` and the converter beside this page. Install Python 3 with `h5py` and `numpy`. Substitute your archive's group letter and the right-hand trial number, counted from one.

```sh
python prepare_trial.py hygrip.h5 --participant GROUP_LETTER --right-trial 1 --output private-trial.json
```

Open the JSON in **Replay a grip trial**. The converter verifies the complete original file, checks both device clocks and reads a single trial. Keep its JSON private. The released voltage has no verified calibration in newtons. A recording can come from someone who contributed to the fit. Replaying it supplies no new estimate of performance on unseen people.
