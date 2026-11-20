[The studies](../README.md) › Study 1 · Wrist pointing: brain signal on a learned forecast

# Scalp EEG made the wrist forecast worse

Three people turned a wrist towards a target. A learned forecast, fitted on six other people, read the wrist's recent path and the time since the cue and forecast both wrist angles a quarter of a second (250 ms) ahead. It missed by **4.053°**. Given eight channels of scalp EEG as well, it missed by **4.523°**, 0.469° worse. Given EEG from a different trial instead, it missed by **4.880°**. Simply repeating the last angle missed by 7.925°.

Every score here is the measure that punishes large misses (root mean squared error), over both wrist axes, with each of the three people counting equally. EEG is electrical activity of the brain picked up on the scalp. A *learned forecast* is a small network that reads a stretch of recent history. This one was trained three times, and the three forecasts were averaged before the error was worked out.

![At six target times between 750 and 2,000 milliseconds after the cue, holding the last angle has higher error than either model. Adding EEG raises flexion–extension error by 1.45 degrees at the first target time and lowers it slightly at the last two. Radial–ulnar deviation error rises at all six target times.](wrist-forecast-public.png)

## What was forecast

The person sees a target and turns the right wrist towards it, inside an exoskeleton whose encoders measure two angles in degrees: bending up and down (flexion–extension) and tilting side to side (radial–ulnar deviation). The forecasts were scored at six moments after the cue, on 960 trials and 5,760 pairs of angles from the three test people. The models never saw those three while they were being fitted. Six more people were set aside when the dataset was split, and their recordings have never been opened.

The last input ends 128 samples before the target on the recording's 512 Hz clock: that is the 250 ms. The source reports that the encoders update at 100 Hz, and the delays between the instruments and the movement were never measured, so the 250 ms is a distance along a stored recording, not a live forecast.

A plain straight-line fit (a weighted sum of its inputs, here ridge regression) on the same wrist history went from 6.530° to 6.439° when EEG was added: slightly better, and EEG from another trial took it to 6.782°. [Study 2](../wrist-pointing-muscle/) asks what forearm EMG adds to that straight-line fit, on the same three people and the same trials.

## What it does not show

Three people, one pointing task, stored recordings scored after the fact. The three test people were never used to fit a model, but they are not the final test: the six people set aside are, and nobody has scored them yet.

## The plan

The plan, `DESIGN-public.json` inside the [study ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/wrist-pointing-temporal/wrist-temporal-forecast-r1-preview.zip), fixed one comparison before scoring: the network with EEG against the same network without it. It set no pass threshold. The models were scored with no refitting and no choice made after seeing the scores.

## Run it yourself

[Download the study ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/wrist-pointing-temporal/wrist-temporal-forecast-r1-preview.zip) and extract all of it. Use Python 3.11 or newer and run the launcher for your system.

| System | Launcher |
| --- | --- |
| Linux | `sh launch-linux.sh` |
| macOS | `sh Launch-macOS.command` in Terminal |
| Windows | Open `Launch-Windows.cmd` |

It prints the measured results offline. Add `--synthetic` to run the fitted model on invented input, which needs NumPy and CPU PyTorch. The ZIP's README gives the separate steps for scoring the study again from the original recordings. The Linux launcher has been run from the archive; the macOS and Windows launchers have not yet been run on those systems.

[Results file](DEVELOPMENT-AGGREGATE.json) · [Figure script](plot_forecast.py) · [Sources and checksums](SOURCE.json)

## Replay a recorded trial

[Open the wrist replay](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) or [download the browser page and its three desktop launchers](WristMotion-Recorded-Replay.zip) for offline use. It opens on the errors at each of the six target times. Switch between the three trained copies of the model and their averaged forecast.

To see where the wrist went on one trial, [download the converter](WristMotion-Recorded-Trial-Converter.zip), extract it and follow its README to turn one trial of the original recordings into a JSON file. The converter checks the source before it writes the six input windows and the measured angles. On the replay page, choose the file under **Open a recorded trial**. The page checks the trial against the 960 fingerprints of the test trials, then runs the six trained models on the earlier inputs and sets their forecasts beside the measured angles. Each point is one target on the stored clock. The data stay in the browser tab, and **Clear recording** returns to the study view.

For a first run, save [the example archive from Figshare version 3](https://ndownloader.figshare.com/files/62570998) as `recording.zip` and keep it zipped. From the extracted converter folder, with Python 3.11 or newer and NumPy 2:

```sh
python convert.py make-archive --archive "/path/to/recording.zip" --block 1 --trial 1 --output local-trial.json
```

Open `local-trial.json` in the page. The download belongs to the [EEG-EMG-WristMotion version 3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3). Once it is downloaded, the converter runs offline.

### Rebuild the browser model

The [browser source](browser-source/) turns the six released models and the scaling values from fitting into a script that runs without a server. Extract the converter ZIP beside the study ZIP. With Python 3.11 or newer and NumPy 2, run this from the study folder:

```sh
python browser-source/build_runtime.py --public-release wrist-temporal-forecast-r1-preview.zip --catalogue wrist-recorded-trial-converter-v1/wrist-recorded-development-sha256.txt --catalogue-sha256 2f6422705881398013b3245fb0d5fb4b0c5bb0528160c2325be8bdbc0286ff30
```

The script prints the hash of each output. The released `wrist-recorded.js` has SHA-256 `8d5d08586ee2979138c5b86ad504725bf73422baf3228fc26631958bb8c46aff`.

## Whose recordings

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz deposited the *EEG-EMG-WristMotion Dataset*, version 3, under CC BY 4.0. NeuroTranslation used selected pointing trials, decoded the encoder angles with extension and radial deviation positive, and binned the earlier recordings to fit the forecasts. The project wrote the analysis code, the fitted model and the figure. [Version 3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Primary study](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

A later study kept the three wrist models fixed and fitted a correction on top. Adding forearm EMG to that correction lowered the error from 3.957° to 3.853°: [Study 3 · Wrist pointing: muscle signal on the learned forecast](../wrist-forearm-transfer/).
