# Open a CEMHSEY trial locally

The companion uses one compact trial packet at a time. It can show the measured result once you choose to score the forecast. The packet retains force readings and four summary features per issue, so keep it in your own private folder. It contains no raw EMG waveform or participant identifier. The public example uses invented data.

Use one original GRASP MATLAB trial for the two-finger pad-to-pad pinch at 30% MVC. The converter expects the published `data_force` row and, when selected, the `data_sEMG` matrix with 320 channels as rows. The MATLAB fields do not identify the condition. Recover it from the source member identity before choosing the file. [CEMHSEY GRASP](https://doi.org/10.1038/s41597-025-05733-y) · [Part I v2](https://doi.org/10.5281/zenodo.15077957) · [Part II v2](https://doi.org/10.5281/zenodo.15070187)

From the folder containing `trial_io.py`, `pinch.py`, `PROTOCOL.md` and `requirements.txt`, use Python 3.14 with the pinned dependencies. Create a private destination directory and give the output a new filename. The converter opens the original in read-only mode and creates the packet on the local filesystem.

    python -m pip install -r requirements.txt
    python trial_io.py --input ORIGINAL.mat --output PRIVATE/trial.json

Use the Python command for your operating system. On Windows with the Python launcher, use `py -3.14` in place of `python`. On macOS and Linux, use the installed Python 3.14 executable or activate its environment first. Choose an owner-private folder, using your operating system's account access settings. The converter creates owner-only file permissions on POSIX.

The default conversion uses measured force only. Add `--timing-mode nominal_release_index` for the paired EMG comparison. This assumes both release indices start at the same nominal trial coordinate. The datasets' physical offset and drift are unbounded by the public record. The +24 prediction is 24 intervals on the nominal 200 Hz force trace, and the EMG cutoff is a separate convention defined in the protocol. [Forecast protocol](PROTOCOL.md)

## Fit a predictor from your own files

Keep the original names so the trainer can group the two repeats by person and recording day. Select both repeats for each person on the same selected days. Write one original MATLAB file path per line in a UTF-8 text file. Relative paths are resolved from that list's folder. You can also repeat the `--trial` option once for each file.

    python fit_local.py --trial-list PRIVATE/trials.txt --output PRIVATE/my-fit.json

By default, this trains the force and task-phase models. For the nominal release-index EMG arm, choose `--timing-mode nominal_release_index` for both training and conversion. Open the reader and select your fit file. Then open a converted trial packet. The fit contains pooled coefficients and feature scaling for the local reader. Your training list, person codes, raw files and per-person predictions stay outside it. This command fits on the selected files and leaves evaluation to separate recordings.

## Forecast and score from the command line

Pass one converted trial packet and a fitted JSON file to the local scorer.

    python score_packet.py PRIVATE/trial.json --fit PRIVATE/my-fit.json --issue 1660

The command prints each prediction and its target index. Use `--score` instead of `--issue` to compare all 592 predictions with the measured targets and print MAE and RMSE for that one trial. A force-only packet can use the fitted force and phase comparisons. The paired EMG arm appears when both the fit and packet supply compatible nominal-index EMG features. To exercise the reader without recordings, use the example packet and weights labeled invented.
