# NeuroTranslation

Reach for a cup. A neural recording captures activity at the recording site. An electrode over a muscle picks up electrical activity as the arm moves. Calibrated cameras estimate where the hand went. NeuroTranslation asks how well one of these observations can predict another. The hand’s measured path gives us something to check the prediction against.

[Open the browser data companion](https://eliminatenoise.github.io/NeuroTranslation/index.html). Choose **Load example**, then open **Metadata checks** to see the units, clock and source declared for each invented signal. You can also inspect your own JSON or CSV files locally and align streams when the files declare the same organism, subject, recording and clock and their partitions are compatible. The companion runs without installation. [Import and alignment guide](demo/README.md) · [Desktop launchers for Windows, macOS and Linux](https://eliminatenoise.github.io/NeuroTranslation/START.html)

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

The public companion imports, plots and aligns samples. The example is synthetic, and the companion has no trained translation model attached. The developmental learner passed 29 synthetic software checks across its four input families. Those checks exercised timing and mask handling, training-only normalization and the transition between pretraining, training and fine-tuning. All three parameter updates used mock data. This version of the learner has completed zero real-data fits. A validated model download and a GUI for that model are still pending.

For a biological result, specify which inputs were available at prediction time, the organism, task, target and units. Keep evaluation subjects or sessions outside training and model selection. A hand tends to keep moving in its current direction, so a predictor can obtain a low error using only recent motion. Compare against that baseline and test what changes when the neural input is withheld.

The papers retain a negative result from a separate forecasting comparison. Across 18 fits and 720 saved epochs, neither model-admission rule passed and none of the five benefit claims held. Reconstructing recorded features leaves sensory delivery and skill transfer as separate experimental questions. [Read the forecasting results](papers/experimental/scientific-layout-2026-11-15/research-evidence-reading-aid.md)

## Code, related projects and reuse

- [Portable interface source](interfaces/experimental/portable/) contains the Python and HTML proposal for a recording-specific interface. The package contains no weights.
- [Historical R11 manuscript source](papers/experimental/r11-source/) preserves an unbuilt snapshot. Its external figures and fonts are incomplete, its proposed terminology was never adopted, and the selected PDFs have separate build provenance. [R9 metadata erratum](papers/errata/r9-reading-aid-metadata.txt)
- [Interoceptomics](https://github.com/eliminatenoise/Interoceptomics) explores internal-body sensing and neural connectivity through anatomical models. [NeuroSurge](https://github.com/eliminatenoise/NeuroSurge) uses a virtual cortex and limb to explore left-hand and arm control in a first-person game. [Shared terminology and project scope](PROJECT-CONTEXT.json)

Original project contributions are dedicated to the public domain under [CC0 1.0](LICENSE) to the extent the project holds the rights. Fonts, cited works and incorporated figures may carry separate terms. [Paper and font notices](papers/experimental/scientific-layout-2026-11-15/NOTICE.md)
