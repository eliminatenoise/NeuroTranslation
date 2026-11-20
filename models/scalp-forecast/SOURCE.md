# Read the scalp, eye and arm recordings

A person sees a cue to move their right arm or hand, or to rest. Electrodes on the scalp and around the eyes record electrical changes. A glove records finger position and the supporting exoskeleton records elbow and forearm movement. The visual cue tells us what the person was asked to do. The instruments tell us what was recorded during that attempt. [Original experiment](https://doi.org/10.1371/journal.pone.0182578)

## Get the recorded files

Keep `download_early_originals.py` and `ofner_early.py` in the same folder. Open a terminal in that folder and run the commands with Python 3.9 or newer. On Windows you can use `py -3` in place of `python`. Replace `arm-recordings` with the folder where you want to keep the recordings.

```sh
python download_early_originals.py fitting arm-recordings
```

This gets the first three motor-execution runs from each of seven people, S1–S7. The 21 files take 1.895 GB. If a recording is already there, the script checks its length and publisher MD5 checksum and reuses it. Each line of output gives the file's SHA-256 fingerprint. You can verify the same files offline by adding `--check-only`. [Versioned files and publisher checksums](https://zenodo.org/records/834976)

To repeat the assessment, first freeze the fitted models, their inputs and the comparison rules. Then get the fourth motor-execution run from each of S8–S12. These five recordings take 0.451 GB. Earlier runs from these five people appeared in a separate mechanical comparison. This selection uses a fresh run from each of them.

```sh
python download_early_originals.py fourth arm-recordings
```

Use `--workers 1` for one download at a time. The default is two and the largest setting is four. If a connection drops, rerun the command. A completed file passes the size and checksum checks before it takes the publisher’s filename. If a forced shutdown leaves a `.gdf.lock` folder behind, confirm that the corresponding transfer has stopped before removing that empty lock folder.

## Find a scalp reading and the elbow reading available at that instant

```python
from ofner_early import EEG_SITES, Run

with Run("arm-recordings", 2, 1) as run:
    cue = next(tick for tick, code in run.events if code == 0x600)
    c3 = EEG_SITES.index("C3") + 1
    scalp_at_cue = run.window(c3, cue, cue + 1)[0]
    elbow_index = cue // 8
    elbow_at_cue = run.window(93, elbow_index, elbow_index + 1)[0]
    print(cue / 512, scalp_at_cue, elbow_index / 64, elbow_at_cue)
```

The first and third numbers are seconds from the beginning of the recording. The event and electrical clocks have 512 ticks per second. The arm stores 64 readings per second, so the latest available elbow reading can precede the cue by up to seven electrical ticks (13.7 ms). The reader converts file event position one to sample index zero. It reads each channel on its stored time grid. The timing of the actual screen change and delays in the individual instruments remain uncalibrated. [GDF format](https://pub.ista.ac.at/~schloegl/biosig/GDF2.0/TR_GDF219.pdf) · [MNE's event-index conversion](https://github.com/mne-tools/mne-python/blob/main/mne/io/edf/edf.py)

Channel numbers start at one. Sample indices start at zero, and the stop index in `window` falls just past the samples returned. Channels 13, 17, 28, 32, 43 and 47 are scalp sites FC3, FC4, C3, C4, CP3 and CP4 in the authors' channel table. S1's files have generic scalp labels, so the site names for those recordings come from the table. Channels 62–64 are the three eye recordings. Their left/right header order varies between files. Inspect `run.header_labels[61:64]` for the actual order. The study used the right mastoid as its electrical reference and AFz as ground. Each scalp reading carries the electrical activity that reached that electrode. Identifying the tissue that produced it requires further evidence. [Authors' channel and cue tables](https://zenodo.org/records/834976/files/data%20set%20description.pdf) · [Recording methods](https://doi.org/10.1371/journal.pone.0182578)

The arm readings used here are elbow (93), forearm rotation (94) and the base of the index finger (68). The file stores little-endian, 64-bit floating-point numbers. The header's digital-to-physical scale is one with offset zero, and the unit fields are blank. Keep changes in each instrument's native units. Converting them to physical angles or comparing absolute electrical amplitude across people would require additional calibration.

## Credit

Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz (2017), *Upper limb movements can be decoded from the time-domain of low-frequency EEG*, Zenodo record 834976. The recordings are licensed under Creative Commons Attribution 4.0 International. This package adds the file selection, integrity checks and a reader for the stored samples. Downloads preserve the authors’ original bytes. [Dataset and licence](https://doi.org/10.5281/zenodo.834976) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
