# Get the original tracking tables

The source is the AnkleImage Task 3 deposit. These commands fetch two recordings for each person in the original four-person development group and four-person assessment group. Each original MATLAB file contains both motion data and ultrasound-derived estimates. The extractor checks the named tracker tables against the deposited length and pennation fields, and verifies the original file and array checksums. Python 3.11 or later, NumPy and SciPy are required. Use a new directory with enough space to store the original files and their derived arrays.

```sh
python -B source/acquire.py development --cache ../ankle-data --manifest source/source-manifest.json
python -B source/acquire_assessment.py assessment --cache ../ankle-data --manifest source/assessment-manifest.json
```

Each row keeps its original tracker order. Some development recordings have 992 rows, others 9,920. The public scores weight each of a person’s two trials equally, then each person equally. Ten tracking steps are the unit of the forecast. The tracker labels and the movie playback rate do not establish a common elapsed time. The source export also varies across files. Some identify both the tracked muscle bundle and the reference tissue. Others verify the first bundle's reported length and angle while leaving the reference tissue's own orientation unavailable.

An ultrasound section measures geometry in the image plane. A projection along one apparent bundle cannot establish the direction or size of a three-dimensional force. The original tracker may use later frames or manual corrections in preparing these exports. A forecast from the resulting history cannot establish latency in a live experiment. [Source deposit](https://doi.org/10.6019/S-BIAD1482) · [Original methods](https://doi.org/10.1038/s41597-024-04285-x) · [Dataset rights](source/RIGHTS.md)
