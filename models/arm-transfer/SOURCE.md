# Read the original arm recordings

A participant sits with the right arm supported. A screen asks them to bend the elbow, straighten it, turn the forearm, open or close the hand, or rest. The recording contains the cue time and the readings from the moving arm. The model uses three of those readings, one from the elbow, one from the forearm and one from a glove on the index finger. [Original study](https://doi.org/10.1371/journal.pone.0182578)

## Get the fitting recordings

Keep `download_originals.py` and `ofner_transfer.py` together. From that folder, run the command below with Python 3.9 or newer. On Windows you can use `py -3` in place of `python`. Replace `arm-recordings` with the folder where you want to keep the original files.

```sh
python download_originals.py fitting arm-recordings
```

This gets the first three motor-execution runs from each of seven people, S1–S7. The 21 files need 1.895 GB. The script checks each file’s size and the publisher’s MD5 checksum, then prints its SHA-256 fingerprint. If a recording is already in the folder, the script checks and reuses it. To repeat those checks entirely offline, add `--check-only`. [Dataset files and checksums](https://zenodo.org/records/834976)

## Assess on new people

Keep S8–S12 aside until the model weights, preprocessing, scoring code and decision rules have been fixed. Then request their 15 recordings, which need another 1.352 GB. The three remaining study participants, S13–S15, stay in reserve.

```sh
python download_originals.py assessment arm-recordings
```

If the connection drops, rerun the same command to continue from the completed files. If a force-quit leaves a `.lock` directory for a missing file, first check that no download for that file is running. Once it has stopped you can remove that empty lock directory and rerun the command.

## Read a cue and the elbow sample at that time

```python
from ofner_transfer import Run

with Run("arm-recordings", 2, 1) as run:
    cue_tick = next(t for t, code in run.events if code == 0x600)
    elbow_row = cue_tick // 8
    elbow_at_cue = run.window(93, elbow_row, elbow_row + 1)[0]
    print(cue_tick / 512, elbow_row / 64, elbow_at_cue)
```

The first number is the cue time in seconds. The second is the time of the last stored elbow sample at or before the cue. There are 512 event ticks and 64 movement samples per second, so the latest available elbow reading can precede the cue by up to 7/512 of a second. The third number is the elbow reading in the instrument’s native units. The files leave physical units blank. Comparisons in degrees would require a separate calibration.

Channel numbers start at one. The elbow sensor is 93, forearm rotation is 94 and the index-near glove sensor is 68. Sample indices start at zero. In `window(channel, start, stop)`, the stop index falls just past the final sample returned. A cue names the action requested on the screen. The timing and extent of movement come from the recorded sensors. [Authors’ cue and channel tables](https://zenodo.org/records/834976/files/data%20set%20description.pdf)

## Credit

Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz (2017), *Upper limb movements can be decoded from the time-domain of low-frequency EEG*, dataset version 1. The authors released the recordings under Creative Commons Attribution 4.0 International. This package selects the runs, verifies the original bytes and reads the stored samples on their two time grids. The downloader keeps each recording as the authors supplied it. [Dataset and licence](https://doi.org/10.5281/zenodo.834976) · [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/)
