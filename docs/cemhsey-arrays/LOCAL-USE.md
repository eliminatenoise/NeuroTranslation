# Read a pinch on your computer

Open an original recording and you can follow one pinch from the electrode grids to the forecast for the gauge. The bundled example and weights use invented signals. Use recordings you’re authorized to examine, and keep the files on your own device. [Study design](./PROTOCOL.md) · [CEMHSEY GRASP data and license](https://doi.org/10.1038/s41597-025-05733-y)

## Open an original trial

Choose the adult CEMHSEY GRASP two-finger pinch at a 30% target, Session 5, Task 2, repeat 1 or 2. Check the source before you confirm the task and choose the original `.mat`. The archive uses participant numbers 1 to 13 and days 1 to 11. If you use an archive-style filename with a higher positive participant number, the reader marks it as a local label outside the archive roster and uses your task confirmation. A renamed file still needs its task checked against the source.

The browser reads the file on your device. To reuse its force and electrode summaries for calibration, choose **Save a local array packet**. Keep that JSON private. It contains derived readings and normalized force. To reopen any compatible array packet, choose **Open an array packet (.json)**.

The import accepts a MATLAB Level 5 file with a `data_force` double row, a 320 × 61,500 `data_sEMG` double matrix and a positive `MVC` scalar. It keeps the first 6,000 normalized force samples and 594 × 320 guarded 100 ms channel RMS values in mV. The force is already expressed as a fraction of MVC. The saved JSON encodes both arrays as little-endian float64 data in base64. Try the Python converter if your browser cannot open the original.

## Convert a trial in Python

Use Python with NumPy and SciPy. The tested versions are Python 3.14.8, NumPy 2.4.5 and SciPy 1.17.1. From the reader package’s Python source directory, run the following in a terminal. On systems where Python is launched as `python3` or `py -3`, use that command.

```console
python trial_packet.py --input "/path/to/original.mat" --output "/path/to/private/trial.json"
```

Choose a new path in an existing private directory. Open the saved JSON using the array packet picker. The packet still contains measurements and belongs with your private files.

## Fit the reader with your selected trials

Open **Fit your own model** and choose the original trials it asks for. When the fit is ready, choose **Use this fit in the reader**. You can also download the weights or use the separate fit page, then open the saved weights under **Choose forecast weights**. To use the command-line fit, create a UTF-8 text file with one original `.mat` path per line, relative to that text file or absolute. Use the original Session5_Task2 names for exactly three people on days 1 and 2, with both repeats for each person and day. The local fit uses the same issue support, comparisons and fixed ridge penalty as the study design. Keep the chosen training recordings separate from any recordings you use to assess performance.

```console
python fit_local.py --trial-list "/path/to/private/trials.txt" --output "/path/to/private/reader-fit.json"
```

In the browser reader, open a trial and load the resulting local fit. The named predictions use force history and cue phase, then add the overall EMG summaries, the five native-grid profiles, or the grid profiles plus channel rank persistence. Persistence returns the current reading. A user-selected fit needs its own independent assessment.

The browser fit stores a fingerprint of the decoded arrays for each fitting trial. The reader marks an exact match as in-sample whether you open the original MATLAB file or its array packet. Point errors on those recordings describe the fit, and the reader excludes those packets from calibration. A different fingerprint leaves open whether two trials came from the same person or source recording. With older weights that have no fingerprints, overlap is unknown. Keep the weights private. Someone who already has a matching packet can confirm its fingerprint.

The tools create new JSON files and refuse to overwrite them. Output files are mode 0600 on POSIX. On Windows, keep the output directory under your private account permissions. The converter and own-fit CLI were exercised on Linux with invented MATs. macOS and Windows native Python execution still need verification.

## Set the width on separate trials

Load the exact reader fit you want to calibrate. Under **Choose or make calibration bands**, open **Calibrate on your own converted packets**. Select up to 32 complete packets, confirm that the trials are separate from training and assessment, and choose **Calculate local bands**. The reader takes the absolute force forecast errors 24 ticks after each cutoff. In ascending order, it takes the error at one-based rank min(n, ceil(0.90 × (n + 1))) as the half-width for a group of n errors. It does this for each of three forecasts, once pooled across phases and once within each issue phase.

A local profile stores six widths per model, counts, the phase and timing protocol identifier and a SHA-256 fingerprint of the exact fit bytes. **Save local profile** downloads it as JSON. Keep both files if you want to reopen the calibration. Even a different serialization of the same coefficients has a different byte fingerprint. Old fit and trial files still give point forecasts while bands require a matching profile.

Keep calibration separate from whatever trial you score. Your saved local profile stores one SHA-256 fingerprint for each calibration packet, computed from the decoded force and EMG arrays. The reader uses these fingerprints to block use of that same packet for interval assessment, even if its file was renamed or reformatted. It can flag exact reuse and repeated inputs. It cannot tell whether different packets came from the same person or recording. The fingerprints contain no readings or subject IDs, but someone who already has a packet could check for a match. Keep the profile private. If you have an older local profile without a packet list, calculate and save new bands from the original calibration inputs. Point forecasts are still available while the band is withheld.

Imported profiles describe their stated origin. The reader checks the exact fit fingerprint and timing and phase protocol, and checks the local packet fingerprint where it has the local calibration list. These checks do not verify the accuracy or provenance of the calibration widths.

The shaded range describes a single target reading at the nominal +120 ms horizon. The curve links successive forecasts and the bands have no joint coverage guarantee. The comparison uses nominal release indices, with unverified physical synchronization between force and EMG. Scores from one trial or calibration on your own selection give no performance result for the published evaluation panel. [Band method and study results](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/)
