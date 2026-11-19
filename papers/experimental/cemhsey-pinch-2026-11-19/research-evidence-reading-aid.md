# Reading the evidence in these four papers

## One finger, two days

Keep the index finger still and press harder. In Hyser, the next reading came from one finger's voltage sensor. For four people held out of training, the voltage history alone gave 14.355 mV mean absolute error. Adding aligned forearm EMG gave 14.457 mV. A second test fitted models to other trials from the same person and day. The choice of error metric changed which model scored better.

Both days and all 40 development trials supplied 18,000 overlapping cutoffs
for each model. Earlier EMG and EMG from the same phase of the next trial
both gave lower average absolute errors than aligned EMG. The gain over
voltage history was −0.103 mV with a descriptive 95% range from −0.321
to +0.115 mV across person resamples. The result uses four people.

Within the training group, models fitted on three other trials from the same
person and day gave MAEs of 17.043 mV with voltage history and 17.316 mV with
aligned EMG. Their RMSEs were 26.180 and 25.851 mV. Squaring before averaging
gives larger misses more weight. Those trials came from the day used for scoring.

### Does yesterday’s calibration carry?

We kept the shared forecast fixed and learned an offset and a gain correction
from five labeled Day 1 trials per person. Day 2 supplied the readings to score.
In the four previously scored development participants, mean absolute error
with voltage history was 14.912 mV unchanged, 15.091 mV with the person’s own
Day 1 adjustment and 15.401 mV with their partner’s. With aligned EMG, the
scores were 14.903, 15.122 and 15.496 mV. The own adjustment beat the partner’s
in both comparisons while leaving the forecast alone gave the lowest mean
absolute error in each. The 12-person internal assessment showed small
average gains from own calibration with descriptive pair-resampling ranges
that included zero. The four final-test participants remain reserved.

[Fixed next-day protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/bacc8d0e79145a129673bc7947e66a5a1122e1cc/benchmarks/hyser-index/crossday/PROTOCOL.md) ·
[Next-day results](https://github.com/eliminatenoise/NeuroTranslation/blob/13d7521e81f04bfda454cc4cc05d0c4d60fb7776/benchmarks/hyser-index/crossday/README.md) · [Machine-readable aggregates](https://github.com/eliminatenoise/NeuroTranslation/blob/13d7521e81f04bfda454cc4cc05d0c4d60fb7776/benchmarks/hyser-index/crossday/RESULTS.json)

### Do the other fingers carry the forecast?

Press with more than one finger and ask what the other four sensors tell you about the index reading. In Hyser, five histories lowered mean absolute error from 14.355 to 14.161 mV for four people whose recordings we had already studied. In the 12-person training assessment, error rose from 16.854 to 16.915 mV. Each forecast looks 12 ticks ahead on the released voltage trace.

All four models keep the same index history. One adds the four other
histories from the same press. The other-trial comparison substitutes
the other fingers’ readings from the next trial, at the same elapsed
time, with matching person and day. That comparison can borrow a later
press. The compact model still uses all five sensors. For each extra
sensor it keeps the latest reading and the slope of the previous 41
readings, through the current tick. Its development MAE came within
0.028 mV of the full model’s.

The ranges from resampling people included zero for the primary MAE
comparisons in both groups. Development RMSE, which gives large misses
more weight, fell by 0.574 mV against index history and by 0.601 mV
against other-trial readings. Its resampling ranges stayed above zero
in development and crossed zero in training. Four familiar records
give a narrow view, and the four reserved participants’ records remain
unopened. The output is voltage. The 120 ms on the released clock
supplies no independent timing of what a live device could use, and the
score leaves the reason for any finger-to-finger prediction open.

[Five-sensor protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/25a35fc72621337c7281093eab9bd2520837d85a/benchmarks/hyser-index/whole-hand/PROTOCOL.md) ·
[Five-sensor results](https://github.com/eliminatenoise/NeuroTranslation/blob/0e7555b2c1a05fa6deb6aeea97befa5636caab7b/benchmarks/hyser-index/whole-hand/README.md) · [Unrounded aggregates](https://github.com/eliminatenoise/NeuroTranslation/blob/0e7555b2c1a05fa6deb6aeea97befa5636caab7b/benchmarks/hyser-index/whole-hand/RESULTS.json)

### When the cue changes

The three learned forecasts received voltage histories from prescribed
combinations and made no use of the cues. The 12 people who contributed
voluntary trials to the fit supplied 360 prescribed trials. Four people
outside that fit, whose voluntary recordings informed the question, supplied
another 120. This compares two groups from the same acquisition study.

Hyser’s prescribed finger combinations put the same forecasts to a different task. Five sensor histories lowered average absolute error against index history alone in all 16 people across the two groups. Repeating the last index reading still gave the smallest average absolute error. The five histories led on the score that gives large misses more weight.

The papers show both index-cue groups and the paired participant-resampling
ranges. The last reading's advantage on average absolute error was larger
when the instructions did not ask the index finger to press. The scores
are in millivolts at a nominal 120 ms horizon in the released recordings.

[Protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/45c1547a8b77a7f38394ff2d2a27735cfec8d75d/benchmarks/hyser-index/prescribed/PROTOCOL.md) · [Task-transfer results](https://github.com/eliminatenoise/NeuroTranslation/blob/ae2abb753941c34585ea75da36b8b980e389f94e/benchmarks/hyser-index/prescribed/README.md) ·
[Unrounded task-transfer aggregates](https://github.com/eliminatenoise/NeuroTranslation/blob/ae2abb753941c34585ea75da36b8b980e389f94e/benchmarks/hyser-index/prescribed/RESULTS.json)

The target is released index-sensor voltage 12 readings ahead on the 100 Hz
grid. The forearm signal ends at least 20 ms before issue on the nominal
grid. The source processing leaves the voltage's live availability unverified.
Hyser reports neither a scalp recording nor a calibrated force in newtons
for this comparison. The original Hyser benchmark's error in percentage
of maximum voluntary contraction answers a different question.

[Fixed Hyser protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/3e111e9f9bd0dde3ccb01317eb2a301dc57f27f7/benchmarks/hyser-index/PROTOCOL.md) · [Hyser results](https://github.com/eliminatenoise/NeuroTranslation/blob/214b5c227c587fb05f4ea11e58aabde7372bf892/benchmarks/hyser-index/RESULTS.md) · [Machine-readable aggregates](https://github.com/eliminatenoise/NeuroTranslation/blob/214b5c227c587fb05f4ea11e58aabde7372bf892/benchmarks/hyser-index/RESULTS.json)

Contains information from the [Hyser database, PhysioNet 2.0.0](https://doi.org/10.13026/hxan-pe94), by Xinyu Jiang, Chenyun Dai, Xiangyu Liu and Jiahao Fan, made available under the [ODC Attribution License 1.0](https://opendatacommons.org/licenses/by/1-0/).

## What a paced grip added

A hand can close by the same amount and squeeze harder. In WAY, the plates on a lifted object measured that squeeze in newtons. In HYGRIP, a hand squeezed a sensor to a cue. In the development group, its voltage forecast got worse with aligned scalp EEG. Aligned forearm EMG lowered mean error, with a drop for one of those three people. An offline shift that can use later samples gave lower error than aligned EMG for all three. The paired results leave the value of precise timing uncertain.

The model forecast six readings ahead on the 50 Hz clock, or 120 ms. Seven
eligible training volunteers supplied 79 right-hand trials and 16,195
overlapping forecast cutoffs. Three development volunteers supplied 39
trials and 7,995 cutoffs. Error first counts trials equally within each
person, then averages the three people's RMSEs. One whole training run failed
the fixed clock screen, and the three reserved final-test participants
remain unopened. The recording clocks leave physical synchronization and live
delivery time open. The release does not provide a usable conversion to newtons.

In the primary comparison, voltage history and cue timing gave 0.360083 mV
mean RMSE. Adding aligned scalp EEG gave 0.461331 mV, next-trial EEG
0.422755 mV and EEG ending 400 ms earlier 0.384986 mV. The aligned branch
failed the directional check. All three paired 95% intervals span zero.

In the secondary comparison, the same development volunteers gave 0.345494 mV
with aligned surface EMG, 0.342696 mV with EMG shifted within the trial
and 0.473943 mV with aligned EMG and EEG. Aligned EMG helped one person
relative to history, while the shift gave lower error for all three relative
to aligned EMG. The shift can use later samples. Both directional tests
failed. Their full comparison families and descriptive intervals appear in
the linked results and the manuscripts.

[HYGRIP primary results](https://github.com/eliminatenoise/NeuroTranslation/tree/ba1171845af2245cd041188507c7c85cc0faed02/benchmarks/hygrip-force/results-2026-11-19) ·
[HYGRIP secondary results](https://github.com/eliminatenoise/NeuroTranslation/tree/6fcd4d79894f7844ece20108cdd3bc728f193f74/benchmarks/hygrip-force/forearm-results) ·
[Original acquisition paper](https://doi.org/10.3389/fnins.2020.00919)




## What the fingers squeeze

Two force plates measured the squeeze in the WAY-EEG-GAL pinch lifts. Six
people supplied the training examples. The three other people from that study
supplied 882 trials and 25,578 overlapping forecast windows. Each estimate
looks 120 ms ahead on the stored recording clock.

The WAY project (Wearable interfaces for hAnd function recoverY, FP7-ICT-288551) supported the original WAY-EEG-GAL recordings.

| Forecast | Mean of the three participants’ RMSE values |
| --- | ---: |
| Cue, recent force and motion | 0.444181 N |
| Same inputs with correctly paired scalp EEG | 0.440183 N |
| Same inputs with the next eligible trial’s scalp EEG | 0.438801 N |

The EEG control keeps the same participant, series, object mass and surface,
and time since the light. It beats the correctly paired EEG. The planned test
of EEG information specific to that lift fails. In the 5,140 windows with
measured target force above 0.5 N, the mechanical forecast scores 0.774960 N
and the paired EEG forecast scores 0.775800 N. The higher-force comparison is
descriptive. The final test stays sealed. Device and filter delays still need
to be measured before using these forecasts to time feedback. For each
of 32 scalp channels, the model used mean differences across four
successive groups of 50 samples, each relative to the first group's mean.
Its other EEG inputs were the natural logs of three band powers, each with
an additive offset of 10⁻²⁴.

[Original experiment](https://doi.org/10.1038/sdata.2014.47) · [Stored recordings and licence notices](https://doi.org/10.6084/m9.figshare.c.988376.v2) ·
[Frozen methods, aggregates and runnable forecast](https://github.com/eliminatenoise/NeuroTranslation/tree/3af280cdb164a35e35c50cded35dcbdc199f6a19/benchmarks/way-grip-force)

## Development, repair and milk in Brain2Body

The two Brain2Body editions also follow early anatomy, skin repair and milk
across distinct marsupial species. The skeletal timing in dunnarts does not
fix the timing in Antechinus. Skin scarring and changes in wallaby milk leave
body-wide repair and precise neural or immune programming open.

[Marlow, newborn antechinus](https://doi.org/10.1071/ZO9610203) ·
[Cook et al., dunnart skeletal stages](https://doi.org/10.1038/s42003-021-02506-2) ·
[Armstrong and Ferguson, opossum skin](https://doi.org/10.1006/dbio.1995.1141) ·
[Green et al., tammar milk composition](https://doi.org/10.1071/BI9800035) ·
[Nicholas, simultaneous different milk in the tammar](https://doi.org/10.1016/0006-291x(88)90172-6)

## What remains after the motion model learns the turn?

The motion network's original error was 4.053°. A motion-only correction
lowered it to 3.957° before forearm signals entered the fit. A second
correction, with matched surface EMG, reached 3.853°. Its incremental
gain over the correction of the same design is 0.104°. The 0.200°
reduction from the original model includes the motion-only correction.
Giving the EMG correction the next trial's forearm features raised error
to 4.140°. The 960 development trials came from the same three previously
examined participants. The reserved test remains sealed.

[Correction study and table](https://github.com/eliminatenoise/NeuroTranslation/tree/51cb7a250c029af86c154b5c233c87fc69d1bc90/benchmarks/wrist-forearm-transfer) ·
[Paired and shifted forearm figure](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/51cb7a250c029af86c154b5c233c87fc69d1bc90/benchmarks/wrist-forearm-transfer/wrist-forearm-correction.png) ·
[Recorded-trial browser companion](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/)

## What changes when we switch tasks, instruments and people?

KIN-MUS UJI gave the model the task and elapsed time, with the wrist's prior
path withheld. Four development participants supplied 104 usable trials and
20,073 of 20,095 candidate angle pairs. The task-and-time fit gave 36.187°;
the matched fit adding EMG gave 34.718°. The 1.468° overall improvement
includes a 2.421° drop for bending and straightening and a 0.700° increase
for side-to-side motion.
The same fit given a shifted forearm trace had 35.385° error. Correct
alignment provided 0.667° more improvement on the matched timing comparison.

The target is a glove-derived angle, calibrated to a reference posture for
each person and filtered forwards and backwards. A label can incorporate
later measurements. The released segment can also begin after acquisition
started. The recorded 250 ms cutoff leaves physical sensor and delivery
timing open. Four people remain reserved.

A second pair used the same fit and checking rows with a new requirement
on the training inputs. A task-time term needed nonzero values from at
least seven people. Each task intercept and each EMG term also needed
support from seven people. On the same development rows its error went
from 36.165° to 34.700°, down 1.465°. The main study keeps its original
fit and scores.

[Study, methods and results](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/uji-wrist-emg/) ·
[Dataset version 1.0](https://zenodo.org/records/3469380) ·
[Scientific Data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC6848200/)

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

### One pinch, one reading

The CEMHSEY GRASP dynamometer measures one squeeze between two finger pads. The papers compare a forecast of that normalized force against the last reading, the cue, force history and muscle readings from the other repeat. Paired muscle readings lowered average absolute error by 0.05% against force history and the cue, and 0.17% against muscle readings from the other repeat. Both descriptive ranges crossed zero. The smallest average absolute error on the four-person development panel was 0.004631948 (add muscle readings from this trial). The horizon is 120 ms on the released force record.

Three people supplied 12 training trials. Four different people supplied 16 trials on different days for the
development check. The panel changes people and days together. The force and muscle samples share a nominal
first index by convention. Physical device offset, drift and live availability remain unmeasured.

[Protocol](https://github.com/eliminatenoise/NeuroTranslation/blob/a2382b0d546c451b825e9ed5f88fcc3957bff1ea/benchmarks/cemhsey-pinch/PROTOCOL.md) · [Pinch results](https://github.com/eliminatenoise/NeuroTranslation/blob/4cb63aa0a88be1d1a05d1201d7fed9b374a86ca3/benchmarks/cemhsey-pinch/README.md) ·
[Unrounded aggregates](https://github.com/eliminatenoise/NeuroTranslation/blob/4cb63aa0a88be1d1a05d1201d7fed9b374a86ca3/benchmarks/cemhsey-pinch/RESULTS.json)
