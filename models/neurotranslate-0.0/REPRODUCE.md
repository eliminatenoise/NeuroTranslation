# Predict and reproduce

## Predict without fitting

Python and NumPy run the two examples. Use the included `movement-weights.npz` (SHA-256 `8636991f783c781142ab811096b0f1769db0a6bcf9386810a3ad7b25fae4e2a6`). The stored configuration identifies the two spatial endpoints, the wrist-angle inputs and the two angular targets. Every mode uses the same temporal attention, position embedding, feed-forward layer and normalization, amounting to 5,016 frozen values. Each angular route adds 1,610 trainable projection and readout values. [Weights](movement-weights.npz) · [Source and rights](NOTICE.md)

```sh
python -m pip install numpy
python predict.py angular-example.json
python predict.py spatial-example.json
```

The angular JSON has `domain` set to `wrist_angle`. Supply a batch of `bins` with shape [N,16,C], an `anchor_deg` array [N,2], and one integer `slot` in 0–5 per example. Each row must come from one participant, run and trial. Supply all required channels through the cutoff. Use mode `motion` for two angle channels, `emg` for those two plus four forearm channels, and `full` for those six plus eight scalp channels. For a missing channel, select a supported mode that uses the measurements you have. The program rejects nonfinite inputs and negative RMS amplitudes. It accepts only the input dimensions required by that mode. Row identity, source clocks and alignment must be checked before passing bare arrays to the reader. [Extraction and channel names](wrist-source/README.md)

Each row of the sixteen-bin history covers 16 stored samples. The first two features are the mean encoder angles over the bin **minus the angle at the forecast cutoff**. The anchor gives both cutoff angles in degrees. A forearm feature is the square root of the mean squared left-minus-right electrode difference in the bin, in µV. A scalp feature is the signed mean voltage in µV. Preserve source channel order. Four consecutive bins form one temporal token. Each bin stays distinct within that token. The six cue slots refer to targets at 384, 512, 640, 768, 896 and 1024 stored ticks after the visual cue. For a target at T, the anchor lies at T−128 and inputs cover T−383 through T−128 inclusive. Return axes are extension and radial deviation in degrees. Each positive angle points towards extension or towards the thumb, respectively.

For a distance forecast pass the original object with `x` and a list of spatial labels `domain`. Each batch row uses one of the two strings `wrist` or `rat`. The original input takes four past motion intervals with five physical features each. Its output remains a single distance in centimetres at the nominal 250-ms horizon. [Original spatial input contract and utilities](https://github.com/eliminatenoise/NeuroTranslation/tree/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/models/shared-motion)

## Reproduce the angle comparison

Obtain only the six named public archives. From the package directory, run the extractor below with your private input and output paths. The data recipe tabulates the exact publisher file identities. It independently verifies clocks, role and sample identities, modality pairing and hashes of all twelve arrays. The original extraction used NumPy 2.4.6. Training, scoring and portable inference here used Python 3.13.15, NumPy 2.5.3 and PyTorch 2.14.1+cpu on Linux. Follow the source extractor's own requirements in a separate environment when reproducing that step. Keep recording-linked arrays local. [Data recipe](wrist-source/README.md)

```sh
python -B wrist-source/extract_wrist.py --archives archives --output train.npz
```

For fitting, install CPU PyTorch and NumPy. Set the BLAS, OpenMP and MKL thread limits to one. The matched synthetic CPU check selected two PyTorch intra-op threads. The first command below writes six held-person fits and the final fit on all six people. The second calculates every new-model contrast and persistence benchmark using only held-person predictions. Both commands expect a new output directory.

```sh
python -B fit.py fit --spatial spatial-seed.npz --threads 2 --data train.npz --manifest wrist-source/array-hashes.json --out fits
python -B score.py --fits fits --data train.npz --manifest wrist-source/array-hashes.json --out scores
```

The model begins with the published spatial checkpoint, hash `9a3649cb8f2119984e7f9f0b96a07bdc95e1833c7068f0e9caef2680f22e3179`. Each of six folds fits only on five people. All channel, anchor and target scaling comes from those same five. Three angular projections and readouts fit the three permitted input sets using four full epochs. Three controls use the same fitting order, seed, optimizer, inputs and opportunities with one random frozen temporal core. The final deployable state uses all six people and the pretrained core with the same settings. The six fold scores describe the method, while this final state has no independent test in this report. The study uses one random core draw. No model was chosen by the six outer results. [Exact architecture, seeds and fit](protocol.json) · [Fitting code](fit.py)

For the older motion CNN and its EMG correction, follow the linked earlier study's own prepare/fit/score commands on the same archives. Pass its output folder as `--rebuilt-comparators PATH` on the new `score.py` command, with a fresh `--out` folder. The comparison requires the same person, block, trial, slot, run, cue, target tick, anchor and observed target. It also checks the exact numerical hashes of the published comparator's held forecasts. Earlier receipt bytes can be supplied with `--comparators` in the original local workspace. [Prior model reproduction](https://github.com/eliminatenoise/NeuroTranslation/blob/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/benchmarks/wrist-forearm-correction/REPRODUCE.md) · [Comparator forecast hashes](comparator-arrays.json)

The comparison uses equal-person mean squared errors on the two axes before taking the square root. The leave-one-out ranges omit a person from the aggregate without refitting. Signed differences and absolute changes in predictions answer different questions. The published table contains only aggregate scores and influence ranges. Private local files also contain source-linked, per-person outputs, subject to the data terms. Different numerical backends may change final digits. This package was checked on Linux. The Windows and macOS launchers open the same offline page on those operating systems. [Aggregate results](results.json)
