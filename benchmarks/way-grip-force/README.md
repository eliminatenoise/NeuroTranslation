[The studies](../README.md) › Study 9 · Pinch and lift: grip force

# EEG from the wrong lift beat EEG from the right one

A thumb and forefinger squeeze a small object before lifting it, and plates under the fingertips measure the squeeze. A straight-line fit, made on six people from the cue, the recent force and the movement of hand and object, forecast the grip force 120 ms ahead for three other people with an error of **0.4442 N**. Given scalp EEG as well, it missed by **0.4402 N**: 0.0040 N better, for two of the three. But the same fit given EEG from a different lift did better still, **0.4388 N**. The pass rule set before scoring required the right EEG to beat that control, so EEG failed it.

Every score here is the measure that punishes large misses (root mean squared error), worked out for each person and averaged over the three. EEG is electrical activity of the brain, picked up on the scalp; EMG is electrical activity of muscle, picked up on the skin. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small. The recordings are stored voluntary pinch-lifts by healthy adults in the WAY-EEG-GAL study. [Original experiment and measurements](https://doi.org/10.1038/sdata.2014.47)

| Forecast | Error, averaged over the three people |
| --- | ---: |
| Repeat the last measured grip force | 0.7878 N |
| Carry the recent change in grip force forward | 0.6730 N |
| Cue and trial context only | 1.4258 N |
| Context, force history and motion history | 0.4442 N |
| The same, with scalp EEG | 0.4402 N |
| The same, with surface EMG | 0.4571 N |
| The same, with scalp EEG and surface EMG | 0.4546 N |
| The EEG fit, given EEG from another lift at the same stage | 0.4388 N |

The models were fixed before the three test people were scored. The main comparison used 25,578 matched forecasts from 882 lifts. The wrong-lift control swaps whole EEG trials within the same person, series, object weight and surface, at the same time after the cue, and all three models in that comparison were fitted and scored on the same matched forecasts.

The small gain also vanished whenever there was real force to forecast. In the 5,140 forecasts where the measured force was above 0.5 N, the fit without EEG scored 0.7750 N and the fit with EEG 0.7758 N. In the 20,438 where it was 0.5 N or less, repeating the last force beat every fitted model: 0.0606 N, against 0.2049 N for the EEG fit. EMG raised the error, from 0.4442 to 0.4571 N, though on the plain average miss (mean absolute error) it lowered it, from 0.2719 to 0.2646 N. [Results file](DEVELOPMENT-AGGREGATE.json)

## What it does not show

The forecasts overlap, so for all their number the study rests on three people. Three more were set aside when the people were split, and their recordings have not been opened. The 120 ms is a distance on the stored sample clock: the timing of the filters and the delay of a live system were never measured. A link between EEG and force would also leave muscle and movement artefacts as explanations.

## The plan

Three conditions for EEG were set before scoring: below the force-and-motion fit, below the best other fit, and below EEG taken from another lift. The first two held and the third did not. `METHOD.md` in the [desktop ZIP](WAY-EEG-GAL-grip-force-experimental-preview.zip) gives the fitting and comparison rules, and the results file records that no weights changed after the test people were scored.

## Try four forecasts

Move the cutoff on the invented pinch-lift to see what the models forecast 120 ms later, and look at the past force, motion, scalp EEG and surface EMG that move those forecasts. Open a compatible JSON window of your own to run the same calculation in your browser. [Open the forecast](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) · [Download the offline page](WAY-EEG-GAL-grip-force-browser.zip)

### Replay one recorded lift

Open a lift from your own computer and move the slider through 29 cutoffs. At each one you can reveal the plate reading recorded 120 ms later. The signed error is positive when the forecast overshoots. **Replay an invented lift** shows the same controls with invented signals.

To use an original recording, save the [lift converter](../../docs/grip-force/convert_lift.py) and take a windowed-series MATLAB file from the data deposit. With Python, NumPy and SciPy installed, run `python convert_lift.py WS_file.mat --trial 1 --out lift.json`, with your file name and trial number, and open that JSON in the page. The file holds the sensor samples of the lift you chose; the errors above come from the full comparison over all three people.

## Run the desktop forecast

[Download the desktop ZIP](WAY-EEG-GAL-grip-force-experimental-preview.zip) and extract the whole folder. Open `Run-Windows.cmd`, `Run-macOS.command` or `Run-Linux.sh` for your system. You need Python 3.10 or later and NumPy. The Linux demo ran in an extracted copy; the Windows and macOS launchers have not been run on those systems.

The example runs five fitted models and two formula forecasts on an invented window. To forecast a compatible recording of your own, use the input format and command in the ZIP's `INFERENCE.md`. The runner needs 400 ms of aligned history, the measured force and motion, the LED cue, the series type and the trial number. The wrong-lift control needs other trials, so it is not in the runner; object weight and surface are used only to pair that control and in side comparisons.

## Check the files

From this folder, run `python verify.py` to check the Python runner and every member of its ZIP against the source manifest. Run `python browser-release/build.py` to rebuild the browser page's study data and offline ZIP in memory and compare both with the files here; add `--write` to write the rebuilt copies. [Source and package manifest](SOURCE.json)

The archives carry the fixed model weights, summary results and the project's forecasting code. Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin recorded and shared WAY-EEG-GAL; the WAY project (FP7-ICT-288551) supported the original recordings. The recordings and their licence notices are available from the data authors; full credit is in [docs/RIGHTS.md](../../docs/RIGHTS.md). [WAY-EEG-GAL collection version 2](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The same question, timed from the moment the plates register the squeeze: [Study 10 · Pinch and lift: grip force, timed from the squeeze](../way-contact-force/).
