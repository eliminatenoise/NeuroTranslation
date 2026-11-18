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
