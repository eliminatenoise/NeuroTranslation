# NeuroTranslation

NeuroTranslation is active again, alongside [NeuroSurge](https://github.com/eliminatenoise/NeuroSurge) and [Interoceptomics](https://github.com/eliminatenoise/Interoceptomics). These previews remain experimental; no validated downloadable model or finalized-model GUI is available yet.

## Open the current previews

[Download a Windows, macOS or Linux launcher](https://eliminatenoise.github.io/NeuroTranslation/START.html). The data-companion launcher opens the application directly.

- [Browser data companion](https://eliminatenoise.github.io/NeuroTranslation/index.html): import and inspect JSON/CSV, check declared metadata and align compatible recordings. Its example uses invented signals; no trained model is connected. [Source and usage](demo/README.md).
- [Selected experimental papers](papers/): four technical/accessible PDFs, with a content manifest, reading aid and full scientific summary. The recorded review covers 26 of 546 pages; 520 are outside visual acceptance.
- [Historical R11 manuscript source](papers/experimental/r11-source/): the preserved unbuilt source snapshot. It has no matching R11 PDFs and omits external figure/font dependencies. Proposed G35 terminology in that snapshot remains unadopted.
- [Portable interface source](interfaces/experimental/portable/): a recording-specific Python/HTML interface proposal. No weights, model payloads or runnable model download are included.

Each preview names what you can inspect and what remains untested. An experimental upload makes the work available; it does not establish a completed Large Movement Model, biological translation or clinical use.

How does a pattern of neural activity become a movement we can measure? NeuroTranslation is a research programme for learning and testing the links between nervous-system activity, muscle activity, body mechanics and movement. It is also our name for a proposed field: mapping neural signals and representations between explicitly defined sources and targets, with the context and limits kept attached.

Consider a hand reaching for a cup. A neural recording captures one observation. EMG captures electrical activity in muscles. Motion capture estimates where the hand goes. A mechanical model describes quantities such as joint motion, forces and muscle–tendon behaviour. Bringing these together gives us a testable question: can the permitted observations predict a specified outcome, and how closely does that prediction match an independent measurement?

## What we are building

The model under development is **NeuroTranslate 0.0**. Its broader direction is a **Large Movement Model**: a learned model connecting neural observations with musculoskeletal structure, mechanics and measured movement. The name describes an ambition, not an accepted large model or a demonstrated universal decoder.

The training programme distinguishes four source groups:

| Source | What it contributes | What must remain clear |
| --- | --- | --- |
| Neural data | Specified brain, spinal or peripheral neural observations; relevant autonomic and visceral pathways where actually recorded | No single recording is assumed to cover the whole nervous system. Recording modality, location and task matter. |
| Muscle data | Myography, including EMG from named muscles | Muscle electrical activity is not direct nerve activity, muscle force or a simulator’s activation command. |
| Displacement data | Observed or tracking-derived position, pose and movement | Coordinates need units, calibration, timing and a declared physical frame. Estimated pose is not automatically measured force. |
| Mechanics data | Measured mechanical quantities and explicitly identified physics-generated examples | A simulated body can support learning and controlled tests; it cannot supply independent biological ground truth for itself. |

The neural scope is deliberately broader than the brain alone. Brain, spinal and peripheral activity belong in the programme, with task-relevant autonomic or visceral observations where available. Current source coverage is incomplete. The main focus is the motor–sensory system: movement and the feedback associated with it.

Some datasets contain simultaneous observations from the same subject and event. Others can contribute through unpaired representation learning, movement pretraining or transfer between anatomically or mechanically comparable features. Those are different uses. We do not manufacture a shared subject or clock to make unrelated files look synchronized.

More data and more varied data may help a model generalize. That is a hypothesis to test with controlled comparisons, rather than a guarantee attached to dataset size.

## How a result earns its claim

A prediction must name its input, target, organism, task, units and validation domain. Preprocessing and model selection must respect the training and evaluation partitions. Comparisons need relevant baselines, including persistence or nuisance information where those could explain an apparent gain.

We keep negative results. A lower average error does not establish that neural information helped, that a model generalizes to another person, or that it reproduces the underlying biology. Error, uncertainty, failures and the conditions of the test belong beside the result. Recorded-feature reconstruction does not demonstrate sensory delivery, and software prediction does not demonstrate skill transfer.

## What is available here

Read the [selected experimental paper drafts](papers/): technical and accessible editions of **NeuroTranslation: A New Paradigm In Brain-Body Mapping.** and **Brain2Body: The Next Generation In Body-Brain Interfacing.** The selected PDFs have their own R2/R3 build provenance; the preserved R9/R11 source snapshots are historical, not matching current build sources.

These papers develop the scientific and engineering argument. The accessible editions are intended to explain the same difficult concepts in plain language; they are not a substitute for methods, evidence or limitations. The project is also developing models, data interfaces and interactive demonstrations. **No validated downloadable Large Movement Model or finalized-model GUI is available yet.**

The [data companion](demo/README.md) imports JSON and CSV, checks their structure, displays the original samples and aligns declared paired recordings. It does not execute a trained translation model. Its example contains invented values.

The selected paper folder includes its relative JSON companions and [research reading aid](papers/experimental/scientific-layout-2026-11-15/research-evidence-reading-aid.md). The [R9 metadata erratum](papers/errata/r9-reading-aid-metadata.txt) records a historical omission; it is not the availability record for this edition. Existing scientific, rights and output limits remain.

## How the projects fit together

- [Interoceptomics](https://github.com/eliminatenoise/Interoceptomics) develops the presentation and explanatory work around internal-body sensing and neural connectivity.
- **NeuroTranslation** develops the mapping methods, models, data relationships and both papers.
- [NeuroSurge](https://github.com/eliminatenoise/NeuroSurge) is the first-person game demo under development, making left-hand and arm motor control visible through a virtual cortex and anatomical limb.

They share a programme, terminology and scientific standards. A compelling demonstration in one project does not validate every claim in the others.

## Reuse

The project’s original contributions are dedicated to the public domain under [CC0 1.0](LICENSE), to the extent the project holds the rights. Third-party material, including fonts, cited works and incorporated figures, may have separate rights. See the [current paper and font notices](papers/experimental/scientific-layout-2026-11-15/NOTICE.md).

[Terminology and project scope](PROJECT-CONTEXT.json).
