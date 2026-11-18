# Reading the evidence in these four papers


## What does a signal add once the model sees the wrist move?

Fit on six people, check on three different people. The 960 development
trials supplied 5,760 angle pairs. The temporal model's error rose from
4.053° with angle history and cue time to 4.523° with scalp EEG. For
ridge regression, adding EEG lowered error from 6.530° to 6.439°.
The same ridge baseline dropped to 6.174° with forearm surface EMG.
Giving the fitted EMG model a trace from the next eligible trial in the
same recording block, at the same cue time, raised error to 6.941°.
These comparisons use the same recordings. [Temporal study](https://github.com/eliminatenoise/NeuroTranslation/tree/a95ae62ddcd51e87a3e97d4348a732ecb11dd052/benchmarks/wrist-pointing-temporal) · [Surface EMG study](https://github.com/eliminatenoise/NeuroTranslation/tree/a95ae62ddcd51e87a3e97d4348a732ecb11dd052/benchmarks/wrist-pointing-muscle)

The last input precedes the target by 128 rows on the stored 512 Hz
grid. That gives a nominal 250 ms interval. The encoder's reported
update rate is 100 Hz and the physical delays remain unverified. The
reserved test remains sealed. The papers explain why an offline forecast,
feedback delivered during a movement and a skill retained afterwards
need different measurements.
[Dataset descriptor](https://doi.org/10.1038/s41597-026-07287-z) ·
[Version 3 data](https://doi.org/10.6084/m9.figshare.29666735.v3)

## What does scalp EEG add once the tracker has seen the hand?

The timing and hand-history model predicted horizontal palm position with 1.09 mm root mean squared error across three development participants. Adding scalp EEG raised the error to 1.22 mm. Each person had equal weight. The original cue-based comparison stopped before fitting because it needed an earlier palm position absent from every trial. The later comparison used a separately specified window, measured from the first available palm position. Its 100 ms input lead is a property of the archived arrays. [Read the cohort comparison](https://github.com/eliminatenoise/NeuroTranslation/tree/d8d56fd2b0f5d609d1e2cd19ff13af4297414c9f/benchmarks/scalp-eeg-palm-history)

## Why propose Antechinus?

A marsupial can be observed after birth through stages that happen before birth in many other mammals. The skeletal evidence in these pages comes from fat-tailed dunnarts. The skin-healing evidence comes from short-tailed opossums. Whether Antechinus offers easier implantation or recovery remains an empirical question. The milk studies measured growth, organ maturation or antibody transfer. Precise direction of neural or immune development through milk remains a proposal. [Developmental anatomy](https://doi.org/10.1038/s42003-021-02506-2) · [Skin healing](https://doi.org/10.1006/dbio.1995.1141) · [Wallaby growth](https://doi.org/10.1002/jez.a.174) · [Opossum antibody transfer](https://doi.org/10.1071/RD18121)

## One acquisition, two forecasting tasks

The study uses the original TRAIN acquisition `sub-03/Cyl` from Reach&Grasp version 1.0, published through IIT Dataverse under a declared CC BY 4.0 licence. Of 3,127 source rows, four invalid rows were excluded, leaving 3,123. The observations comprise 64 derived surface-EMG root-mean-square features with trailing 40 ms support and 18 glove-angle coordinates. Their source-declared units are millivolt-derived RMS and degrees. Physical calibration, synchronization, feature-availability times and online latency remain unqualified.

Each task receives 64 rows of its own stream and forecasts that stream’s later recorded features, one or ten rows ahead. Separate input and prediction components surround one shared gated recurrent unit (GRU) core. The muscle task predicts muscle features; the glove task predicts glove features. Sharing the core supplies no neural input, muscle-to-motion mapping, force or sensory-afferent target, and a row offset is not an independently verified physiological delay.

The pilot made 40 joint updates. Its continuation added 950, reaching 990 cumulative updates and 30,545 window exposures per task across five passes through a 6,109-window catalog. Those windows overlap and are revisited. They remain observations from one acquisition, not independent people or new acquisitions. Batch size also changed from four to 32 while the update budget and repeated exposure increased, so this comparison does not isolate coverage as the cause of improvement.

## The baseline and the unfavourable slices

The untrained state, frozen 40-update state, continued 990-update state and persistence faced the same recorded windows, observed targets, masks and saved original-TRAIN scalers. No scaler was refitted in continuation or evaluation. The full catalog and original first four-window subset were reported separately; the subset belongs to the catalog and is not an independent test.

The table gives the recorded normalized mean squared error pooled across the full selected TRAIN catalog. Lower is better for this specified error measure. Pooling adds squared-error sums and observed-feature counts before division; it does not give unsupported equal weight to differently sized slices. These normalized scores are dimensionless, not squared millivolts or degrees. Their decimal places preserve the numerical record without establishing biological accuracy.

| Target stream | Initial, 0 updates | Frozen, 40 updates | Continued, 990 updates | Persistence |
| --- | ---: | ---: | ---: | ---: |
| Surface-EMG RMS | 1.0195127528126222 | 1.065703117562344 | 0.48371488886038944 | 0.4391345726797162 |
| Glove angles | 0.8750431745338253 | 1.1992171367822229 | 0.37219431399606173 | 0.024541819466343505 |

The pooled result contains different outcomes. EMG at offset ten beats persistence; offset one fails. Glove fails at both offsets. In the original first four windows, glove becomes worse than both the initial and 40-update states. A favourable offset or prefix cannot replace the complete comparison. The private checkpoint remains **UNPROMOTED**.

The full summary retains every offset, scope, squared-error sum, observed-feature count and condition, along with the recorded software and source fingerprints. No independent participant/acquisition uncertainty estimate, statistical p-value or DEV/TEST generalization result is supplied. This remains a TRAIN diagnostic, even where a particular slice improves.

## Separate studies

The LINK neural comparison is a different study. Its 18 fits and 720 saved epochs retain the decisions **BOTH_FAIL** and **ALL_FIVE_FAIL**. Its four reserved dates and protected tests remain closed; complete independent checkpoint and update-trajectory verification remains unfinished. The forecasting result does not replace that failure or supply its missing verification.

MyoHand is different again: two simulated trajectories and 200 dependent integration steps establish a recorded input-to-state software response. They supply no trained controller, training corpus or biological ground truth. A simulated response, a muscle-feature forecast and a neural decoding comparison must keep their own sources, denominators and limits. Earlier studies likewise retain their source, withdrawal or repair records; this aid recomputes no outcome.

## The proposed movement model

The programme’s four broad training groups are neural observations, including brain, spinal, peripheral and relevant visceral sources; myography; measured motion; and physics-generated examples. Myoception includes task-relevant tactile and proprioceptive sensory context. EMG is muscle electrical activity, not an afferent recording. More or more varied data may be worth testing, but quantity/diversity scaling remains a hypothesis. The present comparisons do not demonstrate the four-source Large Movement Model, neural-to-body translation, cross-modal generalization or biological teaching.

The biological roles are trainer and trainee. An ML learner means a computer model and remains a separate role. Earlier tutor/pupil labels belong to historical editions.

## Terminology, sources and availability

The terminology source is canonical registry revision **36**, with **202 terms** and **nine proposals**, identified by SHA256:

`40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406`

This companion supplies that identity, not a full registry snapshot or a promise of access to private binding profiles, projections or historical overlay files. The earlier paper-only overlay remains unadopted as canonical terminology; its historical wording is not certified as verbatim revision 36. The structured aid retains the relevant historical distinctions and fingerprints without turning them into download links.

Reach&Grasp attribution is [DOI 10.48557/L6OWMM](https://doi.org/10.48557/L6OWMM), version 1.0. The recorded selected pair is `sub-03/Cyl`, provider file IDs 14486 and 14393. The full summary retains the filenames, recorded sizes and checksums, release metadata, processing changes and attribution limits. These source-data records are preserved: staging does not re-read or checksum the raw recordings, calibrate or synchronize them, or supply new rights clearance.

The earlier R9 package omitted `research-evidence.json`; its erratum disclosed that omission. A local companion does not prove the older public link has been repaired, and complete source portability remains unverified. The [content manifest](manifest.json) identifies the four candidate PDFs, their companion files, exact hashes and build provenance. It is not an upload or hosting receipt; publication and remote verification are separate facts.

CC0 applies only to selected owned paper/manuscript-source contributions, with third-party notices retained. Upstream and combined-use rights require their own qualification. Paper availability establishes no peer review, validated model/GUI release or biological validation. Whole-paper scientific, editorial, citation, rights, reference-series, physical, held-out, native, font, layout and export assessment, together with finalized-model/GUI assessment, remain open.
