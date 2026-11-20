# How much will each finger move?

The screen says *index*. It tells you which finger the participant was asked to move. It leaves open when they will bend it, how far it will bend, and how much the other fingers will move along with it. This offline experiment asks whether voltages recorded at the cortical surface help predict what a glove actually measured on each finger. [Original FingerFlex experiment](https://doi.org/10.1371/journal.pcbi.1002655)

The cue alone gave the best picture of the next short stretch of movement in this recording. On 23 later trials from the same person, the cue-only Transformer scored **0.289**. Adding the cortical measurements raised its error to **0.321**. The estimated increase was **0.032**, with a 95% paired block-bootstrap interval of **0.008 to 0.057**. Errors here are averaged across the five fingers after scaling by each finger’s variation in the training data. Lower is better. [Aggregate results](results.json)

## What the glove measured

Each prediction covers four future glove readings, one every 40 ms on the released recording grid. Imagine one sensor reads 100, 130, 130, then 115. Its three changes have magnitudes 30, 0 and 15. Their mean is 15 sensor units per step. This counts both bending and straightening as movement and keeps a stationary interval in the average. The first reading sits 40 ms after the last cortical input, and the fourth sits 160 ms after it. The experiment produces one number like this for each finger. The glove supplied flex-sensor counts. An angle in degrees, a fingertip position in space, the direction of movement and a force would each require a different measurement.

Four recent voltage windows feed the cortical decoder. Each window contains 160 ms of data from 46 contacts. We summarize the power in two frequency bands, then give the model the four summaries in order. The visual-cue input identifies the finger named on the screen, whether the name is still visible, and time in the current part of the trial. Every main model works without a past glove reading. A separate comparison asks how far the recent glove readings alone can take us. The original study reports a 37 ms lag between glove and amplifier measurements (3 ms standard error). The released grid provides a common row index. It supplies no independent timestamp for each packet, so the forecast horizon refers to that grid. [Original measurements](https://doi.org/10.1371/journal.pcbi.1002655) · [Acquisition description](https://www.bbci.de/competition/iv/desc_4.pdf) · [Frozen method](METHOD.md)

## What changed the forecasts

The five central columns give mean absolute error in stored sensor units per nominal 40 ms step. Each complete trial has the same weight. The final column scales each finger’s error by its training target standard deviation and gives the five fingers equal weight. *Wrong trial* runs the aligned weights again with cortical measurements from an earlier trial with the same cue, phase and tick. *Ridge* is a linear readout with a penalty on large weights. The Transformer can learn relationships among the four time windows.

| Readout | Thumb | Index | Middle | Ring | Little | Scaled mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Training average | 9.67 | 24.01 | 21.94 | 17.59 | 8.37 | 0.455 |
| Ridge, cue alone | 6.35 | 15.05 | 13.01 | 13.18 | 3.80 | 0.288 |
| Ridge, cortex alone | 9.86 | 24.73 | 22.65 | 15.82 | 8.70 | 0.454 |
| Ridge, cue and cortex | 7.78 | 18.54 | 16.35 | 14.71 | 5.90 | 0.354 |
| Ridge, wrong trial | 7.84 | 20.10 | 16.78 | 15.88 | 6.18 | 0.372 |
| Transformer, cue alone | 6.84 | 14.93 | 12.66 | 12.85 | 3.98 | 0.289 |
| Transformer, cortex alone | 8.43 | 22.71 | 21.53 | 15.58 | 6.53 | 0.412 |
| Transformer, cue and cortex | 7.01 | 16.24 | 15.82 | 13.03 | 5.20 | 0.321 |
| Transformer, wrong trial | 6.77 | 18.64 | 14.93 | 15.43 | 5.55 | 0.341 |
| Separate ridge with past glove only | 6.78 | 19.53 | 17.60 | 17.23 | 10.78 | 0.403 |

Could the model distinguish two movements made in response to the same instruction? We paired trials with the same cued finger, lined them up at the same point in the display or blank interval, and subtracted the first trial’s glove movement from the second’s. Then we did the same for the predictions. The model must get the difference between movements right even though the instruction repeated.

Ten disjoint pairs qualified. Two had thumb cues, two index, three middle, and three ring. The little finger contributed readings during all ten, but there was only one scored little-finger cue trial and so no repeat pair for that cue. On this grid the paired cue inputs coincided, so their predicted difference was exactly zero. A zero-difference prediction beat the aligned Transformer by **0.083** scaled error units (95% interval **0.063 to 0.105**). The aligned Transformer in turn beat the wrong-trial signal on this test by **0.076** (**0.038 to 0.113**). Trial identity mattered to that comparison. The simpler prediction still did better. Both the aligned Transformer and the aligned ridge missed the criteria set in advance for a within-cue advantage. [Paired results, per-finger intervals and display/blank scores](results.json)

Fifty-two earlier trials supplied 3,536 training cutoffs, and the 23 later trials supplied 1,564 evaluation cutoffs. Adjacent windows share many of the same measurements. We resampled contiguous groups of three whole trials, or three disjoint pairs for the repeat comparison, to describe uncertainty within this one recording. A ten-pair interval and one participant provide limited evidence. Fingers also move together, so five output columns do not establish independent control of five fingers. The later reserved source sections and the other participants remain untested. The experiment concerns recorded movement in a timed laboratory task. It does not validate a live device, stimulation, physical control or use on a different hand. [Complete design and decision rule](METHOD.md)

## Try the saved models

From this directory, run the invented example with Python, NumPy and PyTorch. It generates an artificial voltage history locally, reads the saved weights, and prints five movement estimates from each readout. No recording, network connection or accelerator is needed. The separate glove-history comparator uses invented readings too.

```sh
python invented.py --check
python check.py
```

For your own code, `features.packet` accepts 280 consecutive amplifier rows in original contact order, the displayed digit code (1–5), the phase (0 display, 1 blank), and elapsed phase time in milliseconds. It returns four tokens with 60 cue and 92 cortical features each. See the invented example for constructing the batch, choosing a readout and loading its weights. Use the same recorded contact order and signal scale when comparing these saved coefficients. [Invented example](invented.py) · [Feature calculations](features.py) · [Readouts](model.py)

## Reproduce the fit

Download `fingerflex.zip` from version 11 of Kai Joshua Miller’s Stanford Digital Repository collection and extract `fingerflex/data/bp/bp_fingerflex.mat` locally. The preparation utility checks the original file hash and writes the fixed 362,000-row prefix. The original MATLAB file stores complete variables together, so preparing a prefix from scratch transiently decompresses those variables. The fit accepts only the separately verified prefix. Use an empty output directory. [Stanford deposit](https://purl.stanford.edu/zk881ps0522) · [Source and software versions](provenance.json)

```sh
python prepare_prefix.py bp_fingerflex.mat prepared.npz
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python reproduce.py --prefix prepared.npz --output reproduced --threads 2
```

The preparation step also needs SciPy. The saved fit used CPU PyTorch. A Python environment with matching NumPy, PyTorch and SciPy versions is recorded in the provenance file. The second command rebuilds every weight file and the aggregate report. `MANIFEST.sha256` contains the distributed file hashes. [Preparation](prepare_prefix.py) · [Training entry point](reproduce.py) · [Licence and attribution](RIGHTS.md)

## Methods — original study ethics

The following is the original study statement required by the task deposit. Its reference is Miller and colleagues’ 2012 experiment. [Original study](https://doi.org/10.1371/journal.pcbi.1002655)

Ethics statement: All patients participated in a purely voluntary manner, after providing informed written consent, under experimental protocols approved by the Institutional Review Board of the University of Washington (#12193). All patient data was anonymized according to IRB protocol, in accordance with HIPAA mandate. These data originally appeared in the manuscript “Human Motor Cortical Activity Is Selectively Phase- Entrained on Underlying Rhythms” published in PLoS Computational Biology in 2012 [Reference].
