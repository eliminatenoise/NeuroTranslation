# Physics-source protocol: simulated musculoskeletal walking as a training source for a plate-load forecast on new people

Technical edition, protocol version 1, 27 November 2026. The Simple edition is written with the results. [Machine-readable protocol](PROTOCOL.json) · [Allocation script](allocate.py) · [Allocation output](ALLOCATION.json)

## 1. What this protocol fixes

This protocol tests whether walking simulated with musculoskeletal models, over many simulated bodies, lowers the error of a walking-force forecast for measured people who were never used before. The comparison is against the same model trained on measured walks only, with the same number of training updates and the same number of tuned configurations.

The protocol is fixed before any evaluation byte is opened. No reserved recording has been downloaded or read. Every choice below is final except the items listed in section 4, which are copied mechanically from the walking-scale protocol or computed in step S0 by rules fixed here. They are recorded in a binding file before any reserved byte is opened.

The question comes from the project owner's request of 23 November 2026: physics-grounded training from pre-training to post-training, trying MuscleMimic and MyoGen, aiming at a model that generalises to any body, with reinforcement learning on verifiable rewards in the physics engine later. This protocol covers the pre-training and data-mixture part. Reinforcement learning is a later, separate protocol (section 15).

## 2. Claim limits

- A positive result covers healthy adults of one public cohort walking overground in one laboratory (Van Criekinge et al. 2023), forecast 100 ms ahead on four force plates. It does not show generalisation to every body, to clinical gait or to other tasks.
- Simulated, measured and derived values stay labelled apart in every file, model input and report. A simulated walk is a computed trajectory of a model, not a measurement of a person.
- Surface EMG is muscle electrical activity recorded at the skin. It is not a nerve recording.
- People, walks, traversals, issue times, plate rows and loading events are counted separately. Simulated bodies, simulated walks and simulated traversals are counted separately from measured ones.

### Terms used

- **Issue time:** the moment a forecast is made, on the recording's 1 kHz sample clock. Only samples up to that moment may enter the inputs.
- **Plate row:** one forecast for one force plate at one issue time.
- **Traversal:** one pass of a walker over the four force plates. A measured walk file holds one traversal.
- **Impulse:** the sum of the upward vertical plate force over the next 100 ms multiplied by the sample interval, in newton-seconds (N·s).
- **MAE:** mean absolute error. **Brier score:** the mean squared difference between a forecast probability and the observed 0 or 1 outcome; lower is better.
- **Body weight (BW):** body mass × 9.81 m/s², used to express forces relative to the walker.
- **Mixture share:** the fraction of each training batch drawn from simulated (or augmented) rows. **Pre-training:** updates on simulated rows only, before **fine-tuning** on measured rows.
- **Inner folds:** four groups of training people. A configuration is fitted on three groups and scored on the fourth, in turn. All model choices are made this way, inside the training people.
- **Realism gate:** a fixed set of checks a simulated walk must pass, with thresholds taken from training people and the gait literature, before it may enter training.
- **Licence closure:** the set of licences of every source that contributed to a file or checkpoint.

## 3. Facts measured before this protocol was written

These checks used simulation with invented inputs and the summary metadata of consumed training files. They opened no reserved data.

- An earlier unpublished project test replaced 50% of the fitting windows of a compact forecast with five simulated walks of one simulated anatomy. The walks came from the published learned MyoLeg walking policy (myoLegWalk-v0 baseline checkpoint for MyoSuite 3.0.0, sha256 4e7697f296278f9c8c0b4028353eb83db2dcebc6688e1d6c35f4edb68be79d05), not from a reflex controller. It was scored on six treadmill walkers from another public cohort who had already been used in development. Measured-only training scored better: heel error 42.31 against 52.56 mm, impulse error 7.89 against 9.73 N·s, new-load Brier score 0.0492 against 0.0613. No Van Criekinge simulation packet existed, so those numbers are not a baseline for this task.
- In that test the median largest 20 ms simulated force bin was 1,717 N against 763 N measured, the simulated feet were both off the ground in 2.9% of samples against 0.004% measured, and in each fold only 0 or 1 simulated input windows lay inside the central range of the measured windows on all input features at once.
- On 27 November the same policy, sampled at 100 Hz, reached peak foot forces of 2.4 to 5.0 body weights. The largest loaded-plate peak in the two Van Criekinge fit people with a recorded mass was 1.154 body weights. The policy fell when body mass was multiplied by 0.8, 1.2 or 1.25, and when muscle strength was multiplied by 0.7, 0.75, 0.85 or 1.3. It walked 10 s at mass 0.9 and 1.1. Its published manifest reports no successful walks under MyoSuite 3.1, so it is run only under 3.0.0.
- The Song-Geyer reflex controller of MyoSuite (46 gains, 10 ms control step) fell after 0.37 s with its shipped gains. A 181-rollout evolution-strategy search (a random search that keeps and perturbs the best gain sets) raised survival to 2.54 s. Stable three-dimensional walking was not reached.
- Single-thread speeds: MyoLeg 26.4 times real time raw and 19.7 times inside its environment; the reflex controller 12 times real time; the 416-muscle MuscleMimic full-body model 3.06 times real time when passive. A 10 s policy walk took 0.56 s of wall time. A compact forecaster update of batch 256 took 11.3 ms at width 64 and 21.0 ms at width 128 on one thread.

The test is therefore designed so that a simulator must first pass a realism gate built from training people only, and the reserved group stays closed unless one passes.

## 4. Dependence on the walking-scale protocol, and the binding file

The measured test group and several shared parts come from the walking-scale protocol (folder `models/walking-force-scale/` on branch `walking-scale-protocol`). That protocol holds the single allocation of the never-assigned Van Criekinge healthy people. This protocol writes no second allocation of that pool. When this version was written, the walking-scale protocol was not yet committed.

Before any reserved byte is opened, the lead commits `BINDING.json` in this folder. It may contain only the following items, each with the sha256 of the file it comes from:

1. The walking-scale commit, the sha256 of its `PROTOCOL.json`, and the sha256 of its allocation output.
2. The subject codes of the group that allocation reserves for physics-source, copied as listed there, with the files (archive member, CRC-32, byte counts) it names. This is the test group.
3. The subject codes of the walking-scale training people (all training rungs), and the sha256 of each cached walk file reused from that track.
4. The walking-scale input adapter file and its sha256, with any differences from the task definitions of section 6; the forecaster family code and its sha256; whether walking-scale admits marker inputs and under which causality guard; its EMG channel qualification rule, if any.
5. The inner-fold source. Walking-scale's inner folds are used only if its committed protocol places every physics-source training person (section 5.2) in exactly one of exactly four folds. Otherwise the rule in section 5.5 is used. No other consideration decides this.
6. Step S0 outputs, by sha256: `GATE-THRESHOLDS.json`, `FEASIBILITY.json`, the body pass register, and the list of generators that passed.
7. Lists computed from rules fixed here: the inner folds of the full training pool, the narrow training pool of section 9.6, and the reference-walk assignment of generator G4.

Any change to any other item needs a protocol version 2, a separate reviewer's admission and a commit before any reserved byte is opened. Every version stays in the repository.

If the walking-scale protocol is not committed, or reserves no group for physics-source, step S5 does not run. Results from steps S0 to S4 are then reported as development results on training people only.

## 5. Data

### 5.1 Measured source

- Van Criekinge healthy cohort, figshare `10.6084/m9.figshare.24192480.v1`, data CC0 1.0. Article: Van Criekinge T. et al., Scientific Data 10, 852 (2023), `10.1038/s41597-023-02767-y`, CC BY 4.0.
- Archive `138_HealthyPiG.zip`, figshare file 42450060, 463,159,769 bytes, md5 `85235c73455d4df8434810d61517efbb`. Central directory (1,016 entries) sha256 `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b`.
- Recording clocks: markers at 100 Hz, analog channels (plate forces and EMG) at 1,000 Hz, ten analog samples per marker frame.
- Four type-2 force plates with the same corners in all 12 fit files, in the laboratory frame (mm): plate 1 x −508 to 0, y 0 to 463.6; plate 2 x 0 to 508, y 0 to 463.6; plate 3 x −254 to 254, y −463.6 to 0; plate 4 x 508 to 1,005.8, y −17.1 to 480.7.
- Plate force signs differ between files. The walking-scale adapter normalises them to upward-positive vertical force.
- The published marker trajectories are gap-filled and smoothed, so markers are not causal at the 10 ms scale.

### 5.2 Training people

Every arm trains on the same measured people:

- the 12 people of the earlier fit role: SUBJ112, 110, 096, 024, 082, 062, 061, 040, 044, 043, 039, 038 (36 walks);
- the 6 people of the earlier validation role: SUBJ047, 011, 115, 075, 066, 116 (18 walks). They were consumed as validation by earlier fits. Here they are training people only and are never called new;
- the walking-scale training people (all of its training rungs), reused read-only from that track's cache by sha256, with no second download of their walks.

The 54 local walk files of the first 18 people were checked against their recorded sha256 values on 27 November (all 54 matched); the values are listed in `PROTOCOL.json`.

Never used, in any arm or step: the 12-person Van Criekinge test group of the earlier roster (SUBJ016, 084, 092, 008, 053, 014, 077, 074, 057, 056, 020, 089); the walking-scale evaluation group and every walking-scale group other than its training people and the physics-source group; SUBJ099, which walking-scale leaves untouched; the stroke cohort (see section 14); every other reserved group of the project.

### 5.3 Test group

The test group is the physics-source group of the walking-scale allocation, copied into `BINDING.json`. Its walks and static trials are downloaded by ranged reads only after all of the following: this protocol and `BINDING.json` are committed, a separate reviewer has admitted the protocol, and every final fit is sealed (`FIT-COMPLETE.json`). Each download records the URL, byte range, bytes and sha256. The walking-scale draft reserves 8 to 12 people for this group, depending on how many pool members qualify.

### 5.4 Body descriptors

The body vector is mass (kg), height (mm) and leg length (mm), each with a missing flag.

- Source, in order: (1) the `PROCESSING` parameters `Bodymass`, `Height` and `LLegLength`/`RLegLength` of the person's static trial (archive trial code 0); (2) if absent, leg length from static-trial markers (anterior superior iliac spine to knee to ankle marker, both sides averaged) and height from the highest head marker plus 50 mm; mass stays missing; (3) otherwise missing.
- The same static trial supplies body weight for the realism envelope: `Bodymass` × 9.81 m/s², or, if absent, the mean total vertical plate force over at least 2 s of quiet standing on the plates in the static trial. A person with neither is left out of the body-weight-normalised envelope features but stays a training person.
- Step S0 downloads the 18 static trials of the people in section 5.2 (18 archive members, 5,881,322 compressed bytes; CRC-32 and sizes in `PROTOCOL.json`). Static trials of walking-scale training people are downloaded in step S2 if that track has not cached them. Static trials of test people are read only after the conditions in section 5.3, as a declared issue-time input.
- Whether these files carry `Bodymass`, `Height` and `LegLength` is not yet known. Only 2 of the 12 fit walk files carry them.

### 5.5 Inner folds and subsets (computed by `allocate.py`)

- Inner folds: rank training people by ascending sha256 of `physics-source-inner-v1|` + subject code; fold = rank modulo 4. For the 18 known people the folds are: fold 0 SUBJ040, 061, 011, 039, 066; fold 1 SUBJ116, 044, 038, 024, 062; fold 2 SUBJ112, 082, 047, 110; fold 3 SUBJ096, 115, 043, 075. Walking-scale training people are ranked together with these 18 by the same rule at binding (unless section 4 item 5 selects the walking-scale folds), so the 18 may move between folds once the pool grows. The final pool's folds are recorded in `BINDING.json`.
- Data-efficiency subsets: for n = 3, 6 and 12 and subset s = 0 to 4, rank the 18 people by ascending sha256 of `physics-source-subset-v1|` + s + `|` + subject code and take the first n. n = 18 is the one set of all 18. The full pool is the last point. The resulting lists are in `ALLOCATION.json`.

## 6. Measured task

The task is the walking-scale primary task, computed by the walking-scale adapter imported by sha256. Physics-source uses that code path for measured and simulated walks alike. Its definitions, as drafted by walking-scale and by the earlier Van Criekinge protocol, are:

- Issue times on the native 1 kHz analog grid at sample t = 199 + 20k of each walk. Each (issue, plate) pair for plates 1 to 4 is one row.
- Inputs: ten non-overlapping 20 ms means of the target plate's upward vertical force through sample t (N), and the plate state at t built from samples through t only. Markers enter only if walking-scale admits them, under its causality guard.
- New-load label: an unloaded plate (20 consecutive samples within −10 to +10 N) followed by a rising crossing of +20 N that stays at or above +20 N for the next 19 samples. Positive if such an onset falls in t+1 to t+100; negative if the state is known at t, coverage is complete through t+119 and no onset qualifies.
- Impulse target: the sum of upward vertical force over samples t+1 to t+100 multiplied by 0.001 s, in N·s.
- Eligibility uses inputs and target-validity masks only, applied equally to every arm.

If the committed walking-scale adapter differs from these definitions, the committed adapter governs and the differences are listed in `BINDING.json`.

Physics-source adds only three things to the walking-scale inputs: a source tag, an optional body vector (section 5.4), and, if walking-scale admits markers, plate-centred heel and toe positions under walking-scale's causality guard.

If walking-scale admits no marker inputs, a predeclared secondary variant K adds heel and toe markers (LHEE, RHEE, LTOE, RTOE, mm) in a frame centred on the target plate, with the walking direction taken from past sacrum progression: ten frames 20 ms apart ending at the last marker frame at or before t − 100 ms. The 100 ms lag keeps the published smoothing from carrying target-window information into the input; step S0 measures the smoothing cutoff from training-people marker spectra and reports whether 100 ms suffices. Variant K is applied identically in every arm that runs it.

## 7. Simulation corpus

### 7.1 Simulators and environments

Physics-source builds its own environments under its private track folder, pinned to these versions:

| Environment | Contents | Used for |
| --- | --- | --- |
| A | MuJoCo 3.17.0, MyoSuite 3.0.0, myo_sim 0.2.3 | the published walking policy (unscreened control, optional G2) |
| B | MuJoCo 3.17.0, MyoSuite 3.1.0, myo_sim 0.2.5 | G1 reflex walking, G4 tracking, the virtual laboratory, the body-scaling engine |
| C | MuJoCo 4.0.1, musclemimic-models 1.0.6 | G3c and G3f |
| D | MyoGen 0.11.0, NEURON 8.2.7, own environment and own process | private MyoGen EMG only |
| T | PyTorch (CPU, FP32), scikit-learn, NumPy | forecaster training, issuing and scoring |

The MyoLeg muscle and joint files are identical in myo_sim 0.2.3 and 0.2.5 (`myolegs_muscle.xml` sha256 `b998653f78e5ec8e932a7ff6a769a9d4a727cf68918da547c7e7ec4b155e1ef4`, `myolegs_chain.xml` sha256 `da7c4a13eec2abfedc683210972ea423d630461a56909bee2884e181e1bf1d97`). The MuscleMimic full-body file `myofullbody.xml` has sha256 `2701f343ff8407b03ada728426f0e4b8135bc63aa8857a31bad97aeebb68b914`. Step S0 records the sha256 of every compiled model.

### 7.2 Virtual Van Criekinge laboratory

- Floor plates with the corners of section 5.1. The four-plate layout repeats along the simulated path about every 3.5 m, each repeat shifted by a uniform random offset of up to ±0.4 m along and ±0.1 m across the path.
- Per-plate vertical force: the sum of the normal forces of foot-floor contacts whose contact point lies inside the plate, at 1 kHz (the 1 ms simulation step equals the analog clock). A foot that straddles two plates splits its load between them.
- Plate noise and offset: per-plate standard deviation and offset drawn from the distribution measured on unloaded stretches of training-people walks (step S0).
- Traversals: each simulated walk lasts 12 s; the first 2 s are discarded. Each crossing of a plate layout yields one traversal crop of 2.1 to 4.2 s, centred on the layout, like the measured walks. A traversal is passed to the walking-scale adapter as one walk.
- Checks on every recorded walk: vertical impulse closure under 0.5% (total floor contact force against body weight and the change of vertical momentum, including any tracking residual); no floor contact by any body other than the feet; no external force other than the logged tracking residual; and a one-tick future-replacement test (replacing every sample after t must leave every issued input unchanged).
- Simulated markers: Plug-in Gait heel and toe sites placed on the scaled calcaneus and toe bodies, sampled at 100 Hz, with 1 to 2 mm of soft-tissue noise, and low-pass filtered with the cutoff measured in step S0 so that they match the published processing.

### 7.3 Body-scaling engine

Bodies are built with MuJoCo's model-editing interface (MjSpec), which changes a model description before it is compiled: segment lengths (body positions, geometry and mesh sizes, muscle attachment sites, foot contact geometry), masses and inertias, and muscle peak isometric forces. Muscle length ranges are recomputed at compile time. Checks: leg-length and mass sums match the body table, and building with every factor equal to 1 reproduces the compiled sha256 of the unmodified model.

### 7.4 Bodies

The body table in `ALLOCATION.json` holds 1,024 bodies drawn from a scrambled Sobol sequence with seed 20261127 over ten factors. A Sobol sequence is a deterministic sequence of points that fills a multi-dimensional range more evenly than random draws; scrambling randomises it while keeping that property. The scrambling is defined in `allocate.py` (linear matrix scramble and digital shift with bits from sha256), so the table can be recomputed with the Python standard library alone. The ranges come from general adult anthropometry and the published cohort description (ages 21 to 86), never from reserved people:

| Factor | Range |
| --- | --- |
| Stature | 1.50 to 1.95 m (segment scale = stature / 1.70 m) |
| Body mass index | 18 to 34, mass = BMI × stature², clipped to 45 to 115 kg (43 of 1,024 bodies clipped) |
| Thigh/shank length ratio | ±6% at constant leg length |
| Foot length | ±8% |
| Pelvis width | ±8% |
| Muscle strength | 0.6 to 1.3 × (mass / 75 kg)^(2/3), multiplying every peak isometric force |
| Muscle maximum shortening velocity | 8 to 12 optimal fibre lengths per second |
| Foot-floor contact time constant | 0.02 to 0.04 s |
| Foot-floor friction | 0.6 to 1.2 |
| Speed factor | 0.8 to 1.25 |

Generators use prefixes of the table: G4 bodies B0000 to B0599 (3 walks each), G1 B0000 to B0127 (3 target speeds each), G3c B0000 to B0031, G3f B0000 to B0015. Prefixes of length 1, 8, 32 and 128 of a scrambled Sobol sequence are evenly spread, which the diversity series uses. Target speeds are in section 7.5. Bodies, walks, traversals, issues and events are counted separately, and every failed body stays in a failure register.

### 7.5 Generators

Each generator has a time box in step S0 and a fixed order of preference. Source tags keep these kinds apart: measured; derived, augmented (section 9.2); simulated, reference-tracking (G4, G3c, G3f); simulated, generated (G1, G1-cal, G2, the unscreened control); simulated, reduced-order (SLIP).

- **G4, preferred: muscle-driven tracking of training-people reference walks.** Inverse kinematics of the Van Criekinge markers of a training person's walk on that person's scaled model, retargeting to the simulated body (time-warp to the target speed, pelvis path scaled by leg length), then tracking on the simulated body in MuJoCo. Every 10 ms, proportional-derivative joint targets give the joint torques needed to follow the reference, and static optimisation chooses the 80 MyoLeg muscle excitations that produce those torques with the least summed squared activation. A root (pelvis) residual wrench is allowed, capped at 10% of body weight and logged. Ground forces come from the simulated contacts. Target speed = speed factor × reference speed × √(stature / reference stature), clipped to 0.95 to 1.70 m/s. Reference walks come from training people only. Walk w (0, 1 or 2) of body B takes the training walk with the smallest sha256 of `physics-source-g4-ref-v1|` + body id + `|` + w + `|` + subject code + `|` + author trial index (for example `physics-source-g4-ref-v1|B0000|0|SUBJ112|1`); in each inner fold, simulated walks whose reference person is in the held fold are left out. Test people feed no generator. G4 output is physics-consistent retargeting of measured motion onto new bodies, not independently generated motion. Time box 2 days.
- **G1: Song-Geyer reflex controller with CMA-ES** (covariance matrix adaptation evolution strategy, a standard search over controller gains). Gains are searched with population 24, at most 6,000 rollouts for the nominal body and at most 1,200 for every other body, which starts from the nearest solved body. Objective: survival up to 12 s, minus the error from the target speed, minus effort (time integral of activation cubed). No measured-data term. Target speeds = speed factor × (0.9, 1.0, 1.1) × 1.25 m/s × √(stature / 1.70 m), clipped to 0.95 to 1.70 m/s (listed per body in `ALLOCATION.json`). Time box 1.5 days, in parallel with G4. This is the generated-motion source.
- **G1-cal: calibrated reflex variant.** Run only if neither G4 nor G1 passes the gate. The gate's literature and envelope targets (peak force, stance time, double support) are added as penalties to the G1 objective. Labelled calibrated. Time box 1 day.
- **G3c: MuscleMimic legs and torso.** The arm subtree of the full-body model is removed and rigid arm masses (de Leva fractions: upper arm 2.71%, forearm 1.62%, hand 0.61% of body mass on each side) are attached at the shoulders. Driven by the G4 tracker, not by transplanted reflex gains, because MuscleMimic changed muscle paths and attachments. Run only if G4 passes. Time box 0.5 day.
- **G3f: full MuscleMimic myofullbody model** (with its non-commercial arm and hand part), driven by the G4 tracker. Private; scores only.
- **G2 (optional): domain-randomised reinforcement learning from the published policy.** Its checkpoint carries no stated licence, so G2 data and arms stay private and scores only, and G2 cannot satisfy the go/no-go rule. Run only if time remains.
- **SLIP (optional): reduced-order spring-mass walking**, a control for whether musculoskeletal detail matters. Tagged simulated, reduced-order.

### 7.6 Simulated EMG

- Muscle mapping from MyoLeg excitations: BF = bflh + bfsh, GAS = gaslat + gasmed, RF = recfem, ST = semiten, TA = tibant, VL = vaslat, per side. ERS comes from the torso muscles in G3c and G3f and is masked elsewhere.
- **CR-EMG (clean-room generator, public).** Written from published equations by a person who has not read the MyoGen source and records that fact: Fuglevand recruitment (recruitment range 30 to 60), rate coding 8 to 35 Hz, inter-spike-interval coefficient of variation 0.15 to 0.25, Hermite-Rodriguez motor-unit action potentials, attenuation by subcutaneous fat depth (2 to 15 mm, from body mass index), conduction velocity 3.5 to 5 m/s, bipolar electrodes 20 mm apart. Simulated at 10 kHz, band-passed 20 to 450 Hz, decimated to 1 kHz, signal-to-noise ratio 10 to 30 dB, log-normal gain per body and channel. Each channel's amplitude is then quantile-mapped to the training-people RMS distribution. Because of that mapping, CR-EMG is labelled calibrated.
- **MyoGen EMG (private).** The same excitations drive MyoGen 0.11.0 surface EMG in environment D, in a separate process and outside the public folder. MyoGen is AGPL-3.0-or-later; its outputs and every model trained on them stay private, scores only.
- EMG precedes force through MuJoCo's muscle activation dynamics.

### 7.7 Realism gate

The gate is frozen in `GATE-THRESHOLDS.json` in step S0 before any corpus is generated. Its data-derived thresholds come from the 18 training people of section 5.2 only (body weight from their static trials), widened by 10%. Its fixed thresholds come from the fit-pool range and the gait literature.

Per walk, over the steady part:

| Criterion | Threshold |
| --- | --- |
| No fall | pelvis stays above 0.6 × standing pelvis height and no non-foot floor contact, for at least 8 s |
| Speed | mean forward speed 0.90 to 1.75 m/s |
| Cadence | 90 to 140 steps/min |
| Peak vertical force per foot stance / body weight | median 1.00 to 1.30; 99th percentile at most 1.50 |
| Stance time | median, and at least 90% of stances, within [0.9 × 1st percentile, 1.1 × 99th percentile] of training-people plate stance times |
| Double support | median 15% to 30% of the stride |
| Flight | both feet below 20 N in fewer than 0.5% of samples |
| Momentum closure | within 0.5% |
| Tracking residual (G4, G3c, G3f) | root residual force RMS at most 5% of body weight |

A body passes if at least 2 of its walks pass. Only passing walks enter the corpus.

Per generator (corpus level):

- At least 50% of simulated issue rows whose 200 ms history mean is at least 20 N lie jointly inside the training-people central 90% box (5th to 95th percentile per feature) of: mean 200 ms force / body weight, largest 20 ms bin / body weight, 100 ms impulse / body weight, and, if markers are admitted, heel displacement over 180 ms.
- Per-plate onset rate per traversal within the training-people minimum to maximum.
- Reported, not gated: the area under the curve of a classifier separating simulated from measured rows on these features, and per-feature distribution distances.

Go/no-go: at least 128 distinct passing bodies from at least one clean generator (G4, G1 or G1-cal) that also meets the corpus-level criteria, with the passing bodies covering at least 80% of every factor range of section 7.4. G3c and G3f are judged by the same per-walk and corpus criteria with at least 75% of their bodies passing. If no clean generator passes, G1-cal is tried once. If it also fails, the work stops, the test group stays sealed and the negative feasibility result is published.

### 7.8 Provenance

Every simulated walk records: generator, environment and package versions, compiled model sha256, body parameters, controller gains or policy hash, seed, reference walk (G4), licence class (clean, non-commercial, AGPL or unknown) and the list of components. Every training row carries source, generator, body or person id and licence class.

## 8. Model and training

### 8.1 Forecaster

The forecaster family is the one walking-scale commits (its draft: the compact three-pass recurrent forecaster, a causal convolution with kernel 3, a GRU and one shared GRU cell applied three times, with heads for the new-load logit and the impulse residual over persistence; draft width 24). Its code is imported by sha256. Physics-source adds an 8-dimensional source-tag embedding (one learned vector per source tag of section 7.5) and, when switched on, the body vector, both concatenated to the input of the shared cell. At issue the tag is always measured. If walking-scale has committed no family when step S3 starts, the draft family is used and recorded; no test runs without a committed allocation in any case.

Standardisation constants come from the measured training people of each fit, with equal weight per person, and are applied unchanged to simulated and augmented rows.

### 8.2 Training settings, the same for every arm

- FP32 on CPU, `torch.use_deterministic_algorithms(True)`, one thread per fit, at most 16 threads in total pinned to CPUs 16 to 31.
- AdamW, learning rate 0.002, weight decay 0.001, batch 256, cosine schedule with 5% warm-up. Loss as in the walking-scale family.
- Update budget U = 4,000 updates (1,024,000 rows drawn) for every arm unless an arm is labelled compute-unmatched.
- Measured rows are drawn person, then walk, then issue, matching the scoring weights. Simulated rows are drawn generator, then body, then traversal, then issue.
- Mixture share s: the fraction of each batch drawn from simulated (or augmented) rows.
- Pre-training P updates: the first P updates use simulated rows only; the optimiser state is then reset and a new warm-up and cosine schedule runs over the remaining U − P updates.
- Every fit runs its own pre-training, so every arm uses exactly U updates and no checkpoint is shared between folds or seeds.

### 8.3 Seeds

Five seeds for every neural and tree arm: 431, 20261127, 20261128, 20261129 and 20261130. The issued forecast of an arm is the mean of its five seed forecasts (probabilities and impulses averaged). Seed-by-seed results are reported.

## 9. Arms

### 9.1 Tuning budget

Each family is tuned on the inner folds, inside the training people only, with exactly 8 configurations in two stages. Stage A compares 5 family-specific recipes at width 64 with the body vector off. Stage B runs the stage A winner at width 24, at width 128, and at width 64 with the body vector on. The family's configuration is the best of the 8.

- Selection score: impulse MAE pooled over the held people of all four folds, each held person weighted equally, using the five-seed mean forecast.
- A configuration whose pooled Brier score exceeds the family's best by more than 0.002 is not eligible.
- Ties within 0.1% relative go to fewer simulated or augmented updates, then fewer total updates, then the smaller width, then the body vector off.

### 9.2 Primary families

- **M, measured only.** Stage A: U/8, U/4, U/2, 3U/4 and U measured updates (each with its own cosine schedule).
- **S\*, simulation.** All at U total updates, on the pooled corpus of every clean generator that passed the gate (sampled generator, then body). Stage A: mixture share 0.25; mixture share 0.5; pre-training 0.5U then measured fine-tuning; pre-training 0.9U then measured fine-tuning; pre-training 0.75U then fine-tuning with share 0.1.
- **AUG\*, physics-free body-scaling augmentation.** Each augmented traversal scales a measured traversal by a mass factor k_m and a leg factor k_l drawn uniformly in [1 − r, 1 + r]: forces × k_m, time × √k_l (Froude scaling), markers × k_l, body vector scaled to match; labels and targets are recomputed by the adapter on the scaled traversal. Twenty augmented copies per measured traversal, seeded. Tag: derived, augmented. Stage A: share 0.25 with r = 0.25; share 0.5 with r = 0.25; pre-training 0.5U on augmented rows (r = 0.25) then measured fine-tuning; pre-training 0.75U on augmented rows (r = 0.25) then fine-tuning with share 0.1; share 0.25 with r = 0.10.

### 9.3 Tree families

Walking-scale's fit-only planning had boosted trees ahead of the three-pass model (2.41 against 2.64 N·s at nine people), so a tree family is included.

- **H-M, histogram gradient-boosted trees, measured only.** 8 configurations: maximum iterations 200 or 400 × learning rate 0.05 or 0.1 × maximum leaf nodes 15 or 31. A classifier for new load and a regressor for the impulse residual over persistence, with person-equal sample weights. Features as committed by walking-scale for its trees; otherwise the flattened standardised bins, availability flags, last bin, mean, last minus first, and the persistence impulse.
- **H-S, trees with simulated rows.** 8 configurations: simulated weight share 0.10 or 0.25 × learning rate 0.05 or 0.1 × maximum leaf nodes 15 or 31, at 400 iterations, with a source flag feature (measured at issue).

### 9.4 Specificity controls (final fits, using the S\* configuration)

- **P-shuffle:** simulated targets permuted across bodies within strata of plate state at issue and generator, never within a body. This keeps the simulated input distribution and breaks the physical link between history and future.
- **Frozen encoders with a fitted readout:** (i) the S\* encoder after pre-training only (0.75U simulated updates), frozen; (ii) a randomly initialised frozen encoder; (iii) the frozen NeuroTranslate 0.0 shared temporal encoder (`models/neurotranslate-0.0/movement-weights.npz`, sha256 `6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864`) with a new linear input layer. In (i) and (ii) the shared cell and heads are trained, in (iii) the input layer and readout; U/4 measured updates each. If the 0.0 encoder cannot accept these inputs, (iii) is recorded as not run with the reason.
- **Simulation only, zero-shot:** U simulated updates, measured standardisation, issued unchanged.
- **Unscreened simulation like the earlier test:** the published policy's walks on the nominal body (nominal, mass 0.9 and 1.1, traction 1.2, mass 1.1 with traction 1.2), no gate, mixture share 0.5. Private, scores only.
- **SLIP corpus** in the S\* recipe, if SLIP was run.

### 9.5 Secondary arms

- **EMG.** Scored on test people whose EMG qualifies under the walking-scale rule, or, if walking-scale has none, the earlier six-name rule (named left and right BF, GAS, RF, ST, TA and VL present, unique and finite). M_E: the M configuration plus EMG inputs. S\*_E-CR: the S\* configuration with CR-EMG on simulated rows. S\*_E-masked: simulated EMG masked with its flag. S\*_E-MyoGen: MyoGen EMG on simulated rows, private. EMG features follow the walking-scale family's rule; otherwise the published compact rule (within-channel relative change, median and 80th percentile across channels). EMG arms reuse the force-only configurations with no extra tuning.
- **Heel target (only if walking-scale admits markers):** every neural arm then carries an added head for heel displacement from t to t + 100 ms for both heels (mm, Euclidean, counted once per issue, with its loss divided by the issue's plate rows), so the heel secondary compares the same S\* and M fits.
- **Variant K (only if walking-scale admits no markers):** M_K and S\*_K, the M and S\* configurations with the lag-guarded heel and toe inputs of section 6.

### 9.6 Descriptive analyses (no success rule)

- Dose: mixture-only shares 0.05, 0.1, 0.25, 0.5, 0.75 and 0.9; pre-training fractions 0.25, 0.5, 0.75 and 0.9 followed by measured fine-tuning.
- Diversity: the S\* recipe on the preferred passing generator with 1, 8, 32 or 128 bodies (table prefixes) at a fixed 384 simulated walks (extra walks vary the reference walk for G4, or the initial state and target speed for G1), and with the whole corpus.
- Generator ablation: each passing generator alone, including G3f and G2 privately.
- Data efficiency: M and S\* trained on the subsets of section 5.5 (n = 3, 6 and 12 with five subsets each, n = 18, and the full pool). A curve a + b·n^(−c) fitted to M gives the number of measured people at which M would match S\*.
- Compute-unmatched: U simulated pre-training updates followed by U measured updates, against M with 2U measured updates.
- Body shift: M and S\* trained on the narrow pool (training people with leg length at or below the pool median; simulated bodies keep the full range). Gain for test people whose leg length exceeds the narrow pool's maximum against gain for the others.
- Per-person gain of S\* over M against the Mahalanobis distance of the person's height, mass, leg length and walking speed from the training people.
- Trees: H-S minus H-M.

### 9.7 Baselines on identical issues

- Fit prevalence of new load (training people, equal weight) with force persistence (latest 20 ms mean × 0.1 s).
- Linear trend: a least-squares line through the last five 20 ms means, integrated over the next 100 ms; prevalence for new load.
- Ridge and logistic regression on the same inputs as the neural arms, penalty chosen on the inner folds from 0.001, 0.01, 0.1, 1 and 10.
- Heel constant velocity and stationary heel (only with the heel target).
- The published Van Criekinge force specialist (`models/force-baselines/common-six.npz`, sha256 `aa499793a7d84488befd94bc2a628df490896700291af58d2befa0bd1d6bb3bf`), force-only calculation, penalty chosen on the 6 earlier validation people, who were not in its fit.
- The published compact three-pass checkpoint (`benchmarks/walking-neural-scaling/checkpoints/three-pass.safetensors`, sha256 `9feb39a826d30751fad99e1adc8513a5a87191574df6954d51c93a3c7d4576cf`; runtime `predict.py`, sha256 `10d8fb8dc7cbcc7fc26e4c87f982148ea57a8c3adba6d47e92f86be3e3224da7`), issued unchanged where its four or six EMG streams are available; reported with the EMG arms.

## 10. Metrics and uncertainty

- Primary endpoint: per-plate impulse mean absolute error (N·s), averaged over issues within a walk, walks within a person, then people equally. Plates are pooled within a walk.
- Brier score for new load, with the same weighting, on rows with a known label.
- Also reported: reliability bins, per-person differences, the share of people improved, seed-by-seed results, the worst third of people, and counts of people, walks, traversals, issues, plate rows and verified onsets by group.
- Contrast: Δ = mean over test people of error(arm) − error(M); relative contrast r = Δ / mean error(M).
- Uncertainty: paired bootstrap over test people, 10,000 draws, seed 20261127, 95% percentile intervals. Two-sided bootstrap p-values for the Holm-adjusted secondaries.
- Planning: walking-scale's fit-only study measured a between-person standard deviation of the relative paired difference of 8.9% and a seed standard deviation of 0.15 N·s per person. With 12 test people, the minimum detectable relative effect at 80% power and two-sided 0.05 is about 5% to 7%. The projected gain from adding measured people (12 to 46) is about 2.8%, so a simulation gain of that size would not be detectable here.

## 11. Success rule

The rule is applied once, to the configurations selected on the inner folds.

- **HELPED** if all three hold: the 95% upper bound of Δ_impulse(S\* − M) is below 0; the 95% upper bound of Δ_Brier(S\* − M) is below +0.002; and S\*'s impulse MAE point estimate is below those of force persistence and ridge.
- **PHYSICS-SPECIFIC**, tested only after HELPED, in fixed sequence: the 95% upper bound of Δ_impulse(S\* − AUG\*) is below 0. Otherwise the report says the benefit cannot be separated from physics-free body-scaling augmentation.
- **NEW BODIES**: descriptive only at this group size (the body-shift contrast and the distance analysis of section 9.6).
- **HURT** if the 95% lower bound of Δ_impulse(S\* − M) is above 0.
- **INCONCLUSIVE** otherwise, stated with the realised interval and the minimum detectable effect computed from the realised spread (2.80 × standard deviation / √n).
- Key secondaries, Holm-adjusted together at 0.05 (with two secondaries the Holm procedure tests the smaller p-value at 0.025 and, if that passes, the other at 0.05; with one secondary it is tested at 0.05): S\*_E-CR − M_E on impulse MAE (EMG-qualified people), and S\* − M on heel displacement MAE (only if the heel target exists).
- Floor: the primary rule applies only if at least 10 test people are scoreable for impulse and at least 8 of them have both label classes. Below that, every result is descriptive; a test group of 8 or 9 people would therefore give descriptive results only. The EMG secondary needs at least 8 scoreable EMG-qualified people; the heel secondary at least 10.
- Every predeclared result is reported, wins and losses alike. No person, threshold or file is added or changed after any test label is read.

## 12. Steps and estimated times

All machine work uses at most 16 threads on CPUs 16 to 31; generation runs 12 single-thread lanes.

| Step | Work | Estimate |
| --- | --- | --- |
| S0 feasibility | Environments A to D (0.5 h); 18 static trials and the training-people envelope (2 to 3 h); virtual laboratory, units and one policy walk through the walking-scale adapter, which settles whether simulated forces and markers map onto the inputs and targets with their units (0.5 day); body-scaling engine (0.5 day); G4 (2-day time box) with G1 in parallel (1.5 days); G3c assembly (0.5 day); CR-EMG (0.5 day); MyoGen action-potential timing (1 h); gate report and `FEASIBILITY.json` (2 h). Training people and simulation only. | 3 to 4 working days, under 10 core-hours |
| S1 binding and admission | `BINDING.json`, the Simple edition of the protocol, a separate reviewer's admission, the lead's commit. Needs the walking-scale commit. | 1 day |
| S2 corpus | G4 1 to 5 core-hours (under 1 h on 12 lanes); G1 about 40 core-hours (about 4 h on 12 lanes); G3c 3 to 4 h; windows and checks 2 to 3 h; static trials of walking-scale training people if not cached. | one night |
| S3 inner folds | 3 neural families × 8 configurations × 4 folds × 5 seeds = 480 fits of 25 to 90 s, plus 320 tree fits; baselines and checks. | about 0.5 day, 10 to 15 core-hours |
| S4 final fits | about 375 fits on all training people (primary, controls, secondary and descriptive arms, 5 seeds each); reload-equality checks, hashes, `FIT-COMPLETE.json`. | about 0.5 day, 8 to 10 core-hours |
| S5 test | Ranged download of the test group's walks and static trials (about 30 to 40 MB, recorded); history-only packing; an input-only issuer seals the forecasts; a separate scorer; an independent replay. | 0.5 day |
| S6 report | Technical and Simple editions, first draft, distinct rewrite, separate reader, NOTICE. | 1 day |

Total: about 7 to 9 working days, 60 to 90 core-hours, under 5 GB on the home disk (raw simulated walks in RAM-backed temporary storage). If S0 starts on 28 November 2026 and the walking-scale protocol is committed by the end of S0, the report would be ready about 8 to 10 December 2026. The critical path is generator realism in S0.

## 13. Records and sealing

- Every fit: `LOCK.json` (hashes of inputs, code and settings), the checkpoint, a reload with an equality check, `RESULT.json` (sha256, wall time, peak memory, threads, versions) and `READBACK.json`.
- `FIT-COMPLETE.json` lists the sha256 of every final checkpoint and tree file before any reserved byte is downloaded.
- The test packer writes a history-only packet for the issuer and seals the targets with their sha256 for the scorer. The issuer reads no target. The scorer runs in a separate process after the forecasts are sealed. A separate reviewer replays the scoring.
- Sealed files are never re-issued or edited.

## 14. Rights and publication

- Clean sources, which may feed public weights: MuJoCo, MyoSuite and myo_sim (Apache-2.0); the MyoLeg legs from the Rajagopal full-body model (MIT); the MyoTorso lumbar model of Bruno et al. (MIT); musclemimic-models leg and torso assets (Apache-2.0, with its NOTICE); Van Criekinge data (CC0); CR-EMG and the project's own code.
- Restricted, scores only, never in public weights: anything containing the MoBL-ARMS arm and hand model (BSD-3 with a non-commercial restriction), including G3f; MyoGen output (AGPL-3.0-or-later); the published walking policy checkpoint and everything derived from it (G2, the unscreened control) until its licence is confirmed.
- Every generated array records its licence class and component list. Each checkpoint's NOTICE records its licence closure. The release script refuses any checkpoint whose closure is not all clean. Restricted outputs stay in the private track folder.
- Published after the test: this protocol and `BINDING.json`; the clean code (virtual laboratory, scaling engine, clean generators, CR-EMG, training, issuing and scoring); `GATE-THRESHOLDS.json` and `FEASIBILITY.json`, including a negative result; scores of every predeclared arm, private arms included; per-person results by archive subject code; clean weights; optionally the clean simulated windows; a NOTICE crediting every source with its licence and our changes; Technical and Simple editions. Project code and clean weights use the repository licence, CC0 1.0; files derived from Apache-2.0 model assets keep Apache-2.0 and its NOTICE; CC BY 3.0 elements keep their attribution.
- Owner decisions pending: (1) weights trained on MyoGen EMG stay private with scores only, unless the owner chooses a separate AGPL-3.0 release; (2) confirmation that arms built on the non-commercial arm and hand part and on the published policy publish scores only, or retraining G2 from scratch; (3) whether the never-accessed Van Criekinge stroke cohort (50 people) may be spent on an exploratory test of very different bodies, which would use it up; (4) if the test group has 8 to 12 people, acceptance that only effects of about 5% to 7% or more are detectable, or a larger physics reserve at the cost of walking-scale training rungs.

## 15. Later, separate protocol

Reinforcement learning with verifiable rewards on a generator in the physics engine (rewards: no fall, impulse closure, contact consistency, ground-force realism, agreement with held measured references), followed by a new test on fresh measured people. It needs its own allocation through walking-scale and its own admission. Optional, by owner decision: an exploratory test on the stroke cohort.

## 16. Departures from the reviewed design

- Each family's 8 configurations are 5 recipes plus 3 width and body-vector options in two stages. The S\* recipes are 5 of the 7 listed in the design; mixture share 0.1 and plain 0.75U pre-training move to the dose series. Clean generators that pass are pooled rather than chosen on the inner folds. Reason: 7 recipes × 3 widths × 2 body settings × generators cannot fit an equal budget of 8 per family.
- Pre-training is not shared across folds and seeds. Standardisation constants differ by fold, and per-fit pre-training keeps every arm at exactly U updates.
- EMG arms reuse the force-only configurations without separate tuning, so every family keeps the same tuning budget.
- G3c and G3f are judged with 75% of their bodies passing, since they have 32 and 16 bodies by design; G2 cannot satisfy the go/no-go rule while its licence is unknown.
- The diversity series is fixed at 384 simulated walks.
