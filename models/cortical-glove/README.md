# Can a brain recording beat the last glove reading?

A participant saw the name of a finger and bent and straightened it at their own pace. A glove measured the bend of all five fingers. Suppose you already have the last four glove readings and know which finger appeared on screen. Can electrical activity recorded at the surface of the cortex tell you more about where the fingers will be three glove readings from now?

In this development experiment, keeping the last reading gave the lowest average error. Adding cortical power to either fitted model increased error. This is a result for one person, two bands of recorded electrical activity and a nominal 120 ms forecast during one cued task. [Original experiment](https://doi.org/10.1371/journal.pcbi.1002655) · [Source data](https://purl.stanford.edu/zk881ps0522)

## What the glove measured

One sensor on each finger measured flexion in the glove's own counts. The archive records the cortical grid at 1,000 samples per second. Each glove reading occupies 40 rows on that clock, corresponding to a nominal 25 readings per second. We compared predictions with the first row of each 40-row block, including blocks where the recorded value stayed the same. Joint angles, grip force and individual hardware timestamps are unavailable here. The original investigators reported 37 ms of lag between the instruments with a standard error of 3 ms. We used the shared file clock directly. The physical lead time for a particular movement remains unknown. [Original acquisition and timing](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1002655) · [Glove measurement rate](https://www.bbci.de/competition/iv/desc_4.pdf)

## What happened three ticks later

Each entry under a finger is its mean absolute error in glove counts across the same later trials. The last column averages the five errors after dividing each by that finger's training-target standard deviation. A lower number means a closer prediction. Each finger was scored during every eligible trial, including trials cued for other fingers. The little finger was the cued finger only once in the evaluation set.

| Forecast | Thumb | Index | Middle | Ring | Little | Normalized mean |
|---|---:|---:|---:|---:|---:|---:|
| Keep the last reading | 19.26 | 51.04 | 44.79 | 39.10 | 11.79 | **0.1774** |
| Screen cue and phase, linear | 62.75 | 147.93 | 106.30 | 116.83 | 81.80 | 0.5661 |
| Recent movement, linear | 22.15 | 60.28 | 51.71 | 42.67 | 19.57 | 0.2104 |
| Recent movement and cue, linear | 27.53 | 67.94 | 54.11 | 50.61 | 30.10 | 0.2502 |
| Same inputs plus cortical power, linear | 32.80 | 74.63 | 61.96 | 56.48 | 34.87 | 0.2849 |
| Same linear weights with earlier-trial cortex | 33.10 | 78.95 | 63.74 | 55.23 | 35.04 | 0.2892 |
| Linear model fitted and scored with earlier-trial cortex | 34.34 | 77.53 | 63.98 | 56.92 | 33.68 | 0.2905 |
| Recent movement and cue, transformer | 23.81 | 53.69 | 38.18 | 33.82 | 22.34 | 0.1868 |
| Same inputs plus cortical power, transformer | 30.60 | 66.66 | 54.71 | 48.37 | 29.90 | 0.2517 |
| Same transformer weights with earlier-trial cortex | 30.77 | 69.63 | 53.27 | 47.32 | 27.99 | 0.2489 |

The primary linear model lost accuracy with cortex on every finger and on all 23 evaluation trials when errors were averaged across fingers. Its normalized error rose by **0.03470**, with a paired 95% interval of **0.02396 to 0.04630**. Replacing the cortical inputs with those from a previous trial tests what happens when the cue, identity of the finger, task phase and glove history still match. Correct pairing reduced error by **0.00426** compared with this substitution, with an interval of **−0.00061 to 0.00897**. The predeclared requirement for an incremental cortical advantage was a positive lower bound against both comparators. The transformer’s error also rose with cortical input, by **0.06490** (interval **0.04514 to 0.08350**).

The cue tells the model which finger the participant was asked to move. It also tells the model when the screen went blank. Neither observation tells us when the participant chose to start each bend. The error from keeping the last reading averaged 0.2349 during the display and 0.1199 during the following blank. The linear model with cortical inputs reached 0.3111 and 0.2587 respectively. A reliable forecast over these short intervals can owe much to fingers staying still. Training readings for the ring and little fingers had a correlation of 0.319. The task and the five glove columns alone cannot establish five independently controlled movements.

## How we tested it

Only the first 362 seconds of one recording entered development. The cutoff at 240 seconds was fixed before model scoring. We excluded four seconds on each side and any cue-plus-rest pair crossing a boundary. In each partition the first usable trial for each digit supplied earlier-trial cortex only. That left 52 fitting trials (3,536 forecast cutoffs) and 23 later evaluation trials (1,564). Fitting trials had 10 thumb, 11 index, 13 middle, eight ring and 10 little-finger cues. Evaluation had five, four, seven, six and one. Every trial contributed 34 forecasts during the cue and 34 during the following blank. Adjacent predictions share measurements. The uncertainty calculation resampled consecutive groups of three complete trials with replacement and wrapped at the ends, using 5,000 paired draws. Its intervals describe variation within this recording. Other people and the later source validation and test windows remain unexamined in this analysis.

At each forecast cutoff the models saw four ordered tokens ending 120, 80, 40 and 0 ms earlier. Each contained the five glove readings and a history-derived cue basis encoding the displayed finger, whether the screen had gone blank, and time since that transition. The electrical input for each token comprised 160 ms of samples from 46 cortical contacts ending at that token. We converted the amplifier counts to microvolts using 0.0298 µV/count, subtracted the instantaneous common average across contacts, demeaned each window, applied a symmetric Hann taper and summed the one-sided spectral power from 12–32 Hz and 70–150 Hz. We excluded bins from 113.75–126.25 Hz around the second harmonic of 60 Hz mains noise. Inputs used the natural logarithm of one plus band power expressed in µV². No electrode was selected using evaluation data. These bands summarize electrical power; co-occurring sensation, movement, shared recording artifacts and planning remain possible contributors.

For the linear readouts, we flattened the four tokens and fitted ridge regression with a fixed penalty of 0.05 times the number of training cutoffs after standardization. Models with glove history predicted the change from the most recent reading. The cue-only model predicted the future reading directly. The matched transformer used one encoder block, two attention heads, width 24, a 48-unit feedforward layer, a fixed seed and 24 epochs. Its baseline zeroed all standardized cortical inputs. Every scale, offset and fitted coefficient came from the earlier training trials. Each wrong-trial input used the preceding eligible trial of the same cued digit in the same partition, at the corresponding display or blank tick. Grid rounding permits a difference of up to 39 ms in elapsed time between matched trials. These fits offer a retrospective test of a particular representation. They establish neither a causal pathway nor live hand control. [Full per-digit estimates, intervals and correlation matrix](study-results.json) · [Required source ethics statement](RIGHTS.md)

### Original study ethics statement

Ethics statement: All patients participated in a purely voluntary manner, after providing informed written consent, under experimental protocols approved by the Institutional Review Board of the University of Washington (#12193). All patient data was anonymized according to IRB protocol, in accordance with HIPAA mandate. These data originally appeared in the manuscript “Human Motor Cortical Activity Is Selectively Phase- Entrained on Underlying Rhythms” published in PLoS Computational Biology in 2012 [Reference].

[Original study identified by the archive reference](https://doi.org/10.1371/journal.pcbi.1002655)

## Run an invented example

With Python and NumPy installed, open a shell in this folder and run these commands. The input has two invented oscillations, seeded noise and invented glove readings. The default command uses the included aligned linear weights and prints five predictions. It requires no participant data or network connection.

```sh
python invented.py
python invented.py --model motion_cue
python check.py
```

With CPU PyTorch installed, `python invented.py --model encoder_aligned` exercises the fitted transformer. The numerical JSON fixture contains exactly the invented input and two reference ridge outputs. Compare in float64 to an absolute tolerance of 1e-8 counts. Inputs far from this participant's task can give unrealistic readings. [Invented input and expected outputs](invented-case.json) · [Implementation](model.py)

## Reproduce the study

Training is optional. `reproduce.py` verifies the SHA-256 of the separately prepared development archive before loading it. The full fit used Python 3.13, NumPy 2.4.6 and PyTorch 2.14.1+cpu, two BLAS/intra-op threads and one inter-op thread. Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to `2` for matched threading. Use an empty folder for the new outputs.

```sh
python reproduce.py --prefix PATH_TO_PREPARED_DEVELOPMENT_NPZ --output reproduced
```

The source record and exact preparation recipe are in the provenance file. The example and the fitted model run independently of that archive. The package distributes source-linked results and checkpoints under CC BY-SA 4.0, and original code under CC0. [Provenance and preparation](provenance.json) · [Rights, modifications and required ethics wording](RIGHTS.md)

For users who separately hold the original named Stanford MATLAB member, `python prepare_prefix.py ORIGINAL_MEMBER.mat PREPARED.npz` runs the original crop and serialization locally (requires SciPy and NumPy). It verifies both the source member and the prepared file digests and refuses to overwrite an existing file. MATLAB stores whole variables together; decoding the named member transiently decompresses later rows before retaining the prescribed prefix. The model and study never score or fit those rows. The preparation command is optional. [Exact source member and checksums](provenance.json)
