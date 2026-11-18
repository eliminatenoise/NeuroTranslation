# How much does scalp EEG add to a wrist forecast?

[Download the experimental preview ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/wrist-pointing-temporal/wrist-temporal-forecast-r1-preview.zip)

You see a target and turn your wrist towards it. The latest encoder reading gives your wrist angle, and the last half-second gives a model a path to follow. We asked whether eight channels of scalp electroencephalography (EEG) could improve that forecast once the model already had the path and the time since the cue.

We fit the models on six people and evaluated them on three different people. Across 960 development trials and 5,760 two-axis angle pairs, the temporal model's root mean square error (RMSE) was **4.053°** with wrist history and cue time, **4.523°** with scalp EEG added, and **4.880°** when that same EEG model received EEG from a different trial in the same recording block at the same cue offset. Adding EEG raised overall error by **0.469°** using the full-precision scores. Each person contributed equally to the reported error.

![At six target times between 750 and 2,000 milliseconds after the cue, holding the last angle has higher error than either model. Adding EEG raises flexion–extension error by 1.45 degrees at the first target time and lowers it slightly at the last two. Radial–ulnar deviation error rises at all six target times.](wrist-forecast-public.png)

Both fitted curves include elapsed cue time. Each forecast targets flexion–extension and radial–ulnar deviation, in degrees, as measured by the right-wrist exoskeleton encoders. Inputs end 128 rows before the target on the stored 512 Hz grid. The resulting **250 ms** is a nominal interval on that grid. The source reports an encoder update rate of 100 Hz, and the physical delays between instruments and movement remain unverified. The held-out test is still sealed. The development result describes offline forecasts for this task and these participants.

The simpler ridge regression went from 6.530° to 6.439° when EEG was added. The [companion muscle study](../wrist-pointing-muscle/) asks separately what surface EMG adds to that type of regression. It uses the same development participants, so the two studies give different comparisons on the same recordings.

## Open the preview

Extract the whole ZIP. Use Python 3.11 or newer and run the launcher for your operating system.

| System | Launcher |
| --- | --- |
| Linux | `sh launch-linux.sh` |
| macOS | `sh Launch-macOS.command` in Terminal |
| Windows | Open `Launch-Windows.cmd` |

The default view prints the measured development summary offline. Adding `--synthetic` runs the fitted checkpoint on invented input and requires NumPy and CPU PyTorch. The ZIP's README gives the separate steps for reproducing the study from the original deposit. The Linux launcher has been run from the archive. The macOS and Windows launchers are supplied for those systems and await native verification.

[Development aggregate](DEVELOPMENT-AGGREGATE.json) · [Figure script](plot_forecast.py) · [Sources and checksums](SOURCE.json)

## Data credit

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz deposited *EEG-EMG-WristMotion Dataset*, version 3, under CC BY 4.0. NeuroTranslation used selected pointing trials, decoded the encoder angles with extension and radial deviation positive, and binned the earlier recordings to fit the forecasts. The project authored the analysis code, experimental checkpoint and figure. [Version 3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Primary study](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Replay a recorded trial

[Open wrist replay](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) or [download the browser and its three desktop launchers](WristMotion-Recorded-Replay.zip) for offline use. The initial view shows the development errors at each of the six target times. Changing the model fit lets you compare each training seed with the mean of the three forecasts. The mean is taken before the error is calculated.

To see where the wrist went on one trial, [download the source converter](WristMotion-Recorded-Trial-Converter.zip), extract it and follow its README to prepare a JSON file from the original development recordings. The converter checks the source before it writes the six input windows and measured angles. On the replay page, select the file under **Open a recorded trial**. The browser checks the whole trial against the 960 fingerprints derived from the development source, then runs the six trained models on the earlier inputs. The measured target angles are held apart for comparison. Each point shows a sampled target on the stored clock. The data stay in the browser tab and **Clear recording** restores the study view.

For a first run, save [the example development archive from Figshare v3](https://ndownloader.figshare.com/files/62570998) as `recording.zip`. Keep it zipped. From the extracted converter directory, use Python 3.11 or newer with NumPy 2 installed:

```sh
python convert.py make-archive --archive "/path/to/recording.zip" --block 1 --trial 1 --output local-trial.json
```

Open `local-trial.json` in the browser. The original download belongs to the [EEG-EMG-WristMotion v3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3). The converter also runs offline after the download.

### Rebuild the browser model

The [browser source](browser-source/) converts the six released checkpoints and training normalization values into a script that runs without a server. Extract the converter ZIP beside the temporal study ZIP. With Python 3.11 or newer and NumPy 2, run this command from the study directory:

```sh
python browser-source/build_runtime.py --public-release wrist-temporal-forecast-r1-preview.zip --catalogue wrist-recorded-trial-converter-v1/wrist-recorded-development-sha256.txt --catalogue-sha256 2f6422705881398013b3245fb0d5fb4b0c5bb0528160c2325be8bdbc0286ff30
```

The script prints each output hash. The released `wrist-recorded.js` has SHA-256 `8d5d08586ee2979138c5b86ad504725bf73422baf3228fc26631958bb8c46aff`.
