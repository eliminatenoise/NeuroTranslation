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
