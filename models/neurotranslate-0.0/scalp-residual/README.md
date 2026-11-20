# Does an early scalp reading help correct a movement forecast?

A person sees a cue to move the supported right arm. We know the task and the last half second of readings from the arm and hand. Start with the typical movement previously recorded for that task. Will measurements from scalp electrodes bring the forecast closer to the next elbow, forearm and finger readings? [Try the model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#early-signals)

The template comes from seven people, each of whom contributed three execution runs. For every task it contains nine typical changes: three instruments, each at half a second, one second and one and a half seconds after the cutoff. The new readouts estimate corrections to this template. They use a robust loss that limits the influence of very large errors during fitting. The arm component combines changes within four 125 ms intervals with the existing movement encoder. Absolute starting levels do not enter the correction.

## What the fresh runs showed

All 210 trials were eligible. Average scaled error was **0.49777** for the mechanical correction and **0.49628** when scalp readings were added. Giving the same model scalp readings from another repeat of the same task scored **0.49675**. Only two of the five people improved when scalp was added to mechanics; the paired 95% interval for the change was −0.00733 to +0.00263. The cue median alone scored **0.49696**. These small differences missed the specified test for practical benefit.

The model using arm and eye readings scored 0.50245. Adding the part of the scalp readings left after the eye adjustment gave 0.50314; swapping just that part gave 0.50470. The test for additional information after eye adjustment also failed. The independent experimental units are five people, not 210 independent people. Paired intervals from five people have limited precision.

On a secondary check, 204 of the 210 trials passed the pre-cue variability screen. Requiring both the trial and its same-cue replacement to pass left 198 pairs. The analysis reports scores on both supports alongside the full test. The numbers are mean absolute errors normalized separately for each instrument and forecast time using variation in the fitting group. The seven fitting people supplied 882 trials. [Per-instrument errors, task summaries, intervals and formal tests](results.json) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/scalp-forecast/)

## What gets paired

The six scalp sites are FC3, FC4, C3, C4, CP3 and CP4, in that order. The three eye channels are the source columns 62, 63 and 64. The source files and the authors’ table disagree about the sides of the outer eye channels in some recordings, so the model keeps the numbered order. For each electrode, provide the mean over each of four consecutive 64-sample intervals on the 512 Hz electrical clock. The second interval ends on the stored cue tick; the fourth ends 0.25 seconds later. The model subtracts the average of the first two bins from each of the four. The mechanical channels use the original 64 Hz clock.

The eye comparison matters because a signal at a scalp electrode can share variation with the eyes. One model gets arm and scalp readings. A second gets arm and eye readings. A third subtracts the part of each scalp signal predicted from the three eye channels by a regression fitted on the training people. The joint model sees both the eye readings and what remains from the scalp. This subtraction is a statistical adjustment; it does not isolate a particular brain source.

In the trial-pairing test, an electrical recording from another repeat of the same task replaces the original. The arm history, task and target remain fixed. For the eye-adjusted control the replacement scalp pattern is adjusted using its own eye readings before it is paired with the recipient’s arm and eyes. This control uses another recorded trial and is evaluated offline. [Frozen protocol](PROTOCOL.md)

## Run an invented example

From the parent model folder, with Python and NumPy installed:

```sh
python predict.py scalp-residual/example.json
```

Set `domain` to `early_signal_change`. All methods except `still` use a known study cue. `cue_median` uses only that cue; `previous_shared` and `mechanics` also need four mechanical `bins`. For `scalp`, add `scalp_bins` (4 rows × 6 sites). For `eye`, add `eye_bins` (4 × 3). For `residual_scalp` or `joint`, supply both electrical fields. Use only the fields the chosen method requires. The mechanical columns are the three sensor medians followed by their three within-bin differences (second-half median minus first-half median), in the order elbow, forearm rotation, proximal index-finger glove sensor.

The invented example uses the earlier group reader’s practice motion and constructed electrical values. The output gives nine signed changes on each instrument’s own stored scale. The source does not establish physical units, anatomical sign or hardware synchronization. [Example outputs](example-results.json) · [Original data and codebook](https://doi.org/10.5281/zenodo.834976)

## Reproduce fitting and evaluation

The paper by Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz describes the acquisition and the visual task cues. Use motor execution, S1–S7 runs 1–3 for fitting and S8–S12 run 4 for assessment. These fourth recordings were kept unopened until both the shared and separate Transformer models were frozen. The same five assessment people previously supplied their first three runs for a mechanical forecast. S13–S15 remain outside these studies. Download the prior group checkpoint and use a source cache outside the public project. The portable reader checks original file sizes, checksums and channel order. [Acquisition paper](https://doi.org/10.1371/journal.pone.0182578) · [Frozen parent checkpoint](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/687aebb5252a7680c3ab08efe3198e925fb6b507/models/neurotranslate-0.0/movement-weights.npz)

```sh
python scalp-residual/download_early_originals.py fitting fitting-cache
python scalp-residual/study.py fit fitting-cache parent.npz fitted.npz fit-receipt.json
python scalp-residual/download_early_originals.py fourth assessment-cache
python scalp-residual/study.py assess assessment-cache fitted.npz fit-receipt.json scores.json
```

The original recordings and data-derived weights and results retain Creative Commons Attribution 4.0. This reanalysis extracts four early bins, adjusts for eye-channel variation, fits robust readouts and evaluates predictions against arm measurements. Credit the original authors and identify further changes. Original project code and constructed examples carry the project’s CC0 dedication. [Data licence](CC-BY-4.0.txt) · [Project dedication](../LICENSE)
