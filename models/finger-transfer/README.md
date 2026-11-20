# Following five fingers from a new person's cortical recording

The word “index” already tells you which finger a person is likely to move. Can the electrodes tell you how much it moves this time? In five Stanford FingerFlex recordings, a table that knew the word and the time since it appeared made smaller average errors than either model that also read the electrodes. Using the correct cortical recording helped slightly compared with using an earlier repetition. **Neither decoder met the prespecified criterion for transfer across people.** [Study design](METHOD.md) · [Full results](results.json)

Each estimate predicts how much a glove sensor will change over three consecutive 40 ms steps, separately for thumb, index, middle, ring and little finger. A bend and a release can both move the sensor. This target measures the magnitude of that motion and loses its direction. Joint angle, force and the intended action are different quantities. [Source measurements](source/README.md)

## What transferred

We set aside one person at a time. Their first 80 seconds gave us the usual range of their electrode and glove measurements. The other four people supplied all the training examples for that fold. After an eight-second gap, the held person's later trials tested the predictions. Each person supplied 18 complete early calibration trials. The five assessments together supplied 246 scored trials and 56 disjoint comparisons between two repetitions of the same instruction. Each person contributed one fifth of the reported mean, whatever their number of trials. The original external participants and later temporal reserves remain untested. [Method and selection](METHOD.md)

| Input at prediction | Ridge mean error | Transformer mean error |
|---|---:|---:|
| Named finger, display or blank, and elapsed time | 0.4811 | 0.4832 |
| Cortical measurement alone | 0.6100 | 0.6077 |
| Current cue and current cortical measurement | 0.5011 | 0.5134 |
| Current cue and preceding same-cue trial's cortical measurement | 0.5096 | 0.5175 |

Lower is better. Each error is divided by that digit’s early calibration scale. A separate cue table that learned one value per digit, cue and tick reached **0.4770**. Against this table, current cortex plus cue raised the Transformer's average error by 0.0364. The held-person results show who gained and who lost. [Per-person and per-finger results](results.json)

| Held recording | Scored trials | Disjoint repeat pairs | Cue table | Cue + cortex Transformer |
|---|---:|---:|---:|---:|
| bp | 31 | 6 | 0.4315 | 0.4574 |
| cc | 62 | 15 | 0.3964 | 0.4119 |
| ht | 62 | 15 | 0.4022 | 0.5302 |
| jc | 50 | 11 | 0.5454 | 0.4548 |
| jp | 41 | 9 | 0.6094 | 0.7126 |

The correct trial's cortical recording lowered Transformer error by 0.0041 compared with the earlier trial's recording, with a descriptive 95% person-resampling interval of 0.0030 to 0.0050. But if the question is *how much more did this finger move on the second try?*, simply predicting the same amount on both tries beat the aligned Transformer in all five people. Its mean extra error was 0.0394 (descriptive interval 0.0210 to 0.0578). With five people and training sets that overlap between folds, these intervals describe this development group. They give no assurance about the next person. [All prespecified comparisons and intervals](results.json)

## Run an invented example

Use Python with NumPy and CPU PyTorch. From this directory run the two commands below. They need no original recording or network connection. The first prints five forecasts for each of six models. The second compares them with the saved output from the tested environment.

```sh
python invented.py
python invented.py --check
```

The example supplies 280 ms of invented electrical signals, seven invented contact assignments and invented calibration scales. Its index-finger cue has been on the screen for 800 ms. The weights in `weights/` come from a separate final fit to all five development people. They represent the models you can run here. The table above comes from the independent held-person fits, each of which had only four training people. [Example output](invented-result.json) · [Decoder implementation](model.py)

## Use a calibrated packet

Store each input locally as a NumPy `.npz` archive, without Python objects. Use original contact order throughout. Two contacts in the same region share a code, so checking the region vector alone cannot detect their exchange. The operator must preserve the physical channel identities within each recording. All arrays below use samples by channels, with no patient ID or geometry.

| Input to initial calibration | Shape and meaning |
|---|---|
| `voltage` | (80000, C) amplifier counts, consecutive rows at 1000 Hz from time zero |
| `region` | (C,) integer region code per original contact, including all unassigned contacts |
| `cue` | (80000,) integer display values, 0 blank and 1–5 named digit |
| `time_ms` | (2000,) verified nominal timestamps 0, 40, …, 79960 ms |
| `glove` | (2000, 5) sensor counts at those ticks in thumb-to-little order |

```sh
python decode.py calibrate initial.npz personal-scales.npz
python decode.py predict packet.npz personal-scales.npz --digit 2 --phase display --elapsed-ms 800
```

`personal-scales.npz` contains `mean` and `sd` of shape (2, C), low band then high band, five positive `gain` values and the unchanged `region` vector. Keep it private. Each new packet contains exactly two fields, `voltage` of shape (280, C) ending at cutoff t and its `region` vector. Give the current named finger, display or following blank, and milliseconds since that phase began. Study cutoffs occupy offsets 9–42 ticks from the first grid point of the phase, with another 160 ms remaining inside it. Predictions outside this source task or timing are untested. Use `--family ridge` to run the linear decoder or `--mode cue` or `--mode cortex` to use one input stream. Both output scales are printed. A prediction never takes a glove sample. [Packet and calibration code](movement.py)

## Reproduce the fit

The tested CPU environment used Python 3.13.15, NumPy 2.4.6 and PyTorch 2.14.1+cpu. Preparing the original MATLAB files also used SciPy 1.18.1. Use the matching CPU build if you need numerical comparison. The standalone cache reader checks source and array hashes against the Stanford release. The following commands obtain the five permitted early prefixes and reproduce the study. Use **private** directories for the cache and run outputs. The run directory must be new. Each numbered source command can also take `--mat path/to/original.mat` for independent offline acquisition.

```sh
python source/fingerflex_source.py D01 --cache-dir private-cache
python source/fingerflex_source.py D02 --cache-dir private-cache
python source/fingerflex_source.py D03 --cache-dir private-cache
python source/fingerflex_source.py D04 --cache-dir private-cache
python source/fingerflex_source.py D05 --cache-dir private-cache
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python reproduce.py --cache private-cache --output private-run --threads 2
```

On Windows, set the three thread environment variables to 2 before the last Python command. `private-run/results.json` holds the fold summaries, `private-run/folds/` contains their private predictions and weights, and `private-run/deployment/` holds the separate all-person fits. The released `results.json` gives raw-count errors for each digit as well as scaled errors and paired gains. The `person_order` field identifies the order of the person-level results and contrast vectors. The digit order is always thumb, index, middle, ring, little. [Source identities and ethics](source/README.md) · [Rights and changes](RIGHTS.md) · [File checksums](MANIFEST.sha256)
