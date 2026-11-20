# Read the original muscle measurements

This program extracts the length and angle of a tracked bundle of muscle fibres from the authors’ ultrasound measurements. It selects the first two seated ankle-lifting trials from each of the eight people in the study split. Run it with Python 3.11 or newer, NumPy and SciPy. An internet connection is needed the first time it retrieves each selected MATLAB file from the BioImage Archive. The source data, original authors, units and changes are described in the accompanying rights note. [Source and licence](RIGHTS.md)

```sh
python -m pip install numpy scipy
python acquire.py development --cache ankle-tracking --manifest source-manifest.json
python acquire_assessment.py assessment --cache ankle-tracking --manifest assessment-manifest.json
```

The verified extraction used Python 3.13.15, NumPy 2.5.5 and SciPy 1.18.1 on Linux. The development group is A01 through A04. The assessment group is A05 through A08. Add `--person A01 --trial 1` to the development command to reproduce just the first trial. Each manifest lists the exact archive members and their SHA-256 fingerprints, which identify the original bytes and the extracted numbers. The extractor reuses a local original when its download receipt matches. It opens only the geometry fields needed for that file.

Each `trial-N.knots.npz` contains five one-dimensional arrays. `length_mm` and `angle_deg` are the authors’ tracked fascicle length and pennation angle. `tracking_row` counts from the first original table row, starting at one. `tracker_time` preserves each original TIME label. `segment_id` changes after a gap in that trial’s label sequence. A forecast using ten tracking steps should stay within one segment. The first four people illustrate why a common physical duration cannot be assigned to those ten steps. [Source details](RIGHTS.md)

Beside each output, `trial-N.source.json` records the table names and headings, original byte count and fingerprint, measurement units, row count, range and spacing of TIME, and how the angle and length agree with the original exports. For a file with unsupported geometry the program reports the reason and withholds the extracted arrays.

The assessment command uses the same geometry checks. One source file contains MATLAB graphics objects that prevent a complete variable listing in some SciPy versions. The assessment reader can open the four geometry fields in that file directly. Keep both Python files in the same folder.
