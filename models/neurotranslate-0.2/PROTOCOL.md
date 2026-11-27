# NeuroTranslate 0.2 protocol: one pooled movement encoder, tested on people and sessions no earlier fit has used

Technical edition, protocol version 1, revision 3, 28 November 2026. Revision 3 records the lead's decisions of 28 November 2026, made after the second review of the training data: a corrected rule for the D arms of the quantity-versus-diversity study, the values computed from the counted training data with their limits, and the departures, record corrections and process incidents of steps P1 and P2 (section 16.1). Revision 2 is commit 554c59c (section 16.2). Revision 1 is commit c0e522f, which was 17f956b before the branch was rebased (section 16.3). No training run has started, apart from one speed trial of the training code of about 6 seconds (section 16.1), and no evaluation byte has been read. The only bytes of an evaluation set ever transferred are the compressed bytes described in section 3, which came with two design-stage range reads and were never inflated. [Simple edition](PROTOCOL-SIMPLE.md) · [Machine-readable protocol](PROTOCOL.json) · [Allocation script](allocate.py) · [Allocation output](ALLOCATION.json)

## 1. What this protocol fixes

NeuroTranslate 0.2 is one causal network trained at once on the training splits of many openly licensed recordings of neural activity, muscle activity (EMG), body motion and force. It is then frozen. Each test set gets only small adapters (identity rows for new channels and a ridge readout). The network is scored once on people, animals and sessions that no NeuroTranslation fit has used, against matched controls with the same adapter budget.

The protocol is fixed before any evaluation byte is opened. It fixes the training mixture and the rules that admit a dataset to it, the representation, architecture, objective and training loop, how every model choice is made inside the training people, the fresh test sets, the controls, the metrics, the paired bootstrap, the success rules, the quantity-versus-diversity arms, the compute plan and what will be published. Items that can only be counted after the training data are read (for example the number of windows per dataset) are computed by rules fixed here and recorded in `MIXTURE-MANIFEST.json` before the freeze.

The question comes from the project owner's direction to train one combined movement model on as much varied, licensed neural, EMG and motion data as possible, the best model that can be engineered regardless of size, with time estimates. The protocol treats "more and more varied data generalise better" as a hypothesis to test, not as a premise.

## 2. Claim limits

- Results cover the listed datasets, tasks, inputs and horizons. The primary human sets have 10 people (E1) and 5 people (E2). E3 has one animal and carries no population claim.
- Forecasts are made on archived recordings. Published marker trajectories were filtered or gap-filled by their authors, and AJILE12 pose is an offline estimate, so nothing here describes live latency.
- Surface and intramuscular EMG record muscle electrical activity. They are not nerve recordings. EEG and ECoG are field potentials. Spike counts come from sorted units in public archives.
- Measured, derived (DeepLabCut pose, OpenSim joint angles, mean-absolute-value EMG envelopes, author-filtered EEG) and simulated values are labelled apart in every file, token and report. No simulated data enter the primary mixture.
- A win or a loss holds against the listed controls at the stated budgets. It is not evidence of general biological translation. The quantity-versus-diversity result holds only at the data scale tested.
- People, animals, sites, recordings, tasks, windows and events are counted separately.

### Terms used

- **Step:** 20 ms of a recording. Step k covers [20k, 20k + 20) ms and becomes available at its end.
- **Issue time:** the moment a forecast is made. Only samples up to that moment may enter the inputs.
- **Window:** a non-overlapping 1.2 s stretch of a recording, the unit used to count data. Training crops may overlap.
- **Individual:** a person or an animal, the independent unit for weighting and uncertainty.
- **Inner folds:** five groups of training individuals of each dataset (section 6). Fold 0 is the inner-validation fold; all model choices are made with it.
- **Adapter:** the small set of parameters fitted for a test set while the encoder stays frozen.
- **Persistence:** the forecast that nothing changes from the last value. **Linear trend:** a straight-line extrapolation of the recent past.
- **Relative error R:** an individual's error divided by that individual's persistence error.
- **Consumed:** already used as an evaluation group by an earlier study, so no longer new.

## 3. Facts established before this protocol was written

- The NeuroTranslate 0.0 shared encoder (`models/neurotranslate-0.0/movement-weights.npz`, 227,155 bytes, sha256 `6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864`) has 5,184 core parameters: a linear read-in of 6 inputs to width 24, 4 learned positions and one transformer block. It was trained only on HoloAssist headset wrist tracking and one rat's W-track task. In all five of its tests on new people a simpler forecast matched or beat it (for example right foot: plate persistence 76.45 N and ridge 82.04 N against 85.18 N; balance: straight line 7.368/6.617 mm against 8.108/7.429 mm), and none of the five published its plan or model hash first. It has never been retrained on the admitted datasets.
- A prototype of the architecture in section 5 was timed on this machine on 27 November under load from other work (load average about 18, GPU about 66% busy). In BF16 on the GPU, training processed about 115,000 step-tokens per second at size M, 48,000 at L and 25,000 at XL (batch 128 × 128 steps); one pass over 16 million steps takes about 2.3 minutes at M and 5.6 minutes at L. At batch 32, training was faster per step-token with 256 steps than with 128 (M 94,600 against 64,500; L 53,000 against 34,700). CPU FP32 training on 4 threads reached about 1,100 step-tokens per second at M; CPU FP32 forward passes (issuing) at 256 steps on 4 shared threads reached 6.9 windows per second at M and 2.35 at L. After 20 updates at size S, GPU FP32 parameters differed from CPU FP32 by a relative L2 of 3.6e-8 and GPU BF16 by 7.2e-5 (final loss 20.758 against 20.775); at size M after 12 updates, 2.3e-8 and 1.06e-4 (26.055 against 26.130). CPU FP32, GPU FP32 and GPU BF16 runs were each bitwise equal to a repeat of themselves. GPU outputs changed by 3.6e-6 to 4.0e-6 with batch shape; CPU outputs did not. Not measured: this architecture at 512 steps, CPU passes at size XL or larger, CPU passes on 16 threads, and any run without other load. Section 13 states how the estimates extend these measurements. For training, the amount of licensed data, not compute, limits the model; issuing forecasts one issue time at a time is the slow step.
- Counts checked from rosters and archive directories on 27 November are listed in `PROTOCOL.json` (`prior_facts`). Examples: the 66 Gait120 development people have 3,761 marker step segments over 7 tasks; Schreiber-Moissenet ordinals 1-30 have 685 walks and 30 static trials; every AJILE12 participant 03-07 has sessions 3 and 4.

### What was read to write this protocol

No evaluation value was decoded and this protocol downloaded no evaluation data. It used DANDI and figshare metadata (asset lists, digests, session dates, licences), the central directories of archives (member names, sizes, CRC-32) and the roster files of earlier studies. The licences of the Gait120, Schreiber-Moissenet, Moreira and Van Criekinge deposits and of every DANDI set used were read from the deposits on 27 November; the others come from earlier source records and are checked again at P2.

Two range reads of the end of Gait120 archive 53167640, made while the designs were drafted to list its members, also contained compressed (deflated) bytes of 23 marker files of participant S010 that sit just before the central directory: parts of StairAscent trials 2-5, all StairDescent steps and all StandToSit steps (the list is in `PROTOCOL.json`, `state_at_writing`). None of these bytes was inflated; the scripts that read the two files parse central-directory records only. Step P0 was done on 27 November: both private files were replaced by copies of archive bytes 1451983325-1452137137 (153,813 bytes: the central directory and the ZIP64 end records, no member byte; sha256 `499068f777e756f14588e4eec6f5a34720170e7637a56d5e3d3933806939554a` for both copies), and the originals (262,144 bytes, sha256 `4c36aec1d921b53556cb6b66dfd28123e2e32eb1e4fdbc40284e2f6c9fe1640d`, and 2,137,138 bytes, sha256 `1eff1b261eb5b4eab9f073da3091a8fa78ceddb8490dfae5c3f0f79fcd8652fa`) were deleted. The E1 member list recomputed from the copies is unchanged. E1 is scored on all members, and a predeclared sensitivity row repeats E1 without the steps of these 23 files.

## 4. Data

### 4.1 Qualification gate

A dataset, or part of one, enters the mixture only if all six checks pass and are recorded in `MIXTURE-MANIFEST.json` before the freeze.

- **Q1 Licence.** CC0, CC BY, ODC-By, MIT, CDLA-Permissive or PDDL, checked on the deposit page with the sha256 of the licence text. No share-alike data in public weights; non-commercial data may give scores only. Never the worm imaging deposit (Zenodo 10.5281/zenodo.19388374) or the SLEAP sample recordings.
- **Q2 Role.** Only units with a frozen training role in an existing protocol (fit, train, development or engineering), or never-assigned units that a published hash rule sends to training. Every validation, assessment, confirmation, final, test, held or reserved unit, every consumed evaluation group and every unit of a line that is in flight or on hold stays out.
- **Q3 Access.** Local, or reachable by per-file or byte-range reads that never decompress a reserved member.
- **Q4 Clock.** Streams count as paired only if they share one file with one clock, or a documented synchronisation that passes a check on training units. Otherwise they enter as separate acquisitions and are never paired within one window.
- **Q5 Labels.** Units and modality per channel; every value measured, derived or simulated. EMG is never labelled as a nerve recording.
- **Q6 Causality.** Author filtering (forward-backward filters, gap filling, zero-phase high-pass) is recorded. Features computed here use only samples at or before the end of each step.

### 4.2 Training mixture, wave 1

Every role below was read from a roster or manifest on disk. Unit lists and inner folds are in `ALLOCATION.json`; DOIs, licences, streams and checksums are in `PROTOCOL.json` (`data_sources`). Revision 3 corrects five entries so that they state the data as read at step P2: the Gait120, Katmah and Ofner rows and the two conditional members (section 16.1). The counts are in `MIXTURE-MANIFEST.json`.

| Dataset | Licence | Training units | Streams | Left out |
| --- | --- | --- | --- | --- |
| Gait120 (figshare 27677016 v1) | CC BY 4.0 | 66 development people: one recording per author step segment (3,761) and one static trial per person (66) | 39 markers at 100 Hz (author-filtered), OpenSim joint angles (derived), 12-channel EMG at 2 kHz, plate force for 3 tasks; the static trials hold markers only | validation 22, confirmation 22 (consumed); S001-S010 (E1) |
| Schreiber-Moissenet (figshare 7734767 v8) | CC BY 4.0 | ordinals 1-30: 685 walks, 30 static | 52 markers at 100 Hz, EMG at 1,500 Hz, plates | ordinals 31-40 (consumed), 41-50 (reserve) |
| Moreira (figshare 14241812 v1) | CC0 1.0 | 8 development people, 551 trials over 7 speeds | markers, EMG, plates | validation 4, confirmation 4 |
| İzmir (Aperta 286866) | CC BY 4.0 | 16 fit people and engineering person S01 (51 cycles) | markers | development 6, final 6 |
| Van Criekinge (figshare 24192480 v1) | CC0 1.0 | 12 fit people (36 walks) | markers, plates and 14 EMG channels at 1 kHz | validation 6, test 12, the never-assigned pool, stroke cohort |
| Katmah (PhysioNet r0ea-7161) | CC BY 4.0 | identifiers 1-40 at 0.5 m/s | three separate acquisitions, never paired within a window: 12-channel EMG envelope at about 16 Hz (derived; 38 people), IMU joint angles at 60 Hz (derived by the Xsens MVN model; 39 people) and treadmill force of 2 belts × 3 axes at 1,000 Hz (measured; 40 people) | identifiers 41-52 (consumed), 53-59 (reserved), other speeds |
| ds003739 (OpenNeuro 1.0.3) | CC0 1.0 | 18 development people × 4 sessions | 128-channel EEG at 256 Hz (author-preprocessed, derived), 10 EMG, 3 EOG, motion capture in one file | assessment 6 (consumed), reserve 6 |
| Ofner (Zenodo 834976) | CC BY 4.0 | S1-S7, motor-execution runs 1-10 | 61 EEG and 3 EOG at 512 Hz, and 27 arm and glove channels at 64 Hz (uncalibrated) in the same file; the arm and glove tokens are delayed by one 20 ms step (section 16.1) | S8-S12 (consumed, including their unopened runs 5-10), S13-S15 (reserve) |
| Hyser 2.0.0 (PhysioNet) | ODC-By 1.0 | 12 TRAIN people, 120 recordings of about 25 s | 256-channel HD-EMG at 2,048 Hz, finger force at 100 Hz | DEV 4 (consumed; never read), final 4 (never fetched) |
| HYGRIP (figshare 12383639 v1) | MIT | 7 eligible TRAIN groups | 24 EEG at 1 kHz, 4 unmapped EMG channels at 1 kHz, grip transducer volts at 50 Hz (uncalibrated) | /N (withheld by its timing gate), development 3, final 3 |
| CEMHSEY GRASP (Zenodo 15077957) | CC BY 4.0 | S1-S3, 12 pinch recordings | 320-channel HD-EMG at 2,048 Hz, MVC-normalised force at 200 Hz (sample offset unverified, flagged) | DEV S10-S13 and every other group |
| O'Doherty/Sabes (Zenodo 3854034 v2) | CC BY 4.0 | indy_20170131_02, loco_20170215_02 | spike events per electrode, finger position | indy_20161212_02 (reserved), August held days |
| W-track (DANDI 000978) | CC BY 4.0 | ER1, JS15, JS17 and JS14 data recorded before the start of trip 79 | sorted units (CA1, prefrontal cortex), position in cm | JS14 from trip 79 on; JS21, JS34, KL8 (consumed); both ZT2 files (closed) |

HYGRIP left-hand trials enter only after the same inter-Go clock screen (40 ms threshold) used for the right hand is passed on them. W-track files are read by HDF5 byte ranges, spike times and position only.

Conditional members of wave 1, as the audit of step P2 decided them:

- **Area2_Bump** (DANDI 000127, CC BY 4.0) is admitted: only the 290 trials of Han, 7 December 2017, that the area2 separate-day study used for fitting (218) and configuration (72). They give 458 inner-training windows. The 74 trials assessed in the original comparison and the laboratory's Dryad deposit stay out, because several Dryad sessions are consumed and the deposit repeats this laboratory's recordings.
- **FALCON M1** (DANDI 000941, CC BY 4.0) is not admitted. Its condition was "held-in-calib" days that no earlier evaluation scored, and the audit found no such day free (check Q2): 20120928 was scored by earlier project work, and 20120924, 20120926 and 20120927 are the candidate pool of a cross-session contract of a line on hold. No FALCON M1 recording was tokenised.

The mixture therefore has 14 qualified sources: the 13 of the table and Area2_Bump.

The IBL Brain-Wide Map stays with the earlier maintainer: no IBL subject, lab or session enters training or testing (section 14).

### 4.3 Wave 2 and exclusions

Wave 2 sources enter only if they pass Q1-Q6 before the freeze: HoloAssist (CDLA-Permissive-2.0, the 0.0 encoder's own source, not on disk), zebrafish DANDI 000235, Daily and Sports Activities p1-p4, WAY-EEG-GAL fit participants, EEG-EMG-WristMotion v3 TRAIN people, KIN-MUS UJI and IACKD training roles, Ofner motor-imagery runs of S1-S7, MC_RTT after a role audit and Katmah EEG after a clock check. Simulated windows from the physics-source track may enter only as a separately flagged add-on arm. No wave 2 source was qualified at P2, and from revision 3 none enters version 0.2 (section 16.1).

Left out, with reasons: all of AJILE12 (so that E2 is a dataset the model has never seen; participants 08-12 are also kept back for the earlier maintainer's AJILE12 line and are never downloaded by this track); every Jenkins recording (held out for E3); Nitschke and the pedal recordings (held by the earlier maintainer); the IBL Brain-Wide Map (stays with the earlier maintainer); LINK (sealed); FingerFlex (share-alike would bind the weights); MoVi, SUMediPose and AMASS (non-commercial); the worm and SLEAP recordings; KIT, NEMO, Senden, the Harvard camera dataset, the external paired walk and Flint (licence unclear or held); CMU motion capture (non-standard terms); reach_grasp_v1 (no licence found locally); the Van Criekinge pool owned by the walking-scale and physics-source protocols.

### 4.4 Counting

`MIXTURE-MANIFEST.json` records per dataset: individuals, sites, recordings and sessions, tasks and conditions, unique 20 ms steps, non-overlapping 1.2 s windows, channel-seconds per modality, spikes, and the derived and simulated flags. The design estimates were 8 to 30 million steps; the manifest replaces them before any model choice. The count made at P2 is 8,312,952 unique steps and 135,840 windows from 227 individuals over the 14 qualified sources (section 13). The top model size must be justified by inner validation, not by the size of the mixture.

## 5. Model

### 5.1 Representation

- 20 ms causal steps with six group slots: spikes, field (EEG, ECoG), EMG, kinematics (markers, keypoints, joint angles, IMU, hand or cursor), force, and a context token.
- Spikes: counts per unit per step, kept as raw counts. Field: per channel, causal log band power over the trailing 100 ms or 200 ms (chosen by inner folds) in 4-8, 8-13, 13-30 and 70-150 Hz (the last band masked below 400 Hz sampling), plus a causal 10 Hz low-pass value. EMG: log RMS within the step after a causal 20 Hz high-pass; shipped envelopes (Katmah) are used as given and labelled derived. Kinematics: the last sample in the step and its change from the previous step, positions relative to a window anchor at the last input step (pelvis-marker mean for body marker sets, shoulder mean for upper-body keypoints, the point itself for single trackers). Force: last sample and within-step mean.
- Channel identity: for a group with channels c, the read-in matrix is W[c] = E(c)·P with rank 32, applied to x and to gelu(x), with a presence term and LayerNorm. Shared named vocabularies cover muscles with side, anatomical markers and keypoints, joints with axis, 10-10 EEG sites, force axes, and IMU segment and axis. Spike units, ECoG electrodes, HD-EMG electrodes and unmapped EMG channels get learned rows per recording, with a coordinate network where electrode positions exist. New people with named channels need no new parameters.
- Normalisation: per-channel z-scores from training units only; test sets use their adaptation data.
- Context token: dataset, species, task, body plan and a measured / derived / simulated flag. During training the dataset id is replaced by an "unknown dataset" id with probability 0.1, so that unseen datasets have a trained token.
- Missing groups and channels are key-masked.
- Augmentation: with probability 0.2 a 3D marker window is replaced by a random orthographic 2D projection of its landmarks (azimuth 0-360°, elevation −20° to +40°), flagged derived. This exposes the encoder to 2D keypoint-like inputs without using any AJILE12 data.

### 5.2 Architecture

One transformer layer fuses the group tokens of each step (absent groups masked); the step token is the mean of the present group tokens. A pre-LayerNorm causal transformer with rotary position embedding then runs over the step tokens. GRU and hybrid (transformer plus a GRU state token carried between windows) cores are arms. Heads map each group and horizon to 32 dimensions and take dot products with an output identity row per channel, so any channel set can be forecast.

| Size | Width | Layers | Heads | Core parameters |
| --- | ---: | ---: | ---: | ---: |
| XS | 64 | 4 | 2 | 0.29M |
| S | 128 | 6 | 2 | 1.47M |
| M | 256 | 8 | 4 | 7.27M |
| L | 384 | 12 | 6 | 23.3M |
| XL | 512 | 16 | 8 | 53.9M |
| XXL | 768 | 16 | 12 | 121M |

XXL runs only if XL beats L by at least 1% relative on the selection score. Context length T is 64, 128, 256 or 512 steps, chosen by inner folds; shorter segments are padded and masked (the Gait120 training step segments counted at P2 last 0.86 to 3.27 s with a median of 1.26 s, where revision 2 expected 1.5-1.65 s; ds003739 sessions last 10 minutes).

### 5.3 Objective

- Causal forecasting of every present channel at 20, 100 and 200 ms (h = 1, 5 and 10 steps), plus 500 ms for kinematics.
- Spikes: Poisson negative log-likelihood of counts; h = 1 is next-neuron prediction. Continuous groups: Huber loss (δ = 1) on the change from the latest value, in normalised units.
- Each present group is dropped from the input with p = 0.25 (at least one measured group kept) but stays a target, and dropped groups are also reconstructed at h = 0. This trains the cross-modal translations the task readouts need (EMG to kinematics, spikes to kinematics). Channel dropout is 0.15.
- Each group's loss is divided by its baseline loss on the training mixture (persistence, or the per-unit mean rate for spikes); groups and horizons have equal weight.
- Datasets are sampled with probability proportional to N_d^τ, where N_d is the number of individuals, with τ ∈ {0, 0.5, 1} chosen on leave-one-dataset-out folds and no dataset above 25% of examples. Within a dataset, individuals are sampled uniformly, recordings in proportion to duration and crop starts uniformly.

### 5.4 Training loop and records

- AdamW (β 0.9/0.95, weight decay 0.05 on matrices), 2% linear warmup then cosine decay to 10% of the peak. Peak learning rate 6e-4 (XS), 5e-4 (S), 3e-4 (M), 2e-4 (L), 1.5e-4 (XL, XXL). Batch 128 windows × T steps. Gradient clip 1.0, dropout 0.1, stochastic depth 0.1 for XL and XXL. One pass is a number of step-tokens equal to the unique steps of the mixture in use.
- Data order is fixed by salted sha256 per dataset; the sampler draws from counters keyed by sha256 of the seed, update and slot, and its state is saved in every checkpoint. Seeds 20261127, 20261128 and 20261129.
- `torch.use_deterministic_algorithms(True)`, `torch.utils.deterministic.fill_uninitialized_memory = False`, the math attention kernel on the GPU and fixed batch shapes.
- Record chain per run: LOCK (source, array and script sha256) → ATTEMPT → FP32 checkpoint with optimiser and sampler state → reload-equality check → RESULT (sha256, wall time, peak memory, threads, versions) → READBACK.
- At most 16 threads in total, pinned within CPUs 16-31. The GPU is shared with other workflows' browser tests, which have priority.

### 5.5 Precision

- Tier 1, CPU FP32: the reference route; every forecast that enters a set-pass rule is issued with it.
- Tier 2, GPU FP32 with math attention: the reference training route up to M (L if time allows).
- Tier 3, GPU BF16 autocast with FP32 master weights and optimiser: the ladder, the arms and XL and above.
- BF16 is accepted only if matched full runs at S and M (BF16 with 3 seeds, GPU FP32 with seed 20261127, same data order) differ by at most max(1% relative, the 3-seed spread) on the selection score and the inner-validation readout metrics. Otherwise the final runs use GPU FP32.
- Every forecast that enters a set-pass rule (the E1 and E2 scoring windows with primary inputs, for 0.2 and every set-pass control) is issued in FP32 on the CPU from an FP32 export at a fixed batch shape of 32.
- All other encoder passes run on the GPU in FP32 with the math attention kernel and fixed padded shapes: the adaptation windows from which adapters and readouts are fitted, E3, the secondary inputs, the wrong-pairing rows, the secondary arms and the quantity-versus-diversity arms. For each encoder, 1,000 of these windows (drawn by ascending sha256 of `pooled-encoder-0.2|cpu-check|` + encoder + `|` + set + `|` + window id, in equal shares over the sets) are repeated in FP32 on the CPU, and the largest absolute and relative differences are reported. If an encoder's largest relative difference (the largest absolute feature difference divided by the largest absolute CPU feature value over the same windows) exceeds 1e-4, all of that encoder's passes are repeated on the CPU. Revision 1 issued everything on the CPU; section 13 shows that this would take weeks at a 512-step context.
- E1 primary inputs lie inside one step segment, so E1 primary passes use a fixed length of min(T, 128) steps, left-padded and masked as in training; an E1 issue with more than 128 input steps uses T. Revision 2 expected Gait120 step segments to hold at most 83 steps of 20 ms. The 3,761 training segments counted at P2 hold 43 to 163 steps (median 63), and 10 of them hold more than 128. The lengths of the E1 segments are not known, because no E1 file has been read; the rule above covers every length. Because padding is masked and the position embedding is relative, this is the same function as padding to T in exact arithmetic; a CPU check on 1,000 Gait120 inner-validation windows reports the largest difference before the freeze.
- One arm is repeated with identical settings to report GPU run-to-run variation.

## 6. Model choice inside the training people

- Inner folds (computed by `allocate.py`): the training units of each dataset are ranked by ascending sha256 of `pooled-encoder-0.2|fold|` + dataset + `|` + unit; fold = rank mod 5; fold 0 is inner validation. Datasets with fewer than three independent units (O'Doherty/Sabes, area2) use five equal time blocks per recording, the latest block being inner validation. For example, the Gait120 inner-validation people are S108, S033, S036, S115, S050, S011, S092, S046, S098, S104, S066, S020, S119 and S053, and the W-track inner-validation rat is JS14.
- Selection score: for each dataset, the mean over its present groups of (model loss / baseline loss) on its inner-validation units, with identity rows for new units fitted on the first half of each inner-validation recording and the score taken on the second half; then the mean over datasets with equal weight. Lower is better.
- Choices, in this order:
  1. τ by leave-one-dataset-out at size M (transformer, T = 256, seed 20261127, 2 passes): each wave-1 dataset is left out in turn, adapted on its inner-training units and scored on its inner-validation units.
  2. Size and number of passes: ladder XS to XL, up to 40 passes, a checkpoint every 2 passes; the lowest selection score wins.
  3. Core: transformer, GRU and hybrid at M and L; another core replaces the transformer only if it is better by at least 1% relative at both sizes.
  4. Context: T ∈ {64, 128, 256, 512} and field window ∈ {100, 200} ms at size M.
  5. XXL only under the rule in section 5.2.
  6. The ridge control's history T_r, from the same candidates {64, 128, 256, 512} steps and by the same inner folds (section 8.2). This choice uses no encoder and is made before the freeze.
- Ties within 0.5% relative go to the smaller or simpler option. The final model trains on all training units with the chosen configuration and number of passes, 3 seeds.

## 7. Fresh evaluation

No set below spends a reserve owned by an earlier protocol. Using a set makes its units consumed for all later work; the lead decided to spend E1, E2 and E3 once (section 14).

### 7.1 E1, Gait120 S001-S010 (primary; seen dataset, unseen people)

- These 10 people were left out of the chair-rise roster because they lack source-aligned plate data, and their archive (figshare file 53167640) was never fetched by an earlier study. The 1,198 members used (TRC markers, OpenSim joint-angle MOT, RawData.mat; 759,080,170 compressed bytes) are listed with CRC-32 in `ALLOCATION.json`.
- Adaptation: adapters and ridge are fitted on the 66 Gait120 development people (all 7 tasks, same targets), with penalties chosen by five person folds of those people. No per-person calibration.
- Issue times: every 50 ms from 0.5 s after the start of each step segment, while the +200 ms target frame lies inside the segment.
- Primary inputs: past markers of the segment, relative to the pelvis centre at the last input frame. Secondary: markers plus 12-channel EMG, for people whose EMG passes the trial timestamp and frame-identifier check used for training people, with EMG scaled per person from that person's LevelWalking Trial01.
- Targets: displacement of LASI, RASI, LPSI, RPSI, LKNE, RKNE, LANK, RANK, LHEE, RHEE, LTOE and RTOE from the last input frame to +100 ms and +200 ms, in mm. Secondary targets: OpenSim joint angles (derived, degrees) and the EMG log envelope at +100 ms.
- Primary metric: the mean over the 12 markers and both horizons of the 3D Euclidean error, mm. Windows are averaged within a step, then trials, then the 7 tasks with equal weight, then people.
- LevelWalking Trial01 (the EMG scaling trial) and static trials are not scored in any arm. Eligibility (all 12 target markers finite at the last input frame and both target frames) is applied identically to every method.
- Sensitivity: E1 repeated without the steps of the 23 S010 files of section 3.

### 7.2 E2, AJILE12 participants 03-07 (primary; unseen dataset, unseen people)

- DANDI 000055, version 0.220127.0436, participants 03, 04, 05, 06 and 07. For every participant, session 3 is the calibration session and session 4 the scoring session (asset ids, sizes and sha256 in `ALLOCATION.json`). Other sessions are never opened. Pose series, and for the secondary input the ECoG of the needed windows only, are read by HDF5 byte ranges.
- Participants 08-12 are kept back for the earlier maintainer's AJILE12 line. This track never downloads or opens any of their files, and `ALLOCATION.json` lists none of their assets.
- With 5 people, the set-pass rule needs at least ceil(0.7 × 5) = 4 of 5 people improved (section 10). This threshold is fixed in this revision, before any AJILE12 byte is read.
- Adaptation: adapters and ridge on the pooled calibration sessions, penalties by leave-one-participant-out over the 5 calibration sessions; ECoG identity rows per participant from that participant's calibration session.
- Windows: issue frames drawn by sha256 of `pooled-encoder-0.2|ajile12|` + participant + `|ses-` + session + `|` + k, kept if eligible and at least 2 s from every accepted issue time, 600 per session. Let j be the first frame after the last prior frame (the first unseen frame). Eligible: at least 10.24 s after the session start; the 15 prior frames (j − 15 to j − 1) have finite shoulders and finite wrist, elbow and shoulder of both arms; the shoulder frame passes the earlier next-person thresholds (width w ≥ 1 pixel, |mean shoulder vector| ≥ 0.5 w, |vertical component of the perpendicular| ≥ 0.10); both wrists finite at frames j + 7 and j + 14, which are 8 and 15 frames after the last prior frame. Secondary windows: native ReachEvents onsets of the scoring session under the earlier next-person selection rule.
- Primary inputs: past pose (wrists, elbows, shoulders, ears, nose) resampled to 20 ms steps by the last sample in each step, in the shoulder frame built from the 15 prior frames only and divided by the shoulder width. Secondary: pose plus ECoG band power, compared with ECoG taken 60 s earlier.
- Targets: contralateral and ipsilateral wrist displacement 0.267 s and 0.500 s after the last prior frame, in shoulder widths. The contralateral side follows the session's native ReachEvents description and the published implant hemisphere.
- Primary metric: the mean over both wrists and both horizons of the 2D Euclidean error, in shoulder widths (normalised image units). The pose comes from a separate DeepLabCut model for each participant and its published unit conversion is undefined, so no millimetre values are reported.

### 7.3 E3, MC_Maze full and Large (secondary; one animal)

- DANDI 000128 (recorded 25 September 2009, training file 690,612,247 bytes) and DANDI 000138 (6 October 2009, 148,590,536 bytes). Neither date matches the Jenkins sessions of DANDI 000070 (12, 16, 18 and 23 September) nor MC_Maze Small (28 September) or Medium (29 September, consumed). The desc-test files are never opened.
- Per session: identity rows for units and the ridge readout on the NLB "train" trials (penalties by 5 trial folds); scoring on the NLB "val" trials, every 50 ms from 250 ms after the trial start while the target lies inside the trial.
- Primary inputs: past spikes (at least 200 ms, up to the chosen context) and past hand position; secondary: spikes only. Target: 2D hand displacement at +100 ms, mm. Secondary metric: next-step spike log-likelihood in bits per spike.
- Uncertainty: trial bootstrap stratified by session. E3 is always secondary and never enters H1.

### 7.4 E4 is dropped

E4 (IBL held-out labs) is not run. The IBL Brain-Wide Map stays with the earlier maintainer, so no IBL subject, lab or session is used for training or testing (section 14).

### 7.5 Secondary sets

- **B1** is not run: the unopened tasks of the 44 Gait120 validation and confirmation people stay unopened (section 14).
- **A4:** Camargo et al. lower-limb biomechanics as a whole held-out dataset, only under a later protocol version written after a person-overlap check against the consumed Georgia Tech record 10.35090/gatech/70296 and a licence check.
- **Seen-dataset arm** (optional, if GPU time allows): 0.2 continued on AJILE12 sub-01 session 3 only and scored on E2 only, to measure what seeing the dataset adds. Reported whatever the result.
- **Published tasks:** the 0.0 task readouts refitted on 0.2, reported only as a development comparison on previously used people.

Not used: a Van Criekinge group (the walking-scale allocation offers none to this track) and W-track ZT2 (closed).

## 8. Adapters and controls

### 8.1 Adapters (identical budget for every encoder)

Channels are mapped onto the shared vocabularies where their names allow. Rows for unnamed channels are trained for 500 AdamW updates at learning rate 3e-3 with the encoder frozen. The readout is ridge regression on the frozen issue-step features, with the penalty chosen from {1e-3, 1e-2, 0.1, 1, 10, 100, 1000} by the folds of each set's adaptation units. LoRA of rank 8 with 200 updates is a predeclared secondary arm. Released readouts are separate files that record the sha256 of their parent encoder.

### 8.2 Controls

The same adapter budget, seeds, data order and scored rows apply to every method on every set.

- **Persistence:** zero change.
- **Linear trend:** E1, least-squares line over the last 100 ms of each target marker; E2, endpoint velocity of the 15 prior frames (last minus first, scaled by 8/14 or 15/14); E3, least-squares line over the last 100 ms.
- **Ridge:** on the per-step input features of the last T_r steps, target the change from the last value. T_r is chosen from the same candidates as 0.2's context, {64, 128, 256, 512} steps, by the same inner folds: on each wave-1 training dataset, a ridge fitted on its inner-training units forecasts the change of every present continuous channel at the objective horizons (spike counts are inputs, not targets), with the penalty chosen from the adapter grid by the folds of the inner-training units; its selection score (section 6) is taken on the inner-validation units; the T_r with the lowest mean over datasets is used on every set, and ties within 0.5% go to the shorter history. Steps before the start of the available input (for example before a step segment) are zero-filled and marked by a presence flag per step, as 0.2 masks them. Penalties for each set are then chosen as for the adapters.
- **Frozen 0.0:** the movement-weights.npz encoder, frozen, with a 4-token adapter that maps each 80 ms chunk of the last 16 steps to its 6 inputs (trained with a linear head for 500 updates at 3e-3), then the ridge readout on its final-token features. joint_alpha is not used, because it was trained on the worm and SLEAP recordings.
- **Random encoder:** the 0.2 architecture at the final size, initialised with seed 20261127 and never trained.
- **Scrambled 0.2:** every weight tensor of 0.2 with its entries permuted by a fixed permutation (seed 20261128).
- **Single-source encoders:** a size-M encoder per wave-1 source at the arm budget (a screen). The best by selection score and the nearest source of each set (E1 Gait120, E2 Ofner, E3 O'Doherty/Sabes) are retrained at the final 0.2 size and token budget on all their training units (seed 20261127), keeping the checkpoint with the best score on their own source's inner validation. Both the best single-source encoder and the set's nearest single-source encoder are required controls in that set's pass rule (section 10); when they are the same source, it counts once.
- **Scratch size S:** a size-S model trained from random initialisation on the set's adaptation data only (2,000 updates at 5e-4, batch 32), then the ridge readout.
- **Matched history:** frozen 0.0 over the last 16 steps (320 ms), and 0.2 also scored on the same 320 ms history.
- **Task specialists (H3 only):** E1, the chair-rise attention recipe refitted on the 66 development people with E1 targets; E2, the next-person pose ridge recipe with penalty 1 on the calibration sessions; E3, the NeuroTranslate 0.1 eight-pass neural-maze model refitted on each session's train trials.
- **Wrong pairing:** every neural or EMG input is also replaced by the same stream from another time (E1 EMG from the previous step of the same trial, E2 ECoG 60 s earlier, E3 spikes from the next val trial).

## 9. Metrics and uncertainty

- Errors are in physical units where they exist (mm for E1 and E3) and in shoulder widths for E2.
- Within an individual, windows are averaged, then trials or segments, then tasks; each person or animal then has equal weight.
- Each individual's relative error R = error / persistence error is reported with the physical error. The composite is the mean over the two primary sets (E1 and E2) of the set mean R; E3 is reported separately.
- 0.2 and every three-seed control are scored per seed, and each individual's error is averaged over seeds. Forecasts are not ensembled.
- Uncertainty: paired bootstrap over individuals, 10,000 resamples, seed 20261127, 95% percentile intervals, with the number of individuals improved and the range when one individual is left out. E3 uses a trial bootstrap stratified by session. For the composite, individuals are resampled independently within each set.

## 10. Success rules

Fixed before any evaluation byte is read.

- **Set pass (E1, E2).** 0.2 passes a set if, against every one of persistence, linear trend, ridge, frozen 0.0, the random encoder, the fold-chosen best single-source encoder and the set's nearest single-source encoder (Gait120-only for E1, Ofner-only for E2), the mean paired difference (0.2 minus control) is below 0 with the bootstrap 95% upper bound below 0, and at least ceil(0.7 n) of the n individuals have a lower 0.2 error than that control: 7 of 10 people for E1 and 4 of 5 people for E2.
- **E3 result (secondary).** The same controls with the Sabes-only encoder as the nearest single source. With one animal, the upper bound comes from the trial bootstrap stratified by session, and the individual count is replaced by a lower 0.2 error than the control in both sessions. E3 is reported with this rule and never enters H1.
- **H1 (the pooled encoder helps on new people).** E1 passes and E2 passes. H1 needs both sets to pass, an intersection-union test, so no multiplicity adjustment is needed. Each set is reported separately.
- **H2 (diversity at matched windows).** The composite R of the D_all arm at W_max minus the mean composite R of the Q arms at W_max is below 0, with the bootstrap 95% upper bound below 0.
- **H3 (task specialists).** Per set, 0.2 against the specialist under that set's criteria above, reported per set with no overall claim.
- **Floors.** E1 is scored only if at least 8 of its 10 people, and E2 only if at least 4 of its 5 people, have at least 50 eligible windows; otherwise the set is reported as insufficient and counts as not passed.
- Everything else is secondary and reported whatever the result. If H1 fails, the result is stated as no evidence that the pooled encoder improves forecasts for new people over the listed controls. Given the history of 0.0, a null result is the expected outcome and will be reported as such.

## 11. Quantity versus diversity

All arms use the size-M transformer with the chosen τ and context, crops of 60 steps aligned to the counted windows, batch 128 and U = 40 × W_max / 128 updates, so every arm sees the same number of steps × batch. Effective passes are reported.

Revision 3 corrects the rule for the D arms (section 16.1); the other rules are those of revision 2. The values below were computed at P2 from the counted training data. They are recorded in `MIXTURE-MANIFEST.json` and `D-ARM-ORDERS.json`, and `run/check_d_arm_orders.py` recomputes the D arms from the published rules and the counts. No arm has been run.

- **W_max** is the smallest number of unique inner-training windows in any Q anchor, rounded down to a power of 2. The anchors have 2,072 (Gait120), 13,532 (Ofner), 29,004 (ds003739) and 51,772 (W-track) windows, so W_max is 2,048 and U is 640 updates. Gait120's 2,072 windows are 1,923 from step segments and 149 from the static trials of its 52 inner-training people. Static trials are training-role recordings, so they count under the rule as written. Their windows hold markers only (no EMG, no force).
- **Q arms (more data from one source):** anchors Gait120, ds003739, Ofner and W-track, each at W_max/16, W_max/4 and W_max windows (128, 512 and 2,048) drawn in a fixed hash order. The Gait120 arm at W_max uses 2,048 of its 2,072 windows. Every Q-arm report gives the number of static-trial windows drawn at each level.
- **D arms (more sources at the same windows):** k ∈ {2, 4, 8} sources, 3 hash-ordered draws each. A source is eligible if it has at least W_max/8 = 256 unique inner-training windows. It enters a k-source arm only if it has at least W_max/k: 1,024 for k = 2, 512 for k = 4 and 256 for k = 8. For each k and draw, the order of that draw in `D-ARM-ORDERS.json` is walked from the top. A source that is not eligible, or that has fewer than W_max/k windows (short for this k), is skipped, and the first k sources that remain form the arm. Each gives its first W_max/k unique windows in the fixed hash order, so every D arm has exactly 2,048 unique windows, as each Q arm at W_max does. A skipped source stays available to the arms with a larger k and to D_all.
- **D_all** uses every eligible source: 11 sources at floor(2,048 / 11) = 186 unique windows each, 2,046 in total, 2 fewer than W_max, with the same U = 640 updates. The "D_all arm at W_max" of H2 (section 10) is this arm.
- **P arms (more people within one source at the same windows):** Gait120 with 3, 13 or 52 inner-training people and ds003739 with 2, 4 or 14, at W_P windows (the largest power of 2 not above W_max/4 and the windows of the smallest level). W_P is 64 for Gait120, whose levels have 105, 488 and 2,072 windows. W_P is 512 for ds003739, whose levels have 4,188, 8,284 and 29,004 windows, so W_max/4 sets it.
- Seeds 20261127, 20261128 and 20261129: 36 Q, 27 D, 3 D_all and 18 P runs, 84 in total.
- Before any W_max run, a power law through each Q anchor's inner-validation scores at W_max/16 and W_max/4 predicts its W_max score. The prediction file is hashed and its sha256 recorded before the W_max runs start.
- Every arm is scored on inner-validation units (in distribution) before the freeze, and on E1 and E2 after it, with the standard adapters.

Unique inner-training windows of each qualified source, and the D arms it can enter (identifiers as in `D-ARM-ORDERS.json`):

| Source | Identifier | Inner-training windows | D arms it can enter |
| --- | --- | ---: | --- |
| W-track | `wtrack` | 51,772 | k = 2, 4, 8 and D_all |
| ds003739 | `ds003739` | 29,004 | k = 2, 4, 8 and D_all |
| Ofner | `ofner` | 13,532 | k = 2, 4, 8 and D_all |
| Katmah | `katmah` | 4,664 | k = 2, 4, 8 and D_all |
| HYGRIP | `hygrip` | 4,527 | k = 2, 4, 8 and D_all |
| Gait120 | `gait120` | 2,072 | k = 2, 4, 8 and D_all |
| Moreira | `moreira` | 1,982 | k = 2, 4, 8 and D_all |
| Hyser | `hyser` | 1,800 | k = 2, 4, 8 and D_all |
| O'Doherty/Sabes | `sabes` | 1,281 | k = 2, 4, 8 and D_all |
| Schreiber-Moissenet | `schreiber_moissenet` | 897 | k = 4, 8 and D_all |
| Area2_Bump | `area2` | 458 | k = 8 and D_all |
| CEMHSEY GRASP | `cemhsey` | 200 | none (below 256) |
| Van Criekinge | `van_criekinge` | 52 | none (below 256) |
| İzmir | `izmir` | 31 | none (below 256) |

The nine D arms as the rule gives them, with the sources in the order they are taken:

| Arm | Sources | Windows per source | Skipped while walking the order |
| --- | --- | ---: | --- |
| k = 2, draw 0 | `ofner`, `katmah` | 1,024 | none |
| k = 2, draw 1 | `sabes`, `ofner` | 1,024 | `area2` (458 windows, short for k = 2) |
| k = 2, draw 2 | `hygrip`, `katmah` | 1,024 | `area2` (short for k = 2) |
| k = 4, draw 0 | `ds003739`, `katmah`, `gait120`, `schreiber_moissenet` | 512 | `izmir` (not eligible), `area2` (short for k = 4) |
| k = 4, draw 1 | `ofner`, `gait120`, `ds003739`, `hygrip` | 512 | `cemhsey` (not eligible) |
| k = 4, draw 2 | `ds003739`, `ofner`, `hyser`, `sabes` | 512 | `van_criekinge` (not eligible) |
| k = 8, draw 0 | `sabes`, `area2`, `gait120`, `hyser`, `moreira`, `ofner`, `ds003739`, `wtrack` | 256 | `izmir`, `cemhsey` (not eligible) |
| k = 8, draw 1 | `ofner`, `wtrack`, `moreira`, `schreiber_moissenet`, `hyser`, `sabes`, `ds003739`, `gait120` | 256 | `van_criekinge`, `cemhsey` (not eligible) |
| k = 8, draw 2 | `sabes`, `ofner`, `katmah`, `schreiber_moissenet`, `wtrack`, `area2`, `ds003739`, `hyser` | 256 | `van_criekinge` (not eligible) |

Every arm in this table has 2,048 unique windows. D_all has the 11 eligible sources of the first table at 186 windows each.

Limits that the counts set, stated here so that the results are read with them:

- W_max = 2,048 rests on Gait120 by a margin of 24 windows, and 149 of Gait120's 2,072 windows come from static trials, which hold markers only. Its step segments alone give 1,923 windows, which would round down to 1,024.
- The pool of sources differs with k. The k = 2 arms draw only from the 9 sources with at least 1,024 windows, the k = 4 arms from 10 (Schreiber-Moissenet added) and the k = 8 arms from all 11 (Area2_Bump added). Small sources therefore appear only in the wider arms, so a difference between k levels can also reflect which sources were available.
- D_all has 2,046 unique windows, 2 fewer than the Q arms at W_max that H2 compares it with.
- W_P is 64 windows for the Gait120 P arms, because the 3-person level has only 105 windows. This small budget is a limit of those arms; the rule is not changed.
- CEMHSEY GRASP, Van Criekinge and İzmir have fewer than 256 inner-training windows. They enter no D arm and not D_all, and they stay in the main training mixture.
- 1,383 of the 3,761 Gait120 step segments are shorter than one 1.2 s window. They give training steps but no counted window, so Gait120's window count understates its training steps.

## 12. Leak checks

- Subject identifiers of every training list are disjoint from every evaluation list (checked by script before the freeze).
- File hashes are disjoint, and content hashes are compared across derived caches and original files (for example area2 against the Dryad deposit).
- Every evaluation file is downloaded after the freeze commit, and its timestamp is recorded.
- No evaluation file path appears in any LOCK file before the freeze.
- The download records contain no file of AJILE12 participants 08-12 and no IBL file (checked at the freeze and again after scoring).

## 13. Steps, compute and time

| Step | Work | Estimate |
| --- | --- | --- |
| P0 | This protocol, separate review, lead commit; central-directory-only copies of the two tail files (done on 27 November, section 3) | 0.5-1 day |
| P1 | Training downloads, paced and ranged where possible: Ofner S1-S7 runs 4-10 (49 files, 4.44 GB), ds003739 sessions 1-3 of the 18 development people (54 recordings, 5.24 GB), Gait120 development TRC/MOT (426.5 MB), W-track spike times and position (about 1-2 GB), Katmah force plates; conditional sources measured first | 5-7 h |
| P2 | Readers (MATLAB table objects, NWB, C3D, GDF, WFDB, EEGLAB, HDF5) in an own environment, tokenisation, role audits of area2 and FALCON M1, Q1-Q6 records, `MIXTURE-MANIFEST.json` with the re-estimate below | 1.5-2.5 days CPU |
| P3 | Real-mixture parity 1-2 h; τ 4-6 h; ladder XS-XL about 14 h; core arms about 4 h; context arms 2-4 h; XXL +10.5 h only if earned | 25-41 GPU-hours at 16 million steps |
| P4 | Matched BF16 and FP32 runs at S and M | about 10 GPU-hours at 16 million steps |
| P5 | Quantity and diversity arms, sealed prediction, in-distribution scoring | 1-3 GPU-hours. W_max is 2,048 windows, as computed at P2: Gait120 has 2,072 inner-training windows, where revision 2 expected about 3,000 (section 11) |
| P6 | Final 0.2, 3 seeds | at T ≤ 256: L about 11 h, XL about 21 h, L in FP32 about 42 h; at T = 512: up to about 22 h (L), 42 h (XL) and 84 h (L in FP32) |
| P7 | Single-source screen (about 2 h) and full-size retrains of up to 4 sources (the best and the three nearest), random and scrambled encoders, specialists | 14-31 GPU-hours at T ≤ 256 (L or XL); up to about 60 at T = 512 |
| P8 | Freeze: the lead commits `FREEZE.json` with the sha256 of every weight file, adapter and scoring script; then evaluation downloads (Gait120 S001-S010 members 759 MB, MC_Maze 839 MB, AJILE12 participants 03-07 by ranged reads, about 4-6 GB, measured on the first session) | 2-5 h |
| P9 | Adapters; CPU FP32 issuing of the scored E1 and E2 windows; GPU FP32 passes for everything else, with the CPU check (section 5.5); scoring, bootstrap, reports, separate reader | CPU issuing at T ≤ 256: 2-8 h (L), 6-19 h (XL); at T = 512: 4-15 h (L), 9-34 h (XL), up to about 77 h (XXL). GPU passes at T ≤ 256: 1.5-10 h (L), 3.5-24 h (XL); at T = 512: 5-38 h (L), 11-91 h (XL). Then about 1 day for scoring, reports and the reader |

Total: about 60-130 GPU-hours and 7-11 calendar days including reviews at the central assumptions (16 million unique steps, T ≤ 256, final size L or XL). At the low end (8 million steps, size L) the GPU total is about 35 hours; at the high end (30 million steps, T = 512, size XL) it rises to about 370 hours and about 4 weeks. Disk on /home stays under 26 GB (tokens 3-6 GB, checkpoints under 5 GB); raw files are transient in RAM-backed temporary space. Every download records the URL, byte range, bytes and sha256. Training and downloads start only after a separate reviewer admits this protocol and the lead commits it.

How the estimates were made, and how uncertain they are:

- **GPU training.** The measured BF16 rates at 128 steps and batch 128 (section 3) are multiplied by 40 passes of 16 million steps; for example one L seed takes 40 × 5.6 min. At batch 32, the 256-step runs were faster per step-token than the 128-step runs, so the 128-step rates are used for T ≤ 256. No run at 512 steps was measured. At widths 384-512 the attention share of the arithmetic rises from about 4-5% at 128 steps to about 14-18% at 512 steps, and the math attention kernel stores score tensors that grow with the square of T, so a 512-step run is taken to cost 1 to 2 times as much per step-token. This factor is an estimate, not a measurement.
- **Mixture size and passes.** Every training figure scales linearly with the unique steps of the mixture (design range 8-30 million, so 0.5 to 1.9 times the figures above) and with the number of passes the folds choose (at most 40). The mixture counted at P2 has 8,312,952 unique steps, 0.52 times the central assumption of 16 million and close to the low end of the design range. The figures in the table are not recomputed here; the re-estimate below does that.
- **Padding.** Segments shorter than T are padded, and padded positions cost compute without adding steps. As counted at P2, the Gait120 training step segments hold 43 to 163 steps with a median of 63 (revision 2 assumed about 80). When each recording is cut into rows of T steps, the padded share of the Gait120 rows is 28.7% at T = 64, 48.5% at T = 128, 73.7% at T = 256 and 86.9% at T = 512. Over all 14 qualified sources it is 2.1%, 4.3%, 10.6% and 22.5%. These shares are not included in the figures above.
- **Load.** All rates were measured with the GPU about two-thirds busy with other work and a load average of about 18. Quieter or busier periods can change every time by about ±50%.
- **CPU issuing.** The measured forward rates (6.9 windows per second at M and 2.35 at L, 256 steps, 4 shared threads) are scaled by core parameters to XL (about 1.0 window per second) and XXL (about 0.45), by 1 to 3 times for 16 threads (not measured) and by 1/1.3 to 1/1.1 for the attention share at 512 steps. The kinematic anchor moves with each issue time, so every issue time needs its own encoder pass. Counts per final-size encoder: E1 about 9,700-11,400 scored windows (about 570 step segments × 17-20 issue times) and about 64,000-75,000 adaptation windows per input variant; E2 3,000 scored and 3,000 calibration windows per input variant; E3 about 24-54 issue times per trial (for trials of 1.5-3 s; their lengths are unknown until the freeze) over 2,795 train and val trials. Seven final-size encoders are scored on each set: 0.2 with 3 seeds, the random and scrambled encoders, and the best and the nearest single-source encoders. The E1 counts assume step segments of 1.5-1.65 s. The training segments counted at P2 are shorter (median 1.26 s), so if the E1 segments are similar, E1 has fewer issue times per segment than assumed. The E1 counts are not recomputed, because no E1 file has been read.
- **Why the issuing route changed.** Issuing every pass on the CPU, as revision 1 required, would take about 45-450 hours at size L with T ≤ 256 and about 200-1,200 hours at T = 512, mostly for E3 and the adaptation windows. Revision 2 keeps every forecast that enters a set-pass rule on the CPU and moves the rest to GPU FP32 with a CPU check (section 5.5).
- **Re-estimate.** Before any model choice, `MIXTURE-MANIFEST.json` records the counted unique steps and the padded share at each T, a 512-step GPU throughput measurement and a 16-thread CPU issuing measurement at sizes M and L on training data, and P3-P9 recomputed from them. The counted steps and the padded shares are in the manifest now. The two measurements and the recomputed times are not made yet; they come before any model choice. The speed trial named in section 16.1 ran at 64 steps and size XS and is neither of them.

## 14. Decisions on the items left to the owner

The project owner's instruction of 27 November 2026 to continue training the models, given with the owner's standing pre-approval to add any openly licensed dataset at the maintainers' discretion, is the task lease for this protocol's downloads and training. Under it, the lead decided on 27 November 2026 the seven items that revision 1 left to the owner:

1. Fresh units are spent once, as tests: Gait120 S001-S010 (E1); AJILE12 participants 03-07 only (E2); MC_Maze full (DANDI 000128) and Large (DANDI 000138) (E3). AJILE12 participants 08-12 are kept back for the earlier maintainer's AJILE12 line and are never downloaded by this track, so that line can continue with them. E2's pass threshold is fixed now at ceil(0.7 × 5) = 4 of 5 people. The optional B1 set (the unopened tasks of the 44 Gait120 validation and confirmation people) stays out.
2. The IBL Brain-Wide Map stays with the earlier maintainer. It is admitted to neither training nor testing, so E4 is dropped and H1 requires E1 and E2 both to pass. AJILE12 participants 08-12, the Churchland/Nitschke recordings and IBL are not touched.
3. Consumed evaluation groups (Ofner S8-S12 runs 5-10, Hyser DEV, HYGRIP development, Gait120 validation and confirmation) stay out of training.
4. CMU motion capture and FingerFlex stay out.
5. Public weights: CC BY 4.0, with a NOTICE crediting every source and its licence. Code: CC0 1.0.
6. The GPU plan is accepted, with BF16 as the primary training route and the FP32 check reported (section 5.5). Section 13 gives the time estimates and their uncertainty.
7. The owner's instruction of 27 November is the task lease. The separate reviewer's admission and the lead's commit of this protocol are the scientific admission.

## 15. Rights and publication

- Public weights: CC BY 4.0, with a NOTICE that credits every source, its licence and the changes made (ODC-By attribution for Hyser, the MIT notice for HYGRIP, CDLA-Permissive-2.0 for HoloAssist if used). Code: CC0 1.0. Share-alike and non-commercial data, MyoGen (AGPL-3.0) outputs, MuscleMimic's non-commercial arm and hand parts and the two datasets without a clear licence stay out of public weights.
- Published now: this protocol, `PROTOCOL.json`, `allocate.py` and `ALLOCATION.json`. Before the freeze: `MIXTURE-MANIFEST.json` (counts, flags, licences and file hashes, no recording values) and the hash of the sealed scaling prediction. At the freeze: `FREEZE.json`. After scoring: FP32 weights of the three 0.2 seeds with a NumPy-only reader, readouts per set, per-individual errors with public dataset identifiers, bootstrap intervals, the H1, H2 and H3 outcomes, every secondary result, the LOCK and RESULT records, NOTICE, and README and METHOD in a Technical and a Simple edition after a separate reader. Raw recordings and private participant files are never published.

## 16. Departures and revisions

### 16.1 Revision 3

Revision 3 records the lead's decisions of 28 November 2026. They followed the second review of the training data (verdict: pass) and were made before any training run and before any evaluation byte was read, so no model result existed. A separate reviewer must admit revision 3 before step P3 starts.

Rule changed:

- **D arms (section 11).** Revisions 1 and 2 made a source eligible for the D arms at W_max/8 = 256 unique inner-training windows, although a k-source arm takes W_max/k windows from each source. A source between the two values could be drawn into an arm whose share it cannot fill. Area2_Bump has 458 windows and was drawn into two k = 2 arms (share 1,024) and one k = 4 arm (share 512). From revision 3 a source enters a k-source arm only if it has at least W_max/k windows. Every D arm then has exactly W_max unique windows, as each Q arm at W_max does. Repeating windows, or running an arm short, would mix quantity with diversity, which the study separates.
- Three arms change. k = 2, draw 1 is `sabes`, `ofner` (it was `area2`, `sabes`). k = 2, draw 2 is `hygrip`, `katmah` (it was `area2`, `hygrip`). k = 4, draw 0 is `ds003739`, `katmah`, `gait120`, `schreiber_moissenet` (it was `ds003739`, `katmah`, `gait120`, `area2`). The other six arms are unchanged. The arms follow from the window counts and the nine orders alone.
- The nine orders are unchanged, and `ALLOCATION.json` is not edited. Section 11 replaces the last part of its D-arm rule, "the first k sources in that order that are eligible". `D-ARM-ORDERS.json` and `MIXTURE-MANIFEST.json` hold the arms, and `run/check_d_arm_orders.py` recomputes them.
- **D_all** keeps the 11 eligible sources at floor(2,048 / 11) = 186 windows each, 2,046 in total. The 2 windows short of W_max are stated in section 11 and are stated again with the results.

Values computed at P2 and applied as the rules give them:

- **W_max stays 2,048.** Gait120, the smallest Q anchor, has 2,072 unique inner-training windows: 1,923 from step segments and 149 from static trials. Static trials are training-role recordings and were counted in the first count as well, so the rule is applied as written. Four statements go with the value, in the manifest and in section 11. The 149 static windows hold markers only (no EMG, no force). Step segments alone give 1,923 windows, which would round down to 1,024, and the margin over 2,048 is 24 windows. The Gait120 Q arm at W_max uses 2,048 of the 2,072 windows. Every Q-arm report gives the number of static-trial windows drawn at each level.
- The Q levels are 128, 512 and 2,048 windows, and every arm has U = 640 updates.
- **The P arms stay as computed.** W_P is 64 windows for Gait120, whose 3-person level has 105 windows, and 512 for ds003739. The small Gait120 budget is stated as a limit of those arms and is not changed.

Departures of the counted data from what revision 2 expected:

- Gait120 step segments are shorter than expected. The 3,761 training segments last 0.86 to 3.27 s with a median of 1.26 s, which is 43 to 163 steps of 20 ms with a median of 63. Revision 2 expected 1.5-1.65 s and at most 83 steps (sections 5.2, 5.5 and 13). 10 segments hold more than 128 steps. The E1 rule of section 5.5 is not changed.
- 1,383 of the 3,761 segments are shorter than one 1.2 s window. They give training steps but no counted window.
- Gait120 has 2,072 inner-training windows. Section 13 of revision 2 expected about 3,000.
- The mixture has 8,312,952 unique steps. The time estimates of section 13 assumed 16 million, inside a design range of 8 to 30 million.
- Section 4.2 now states the Gait120 training unit: one recording per author step segment (3,761) and one static trial per person (66). Revision 2 counted the 3,761 step segments (section 3) and did not mention the static trials, whose windows are counted (see W_max above).
- Area2_Bump is admitted with its 290 fitting and configuration trials. FALCON M1 is not admitted, because the audit found no "held-in-calib" day that is free (section 4.2). The mixture has 14 qualified sources.
- The Ofner arm and glove tokens are delayed by one 20 ms step. Each 64 Hz reading spans 8 ticks of the 512 Hz clock, and the acquisition time inside those ticks is not documented, so a reading may have been taken up to 13.7 ms after the time its file position gives. The token of step k therefore holds the last reading whose file time lies in step k - 1, which was acquired before step k ends in every case. The EEG and EOG tokens are not delayed.
- The Katmah row names its three streams as they were read: an EMG envelope (derived), IMU joint angles (derived by the Xsens MVN model) and treadmill force (measured). They are separate acquisitions and are never paired within a window. Revision 2 required this of the EMG and IMU streams; the force stream was read in the same way at step P2.

Process incidents of steps P1 and P2. All five are in the private incident and download records. None changed a role or a count, and none touched E1, E2 or E3. The Gait120 training tokens are built from the download of incident 1. No token is built from the bytes of the other four.

1. Gait120 was downloaded a third time (262 ranges, 427,525,976 B), although a re-cut from the stored shards was possible, and the reason was logged afterwards. The download holds only the 66 development people.
2. Ofner runs 4-10 were requested again (30 whole files, 2,720,902,568 B, and 23,068,672 B of a 31st), although the decision said "without a new download". The fetch was stopped, and no token comes from it. The 30 whole files were read once, to compare the corrected shards with a fresh run of the reader: with the 21 files of runs 1-3 already on disk, 51 of the 70 runs were compared and every array was equal. The other 19 runs were checked against a copy of the shards from before the delay. All 31 files were deleted at 08:50 on 28 November 2026. All of the files are training runs of S1-S7.
3. A metadata probe of the W-track JS14 file transferred 59,424 B that hold the last 2,476 stored position rows of the file. They lie after the JS14 cut (the start of trip 79), in the part of JS14 that this protocol leaves out. The bytes were never decoded and never written to disk, and they were discarded when the probe ended. Which trips the rows belong to is not established, because their timestamps were not read. Every later JS14 read forbids those byte intervals.
4. The search for each Area2_Bump unit's last spike before the 1,809.676 s cut read 408 single spike times at or after the cut, in the region of the 74 held (consumed) trials or later. Each value was only compared with the cut and discarded. The reader now scans forward and stops at the first value at or after the cut. It was not run again on the file, and the tokens are unchanged.
5. Two processes sent 6 requests to the figshare API in about 5 s, because each paced only its own requests. No request was refused. The pacer is now shared by every process, per host.

Incidents 1 and 2 were made against earlier decisions of the lead. They cover training units only and cannot be undone. They are stated in the results in both editions. From here on no step downloads anything until the freeze (step P8), and a repeated download needs its reason logged first. This also binds wave 2 (section 4.3). No wave 2 source was qualified at P2, and a wave 2 source whose training files are not already on disk cannot enter version 0.2. Training reads only the 227 reviewed shards (below), so the mixture of version 0.2 is the 14 qualified sources, and wave 2 waits for a later version.

Records corrected, in the manifest and its private parts:

- Four manifest parts (Area2_Bump, ds003739, O'Doherty/Sabes and W-track) carried an older wording of the entry `field_storage`, which names the stored number format of the field group: "float16" followed by a pointer in brackets. They now carry the current wording, "float16".
- The Gait120 clock check had a field named `steps_inside_emg_span`. It is filled from the frame-range check (each step segment's frames lie inside the frames of its trial), not from EMG cover, so it is renamed `segment_frames_inside_trial_frames`.
- 16 of the 244,423 step-segment steps of Gait120 have no EMG token: the last 15 of the 90 steps of S063_StandToSit_T02_S01 and the first step of S107_SlopeDescent_T04_S01. Those steps are masked for EMG and nothing is filled in.
- 1,505 pairs of consecutive Gait120 step segments share one boundary frame, and 748 of those frames are tokenised in both recordings. Both recordings of a pair belong to the same person, so nothing crosses a fold.
- The revision that governed each step is recorded. Revision 1 (commit c0e522f, which was 17f956b before the branch was rebased) governed the Katmah force-plate download and the first Gait120 pass. Revision 2 (commit 554c59c, which was 7d09f33 before the rebase) governed the rest of P1 and all of P2. Revision 3 governs P3 onwards.

Training data, editions and state:

- Training reads the 227 shards that the second review checked. Their digests are in the private token records as they stood at commit 4e0829d of the data branch, and `MIXTURE-MANIFEST.json` gives the sha256 of each source's shard list. No shard was changed for revision 3.
- The lead moves the training code onto the data branch before any run.
- The copy of the Ofner shards from before the delay, kept in a RAM-backed scratch folder, was deleted on 28 November 2026, after revision 3 was admitted.
- The header and `PROTOCOL.json` now name the Simple edition of this protocol, `PROTOCOL-SIMPLE.md`, which was written on 27 November 2026 after revision 2. Revision 2 said that the Simple edition would be written with the results. The results still get their own two editions (section 15).
- No training run of this protocol has started and no evaluation byte has been read. One speed trial of the training code read training tokens on 28 November 2026 at 10:06, ten minutes before revision 3 was committed and before its admission: 7 timed updates of a size XS network at T = 64 in BF16 in about 3 s, after a warm-up of about 3 s that also made updates (their count is not in the record; the script's default is 2), on the tokens of 12 sources (Gait120 and Ofner were left out). It measured throughput only and saved no weights. It is not one of the 84 runs of the quantity-versus-diversity study, not a run of step P3 and not one of the two measurements of section 13, and no choice rests on it. Any other run of the training code on training tokens before step P3 is stated in the results in the same way.
- The separate review that admitted revision 3 on 28 November 2026 listed five minor points of wording, and they are applied in this text: the sentences on wave 2 (sections 4.3 and 16.1), the Katmah force stream, the one read of the re-fetched Ofner files, the speed trial, and fields of `PROTOCOL.json` that still carried revision 2 wording. No rule, count or arm changed. The admitting review asked for these changes, and a separate reader checked them before the push; they are part of revision 3.

### 16.2 Revision 2

Revision 2 records the decisions in section 14 and applies the minor points of the separate admission review of revision 1:

- E2 scores AJILE12 participants 03-07 only, with a pass threshold of 4 of 5 people and a floor of 4 of 5 people with at least 50 eligible windows. `ALLOCATION.json` lists no asset of participants 08-12.
- E4 and every IBL use are dropped. H1 is E1 and E2 both passing. The composite R, the quantity-versus-diversity scoring and the Q anchors no longer mention E4 or IBL, and `allocate.py` no longer computes an IBL lab order.
- B1 is not run.
- Each set's pass rule now names the nearest single-source encoder as a required control (Gait120-only for E1, Ofner-only for E2, Sabes-only for E3) next to the fold-chosen best one. E3, which has one animal, gets a defined secondary rule (section 10).
- The ridge control's history T_r is chosen from the same candidate lengths as 0.2's context by the same inner folds, instead of being fixed at 16 steps (sections 6 and 8.2). The 16-step history stays in the matched-history arm.
- `PROTOCOL.json` defines j in E2's eligibility rule as the first frame after the last prior frame, as the Markdown does.
- The E1 member-list check no longer fetches the last 262,144 bytes of archive 53167640, which held 108,331 compressed bytes of an E1 member. It reads bytes 1451983325-1452137137, the central directory and the ZIP64 end records, which begin after the last byte of every member's data. `allocate.py` now refuses a file that holds any byte before the central directory.
- Step P0 was done: both design-stage tail files were replaced by central-directory-only copies and deleted (section 3).
- The time estimates state what was measured and how far they extend it (section 13). Because issuing everything on the CPU would take weeks at a 512-step context, only the forecasts that enter a set-pass rule are issued on the CPU; the other passes run in GPU FP32 with a CPU check, and E1 primary passes use a fixed length of min(T, 128) steps (section 5.5).
- A leak check confirms that no file of AJILE12 participants 08-12 and no IBL file was downloaded.

### 16.3 Revision 1

The reviewed plan merged two designs. These points were settled while writing revision 1:

- ds003739 sessions 1-3 of the development people are not local and are added to the P1 downloads (5.24 GB).
- HYGRIP EMG has 4 channels at 1 kHz without a verified electrode map, so it enters as unnamed channels; the grip signal is uncalibrated transducer voltage.
- W-track JS14 contributes all data recorded before the start of trip 79, a time cut that covers "trips up to 78".
- P-arm levels use inner-training people (Gait120 3/13/52, ds003739 2/4/14) so that every arm can also be scored on inner-validation people.
- Single-source controls are a size-M screen of every source followed by full-size retrains (one seed) of the best and the nearest source per set.
- The dataset id in the context token is dropped to "unknown" with probability 0.1, so that unseen datasets have a trained token.
- Area2 enters only as the 290 fitting and configuration trials of Han, 7 December 2017; FALCON M1 only after a role audit.
- No Van Criekinge group is used (none offered); A4 needs a protocol version 2.
- τ is chosen at size M with a 2-pass budget and one seed.
- E3 is left out of the H2 composite because it has one animal.
- 0.2 is scored per seed with errors averaged over seeds; forecasts are not ensembled.
- E1's primary metric averages the 12 markers and the +100 and +200 ms horizons; LevelWalking Trial01 is not scored in any arm.
- The compressed bytes of 23 S010 files in two metadata range reads are disclosed, never inflated, and covered by a sensitivity row.
- The quantity-versus-diversity study counts 84 runs, fewer than the reviewed estimate of about 145; its GPU estimate is kept as an upper bound.
- P1 rises to 5-7 h and P2 to 1.5-2.5 days because of the ds003739 sessions and the role audits.

Any further change needs a new protocol version or revision, a separate reviewer's admission and a commit before any evaluation byte is read. Every version and revision stays in the repository.
