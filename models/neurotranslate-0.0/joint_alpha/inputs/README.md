# Rebuild the seven NeuroTranslate replay tasks

A reach gives us two questions on the same clock. Given the arm and cortical activity up to this instant, how far will the hand move in the next tenth of a second? How many spikes will each electrode record? One macaque supplies both answers. Other measurement settings also appear in the joint model’s training and evaluation, from human muscle voltage to a tracked point on a moving animal. Each forecast belongs to its own source recording.

| Task | Input available at issue | Measured target | Training and historical evaluation |
|---|---|---|---|
| Macaque motion | 20 ten-millisecond bins of arm/handle coordinates and counts on 37 cortical contacts | Hand and near-elbow XYZ and handle XY displacement at +100 ms, in mm | One animal, 198 original trials on the earlier date, two recording blocks seven days later |
| Macaque cortical activity | The same synchronized history | 37 contact spike totals over the next 100 ms | The same animal and split. Counts combine the sorts on each contact. Single-neuron identity across days is unknown |
| Human leg muscle activity | Five 125 ms windows of central scalp voltage, leg muscle voltage and sacrum movement, plus posture and cue direction | RMS voltage over the next 125 ms, in µV for eight leg muscle channels | 18 healthy adults for training, six different previously assessed adults for evaluation, with both standing and walking |
| Human sacrum motion | The same synchronized history | Four XYZ sacrum displacements in mm from issue through +125 ms | The same participants and events. The two outputs share one measured population |
| Next sorted rat unit | A causal activity history for every unit in the local sorting table | Local unit in the next occupied millisecond bin when that bin contains exactly one spike | JS14 trips 55–78 for training, trips 80–89 for assessment, and ER1 trips 0–9 from another rat. Trip 79 is omitted |
| Optical fluorescence | Four earlier fluorescence samples from one ROI on its own clock, spanning about 3.6 s | Optical signal approximately 1.2 s later | One larval fish and eight adult worms for training, seven different fish for assessment. Assay scales use development readings alone |
| Animal landmark motion | Five timed frames of a point and its visible neighbours, in a coordinate frame fixed at issue | Two camera-plane displacements relative to the measured body radius, approximately 120 ms later, or 200 ms for the 5 Hz locust camera | Two independent mammal video recordings containing nine local tracks for training. Fourteen other recordings supply the historical comparison. A track number identifies an animal within its own recording |

The case unit changes with the instrument. Repeated go cues in one reach share an original trial. Fifty thousand rat forecasts still come from one training rat. A worm’s 32 regions of interest share an animal. Read the gold comparison by its actual sampling unit.

## From original recordings to private inputs

Use Python 3.13, Git, and the packages in `requirements.txt`. The human download contains multichannel recordings, so allow working space for both recording objects and their derivatives. Keep both destinations on private storage. Run these commands from the directory containing this guide.

```sh
python -m pip install -r requirements.txt
python rebuild.py train --cache recording-cache --out packed
```

To rebuild a single task family, add `--assay macaque`, `human`, `rat`, `calcium` or `landmark`. Each reader uses the original source version and checks its inputs. Missing source files, changed checksums, inaccessible storage, and network errors stop that family. If you have the exact upstream measurement archives already, use `python pack.py ASSAY train --inputs DIRECTORY --out packed` for offline packing. For rat, the directory contains `train`, `test` and `er1` trip directories. For calcium, it contains `train` and `held`. The landmark directory contains `tracks/train` and `tracks/test`. Macaque needs `train.npz`, then `block1.npz` and `block2.npz`. Human needs the paired `development.npz` and `assessment.npz` produced by the supplied balance and scalp readers.

After training and development-only model selection, use the same output directory and supply the saved checkpoint. The optical reader reuses the two scales learned on development recordings.

```sh
python rebuild.py held --cache recording-cache --out packed --frozen-model path/to/checkpoint.npz
```

The public code contains no measured human event rows. The resulting private archives do contain those measurements. The participant field groups training and assessment by whole person. It stays out of model features.

## Read one packed record

`manifest.json` in the output directory lists the order and units of every input and target. `X` carries earlier readings; `y` carries future measured values. Each archive also stores the recording group, the issue clock, and a reference forecast for that same case. Missing sensor or target values use IEEE NaN. A measured zero stays zero. Dense inputs use the order case, time, channel. The rat archive inserts the entire recording-local candidate axis between case and time. Sorted labels are indices into this local candidate set.

The human marker axes follow source order, mediolateral, superior–inferior, and anterior–posterior. Four timepoints at +8, +16, +24 and +32 samples each supply all three axes. The source sampling rate is 256 Hz. Only measurements available by the forecast issue enter the model. The archives' original offline filtering, spike sorting and optical processing still limit how closely these replays describe a live system.

## Original recordings and reuse

- Raeed Chowdhury, Joshua Glaser and Lee Miller recorded the macaque. The adapter aligns cortical counts and optical markers and converts both coordinate systems to mm. [CC0 recordings](https://doi.org/10.5061/dryad.nk98sf7q7) · [Measurement details](sources/macaque/RECONSTRUCT.md)
- Steven Peterson and Daniel Ferris recorded the healthy human balance tasks. The adapters align visual rotation, scalp and surface muscle voltage, and a sacrum marker within each event. [OpenNeuro ds003739 v1.0.3, CC0](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Source reader](sources/human_balance/README.md)
- Justin Shin and Shantanu Jadhav recorded JS14 and ER1. The adapter bins sorted spikes at 1 ms and forms causal traces for each unit. [DANDI release, CC BY 4.0](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Source credits, license and changes](sources/rat/NOTICE.md)
- Adam Atanas, Jungsoo Kim and colleagues recorded nuclear fluorescence in freely moving worms. Martin Haesemeyer and Kaarthik Balakrishnan recorded zebrafish forebrain fluorescence. The adapter selects early ROI traces on each instrument’s clock and uses a fixed development scale for each assay. [Worm data, CC BY 3.0 US](https://doi.org/10.5281/zenodo.19388374) · [Fish data, CC BY 4.0](https://doi.org/10.48324/dandi.000235/0.230316.1600) · [Extraction details](sources/calcium/README.md)
- The SLEAP acquisition teams, Angela Albi and Daniele Carlesso, and the WCON contributors supply the tracker data. The adapter expresses each point’s motion in units of its body’s measured radius at issue. The complete acquisition credits, dataset links, license texts and modifications accompany the reader. [All source credits](sources/landmark/SOURCES.md) · [SLEAP Clear BSD license](sources/landmark/SLEAP-LICENSE.txt) · [CC BY 4.0](sources/landmark/CC-BY-4.0.txt)

The original adapter code is available under CC0. Keep the applicable source credits and licenses with any data-derived release. The recording, tracker and study teams retain credit for their measurements. [Code license](LICENSE-CODE)

### Historical specialists

Two earlier models make forecasts on exactly these held events. The earlier macaque model uses the go cue as well as movement and spike history. The paired human study supplies the first published seed (431) for the early-fusion muscle forecast and the paired path forecast. The earlier cortical-count study forecasts a later set of count bins, so it cannot supply the same target. For a local scoring run, `references.py` aligns the models’ outputs by source trial or person, event and clock. It adds a `strong_reference` field to the historical records. These weights serve as evaluation references. The shared predictor runs on its own checkpoint.

```sh
python references.py macaque --inputs recording-cache/macaque --model path/to/reach-feedback-week/motor --out packed
python references.py human --inputs recording-cache/human/paired --model path/to/balance-weights.npz --out packed
```

The macaque reference is published. The balance fit can be reproduced privately from the same development population. Its original training protocol used three seeds, 384 updates and one shared set of development scales. The reference reader checks the archived balance file and all macaque reference components by checksum. [Macaque specialist](https://github.com/eliminatenoise/NeuroTranslation/tree/f2fb8a1bec811642b6718ec155e1bf755ac4bd0f/models/reach-feedback-week/motor) · [Human study and training instructions](https://github.com/eliminatenoise/NeuroTranslation/tree/f2fb8a1bec811642b6718ec155e1bf755ac4bd0f/models/neural-and-muscle-composites/balance)
