# NeuroTranslate 0.2 protocol, Simple edition: one shared movement model, tested on people and sessions no earlier fit has used

Simple edition of protocol version 1, revision 2, 27 November 2026 · [Technical edition](PROTOCOL.md) · [Machine-readable protocol](PROTOCOL.json) · [Allocation script](allocate.py) · [Allocation output](ALLOCATION.json)

This is the Simple edition of the NeuroTranslate 0.2 protocol. It explains the same plan as the Technical edition, [PROTOCOL.md](PROTOCOL.md), in more words and with examples, and changes none of the rules; if a sentence here reads differently, PROTOCOL.md and PROTOCOL.json govern. Sections 1 to 16 have the same numbers and subjects as the Technical edition, so a reader can move between the two. Examples are labelled, and made-up numbers are labelled as made up.

## The plan in brief

**What is built.** NeuroTranslate 0.2 is one computer model, a neural network, that reads the recent past of recordings from the body and the nervous system and forecasts movement from 20 milliseconds up to half a second ahead. The recordings include electrical pulses of single nerve cells in animals, voltages measured on the scalp or on the surface of the brain, the electrical activity of muscles (EMG), the positions of body markers, joints or hands, and forces. The model is trained on the training parts of 13 openly licensed datasets together, in one combined training rather than one dataset after another. The final model is trained with three seeds (section 6). Two more datasets (area2 and FALCON M1) join if an audit in step P2, before the freeze, confirms that their units have training roles, and further "wave 2" datasets join only if they pass the same checks. A model trained on many sources together is called pooled. The part of the network that turns recordings into an internal summary is called the encoder, and 0.2 has one encoder shared by every dataset.

**How it is tested.** After training, the encoder is frozen: its learned numbers no longer change. For each test set it receives only small add-on parts, called adapters, fitted on separate data from that set. It is then scored once on people and sessions that no NeuroTranslation model has used, in three test sets:

- **E1:** 10 people (S001 to S010) of the Gait120 walking dataset. No earlier study downloaded their recordings. The model trains on other people of the same dataset, but never on these 10.
- **E2:** 5 people (participants 03 to 07) of AJILE12, a dataset of hospital recordings from electrodes on the surface of the brain, with upper-body poses estimated from video. Earlier NeuroTranslation studies used other AJILE12 participants, but the 0.2 that is scored for the pass rules is never trained on any part of this dataset (section 7.5 describes an optional separate copy that is).
- **E3:** two recording sessions (25 September and 6 October 2009) of one monkey reaching through a maze. This set is secondary: it has one animal, so it cannot speak for monkeys in general.

**Compared with what.** In each set, 0.2 is compared with other methods, called controls. They get the same adapters and are scored on the same forecasts. Seven of them decide whether a set is passed: a forecast of no change, a straight-line extension of the recent movement, a standard linear method (ridge regression), the frozen earlier NeuroTranslate 0.0 encoder, an untrained network of the same shape, and two networks of the same size trained on one source only (the source that scores best in model choice, and the source nearest to the test set). The other controls are reported beside them but do not decide a pass (section 8.2).

**Why.** The project owner asked for one combined movement model trained on as much varied, openly licensed neural, EMG and motion data as possible: the best model that can be engineered regardless of size, with time estimates. A common idea is that more data, and more varied data, give a model that carries over better to new people. This protocol treats that idea as a hypothesis to test, not as a fact. A secondary study asks whether a fixed number of training windows drawn from many sources gives better forecasts than the same number of windows drawn from one source (section 11).

**What counts as success.** The main claim, called H1, is that the pooled encoder helps on new people. H1 holds only if 0.2 passes both E1 and E2. A set is passed only if, against each of these seven controls (listed again in section 10), 0.2's average error is lower, the whole 95% uncertainty range of the difference lies below zero, and at least 7 of the 10 E1 people, or 4 of the 5 E2 people, have a lower error with 0.2 than with that control.

**What is expected.** The earlier shared encoder, NeuroTranslate 0.0, was matched or beaten by a simpler forecast in all five of its tests on new people. A null result, meaning no evidence that 0.2 improves forecasts for new people over the listed controls, is the expected outcome. It will be reported as such.

**Measured, derived and simulated values.** Values recorded by an instrument (marker positions, voltages, forces, spike times) are measured. Values computed from measurements are derived: joint angles from a body model, body points estimated from video, envelopes of muscle signals, and EEG cleaned by its authors. Values produced by a computer simulation are simulated. Every file, model input and report keeps the three kinds apart. No simulated data enter the main training mixture.

**The main limits.** 10 people in E1, 5 people in E2 and one animal in E3. Stored recordings only, so nothing is said about live use. EMG is a recording of muscle activity, not of nerves. A result holds against the listed controls at the stated budgets and is not evidence of general biological translation.

**What is published.** Now: this protocol and its machine-readable files. Before the freeze, and so before any test data are downloaded: the counts of the training data and the fingerprint of a sealed prediction. At the freeze: the fingerprints of every weight file, adapter and scoring script. After scoring: the model weights, every planned result (wins and losses alike) and reports in a Technical and a Simple edition (section 15).

**Where things stand.** When this edition was written, no test value had been decoded and this protocol had downloaded no test data. The one exception was incidental. Two reads of the end of the E1 archive, made while the designs were drafted, also caught compressed bytes of 23 marker files of participant S010. They were never decompressed. In the clean-up step P0, done on 27 November, the two files that held them were replaced by copies without them and the originals were deleted, and a sensitivity row repeats E1 without those 23 files (section 3). Revision 1 of the protocol (commit 17f956b) was read by a separate reviewer, who admitted it with a list of minor corrections. Revision 2 applies those corrections and records the lead's decisions on seven questions that revision 1 left to the owner (section 14). Training and downloads start only after a separate reviewer admits this protocol and the lead commits it.

## Words used in this plan

The Technical edition defines some of these terms in its section 2. They are collected here, with the other terms a reader needs.

### Time and amounts of data

- **Step:** 20 milliseconds (ms) of a recording, the basic time unit of the model. Step k covers the time from 20k ms up to 20k + 20 ms, and it becomes available at its end. Example: step 0 covers 0 to 20 ms and can be used from 20 ms on; step 50 covers 1,000 to 1,020 ms.
- **Issue time:** the moment a forecast is made. Only samples recorded up to that moment may enter the inputs.
- **Horizon:** how far ahead a forecast looks, for example 100 ms.
- **Window:** a stretch of 1.2 seconds (60 steps) of a recording. Windows do not overlap. They are used to count how much data there is, for example in section 11. The pieces of recording used as training examples, called crops, may overlap. In sections 3, 5.5 and 13, as in the Technical edition, the windows that are issued, scored, checked or used for adaptation or calibration, and "windows per second", mean the input history of one forecast at one issue time. There is one such window per forecast, and these windows overlap.
- **Individual:** a person or an animal. Individuals are treated as independent of each other: each one counts equally, and uncertainty is worked out by resampling individuals.
- **Hz (hertz):** samples or cycles per second. A signal recorded at 100 Hz has a sample every 10 ms.

### Signals

- **Spikes:** the brief electrical pulses of single nerve cells, recorded here with electrodes inside the brains of monkeys and rats. Public archives group the spikes by the cell that most likely produced them; each such group is a **sorted unit**.
- **EEG:** voltages measured on the scalp. **ECoG:** voltages measured with electrodes placed on the surface of the brain, here in hospital patients. Both are **field potentials**: the summed activity of very many cells, not of single cells.
- **EOG:** voltages caused by eye movements, recorded near the eyes.
- **EMG (electromyography):** the electrical activity of muscles, measured with electrodes on the skin (surface EMG) or inside the muscle (intramuscular EMG). **HD-EMG** (high-density EMG) uses grids of many closely spaced skin electrodes, here 256 or 320. EMG is not a recording from nerves.
- **Markers:** small reflective balls on the skin. Motion-capture cameras track their positions, here in millimetres (mm). **Keypoints:** body points such as wrists and elbows, estimated from ordinary video by a program (here DeepLabCut). **Joint angles:** angles worked out from markers with a body model (here OpenSim); they are derived. **IMU:** a small sensor on the body that measures acceleration and rotation.
- **Force plate:** a measuring plate in the floor that records how hard a foot pushes on it. A **force transducer** measures a force such as finger or grip force.
- **Kinematics:** positions and movements of the body: markers, keypoints, joint angles, IMU signals, and hand or cursor positions.

### Data roles and rights

- **Unit (of data):** what an earlier study or this protocol gives a role, a fold or a test set to: a person, an animal, a recording or a session, depending on the dataset. Training units, inner-validation units, adaptation units and fresh units are units of data. This is not the same as a sorted unit (spikes, above) or a measurement unit such as the millimetre.
- **Roles:** earlier studies gave each person, animal or recording a role. Roles called fit, train, development or engineering are training roles. Roles called validation, assessment, confirmation, final, test, held or reserve are set aside for testing.
- **Consumed:** already used as a test group by an earlier study, and so no longer new.
- **Reserved:** set aside, unopened, for a later test.
- **Licences:** CC0 1.0 is a public-domain dedication. CC BY 4.0 allows any use with credit. ODC-By 1.0 is an open-data licence that requires attribution. MIT is a permissive licence that requires its notice to be kept. CDLA-Permissive is a permissive data licence. PDDL is a public-domain licence for data. Share-alike licences (such as CC BY-SA) would require trained weights to carry the same licence, and non-commercial licences forbid commercial use.
- **Hash (sha256):** a fixed recipe that turns any text or file into a 64-character fingerprint. The same input always gives the same fingerprint, and a tiny change gives a completely different one. Hashes are used in two ways here: to show that a file has not changed, and to put names into an order that looks random but that anyone can recompute. The fixed text added before hashing, here `pooled-encoder-0.2`, is called the **salt**; it makes this protocol's orders differ from those of other studies.
- **Freeze:** the point at which every weight file, adapter and scoring script is fixed, and their fingerprints are committed in `FREEZE.json`. Test data are downloaded only after the freeze.
- **The lead:** the maintainer who leads this line of work and commits its files. **The earlier maintainer:** the maintainer of the project's earlier model lines, which include lines of work on AJILE12, on the IBL Brain-Wide Map and on the Churchland/Nitschke recordings.
- **NeuroTranslation fit:** any model the NeuroTranslation project has fitted before.

### The model

- **Neural network:** a computer model with many adjustable numbers, called parameters or weights, that are tuned during training. **Core parameters** is the protocol's count of these numbers for each model size, for example 7.27 million at size M.
- **Encoder:** the part of the network that turns input recordings into features, an internal list of numbers per step. **Readout:** the part that turns features into a forecast.
- **Token:** a list of numbers that the network holds for one item, with as many numbers as the model's width (section 5.2). In 0.2, each group of signals in a step becomes a group token, the group tokens of a step are combined into a step token, and the context token carries the dataset, species, task, body plan and the measured / derived / simulated flag (section 5.1). The hybrid core also carries a memory token (section 5.2), and the adapter of the frozen 0.0 encoder cuts the last 16 steps into 4 chunks of 80 ms and turns each chunk into one input token of the 6 numbers that 0.0 reads, so 0.0 receives 4 tokens (section 8.2). A **step-token** is one 20 ms step of one training example processed by the network. It is the unit used for speed (step-tokens per second) and for training budgets: the token budget of a run is the number of step-tokens it processes. Tokenisation (step P2) turns recordings into these inputs, and the tokenised data stored on disk are also called tokens (section 13).
- **Causal:** using only the past.
- **Transformer:** a type of network that combines information across time steps through a mechanism called attention. **GRU:** a type of network that carries a memory from one step to the next.
- **Adapter:** the small set of parameters fitted for a test set while the encoder stays frozen.
- **Identity row:** a list of 32 learned numbers that describes one channel to the model (section 5.1).
- **Ridge regression:** a standard method that fits a weighted sum of many inputs to a target, with a penalty that keeps the weights small so that the fit does not follow noise. The penalty's strength is chosen by folds (below).
- **Update:** one adjustment of the parameters during training. **Batch:** the number of examples used together for one update. **Pass:** here, as many step-tokens (see Token) as there are unique steps in the training data in use.
- **Seed:** the starting number of a random number generator. A run repeated with the same seed gives the same result.
- **Inner folds:** five groups of each dataset's training individuals (section 6). Fold 0 is the **inner-validation** fold, and all model choices are made with it. The other four folds are the **inner-training** units.
- **Selection score:** the number used to compare models during model choice (section 6). Lower is better.

### Comparisons and statistics

- **Control:** a comparison method scored on exactly the same forecasts as 0.2.
- **Arm:** one of several predeclared variants of a training or scoring run that differ in a stated way. Examples: a different core (sections 5.2 and 6), a different context length (section 6), the LoRA adapter (section 8.1), the matched-history comparison (section 8.2) and the data mixes of the quantity-versus-diversity study (section 11). Arms are fixed in this protocol before any test, and every predeclared result, arms included, is reported whatever it is (section 10). The word has nothing to do with the body's arms, which also appear in this plan (arm movements, arm sensors).
- **Persistence:** the forecast that nothing changes from the last value. **Linear trend:** a straight line through the recent past, extended forward.
- **Relative error R:** an individual's error divided by that individual's persistence error. Example with made-up numbers: if persistence misses by 20 mm on average for one person and 0.2 misses by 15 mm, R = 15 / 20 = 0.75. An R below 1 means the forecast beat persistence for that person.
- **Paired bootstrap, 95% interval, upper bound:** the method used to say how much a result could change with a different sample of people (section 9).
- **ceil:** rounding up to the next whole number. ceil(0.7 × 10) = 7 and ceil(0.7 × 5) = ceil(3.5) = 4.

### Computing

- **CPU and GPU:** the computer's main processor and its graphics processor. The GPU trains networks much faster. Its results can differ very slightly with the shape of a batch.
- **FP32 and BF16:** two ways of storing numbers in a computer. FP32 (32-bit floating point) is standard precision. BF16 (bfloat16) uses 16 bits; it is much faster on the project's GPU and less precise. BF16 "autocast with FP32 master weights" means that the heavy arithmetic runs in BF16 while the stored weights and the optimiser stay in FP32.
- **Thread:** one stream of work on the CPU.

## 1. What this protocol fixes

A protocol is a plan written and published before a test, so that the way the test is judged cannot be adjusted after the answer is known.

NeuroTranslate 0.2 is one causal network, trained on the training splits of many openly licensed recordings of neural activity, muscle activity (EMG), body motion and force, all together. It is then frozen. Each test set gets only small adapters: identity rows for channels the model has not met, and a ridge readout that turns the encoder's features into the forecast. The network is scored once on people and recording sessions that no NeuroTranslation fit has used, against matched controls with the same adapter budget. E3's monkey, Jenkins, was used by earlier NeuroTranslation fits in other sessions, so E3 tests new sessions of a known animal, not a new animal (section 7.3).

The protocol is fixed before any evaluation byte, meaning any byte of test data, is opened. It fixes:

- the training mixture and the rules that admit a dataset to it (section 4);
- how recordings are turned into model inputs, the network, what it learns to do and how it is trained (section 5);
- how every model choice is made inside the training people (section 6);
- the fresh test sets (section 7);
- the adapters and the controls (section 8);
- the error measures and the uncertainty method, a paired bootstrap (section 9);
- the success rules (section 10);
- the study of quantity against diversity (section 11);
- the checks against leaks of test data (section 12);
- the compute plan and time estimates (section 13);
- and what will be published (section 15).

Some numbers can only be counted after the training data are read, for example the number of windows each dataset holds. The protocol fixes the rules for counting them, and the counts are written to `MIXTURE-MANIFEST.json` before the freeze.

The question comes from the project owner's direction: train one combined movement model on as much varied, licensed neural, EMG and motion data as possible, the best model that can be engineered regardless of size, with time estimates. The protocol treats "more and more varied data generalise better" as a hypothesis to test, not as a premise.

## 2. Claim limits

These limits apply to every result of this protocol, whatever it turns out to be.

- **Only the listed data.** Results cover the listed datasets, tasks, inputs and horizons. The two main human test sets are small: E1 has 10 people and E2 has 5 people. E3 has one animal and makes no claim about a population of animals.
- **Stored recordings, not live use.** Forecasts are made on archived recordings. The authors of the marker data filtered their trajectories or filled gaps in them, and AJILE12 pose is estimated from video after the fact. Filtering that looks at both earlier and later samples can carry a little future information into past values. Nothing here describes the delay or accuracy of live use.
- **What each signal is.** Surface and intramuscular EMG record the electrical activity of muscles. They are not nerve recordings. EEG and ECoG are field potentials. Spike counts come from sorted units in public archives.
- **Measured, derived and simulated values stay apart.** Derived values include DeepLabCut pose, OpenSim joint angles, mean-absolute-value EMG envelopes and EEG filtered by its authors. These, the measured values and any simulated values are labelled apart in every file, input token and report. No simulated data enter the primary mixture.
- **A result holds against the listed controls only.** A win or a loss holds against the listed controls at the stated budgets. It is not evidence of general biological translation. The quantity-versus-diversity result holds only at the data scale tested.
- **Separate counts.** People, animals, sites, recordings, tasks, windows and events are counted separately, so that a large number of windows from a few people is not presented as many people.

The terms the Technical edition defines in this section (step, issue time, window, individual, inner folds, adapter, persistence, linear trend, relative error R and consumed) are explained in "Words used in this plan" above.

## 3. Facts established before this protocol was written

### The earlier shared encoder, NeuroTranslate 0.0

The NeuroTranslate 0.0 shared encoder is stored in `models/neurotranslate-0.0/movement-weights.npz` (227,155 bytes, sha256 `6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864`). It is small: 5,184 core parameters. It reads 6 inputs through a linear layer into an internal width of 24 numbers, has 4 learned positions and one transformer block. It was trained only on headset wrist tracking from HoloAssist and on one rat's task on a W-shaped track.

In all five of its tests on new people, a simpler forecast matched or beat it. Two examples:

- **Right foot force:** the error of forecasting no change in the plate force was 76.45 newtons (N), and the error of ridge regression was 82.04 N. The error of 0.0 was 85.18 N. Lower is better, so both simpler methods did better.
- **Balance:** the two balance error figures of a straight-line forecast were 7.368 mm and 6.617 mm, against 8.108 mm and 7.429 mm for 0.0.

The other three results are in PROTOCOL.json (`prior_facts`). None of the five tests published its plan or the fingerprint of its model before its results. This protocol publishes both first. The 0.0 encoder has never been retrained on the datasets admitted here.

### Speed measurements on the project's computer

A prototype of the network in section 5 was timed on 27 November while other work was running. The machine's load average was about 18 and the GPU was about 66% busy. The speeds are given in step-tokens per second; the sizes M, L and XL are explained in section 5.2.

- **GPU training in BF16** with batches of 128 examples of 128 steps: about 115,000 step-tokens per second at size M, 48,000 at L and 25,000 at XL. One pass over 16 million steps therefore takes about 2.3 minutes at M and 5.6 minutes at L.
- **Longer examples were faster per step-token.** With batches of 32, training with 256-step examples was faster per step-token than with 128-step examples: 94,600 against 64,500 at M, and 53,000 against 34,700 at L.
- **CPU training in FP32** on 4 threads: about 1,100 step-tokens per second at M.
- **CPU forward passes in FP32** (running the trained network to issue forecasts, without training) at 256 steps on 4 shared threads: 6.9 windows per second at M and 2.35 at L.

The routes were also compared with each other. The difference between two sets of learned numbers is given as a relative L2 difference: the size of the difference divided by the size of the numbers.

- At size S after 20 updates, the GPU FP32 parameters differed from the CPU FP32 parameters by 3.6e-8 (0.0000036%), and the GPU BF16 parameters by 7.2e-5 (0.0072%). The final training loss was 20.758 in BF16 against 20.775 on the CPU.
- At size M after 12 updates, the differences were 2.3e-8 and 1.06e-4 (0.0106%), and the final losses 26.055 against 26.130.
- CPU FP32, GPU FP32 and GPU BF16 runs were each bitwise equal to a repeat of themselves: every bit of the result was the same.
- GPU outputs changed by 3.6e-6 to 4.0e-6 when the batch shape changed. CPU outputs did not change.

Four things were not measured: this network at 512 steps, CPU passes at size XL or larger, CPU passes on 16 threads, and any run without other load. Section 13 explains how the time estimates extend the measurements. The main finding is that for training, the amount of licensed data, not compute, limits the model. Issuing forecasts one issue time at a time is the slow step.

### Counts checked from role lists and archive directories

On 27 November, counts were checked from the role lists (rosters) of earlier studies and from archive directories. They are listed in PROTOCOL.json (`prior_facts`). Examples:

- The 66 Gait120 development people have 3,761 marker step segments over 7 tasks. A step segment is one file covering one walking step or one movement.
- Schreiber-Moissenet ordinals 1 to 30 (the first 30 people in an earlier study's ordering) have 685 walks and 30 static trials, in which the person stands still.
- Every AJILE12 participant from 03 to 07 has a session 3 and a session 4.

### What was read to write this protocol

No evaluation value was decoded, and this protocol downloaded no evaluation data. It used:

- metadata from DANDI and figshare, two public data archives: lists of files, their fingerprints (digests), session dates and licences;
- the central directories of archives: the list at the end of a ZIP file that gives each member's name, size and CRC-32 checksum;
- the roster files of earlier studies.

The licences of the Gait120, Schreiber-Moissenet, Moreira and Van Criekinge deposits and of every DANDI set used were read from the deposits on 27 November. The other licences come from earlier source records and are checked again at step P2.

### Compressed bytes of 23 test files, and the clean-up step P0

A ZIP archive stores its members one after another and ends with the central directory, which lists them. To list the members of the Gait120 archive for S001 to S010 (figshare file 53167640) without downloading it, two reads of the end of the archive were made while the designs for this protocol were drafted. These reads took more than the directory. They also held compressed bytes of 23 marker files of participant S010, which sit just before the directory in the archive: parts of the StairAscent trials 2 to 5, all StairDescent steps and all StandToSit steps. The full list is in PROTOCOL.json (`state_at_writing`).

None of these bytes was decompressed (inflated). The scripts that read the two files parse directory records only.

Step P0 was done on 27 November:

1. Both private files were replaced by copies of archive bytes 1451983325 to 1452137137. That range is 153,813 bytes long. It holds the central directory and the ZIP64 end records (the final records of a large ZIP file) and no byte of any member. Both copies have the same sha256 fingerprint, `499068f777e756f14588e4eec6f5a34720170e7637a56d5e3d3933806939554a`.
2. The originals were deleted. They were 262,144 bytes long (sha256 `4c36aec1d921b53556cb6b66dfd28123e2e32eb1e4fdbc40284e2f6c9fe1640d`) and 2,137,138 bytes long (sha256 `1eff1b261eb5b4eab9f073da3091a8fa78ceddb8490dfae5c3f0f79fcd8652fa`).
3. The list of E1 members was worked out again from the copies. It is unchanged.

E1 is scored on all its members. A sensitivity row, fixed in advance, repeats E1 without the steps of these 23 files, so a reader can see whether they make any difference.

## 4. Data

### 4.1 The six checks a dataset must pass

A dataset, or part of one, enters the training mixture only if all six checks below pass and are recorded in `MIXTURE-MANIFEST.json` before the freeze.

- **Q1 Licence.** The licence must be CC0, CC BY, ODC-By, MIT, CDLA-Permissive or PDDL. It is checked on the deposit page, and the sha256 fingerprint of the licence text is recorded. Share-alike data are not used in public weights. Non-commercial data may give scores only. Two sources are never used: the worm imaging deposit (Zenodo 10.5281/zenodo.19388374) and the SLEAP sample recordings, whose licences are unclear.
- **Q2 Role.** Only units with a frozen training role in an existing protocol (fit, train, development or engineering), or units never given a role that a published hash rule sends to training. Every validation, assessment, confirmation, final, test, held or reserved unit stays out. So does every consumed test group and every unit of a line of work that is in progress or on hold.
- **Q3 Access.** The data must be on the project's computer, or reachable by reading single files or byte ranges in a way that never decompresses a reserved member.
- **Q4 Clock.** Two signals count as recorded together (paired) only if they share one file with one clock, or if a documented synchronisation passes a check on training units. Otherwise they enter as separate recordings and are never put side by side in one training example.
- **Q5 Labels.** The measurement units (for example mm or volts) and the kind of signal are known for each channel, and every value is labelled measured, derived or simulated. EMG is never labelled as a nerve recording.
- **Q6 Causality.** Filtering by the data's authors is recorded, for example filters that run forwards and backwards in time, gap filling, or high-pass filters with no time shift (zero-phase). Features computed in this project use only samples at or before the end of each step.

### 4.2 Training mixture, wave 1

Wave 1 is the set of datasets admitted now. Every role below was read from a roster or manifest on disk. The unit lists and inner folds are in `ALLOCATION.json`; the DOIs, licences, signals and checksums are in PROTOCOL.json (`data_sources`).

1. **Gait120** (figshare 27677016 v1, CC BY 4.0). People recorded in seven tasks: level walking, walking up and down a slope, up and down stairs, sitting down and standing up. **Training:** the 66 development people. **Signals:** 39 markers at 100 Hz (filtered by the authors), OpenSim joint angles (derived), 12-channel EMG at 2 kHz, and force-plate data for three tasks. **Left out:** the 22 validation and 22 confirmation people (consumed), and S001 to S010, who form test set E1.
2. **Schreiber-Moissenet** (figshare 7734767 v8, CC BY 4.0). Walking at different speeds. **Training:** ordinals 1 to 30, with 685 walks and 30 static trials. **Signals:** 52 markers at 100 Hz, EMG at 1,500 Hz, force plates. **Left out:** ordinals 31 to 40 (consumed) and 41 to 50 (reserve).
3. **Moreira** (figshare 14241812 v1, CC0 1.0). Walking at controlled speeds. **Training:** 8 development people, 551 trials over 7 speeds. **Signals:** markers, EMG and force plates. **Left out:** 4 validation and 4 confirmation people.
4. **İzmir** (Aperta 286866, CC BY 4.0). Walking motion capture. **Training:** the 16 people of the fitting group and the engineering person S01, with 51 walking cycles in all. **Signals:** markers. **Left out:** 6 development and 6 final people.
5. **Van Criekinge** (figshare 24192480 v1, CC0 1.0). Healthy adults walking. **Training:** 12 people of the fitting group (36 walks). **Signals:** markers, force plates, and 14 EMG channels at 1 kHz. **Left out:** 6 validation people, the 12-person test group, the pool of people never given a role, and the stroke survivors in the same release.
6. **Katmah** (PhysioNet r0ea-7161, CC BY 4.0). Treadmill walking. **Training:** identifiers 1 to 40, at 0.5 metres per second only. **Signals:** an EMG envelope shipped by the authors (derived; 38 people), IMU signals (39 people) and force plates. EMG and IMU are kept as separate recordings, because no shared clock between them has been verified. **Left out:** identifiers 41 to 52 (consumed), 53 to 59 (reserved), and the other walking speeds.
7. **ds003739** (OpenNeuro 1.0.3, CC0 1.0). A perturbed beam-walking task, with two kinds of perturbation called pull and rotate in the archive. **Training:** 18 development people with 4 sessions each (pull-stand, pull-walk, rotate-stand and rotate-walk, about 10 minutes each). **Signals:** 128-channel EEG at 256 Hz (preprocessed by the authors, so derived), 10 EMG channels, 3 EOG channels and motion capture, all in one file. **Left out:** 6 assessment people (consumed) and 6 reserve people.
8. **Ofner** (Zenodo 834976, CC BY 4.0). Arm and hand movements recorded with EEG. **Training:** people S1 to S7, movement runs 1 to 10. These are the runs in which people really moved; runs in which they only imagined moving are in wave 2. **Signals:** 61 EEG and 3 EOG channels at 512 Hz, with arm and glove sensors in the same file. **Left out:** S8 to S12 (consumed, including their unopened runs 5 to 10) and S13 to S15 (reserve).
9. **Hyser 2.0.0** (PhysioNet, ODC-By 1.0). Finger tasks recorded with high-density EMG. **Training:** 12 TRAIN people, 120 recordings of about 25 seconds. **Signals:** 256-channel HD-EMG at 2,048 Hz, and finger force at 100 Hz. **Left out:** 4 DEV people (consumed; never read) and 4 final people (never fetched).
10. **HYGRIP** (figshare 12383639 v1, MIT). A hand-grip task. **Training:** 7 eligible TRAIN groups. **Signals:** 24 EEG channels at 1 kHz; 4 EMG channels at 1 kHz whose electrode positions are not mapped, so they enter as unnamed channels; and grip-transducer voltage at 50 Hz, which is not calibrated to newtons. **Left out:** group /N, held back by its timing check, and 3 development and 3 final groups.
11. **CEMHSEY GRASP** (Zenodo 15077957, CC BY 4.0). Hand grasp recordings. **Training:** S1 to S3, 12 pinch recordings. **Signals:** 320-channel HD-EMG at 2,048 Hz, and pinch force at 200 Hz expressed as a fraction of each person's maximum voluntary contraction (MVC, their strongest pinch). The offset in samples between the EMG and the force has not been verified, and this is flagged. **Left out:** DEV people S10 to S13 and every other group.
12. **O'Doherty/Sabes** (Zenodo 3854034 v2, CC BY 4.0). Monkeys reaching to targets while spikes were recorded from the sensorimotor cortex. **Training:** the recordings indy_20170131_02 and loco_20170215_02. **Signals:** spike events per electrode, and finger position. **Left out:** indy_20161212_02 (reserved) and the August held days (recording days with a held role, which is a test role).
13. **W-track** (DANDI 000978, CC BY 4.0). Rats learning a W-shaped track. **Training:** the rats ER1, JS15 and JS17, and the data of rat JS14 recorded before the start of trip 79. The trips are numbered in time order, so this is a cut in time (PROTOCOL.md calls it a time cut that covers "trips up to 78"). **Signals:** sorted units in hippocampal area CA1 and in the prefrontal cortex, and position in centimetres. **Left out:** JS14 from trip 79 on (trips 79 and 90 are under embargo, 80 to 89 are consumed, 91 to 95 are reserved, and JS14's later recording epochs are also left out); the rats JS21, JS34 and KL8 (consumed); and both ZT2 files (closed to use).

Labels such as trip, epoch, ZT2 and the August held days, and "held-in-calib" below, are the names that the datasets or earlier studies use for their recording blocks, files and splits. PROTOCOL.json (`data_sources`) gives each one with its role.

Two special rules apply. HYGRIP left-hand trials enter only after they pass the same inter-Go clock screen (threshold 40 ms) that was used for the right hand. The screen compares the intervals between the "Go" trial markers as recorded by each device, and requires them to agree to within 40 ms. W-track files are read by HDF5 byte ranges, taking only spike times and position.

Two more datasets are conditional members of wave 1. An audit in step P2, before the freeze, decides whether they enter:

- **Area2_Bump** (DANDI 000127, CC BY 4.0). Only the 290 trials of the monkey Han on 7 December 2017 that an earlier area2 study used for fitting (218 trials) and configuration (72 trials). The 74 trials assessed in that study's original comparison stay out. So does the laboratory's Dryad deposit, because several of its sessions are consumed and it repeats this laboratory's recordings.
- **FALCON M1** (DANDI 000941, CC BY 4.0). Only the "held-in-calib" days (the benchmark's own name for one of its data splits) that no earlier evaluation scored.

The IBL Brain-Wide Map stays with the earlier maintainer. No IBL subject, lab or session enters training or testing (section 14).

### 4.3 Wave 2 and datasets left out

Wave 2 datasets enter only if they pass Q1 to Q6 before the freeze. The candidates are:

- HoloAssist (CDLA-Permissive-2.0; the 0.0 encoder's own source; not on disk);
- zebrafish recordings, DANDI 000235;
- Daily and Sports Activities, participants p1 to p4;
- WAY-EEG-GAL fit participants;
- EEG-EMG-WristMotion version 3, TRAIN people;
- the training roles of KIN-MUS UJI and IACKD;
- the Ofner motor-imagery runs of S1 to S7;
- MC_RTT, after a role audit;
- Katmah EEG, after a clock check.

Simulated windows from the project's physics-source track, which produces movement from physics simulations of the body, may enter only in a separately flagged, predeclared add-on arm (see "Arm" in the word list), never as part of the primary mixture.

The following are left out, with the reason for each:

- **All of AJILE12**, so that E2 is a dataset the model has never seen. Participants 08 to 12 are also kept back for the earlier maintainer's AJILE12 line of work and are never downloaded by this track.
- **Every Jenkins recording**, held out for E3.
- **The Nitschke recordings and the Churchland pedal recordings**, which are held by the earlier maintainer and have no training role.
- **The IBL Brain-Wide Map**, which stays with the earlier maintainer.
- **LINK**, an earlier project test: its LINK720 epochs and its results stay sealed.
- **FingerFlex**, whose share-alike licence would bind the weights.
- **MoVi, SUMediPose and AMASS**, which are non-commercial.
- **The worm and SLEAP recordings**, whose licences are unclear.
- **KIT, NEMO, Senden, the Harvard camera dataset, the external paired walk and Flint**, whose licences are unclear or which are held.
- **CMU motion capture**, which has non-standard terms.
- **reach_grasp_v1**, for which no licence was found locally.
- **The Van Criekinge pool**, which belongs to the walking-scale and physics-source protocols.

### 4.4 Counting the data

For each dataset, `MIXTURE-MANIFEST.json` records:

- individuals and sites;
- recordings and sessions;
- tasks and conditions;
- unique 20 ms steps and non-overlapping 1.2 s windows;
- channel-seconds per kind of signal (the number of channels times the seconds recorded);
- spikes;
- and the derived and simulated flags.

The designs estimated 8 to 30 million steps in total. The manifest replaces this estimate with real counts before any model choice. The largest model size must be justified by inner validation (section 6), not by the size of the mixture.

## 5. Model

### 5.1 How recordings become model inputs

The model's inputs are built in seven steps.

**1. Cut time into steps and slots.** Each recording is cut into 20 ms causal steps. In each step the model has six slots, called groups: spikes, field signals (EEG and ECoG), EMG, kinematics (markers, keypoints, joint angles, IMU, hand or cursor position), force, and a context token.

**2. Turn each group into numbers for the step.**

- **Spikes:** the number of spikes of each sorted unit in the step, kept as raw counts.
- **Field signals:** for each channel, the log band power, a measure on a log scale of how strong the rhythm in a frequency band is. It is computed over the trailing 100 ms or 200 ms (the inner folds choose which) in four bands: 4-8, 8-13, 13-30 and 70-150 Hz. A recording must be sampled fast enough to contain a band; the 70-150 Hz band is masked (left out) for recordings sampled below 400 Hz. Example: the ds003739 EEG, sampled at 256 Hz, has no 70-150 Hz band. A slow component, the value after a causal 10 Hz low-pass filter, is added.
- **EMG:** the log RMS of the signal within the step after a causal 20 Hz high-pass filter. RMS (root mean square) measures the size of a varying signal; the high-pass filter removes slow drifts. "Causal" filters use only past samples. Katmah ships an envelope instead of the raw EMG; it is used as given and labelled derived.
- **Kinematics:** the last sample in the step and its change from the previous step. Positions are measured from an anchor taken at the last input step: the mean of the pelvis markers for body marker sets, the mean of the shoulders for upper-body keypoints, and the point itself for a single tracker. The model therefore sees body shape and movement, not where in the room the body is.
- **Force:** the last sample in the step and the mean over the step.

**3. Tell the model which channel each number comes from.** For a group with channels c, the numbers are read in through a matrix W[c] = E(c)·P. Here E(c) is the identity row of channel c, 32 learned numbers, and P is a matrix shared by all channels, so the read-in matrix has rank 32. The read-in is applied both to the value x and to a bent version of it, gelu(x). A term that says whether the channel is present is added, and the result is normalised (LayerNorm). Channels with shared names use the same identity row in every dataset. The shared name lists cover muscles with their side, anatomical markers and keypoints, joints with their axis, the 10-10 EEG sites (a standard system of scalp positions), force axes, and IMU segments and axes. Sorted units, ECoG electrodes, HD-EMG electrodes and unmapped EMG channels have no shared names, so they get learned rows per recording, with a small coordinate network where electrode positions exist. A new person whose channels have shared names needs no new parameters.

**4. Put channels on a common scale.** Each channel is converted to a z-score (its value minus its mean, divided by its standard deviation). The mean and standard deviation come from training units only. Test sets use their own adaptation data for this.

**5. Add a context token.** The context token says which dataset, species, task and body plan the data come from, and whether they are measured, derived or simulated. During training, the dataset is replaced by an "unknown dataset" label with probability 0.1 (10% of the time), so that datasets the model has never seen have a trained token.

**6. Mask what is missing.** Missing groups and channels are masked, so the model ignores them.

**7. Add flat views of 3D markers.** With probability 0.2, a training example of 3D markers is replaced by a flat 2D picture of its landmarks, as a camera far away would see it (an orthographic projection). The viewing direction is random: any angle around the body (azimuth 0-360°) and from 20° below to 40° above (elevation −20° to +40°). These examples are flagged derived. They show the encoder 2D inputs similar to video keypoints without using any AJILE12 data.

### 5.2 Architecture

The network works in two stages. First, one transformer layer combines the group tokens within each step (absent groups are masked), and the step token is the mean of the present group tokens. Second, a causal transformer runs over the step tokens. It uses pre-LayerNorm and rotary position embedding, a way of telling the network how far apart two steps are. Two other cores are tried as arms: a GRU, and a hybrid (a transformer plus a GRU memory token carried from one stretch of input to the next). The output heads map each group and horizon to 32 numbers and combine them (by a dot product) with an output identity row for each channel. Any set of channels can therefore be forecast.

The network comes in six sizes. Width is the number of values per token; layers are stacked processing stages; heads are attention parts that work side by side within a layer.

| Size | Width | Layers | Heads | Core parameters |
| --- | ---: | ---: | ---: | ---: |
| XS | 64 | 4 | 2 | 0.29 million |
| S | 128 | 6 | 2 | 1.47 million |
| M | 256 | 8 | 4 | 7.27 million |
| L | 384 | 12 | 6 | 23.3 million |
| XL | 512 | 16 | 8 | 53.9 million |
| XXL | 768 | 16 | 12 | 121 million |

XXL runs only if XL beats L by at least 1% relative on the selection score. Example with made-up numbers: if L scores 0.800, XL must score 0.792 or lower for XXL to run.

The context length T is how many past steps the network sees: 64, 128, 256 or 512 steps (1.28, 2.56, 5.12 or 10.24 seconds), chosen by the inner folds. Shorter segments are padded and the padding is masked. Recordings differ a lot in length: Gait120 step segments last 1.5 to 1.65 s, while ds003739 sessions last 10 minutes.

### 5.3 What the model learns to do

- **Forecast every present channel.** The model forecasts every channel that is present at 20, 100 and 200 ms ahead (horizons h = 1, 5 and 10 steps), and kinematics also at 500 ms.
- **Loss for spikes.** For spikes the error measure (the loss) is the Poisson negative log-likelihood of the counts: it rewards giving high probability to the spike count that actually happened. At h = 1 this means forecasting each neuron's count in the next step, which the protocol calls next-neuron prediction.
- **Loss for other signals.** For the other signals the loss is the Huber loss (δ = 1) on the change from the latest value, in normalised units. The Huber loss grows like a squared error for small errors and like an absolute error for large ones.
- **Hide whole groups.** Each present group is hidden from the input with probability 0.25, keeping at least one measured group, but it stays a target. Hidden groups are also reconstructed at h = 0, the present step. This trains the translations between kinds of signal that the test readouts need, for example from EMG to kinematics and from spikes to kinematics.
- **Hide single channels.** Single channels are hidden with probability 0.15.
- **Balance the losses.** Each group's loss is divided by its baseline loss on the training mixture: the persistence loss, or for spikes the loss of each sorted unit's mean rate. Groups and horizons then have equal weight.
- **Draw datasets.** Datasets are drawn with probability proportional to N_d^τ, where N_d is the number of individuals in dataset d. τ (tau) is 0, 0.5 or 1, chosen on leave-one-dataset-out folds (section 6), and no dataset may supply more than 25% of the examples. Within a dataset, individuals are drawn uniformly, recordings in proportion to their duration, and crop starts uniformly.

An example of the dataset draw, with the real numbers of individuals of two datasets: Gait120 has 66 training people and Ofner 7. With τ = 1, Gait120 is drawn about 9.4 times as often as Ofner (66 / 7). With τ = 0.5, about 3.1 times as often (the square root of 66 divided by the square root of 7). With τ = 0, both are equally likely. The 25% cap applies in every case.

### 5.4 Training settings and records

- **Optimiser and schedule.** AdamW is the method that adjusts the parameters (β 0.9/0.95, weight decay 0.05 on matrices). The learning rate rises linearly over the first 2% of training (warm-up), then falls along a cosine curve to 10% of its peak.
- **Peak learning rates.** 6e-4 (XS), 5e-4 (S), 3e-4 (M), 2e-4 (L), 1.5e-4 (XL and XXL).
- **Batches.** 128 training examples (crops) of T steps each per batch.
- **Safeguards.** The gradient is clipped at 1.0, which limits the size of any single adjustment. Dropout is 0.1, which hides random parts of the network during training. Stochastic depth is 0.1 for XL and XXL, which skips random layers during training.
- **Passes.** One pass is a number of step-tokens equal to the unique steps of the mixture in use.
- **Data order.** The order of the data is fixed by salted sha256 hashes per dataset. The sampler draws from counters keyed by the sha256 of the seed, the update number and the slot, and its state is saved in every checkpoint, so a run can be resumed exactly.
- **Seeds.** 20261127, 20261128 and 20261129.
- **Repeatable arithmetic.** The settings `torch.use_deterministic_algorithms(True)` and `torch.utils.deterministic.fill_uninitialized_memory = False` are used, with the plain ("math") attention method on the GPU and fixed batch shapes. Together these make runs repeatable.
- **Records.** Each run leaves a chain of records:
  1. LOCK, with the fingerprints of the source data, the arrays and the scripts;
  2. ATTEMPT;
  3. an FP32 checkpoint with the optimiser and sampler state;
  4. a check that the reloaded checkpoint equals the saved one;
  5. RESULT, with fingerprints, wall-clock time, peak memory, threads and software versions;
  6. READBACK.
- **Sharing the machine.** At most 16 threads are used in total, pinned to CPUs 16 to 31. The GPU is shared with browser tests run by other work, which have priority.

### 5.5 Precision: which processor and number format is used for what

There are three tiers.

- **Tier 1, CPU FP32.** The reference route. Every forecast that enters a set-pass rule (section 10) is issued with it.
- **Tier 2, GPU FP32** with the plain attention method. The reference training route up to size M, and L if time allows.
- **Tier 3, GPU BF16** autocast, with FP32 master weights and optimiser. Used for the size ladder, the arms, and sizes XL and above.

BF16 must pass a check before it is accepted. Matched full runs are made at sizes S and M: BF16 with 3 seeds, and GPU FP32 with seed 20261127, on the same data order. BF16 is accepted only if the two differ by at most the larger of 1% relative and the spread across the 3 BF16 seeds, on the selection score and on the inner-validation readout measures. Otherwise the final runs use GPU FP32.

Issuing forecasts is split between the processors in four rules.

1. **CPU for forecasts that decide a pass.** Every forecast that enters a set-pass rule is issued in FP32 on the CPU, from an FP32 copy of the model, at a fixed batch shape of 32. These are the E1 and E2 scoring windows with primary inputs, for 0.2 and for every set-pass control.
2. **GPU for all other passes, with a CPU check.** All other encoder passes run on the GPU in FP32 with the plain attention method and fixed padded shapes. These are the adaptation windows from which adapters and readouts are fitted, E3, the secondary inputs, the wrong-pairing rows, the secondary arms and the quantity-versus-diversity arms. For each encoder, 1,000 of these windows are repeated in FP32 on the CPU, and the largest absolute and relative differences are reported. The 1,000 windows are drawn by ascending sha256 of `pooled-encoder-0.2|cpu-check|` + encoder + `|` + set + `|` + window id, in equal shares over the sets. The relative difference is the largest absolute difference in any feature divided by the largest absolute CPU feature value over the same windows. If it exceeds 1e-4 for an encoder, all of that encoder's passes are repeated on the CPU. Example with made-up numbers: if the largest CPU feature value is 10, the largest difference may be at most 0.001. Revision 1 issued everything on the CPU; section 13 shows that this would take weeks at a 512-step context.
3. **A shorter fixed length for E1.** E1 primary inputs lie inside one step segment, and Gait120 step segments hold at most 83 steps of 20 ms. E1 primary passes therefore use a fixed length of min(T, 128) steps, the smaller of T and 128, padded on the left and masked as in training. An E1 issue time with more than 128 input steps uses T. Because padding is masked and the position embedding only uses distances between steps, this gives the same function as padding to T in exact arithmetic. A CPU check on 1,000 Gait120 inner-validation windows reports the largest difference before the freeze.
4. **A repeated arm.** One arm is repeated with identical settings to report how much GPU results vary from run to run.

## 6. Model choice inside the training people

Every choice about the model (its size, training length, core, context and so on) is made using training people only. A choice made by looking at test results would make the test unfair, because the method would then be fitted to the test.

### The inner folds

The inner folds are computed by `allocate.py`.

1. Each training unit's name is combined with fixed text and hashed: sha256 of `pooled-encoder-0.2|fold|` + dataset + `|` + unit.
2. The units of each dataset are ranked by ascending fingerprint.
3. Each unit's fold is its rank modulo 5, counting ranks from 0. So the 1st, 6th, 11th and later units in the ranking go to fold 0, the 2nd, 7th and so on to fold 1, and similarly for folds 2 to 4.
4. Fold 0 is inner validation.

Datasets with fewer than three independent individuals or recordings (O'Doherty/Sabes and area2) are split by time instead: each recording is cut into five equal time blocks, and the latest block is inner validation.

Examples from `ALLOCATION.json`: the Gait120 inner-validation people are S108, S033, S036, S115, S050, S011, S092, S046, S098, S104, S066, S020, S119 and S053 (14 of the 66), and the W-track inner-validation rat is JS14.

### The selection score

The selection score is worked out in three steps.

1. **Fit new channels.** For each inner-validation unit, identity rows for new channels are fitted on the first half of each recording.
2. **Score each dataset.** On the second half, each present group's model loss is divided by its baseline loss, and these ratios are averaged over the groups of the dataset.
3. **Average over datasets.** The dataset values are averaged with equal weight.

Lower is better. Example with made-up numbers: a ratio of 0.8 for a group means the model's loss is 20% below the simple baseline's loss for that group.

### The choices, in order

1. **τ (the dataset draw):** chosen by leaving one dataset out at a time, at size M with a transformer core, T = 256, seed 20261127 and a budget of 2 passes. Each wave-1 dataset is left out of training in turn, adapted on its inner-training units and scored on its inner-validation units.
2. **Size and number of passes:** a ladder of runs from XS to XL, each up to 40 passes, with a checkpoint every 2 passes. The size and checkpoint with the lowest selection score win.
3. **Core:** transformer, GRU and hybrid at sizes M and L. Another core replaces the transformer only if it is better by at least 1% relative at both sizes.
4. **Context:** T of 64, 128, 256 or 512 steps, and a field-signal span of 100 or 200 ms (the trailing time over which band power is computed, section 5.1), at size M.
5. **XXL:** only under the rule in section 5.2.
6. **The ridge control's history T_r:** chosen from the same candidates (64, 128, 256 or 512 steps) by the same inner folds (section 8.2). This choice uses no encoder and is made before the freeze.

Results within 0.5% relative of each other count as a tie, and a tie goes to the smaller or simpler option. The final model is then trained on all training units (inner-training and inner-validation together) with the chosen settings and number of passes, with 3 seeds.

## 7. Fresh evaluation

No test set below uses a reserve owned by an earlier protocol. Using a set makes its units consumed for all later work. The lead decided to spend E1, E2 and E3 once (section 14).

### 7.1 E1, Gait120 S001-S010 (primary; a seen dataset, unseen people)

**Who and why they are new.** These 10 people were left out of an earlier chair-rise study's roster because they lack force-plate data aligned with the source recordings. Their archive (figshare file 53167640) was never fetched by an earlier study. 0.2 trains on other Gait120 people, so E1 tests new people from a dataset the model knows.

**Files.** 1,198 members of the archive are used: TRC marker files, OpenSim joint-angle (MOT) files and RawData.mat files, 759,080,170 compressed bytes in all. They are listed with their CRC-32 checksums in `ALLOCATION.json`.

**Adaptation.** The adapters and the ridge readout are fitted on the 66 Gait120 development people (all 7 tasks, same targets). Their penalties are chosen by five folds of those people. No adapter or readout is calibrated on an individual test person; the only per-person step is the EMG scaling of the secondary input, below.

**Issue times.** A forecast is issued every 50 ms, starting 0.5 s after the start of each step segment, as long as the target frame 200 ms ahead still lies inside the segment. Example: in a segment of 1.6 s, the issue times run from 0.5 s to 1.4 s, which gives 19 forecasts. Segments of 1.5 to 1.65 s give 17 to 20.

**Inputs.**

- *Primary:* the past markers of the segment, measured from the centre of the pelvis at the last input frame.
- *Secondary:* markers plus 12-channel EMG, for people whose EMG passes the same check of trial timestamps and frame identifiers used for training people. Each person's EMG is scaled from their LevelWalking Trial01.

**Targets.** How far 12 markers move from the last input frame to 100 ms and to 200 ms later, in mm. The markers are LASI and RASI (front of the left and right hip bone), LPSI and RPSI (back of the pelvis), LKNE and RKNE (knees), LANK and RANK (ankles), LHEE and RHEE (heels), and LTOE and RTOE (toes). Secondary targets are the OpenSim joint angles (derived, in degrees) and the EMG log envelope at 100 ms ahead.

**Primary measure.** For each forecast, the straight-line (Euclidean) distance in 3D between the forecast and the real movement is taken for each of the 12 markers at both horizons, and these 24 distances are averaged, in mm. Forecasts are averaged within a step, then within trials, then over the 7 tasks with equal weight, and finally over people.

**Rows not scored.** LevelWalking Trial01, the EMG scaling trial, and the static trials are not scored for any method. A forecast is eligible only if all 12 target markers are present at the last input frame and at both target frames. This rule is applied the same way to every method.

**Sensitivity row.** E1 is repeated without the steps of the 23 S010 files described in section 3.

**Note on filtering.** The authors filtered the marker trajectories, so past inputs may carry a little information from later samples. This affects every method alike, and the result is labelled as a result on archived recordings only.

### 7.2 E2, AJILE12 participants 03-07 (primary; an unseen dataset, unseen people)

**The dataset.** AJILE12 holds long recordings of people with electrodes on the surface of the brain (ECoG) during a hospital stay, with video from which a separate DeepLabCut model for each person estimated the positions of body points. The protocol uses DANDI 000055, version 0.220127.0436, participants 03, 04, 05, 06 and 07. The encoder of 0.2 is never trained on any AJILE12 data; only its adapters and readout are fitted, on the calibration sessions described below. So E2 tests new people from a dataset the model has never been trained on. The optional seen-dataset arm in section 7.5 is a separate copy and does not change this. Earlier NeuroTranslation studies used other AJILE12 participants; no NeuroTranslation fit has used participants 03 to 07.

**Sessions.** For every participant, session 3 is the calibration session and session 4 the scoring session. Their file ids, sizes and sha256 fingerprints are in `ALLOCATION.json`. No other session is ever opened. The pose series and, for the secondary input, only the ECoG needed for the chosen forecasts are read by HDF5 byte ranges.

**Participants kept back.** Participants 08 to 12 are kept back for the earlier maintainer's AJILE12 line of work. This track never downloads or opens any of their files, and `ALLOCATION.json` lists none of them.

**Pass threshold.** With 5 people, the set-pass rule needs at least ceil(0.7 × 5) = 4 of the 5 people improved (section 10). This threshold was fixed in revision 2, before any AJILE12 byte was read.

**Adaptation.** The adapters and the ridge readout are fitted on the five calibration sessions pooled together. Penalties are chosen by leaving one participant out at a time over the 5 calibration sessions. Each participant's ECoG identity rows come from that participant's own calibration session.

**Choosing the forecast times.** Candidate frames are drawn by sha256 of `pooled-encoder-0.2|ajile12|` + participant + `|ses-` + session + `|` + k, for k = 0, 1, 2 and so on. A candidate is kept if it is eligible and at least 2 s from every frame already accepted, until 600 are accepted per session. The video runs at 30 frames per second, and "the last prior frame" is the last frame the model may see. Let j be the first frame after it, the first unseen frame. A candidate is eligible only if all of the following hold:

- it is at least 10.24 s after the start of the session (512 steps, the longest context);
- in the 15 prior frames (j − 15 to j − 1), both shoulders are present, and the wrist, elbow and shoulder of both arms are present;
- the shoulders pass three checks taken from an earlier study's rule, which make sure they define usable axes: the shoulder width w is at least 1 pixel; the length of the mean shoulder-to-shoulder vector is at least 0.5 w; and the vertical component of the direction perpendicular to the shoulders has a size of at least 0.10;
- both wrists are present at frames j + 7 and j + 14, which are 8 and 15 frames after the last prior frame.

Secondary forecast times are the reach onsets recorded in the session's own ReachEvents table, selected under the earlier study's rule.

**Inputs.**

- *Primary:* the past pose (wrists, elbows, shoulders, ears and nose), resampled to 20 ms steps by taking the last video sample in each step. Positions are expressed in shoulder axes (a coordinate frame built from the shoulder positions in the 15 prior frames only) and divided by the shoulder width.
- *Secondary:* pose plus ECoG band power, compared with ECoG taken from 60 s earlier.

**Targets.** How far each wrist moves from the last prior frame to 8 frames (0.267 s) and 15 frames (0.500 s) later, in shoulder widths. Both the wrist on the opposite side to the brain implant (contralateral) and the wrist on the same side (ipsilateral) are forecast; each side of the brain mainly controls the opposite side of the body. The contralateral side is taken from the session's own ReachEvents description and the published implant hemisphere.

**Primary measure.** The 2D straight-line distance between forecast and real wrist movement, averaged over both wrists and both horizons, in shoulder widths (normalised image units). Example: an error of 0.1 is a tenth of the person's shoulder width. No millimetre values are reported, because the published conversion from image units to millimetres is undefined.

### 7.3 E3, MC_Maze full and Large (secondary; one animal)

**The data.** In the MC_Maze recordings, a monkey (named Jenkins in the archive) reached to targets around barriers on a screen while spikes were recorded from the motor areas of the cortex. They were published by the Neural Latents Benchmark (NLB), which split each session into "train", "val" and "test" trials. Two sessions are used:

- DANDI 000128, recorded on 25 September 2009 (training file 690,612,247 bytes);
- DANDI 000138, recorded on 6 October 2009 (148,590,536 bytes).

**Why these sessions are new.** Neither date matches the Jenkins sessions of DANDI 000070 (12, 16, 18 and 23 September), MC_Maze Small (28 September) or MC_Maze Medium (29 September, consumed). The benchmark's test files ("desc-test") are never opened. 0.2 never trains on any Jenkins recording; earlier NeuroTranslation fits used other Jenkins sessions.

**Adaptation.** For each session, identity rows for the sorted units and the ridge readout are fitted on the NLB "train" trials, with penalties chosen by 5 folds of those trials.

**Scoring.** Scoring uses the NLB "val" trials. A forecast is issued every 50 ms from 250 ms after the trial start, while the target lies inside the trial.

**Inputs.** Primary: past spikes (at least 200 ms, up to the chosen context) and past hand position. Secondary: spikes only.

**Target and measures.** How far the hand moves in 2D in the next 100 ms, in mm. A secondary measure is the next-step spike log-likelihood in bits per spike, which says how well the spike counts of the next step are predicted compared with each sorted unit's mean rate.

**Uncertainty.** With one animal, uncertainty comes from resampling trials, stratified by session (each resample keeps the trials of the two sessions separate). E3 is always secondary and never enters H1.

### 7.4 E4 is dropped

E4, a test on held-out laboratories of the IBL Brain-Wide Map, is not run. The IBL Brain-Wide Map stays with the earlier maintainer, so no IBL subject, lab or session is used for training or testing (section 14).

### 7.5 Secondary sets

- **B1** is not run. The unopened tasks of the 44 Gait120 validation and confirmation people stay unopened (section 14).
- **A4** would use the Camargo et al. lower-limb biomechanics dataset as a whole held-out dataset. It needs a later protocol version, written after a check that none of its people overlap with the consumed Georgia Tech record 10.35090/gatech/70296, and after a licence check.
- **Seen-dataset arm** (optional, if GPU time allows): a separate copy of 0.2 is trained further on AJILE12 participant sub-01, session 3 only, and scored on E2 only. The 0.2 that is scored for the pass rules is not this copy. No encoder that enters a pass rule, whether 0.2 or a control, is trained on AJILE12 data; their adapters and readouts are fitted on the E2 calibration sessions only. This copy measures what seeing the dataset adds, and it is reported whatever the result.
- **Published tasks:** the task readouts of 0.0 are refitted on 0.2. They are reported only as a development comparison on people used before, not as a test on new people.

Two candidates are not used: a Van Criekinge group, because the walking-scale allocation offers none to this track, and W-track ZT2, which is closed.

## 8. Adapters and controls

### 8.1 Adapters (the same budget for every encoder)

An adapter is fitted in four steps, and every encoder gets exactly the same budget.

1. **Map named channels.** Channels are mapped onto the shared name lists where their names allow.
2. **Train rows for unnamed channels.** Identity rows for unnamed channels are trained for 500 AdamW updates at a learning rate of 3e-3, with the encoder frozen.
3. **Fit the readout.** The readout is ridge regression on the frozen features of the issue step. Its penalty is chosen from {1e-3, 1e-2, 0.1, 1, 10, 100, 1000} by the folds of each set's adaptation units.
4. **Store it separately.** Released readouts are separate files that record the sha256 fingerprint of their parent encoder.

As a predeclared secondary arm, LoRA of rank 8 (a method that adds a small trainable change to the frozen weights) is trained for 200 updates.

### 8.2 Controls

The same adapter budget, seeds, data order and scored rows apply to every method on every set. Each control answers a different question about where a result could come from.

- **Persistence:** a forecast of zero change. It is the simplest possible forecast, and a useful method must beat it.
- **Linear trend:** a straight-line forecast.
  - E1: a least-squares line over the last 100 ms of each target marker.
  - E2: the endpoint velocity of the 15 prior frames: the last position minus the first, scaled by 8/14 for the 8-frame horizon or by 15/14 for the 15-frame horizon (the 15 frames span 14 frame intervals). Example with made-up numbers: if a wrist moved 0.28 shoulder widths over the 15 prior frames, the trend forecasts 0.28 × 8/14 = 0.16 at 8 frames and 0.28 × 15/14 = 0.30 at 15 frames.
  - E3: a least-squares line over the last 100 ms of hand position.
- **Ridge:** ridge regression on the per-step input features of the last T_r steps, with the change from the last value as the target. It shows what a simple linear method achieves with the same inputs. T_r is chosen from the same candidates as 0.2's context (64, 128, 256 or 512 steps) by the same inner folds, in five steps:
  1. On each wave-1 training dataset, a ridge regression is fitted on the inner-training units. It forecasts the change of every present continuous channel at the training horizons. Spike counts are inputs, not targets.
  2. Its penalty is chosen from the adapter grid by folds of the inner-training units.
  3. Its selection score (section 6) is taken on the inner-validation units.
  4. The T_r with the lowest mean over datasets is used on every set. Ties within 0.5% go to the shorter history.
  5. Steps before the start of the available input (for example before a step segment begins) are filled with zeros and marked by a presence flag per step, as 0.2 masks them.

  Penalties for each test set are then chosen as for the adapters.
- **Frozen 0.0:** the `movement-weights.npz` encoder, frozen. It shows whether 0.2 improves on the project's earlier shared encoder.
  - A 4-token adapter cuts the last 16 steps (320 ms) into four chunks of 80 ms and maps each chunk to the 6 inputs that 0.0 expects. It is trained with a linear head for 500 updates at 3e-3.
  - The ridge readout is then fitted on 0.0's final-token features.
  - A related set of weights, joint_alpha, is not used, because it was trained on the worm and SLEAP recordings, whose licences are unclear.
- **Random encoder:** the 0.2 network at the final size, started with seed 20261127 and never trained. It shows how much of a result comes from the network's shape and the adapters alone, without any learning.
- **Scrambled 0.2:** every weight tensor of 0.2 with its entries shuffled by a fixed permutation (seed 20261128). It keeps the same numbers but destroys their learned arrangement.
- **Single-source encoders:** encoders trained on one source only. They show whether pooling many sources beats training on one. They are made in two stages:
  1. A size-M encoder is trained for each wave-1 source, with the same training budget for every source, as a screen. PROTOCOL.md and PROTOCOL.json call this the arm budget and do not give it as a number; step P7 (section 13) estimates the whole screen at about 2 hours.
  2. Two kinds are then retrained at the final 0.2 size and token budget on all their training units (seed 20261127): the best by selection score, and the nearest source of each set (E1: Gait120; E2: Ofner; E3: O'Doherty/Sabes). Each keeps the checkpoint with the best score on its own source's inner validation.

  Both the best single-source encoder and the set's nearest single-source encoder are required controls in that set's pass rule (section 10). When they are the same source, it counts once.
- **Scratch size S:** a size-S model trained from random starting values on the set's adaptation data only (2,000 updates at a learning rate of 5e-4, batch 32), then the ridge readout. It shows what can be learned from the test set's own adaptation data without any pre-training.
- **Matched history:** frozen 0.0 sees only the last 16 steps (320 ms). 0.2 is also scored on the same 320 ms history, so the effect of a longer history can be separated from the effect of the encoder.
- **Task specialists (for H3 only):** the recipe that earlier project studies wrote for each task.
  - E1: the attention recipe of the chair-rise study, refitted on the 66 development people with the E1 targets.
  - E2: the pose ridge recipe of the earlier next-person study, with penalty 1, fitted on the calibration sessions.
  - E3: the NeuroTranslate 0.1 eight-pass neural-maze model, refitted on each session's train trials.
- **Wrong pairing:** every neural or EMG input is also replaced by the same kind of signal from another time. This shows whether the model uses the real link between that signal and the movement.
  - E1: EMG from the previous step of the same trial.
  - E2: ECoG from 60 s earlier.
  - E3: spikes from the next val trial.

## 9. Error measures and uncertainty

- **Units.** Errors are in physical units where they exist: mm for E1 and E3. E2 uses shoulder widths.
- **Averaging order.** Within an individual, forecasts are averaged first, then trials or segments, then tasks. Each person or animal then has equal weight, so a person with many recordings does not count more.
- **Relative error.** Each individual's relative error R = error / persistence error is reported beside the physical error. The composite is the mean of the set mean R over the two primary sets, E1 and E2. E3 is reported separately.
- **Seeds.** 0.2 and every three-seed control are scored per seed, and each individual's error is averaged over the seeds. Forecasts of different seeds are not combined into one forecast (no ensembling).

### The paired bootstrap

The test groups are small samples of people, so each result comes with a 95% interval that shows how much it could change with a different sample of people. The interval comes from a paired bootstrap over individuals:

1. Take the n individuals of the set.
2. Draw n individuals at random with replacement, so some appear twice and some not at all.
3. For this resample, compute the mean paired difference: 0.2's error minus the control's error, on the same individuals. "Paired" means both methods are compared on the same resampled people.
4. Repeat 10,000 times, with seed 20261127.
5. The middle 95% of the 10,000 values is the 95% percentile interval. Its top end is the upper bound.

Beside each interval, the report gives the number of individuals improved and the range of the result when one individual at a time is left out. E3 resamples trials, stratified by session. For the composite, individuals are resampled independently within each set.

## 10. Success rules

These rules were fixed before any evaluation byte was read.

### Set pass (E1 and E2)

0.2 passes a set only if three conditions hold against every one of these seven controls:

1. persistence;
2. linear trend;
3. ridge;
4. frozen 0.0;
5. the random encoder;
6. the fold-chosen best single-source encoder;
7. the set's nearest single-source encoder (Gait120-only for E1, Ofner-only for E2).

The three conditions are:

- the mean paired difference (0.2 minus the control) is below 0;
- the bootstrap 95% upper bound is below 0;
- at least ceil(0.7 n) of the n individuals have a lower error with 0.2 than with that control. That is 7 of 10 people for E1 and 4 of 5 people for E2.

A single control that 0.2 does not clearly beat is enough for the set to fail.

### E3 (secondary)

The same controls are used, with the O'Doherty/Sabes-only encoder as the nearest single source. With one animal, the upper bound comes from the trial bootstrap stratified by session. The count of individuals is replaced by a simpler requirement: 0.2 must have a lower error than the control in both sessions. E3 is reported with this rule and never enters H1.

### H1: the pooled encoder helps on new people

H1 holds if E1 passes and E2 passes. Because H1 needs both sets to pass, running two tests does not raise the chance of a false H1. This kind of test is called an intersection-union test, and it needs no adjustment for multiple tests. Each set is reported separately.

### H2: diversity at a matched amount of data

H2 holds if the composite R of the D_all arm at W_max, minus the mean composite R of the Q arms at W_max, is below 0 with the bootstrap 95% upper bound below 0. Section 11 explains these arms.

### H3: comparison with the task specialists

For each set, 0.2 is compared with that set's task specialist under the same criteria as above. H3 is reported per set, with no overall claim.

### Floors

E1 is scored only if at least 8 of its 10 people have at least 50 eligible forecasts each, and E2 only if at least 4 of its 5 people do. Otherwise the set is reported as insufficient and counts as not passed.

### Reporting

Everything else is secondary and is reported whatever the result. If H1 fails, the result is stated as no evidence that the pooled encoder improves forecasts for new people over the listed controls. Given the history of 0.0, a null result is the expected outcome and will be reported as such.

## 11. Quantity versus diversity

This study asks whether a fixed number of training windows drawn from many sources gives better forecasts than the same number of windows drawn from one source. That comparison is H2 (section 10). The study also measures how the score changes with more windows from one source (the Q arms below) and with more people within one source at the same number of windows (the P arms).

### Common settings

All arms use the size-M transformer with the chosen τ and context. Training crops are 60 steps long (1.2 s, one counted window) and aligned to the counted windows. Batches hold 128 crops. Every arm gets U = 40 × W_max / 128 updates, so every arm sees the same number of steps times batch, and the effective number of passes is reported.

W_max is the smallest number of unique inner-training windows in any Q anchor (below), rounded down to a power of 2. It is computed at step P2.

### The arms

- **Q arms (more data from one source):** the anchors are Gait120, ds003739, Ofner and W-track. Each is trained at W_max/16, W_max/4 and W_max windows, drawn in a fixed hash order.
- **D arms (more sources at the same number of windows):** k = 2, 4 or 8 sources, with 3 hash-ordered draws for each k, from the sources that have at least W_max/8 inner-training windows. Each source gives W_max/k windows. A D_all arm uses every eligible source.
- **P arms (more people within one source at the same number of windows):** Gait120 with 3, 13 or 52 inner-training people, and ds003739 with 2, 4 or 14. The number of windows, W_P, is the largest power of 2 that exceeds neither W_max/4 nor the windows of the smallest level. The people of each level are listed in `ALLOCATION.json`.

**A worked example.** Section 13 expects W_max to be about 2,048 windows, because Gait120's inner-training step segments give about 3,000 windows; the real value is computed at P2. With W_max = 2,048:

- the Q arms use 128, 512 and 2,048 windows of one source;
- the D arms use sources with at least 256 inner-training windows, taking 1,024 windows from each of 2 sources, 512 from each of 4, or 256 from each of 8;
- for the P arms, W_P is at most 512;
- every arm gets U = 40 × 2,048 / 128 = 640 updates.

### Runs, the sealed prediction and scoring

With seeds 20261127, 20261128 and 20261129, there are 36 Q runs (4 anchors × 3 levels × 3 seeds), 27 D runs (3 values of k × 3 draws × 3 seeds), 3 D_all runs and 18 P runs (2 sources × 3 levels × 3 seeds): 84 runs in total.

Before any W_max run, a prediction is sealed. For each Q anchor, a power law (a curve of the form score = a × windows^b) is drawn through the inner-validation scores at W_max/16 and W_max/4, and it predicts the score at W_max. The prediction file is hashed, and its sha256 fingerprint is recorded before the W_max runs start. The prediction can then be checked against the result.

Every arm is scored on inner-validation units (in distribution, meaning the same kind of data it was trained on) before the freeze, and on E1 and E2 after it, with the standard adapters.

## 12. Leak checks

A leak is any way in which test data could reach the training or the model choices. Five checks guard against leaks:

1. The subject identifiers of every training list are disjoint from every evaluation list: no name appears in both. A script checks this before the freeze.
2. File fingerprints are disjoint. Fingerprints of the content are also compared across derived caches and original files, for example area2 against the Dryad deposit, so that the same recording cannot enter twice under different file names.
3. Every evaluation file is downloaded after the freeze commit, and its download time is recorded.
4. No evaluation file path appears in any LOCK record before the freeze.
5. The download records contain no file of AJILE12 participants 08 to 12 and no IBL file. This is checked at the freeze and again after scoring.

## 13. Steps, compute and time

The work runs in ten steps, P0 to P9. The estimates are GPU-hours (hours of GPU time) or wall-clock time as stated.

| Step | Work | Estimate |
| --- | --- | --- |
| P0 | This protocol, the separate review and the lead's commit; the copies of the two tail files that hold only the central directory (done on 27 November, section 3) | 0.5-1 day |
| P1 | Training downloads, paced and by byte ranges where possible: Ofner S1-S7 runs 4-10 (49 files, 4.44 GB); ds003739 sessions 1-3 of the 18 development people (54 recordings, 5.24 GB); Gait120 development TRC/MOT files (426.5 MB); W-track spike times and position (about 1-2 GB); Katmah force plates; the conditional sources are measured first | 5-7 h |
| P2 | Readers for the file formats (MATLAB table objects, NWB, C3D, GDF, WFDB, EEGLAB, HDF5) in the track's own software environment; tokenisation; the role audits of area2 and FALCON M1; the Q1-Q6 records; `MIXTURE-MANIFEST.json` with the re-estimate described below | 1.5-2.5 days of CPU time |
| P3 | Parity checks on the real mixture 1-2 h; τ 4-6 h; size ladder XS-XL about 14 h; core arms about 4 h; context arms 2-4 h; XXL another 10.5 h, only if earned | 25-41 GPU-hours at 16 million steps |
| P4 | Matched BF16 and FP32 runs at S and M | about 10 GPU-hours at 16 million steps |
| P5 | Quantity and diversity arms, the sealed prediction, scoring in distribution | 1-3 GPU-hours if W_max is 2,048 windows (expected, because Gait120's inner-training step segments give about 3,000 windows); otherwise in proportion to W_max (8-14 h at 16,384) |
| P6 | Final 0.2, 3 seeds | at T ≤ 256: L about 11 h, XL about 21 h, L in FP32 about 42 h; at T = 512: up to about 22 h (L), 42 h (XL) and 84 h (L in FP32) |
| P7 | Single-source screen (about 2 h) and full-size retrains of up to 4 sources (the best and the three nearest); random and scrambled encoders; specialists | 14-31 GPU-hours at T ≤ 256 (L or XL); up to about 60 at T = 512 |
| P8 | Freeze: the lead commits `FREEZE.json` with the sha256 of every weight file, adapter and scoring script; then the evaluation downloads (Gait120 S001-S010 members 759 MB; MC_Maze 839 MB; AJILE12 participants 03-07 by byte ranges, about 4-6 GB, measured on the first session) | 2-5 h |
| P9 | Adapters; CPU FP32 issuing of the scored E1 and E2 windows; GPU FP32 passes for everything else, with the CPU check (section 5.5); scoring, bootstrap, reports and a separate reader | CPU issuing at T ≤ 256: 2-8 h (L), 6-19 h (XL); at T = 512: 4-15 h (L), 9-34 h (XL), up to about 77 h (XXL). GPU passes at T ≤ 256: 1.5-10 h (L), 3.5-24 h (XL); at T = 512: 5-38 h (L), 11-91 h (XL). Then about 1 day for scoring, reports and the reader |

### Totals

The central assumptions are 16 million unique steps, T ≤ 256 and a final size of L or XL. At these assumptions the work takes about 60 to 130 GPU-hours and 7 to 11 calendar days, including reviews. At the low end (8 million steps, size L), the GPU total is about 35 hours. At the high end (30 million steps, T = 512, size XL), it rises to about 370 hours and about 4 weeks.

Disk use in the home folder stays under 26 GB: 3-6 GB of tokens and under 5 GB of checkpoints. Raw files are kept only for a short time in temporary space held in memory. Every download records the URL, byte range, bytes and sha256. Training and downloads start only after a separate reviewer admits this protocol and the lead commits it.

### How the estimates were made, and how uncertain they are

- **GPU training.** The measured BF16 rates at 128 steps and batch 128 (section 3) are multiplied by 40 passes of 16 million steps. Example: one L seed takes 40 × 5.6 minutes = 224 minutes, about 3.7 hours, so three seeds take about 11 hours. With batches of 32, the 256-step runs were faster per step-token than the 128-step runs, so the 128-step rates are used for every T up to 256. No run at 512 steps was measured. At widths 384-512, attention takes a larger share of the arithmetic at 512 steps (about 14-18%) than at 128 steps (about 4-5%), and the plain attention method stores score tables that grow with the square of T. A 512-step run is therefore taken to cost 1 to 2 times as much per step-token. This factor is an estimate, not a measurement.
- **Mixture size and passes.** Every training figure scales in proportion to the unique steps of the mixture, and the design range of 8 to 30 million steps is 0.5 to 1.9 times the figures above. The figures also scale with the number of passes the folds choose, at most 40.
- **Padding.** Segments shorter than T are padded, and padded positions cost compute without adding steps. Gait120 step segments hold about 80 steps, so at T = 512 most of a Gait120 row is padding. The padded share at each T is counted at P2 and is not included above.
- **Load.** All rates were measured with the GPU about two-thirds busy with other work and a load average of about 18. Quieter or busier periods can change every time by about ±50%.
- **CPU issuing.** The measured forward rates (6.9 windows per second at M and 2.35 at L, at 256 steps on 4 shared threads) are scaled in three ways. By core parameters, they give about 1.0 window per second at XL and about 0.45 at XXL. For 16 threads, which were not measured, the rates are multiplied by 1 to 3. For the attention share at 512 steps, they are multiplied by 1/1.3 to 1/1.1. The kinematic anchor moves with each issue time, so every issue time needs its own encoder pass. The counts per final-size encoder are:
  - E1: about 9,700-11,400 scored windows (about 570 step segments × 17-20 issue times) and about 64,000-75,000 adaptation windows per input variant;
  - E2: 3,000 scored and 3,000 calibration windows per input variant;
  - E3: about 24-54 issue times per trial (for trials of 1.5-3 s, whose real lengths are unknown until the freeze) over 2,795 train and val trials.

  Seven final-size encoders are scored on each set: 0.2 with 3 seeds, the random and scrambled encoders, and the best and the nearest single-source encoders.
- **Why the issuing route changed.** Issuing every pass on the CPU, as revision 1 required, would take about 45-450 hours at size L with T ≤ 256, and about 200-1,200 hours at T = 512, mostly for E3 and the adaptation windows. Revision 2 keeps every forecast that enters a set-pass rule on the CPU and moves the rest to GPU FP32 with a CPU check (section 5.5).
- **Re-estimate.** Before any model choice, `MIXTURE-MANIFEST.json` records four things: the counted unique steps, the padded share at each T, a GPU speed measurement at 512 steps, and a CPU issuing measurement on 16 threads at sizes M and L on training data. Steps P3 to P9 are then recomputed from them.

## 14. Decisions on the items left to the owner

The project owner's instruction of 27 November 2026 was to continue training the models. It was given with the owner's standing pre-approval to add any openly licensed dataset at the maintainers' discretion. This instruction is the task lease, the authorisation for this protocol's downloads and training. Under it, the lead decided on 27 November 2026 the seven items that revision 1 left to the owner:

1. **Fresh units are spent once, as tests:** Gait120 S001-S010 (E1); AJILE12 participants 03-07 only (E2); MC_Maze full (DANDI 000128) and Large (DANDI 000138) (E3). AJILE12 participants 08-12 are kept back for the earlier maintainer's AJILE12 line and are never downloaded by this track, so that line can continue with them. E2's pass threshold is fixed now at ceil(0.7 × 5) = 4 of 5 people. The optional B1 set (the unopened tasks of the 44 Gait120 validation and confirmation people) stays out.
2. **IBL stays with the earlier maintainer.** The IBL Brain-Wide Map is admitted to neither training nor testing, so E4 is dropped and H1 requires E1 and E2 both to pass. AJILE12 participants 08-12, the Churchland/Nitschke recordings and IBL are not touched.
3. **Consumed test groups stay out of training:** Ofner S8-S12 runs 5-10, Hyser DEV, HYGRIP development, and Gait120 validation and confirmation.
4. **CMU motion capture and FingerFlex stay out.**
5. **Licences:** public weights under CC BY 4.0, with a NOTICE crediting every source and its licence; code under CC0 1.0.
6. **The GPU plan is accepted,** with BF16 as the primary training route and the FP32 check reported (section 5.5). Section 13 gives the time estimates and their uncertainty.
7. **Lease and admission.** The owner's instruction of 27 November is the task lease. The separate reviewer's admission and the lead's commit of this protocol are the scientific admission.

## 15. Rights and publication

### Licences

The public weights will be released under CC BY 4.0, with a NOTICE that credits every source, its licence and the changes made. The NOTICE includes the ODC-By attribution for Hyser, the MIT notice for HYGRIP, and CDLA-Permissive-2.0 for HoloAssist if it is used. The code is released under CC0 1.0.

Kept out of the public weights:

- share-alike and non-commercial data;
- outputs of MyoGen, a simulation package under AGPL-3.0;
- the non-commercial arm and hand parts of the MuscleMimic model package;
- the two datasets without a clear licence (the worm imaging deposit and the SLEAP sample recordings).

### What is published, and when

- **Now:** this protocol (PROTOCOL.md), PROTOCOL.json, `allocate.py` and `ALLOCATION.json`, with this Simple edition beside them. PROTOCOL.md and PROTOCOL.json say that the Simple edition comes with the results. This edition of the protocol was added early, before any test data were opened, and those files were not changed. The results will get their own Technical and Simple editions.
- **Before the freeze:** `MIXTURE-MANIFEST.json` (counts, flags, licences and file fingerprints, with no recording values) and the fingerprint of the sealed scaling prediction (section 11).
- **At the freeze:** `FREEZE.json`.
- **After scoring:**
  - the FP32 weights of the three 0.2 seeds, with a reader that needs only NumPy;
  - the readouts for each set;
  - each individual's errors under their public dataset identifiers;
  - the bootstrap intervals;
  - the H1, H2 and H3 outcomes and every secondary result;
  - the LOCK and RESULT records and the NOTICE;
  - README and METHOD documents in a Technical and a Simple edition, checked by a separate reader.
- **Never:** raw recordings and private participant files.

## 16. Departures and revisions

### 16.1 Revision 2

Revision 2 records the decisions in section 14 and applies the minor points of the separate admission review of revision 1:

- **E2 scores AJILE12 participants 03-07 only.** The pass threshold is 4 of 5 people, and the floor is 4 of 5 people with at least 50 eligible forecasts. `ALLOCATION.json` lists no file of participants 08-12.
- **E4 and every use of IBL are dropped.** H1 is E1 and E2 both passing. The composite R, the quantity-versus-diversity scoring and the Q anchors no longer mention E4 or IBL, and `allocate.py` no longer computes an IBL laboratory order.
- **B1 is not run.**
- **Each set's pass rule names its nearest single-source encoder as a required control,** next to the fold-chosen best one: Gait120-only for E1, Ofner-only for E2 and O'Doherty/Sabes-only for E3. E3, which has one animal, gets a defined secondary rule (section 10).
- **The ridge control's history T_r is chosen by the inner folds** from the same candidate lengths as 0.2's context, instead of being fixed at 16 steps (sections 6 and 8.2). The 16-step history stays in the matched-history arm.
- **PROTOCOL.json now defines j** in E2's eligibility rule as the first frame after the last prior frame, as the Markdown does.
- **The E1 member-list check reads only the central directory.** It no longer fetches the last 262,144 bytes of archive 53167640, which held 108,331 compressed bytes of an E1 member. It reads bytes 1451983325-1452137137, the central directory and the ZIP64 end records, which begin after the last byte of every member's data. `allocate.py` now refuses a file that holds any byte before the central directory.
- **Step P0 was done.** Both design-stage tail files were replaced by copies that hold only the central directory, and the originals were deleted (section 3).
- **The time estimates state what was measured** and how far they extend it (section 13). Because issuing everything on the CPU would take weeks at a 512-step context, only the forecasts that enter a set-pass rule are issued on the CPU. The other passes run in GPU FP32 with a CPU check, and E1 primary passes use a fixed length of min(T, 128) steps (section 5.5).
- **A leak check confirms** that no file of AJILE12 participants 08-12 and no IBL file was downloaded.

### 16.2 Revision 1

The plan that was reviewed before revision 1 merged two draft designs. These points were settled while revision 1 was written:

- ds003739 sessions 1-3 of the development people were not on the project's computer, so they were added to the P1 downloads (5.24 GB).
- HYGRIP EMG has 4 channels at 1 kHz without a verified electrode map, so it enters as unnamed channels. The grip signal is uncalibrated transducer voltage.
- W-track rat JS14 contributes all data recorded before the start of trip 79, a time cut that covers "trips up to 78".
- The P-arm levels use inner-training people (Gait120 3, 13 and 52; ds003739 2, 4 and 14), so that every arm can also be scored on inner-validation people.
- The single-source controls are a size-M screen of every source, followed by full-size retrains (one seed) of the best source and the nearest source for each set.
- The dataset label in the context token is replaced by "unknown" with probability 0.1, so that unseen datasets have a trained token.
- Area2 enters only as the 290 fitting and configuration trials of Han, 7 December 2017. FALCON M1 enters only after a role audit.
- No Van Criekinge group is used, because none was offered. A4 needs protocol version 2.
- τ is chosen at size M with a 2-pass budget and one seed.
- E3 is left out of the H2 composite because it has one animal.
- 0.2 is scored per seed, with errors averaged over the seeds. Forecasts are not combined into ensembles.
- E1's primary measure averages the 12 markers and the 100 ms and 200 ms horizons. LevelWalking Trial01 is not scored for any method.
- The compressed bytes of 23 S010 files in two metadata reads are disclosed, were never inflated, and are covered by a sensitivity row.
- The quantity-versus-diversity study counts 84 runs, fewer than the reviewed estimate of about 145. Its GPU estimate is kept as an upper bound.
- P1 rises to 5-7 h and P2 to 1.5-2.5 days, because of the ds003739 sessions and the role audits.

Any further change needs a new protocol version or revision, a separate reviewer's admission and a commit, all before any evaluation byte is read. Every version and revision stays in the repository.
