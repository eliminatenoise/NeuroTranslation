# Physics-source protocol: a test of whether simulated walking improves floor-force forecasts for new people

Simple edition of protocol version 1, 27 November 2026 · [Technical edition](PROTOCOL.md) · [Machine-readable protocol](PROTOCOL.json) · [Allocation script](allocate.py) · [Allocation output](ALLOCATION.json)

## The plan in brief

This document is a test plan. It was fixed before any test data were opened, so the way the test is judged cannot be adjusted to suit the answer. The rules are the ones in the Technical edition and in PROTOCOL.json. This edition explains the same rules in ordinary language and changes none of them.

**What is tested.** A small computer model watches the force that a walker puts on a panel in the floor and forecasts the next tenth of a second (100 ms). It forecasts two things: the panel's force added up over that time (the impulse), and whether a foot is about to land on a panel that is empty. The test asks whether this model makes smaller errors for people it has never seen when part of its training uses walking produced by physics simulations of the human skeleton and muscles, in many simulated body sizes and shapes. It is compared with the same model trained on measured walking only, given the same number of training steps and the same number of tuned settings.

**Why it is tested.** On 23 November 2026 the project owner asked for training grounded in physics, from the first training stage (pre-training) through to later stages, for trying two simulation packages, MuscleMimic and MyoGen, and for a model that generalises to any body. Measured recordings only cover the people who were recorded. A simulator can produce walking for as many bodies as needed. It is not known whether that extra simulated walking helps with real people. An earlier small project test found that it made the forecasts worse.

**Which data, and whose.** The measured walking comes from the healthy adults in an openly published collection of walking recordings by Van Criekinge and colleagues (Scientific Data, 2023). The data are released under CC0 1.0, which places no conditions on their use. Training uses 18 named people who were already used in earlier project work, plus the training people of a related plan, the walking-scale protocol. The test uses a separate group of 8 to 12 people from the same collection (the number set aside in the walking-scale draft), whose recordings have never been opened. The simulated walking is produced by the project in the MuJoCo physics engine with the MyoSuite and MuscleMimic body models, on a planned table of 1,024 simulated bodies.

**What is measured and what is simulated.** The plate forces, marker positions and muscle signals in the Van Criekinge recordings are measured. Every walk produced by a simulator is a computed movement of a model, not a measurement of a person. Measured walks that have been stretched or scaled to a new body size are labelled derived. Every file, model input and report keeps these three kinds apart.

**What counts as success.** The simulation-trained model "helped" only if all three of these hold: its impulse error for the test people is lower than the measured-only model's, with the whole 95% uncertainty range below zero; its landing forecasts are not worse by more than a small fixed margin; and it beats two simple reference forecasts. A further test then checks whether the gain needs physics at all, or whether simply scaling measured walks to new sizes would give the same gain. The outcomes "hurt" and "inconclusive" are defined just as exactly.

**What is published whatever the result.** This protocol and its binding file; the openly licensed code; the realism thresholds and the feasibility report, even if no simulator turns out to be realistic enough; the scores of every planned comparison, wins and losses alike, including those that must stay private; per-person results; the openly licensed trained models; a NOTICE that credits every source; and a Technical and a Simple edition of the report.

**The main limits.** A positive result would hold for healthy adults from one collection, walking across one laboratory floor, forecast 100 ms ahead on four plates. It would not show that the model works for every body, for people with walking difficulties, or for other movements. With about 12 test people, only improvements of roughly 5% to 7% or more are likely to be detected (section 11.4).

**Where things stand.** When this plan was written, no test data had been opened and no reserved recording had been downloaded. The walking-scale protocol, which names the test people, had not yet been committed to the repository. The test cannot run until it is.

## How to use this edition

The sections below follow the order in which a reader needs the material. The table shows where each part is treated in the Technical edition. Where this edition and the Technical edition seem to differ, the Technical edition and PROTOCOL.json are the fixed rules.

| This edition | Technical edition |
| --- | --- |
| 1. The forecast and the words used for it | sections 2 (terms) and 6 |
| 2. Why simulated walking needs a careful test | sections 1 and 3 |
| 3. What a result can and cannot show | section 2 |
| 4. The people and recordings | section 5 |
| 5. The link to the walking-scale protocol | section 4 |
| 6. The forecasting task in detail | section 6 |
| 7. How the simulated walking is made | section 7 |
| 8. Measured, derived and simulated values | sections 2 and 7.5 |
| 9. The model and how it is trained | section 8 |
| 10. The comparisons | section 9 |
| 11. How errors and uncertainty are measured | section 10 |
| 12. The success rule | section 11 |
| 13. How the test is sealed | section 13 |
| 14. Rights, licences and publication | section 14 |
| 15. Steps, times and computer use | section 12 |
| 16. What comes later | section 15 |
| 17. Changes from the reviewed design | section 16 |
| Appendix: plate corners and file fingerprints | sections 3, 5.1, 7.1 and 9 |

The Technical edition states that the Simple edition would be written with the results. This Simple edition of the protocol is written now, before the test, as part of step S1 of the plan (section 15). A Technical and a Simple edition of the final report follow the results in step S6.

## 1. The forecast and the words used for it

### 1.1 What the laboratory records

The Van Criekinge laboratory has four force plates set into the floor. A force plate is a stiff panel with sensors underneath that measure how hard anything on it pushes. As a person walks across the room, each foot lands on one or more of the plates. The plates are sampled 1,000 times a second. Cameras track small reflective markers stuck on the skin 100 times a second. Sensors on the skin record the electrical activity of muscles (surface EMG) 1,000 times a second. So there are ten force samples for every camera frame.

### 1.2 What the forecasting model does

At regular moments during each walk, the model makes a forecast for each plate:

1. It looks back over the last 200 ms of that plate's upward force, summarised as ten averages of 20 ms each, and at the plate's state at that moment, such as whether it is empty.
2. It forecasts two things for the next 100 ms: the impulse, and the chance that a new load starts.
3. After the test, the forecasts are compared with what the plate actually measured.

The model never sees anything recorded after the moment of the forecast.

### 1.3 Words used throughout

- **Issue time.** The moment a forecast is made, counted on the 1,000-per-second clock of the recording. Only samples up to and including that moment may be used.
- **Plate row.** One forecast for one plate at one issue time. Four plates give four rows per issue time.
- **Traversal.** One pass of a walker across the four plates. Each measured walk file holds one traversal.
- **Impulse.** Force added up over time. Here it is the upward force on a plate over the next 100 ms, added up sample by sample and multiplied by the sample interval of 0.001 s. The unit is the newton-second (N·s). Example: a plate that carries a steady 700 N for the whole 100 ms has an impulse of 700 × 0.1 = 70 N·s. A plate that is empty throughout has an impulse of 0 N·s.
- **New load.** A foot landing on a plate that was empty. The exact definition, with its force thresholds, is in section 6.
- **Persistence.** The simplest forecast: assume the latest force stays as it is. Its impulse is the latest 20 ms average × 0.1 s. Example: if the latest average is 600 N, persistence forecasts 60 N·s.
- **MAE (mean absolute error).** The average size of the miss, ignoring whether the forecast was too high or too low. Example: misses of +3 and −5 N·s give an MAE of 4 N·s.
- **Brier score.** The average of the squared difference between a forecast probability and what happened, written as 1 if the event happened and 0 if it did not. Lower is better. Example: a forecast of 0.2 for a landing that does not happen scores 0.2² = 0.04; if the landing does happen, it scores 0.8² = 0.64.
- **Body weight (BW).** Body mass × 9.81 m/s². Dividing a force by body weight lets people of different sizes be compared. Example: a 70 kg person has a body weight of about 687 N, so a force of 1.2 BW is about 824 N.
- **Mixture share.** The fraction of each training batch taken from simulated rows (or from scaled measured rows). A share of 0.25 with a batch of 256 rows means 64 simulated and 192 measured rows.
- **Pre-training and fine-tuning.** Pre-training means training updates on simulated rows only. Fine-tuning means the training on measured rows that follows.
- **Inner folds.** The training people are split into four groups. A setting is trained on three groups and scored on the fourth, and this is repeated so that each group is scored once. Every choice of model setting is made this way, inside the training people, so the test people play no part in any choice.
- **Realism gate.** A fixed set of checks that a simulated walk must pass before it may be used in training.
- **Licence closure.** The set of licences of every source that went into a file or a trained model. A model is only as open as the most restrictive licence in its closure.
- **sha256 fingerprint.** A standard calculation that turns any file or text into a fixed 64-character code. The same input always gives the same code, and any change gives a different one. The plan uses fingerprints to name exact files and to run fair, checkable lotteries.

## 2. Why simulated walking needs a careful test

### 2.1 The request

The owner's request of 23 November 2026 covered physics-grounded training from pre-training to post-training, trying MuscleMimic and MyoGen, aiming at a model that generalises to any body, and, later, reinforcement learning on verifiable rewards inside the physics engine. Reinforcement learning means improving a controller by trial and reward; verifiable rewards are rewards that can be checked by calculation, such as not falling. This protocol covers the first part: whether simulated walking helps as pre-training or as part of the training mixture. Reinforcement learning is left to a later, separate protocol (section 16).

The facts in sections 2.2 and 2.3 were gathered before this plan was written. Those checks used simulation with invented inputs and summary information from training files that had already been used. They opened no reserved data.

### 2.2 What the earlier project test found

Before this plan, an unpublished project test tried simulation with a small forecasting model. It replaced half (50%) of the model's training windows with five simulated walks of one simulated body. The walks came from a published learned walking controller for the MyoLeg leg model (the myoLegWalk-v0 baseline checkpoint for MyoSuite 3.0.0), not from a reflex controller. The model was scored on six treadmill walkers from another public collection, who had already been used during development.

Training on measured walking only did better on all three measures:

| Measure | Measured only | Half simulated |
| --- | ---: | ---: |
| Heel position error | 42.31 mm | 52.56 mm |
| Impulse error | 7.89 N·s | 9.73 N·s |
| New-load Brier score | 0.0492 | 0.0613 |

No simulated version of the Van Criekinge laboratory existed then, so these numbers are not a starting point for this task. They are a warning.

The same test showed why the simulated walking did not help. The simulated forces did not look like measured forces:

- The median of the largest 20 ms force value was 1,717 N in simulation and 763 N in the measurements.
- Both simulated feet were off the ground in 2.9% of samples. In the measurements this happened in 0.004% of samples.
- In each fold, only 0 or 1 simulated input windows lay inside the central range of the measured windows on all input features at once. In other words, almost none of the simulated inputs resembled real ones.

### 2.3 What was checked on 27 November

The same learned controller was run again, sampled 100 times a second:

- Its peak foot forces were 2.4 to 5.0 body weights. Among the two Van Criekinge training people with a recorded mass, the largest peak on a loaded plate was 1.154 body weights. The simulated peaks were therefore about two to four times the largest measured one.
- It fell when body mass was multiplied by 0.8, 1.2 or 1.25, and when muscle strength was multiplied by 0.7, 0.75, 0.85 or 1.3. It walked for 10 s when mass was multiplied by 0.9 or 1.1. So it cannot walk across the range of body sizes the test needs.
- Its published notes report no successful walks under MyoSuite version 3.1, so it is run only under version 3.0.0.

The reflex controller supplied with MyoSuite was also tried. A reflex controller produces walking from simple rules that link body sensations to muscle commands, much as spinal reflexes do; this one is the Song-Geyer controller, with 46 adjustable settings (gains) and a new command every 10 ms. With its shipped gains it fell after 0.37 s. A search of 181 trial runs, an evolution strategy that keeps the best gain sets and tries small changes to them, raised the time before falling to 2.54 s. Stable walking in three dimensions was not reached.

Speeds were measured on one processor thread. The MyoLeg model ran 26.4 times faster than real time on its own and 19.7 times inside its simulation environment. The reflex controller ran 12 times faster than real time. The 416-muscle MuscleMimic full-body model ran 3.06 times faster than real time when passive (with no muscle commands). A 10 s walk with the learned controller took 0.56 s of computer time. One training update of a small forecaster with a batch of 256 rows took 11.3 ms at width 64 and 21.0 ms at width 128.

### 2.4 What follows from these findings

Simulated walking is cheap to produce, but the walking available on 27 November was not realistic. So the test is built in two stages. First, a simulator must pass a realism gate that is built only from training people and published walking ranges (section 7.7). Only if a simulator passes is the reserved test group opened. If none passes, the test group stays closed and that negative result is published.

## 3. What a result can and cannot show

- **One group, one laboratory, one task.** A positive result covers healthy adults from one public collection (Van Criekinge and colleagues, 2023), walking over the ground in one laboratory, forecast 100 ms ahead on four force plates. It does not show generalisation to every body, to the walking of people with medical conditions, or to other tasks.
- **Simulation is not measurement.** Simulated, measured and derived values stay labelled apart in every file, model input and report. A simulated walk is a computed movement of a model, not a measurement of a person.
- **EMG is not a nerve recording.** Surface EMG is the electrical activity of muscles picked up by sensors on the skin. It is not a recording of nerve signals.
- **Counts are kept separate.** People, walks, traversals, issue times, plate rows and new-load events are counted separately. Simulated bodies, simulated walks and simulated traversals are counted separately from measured ones. A large number of rows does not mean a large number of people.
- **Small test group.** With 8 to 12 test people, small effects are unlikely to be detected (section 11.4), and with fewer than 10 scoreable people every result is only descriptive (section 12.6).

## 4. The people and recordings

### 4.1 The collection

- **Source.** The healthy group of the Van Criekinge collection, published on figshare with the identifier 10.6084/m9.figshare.24192480.v1. The data are CC0 1.0. The accompanying article is Van Criekinge T. et al., Scientific Data 10, 852 (2023), identifier 10.1038/s41597-023-02767-y, published under CC BY 4.0.
- **Archive.** The recordings sit in one archive file, 138_HealthyPiG.zip (figshare file 42450060, 463,159,769 bytes, 1,016 entries). Its md5 checksum and the fingerprint of its table of contents are in the appendix.
- **Clocks.** Markers are recorded 100 times a second. The analog channels, which are the plate forces and the EMG, are recorded 1,000 times a second, ten analog samples per marker frame.
- **Plates.** There are four plates of one type. Their corners are the same in all 12 fit files (the walks of the earlier fit role, section 4.2). Plates 1, 2 and 4 lie in a row along one floor axis; plate 3 lies beside plates 1 and 2 along the other axis, centred on the line where they meet. Their exact corners in millimetres are in the appendix.
- **Force direction.** Plate force signs differ between files: in some files upward force is positive, in others negative. The walking-scale adapter (section 5) converts them all to upward-positive vertical force.
- **Smoothed markers.** The published marker paths have had gaps filled and have been smoothed. Smoothing mixes each value with its neighbours, including later ones, so a marker value can carry information from slightly later moments. The markers are therefore not causal at the 10 ms scale, which is why marker inputs are only used with a delay (section 6.3).

### 4.2 The training people

Every comparison trains on the same measured people:

- the 12 people of the earlier fit role: SUBJ112, 110, 096, 024, 082, 062, 061, 040, 044, 043, 039 and 038, with 36 walks;
- the 6 people of the earlier "validation" role: SUBJ047, 011, 115, 075, 066 and 116, with 18 walks. Earlier fits used them for checking, so they have already been seen. Here they are training people only and are never described as new;
- the training people of the walking-scale protocol, from all of its training stages ("rungs"). Their walks are reused read-only from that track's stored copies, identified by fingerprint, with no second download.

On 27 November, the 54 local walk files of the first 18 people were checked against their recorded fingerprints. All 54 matched. The fingerprints are listed in PROTOCOL.json.

### 4.3 People who are never used

These people are not used in any comparison or step:

- the 12-person Van Criekinge test group of the earlier project roster: SUBJ016, 084, 092, 008, 053, 014, 077, 074, 057, 056, 020 and 089;
- the walking-scale evaluation group, and every walking-scale group other than its training people and the physics-source group;
- SUBJ099, whom the walking-scale protocol leaves untouched;
- the 50-person stroke group of the Van Criekinge collection, which has never been accessed (section 14.4 explains a pending decision about it);
- every other reserved group of the project.

### 4.4 The test group and when it is opened

The test group is the group that the walking-scale protocol sets aside for physics-source. It is copied into the binding file, BINDING.json (section 5). The walking-scale draft sets aside 8 to 12 people for this group, depending on how many people in the pool qualify.

The test people's walks and standing trials are downloaded only when all of these are true:

1. this protocol and BINDING.json are committed to the repository;
2. a separate reviewer has admitted the protocol;
3. every final model has been trained and sealed in a file called FIT-COMPLETE.json.

The downloads are ranged reads: only the byte ranges that hold the needed files are fetched from the large archive. Each download records the web address, the byte range, the number of bytes and the fingerprint of what arrived.

### 4.5 Body measurements

The model may be given three body measurements, called the body vector: mass (kg), height (mm) and leg length (mm). Each comes with a flag that says whether the value is missing.

The measurements are taken from each person's standing trial, a short recording of the person standing still (archive trial code 0), in this order:

1. the stored processing parameters Bodymass, Height and LLegLength or RLegLength in that file;
2. if these are absent, leg length from the standing-trial markers (from the front of the hip bone, the anterior superior iliac spine, to the knee marker to the ankle marker, with both sides averaged), and height as the highest head marker plus 50 mm; mass then stays missing;
3. otherwise, the value is missing.

The same standing trial gives body weight for the realism checks. Body weight is Bodymass × 9.81 m/s², or, if Bodymass is absent, the average total vertical plate force over at least 2 s of quiet standing on the plates in that trial. A person with neither is left out of the realism features that are divided by body weight, but remains a training person.

When the standing trials are read:

- Step S0 downloads the 18 standing trials of the people in section 4.2 (18 archive members, 5,881,322 compressed bytes; their checksums and sizes are in PROTOCOL.json).
- The standing trials of walking-scale training people are downloaded in step S2 if that track has not stored them already.
- The standing trials of test people are read only after the conditions of section 4.4, and they are used as an input that is available at forecast time. A person's height and mass are known before they walk, so using them does not reveal the future.

It is not yet known whether these files contain Bodymass, Height and leg length. Only 2 of the 12 walk files of the earlier fit role contain them.

### 4.6 The inner folds and the training subsets

Both are made by fixed lotteries in allocate.py, from subject codes alone, without reading any data.

**Inner folds.** Each training person's subject code is added to the text `physics-source-inner-v1|` and fingerprinted with sha256. The people are ranked by fingerprint, from smallest to largest. The fold is the rank modulo 4, which means the remainder after dividing the rank by 4: ranks 0, 4, 8 and so on go to fold 0, ranks 1, 5, 9 to fold 1, and so on. For the 18 people known now, the folds are:

| Fold | People |
| --- | --- |
| 0 | SUBJ040, 061, 011, 039, 066 |
| 1 | SUBJ116, 044, 038, 024, 062 |
| 2 | SUBJ112, 082, 047, 110 |
| 3 | SUBJ096, 115, 043, 075 |

At binding, the walking-scale training people are ranked together with these 18 by the same rule, unless the walking-scale protocol's own folds are chosen (section 5, item 5). Once the pool grows, some of the 18 may therefore move to another fold. The final folds are recorded in BINDING.json.

**Data-efficiency subsets.** To see how results change with the number of measured people, the plan also trains on smaller groups. For 3, 6 and 12 people there are five different subsets each (numbered 0 to 4). Subset s is made by ranking the 18 people by the fingerprint of `physics-source-subset-v1|` + s + `|` + subject code and taking the first 3, 6 or 12. The group of all 18 is one more point, and the full pool of training people is the last point. The lists are in ALLOCATION.json.

## 5. The link to the walking-scale protocol and the binding file

The test group and several shared parts come from a related plan, the walking-scale protocol, kept in the folder `models/walking-force-scale/` on the branch `walking-scale-protocol`. That plan makes the single allocation of the Van Criekinge healthy people who were never assigned to any role before. Physics-source does not make a second allocation of those people, so that no person can end up in two roles. When this version was written, the walking-scale protocol was not yet committed.

Before any reserved byte is opened, the lead commits a file called BINDING.json in this folder. It may contain only the seven items below, each with the fingerprint of the file it comes from:

1. The walking-scale commit, the fingerprint of its PROTOCOL.json, and the fingerprint of its allocation output.
2. The subject codes of the group that the walking-scale allocation sets aside for physics-source, copied exactly as listed there, with the archive files that allocation names (archive member, CRC-32 checksum, byte counts). This is the test group.
3. The subject codes of the walking-scale training people (all training rungs), and the fingerprint of each stored walk file reused from that track.
4. The walking-scale input adapter file and its fingerprint, with any differences from the task described in section 6; the code of the forecaster family and its fingerprint; whether walking-scale admits marker inputs, and under which causality guard; and its rule for qualifying EMG channels, if it has one.
5. The source of the inner folds. The walking-scale folds are used only if its committed protocol places every physics-source training person (section 4.2) in exactly one of exactly four folds. Otherwise the rule of section 4.6 is used. Nothing else decides this.
6. The outputs of step S0, by fingerprint: GATE-THRESHOLDS.json, FEASIBILITY.json, the register of which bodies passed, and the list of generators that passed.
7. Lists computed by rules fixed in this plan: the inner folds of the full training pool, the narrow training pool used in the body-shift analysis (section 10.6), and the reference walks assigned to generator G4 (section 7.5).

Any change to anything else needs a protocol version 2, admission by a separate reviewer, and a commit, all before any reserved byte is opened. Every version stays in the repository.

If the walking-scale protocol is never committed, or sets aside no group for physics-source, the test step S5 does not run. The results of steps S0 to S4 are then reported as development results on training people only.

## 6. The forecasting task in detail

### 6.1 Shared definitions

The task is the main task of the walking-scale protocol. It is computed by that protocol's adapter code, imported by fingerprint so that the exact same code is used. Physics-source sends measured walks and simulated walks through the same code. As drafted by walking-scale and by the earlier Van Criekinge protocol, the definitions are:

- **Issue times.** Forecasts are made on the 1,000-per-second clock at sample t = 199 + 20k of each walk, for k = 0, 1, 2 and so on. The first forecast therefore has 200 ms of history behind it, and the next ones follow every 20 ms. Each pair of an issue time and a plate (plates 1 to 4) is one row.
- **Inputs.** Ten back-to-back 20 ms averages of the target plate's upward vertical force, ending at sample t, in newtons; and the state of the plate at t (such as whether it is known to be unloaded), worked out from samples up to t only. Marker inputs are used only if walking-scale admits them, under its causality guard.
- **New-load label.** A plate counts as unloaded after 20 samples in a row between −10 and +10 N. A new load starts when the force then rises past +20 N and stays at or above +20 N for the next 19 samples, so for 20 ms in all. A row is positive if such a start falls between sample t+1 and sample t+100. It is negative if the plate state is known at t, the recording continues without gaps through sample t+119, and no start qualifies. The extra 19 samples after t+100 are needed to confirm a start at the very end of the window. Rows that are neither are left out of the new-load score.
- **Impulse target.** The sum of upward vertical force over samples t+1 to t+100, multiplied by 0.001 s, in N·s.
- **Eligibility.** Whether a row is used depends only on its inputs and on whether its targets can be computed. The same rule applies to every comparison, so no comparison is scored on easier rows.

If the committed walking-scale adapter differs from these definitions, the committed adapter governs, and the differences are listed in BINDING.json.

### 6.2 What physics-source adds

Physics-source adds only three things to the walking-scale inputs:

1. a source tag that says whether a row is measured, derived or simulated, and by which kind of simulator (section 8);
2. an optional body vector (section 4.5);
3. if walking-scale admits marker inputs, the heel and toe positions measured from the centre of the target plate, under the walking-scale causality guard.

### 6.3 Variant K, used only if walking-scale admits no markers

If walking-scale admits no marker inputs, a second, predeclared version of the task called variant K adds heel and toe markers. The markers are LHEE, RHEE, LTOE and RTOE (left and right heel and toe, in mm). They are expressed in a frame centred on the target plate, with the walking direction taken from how the sacrum marker (at the base of the spine) has moved in the past. Variant K uses ten marker frames 20 ms apart, ending at the last marker frame at or before t − 100 ms.

The 100 ms delay keeps the smoothing of the published markers from carrying information about the forecast window into the inputs. Step S0 measures how strong the smoothing is (its cutoff frequency) from the marker data of training people, and reports whether 100 ms is enough. Variant K is applied in the same way in every comparison that runs it.

## 7. How the simulated walking is made

### 7.1 The software

A musculoskeletal simulation is a computer model of bones, joints and muscles that moves under the laws of physics. The muscles pull on the bones, the feet press on a simulated floor, and the physics engine works out the resulting motion and forces. The physics engine used here is MuJoCo. MyoSuite and its model files (myo_sim) provide the leg models; musclemimic-models provides a full-body model.

The track builds its own software environments in its private folder, each pinned to fixed versions:

| Environment | Contents | Used for |
| --- | --- | --- |
| A | MuJoCo 3.17.0, MyoSuite 3.0.0, myo_sim 0.2.3 | the published learned walking controller (the unscreened control, and the optional G2) |
| B | MuJoCo 3.17.0, MyoSuite 3.1.0, myo_sim 0.2.5 | G1 reflex walking, G4 tracking, the virtual laboratory, the body-scaling engine |
| C | MuJoCo 4.0.1, musclemimic-models 1.0.6 | G3c and G3f |
| D | MyoGen 0.11.0, NEURON 8.2.7, in its own environment and process | private MyoGen EMG only |
| T | PyTorch (on the CPU, 32-bit numbers), scikit-learn, NumPy | training the forecasters, issuing forecasts and scoring |

The MyoLeg muscle file and joint file are byte-for-byte identical in myo_sim 0.2.3 and 0.2.5, so the leg's muscles and joints are the same in environments A and B. Their fingerprints, and that of the MuscleMimic full-body file, are in the appendix. Step S0 records the fingerprint of every compiled model.

### 7.2 A virtual copy of the laboratory

So that simulated walks produce the same kind of data as the real ones, the plan builds a virtual Van Criekinge laboratory:

- **Plates.** The simulated floor has plates with the same corners as the real ones (appendix). Along the simulated path, the four-plate layout repeats about every 3.5 m. Each copy is moved by a random amount of up to ±0.4 m along the path and ±0.1 m across it, so the feet land in different places on each copy.
- **Plate force.** The vertical force on each plate is the sum of the pushing (normal) forces of the foot-floor contacts whose contact point lies inside that plate, recorded 1,000 times a second. The simulation step is 1 ms, the same as the laboratory clock. A foot that stands across two plates shares its load between them.
- **Plate noise.** Each simulated plate gets noise and a small offset, drawn from the noise and offsets measured on unloaded stretches of training-people walks in step S0.
- **Traversals.** Each simulated walk lasts 12 s. The first 2 s are thrown away so that the walk has settled. Each crossing of a plate layout gives one traversal: a cut of 2.1 to 4.2 s, centred on the layout, like the measured walks. Each traversal goes to the walking-scale adapter as one walk.
- **Checks on every recorded walk.** (1) Vertical impulse closure within 0.5%: over the walk, the total floor force must balance body weight and the change in vertical momentum, counting any help from the tracker; this follows from Newton's second law, so a failure points to an error in the simulation. (2) No floor contact by any body part except the feet. (3) No outside force other than the logged tracking help. (4) A future-replacement test: replacing every sample after t with something else must leave every input issued at t unchanged, which shows that no future information leaks into the inputs.
- **Simulated markers.** Heel and toe markers are placed where the standard Plug-in Gait marker set puts them, on the scaled heel bone (calcaneus) and toe segments. They are sampled 100 times a second, given 1 to 2 mm of noise to imitate skin movement, and smoothed with the filter cutoff measured in step S0, so that they match the processing of the published markers.

### 7.3 The body-scaling engine

Different bodies are built with MuJoCo's model-editing interface, MjSpec, which changes a model's description before it is compiled into a runnable simulation. For each body it changes:

- segment lengths, including where the body parts join, the shapes and mesh sizes, the points where muscles attach, and the contact shapes of the feet;
- masses and inertias (how mass is spread inside each segment);
- muscle peak isometric forces, which set how strong each muscle is.

The working length ranges of the muscles are recomputed when the model is compiled. Two checks guard the engine: the leg lengths and summed masses of each built body must match the body table, and building a body with every factor equal to 1 must reproduce exactly the same compiled model as the unmodified original, shown by an identical fingerprint.

### 7.4 The table of 1,024 bodies

The body table in ALLOCATION.json holds 1,024 simulated bodies. They are drawn from a scrambled Sobol sequence with seed 20261127 over ten body factors. A Sobol sequence is a fixed list of points that fills a range of many dimensions more evenly than random draws would. Scrambling shuffles it in a repeatable way while keeping that even coverage. The scrambling (a linear matrix scramble and a digital shift, with random bits taken from sha256) is written in allocate.py, so anyone can recompute the table with standard Python and nothing else.

The ranges come from general adult body measurements and from the published description of the collection (ages 21 to 86). They never come from reserved people.

| Factor | Range |
| --- | --- |
| Height (stature) | 1.50 to 1.95 m; each segment is scaled by height / 1.70 m |
| Body mass index (BMI) | 18 to 34; mass = BMI × height², limited to 45 to 115 kg (43 of the 1,024 bodies hit a limit) |
| Thigh-to-shank length ratio | ±6%, with total leg length unchanged |
| Foot length | ±8% |
| Pelvis width | ±8% |
| Muscle strength | 0.6 to 1.3 × (mass / 75 kg)^(2/3), multiplying every muscle's peak isometric force |
| Muscle maximum shortening speed | 8 to 12 optimal fibre lengths per second |
| Foot-floor contact time constant (how soft the contact is) | 0.02 to 0.04 s |
| Foot-floor friction | 0.6 to 1.2 |
| Speed factor | 0.8 to 1.25 |

Example from the table: the first body, B0000, is 1.684 m tall and weighs 55.3 kg, with a speed factor of 1.136. Its strength factor is 0.55, below the base range of 0.6 to 1.3 because its mass is below 75 kg. Its three G1 target speeds are 1.27, 1.41 and 1.56 m/s. This is one entry, given only as an example; the full table is in ALLOCATION.json.

Each generator uses the start of the table:

- G4: bodies B0000 to B0599, 3 walks each;
- G1: bodies B0000 to B0127, 3 target speeds each;
- G3c: bodies B0000 to B0031;
- G3f: bodies B0000 to B0015.

The first 1, 8, 32 and 128 entries of a scrambled Sobol sequence are each spread evenly over the ranges, which the diversity analysis uses (section 10.6). Bodies, walks, traversals, issue times and events are counted separately, and every body that fails stays in a failure register.

### 7.5 The generators

A generator is a way of producing simulated walks. Each one has a time box in step S0 (a fixed amount of working time it may use) and a place in a fixed order of preference. Source tags keep the kinds of data apart: measured; derived, augmented (section 10.2); simulated, reference-tracking (G4, G3c and G3f); simulated, generated (G1, G1-cal, G2 and the unscreened control); and simulated, reduced-order (SLIP).

**G4 (preferred): muscle-driven tracking of training people's walks.** G4 takes a real walk of a training person and has a simulated body reproduce it with its own muscles:

1. Inverse kinematics: the Van Criekinge markers of a training person's walk are turned into joint angles on that person's scaled model.
2. Retargeting: the motion is moved to the simulated body. It is stretched in time to the body's target speed, and the pelvis path is scaled by leg length.
3. Tracking: the simulated body follows the motion in MuJoCo. Every 10 ms, proportional-derivative joint targets (a standard way of pulling each joint towards its reference angle) give the joint torques needed to follow the reference. Static optimisation then chooses the 80 MyoLeg muscle excitations (muscle commands) that produce those torques with the least summed squared activation, which spreads the work across the muscles.
4. A helping force and twisting force at the pelvis (a root residual) is allowed, up to 10% of body weight, and logged. The realism gate then limits it further (section 7.7).
5. Ground forces come from the simulated foot contacts, not from the recording.

The target speed is the speed factor × the reference walk's speed × √(height / reference person's height), limited to 0.95 to 1.70 m/s. Reference walks come from training people only. Walk w (0, 1 or 2) of body B uses the training walk with the smallest fingerprint of `physics-source-g4-ref-v1|` + body id + `|` + w + `|` + subject code + `|` + author trial index; for example, `physics-source-g4-ref-v1|B0000|0|SUBJ112|1`. In each inner fold, simulated walks whose reference person is in the held-out group are left out, so a fold is never scored on people whose walks its simulated data copied. Test people feed no generator. G4 output is measured motion moved onto new bodies in a physically consistent way. It is not independently generated motion. Time box: 2 days.

**G1: the reflex controller tuned with CMA-ES.** CMA-ES (covariance matrix adaptation evolution strategy) is a standard search method: it tries a population of gain sets, keeps the best, and learns which directions of change help. Population 24; at most 6,000 trial runs for the nominal (standard) body and at most 1,200 for every other body, which starts from the gains of the nearest body already solved. The goal rewards staying up for up to 12 s and subtracts the error from the target speed and the effort (activation cubed, added up over time). The goal contains no measured data. The target speeds are speed factor × (0.9, 1.0 and 1.1) × 1.25 m/s × √(height / 1.70 m), limited to 0.95 to 1.70 m/s; they are listed for each body in ALLOCATION.json. Time box: 1.5 days, run in parallel with G4. G1 is the source of generated motion, made without copying any measured walk.

**G1-cal: a calibrated reflex variant.** Run only if neither G4 nor G1 passes the realism gate. The gate's literature and range targets for peak force, stance time and double support (section 7.7) are added to the G1 goal as penalties. Because it is tuned towards measured ranges, it is labelled calibrated. Time box: 1 day.

**G3c: MuscleMimic legs and trunk.** The arms are removed from the MuscleMimic full-body model, and rigid arm masses are attached at the shoulders instead. The masses follow de Leva's standard segment fractions: upper arm 2.71%, forearm 1.62% and hand 0.61% of body mass on each side. G3c is driven by the G4 tracker, not by reflex gains copied from MyoLeg, because MuscleMimic changed the muscle paths and attachment points. Run only if G4 passes. Time box: 0.5 day.

**G3f: the full MuscleMimic body.** The complete myofullbody model, including its arm and hand part, which carries a non-commercial licence, driven by the G4 tracker. Its data and models stay private, and only scores are published.

**G2 (optional): reinforcement learning with randomised physics, starting from the published learned controller.** Domain randomisation means training while the body and contact settings vary, so the controller copes with many of them. The published controller's checkpoint has no stated licence, so G2 data and comparisons stay private with scores only, and G2 cannot satisfy the go/no-go rule. Run only if time remains.

**SLIP (optional): reduced-order spring-mass walking.** SLIP (spring-loaded inverted pendulum) treats the body as a point mass on springy legs. It serves as a control for whether musculoskeletal detail matters at all. Tagged simulated, reduced-order.

### 7.6 Simulated EMG

The recordings include surface EMG, so the plan also simulates EMG for the secondary comparisons (section 10.5).

**Which muscles.** The MyoLeg muscle excitations are mapped to the recorded EMG channels on each side: BF (biceps femoris, the sum of its long head bflh and short head bfsh), GAS (gastrocnemius, the sum of its lateral and medial heads), RF (rectus femoris), ST (semitendinosus), TA (tibialis anterior) and VL (vastus lateralis). The back-muscle channel ERS comes from the trunk muscles in G3c and G3f, which have a trunk, and is masked (marked absent) elsewhere.

**CR-EMG: a clean-room generator that can be published.** It is written from published equations by a person who has not read the MyoGen source code and who records that fact, so that the generator carries none of MyoGen's licence terms. Its parts:

- Fuglevand recruitment, a standard model of how motor units switch on as effort rises, with a recruitment range of 30 to 60;
- rate coding: each motor unit fires 8 to 35 times a second, faster with more effort;
- variable firing intervals, with a coefficient of variation (spread divided by average) of 0.15 to 0.25;
- Hermite-Rodriguez motor-unit action potentials, a standard mathematical shape for the electrical signal of one motor unit;
- weakening of the signal by the fat under the skin, 2 to 15 mm thick depending on body mass index;
- conduction velocity (the speed of the signal along the muscle fibres) of 3.5 to 5 m/s;
- two electrodes 20 mm apart (a bipolar recording).

The signal is simulated 10,000 times a second, filtered to keep 20 to 450 Hz, reduced to 1,000 samples a second, given a signal-to-noise ratio of 10 to 30 dB, and multiplied by a random log-normal gain for each body and channel. Finally, each channel's amplitude is mapped so that its spread of RMS (root-mean-square) values matches that of the training people. Because of this last step, which uses measured data, CR-EMG is labelled calibrated.

**MyoGen EMG (private).** The same muscle excitations also drive MyoGen 0.11.0 surface EMG, in environment D, in a separate process and outside the public folder. MyoGen is licensed AGPL-3.0-or-later, so its output and every model trained on it stay private, with scores only.

**Timing.** In the simulation, EMG comes before force, because MuJoCo's muscles take time to activate after they are excited, as real muscles do.

### 7.7 The realism gate

The realism gate decides whether a simulator is good enough to be used. It is frozen in GATE-THRESHOLDS.json during step S0, before any simulated corpus is generated. Thresholds that come from data use only the 18 training people of section 4.2 (with body weight from their standing trials), widened by 10%. The fixed thresholds come from the range of the training people and from the published walking literature.

**Checks on each walk**, over its steady part:

| Check | Threshold |
| --- | --- |
| No fall | the pelvis stays above 0.6 × its standing height, and nothing but the feet touches the floor, for at least 8 s |
| Speed | average forward speed 0.90 to 1.75 m/s |
| Cadence (steps per minute) | 90 to 140 |
| Peak vertical force per foot contact, divided by body weight | median 1.00 to 1.30; 99th percentile at most 1.50 |
| Stance time (how long each foot stays down) | the median, and at least 90% of stances, between 0.9 × the 1st percentile and 1.1 × the 99th percentile of training-people plate stance times |
| Double support (both feet down) | median 15% to 30% of the stride |
| Flight (both feet off the ground) | both feet below 20 N in fewer than 0.5% of samples |
| Momentum closure | within 0.5% |
| Tracking help (G4, G3c and G3f only) | RMS of the pelvis helping force at most 5% of body weight |

Several of these checks target the failures found earlier (section 2): feet striking at 2.4 to 5.0 body weights would fail the peak-force check, and the earlier 2.9% of samples with both feet off the ground would fail the flight check.

A body passes if at least 2 of its walks pass. Only walks that pass enter the corpus.

**Checks on each generator as a whole:**

- Among simulated rows whose last 200 ms average at least 20 N (rows where the plate is carrying load), at least 50% must lie inside the central 90% (5th to 95th percentile) of training-people values on all of these features at once: average 200 ms force / body weight, largest 20 ms value / body weight, 100 ms impulse / body weight, and, if markers are admitted, heel movement over 180 ms. This check is aimed at the earlier problem, where almost no simulated inputs looked like real ones.
- The number of new-load starts per plate per traversal must lie within the training people's minimum and maximum.
- Reported but not used to decide: how well a classifier can tell simulated rows from measured ones on these features (the area under its curve, where 0.5 means it cannot tell them apart), and distances between the simulated and measured distributions of each feature.

**Go/no-go.** The test goes ahead only if at least one clean generator (G4, G1 or G1-cal) produces at least 128 different passing bodies, meets the generator-level checks, and its passing bodies cover at least 80% of the range of every body factor in section 7.4. G3c and G3f are judged by the same walk and generator checks, with at least 75% of their bodies passing. If no clean generator passes, G1-cal is tried once. If it also fails, the work stops, the test group stays sealed, and the negative feasibility result is published.

### 7.8 A record for every simulated walk

Every simulated walk records: its generator; its environment and package versions; the fingerprint of the compiled model; the body's parameters; the controller gains or the fingerprint of the controller; the seed; the reference walk (for G4); the licence class (clean, non-commercial, AGPL or unknown); and the list of components that went into it. Every training row carries its source, generator, body or person code, and licence class.

## 8. Measured, derived and simulated values

| Kind | What it includes in this plan | Source tag |
| --- | --- | --- |
| Measured | Van Criekinge plate forces, markers and surface EMG; body measurements stored in the standing trials | measured |
| Derived from measured values | body weight computed from mass or from quiet-standing force; leg length and height computed from markers; augmented copies of measured traversals scaled to new sizes (section 10.2); standardisation constants | derived, augmented (for augmented rows) |
| Simulated by tracking measured motion | G4, G3c and G3f walks, their plate forces and markers | simulated, reference-tracking |
| Simulated without measured motion | G1, G1-cal (calibrated towards measured ranges), G2 and the unscreened control | simulated, generated |
| Simulated with a reduced model | SLIP | simulated, reduced-order |
| Simulated EMG | CR-EMG (calibrated to measured RMS values) and private MyoGen EMG | the tag of the simulated walk it belongs to; CR-EMG is also labelled calibrated |

At forecast time the source tag is always "measured", because every forecast that is scored is made on a measured walk.

## 9. The model and how it is trained

### 9.1 The forecaster

The forecaster family is the one that the walking-scale protocol commits, imported by fingerprint. Its draft is the compact three-pass recurrent forecaster:

- a causal convolution with kernel 3, a filter that combines each input step with the two before it and never with later ones;
- a GRU (gated recurrent unit), a standard network layer that keeps a running memory of a sequence;
- one shared GRU cell applied three times in a row, so the model refines its estimate in three passes;
- two outputs ("heads"): one for the new-load probability (given as a logit, a number that converts to a probability) and one for the impulse residual, the correction the model adds to the persistence forecast.

The draft width (the size of the model's internal layers) is 24.

Physics-source adds an 8-number source-tag embedding, a learned list of 8 numbers for each source tag of section 7.5, and, when switched on, the body vector. Both are joined to the input of the shared cell. At forecast time the tag is always "measured". If walking-scale has committed no family when step S3 starts, the draft family is used and recorded. In any case, no test runs without a committed allocation.

**Standardisation.** Before training, inputs are standardised: shifted and scaled so that typical values are near zero with a spread of about one. The constants come from the measured training people of each fit, with each person given equal weight, and they are applied unchanged to simulated and augmented rows. So simulated data never change how measured inputs are scaled.

### 9.2 Training settings, the same for every comparison

- **Arithmetic.** 32-bit floating-point numbers on the CPU, with PyTorch's repeatable-algorithm setting switched on (`torch.use_deterministic_algorithms(True)`), so the same inputs and seed always give the same model.
- **Threads.** One thread per fit, and at most 16 threads in total, fixed to processor cores 16 to 31.
- **Optimiser.** AdamW, a standard training method, with learning rate 0.002 and weight decay 0.001 (a small pull that keeps weights from growing large), batch 256 rows, and a cosine schedule with 5% warm-up: the learning rate rises over the first 5% of updates, then falls smoothly along a cosine curve. The loss is the walking-scale family's.
- **Update budget.** U = 4,000 updates for every comparison, which draws 4,000 × 256 = 1,024,000 rows, unless a comparison is labelled compute-unmatched.
- **How rows are drawn.** Measured rows are drawn by person, then walk, then issue time, which matches how scores are weighted (each person counts equally). Simulated rows are drawn by generator, then body, then traversal, then issue time.
- **Mixture share s.** The fraction of each batch drawn from simulated (or augmented) rows.
- **Pre-training of P updates.** The first P updates use simulated rows only. The optimiser's internal state is then reset, and a new warm-up and cosine schedule runs over the remaining U − P updates on measured rows (or on a mixture, where the recipe says so). For example, pre-training of 0.5U means 2,000 simulated updates followed by 2,000 fine-tuning updates.
- **No shared pre-training.** Every fit runs its own pre-training. Every comparison therefore uses exactly U updates, and no trained model is shared between folds or seeds.

### 9.3 Seeds

A seed fixes the random choices of a training run. Every neural and tree comparison is trained with five seeds: 431, 20261127, 20261128, 20261129 and 20261130. The forecast issued for a comparison is the average of its five seed forecasts (probabilities averaged, impulses averaged). The results of each seed are also reported.

## 10. The comparisons

The plan calls each model that is compared an arm. The arms whose settings are tuned on the inner folds are grouped in families: M, S\*, AUG\*, H-M and H-S.

### 10.1 The tuning budget

Each family is tuned on the inner folds, inside the training people only, with exactly 8 configurations in two stages:

1. **Stage A** compares 5 recipes specific to the family, at width 64 with the body vector off.
2. **Stage B** runs the stage A winner three more ways: at width 24, at width 128, and at width 64 with the body vector on.

The family's configuration is the best of the 8. Every family gets the same budget of 8, so no family wins by being tuned more.

- **Selection score.** Impulse MAE pooled over the held-out people of all four folds, each held-out person weighted equally, using the average forecast of the five seeds.
- **Brier guard.** A configuration whose pooled Brier score is worse than the family's best by more than 0.002 is not eligible, so a gain in impulse error cannot be bought with much worse landing forecasts.
- **Ties.** If configurations are within 0.1% of each other (relative), the tie goes to fewer simulated or augmented updates, then to fewer total updates, then to the smaller width, then to the body vector off. Ties therefore favour the simpler option.

### 10.2 The three main families

**M: measured only.** Trained on measured rows only. Its five stage A recipes use U/8, U/4, U/2, 3U/4 and U measured updates (500, 1,000, 2,000, 3,000 and 4,000), each with its own cosine schedule. This lets the measured-only model use fewer updates if fewer score better on the inner folds; none uses more than U.

**S\*: simulation.** Always U updates in total, on the pooled corpus of every clean generator that passed the gate, drawing first a generator and then a body. Its five stage A recipes:

1. mixture share 0.25 throughout;
2. mixture share 0.5 throughout;
3. pre-training for 0.5U, then measured fine-tuning;
4. pre-training for 0.9U, then measured fine-tuning;
5. pre-training for 0.75U, then fine-tuning with mixture share 0.1.

**AUG\*: body-scaling augmentation without physics.** This family checks whether simply scaling measured walks to new body sizes gives the same benefit as simulation. Each augmented traversal scales a measured traversal by a mass factor k_m and a leg factor k_l, each drawn uniformly between 1 − r and 1 + r:

- forces are multiplied by k_m;
- time is multiplied by √k_l, which is Froude scaling: the timing of a walker's steps stretches with the square root of leg length, as the swing of a longer pendulum does;
- markers are multiplied by k_l;
- the body vector is scaled to match;
- labels and targets are recomputed by the adapter on the scaled traversal.

Each measured traversal gets twenty augmented copies, with fixed seeds. The tag is "derived, augmented". Example: with r = 0.25, a factor k_m could be anything from 0.75 to 1.25, so a walk with 700 N peaks could become one with peaks between 525 and 875 N. The five stage A recipes:

1. mixture share 0.25 with r = 0.25;
2. mixture share 0.5 with r = 0.25;
3. pre-training for 0.5U on augmented rows (r = 0.25), then measured fine-tuning;
4. pre-training for 0.75U on augmented rows (r = 0.25), then fine-tuning with share 0.1;
5. mixture share 0.25 with r = 0.10.

### 10.3 The tree families

Gradient-boosted trees are a different kind of model: many small decision trees, each one correcting the errors of the ones before. In the walking-scale protocol's planning on training people only, boosted trees beat the three-pass model (2.41 against 2.64 N·s with nine people), so a tree family is included.

**H-M: histogram gradient-boosted trees, measured only.** Its 8 configurations are every combination of maximum iterations 200 or 400, learning rate 0.05 or 0.1, and maximum leaf nodes 15 or 31. It has a classifier for new load and a regressor for the impulse residual over persistence, both with sample weights that give each person equal weight. The features are those that walking-scale commits for its trees; otherwise they are the flattened standardised 20 ms averages, the availability flags, the last average, the mean, the last minus the first, and the persistence impulse.

**H-S: trees with simulated rows.** Its 8 configurations are every combination of simulated weight share 0.10 or 0.25, learning rate 0.05 or 0.1, and maximum leaf nodes 15 or 31, at 400 iterations, with a feature that flags the source (always "measured" at forecast time).

### 10.4 Controls that test where a gain comes from

These are trained in the final fits, using the configuration chosen for S\*.

- **P-shuffle.** The simulated targets are shuffled between bodies, within groups that share the same plate state at issue time and the same generator, but never within one body. The simulated inputs stay exactly as they were, but the physical link between the past force and the future force is broken. If P-shuffle were to help as much as S\*, the gain could not be credited to that physical link.
- **Frozen encoders with a trained readout.** An encoder is the part of the model that turns the inputs into an internal summary. Three encoders are frozen (not trained further): (i) the S\* encoder after pre-training only, which is 0.75U = 3,000 simulated updates; (ii) a randomly initialised encoder; (iii) the frozen shared temporal encoder of the published NeuroTranslate 0.0 model, with a new linear input layer. In (i) and (ii), the shared cell and the output heads are trained; in (iii), the new input layer and the readout. Each gets U/4 = 1,000 measured updates. If the NeuroTranslate 0.0 encoder cannot accept these inputs, (iii) is recorded as not run, with the reason.
- **Simulation only, zero-shot.** U simulated updates and no measured training rows, with the measured standardisation, issued unchanged on the measured test walks.
- **Unscreened simulation like the earlier test.** The published learned controller's walks on the nominal body (nominal; mass 0.9 and 1.1; traction 1.2; mass 1.1 with traction 1.2), with no realism gate and a mixture share of 0.5. Private, scores only.
- **SLIP corpus** in the S\* recipe, if SLIP was run.

### 10.5 Secondary comparisons

**EMG.** These comparisons add muscle signals. They are scored on test people whose EMG qualifies under the walking-scale rule; if walking-scale has no such rule, a person qualifies when the left and right BF, GAS, RF, ST, TA and VL channels are all present, unique and finite (the earlier six-name rule). The arms:

- M_E: the M configuration plus EMG inputs;
- S\*_E-CR: the S\* configuration with CR-EMG on the simulated rows;
- S\*_E-masked: the S\* configuration with the simulated EMG masked and flagged as absent;
- S\*_E-MyoGen: MyoGen EMG on the simulated rows; private.

The EMG features follow the walking-scale family's rule; otherwise they follow the published compact rule (each channel's change relative to its own earlier values, then the median and 80th percentile across channels). The EMG arms reuse the force-only configurations without extra tuning.

**Heel target (only if walking-scale admits markers).** Every neural arm then carries an added output for heel movement from t to t + 100 ms for both heels (in mm, as a straight-line distance, counted once per issue time, with its training loss divided by the number of plate rows at that issue time). The heel comparison therefore uses the same S\* and M fits.

**Variant K (only if walking-scale admits no markers).** M_K and S\*_K: the M and S\* configurations with the delayed heel and toe inputs of section 6.3.

### 10.6 Descriptive analyses

These are reported in full but have no success rule. They help explain the main result.

- **Dose.** How much simulation to use: mixture shares 0.05, 0.1, 0.25, 0.5, 0.75 and 0.9, and pre-training fractions 0.25, 0.5, 0.75 and 0.9, each followed by measured fine-tuning.
- **Diversity.** Whether many different bodies matter more than many walks: the S\* recipe on the preferred passing generator with 1, 8, 32 or 128 bodies (the first entries of the table), always with 384 simulated walks in total, and with the whole corpus. Extra walks vary the reference walk for G4, or the starting state and target speed for G1. With 1 body, all 384 walks come from that body; with 128 bodies, each gives 3.
- **Generator ablation.** Each passing generator alone, including G3f and G2 privately.
- **Data efficiency.** M and S\* trained on the subsets of section 4.6 (3, 6 and 12 people with five subsets each, all 18, and the full pool). A curve a + b·n^(−c) is fitted to M's error against the number of people n. It estimates how many measured people M would need to match S\*, which expresses the value of the simulation in measured people.
- **Compute-unmatched.** U simulated pre-training updates followed by U measured updates (8,000 in all), against M with 2U = 8,000 measured updates.
- **Body shift.** M and S\* trained on the narrow pool: training people whose leg length is at or below the pool median, while the simulated bodies keep their full range. The gain for test people whose leg length is above the narrow pool's maximum is compared with the gain for the others. This asks whether simulated bodies help more for people whose legs are longer than any in the narrow training pool.
- **Distance from training people.** Each test person's gain of S\* over M, plotted against the Mahalanobis distance of that person's height, mass, leg length and walking speed from the training people. Mahalanobis distance measures how unusual a person is relative to the spread of the training people, taking into account that the measurements are related.
- **Trees.** H-S minus H-M.

### 10.7 Reference forecasts on exactly the same rows

- **Persistence with prevalence.** The new-load forecast is the training people's rate of new loads (each person weighted equally); the impulse forecast is persistence, the latest 20 ms average × 0.1 s.
- **Linear trend.** A straight line fitted by least squares through the last five 20 ms averages and extended over the next 100 ms to give the impulse; the training rate for new load.
- **Ridge and logistic regression.** Simple linear models on the same inputs as the neural arms (ridge for impulse, logistic for new load), with the penalty that keeps weights small chosen on the inner folds from 0.001, 0.01, 0.1, 1 and 10.
- **Heel at constant velocity, and stationary heel** (only with the heel target).
- **The published Van Criekinge force specialist** (`models/force-baselines/common-six.npz`), using its force-only calculation, with its penalty chosen on the 6 people of the earlier "validation" role, who were not in its fit.
- **The published compact three-pass checkpoint** (`benchmarks/walking-neural-scaling/checkpoints/three-pass.safetensors`, run with its `predict.py`), issued unchanged where its four or six EMG streams are available; reported with the EMG arms.

The fingerprints of these files and of the NeuroTranslate 0.0 encoder are in the appendix.

## 11. How errors and uncertainty are measured

### 11.1 The main measure

The primary endpoint is per-plate impulse MAE, in N·s. It is averaged over issue times within a walk, then over walks within a person, then over people with equal weight. The four plates are pooled within a walk. Equal weight per person means that a person with many walks counts no more than a person with few.

### 11.2 Other measures

- The Brier score for new load, with the same weighting, on rows with a known label.
- Also reported: reliability bins (whether forecasts of, say, 30% come true about 30% of the time), per-person differences, the share of people who improved, seed-by-seed results, the results for the worst third of people, and counts of people, walks, traversals, issue times, plate rows and confirmed new-load starts in each group.

### 11.3 Comparing two arms

The contrast between an arm and the measured-only model is Δ = the average over test people of error(arm) − error(M). A negative Δ means the arm's errors are smaller. The relative contrast is r = Δ / average error(M). For example, if M's average impulse error were 2.5 N·s and an arm's were 2.4 N·s, Δ would be −0.1 N·s and r would be −4%; these numbers are an illustration, not a result.

### 11.4 Uncertainty

- **Paired bootstrap over test people.** Both arms are scored on the same people, and the difference is taken person by person. The bootstrap then draws test people at random with replacement 10,000 times (seed 20261127), recomputes the average difference each time, and reports the middle 95% of those values as the 95% interval (a percentile interval). This shows how much the result could change with a different set of people of the same kind.
- **p-values.** Two-sided bootstrap p-values are computed for the key secondary comparisons, which are then corrected by the Holm procedure (section 12.5).
- **Planning.** In the walking-scale protocol's study on training people, the improvement of one model over another varied between people with a standard deviation of 8.9% of the error, and repeating a fit with different seeds varied a person's error by 0.15 N·s (standard deviation). With 12 test people, the minimum detectable relative effect at 80% power and two-sided 0.05 is about 5% to 7%: a true improvement smaller than that would usually be missed. The projected gain from adding measured people (from 12 to 46) is about 2.8%. A simulation gain of that size would not be detectable in this test.

## 12. The success rule

The rule is applied once, to the configurations chosen on the inner folds. Nothing is re-chosen after test results are seen.

### 12.1 HELPED

S\* helped if all three of these hold:

1. the upper end of the 95% interval of Δ impulse (S\* − M) is below 0, which means the whole interval lies on the side where S\*'s impulse errors are smaller;
2. the upper end of the 95% interval of Δ Brier (S\* − M) is below +0.002, which means the landing forecasts are at most slightly worse;
3. S\*'s impulse MAE (the point estimate) is below that of force persistence and below that of ridge regression.

### 12.2 PHYSICS-SPECIFIC

Tested only after HELPED, in this fixed order. The result is physics-specific if the upper end of the 95% interval of Δ impulse (S\* − AUG\*) is below 0, which means the simulation beats physics-free body scaling. Otherwise, the report says that the benefit cannot be separated from physics-free body-scaling augmentation.

### 12.3 NEW BODIES

Descriptive only at this group size, using the body-shift contrast and the distance analysis of section 10.6. No claim about new body types is tested.

### 12.4 HURT and INCONCLUSIVE

- **HURT** if the lower end of the 95% interval of Δ impulse (S\* − M) is above 0, which means the whole interval lies on the side where S\*'s errors are larger.
- **INCONCLUSIVE** otherwise. The report then gives the actual interval and the minimum detectable effect computed from the actual spread between people: 2.80 × standard deviation / √n, where n is the number of test people.

### 12.5 Key secondary comparisons

Two secondary comparisons are tested together, with the Holm correction at 0.05, which keeps the chance of any false positive across both at no more than 5%:

- S\*_E-CR − M_E on impulse MAE, in the EMG-qualified test people;
- S\* − M on heel movement MAE, only if the heel target exists.

With two secondaries, Holm tests the smaller p-value at 0.025 and, if that one passes, the other at 0.05. With one secondary, it is tested at 0.05.

### 12.6 Minimum group sizes

- The main rule applies only if at least 10 test people can be scored for impulse and at least 8 of them have both new-load outcomes (some rows with a landing and some without). Below that, every result is descriptive. A test group of 8 or 9 people would therefore give descriptive results only.
- The EMG secondary needs at least 8 scoreable EMG-qualified people. The heel secondary needs at least 10.

### 12.7 Reporting

Every predeclared result is reported, wins and losses alike. No person, threshold or file is added or changed after any test label has been read.

## 13. How the test is sealed

- **Every fit** produces `LOCK.json` (fingerprints of its inputs, code and settings), the trained model, a reload of the model with a check that it gives identical outputs, `RESULT.json` (fingerprint, wall time, peak memory, threads, versions) and `READBACK.json`.
- **FIT-COMPLETE.json** lists the fingerprint of every final model and tree file. It is written before any reserved byte is downloaded, so the final models are fixed before the test data arrive.
- **The test packer** writes a packet that holds only the history (the inputs) for the issuer, and seals the targets with their fingerprint for the scorer.
- **The issuer** makes the forecasts and reads no target.
- **The scorer** runs in a separate process, after the forecasts have been sealed.
- **A separate reviewer** replays the scoring independently.
- **Sealed files** are never re-issued or edited.

## 14. Rights, licences and publication

### 14.1 Clean sources, which may feed public models

- MuJoCo, MyoSuite and myo_sim (Apache-2.0);
- the MyoLeg legs, which come from the Rajagopal full-body model (MIT);
- the MyoTorso lumbar (lower back) model of Bruno et al. (MIT);
- the leg and trunk files of musclemimic-models (Apache-2.0, with its NOTICE);
- the Van Criekinge data (CC0);
- CR-EMG and the project's own code.

### 14.2 Restricted sources: scores only, never in public models

- anything that contains the MoBL-ARMS arm and hand model, which is BSD-3 with a non-commercial restriction; this includes G3f;
- MyoGen output (AGPL-3.0-or-later);
- the published learned walking controller and everything derived from it (G2 and the unscreened control), until its licence is confirmed.

### 14.3 How the licences are enforced

Every generated array records its licence class and the list of its components. Each trained model's NOTICE records its licence closure. The release script refuses any model whose closure is not entirely clean. Restricted outputs stay in the private track folder.

### 14.4 What will be published after the test, whatever the result

- this protocol and BINDING.json;
- the clean code: the virtual laboratory, the body-scaling engine, the clean generators, CR-EMG, and the training, issuing and scoring code;
- GATE-THRESHOLDS.json and FEASIBILITY.json, including a negative feasibility result if no simulator passes;
- the scores of every predeclared arm, including the private arms (scores only);
- per-person results, listed by archive subject code;
- the clean trained models (weights);
- optionally, the clean simulated windows;
- a NOTICE that credits every source with its licence and the project's changes;
- a Technical and a Simple edition of the report.

Project code and clean weights use the repository's licence, CC0 1.0. Files derived from Apache-2.0 model files keep Apache-2.0 and its NOTICE. Elements under CC BY 3.0 keep their attribution.

### 14.5 Decisions waiting for the project owner

1. Models trained on MyoGen EMG stay private, with scores only, unless the owner chooses a separate AGPL-3.0 release.
2. Confirmation that arms built on the non-commercial arm and hand part, and on the published learned controller, publish scores only; or else retraining G2 from scratch.
3. Whether the never-accessed Van Criekinge stroke group (50 people) may be spent on an exploratory test of very different bodies. Using it would use it up for any later test.
4. If the test group has 8 to 12 people, acceptance that only effects of about 5% to 7% or more can be detected; or else a larger physics reserve, at the cost of training people in the walking-scale protocol's stages.

## 15. Steps, times and computer use

All machine work uses at most 16 threads, on processor cores 16 to 31. Generating simulated walks runs 12 single-thread lanes side by side. A core-hour is one processor core busy for one hour.

| Step | Work | Estimate |
| --- | --- | --- |
| S0 feasibility | Set up environments A to D (0.5 h). Download the 18 standing trials and build the training-people ranges (2 to 3 h). Build the virtual laboratory, check units, and run one learned-controller walk through the walking-scale adapter, which settles whether simulated forces and markers fit the inputs and targets with the right units (0.5 day). Build the body-scaling engine (0.5 day). Run G4 (2-day time box) with G1 in parallel (1.5 days). Assemble G3c (0.5 day). Build CR-EMG (0.5 day). Run the MyoGen action-potential timing check (1 h). Write the gate report and FEASIBILITY.json (2 h). Uses training people and simulation only. | 3 to 4 working days, under 10 core-hours |
| S1 binding and admission | BINDING.json, the Simple edition of the protocol, admission by a separate reviewer, the lead's commit. Needs the walking-scale commit. | 1 day |
| S2 corpus | G4 1 to 5 core-hours (under 1 h on 12 lanes); G1 about 40 core-hours (about 4 h on 12 lanes); G3c 3 to 4 h; cutting windows and running checks 2 to 3 h; standing trials of walking-scale training people if not already stored. | one night |
| S3 inner folds | 3 neural families × 8 configurations × 4 folds × 5 seeds = 480 fits of 25 to 90 s each, plus 320 tree fits (2 tree families × 8 × 4 × 5); reference forecasts and checks. | about 0.5 day, 10 to 15 core-hours |
| S4 final fits | About 375 fits on all training people (main arms, controls, secondary and descriptive arms, 5 seeds each); reload checks, fingerprints, FIT-COMPLETE.json. | about 0.5 day, 8 to 10 core-hours |
| S5 test | Ranged download of the test group's walks and standing trials (about 30 to 40 MB, recorded); packing of the history only; the input-only issuer seals the forecasts; a separate scorer; an independent replay. | 0.5 day |
| S6 report | Technical and Simple editions, each as a first draft and a distinct rewrite; a separate reader; the NOTICE. | 1 day |

In total: about 7 to 9 working days, 60 to 90 core-hours, and under 5 GB on the home disk. The raw simulated walks are kept in temporary storage held in memory. If S0 starts on 28 November 2026 and the walking-scale protocol is committed by the end of S0, the report would be ready around 8 to 10 December 2026. The step that sets the overall timing (the critical path) is getting a generator realistic enough in S0.

## 16. What comes later

A later, separate protocol would use reinforcement learning with verifiable rewards on a generator in the physics engine. The rewards would be: no fall, impulse closure, contact consistency, realistic ground forces, and agreement with held-out measured reference walks. It would be followed by a new test on fresh measured people. It needs its own allocation through the walking-scale protocol and its own admission. Optionally, if the owner decides so, there could be an exploratory test on the stroke group.

## 17. Changes from the reviewed design

An earlier design of this test was reviewed before the protocol was written. The protocol departs from it in five ways, each with its reason:

- **Eight configurations per family.** Each family's 8 configurations are 5 recipes plus 3 width and body-vector options, run in two stages. The S\* recipes are 5 of the 7 listed in the design: mixture share 0.1 and plain 0.75U pre-training move to the dose series. The clean generators that pass are pooled rather than chosen on the inner folds. The reason: 7 recipes × 3 widths × 2 body settings × the generators cannot fit an equal budget of 8 per family.
- **Pre-training is not shared across folds and seeds.** The standardisation constants differ by fold, and pre-training inside each fit keeps every arm at exactly U updates.
- **EMG arms reuse the force-only configurations without separate tuning**, so every family keeps the same tuning budget.
- **G3c and G3f are judged with 75% of their bodies passing**, because they have only 32 and 16 bodies by design. G2 cannot satisfy the go/no-go rule while its licence is unknown.
- **The diversity series is fixed at 384 simulated walks.**

## Appendix: plate corners and file fingerprints

### Plate corners

The four plates in the laboratory frame, in millimetres. They are the same in all 12 fit files.

| Plate | x range | y range |
| --- | --- | --- |
| 1 | −508 to 0 | 0 to 463.6 |
| 2 | 0 to 508 | 0 to 463.6 |
| 3 | −254 to 254 | −463.6 to 0 |
| 4 | 508 to 1,005.8 | −17.1 to 480.7 |

### File fingerprints

These identify the exact files named in this plan. They are the same values as in the Technical edition.

| File | Fingerprint |
| --- | --- |
| Archive 138_HealthyPiG.zip | md5 `85235c73455d4df8434810d61517efbb` |
| Its table of contents (central directory, 1,016 entries) | sha256 `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b` |
| Published learned walking controller (myoLegWalk-v0 baseline, MyoSuite 3.0.0) | sha256 `4e7697f296278f9c8c0b4028353eb83db2dcebc6688e1d6c35f4edb68be79d05` |
| MyoLeg muscle file `myolegs_muscle.xml` | sha256 `b998653f78e5ec8e932a7ff6a769a9d4a727cf68918da547c7e7ec4b155e1ef4` |
| MyoLeg joint file `myolegs_chain.xml` | sha256 `da7c4a13eec2abfedc683210972ea423d630461a56909bee2884e181e1bf1d97` |
| MuscleMimic full-body file `myofullbody.xml` | sha256 `2701f343ff8407b03ada728426f0e4b8135bc63aa8857a31bad97aeebb68b914` |
| NeuroTranslate 0.0 shared encoder `models/neurotranslate-0.0/movement-weights.npz` | sha256 `6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864` |
| Van Criekinge force specialist `models/force-baselines/common-six.npz` | sha256 `aa499793a7d84488befd94bc2a628df490896700291af58d2befa0bd1d6bb3bf` |
| Compact three-pass checkpoint `benchmarks/walking-neural-scaling/checkpoints/three-pass.safetensors` | sha256 `9feb39a826d30751fad99e1adc8513a5a87191574df6954d51c93a3c7d4576cf` |
| Its runtime `predict.py` | sha256 `10d8fb8dc7cbcc7fc26e4c87f982148ea57a8c3adba6d47e92f86be3e3224da7` |

The fingerprints of the 54 checked walk files, and the checksums and sizes of the 18 standing trials, are in PROTOCOL.json.
