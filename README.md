# NeuroTranslation

Reach for a cup. A neural recording captures activity at the recording site. An electrode over a muscle picks up electrical activity as the arm moves. Calibrated cameras estimate where the hand went. NeuroTranslation asks how well one of these observations can predict another. The hand’s measured path gives us something to check the prediction against.

[Open Palm replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay). Import a prepared IACKD right-hand trial and choose **Compare estimates**. You can put the two fitted estimates beside the tracked palm position, inspect individual samples and download the comparison. Prepare the trial from the archived recordings using the study instructions. [Study and trial preparation](benchmarks/scalp-eeg-palm-history/)

The companion also inspects your own JSON or CSV locally. It can align streams when they declare the same organism, subject, recording and clock and their partitions are compatible. Choose **Load example**, then **Metadata checks**, to see how the invented example records those fields. The companion runs without installation. [Import and alignment guide](demo/README.md) · [Desktop launchers for Windows, macOS and Linux](https://eliminatenoise.github.io/NeuroTranslation/START.html)

## Predicting measured movement

How much do three scalp EEG channels add once you know where the hand was? In the palm replay study, both fits had elapsed time and earlier palm position and velocity. One fit also had EEG. We trained on three people and evaluated on three others. Across 173 development trials, the person-weighted root mean squared error rose from 1.093 to 1.223 mm when EEG was added, and it rose for each development participant. The latest inputs preceded the target by 100 ms on the stored clock. The recordings were processed after collection, so live decoding latency remains untested.

The first analysis started its clock at the task cue and found no eligible trials because required palm observations were missing. The replay follows the alternate analysis, which starts at the first available palm sample at or after that cue. [Six-person study, fitted parameters and reproduction](benchmarks/scalp-eeg-palm-history/)

In a hand-to-mouth task, did muscle activity predict elbow angle better than knowing when the movement began? A ridge regression trained on one participant had 62.4° root mean squared error on a second participant. A trajectory based on movement onset had 30.8°. Each participant contributed five repetitions, and their dominant arms differed. The benchmark includes the code, data sources and errors for each repetition. [Read and reproduce the experiment](benchmarks/surface-emg-elbow/README.md)

In the earlier IACKD palm pilot, a ridge model using three EEG channels had 7.51 mm root mean squared error on 59 development trials. A template using only time within the trial had 7.38 mm. The pilot used stored recordings from one participant for training and another for development. [Read and reproduce the two-person pilot](benchmarks/scalp-eeg-hand/README.md)

## Read the papers

| Paper | Technical edition | Plain-English edition |
| --- | --- | --- |
| *NeuroTranslation: A New Paradigm In Brain-Body Mapping.* | [NeuroTranslation technical edition](papers/experimental/scientific-layout-2026-11-15/neurotranslation-technical.pdf) | [Read NeuroTranslation explained](papers/experimental/scientific-layout-2026-11-15/neurotranslation-explained.pdf) |
| *Brain2Body: The Next Generation In Body-Brain Interfacing.* | [Brain2Body technical edition](papers/experimental/scientific-layout-2026-11-15/brain2body-article.pdf) | [Read Brain2Body explained](papers/experimental/scientific-layout-2026-11-15/brain2body-simple-english.pdf) |

Both editions develop the methods and their limits. The plain-English editions give more space to the steps between them. [Download all four papers with their companions](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/papers/downloads/NeuroTranslation-Brain2Body-Paper-Previews-2026-11-15.zip), or use the [reading aid](papers/experimental/scientific-layout-2026-11-15/research-evidence-reading-aid.md) to trace the studies behind the argument. Extract the ZIP with its folder structure intact so links between files work.

These are experimental drafts. The recorded visual reviews cover selected issues on 26 of 546 pages. The [paper index](papers/) identifies the selected builds, the 520 pages outside that review and the historical source editions.

## What goes into a translation?

**NeuroTranslate 0.0** is the model under development. Its longer-term aim is a **Large Movement Model** connecting neural observations with muscle activity, body mechanics and measured movement. Recording site and task matter. A model trained on cortical activity during a reach has yet to earn a claim about spinal, peripheral, autonomic or visceral signals in another task.

| Source | What it contributes to the reach |
| --- | --- |
| Neural recordings | Activity from the brain, spinal cord or peripheral nerves, at the sites actually recorded. Autonomic and visceral pathways enter the analysis where relevant recordings exist. |
| Muscle recordings | Electromyography (EMG) measures electrical activity in named muscles. A direct nerve recording measures activity at a different site. Estimating force from EMG requires additional measurements or a mechanical model. |
| Displacement recordings | A tracker estimates hand position or joint angle. The coordinate frame, calibration, units and timestamps give those numbers meaning. |
| Mechanics data | Instruments can measure force. A physics simulation can generate a force estimate under stated assumptions. An independent force measurement from the same task, in the same units, gives that estimate a test. |

Suppose the motion trace belongs to a different reach. It might help a model learn common movement patterns. It cannot tell us where *this* hand was when *this* neural sample was recorded. A supervised prediction needs evidence linking the subject, event and time across the recordings. Even two files with the same clock label can carry an offset.

## What has been tested?

The public companion imports, plots and aligns samples. Its invented example exercises those tools. Palm replay instead runs the fitted regressions for the specified IACKD study on an imported trial. The published development result and the error for the imported trial have different denominators.

The separate general learner passed 29 synthetic software checks across its four input families. Those checks exercised timing and mask handling, training-only normalization and the transition between pretraining, training and fine-tuning. All three recorded parameter updates used mock data. The study regressions have a narrow input and task contract. A validated general-model download and a GUI for that model are still pending.

For a biological result, specify which inputs were available at prediction time, the organism, task, target and units. Keep evaluation subjects or sessions outside training and model selection. A hand tends to keep moving in its current direction, so a predictor can obtain a low error using only recent motion. Compare against that baseline and test what changes when the neural input is withheld.

The papers retain a negative result from a separate forecasting comparison. Across 18 fits and 720 saved epochs, neither model-admission rule passed and none of the five benefit claims held. Reconstructing recorded features leaves sensory delivery and skill transfer as separate experimental questions. [Read the forecasting results](papers/experimental/scientific-layout-2026-11-15/research-evidence-reading-aid.md)

## Code, related projects and reuse

- [Portable interface source](interfaces/experimental/portable/) contains the Python and HTML proposal for a recording-specific interface. The package contains no weights.
- [Historical R11 manuscript source](papers/experimental/r11-source/) preserves an unbuilt snapshot. Its external figures and fonts are incomplete, its proposed terminology was never adopted, and the selected PDFs have separate build provenance. [R9 metadata erratum](papers/errata/r9-reading-aid-metadata.txt)
- [Interoceptomics](https://github.com/eliminatenoise/Interoceptomics) explores internal-body sensing and neural connectivity through anatomical models. [NeuroSurge](https://github.com/eliminatenoise/NeuroSurge) uses a virtual cortex and limb to explore left-hand and arm control in a first-person game. [Shared terminology and project scope](PROJECT-CONTEXT.json)

Original project contributions are dedicated to the public domain under [CC0 1.0](LICENSE) to the extent the project holds the rights. Fonts, cited works and incorporated figures may carry separate terms. [Paper and font notices](papers/experimental/scientific-layout-2026-11-15/NOTICE.md)
