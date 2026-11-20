# Read a cued right-arm movement

A person sees a cue to bend the right elbow. The cue marker tells you when the instruction appeared on the recording clock. An elbow sensor on the supporting exoskeleton tells you what happened next. The same file contains electrical activity recorded at 61 scalp sites, three eye channels and a glove that recorded finger movement. Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz recorded these signals at Graz University of Technology. [Study](https://doi.org/10.1371/journal.pone.0182578) · [Original dataset, version 1](https://doi.org/10.5281/zenodo.834976)

This reader opens the first three motor-execution runs of source participant S1, who used the right arm and was the study’s only left-handed participant. Each run includes six cues each for elbow flexion, elbow extension, turning the palm up, turning it down, closing the hand, opening it and resting. The seven names identify the tasks depicted by the cues. The files contain neither a transcription of the instructions nor the participant’s report of intent. [Authors’ description, tables 1 and 2](https://zenodo.org/records/834976/files/data%20set%20description.pdf) · [Experiment and recording](https://doi.org/10.1371/journal.pone.0182578)

## Download and verify

Use Python 3.9 or newer. Open a terminal in the directory containing `ofner_source.py`. Choose a private directory outside the website or package for the original recordings. The three files need 270,251,972 bytes in total. The first command fetches the originals from Zenodo and checks their size, the publisher’s MD5 checksum and the complete-file SHA-256. The second command repeats the checks offline. [Zenodo record](https://zenodo.org/records/834976)

```sh
python ofner_source.py fetch /path/to/private-cache
python ofner_source.py verify /path/to/private-cache
```

This example reads one second of scalp activity around the first elbow-flexion cue. It then finds the most recent elbow sample available at the exact cue time. Channel numbers come from the authors’ table and begin at one. Sample indices begin at zero. The last argument to `window` is the first sample **outside** the interval.

```python
from ofner_source import Run

with Run("/path/to/private-cache", 1) as run:
    cue_tick = min(t for t, code in run.events if code == 0x600)
    eeg = run.window(28, cue_tick - 256, cue_tick + 256)  # C3, 512 samples
    elbow_index = cue_tick // 8
    elbow = run.window(93, elbow_index, elbow_index + 1)[0]
    print(cue_tick / 512, elbow_index / 64, len(eeg))
```

## Two sample grids

The files store one-second records. The first 64 channels contain 512 samples each per second. The last 32 contain 64 each. At a 512 Hz cue tick `t`, the elbow sample at index `t // 8` can be up to seven ticks (13.671875 ms) old. In run 1 the first elbow-flexion cue has file position 22,324. Subtracting one and dividing by 512 gives 43.599609375 s. The last available elbow sample is row 2,790 at 43.59375 s. The reader returns the samples at their recorded cadence. Display latency, clock drift between devices and delays in the sensors have not been calibrated here. [GDF format](https://pub.ista.ac.at/~schloegl/biosig/GDF2.0/TR_GDF219.pdf) · [MNE’s GDF event-position conversion](https://github.com/mne-tools/mne-python/blob/main/mne/io/edf/edf.py)

Each run contains 42 task markers. The matching end marker for every cue is exactly 1,536 EEG ticks (3 s) later. The participant was asked to hold the movement until the cue ended, then return to the starting posture. A task marker specifies when the action was requested. An observed movement onset needs a definition in terms of the measured motion. [Authors’ paradigm and onset measurement](https://doi.org/10.1371/journal.pone.0182578)

## Electrode and sensor names

The full channel order in `codebook.json` and `ofner_source.py` comes from table 2 and the headers of all three files. For example, the headers label each scalp channel simply `eeg`. The table identifies 28 as C3, 30 as Cz and 32 as C4. The reference was on the right mastoid and ground was at AFz. These site names locate scalp electrodes. A voltage recorded at one site can reflect several sources, including eye and muscle activity. [Authors’ channel table](https://zenodo.org/records/834976/files/data%20set%20description.pdf) · [Recording methods](https://doi.org/10.1371/journal.pone.0182578)

Use indices **62, 63 and 64** for the eye channels. The table gives left, middle, right. The files give `eog-r`, `eog-m`, `eog-l`. The lateral assignments of 62 and 64 therefore remain uncertain. The table also leaves 80–83 and 96 unnamed, although the files supply labels. The map retains both readings. Channel 68 is the index-near glove sensor, 93 the elbow sensor and 94 the exoskeleton’s forearm-rotation sensor. [Original table and files](https://zenodo.org/records/834976)

All three files store little-endian, 64-bit floating-point values. Digital and physical minima and maxima coincide, so the file conversion multiplies by one and adds zero. The physical-unit codes are zero and the unit strings are blank. Report changes in native sensor units. The paper describes joint-angle measurements and EEG analysis in microvolts. Establishing degrees, volts or the anatomical direction corresponding to a positive elbow reading for these stored channels requires additional calibration evidence. [Recording and analysis](https://doi.org/10.1371/journal.pone.0182578) · [Data and codebook](https://doi.org/10.5281/zenodo.834976)

## Credit and changes

Ofner, P., Schwarz, A., Pereira, J. and Müller-Putz, G. R. (2017). *Upper limb movements can be decoded from the time-domain of low-frequency EEG*, dataset version 1, Zenodo. The authors released the dataset under Creative Commons Attribution 4.0 International. This package supplies a three-run reader, integrity checks, channel crosswalk and zero-based access to event times. The downloaded recordings retain the authors’ original bytes. Credit the authors and identify subsequent processing when reusing their material. [Dataset](https://doi.org/10.5281/zenodo.834976) · [Paper](https://doi.org/10.1371/journal.pone.0182578) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
