# Read a pinch on your computer

The browser example uses invented data and weights. It lets you see what changes when the reader keeps the electrode-grid layout. To examine recordings you’re authorized to use, convert one compatible original CEMHSEY MATLAB trial and open the resulting file in the offline reader. A local reader fit can be made from recordings you select. The archived demonstration is not a live experiment or a source of measured scores. [Study design](./PROTOCOL.md) · [CEMHSEY GRASP data and license](https://doi.org/10.1038/s41597-025-05733-y)

## Convert one trial

Use Python with NumPy and SciPy. The tested versions are Python 3.14.8, NumPy 2.4.5 and SciPy 1.17.1. From the reader package’s Python source directory, run the following in a terminal. On systems where Python is launched as `python3` or `py -3`, use that command.

```console
python trial_packet.py --input "/path/to/original.mat" --output "/path/to/private/trial.json"
```

Choose a new path in an existing private directory. The converter accepts a compatible adult CEMHSEY Session 5, Task 2 recording with a double `data_force` row and a 320 × 61,500 double `data_sEMG` matrix. It keeps the first 6,000 normalized force samples and the 594 × 320 guarded 100 ms channel RMS values. The JSON encodes both as little-endian float64 data in base64. Force uses the released fraction of MVC and channel RMS uses mV. The converter writes no raw waveform or subject field to the packet. The packet still contains measurements and belongs with your private files.

## Fit the reader with your selected trials

Create a UTF-8 text file with one original `.mat` path per line, relative to that text file or absolute. Use the original Session5_Task2 names for exactly three people on days 1 and 2, with both repeats for each person and day. The local fit uses the same issue support, comparisons and fixed ridge penalty as the study design. Keep the chosen training recordings separate from any recordings you use to assess performance.

```console
python fit_local.py --trial-list "/path/to/private/trials.txt" --output "/path/to/private/reader-fit.json"
```

In the browser reader, choose the converted trial and the resulting local fit. The named predictions use force history and cue phase, then add the overall EMG summaries, the five native-grid profiles, or the grid profiles plus channel rank persistence. Persistence returns the current measured value. The reader keeps the example and user-fit origins explicit. A fit from a user-selected set has not passed the separate study’s source and evaluation checks.

The tools create new JSON files and refuse to overwrite them. Output files are mode 0600 on POSIX. On Windows, keep the output directory under your private account permissions. The converter and own-fit CLI were exercised on Linux with invented MATs. macOS and Windows native Python execution still need verification.

## Set the width on separate trials

Load the exact reader fit you want to calibrate. Under **Choose or make calibration bands**, open **Calibrate on your own converted packets**. Select up to 32 complete packets, confirm that the trials are separate from training and assessment, and choose **Calculate local bands**. The reader takes the absolute force forecast errors 24 ticks after each cutoff. In ascending order, it takes the error at one-based rank min(n, ceil(0.90 × (n + 1))) as the half-width for a group of n errors. It does this for each of three forecasts, once pooled across phases and once within each issue phase.

A local profile stores six widths per model, counts, the phase and timing protocol identifier and a SHA-256 fingerprint of the exact fit bytes. **Save local profile** downloads it as JSON. Keep both files if you want to reopen the calibration. Even a different serialization of the same coefficients has a different byte fingerprint. Old fit and trial files still give point forecasts while bands require a matching profile.

Keep calibration separate from whatever trial you score. Your saved local profile stores one SHA-256 fingerprint for each calibration packet, computed from the decoded force and EMG arrays. The reader uses these fingerprints to block use of that same packet for interval assessment, even if its file was renamed or reformatted. It can flag exact reuse and repeated inputs. It cannot tell whether different packets came from the same person or recording. The fingerprints contain no readings or subject IDs, but someone who already has a packet could check for a match. Keep the profile private. If you have an older local profile without a packet list, calculate and save new bands from the original calibration inputs. Point forecasts are still available while the band is withheld.

Imported profiles describe their stated origin. The reader checks the exact fit fingerprint and timing and phase protocol, and checks the local packet fingerprint where it has the local calibration list. These checks do not verify the accuracy or provenance of the calibration widths.

The shaded range describes a single target reading at the nominal +120 ms horizon. The curve links successive forecasts and the bands have no joint coverage guarantee. The comparison uses nominal release indices, with unverified physical synchronization between force and EMG. Scores from one trial or calibration on your own selection give no performance result for the published evaluation panel. [Band method and study results](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/)
