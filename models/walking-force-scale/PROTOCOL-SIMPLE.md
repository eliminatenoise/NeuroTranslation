# Walking-force quantity ladder: protocol, Simple edition

[Technical edition](PROTOCOL.md) · [Machine-readable protocol](PROTOCOL.json) · [Allocation script](allocate.py) · [Candidate pool](POOL.json) · [Hash orders](ORDER.json)

This is the Simple edition of protocol version 1, fixed on 27 November 2026. It explains the same rules as the Technical edition, in more words and with examples. It was written after the protocol was fixed and changes none of its rules: those are set in `PROTOCOL.json` and `PROTOCOL.md`, and if a sentence here reads differently, those two files govern. The results will get their own Technical and Simple editions when the work is finished (stage C6, section 14). Sections 1 to 20 below have the same numbers and subjects as the sections of the Technical edition, so a reader can move between the two.

## The plan in brief

**What is tested.** The project has published small computer models that watch the last fifth of a second of a person's walk and forecast what a force plate in the floor will measure over the next tenth of a second. All of them learned from the same 12 people (one of them also from 8 people of a second laboratory). This experiment fits the same models on more people from the same laboratory, in steps from 12 people up to the whole training pool, and measures whether their forecasts become more accurate for people they have never seen.

**Why.** The project works from the presumption that more data, and more varied data, make a model that carries further to new people. That presumption needs fair tests. The published walking-force models learned from the same 12 people, and the same laboratory's release holds about 80 more healthy people who have never been used for anything. That makes a fair test possible within one laboratory: only the number of training people changes.

**Which data, and whose.** Every recording this experiment reads comes from one public dataset: the healthy-adult walking recordings of Van Criekinge and colleagues, released on figshare under CC0 1.0 (a public-domain dedication). Each recording holds force-plate measurements and muscle voltages measured on the skin. The stroke recordings in the same release are not used.

**What counts as success.** The main measure is the change in average forecast error, in newton-seconds, between models fitted on 12 people and models fitted on the largest available number of people, measured on a separate group of new people. For each of three model families the result gets one of four labels fixed in advance: helped, harmed, practically no change, or inconclusive. "Helped" needs a statistically clear fall in error (after a correction for running three tests) with an estimated size of at least 3%. The planning study expects the project's own compact model to gain about 3%, right at that line, so it may well end as "practically no change" or "inconclusive". That is stated here, before any result exists.

**What will be published whatever the result.** Every number the plan names in advance, wins and losses alike, with its uncertainty and its counts; each new person's error by their archive code; the code; the fitted models from the largest training group under CC0; and a series of fingerprint files committed at fixed points, most of them pushed to the public repository before the next stage starts, so that anyone can check that sealed files were not changed later (section 18).

**What is measured, derived, predicted or simulated.** The force and muscle-voltage samples are measured in the laboratory. The model inputs, the force targets and the "new load" labels are derived from those samples by fixed rules (section 6). The forecasts are model predictions. The planning figures and the trend predictions are predictions made before the outcome is scored. No simulated data are used for fitting or scoring; the only generated values are the noise used in one engineering check (G3, section 13).

**The main limits.** One laboratory, one walking task, healthy adults, two force plates, and only sessions whose files name six particular muscle channels. Muscle voltage on the skin is not a recording from nerves. A trend seen across a few training sizes from one laboratory is not a general law (section 1 lists the limits in full).

**Where things stand.** When this was written, no test data had been opened and this part of the project had downloaded nothing. The work waits for the owner's decisions listed in section 20.

## Words used in this plan

- **Force plate**: a flat measuring plate set into the floor. It records how hard a foot pushes on it, 1,000 times per second. This laboratory has four; plates 1 and 2 are used.
- **Newton (N) and newton-second (N·s)**: the newton is the unit of force; for example, a person of 80 kg standing still presses down with about 785 N. A newton-second is force added up over time: 500 N held for 0.1 s gives 50 N·s.
- **Impulse**: force added up over a stretch of time, in N·s. The models forecast the impulse on one plate over the next 100 ms.
- **EMG (surface electromyography)**: the small voltage that working muscles produce, measured with sensors on the skin. It is not a recording from nerves.
- **Walk**: one recorded pass along the 12 m walkway. Each person in the plan contributes three walks.
- **Rung**: one training-set size, counted in people. The set of rungs, from 12 people upward, is the "ladder" of the title.
- **Draw**: one fixed way of choosing which extra people join each rung. There are 10 draws, so a result does not depend on one lucky choice of people.
- **Seed**: the starting number of a model's random choices. Fitting the same model with different seeds shows how much a result varies by chance.
- **Fit**: one run of training a model on a training set.
- **Checkpoint**: a saved file of a model's learned numbers (its weights).
- **Frozen checkpoint**: a model file that has already been published. It is scored exactly as it is and never refitted.
- **Hash (SHA-256)**: a fingerprint of a file or a piece of text, written as 64 letters and digits. The same input always gives the same fingerprint; any change, even of one character, gives a completely different one.
- **Sealed**: a file's fingerprint has been recorded in a commit, so any later change to the file would be noticed.
- **Evaluation group**: the new people on whom the final scores are measured. Their recordings are downloaded only after every model has been fitted.

## 1. The question and the main measure

### What the published models forecast

During a walk, a person steps onto and off the force plates. The published walking-force models are given the most recent 200 ms of measurements and forecast, for one plate:

- the **signed vertical impulse** over the next 100 ms, in N·s. "Signed" means that small negative readings, which occur when an unloaded plate reads slightly below zero, are kept with their sign rather than set to zero;
- the **chance that the plate starts carrying a new load** in the next 100 ms, for example a foot arriving on it.

All of the published walking-force models were fitted on the same 12 healthy people from one laboratory: the Van Criekinge recordings, released under CC0. One of them also used 8 people from a second laboratory, in İzmir. The same Van Criekinge release holds about 80 more healthy people who were never given any role in the project: not for fitting, not for checking and not for testing.

### The question

The question is whether the forecast error falls for people never used before when the same recipes are fitted on more of these people. "The same recipe" means the same model design, the same settings and the same amount of training. Only the data change.

### The main measure, step by step

For each model family f (section 7 describes the three families), the main measure is called Delta_f:

Delta_f = mean over scoreable evaluation people i of [MAE_i,f(N_max) − MAE_i,f(12)]

In words:

1. Take one person i from the evaluation group (new people, never used for fitting).
2. Score family f fitted on the original 12 people. The score is MAE, the **mean absolute error**: the average size of the miss in impulse, in N·s, whether the forecast was too high or too low. Call it MAE_i,f(12).
3. Score family f fitted on the largest available training group, N_max people. Call it MAE_i,f(N_max).
4. Subtract: the error at N_max minus the error at 12. A negative number means the error fell for this person.
5. Average that difference over all evaluation people who can be scored.

Each family is fitted many times at each size, with different seeds and, at the in-between sizes, different draws of people. For each person, the error is first averaged over all those repeat fits of the same size, and only then are people averaged. The measure therefore describes the recipe, not one lucky fit.

The **relative change** is Delta_f divided by the average of MAE_i,f(12) over the same people. Example with made-up numbers: if the 12-person error averaged 2.0 N·s and Delta were −0.08 N·s, the relative change would be −4%, a 4% smaller error.

The amount of training data is counted in **people**, with three walks per person. A person is the natural unit because the plan asks about new people. For every rung the report also gives the numbers of walks, forecast rows, separate new-load onsets, optimizer updates (training steps) and training examples drawn, so that other ways of counting data can be checked.

The 12-person rung is our own new fit of the earlier 12 people with the identical recipe. It is not one of the published model files. Those published files are scored separately as fixed comparisons (section 8).

### Limits stated in advance

These limits are written down now, before any result exists, so that the results cannot be described more broadly than the experiment allows:

- **One laboratory and one task.** Healthy adults walking barefoot along the floor at their own preferred speed. Nothing here says how the models behave for other laboratories, other people, shoes, running, stairs or illness.
- **Two plates.** Plates 1 and 2 cover part of a 12 m walkway. The forecast describes those two plates only.
- **A possible hidden selection.** The results cover only sessions whose files carry six exact muscle-channel names. If the way files were named depended on when they were recorded, keeping only correctly named files would also keep only certain recording periods. The results would then describe those periods, and this is reported with them.
- **EMG is muscle voltage, not nerve activity.** Surface EMG measures muscle voltage on the skin. It is not a nerve recording.
- **Overlapping windows and rare events.** Each 200 ms history overlaps the next one by 180 ms, so neighbouring forecasts share most of their data. The person, not the forecast window, is therefore the unit of analysis. New loads are rare: about two separate onsets per walk.
- **A short trend is not a law.** A trend fitted to three or four training sizes is a short-range extrapolation. It is not a scaling law, and it says nothing about other laboratories, bodies, tasks or species.
- **Equal training steps favour small sets.** The main fits give every rung the same number of training steps, which can favour small data sets. Two secondary arms (S1 and S3 in section 9) check whether a flat result comes from that budget or from the model's size rather than from the data.

## 2. What had been done when this was written

No evaluation, reserved or test data had been opened, and this part of the project had downloaded nothing. A number of checks were made that only read existing files and changed nothing:

- **The archive's table of contents.** A zip archive ends with a table of contents, called the central directory, that lists every file in it with its size, position and checksum. This one is 87,971 bytes long (SHA-256 beginning `96a6b5d9`) and lists 1,016 entries. Reading it says who is in the archive without opening any recording. It was compared with the earlier roster (section 3.3). Of 138 healthy person codes:
  - 26 are listed by the dataset's authors as lacking analog data (force and muscle signals);
  - 1, SUBJ001, is an engineering person;
  - 30 are on the earlier roster;
  - 81 were never assigned to anything.

  One of the 81, SUBJ099, is a boundary case explained in section 3.3. That leaves 80 candidates.
- **How many people pass the muscle-name rule.** In the earlier validation metadata, 3 of 6 people failed the six-name rule (section 4): a generic label such as `Voltage.12` stood where `Voltage.LBF` or `Voltage.LRF` should be. All 36 walks of the 12 fit people passed. So 15 of 18 people checked so far pass, and the failures concern whole people or whole sessions, not single walks.
- **The published model files.** The fingerprints of the frozen published model files were confirmed at repository commit `03e76d4` (section 8).
- **Re-training reproduces the sealed files.** We re-trained the six sealed 12-person compact model files, using our own reader for the recording files and our own copy of the feature calculations. Every number in every weight array came out identical to the sealed files. The files' fingerprints still differ, only because the file format (safetensors) writes its descriptive metadata keys in a varying order. Saved without metadata, three separate runs produced identical files, byte for byte.
- **Re-fitting reproduces the tree models.** The published 12-person tree models, refitted from the same rows, give predictions identical to the sealed tree file down to the last bit.
- **What else the recording files contain.** One already-used fit walk shows that each recording file's description section also holds processed foot events (`EVENT:TIMES`, `EVENT:LABELS`), gait measurements (`ANALYSIS:VALUES`), information about the person (`SUBJECTS`) and about the equipment maker (`MANUFACTURER`). The probe in section 4 never decodes them.
- **Planning used old data only.** Planning studies used only the 12 fit people who had already been used (with 3, 6 or 9 of them for training and 3 held out). They helped set the plan, but they are not evidence about new people.

## 3. The data

### 3.1 Source

The dataset and its article:

- Van Criekinge healthy cohort, figshare `10.6084/m9.figshare.24192480.v1`. Data licence: CC0 1.0.
- Article: Van Criekinge T., Saeys W., Truijen S., Vereeck L., Sloot L. H., Hallemans A., Scientific Data 10, 852 (2023), `10.1038/s41597-023-02767-y`. Article licence: CC BY 4.0.

The exact archive, identified so that anyone can check they have the same bytes:

- File `138_HealthyPiG.zip`, figshare file number 42450060, 463,159,769 bytes, md5 `85235c73455d4df8434810d61517efbb`, storage version `c9jtqYlgGUVrgEUy1JMXkChG6zGtCpvu`.
- Its table of contents runs from byte 463,071,776 to byte 463,159,746 of the archive, SHA-256 `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b`.

How the recordings are timed:

- Body markers (reflective dots tracked by cameras) are recorded 100 times per second.
- Plate forces and EMG are recorded 1,000 times per second, so there are ten force and EMG samples for each marker frame.
- There are four force plates. Plates 1 and 2 are used.

The stroke group in the same release has never been opened by this work and is not part of this plan.

### 3.2 The people in the pool

The file [`POOL.json`](POOL.json) lists every healthy person code, with the reason it is or is not a candidate. For each candidate it also lists the walk files inside the archive: their path, CRC-32 checksum (a short check number for detecting damaged data) and byte range. It was produced by the command `allocate.py pool` from the table of contents alone, without opening any recording.

- **The 80 candidates:** SUBJ002-007, 009, 010, 012, 013, 015, 017-019, 021, 022, 025-037, 041, 042, 045, 046, 049-052, 055, 058-060, 063-065, 067-071, 073, 076, 078-081, 083, 086-088, 090, 091, 093-095, 097, 098, 100-109, 111, 113, 114, 117.
- **Their walks:** 73 people have 3 numbered walks, 6 have 4, and 1 has 5. Their first three walks are 240 files, 228,181,413 bytes in compressed form. The median walk file is 945,890 bytes and the largest 1,839,822 bytes.
- **Which walks count:** each person contributes three walks, namely the three lowest-numbered walks that pass the checks in section 4. Walk numbers play no other role.
- One unnumbered file, `SUBJ101/SUBJ101.c3d`, is ignored.

### 3.3 The earlier roster and the SUBJ099 case

An earlier roster, built from metadata only (SHA-256 beginning `34bf97f3`), assigned 30 people to roles: 12 for fitting, 6 for validation and 12 for testing. It is still waiting for the project owner's admission. This plan neither reassigns nor edits it.

- **The 12 fit people** (SUBJ024, 038, 039, 040, 043, 044, 061, 062, 082, 096, 110, 112) form the 12-person rung. Their 36 walks (31,290,834 compressed bytes) are read where they already sit, in the earlier fit download store, without changing them. Each walk is checked for CRC-32 and size against the archive's table of contents, and for SHA-256 against that store's own readback record. A walk is downloaded again only if a check fails.
- **The 6 validation people and the 12 test people** (test: SUBJ008, 014, 016, 020, 053, 056, 057, 074, 077, 084, 089, 092) are never opened by this work.
- **SUBJ099** is left out of every role and never opened. The reason: the earlier selection program paired each archive entry with the entry after it. The very last file in the archive, `SUBJ99 (3).c3d`, had no entry after it and was dropped, so SUBJ099 seemed to have only two walks. Under the rule as intended, SUBJ099 would have been the second person of the earlier test block, and SUBJ089 would have dropped out. Because the sealed earlier roster still governs, SUBJ089 stays reserved for that test, and SUBJ099 waits for the owner's decision (section 20).

## 4. The header probe and qualification

Before people can be placed in groups, the plan needs to know which of the 80 candidates have usable recordings. The **header probe** finds this out by reading only the descriptive start of each walk file, never the recorded signals.

### Why six named muscle channels are required

The published comparison of tree, linear and NeuroTranslate 0.0 models needs six muscle channels with particular names, because those models expect each input column to be a particular muscle. The project's compact three-pass model does not: it accepts four or six voltage streams without names. The six-name rule exists so that all model families can be compared on exactly the same people. Its possible selection effect (section 1) is reported with the results.

### 4.1 What is read

The probe runs only after three things have happened: this plan has been pushed to the public repository, the code commit (C1b, section 14) has been reviewed, and the owner has given permission to download.

Then, for each of the first three walks of the 80 candidates (240 files), one request downloads only the beginning of that file inside the archive. In detail:

1. Each file in a zip archive starts with a short local header. Call its position in the archive o. The request asks for bytes o up to (but not including) o + 8,704.
2. The local header (its signature, the file name, compression method 8, flags 0, the CRC-32 and the sizes) must match the archive's table of contents exactly.
3. The file's compressed bytes are then unpacked step by step (below). If unpacking has not yet reached the end of the recording's description section, the next 8,192 bytes are requested, and so on, until 65,536 compressed bytes have been read. If the description section still has not been reached, the walk fails with the reason "header not reached".

On the fit walks, the description section took 3,272 to 3,704 compressed bytes. So about 2.1 MB in total is expected for all 240 walks, and never more than about 16.4 MB.

Each recording file (format C3D) has three parts in order: a 512-byte header, a parameter section that describes the recording, and then the recorded data. The probe unpacks the compressed file with a hard limit on how much it produces, and stops at the end of the parameter section, so no recorded sample is ever produced:

1. Unpack the first 512 bytes. Read where the parameter section starts (block p) and where the data start (DATA_START, header word 9).
2. Unpack up to (p − 1) × 512 + 4 bytes. Read the number of parameter blocks, c.
3. Unpack up to H = (p − 1 + c) × 512 bytes, the end of the parameter section. The walk fails unless H ≤ (DATA_START − 1) × 512, which means the parameter section ends before the data begin.

### 4.2 What is decoded and what is kept

Only a short, fixed list of facts is decoded:

- **From the file header**, words 1 to 12 only: where the parameter section starts, the number of tracked points, the number of analog values per frame, the first and last frame, the scale, DATA_START, the number of analog samples per frame and the frame rate. The header's table of events (words 150 to 234) is not decoded.
- **From the parameter section**, the records are stepped through using the length fields that point from one record to the next. Group names are read so the probe knows which group is which. Parameter names are read only inside the groups listed below; everywhere else they are skipped without being decoded.
- **Values are decoded only for:** `ANALOG` USED, LABELS, UNITS, SCALE, OFFSET, GEN_SCALE and RATE; every `FORCE_PLATFORM` parameter; `POINT` RATE, DATA_START, UNITS, FRAMES, USED and SCALE; and `TRIAL:Z_DIRECTION`. All parameter names in the `ANALOG` group are read so that unexpected fields can be detected.
- **Never decoded, logged or kept:** the groups `EVENT`, `EVENT_CONTEXT`, `ANALYSIS`, `SUBJECTS`, `MANUFACTURER` and `PROCESSING`, every other group and parameter, and all marker values.

For each walk the probe stores only: the archive path, the byte ranges read, the SHA-256 of the compressed bytes received, the verdict with its reason codes, the number of analog channels, the number of channels named `Voltage.*` and measured in volts, and which of the 14 exact muscle names are present (kept for description only). The downloaded and unpacked bytes stay in memory and are thrown away after the verdict. No header byte is written to disk.

The same restricted reader, which decodes only the listed parameters, is used later for every person's full walks, including the training people.

### 4.3 Verdicts: Q6, QP and X

Each walk gets one of three verdicts.

A walk is **Q6** if it passes every one of these checks:

| Check | What it requires | What it means |
| --- | --- | --- |
| Native clocks | 100 Hz frames, 1,000 Hz analog, ten analog samples per frame, floating-point storage, Intel byte order | The file is recorded and stored in the same way as the fit walks. |
| Agreement | Header and parameters agree on point count, frame range, DATA_START and analog words per frame; the stored size implied by DATA_START, the number of frames and the bytes per frame matches the unpacked size in the table of contents to within one 512-byte block | The file's own description is consistent with itself and with the archive. |
| Six named muscle channels | Analog labels are unique; `Voltage.LBF`, `Voltage.LERS`, `Voltage.LGAS`, `Voltage.LRF`, `Voltage.LST` and `Voltage.RERS` are each present once, in volts; no `ANALOG` parameter other than USED, LABELS, DESCRIPTIONS, GEN_SCALE, SCALE, OFFSET, UNITS, RATE and GAIN | The six muscle channels the published models use are present and clearly named, and nothing unexpected changes how the voltages are scaled. |
| Plate settings | `FORCE_PLATFORM` USED 4, TYPE [2, 2, 2, 2], ZERO [1, 0], no CAL_MATRIX; `TRIAL:Z_DIRECTION` 5; `POINT:UNITS` mm | Four plates of the same type and the same calibration arrangement as the fit walks. |
| Plate channels | The plate channel table is 4 × 6 with 24 unique, valid columns that do not overlap the six EMG columns; for each plate the labels are `Force.Fx`, `Force.Fy`, `Force.Fz`, `Moment.Mx`, `Moment.My`, `Moment.Mz` with the plate number, in N and Nmm | Each plate's three forces and three turning moments are where they should be, in the expected units. |
| Plate geometry | Four flat plates (corner z = 0), finite corners and origins, origin z > 0, plate normal z = −1 | The plates lie flat in the floor and face the expected way. |
| Scales | Finite, non-zero channel scales and general scale | The numbers that convert stored values into volts and newtons are usable. |

A walk is **QP** if it passes every check except the six-name rule and still has at least four channels named `Voltage.*` in volts. Such a walk lacks the six named channels that the comparison of all families needs.

Any other walk is **X** (unusable).

**From walks to people.** The first three walks of each person are probed. If one of them is not Q6 and the person has a 4th or 5th walk, those are probed too, lowest number first (at most 8 extra requests in all). Then:

- A person is **Q6** if they have at least three Q6 walks. Their three lowest-numbered Q6 walks are used.
- A person is **QP** if they are not Q6 but have at least three walks that are Q6 or QP.
- Otherwise the person is **X**.

Because 15 of 18 earlier people passed, about 67 of the 80 candidates are expected to be Q6, with a 95% interval of roughly 47 to 77. This is a planning figure only; the real number comes from the probe.

**Why the probe may read these headers before groups are set.** The probe touches bytes from people who will later become evaluation or physics-source people, before the groups are applied. This is allowed for two reasons. First, the probe reads only recording settings and channel names, never the recorded signals. Second, the hash order that places people into groups (section 5) was fixed and published before the probe, in `ORDER.json`, which is committed together with this plan. So the verdicts cannot be used to steer who goes where. The separate reviewer accepts this safeguard explicitly when admitting the plan. The probe's receipt, `QUALIFICATION.json`, gives each candidate's class, their three walk numbers and the verdict for each walk. It is committed together with `ALLOCATION.json` at stage C2.

## 5. The single allocation

"Allocation" means deciding which person goes into which group. This part of the project is the only one that writes an allocation for the 80 candidates. The physics-source track, a separate part of the project with its own protocol, copies its group from `ALLOCATION.json` and writes no second allocation. One writer means no person can end up in two conflicting roles.

### 5.1 The hash order

People are put in order by a hash, so that the order is reproducible and nobody can choose it. A hash turns any text into a 64-character fingerprint; sorting people by the fingerprint of a fixed text gives an order that anyone can recompute and no one can arrange.

The fixed text starts with a "tag" built from the dataset's identifier and this plan's own file:

TAG = `10.6084/m9.figshare.24192480.v1|walking-scale|` + the SHA-256 of the committed `PROTOCOL.json`

The **primary order** sorts the 80 candidates by the SHA-256 fingerprint (written in hexadecimal) of TAG + `|SUBJnnn`, smallest first, where SUBJnnn is the person's three-digit code.

Because the tag contains the fingerprint of the finished plan file, the order could not be known until the plan was final. Any change to the plan, however small, would have produced a completely different order. So nobody could have looked at a preview of the order and adjusted the plan to get a convenient one.

The command `allocate.py order` writes the primary order to `ORDER.json`, together with the draw orders, the inner-fold order and the variety-walk positions described below. The command `allocate.py check` recomputes both output files (`POOL.json` and `ORDER.json`) and confirms they match byte for byte.

### 5.2 Group sizes

Let Q be the number of Q6 people found by the probe. Going down the primary order and counting only Q6 people:

- **Evaluation group E:** the first clamp(floor(0.30 Q + 0.5), 12, 24) people. In words: 30% of Q, rounded to the nearest whole number (halves upward), but never fewer than 12 or more than 24.
- **Physics-source group P:** the next clamp(floor(0.15 Q + 0.5), 8, 12) people. In words: 15% of Q, rounded, between 8 and 12. These people are the measured test of the physics-source track. This part of the project never downloads their walks.
- **Training pool T:** all remaining Q6 people.
- **Physics supplement:** every QP person. This part of the project never opens them; they are available to the physics-source track under its own protocol.
- **Unusable:** every X person, listed with the reason.
- **If the training pool would have fewer than 6 people, the ladder is cancelled.** Then no evaluation group is formed, P is taken from the start of the order, and the other Q6 people stay unassigned and unopened.

To make sure rounding cannot differ between computers, both sizes are calculated with whole numbers only, as floor((3Q + 5) / 10) and floor((3Q + 10) / 20), and then kept within their limits.

The evaluation group is given priority over the training pool for a reason. The planning study projects that adding a few more training people barely changes the expected gain, while a larger evaluation group lowers the smallest effect the test can detect (section 12).

What the rules give for some values of Q:

| Q6 people (Q) | Evaluation E | Physics-source P | Training pool T | Training people N at each rung |
| ---: | ---: | ---: | ---: | --- |
| 80 | 24 | 12 | 44 | 12, 18, 24, 36, 56 |
| 67 | 20 | 10 | 37 | 12, 18, 24, 36, 49 |
| 52 | 16 | 8 | 28 | 12, 18, 24, 40 |
| 40 | 12 | 8 | 20 | 12, 18, 24, 32 |
| 26 | 12 | 8 | 6 | 12, 18 |
| 25 | 0 | 8 | 0 | ladder cancelled |

The command `allocate.py sizes` prints this table for every Q from 0 to 80.

### 5.3 Rungs and draws

**Rungs.** A rung is one training-set size. The 12 earlier fit people are in every rung. On top of them, a rung adds a people from the training pool, so a rung has N = 12 + a people. The values of a are:

- 6, 12 and 24, each kept only if it is smaller than T and the largest rung is at least 25% bigger than it, that is (12 + T) / (12 + a) ≥ 1.25;
- plus a = T, the whole training pool, which gives the largest rung, N_max = 12 + T.

Example from the table: with T = 28, adding 24 people would give 36, but the largest rung has 40, and 40 / 36 is about 1.11, less than 1.25. That rung would be almost the same as the largest one, so it is dropped, and the rungs are 12, 18, 24 and 40.

**Draws.** For the in-between rungs, the plan has to choose which training-pool people are added. It does this in 10 different ways, called draws, numbered d = 0 to 9. Draw d puts the training pool in its own hash order, sorting by SHA-256 of TAG + `|rung-draw-d|SUBJnnn`. Rung a of draw d takes the first a people of that order. So within one draw the rungs are nested: the 12-added rung contains the 6-added rung's people, and so on. The 12-person rung and the largest rung are the same in every draw, because they are single fixed sets: no one added, or everyone added.

**Inner folds.** These are used only by the tuned secondary arm G9 (section 9), which picks model settings using the training people alone. Within one fit's training people, each person is ranked by SHA-256 of TAG + `|inner-fold|SUBJnnn`, and their fold is the rank modulo 4. That splits the training people into four fixed parts.

### 5.4 The physics-source group

The physics-source protocol (folder `models/physics-source/`, version 1) takes its measured test from group P. P is drawn from people who pass the six-name rule, so it is comparable with the evaluation group and every comparison model can run on it. The physics-source lead agrees to this choice of people and the size rule before this plan is pushed.

For the physics-source track's own binding file, this plan provides:

- `ALLOCATION.json`, with the P codes and their walk files (path, CRC-32, position and byte range), the training-pool codes, and the physics-supplement codes with their walks that pass the plate checks;
- the input adapter and the code of the compact model family, with their SHA-256 fingerprints, from the code commit C1b;
- no marker inputs: markers are not allowed in this plan, so the physics-source track runs its own marker version, with its own guard against marker data leaking information from the future;
- the EMG rule, which is the six-name rule; every P person passes it;
- a note on folds: our inner folds cover the 12 fit people and each rung's added people, not the 6 earlier validation people, so the physics-source track uses its own fold rule;
- plates 1 and 2 only.

After the training pool has been downloaded, the physics-source track may read those walk files and their arrays from this part of the project's private folder, without changing them. That way there is only one downloader. It never reads evaluation-group files or forecasts.

## 6. The forecasting task

The task is exactly the published walking-force task, with nothing changed. This section describes what goes into each forecast, what comes out, and which forecasts are scored.

### When forecasts are made

- **Forecast times.** A forecast is made at sample t = 199 + 20k of each walk's stored 1,000 Hz clock (k = 0, 1, 2, ...), for every t that leaves a full history. In other words, one forecast every 20 ms, starting once 200 samples have been recorded. Each forecast is made immediately after sample t has been read.
- **Two rows per forecast time.** Each forecast time gives one row for plate 1 and one row for plate 2.

### What the model sees

- **History.** Samples t − 199 to t, that is the last 200 ms, cut into ten consecutive bins of 20 ms each. A bin is valid only if all 20 of its samples are real, finite numbers.
- **Muscle input (EMG).** For each bin, the root-mean-square voltage of each of the six muscle channels `Voltage.LBF`, `LERS`, `LGAS`, `LRF`, `LST` and `RERS`. Root-mean-square is a standard measure of the size of a changing signal. Each stored value is first converted into volts as (raw − OFFSET) × SCALE × GEN_SCALE, using the numbers stored in the file. The voltages are used as recorded: no smoothing envelope, no filter, and no scaling to a person's maximum.
- **Force input.** For each bin, the mean vertical force on the plate being forecast. The stored value of the plate's vertical channel (Fz) is converted as (raw − OFFSET) × SCALE × GEN_SCALE, then multiplied by the plate's normal direction z (−1), so that upward force on the plate is positive. The unit is the newton.

### What the model forecasts

- **Impulse target.** The sum of the plate's upward force over the next 100 samples (t + 1 to t + 100), times 0.001 s, in N·s. All 100 samples must be valid.
- **Plate state.** To decide when a new load starts, each plate's state is followed sample by sample with these rules:
  - the state is *unknown* at the start of a walk and after any invalid sample;
  - it becomes *unloaded* after 20 consecutive samples between −10 and +10 N;
  - from unloaded, a rise past +20 N becomes a *new load*, dated at the moment of the rise, if the next 19 samples also stay at or above +20 N;
  - if the force drops below +20 N before those 19 samples are complete, the state returns to unloaded.
- **New-load label.** Each row is labelled:
  - *positive* if a new load starts in t + 1 to t + 100 and every sample up to its confirmation is valid;
  - *negative* if the state at t is known, samples t + 1 to t + 119 are all valid and no new load starts in t + 1 to t + 100 (a load starting at the very end of the window needs 19 more samples to be confirmed, hence 119);
  - *undefined* otherwise.

### Which rows are scored, and how they are weighted

- **Support (rows that can be scored).** A row is scored for impulse when all six EMG channels and the plate are valid in all ten bins and the impulse target is defined. It is scored for new load when those inputs are valid and the label is defined. Every method is scored on exactly the same rows, so no method gains by skipping hard rows.
- **Weights.** People count equally. Within a person, walks count equally; within a walk, forecast times count equally; within a forecast time, the plates present count equally. These are the published person weights. One person with long walks therefore cannot outweigh another.
- **Two grids.** The full set of forecast times is the primary grid. A second, smaller grid is the published 24-position schedule: per walk, 8 groups of 3 neighbouring eligible forecast times, spread evenly over the times with t < n − 119 (n being the walk's length in samples), which gives 48 plate rows per walk; walks with fewer than 24 eligible times are left out of it. Every method is also reported on this grid as a secondary table, and it is the only grid used for the optional Research Edition (F5, section 8).
- **Inputs that are never used.** Markers (their published paths have been gap-filled and smoothed, which can mix in information from later in the walk), processed gait events, analysis values, modelled forces, measurements of the person, the identity of the person, walk or laboratory, and the time of day or date.

### How each model receives the inputs

The same measurements are arranged in slightly different ways for different models:

- **Compact input** (used by M1, M2, S5 and C4): for each bin, the plate's force divided by 800 N. From bin 4 onwards, it also holds two summaries of the muscle channels: the median and the 80th percentile, across the available channels, of log(1 + RMS / RMS of the earlier bins of the same window). This compares each channel with its own recent past, so the channel names do not matter. A force mask and an EMG-summary mask mark which values are present.
- **Tree input** (used by M3): for each bin, the six EMG values, the forecast plate's force and the other plate's force, each standardised with the mean and standard deviation of that rung's training data, plus eight masks that mark which values are present. These are laid out in one row, together with the last bin, the window means, the change from first to last bin and the persistence impulse: 185 columns in all.
- **Persistence**: the latest bin's mean force times 0.1 s. Example: if the last 20 ms averaged 500 N, the persistence forecast is 50 N·s.

## 7. The models fitted at every rung

No model choice is made anywhere in the main analysis. Each family uses the same published recipe at every rung; only the training data change. That way any change in error comes from the data, not from tuning.

**M1, the compact three-pass recurrent model.** This is the project's own small forecasting model. In order:

1. a causal convolution (it looks for short patterns across neighbouring bins, using only past bins; kernel 3, width 24) with the SiLU activation;
2. a GRU, a recurrent layer that carries a memory along the window;
3. one shared GRU cell applied three times in a row (the "three passes");
4. a linear output that gives a score for the chance of a new load and a correction that is added to the persistence impulse.

It has 7,634 learned parameters. Training: the AdamW optimizer with learning rate 0.002 and weight decay 0.001; 900 updates, each on 128 rows drawn with replacement in proportion to each row's person-equal impulse weight. The training loss is 0.5 × (smooth L1 on the impulse correction + new-load cross-entropy, with the rung's share of new loads used as a fixed offset, weighted by the event weight against the impulse weight). Smooth L1 is an error measure like the absolute error but rounded off near zero; cross-entropy is the usual error measure for probabilities. It runs in 32-bit precision on the CPU, with deterministic algorithms and one thread, so a fit with the same seed always gives the same result.

**M2, ridge and logistic regression on the compact input.** These are standard straight-line methods. They use 61 columns: the compact input laid out in one row, plus the last bin, the window mean and the change in force from first to last bin. Ridge regression with penalty 1 forecasts the impulse correction to persistence; logistic regression with C = 1 forecasts the chance of a new load. People are weighted equally.

**M3, boosted trees on the published tree input.** Many small decision trees, each correcting the previous ones (histogram gradient boosting). Settings: 128 iterations, learning rate 0.065, at least 24 rows per leaf, L2 penalty 0.3, 95 bins, no early stopping, random state 20261124. New load uses trees with 7 leaves (log-loss); the impulse correction uses trees with 31 leaves (absolute error). At N = 12 this is exactly the published tree model.

**Repeat fits.**

- M1 at N = 12 and at N_max: 50 seeds each, 20261124 + j for j = 0 to 49. Seeds 20261124 to 20261126 at N = 12 must reproduce the sealed earlier model files weight for weight.
- M1 at each in-between rung: 10 draws × 5 seeds; draw d uses seeds 20261124 + 5d + s, for s = 0 to 4.
- M2 and M3 always give the same result on the same data, so they are fitted once at N = 12 and once at N_max, and once per draw at each in-between rung.
- A fit that fails stays visible as failed and is never replaced by a new attempt.

Model files are saved in the safetensors format without metadata, so the same fit gives exactly the same bytes; the metadata goes into a separate small file. Earlier files, which were saved with metadata, are compared by their weights.

## 8. Comparison methods and frozen published models

### Simple comparison methods

These need no training (or only a single number from the 12 fit people) and are scored once, on the same rows:

- **C1, persistence.** The latest bin's mean force held for the next 100 ms. The new-load probability is the share of positive rows among the 12 earlier fit people, 0.03725847908677051 (about 3.7%).
- **C2, unconditional.** The same probability, and for impulse the person-weighted median impulse of the 12 earlier fit people, whatever the history shows.
- **C3, linear trend.** A least-squares straight line through the last three bin means, placed at the bin centres (t − 49.5, t − 29.5 and t − 9.5 samples), continued over t + 1 to t + 100 and added up without any clipping: 0.1 s × (intercept + 50.5 × slope per sample). Probability as C1.
- **C4, random recurrent readout** (secondary). M1 with its convolution and recurrent layers frozen at their random starting values, so that only the final output layer is trained. It is fitted at N = 12 and N_max, with 50 seeds each. It shows how much of M1's result needs trained recurrent layers rather than random ones.

### Frozen published models

These published model files, from repository commit `03e76d4`, are scored once, exactly as published:

| | Model file | SHA-256 (beginning) | Fitted on |
| --- | --- | --- | --- |
| F1 | `benchmarks/walking-neural-scaling/checkpoints/three-pass.safetensors` | `9feb39a8` | 12 Belgian + 8 İzmir people, augmented continuation; descriptive comparison only |
| F2 | `load.onnx` and `impulse-residual.onnx` in the same folder | `d08f2d79`, `b6cbe5c0` | 12 Belgian people; at N = 12 the same model as M3 |
| F3 | NeuroTranslate 0.0 expanded: the past-load gate with trainable core, the past-load gate with frozen core, and the two earlier expanded cores | `dd795a15`, `3197e25e`, `da97baca`, `b371040d` | 12 Belgian people; never tested on other people before |
| F4 | `models/force-baselines/common-six.npz` | `aa499793` | 12 Belgian people; penalty chosen on the training pool |
| F5 | NeuroTranslate 0.1 Research Edition, `SENSOR-LOOP-JOINT.safetensors` | `3d9a5a2c` | 12 Belgian people; optional |

"Belgian people" are the Van Criekinge people; "İzmir people" are from the second laboratory. How each one is run and what it is for:

- **F1 and F2** are given their inputs through the published preprocessing files. F1 also learned from the İzmir people, in an augmented continuation of training, and its comparison with our rungs is descriptive only.
- **F2 and M3 at N = 12 are the same model in two formats** (ONNX and scikit-learn). Their agreement is reported on the fit rows (at stage S0) and on the evaluation rows (at stage S-c): the largest difference, and the number of rows that differ by more than the published tolerance of 0.000017 N·s and 0.00000026 probability. This checks the export and does not stop the work, because the ONNX graphs compare inputs with the tree thresholds in 32-bit precision, and a row lying very close to a threshold can fall on the other side of it. F2 is scored from the ONNX graphs as published.
- **F3** is run through its published code, given the six EMG values and the plate's force for each bin. This is the first test of the NeuroTranslate 0.0 walking-force preview on people outside its fitting group. Its named comparison is the trainable-core past-load gate against persistence (section 10).
- **F4** holds 40 candidate settings. For each target, input group and arm, the penalty with the lowest person-equal error on the training-pool people is chosen (impulse MAE for impulse, Brier score for new load); a tie goes to the larger penalty. The choice is sealed at stage C3, before the evaluation group is downloaded. This is the separate check that its own README asks for.
- **F5** runs only if the owner allows it. It needs about 50 to 55 GB of memory and 3 to 6 hours, running alone, and reads its base model files without changing them, checked by SHA-256. It is run on the 24-position grid, one forecast time (both plates) per call, because its outputs depend on how many rows are processed together. If it is not run, the report says it was not issued.
- **Not scored:** the 0.1 Inkling adapter, `strict-fourteen.npz` and the three top-level 0.0 recorded-force files. They need all 14 muscle names and were fitted on only 2 people.

## 9. Secondary arms

Secondary arms are extra comparisons that help explain the main result. Each is reported with its intervals, but they are outside the corrected test families (section 10) and never change a main label.

- **S1, epoch-matched M1.** M1 trained with round(900 × rows_N / rows_12) updates, where rows_N is the number of training rows at rung N. Larger rungs then see their data as often as the 12-person rung sees its own.
- **S2, force only.** M1, M2 and M3 without any muscle input, at every rung. This shows how much the muscle input adds at each rung, and whether that gain changes from N = 12 to N_max.
- **S3, capacity.** A wider M1 (width 96 instead of 24), with the update count matched as in S1. It shows whether a small model is what limits the gain.
- **S4, fixed example budget.** M1, M2 and M3 at each rung above 12, trained on a subsample of training rows equal in number to the 12-person rung's rows. The rows are chosen by hash: ranked by SHA-256 of TAG + `|example-budget|` + N, draw, person, walk, forecast time and plate. This separates the effect of more people from the effect of more examples.
- **S5, trees on the compact input**, with the published comparator settings, at every rung.
- **S6, earlier-EMG timing check.** M1 and M2 at N = 12 and N_max, with the muscle window ending 500 ms before the forecast time in the same walk, and the force history unchanged. Results are compared with the normal, current muscle input on the same rows. The rhythm of walking can still show in the earlier window, so this checks timing; it does not remove the muscle information.
- **S8, subgroups** (descriptive): the plate loaded or unloaded at the forecast time (the state worked out from samples up to t only), plate 1 or plate 2, ten bins of forecast probability to check how well probabilities match outcomes, and separate onsets.
- **S9, ranking** (descriptive) of all families, comparison methods and frozen models at each rung.
- **G8, variety.** At N_max, for M1 (50 seeds), M2 and M3, two training sets with nearly the same number of rows are compared:
  - the 12 earlier people plus every training-pool person with one walk each (the walk picked by SHA-256 of TAG + `|variety-walk|SUBJnnn`, modulo 3);
  - the 12 earlier people plus the first floor(T / 3) people of draw order 0, with all three walks each.

  This tests more different people against more walks per person.
- **G9, tuned.** The settings are chosen instead of fixed: M3's number of leaves from {7, 15, 31}, and M2's penalty from {0.001, 0.01, 0.1, 1} (with logistic C = 1 / penalty). They are chosen separately for each target using the four inner folds of each fit's own training people, never the evaluation people. Ties go to fewer leaves and the larger penalty.

Arm S7 of the reviewed designs, which would have averaged the repeat forecasts into one, is not run.

## 10. How results are measured and judged

### The two error measures

- **Impulse error.** The mean absolute error of the signed impulse, in N·s, with people weighted equally, on the shared scored rows.
- **New-load error.** The Brier score: the average of the squared difference between the forecast probability and the outcome, coded 1 if a new load started and 0 if not, with people weighted equally. Example: a forecast of 0.2 when no new load followed contributes a squared difference of (0.2 − 0)² = 0.04 to the average. Lower is better for both measures.
- **Per person first.** For each person, each repeat fit's error is computed with the published weights. Those errors are averaged over the rung's repeats and draws before people are averaged or resampled.

### Uncertainty: the paired bootstrap

The evaluation group is a small sample of people, so each result comes with a 95% interval that shows how much it could vary with a different sample of people. The interval comes from a **paired bootstrap over people**:

1. Take the scoreable evaluation people, in ascending order of their codes.
2. Draw the same number of people at random, with replacement (some people appear twice, some not at all).
3. Recompute Delta and the relative change for that resample. "Paired" means both rungs are scored on the same resampled people.
4. Repeat 10,000 times. The middle 95% of the 10,000 values is the percentile 95% interval.

The random draws come from `numpy.random.default_rng(20261127)`. They are made once for the people scoreable for impulse, and once more, with a fresh generator and the same seed, for the people scoreable for new load. Each set of 10,000 resamples is then shared by every comparison and by the trend test on that set of people, so all of them are judged on the same resamples.

The two-sided p-value is

p = min(1, 2 × min(1 + #(Delta* ≥ 0), 1 + #(Delta* ≤ 0)) / 10,001)

where Delta* is Delta in one resample and # counts resamples. In words: count the resamples in which Delta is zero or above, and those in which it is zero or below; take the smaller count, add one, double it, and divide by 10,001, with 1 as the largest possible value. Adding one keeps p from ever being exactly zero.

As a sensitivity check, a second bootstrap, which resamples people and then the repeat fits within each person, is reported beside the main interval.

### The smallest effect the test can detect

The **minimum detectable effect** is the smallest relative change the test would detect 80% of the time, at a two-sided level of 0.05:

(1.960 + 0.842) × SD of the per-person differences / √E_s / mean MAE(12)

Here E_s is the number of scoreable evaluation people, and SD is the standard deviation. The same is also given with 2.394 in place of 1.960, which corresponds to the strictest corrected level used below.

### The success rule

There are three main tests, one for each family (M1, M2 and M3). Each tests the impulse error on the full grid, comparing N_max with 12.

Because three tests are run, the chance that at least one shows a false effect is larger than for one test. The **Holm correction** keeps that overall chance at or below 0.05 (the familywise level). It multiplies the smallest of the three p-values by 3, the next by 2 and the largest by 1, and keeps the adjusted values in the same order (an adjusted value is never smaller than the one before it). Example with made-up numbers: p-values 0.01, 0.03 and 0.04 become 0.03, 0.06 and 0.06, so only the first stays below 0.05.

Each family then gets the first of these labels that applies, checked in this order:

1. **Harmed**: adjusted p < 0.05 and Delta > 0 (error rose).
2. **Helped**: adjusted p < 0.05, Delta < 0 and a relative change of −3% or better (error fell by at least 3%).
3. **Practically no change**: the 95% interval of the relative change lies entirely inside −3% to +3%.
4. **Inconclusive**: none of the above. It is reported with the minimum detectable effect, so the reader can see how large an effect the test could have found.

Why 3%: it is about twice the seed-to-seed spread of the published three-pass curve, so a smaller change would be hard to tell apart from the variation that the random start of training causes on its own.

What may and may not be claimed: a statement that the NeuroTranslate compact model gains from more people requires M1 to be labelled **helped**. The planning study projects a gain of about 3% for M1, right at the threshold, so M1 may well end as practically no change or inconclusive. This is stated in advance.

The three Brier-score comparisons (new load) form a second, secondary Holm family with the same labels. Three further numbers are descriptive only: the slope of the rung means against log2 N (the change per doubling of people), the gain per doubling in the upper half of the ladder against the lower half, and the share of people whose error fell.

**Minimum numbers of people.** Main impulse labels need at least 12 scoreable evaluation people. Brier labels need at least 10, among whom both outcomes (new load and no new load) occur. Below these floors every result is descriptive only. People who were assigned to the evaluation group but turn out to have no scoreable rows are reported as such and count against the floors, and the error averages use only the scoreable people.

### The first held test of the NeuroTranslate 0.0 preview

Outside the Holm family, one more comparison is named in advance: the F3 trainable-core past-load gate minus C1 persistence, in impulse error, with a 95% interval, on the full grid and on the 24-position grid used in its model card. If the interval excludes zero, the gate has lower (or higher) error than persistence; otherwise there is no detectable difference.

### Everything else is reported too

Every frozen model and comparison method is also reported against our N = 12 and N_max fits, with paired intervals. Every result named in advance is reported, whichever way it falls.

## 11. Sealed predictions and the trend test

Besides measuring the gain, the plan tests whether the gain can be predicted. Predictions are written down and sealed before the numbers they predict are scored.

- **P0, the planning prior.** From the planning study on the 12 already-used fit people (288 three-pass fits, with matching linear and tree fits), the curve L + a / √N was fitted to the mean errors with 3, 6 and 9 training people. Carried forward, it projects a relative gain from 12 to 49 people of −2.9% for M1, −2.8% for M2 and −9.7% for boosted trees. The planning trees used the compact input, not the published tree input, so the M3 figure is approximate. P0 is a prior expectation only, not evidence.
- **P1, the pool-tail curve.** Made only if T ≥ 32, and sealed at stage C3, before any evaluation byte is downloaded. In each draw, the training-pool people who come after the largest in-between rung have not been seen by that draw's in-between fits or by the 12-person fits. Those fits are scored on these unseen people, the trend forms below are fitted to the curve averaged over draws, and the gain at N_max is predicted.
- **P2, the trend prediction.** After all forecasts are sealed (C4), stage S-b scores only the rungs below N_max on the evaluation people. The trend forms are fitted to those rung means. The point predictions, and the predicted N_max value in every bootstrap resample, are written to `P2-TREND-PREDICTION.json` and committed (C5). Only after that does stage S-c score N_max, the frozen models and the comparison methods. The S-c scoring program refuses to run unless it is given the SHA-256 of the committed P2 file.

### The trend forms

For M1, M2 and M3, trend forms are fitted only when at least three rungs lie below N_max. (With the sizes in section 5.2, Q = 40, 52, 67 or 80 gives three or four such rungs; Q = 26 gives only one, so no trend would be fitted.)

- **Main form:** MAE(N) = L + a / √N, fitted by least squares to the rung means, with L not allowed below zero. This is the form used by the repository's training-scale study. It says the error falls with more people and levels off at L.
- **Competing forms:** MAE(N) = c + b log2 N, a steady change per doubling of people; and carry-forward, which simply predicts that N_max will score the same as the second-largest rung.

### How the trend is tested

The trend uses the same shared bootstrap resamples as section 10. In each resample, the form is refitted to that resample's rung means, and the difference "actual minus predicted" at N_max is taken on the same resample. Then:

- if the 95% interval of that difference contains zero, the trend held;
- if it lies entirely below zero, the error fell faster than predicted;
- if it lies entirely above zero, the error fell more slowly than predicted.

Each form's absolute miss is also reported, together with whether the main form beat carry-forward. The trend code is deterministic and is committed in C1b, before any data are downloaded.

## 12. Power: how large an effect the test can see

From the planning study on the 12 fit people:

- the M1 seed-to-seed standard deviation is 0.146 N·s per person;
- the standard deviation across people of the paired change, after removing seed noise, is 0.19 N·s, about 7% of the error;
- the projected M1 gain from 12 to N_max is about 3%.

If the per-person standard deviation is 6% of the error, the smallest relative effect the test can detect with 80% probability, at a two-sided level of 0.05, is:

| Evaluation people E | Smallest detectable relative effect |
| ---: | ---: |
| 12 | 4.9% |
| 16 | 4.2% |
| 20 | 3.8% |
| 24 | 3.4% |

M3, projected to gain about 10%, is therefore well covered by the test at any of these sizes. M1, projected at about 3%, sits at the decision threshold. If M1 shows no clear gain, the secondary arms S1 and S3 show whether that comes from the matched training budget or from the model's size rather than from the data.

## 13. Engineering checks and stop rules

### Checks before any new data are read

These checks are run in our own software, on the 12 earlier fit people only, before any new byte is read. They make sure the code reproduces the published work exactly before it is used on new people. (Checks G0 to G2 and the tree check already passed in design work; all are re-run at stage S0.)

- **G0, training replay.** Our training code, run on the encoded 12-person cache, reproduces the sealed three-pass model files for seeds 20261124 to 20261126 weight for weight, with the same loss on the last training batch.
- **G1, feature replay.** Our reader for the recording files and our feature code reproduce the 9,946 forecast rows of the 36 fit walks exactly, bit for bit: 9,586 rows scored for impulse, 9,150 for new load, and 324 positive new-load rows.
- **G2, end to end.** From the recording files, to the encoded cache (identical on every key), to the model file: identical weights.
- **Trees.** M3 at N = 12 gives predictions identical to the sealed tree file; M2 and S5 at N = 12 equal the sealed 12-person comparator predictions.
- **G3, past only.** On the fit walks, every sample after the forecast time t is replaced with noise. Every input and every forecast of every method must stay unchanged; this shows that no method can see the future. Forecasts made one row at a time and in batches must agree within 0.0001 N·s and 0.000001 probability (the size of 32-bit rounding). Forecasts are always made in one fixed batch order, so they repeat exactly.
- **F4 refit.** Refitting the 40 common-six candidates with the earlier baseline method (ridge regression solved directly, logistic regression by Newton steps) reproduces `common-six.npz` array for array.
- **Reload.** Every saved model file is loaded again and its forecasts recomputed before it is sealed.

A failed check stops the work before the next download.

### Stop rules

- **No changes after a number is seen.** The plan may not change after P1 or after any interim number. A change needs a new protocol version, a separate admission and new evaluation people.
- **No substitution.** Training walks with no scoreable rows are dropped and counted. Nothing is substituted after qualification.
- **Unscoreable people stay counted.** Evaluation people who turn out to be unscoreable stay in the count as "assigned-unscoreable".
- **Failed fits stay visible.**
- **A failed download check halts the stage.** If the ETag, version, size or CRC-32 of a download does not match, that stage stops.

## 14. Stages, commits and custody

The work runs in a fixed sequence. Stages marked C are commits to the repository, stages marked D are downloads, and S-b and S-c are scoring stages. Each commit seals what came before it, so that the next stage cannot change it unnoticed.

| Stage | What happens |
| --- | --- |
| S0 | Build the software, write and test the code on the 12 fit people, re-run the checks in section 13. No new data. |
| C1 | This protocol, `POOL.json`, `ORDER.json` and `allocate.py`. A separate reviewer admits it; the lead pushes it before any download. |
| C1b | The code (fetch, qualify, extract, three-pass, trees, linear, fit, issue, score, trend) with receipts of the checks; reviewed against this protocol before D1. |
| D1 | The header probe (section 4). |
| C2 | `QUALIFICATION.json` and `ALLOCATION.json`, reviewed before any recorded sample is downloaded. |
| D2 | The training-pool walks. |
| Fits | All fits, the F4 penalty choice, and P1. |
| C3 | `FIT-COMPLETE.json`: the SHA-256 of every model and tree file (taken over the weights), the F4 penalties, and P1. |
| D3 | The evaluation-group walks. |
| Issue | Packets that hold only the histories; forecasts from every method; the N_max forecasts in a separate file. |
| C4 | `FORECASTS-SEAL.json`: the SHA-256 of every private forecast file. |
| S-b | Score the rungs below N_max; fit the trends. |
| C5 | `P2-TREND-PREDICTION.json`. |
| S-c | Score N_max, the frozen models and the comparison methods; an independent replay of every total and of sample rows from each plate. |
| C6 | The results in a Technical and a Simple edition (first draft, rewrite, separate reader). |

**Custody: who can see what.**

- The program that extracts data from the recordings writes the inputs (keys, histories, input masks) and the answers (labels, impulses, answer masks) to separate private files. The forecasting program reads inputs only; a separate scoring program joins the answers. So the forecasting program never has the answers.
- The N_max forecasts sit in their own file, which the S-b scoring program cannot read. This keeps the trend prediction (P2) honest.
- Each stage keeps a chain of records in this order: LOCK, ATTEMPT, checkpoint, reload equality, RESULT, READBACK, SCORE-LOCK.
- The lead pushes C1, C2, C3 and C5 to the public repository before the next stage starts, so each seal has a public time.

## 15. Downloads

| Stage | What is downloaded | Size |
| --- | --- | --- |
| D1, header probe | 240 to 248 walks, partial reads | about 2.1 MB, at most 16.4 MB |
| D2, training pool | 3 × T walks | about 100 to 130 MB (about 0.95 MB per walk) |
| D3, evaluation group | 3 × E walks | about 34 to 68 MB |

Never downloaded by this part of the project: the physics-source and physics-supplement walks, static trials (recordings made while standing still), SUBJ099, the earlier validation and test people, and the stroke group.

How each download is made:

1. Every request starts at the stable file address `https://ndownloader.figshare.com/files/42450060` and follows a fresh redirect, because the signed storage address it leads to is valid for only about 10 seconds.
2. One ranged request then reads from the walk file's local header to the next local header in the archive, that is, exactly one file.
3. The ETag (the server's version tag) and the storage version must equal the values in section 3.1.
4. Each whole file is checked for size and CRC-32 against the archive's table of contents, and its SHA-256 is recorded.

Politeness and failures: at most one request per second, paced inside the downloader by a monotonic clock (one that only moves forward, whatever happens to the computer's time setting). If the server replies 429 (too many requests) or a 5xx server error, the downloader waits 60 seconds and retries once, then stops.

Private receipts record the stable address, the storage host and path, the version, the ETag, the byte range, the number of bytes, the CRC-32 and the SHA-256. The signed parts of the address are removed. In total, about 10 minutes of transfer.

## 16. Computing

Two fixed software setups are used, with these exact versions:

- **Runtime A:** CPython 3.13.15, torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0. Used for M1, C4, S1, S3 and F1.
- **Runtime B:** CPython 3.12.14, numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0. Used for M2, M3, S5, G9, F2, F3, F4 and all scoring.

Exactly one thread is used per fit, because two threads change the learned weights, and a different torch build changes weights by up to 0.22. At most 12 single-thread fits run side by side on CPUs 20 to 31, with control work on CPUs 16 to 19: at most 16 threads in total.

Measured times: one M1 fit (900 updates) takes 1.5 to 4 seconds. One tree fit takes 4.6 seconds at 9,586 rows, and about 52 seconds for three leaf settings and both targets at 48,000 rows. In all there are about 250 main and 1,450 total M1 fits, about 550 tree fits and 650 linear fits: about 4 to 8 core-hours, or 30 to 60 minutes of real time. The private folder stays under 0.7 GB.

## 17. Rights

- The Van Criekinge recordings are CC0 1.0 and the article is CC BY 4.0. Both are credited.
- The weights fitted in this ladder come only from Van Criekinge CC0 recordings. They are released under CC0 1.0 with a NOTICE that credits the dataset and the article and describes our processing.
- Some frozen models are only scored here, never refitted or redistributed:
  - F1 inherits data from İzmir (CC BY 4.0, `10.48623/aperta.286865`);
  - F3's core inherits training on worm imaging (Zenodo `10.5281/zenodo.19388374`) and SLEAP sample tracks;
  - F5's base model is Apache-2.0 with its acceptable-use policy.

  Scoring a model is not training on its sources. The results state each model's lineage.
- Material from İzmir, MoVi, the worm data, SLEAP, MuscleMimic and MyoGen never enters the ladder weights.
- The recording files, arrays, forecasts and answers stay in this part of the project's private folder and are never committed.

## 18. What will be published

All of the following is published whatever the result:

- **Now:** `PROTOCOL.md`, `PROTOCOL.json`, `allocate.py`, `POOL.json` and `ORDER.json`.
- **At C1b:** the code and the receipts of the checks.
- **At C2:** `QUALIFICATION.json` and `ALLOCATION.json`.
- **At C3:** `FIT-COMPLETE.json`.
- **At C4:** `FORECASTS-SEAL.json`.
- **At C5:** `P2-TREND-PREDICTION.json`.
- **At C6:**
  - `RESULTS.json`, with every number, interval and count named in advance, and each evaluation person's errors listed by archive code;
  - the results in a Technical and a Simple edition;
  - the M1 model fitted on N_max people (seed 20261124), saved without metadata, with its metadata file; the M3 trees fitted on N_max people as ONNX graphs checked against scikit-learn; and the M2 coefficients fitted on N_max people; all under CC0 with a NOTICE;
  - the download receipts, with the signed addresses removed.

## 19. Time estimates

These assume the owner gives download permission and admission on 28 November 2026:

| Step | When | Machine time |
| --- | --- | --- |
| S0 and code commit C1b | 28 November | about half a day |
| D1 and C2 | 28 to 29 November | minutes of download, hours of review |
| D2, fits and C3 | 29 November | about 10 min of download, 30 to 60 min of computing |
| D3 to S-c | 29 to 30 November | minutes of download, under 1 h of computing |
| Results editions and separate reader | 30 November to 1 December | about a day |
| F5, if admitted | after S-c | 3 to 6 h, running alone |

The whole run takes about two days after admission. The review steps, not the computing, set that time.

## 20. Decisions waiting for the owner

1. A task lease (permission) and scientific admission for the downloads after this protocol is pushed: the header probe (about 2 to 16 MB), the training pool (about 100 to 130 MB) and the evaluation group (about 34 to 68 MB).
2. Agreement to spend the last fresh pool of healthy Van Criekinge people (80 people) on this ladder, the physics-source group and the physics supplement. Afterwards, only the earlier 12-person test group and the stroke group remain unopened.
3. SUBJ099: keep it unopened (the default here) or include it.
4. Whether to score the optional Research Edition (F5).
5. A courtesy confirmation that this part of the project is the only allocation writer for the 80 never-assigned people, because the earlier roster's owner holds the source line and that roster is still waiting for admission.
