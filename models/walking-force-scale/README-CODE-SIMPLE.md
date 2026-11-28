# Walking-force quantity ladder: run code, Simple edition

[Technical edition](README-CODE.md) · [Results, Simple edition](README-SIMPLE.md) · [Results](README.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Machine-readable protocol](PROTOCOL.json) · [Choices left to the code](DECISIONS.md) · [Sources and terms](NOTICE.md)

This is the Simple edition of the guide to the run code of the walking-force quantity ladder. It explains in ordinary words what the code in this folder does, what each stage of the run did and when, which files stay private and why, and how a reader can check the published records. Every stage up to the final scoring ran on 27 November 2026. All times in this guide are in UTC (Coordinated Universal Time) on that day. The results themselves are in [README-SIMPLE.md](README-SIMPLE.md) (Simple edition) and [README.md](README.md) (Technical edition). The Technical edition covers the same material more briefly. The rules of the experiment are set in the protocol; if anything here reads differently from [PROTOCOL.json](PROTOCOL.json), PROTOCOL.json governs.

## The experiment in brief

The project has published computer models that read the last 200 milliseconds (ms) of measurements from a person's walk and forecast what one force plate in the floor will measure over the next 100 ms. The measurements are the force on two force plates and the voltage of six leg and back muscles, measured on the skin. The forecasts are the force added up over the next 100 ms (the impulse, in newton-seconds, N·s) and the chance that the plate starts carrying a new load, such as a foot arriving on it. All of these models learned from the same 12 people, taken from one laboratory's public recordings: the Van Criekinge healthy-adult walking dataset, released under CC0 (a public-domain dedication). One of them also used 8 people from a second laboratory.

The same dataset holds 80 more healthy people who have never been given any role in the project; they are the candidates of this experiment. The experiment fits the same model recipes on more of these people, in steps from 12 people up to all the available training people, and measures whether the forecasts become more accurate for new people who were not used for fitting. Each step is called a rung, so the set of steps is a ladder. The rules were written and published before any of the 80 people's recordings was read. They are in the protocol: [PROTOCOL.md](PROTOCOL.md) (Technical edition) and [PROTOCOL-SIMPLE.md](PROTOCOL-SIMPLE.md) (Simple edition).

The code in this folder carries out those rules one stage at a time. Each stage has a short name. Stages whose names start with D download data. Stages whose names start with C save a record file in the public repository, so that any later change to what was sealed would be visible. The order is part of the design: the recordings of the people used for the final scores are downloaded only after every model has been fitted and the fingerprints of all fitted models have been saved.

| Stage | What it does | State (times are UTC on 27 November 2026) |
| --- | --- | --- |
| C1 | Publish the protocol | Done: NeuroTranslation commit `3f2bae7`, pushed at 11:33:22 |
| S0 | Build the software and check the code on the 12 earlier people only | Done: all 15 gates and all 4 tests passed |
| C1b | A separate reviewer checks the code against the protocol | Done: no blocking or major problem, 8 minor ones. The fixes were committed at 11:54:47 and checked in the C2 review |
| D1 | Read only the file headers of the 80 candidates' walks, to see which files qualify | Done, from 11:55:07 to 12:03:58 |
| C2 | Split the qualified people into groups, by the fixed published rule | Done, and reviewed separately: no blocking or major problem in the probe records or the groups. The groups were committed at 12:04:59 (commit `8a8fab5`), the texts corrected after the review at 12:53:48 (commit `0fc1bb7`), and both were pushed at 13:04:52 |
| D2 | Download the walks of the training people | Done, from 13:08:41 to 13:14:17: 105 walks of 35 people |
| Extraction and fits | Turn walks into model inputs; fit every model | Done. Extraction at 13:14:45, about 2 seconds. Fits from 13:15:28 to 13:47:10: 1,742 of 1,742 fitted, none failed |
| C3 | Save the fingerprints of every fitted model | Done: written at 13:51:31, committed at 13:52:48 (commit `4652d69`), reviewed separately (no blocking or major problem) and pushed at 14:03:24 |
| D3 | Download the walks of the evaluation people | Done, from 14:06:17 to 14:09:36: 60 walks of 20 people. Their extraction took 1 second, at 14:09:47 |
| Issue | Make forecasts for the evaluation people | Done, from 14:09:58 to 14:53:18 |
| C4 | Save the fingerprints of every forecast file | Done: written at 14:54:10, committed at 14:54:24 (commit `be66803`) and pushed at 15:08:44 |
| S-b | Score the smaller rungs and predict the result of the largest | Done, at 14:54:32, in under 1 second |
| C5 | Save that prediction | Done: committed at 14:55:40 (commit `46d27d6`). C4, S-b and C5 were reviewed separately (no blocking or major problem) and pushed at 15:08:44 |
| S-c | Score everything else and recompute the main numbers independently | Done: the scoring from 15:11:08 to 15:11:17, the recomputation from 15:11:32 to 15:11:34 (it passed). `RESULTS.json` was committed at 15:14:37 |
| Supplement | Compute extra tables from the same sealed forecasts; not a stage of the protocol | Done, from 22:08:28 to 22:08:42, after S-c. `RESULTS-SUPPLEMENT.json` was committed at 22:14:39 |
| C6 | Publish the results | The two results editions and the notice are written. The fitted models of the largest rung are not exported yet (see [Open items](#open-items)) |

A commit time is the author time recorded in the commit itself, that is, the time at which the commit was first made. A push time comes from this computer's record of each push. [What each stage did](#what-each-stage-did) gives the details of every row.

## Words used in this guide

- **Script**: a program file, here written in Python and ending in `.py`. Scripts are started by typing a command in a terminal (a text window for commands).
- **Runtime**: one fixed installation of Python together with fixed versions of the add-on packages it uses. Two runtimes are used, called A and B. The versions are fixed because a different version of a package can change the fitted numbers.
- **Repository, commit, push**: the project's files are kept in a public repository that stores every saved version. A commit is one saved version, identified by a short code such as `3f2bae7`. Commits are first made on the project's computer; pushing copies them to the public repository, where anyone can see them and the order in which they were made. The clock times of commits and pushes given in this guide are this computer's own records.
- **sha256 fingerprint**: a 64-character code computed from a file's bytes. The same bytes always give the same code; changing even one byte gives a completely different code. This guide often shortens a fingerprint to its first 8 characters followed by "…".
- **Seal**: a file, or its fingerprint, recorded in a commit, so that any later change would be noticed.
- **Archive and member**: the whole dataset is one zip file of 463,159,769 bytes on figshare, called the archive. Each file inside it is a member. Each walk is one member.
- **Central directory**: the archive's table of contents, stored at its end (87,971 bytes). It lists every member's name, position, sizes and CRC-32.
- **CRC-32**: a short checksum of a file's contents, used to detect damaged bytes.
- **Local header**: the short record in front of each member that repeats its name, compression method, sizes and CRC-32.
- **C3D file**: the file format of the recordings. Each file starts with a header and a parameter section (channel names, units, scale factors, plate positions and similar settings), followed by the samples, which are the measured values.
- **Ranged read**: a request for a stated span of bytes of the archive instead of the whole file.
- **Redirect and signed address**: a request to the dataset's stable address is answered with a temporary storage address, which works for about 10 seconds. Each read asks for a new one.
- **429 and 5xx**: answers a server can give, meaning "too many requests" (429) and "server error" (500 to 599).
- **Lease**: the project owner's permission for a download stage.
- **Q6, QP, X**: the classes a walk or a person can get in the header probe. Q6 means the file passes every check, including the presence of six named muscle channels. QP means it passes every check except the six names but has at least four muscle-voltage channels. X means it fails some other check. Section 4.3 of the protocol gives the full list.
- **Groups**: the evaluation group (E) is the new people on whom the final scores are measured. The physics-source group (P) belongs to a separate part of the project and is never downloaded by this code. The training pool (T) is the people added to the 12 earlier people at the rungs. The physics supplement is the QP people, also never downloaded here.
- **Supplement**: extra tables computed after the final scoring from the same sealed forecasts, and saved as `RESULTS-SUPPLEMENT.json`. It is not the physics supplement, which is a group of people.
- **Hash order and salt**: a fixed order of people. The code computes the sha256 fingerprint of a fixed text followed by each person's code and sorts the people by these fingerprints. Nobody can choose this order or work it out in advance. The fixed text is called the salt. Here it is made of the dataset's identifier, a fixed label and the fingerprint of PROTOCOL.json, so no order could be known before the protocol was final, and each use adds its own label, for example one for the group order and one for each draw (protocol section 5.1).
- **Rung, draw and N_max**: a rung is one training-set size, counted in people. A draw is one fixed way of choosing which extra people join a rung; there are 10, so a result does not depend on one lucky choice. N_max is the largest rung, with every training-pool person.
- **Inner folds**: the four groups into which a fit's own training people are divided by a hash order. Only the tuned arm G9 uses them (see below).
- **Fit, seed, checkpoint**: a fit is one run of training a model. A seed is the starting number of a model's random choices; fitting with several seeds shows how much a result varies by chance. A checkpoint is the saved file of a fitted model's numbers.
- **Model families**: M1 is the project's compact three-pass recurrent model, a small neural network that reads the 200 ms history one 20 ms step at a time and keeps a running memory of what it has read. M2 is ridge and logistic regression, straight-line models (ridge for the impulse, logistic regression for the chance of a new load). M3 is boosted trees: many small decision trees, each one correcting the errors of the trees before it.
- **Compact input and tree input**: the two published ways of summarising the 200 ms history for a model (protocol section 6). The compact input, read by M1, M2, S5 and C4, gives for each 20 ms step the force on the plate and, from the fourth step on, two summaries of the muscle signals, with marks for missing values. The tree input, read by M3, gives for each step the six muscle values and the forces on both plates, with marks for missing values and a few summary columns: 185 columns in all.
- **File types**: `.json` and `.jsonl` files are plain text records (one record per line in `.jsonl`); `.npz` files hold arrays of numbers for NumPy, a Python package for numerical work; `.safetensors` and `.joblib` files hold saved models.
- **Arms**: variants used for side questions (protocol section 9). They are reported with their own uncertainty and never change the label of a main result.
  - S1: M1 given more training steps at larger rungs, so that each row is seen as often as at 12 people.
  - S2: force only, no muscle signals (for M1, M2 and M3).
  - S3: a wider M1 (width 96), trained like S1.
  - S4: the same number of training rows at every rung, to separate more people from more rows.
  - S5: boosted trees on M1's compact input.
  - S6: muscle signals from a window that ends 500 ms before the forecast time.
  - G8, the variety arm: at N_max, two training sets with nearly the same number of rows, called the variety sets. One has the 12 earlier people plus all 35 training-pool people with one walk each (the walk is picked by a hash order). The other has the 12 earlier people plus 11 training-pool people with three walks each. The comparison asks whether more different people help more than more walks from each person.
  - G9, the tuned arm: the main fits use fixed settings, but G9 chooses one. For M3 it chooses the number of leaves per tree (7, 15 or 31; more leaves make larger trees), and for M2 the penalty (0.001, 0.01, 0.1 or 1). The choice uses only the fit's own training people: each setting is fitted on three inner folds and tested on the fourth, in turn, and the setting with the lowest average error is kept.
- **Controls (C1 to C4)**: simple reference forecasts (protocol section 8). C1, persistence, holds the latest 20 ms average force for the next 100 ms. C2 always gives the median impulse and the new-load rate of the 12 earlier people. C3 extends a straight line through the last three 20 ms force averages. C4, the random-readout control, is M1 with its inner layers left at their random starting values and only its final output layer trained; it shows how much of M1's result needs trained inner layers. The controls share the names C1 to C4 with stages C1 to C6; the context makes clear which is meant.
- **Frozen checkpoints (F1 to F5)**: models published earlier, scored as they were published. F4, the published force baselines, are straight-line models stored with four penalty settings each; one setting is chosen on the training-pool people before any evaluation walk is downloaded. F5 is optional; it was not admitted, and no forecast was made with it.
- **Penalty**: a setting of a straight-line model that pulls its weights towards zero. A larger penalty gives a simpler, more cautious model. The penalty is chosen only for F4 and in G9; everywhere else it is fixed by the protocol.
- **Bootstrap and resamples**: a way to measure how much a result depends on which people happened to be in the evaluation group. A resample is a group of the same size drawn at random from the evaluation people with replacement, so one person can appear more than once and another not at all. The result is recomputed on each of 10,000 resamples, and the middle 95% of the recomputed values gives the 95% interval. The bootstrap is paired: in each resample, the two models being compared are scored on the same people.
- **p-value**: a number between 0 and 1, computed here from the bootstrap. It is small when nearly all resampled differences fall on the same side of zero, so the direction of the change is unlikely to come from the choice of people alone. Section 10 of the protocol gives the exact formula. The three main tests, one per model family, are corrected together by the Holm method: the smallest p-value is multiplied by 3, the next by 2 and the largest by 1, so that running three tests does not make a chance result look clear.
- **Trend forms**: two simple curves fitted to the average error at each rung, to predict the error at N_max. In the first, error = L + a / √N: the error falls towards a floor L as the number of people N grows. In the second, error = c + b × log2 N: the error changes by the same amount b each time N doubles. A third, simpler competitor carries forward the error of the second-largest rung. The trend test compares the actual error at N_max with these predictions (protocol section 11).
- **P1 and P2**: two sealed predictions of the error at N_max. For P1, the 12-person fits and each draw's middle-rung fits are scored on that draw's 11 training-pool people who are in none of its middle rungs; the averages over the 10 draws form the P1 curve, and the trend forms are fitted to it. P1 is sealed before any evaluation walk is downloaded. P2 fits the trend forms to the evaluation scores of the rungs below N_max and is sealed before N_max is scored.
- **EMG**: surface electromyography, the voltage of working muscles measured on the skin. It is not a recording from nerves.
- **Private folder**: a folder on the project's computer that is never committed or published.
- **Environment variable**: a named setting that the terminal passes to every program it starts, for example `OMP_NUM_THREADS=1`.

## What each stage did

### The protocol (C1)

The protocol was published at NeuroTranslation commit `3f2bae7` together with three companion files: `allocate.py` (the script that splits people into groups), `POOL.json` (the 80 candidates and the archive positions of their walks) and `ORDER.json` (the fixed hash orders that decide group membership). Their fingerprints are listed in [Checking the published records](#checking-the-published-records).

### Engineering checks on the 12 earlier people (S0)

Before any new byte was read, the code was checked on the 12 people whose walks were already used for the earlier models (36 walks), and on made-up numbers. Nothing was downloaded. The checks are called gates. All 15 passed:

- **G0, training replay**: our training code, given the earlier encoded data, reproduces the three sealed 12-person checkpoints of M1 exactly, number for number, with the same final training loss.
- **G1, feature port**: our file reader and input code reproduce the 9,946 forecast rows of the 36 walks bit for bit.
- **G2, end to end**: from the raw files to a fitted checkpoint, our whole path reproduces the sealed checkpoints exactly.
- **Trees R0**: M3 fitted on the 12 people gives exactly the predictions of the sealed tree file.
- **M2 and S5 R0**: the same for M2 and S5.
- **G3, past only**: replacing every measurement after the forecast time with noise changes no input and no forecast of any method, so no forecast can use the future.
- **One row against batches, fixed order**: a forecast made one row at a time agrees with one made in batches, within 32-bit rounding, and a repeat in the fixed order gives identical bytes.
- **F4 refit**: refitting the published force baselines reproduces their file array for array.
- **Q6 on the 36 fit walks**: all 36 walks pass the walk checks through the same probe code D1 uses.
- **Whitelist reader**: the file reader decodes nothing outside its list of allowed fields.
- **Tree-input cache**: our tree inputs equal the earlier ones on all 9,586 rows.
- **C1 and C2 reference**: the prevalence of new loads in the 12 earlier people (how often a new load starts in their rows, 0.03725847908677051) and their median impulse, which the controls C1 and C2 use, are recomputed exactly.
- **Reload equality**: every saved checkpoint, loaded again, gives identical forecasts.
- **Reference checkpoints match the protocol pins**: the sealed checkpoints compared in G0 and G2 have the fingerprints the protocol records.
- **C4 readout smoke**: the random-readout control trains and runs.

All 4 tests passed as well; they are described in [The files in this folder](#the-files-in-this-folder). The largest test, a smoke run, carried every stage from the header probe to the final replay on the 12 earlier people with fewer seeds: it completed 126 of 126 fits, and its independent replay differed from the scorer by at most 5.3e-14 (0.000000000000053) on 36 averages and by 0 on 12 recomputed targets. The results are in [S0-GATES.json](S0-GATES.json).

### Code review (C1b)

A separate reviewer reran the key checks and read the code file by file against the protocol. The verdict was a pass with no blocking and no major problem, and 8 minor problems. Five are fixed or recorded. Of the other three, the sharing of the processor was handled in the run by a private arrangement, without a change to the code; the custody finding was fixed in part (the folders), and its other part (a commit check in D3) was covered by the order of the push and the download; and this guide, brought up to date after the run, still needs its separate reader. See [What the reviews found](#what-the-reviews-found). The fixes were made after this review and before the header probe. They were first checked in the separate review of stage C2, which found them correct.

### The header probe (D1)

**Purpose.** The comparison of model families needs six muscle channels with fixed names in each file. Some sessions in this dataset use generic names instead, so each candidate's files had to be checked before the groups could be formed. The probe reads only the beginning of each file: the C3D header and parameter section, which hold the channel names, units and plate settings. It never produces a measured value.

**How it reads.** For each walk, the code makes one ranged read of 8,704 bytes, starting at the member's local header. It checks that the local header matches the central directory. It then decompresses the bytes with a hard limit that stops exactly at the end of the parameter section, so the decompression can never reach the measured samples. It decodes only the fields on an allowed list (for example the analog channel labels, units and scale factors, and the force-plate settings); fields such as processed gait events, analysis values and subject details are never decoded. If 8,704 bytes had not been enough, it would have asked for 8,192 more at a time, up to 65,536 bytes. It keeps only the verdict, the reasons, a few channel counts and the fingerprint of the compressed bytes received; no header byte is written to disk.

**What was read.** The probe ran on 27 November 2026 from 11:55:07 to 12:03:58 UTC, about 9 minutes. It read 241 walks: the three lowest-numbered walks of each of the 80 candidates (240 walks) and the 4th walk of SUBJ060, whose 2nd walk failed the six-name rule. Each walk needed two requests, the redirect and the ranged read, so there were 482 requests and 2,097,664 bytes received in all. Every ranged read was answered normally (status 206, "partial content") with the expected archive version and fingerprint (ETag). No request had to be repeated and no walk needed more than the first 8,704 bytes. On all 241 walks the decompression stopped at the end of the parameter section, so no measured sample was produced.

**Which code ran.** The probe ran on the code checked in the C1b review plus the fixes for that review. The fixes were committed 20 seconds before the probe started, so they had not yet been reviewed; the C2 review checked them afterwards and found them correct. The fixes that the probe uses (items 13 and 14 of [DECISIONS.md](DECISIONS.md)) change only what happens when a request must be repeated or the stage must halt. Neither happened: every read succeeded at the first attempt, and no local header differed from the central directory. So the verdicts are the ones the reviewed code would have given.

**What it found.** Walks: 205 Q6, 30 QP and 6 X. People: 65 Q6, 11 QP and 4 X. A person is Q6 with at least three Q6 walks, and then the three lowest-numbered Q6 walks are used; this is why SUBJ060 uses walks 1, 3 and 4.

**Records.** The verdicts are in [QUALIFICATION.json](QUALIFICATION.json). The request log and the walk log are in the `receipts` folder. They name the storage host and path but never the temporary signed part of the address.

**A note on the lease note.** The probe records the lease note it was given, word for word. That note says "C1b reviewed 28 Nov". The review was finished, and the probe run, on 27 November 2026; the receipts give the exact UTC times.

### The single allocation (C2)

The script `assign.py` applied the published split rule to the probe's verdicts. The rule walks down the fixed hash order (published before the probe, so no verdict could steer who goes where), counting Q6 people only. With 65 Q6 people:

- the first 20 form the evaluation group E;
- the next 10 form the physics-source group P;
- the remaining 35 form the training pool T.

The rungs are 12, 18, 24, 36 and 47 people: the 12 earlier people plus 6, 12, 24 or all 35 training-pool people. The three middle rungs each have 10 draws, and within a draw the rungs are nested (each rung contains the people of the smaller one). Because the training pool has at least 32 people, an extra sealed prediction called P1 is made: for each draw, the 11 training-pool people who are not in that draw's intermediate rungs serve as unseen people for an early estimate of the trend. The 11 QP people form the physics supplement. The 4 X people are unusable; their reasons are recorded (for example a plate channel layout or plate geometry that fails the checks). SUBJ099 stays out of every role and unopened, as the protocol says. Every group and walk list is in [ALLOCATION.json](ALLOCATION.json).

**The review of C2.** A separate reviewer checked this stage on 27 November 2026. The reviewer compared every line of the probe's request log with the archive's table of contents, using a reader written independently of ours; rebuilt `QUALIFICATION.json` from the two logs and `ALLOCATION.json` from `QUALIFICATION.json`, and got identical bytes both times; and recomputed the groups, rungs, draws, folds, P1 groups and variety sets from the protocol's rules with separate code. No blocking or major problem was found in these records. The reviewer's findings on this guide, its Technical edition and DECISIONS.md are listed in [What the reviews found](#what-the-reviews-found).

**When it became public.** The groups were committed at 12:04:59 (commit `8a8fab5`). The corrections to the texts that followed the review were committed at 12:53:48 (commit `0fc1bb7`). One push at 13:04:52 made both public, before the training-pool download began.

### The training-pool download (D2)

**What was downloaded.** D2 began at 13:08:41, after the allocation had been pushed, and ended at 13:14:17, the time written in its receipt: 5 minutes 36 seconds. It downloaded the 105 walks of the 35 training-pool people. Each walk needed two requests, the redirect and one ranged read of the whole member, so there were 210 requests. Every ranged read succeeded at the first attempt, with status 206 and the expected archive fingerprint (ETag) and version.

**How many bytes.** 98,801,524 bytes were received. Each read runs from a walk's local header to the local header of the next member. Of the bytes received, 98,793,925 are the compressed walks, which is the figure given in `ALLOCATION.json`, and the other 7,599 are the local headers. Decompressed, the walks take 165,541,248 bytes.

**Checks.** Every decompressed walk had the size and the CRC-32 that the central directory lists for it. A second, private pass recomputed the size, the CRC-32 and the fingerprint of all 105 stored walks and found no difference.

**Records.** The request log `D-training_pool-requests.jsonl` and the download receipt `D2-RECEIPT.json` are in the `receipts` folder. They were committed at 13:52:58 (commit `c6e6909`).

### Extraction, the fits, P1 and the fit seal (C3)

**Extraction.** At 13:14:45 the extraction turned the walks into model inputs and targets, in about 2 seconds. It read 141 walks of 47 people (the 12 earlier people and the 35 training-pool people) and made 42,030 rows; a row is one forecast time on one plate. Every walk gave usable rows. The 12 earlier people give 9,946 rows, of which 9,586 have an impulse target and 9,150 a new-load label: the same counts as in the engineering checks. The 35 training-pool people add 32,084 rows (31,034 with an impulse target, 30,579 with a new-load label).

**The fits.** The job list has 1,742 fits. All were completed and none failed, and every saved model, loaded again, gave identical forecasts. Runtime A fitted its 1,450 models from 13:15:28 to 13:39:06 (23 minutes 38 seconds), and runtime B its 292 models from 13:39:17 to 13:47:10 (7 minutes 53 seconds). Eight fits ran at a time, each on its own processor core (cores 24 to 31); [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done) explains why eight.

**P1 and the F4 choice.** The P1 scoring of M1 (runtime A) ran from 13:39:28 to 13:51:20, 712 seconds, on one more core beside the runtime-B fits. The P1 scoring of M2 and M3 took 53 seconds. The choice of the F4 penalties took 2 seconds, at 13:49:59.

**A check against the earlier fits.** A private check compared the 12-person fits of this run with the earlier sealed files. The M1 checkpoints of seeds 20261124, 20261125 and 20261126 have exactly the fingerprints recorded in PROTOCOL.json. M2, M3 and S5 fitted on the 12 people give forecasts identical to the earlier ones on 9,586 rows. So where an earlier sealed fit exists, the 12-person fit of this run gives the same model file (M1) or the same forecasts (M2, M3 and S5).

**The seal.** `FIT-COMPLETE.json` was written at 13:51:31, 42 minutes 50 seconds after D2 began, and committed at 13:52:48 (commit `4652d69`). Before it was pushed, a separate reviewer fitted 22 of the 1,742 models again with the committed code; each model file was identical, byte for byte, to the sealed one. The seal was pushed at 14:03:24.

### The evaluation download (D3), the forecasts and the forecast seal (C4)

**The download.** D3 began at 14:06:17, after the public main branch was seen to hold the fit seal, and ended at 14:09:36: 3 minutes 19 seconds. It downloaded the 60 walks of the 20 evaluation people in 120 requests. Every ranged read succeeded at the first attempt, with status 206 and the expected archive fingerprint and version. 55,832,987 bytes were received: 55,828,652 of compressed walks and 4,335 of local headers. Decompressed, the walks take 92,761,088 bytes. The request log `D-evaluation-requests.jsonl` and the receipt `D3-RECEIPT.json` were committed at 15:14:59.

**Extraction.** From 14:09:47 to 14:09:48 the extraction turned the 60 walks into 17,888 rows for the 20 people: 17,288 with an impulse target and 17,040 with a new-load label. Inputs and targets went into two separate files (see [What stays private](#what-stays-private-and-why)).

**The forecasts.** A method is anything that makes forecasts: a fitted model, a control or a frozen checkpoint. Each runtime made its forecasts on one core, both at the same time. Runtime A made the forecasts of 1,451 methods from 14:09:58 to 14:53:18 (43 minutes 20 seconds): 200 main fits below N_max, 450 fits at N_max and 801 others, including F1. Runtime B made the forecasts of 305 methods from 14:10:02 to 14:15:04 (5 minutes 2 seconds): 62 main fits below N_max, 14 fits at N_max and 229 others, including the controls C1 to C3, F2, the four F3 models and the five F4 arms. A forecast was made with every one of the 1,742 fits. Every forecast is an ordinary number, with one exception: one F4 arm uses the earlier muscle window, has no forecast on the 3,000 rows where that window is incomplete, and is not scored there (item 6 of [DECISIONS.md](DECISIONS.md)).

**The seal.** `FORECASTS-SEAL.json` holds the fingerprints of the six forecast files. It was written at 14:54:10 and committed at 14:54:24 (commit `be66803`).

### The P2 prediction (S-b and C5)

Stage S-b ran at 14:54:32, 8 seconds after the forecast seal was committed, and took under 1 second. It opened only the two forecast files of M1, M2 and M3 below N_max, one per runtime, and wrote `P2-TREND-PREDICTION.json`. That file was committed at 14:55:40 (commit `46d27d6`).

The forecast seal and the P2 prediction were pushed together at 15:08:44. So the forecast seal became public after S-b, not before it. The protocol asks for C1, C2, C3 and C5 to be pushed before the next stage and does not list C4. That the forecast seal was made before S-b therefore rests on this computer's records and not on a public time.

Before that push, a separate reviewer made the forecasts of 24 methods (fitted models, controls and frozen checkpoints) again from the saved model files and the inputs alone. They were identical to the sealed forecasts. The reviewer also recomputed S-b and the P2 prediction with separate code.

### The final scoring (S-c) and the independent recomputation

The final scoring began at 15:11:08, after the P2 prediction was public, and took 9 seconds. It wrote `RESULTS.json`, which was committed at 15:14:37.

From 15:11:32 to 15:11:34, `replay.py`, a program written separately from the scorer, recomputed two things. With plain loops it recomputed each evaluation person's impulse error for M1, M2 and M3 at every rung: 300 numbers (3 families, 5 rungs, 20 people). And it recomputed 40 targets directly from the walk files. The largest difference from the scorer was 7.9e-14 (0.000000000000079) on the 300 numbers and 0 on the 40 targets, so it passed. [Stage S-c](#stage-s-c-and-the-independent-replay-done) says what this recomputation covers and what it does not.

### The supplement

The supplement is a set of extra tables. Its program, `supplement.py`, was written and run after the final scoring, when `RESULTS.json` had already been read, so it is not a stage of the protocol. It uses the same scoring code on the same sealed forecasts and changes no number of `RESULTS.json`: every value it recomputes on all forecast times is compared with that file, and the largest difference was 0.0. It ran from 22:08:28 to 22:08:42. `RESULTS-SUPPLEMENT.json` was committed at 22:14:39.

### The results (C6)

The results are written in two editions, [README-SIMPLE.md](README-SIMPLE.md) and [README.md](README.md), with the sources and terms in [NOTICE.md](NOTICE.md). The fitted models of the largest rung are not exported yet (see [Open items](#open-items)).

This code downloaded no walk of group P (30 walks, 25,425,332 compressed bytes) or of the physics supplement (33 walks, 34,449,181 compressed bytes). Of those people it read only the header bytes of the probe (D1).

## What stays private, and why

The recordings, the model inputs and targets made from them, the fitted models and the forecasts stay in a private folder and are never committed, as protocol section 17 says. Local folder names are also kept out of every committed file. What is published instead are the stage records (the fingerprints, verdicts, groups, seals and finally the results), so that anyone can check that the sealed files were not changed.

The private folder is divided so that access can be given folder by folder. The physics-source part of the project may read the training-pool walks and the training arrays after D2, so that only one process downloads them; the training arrays also hold the rows of the 12 earlier people. It is never given the evaluation folders, the fits or the forecasts.

| Folder | What it holds | Physics-source access |
| --- | --- | --- |
| `receipts/` | The D1 logs, the D2 request log and the D2 download receipt. Copies of all four are committed in this folder's `receipts` | none |
| `walks/` | The decompressed training-pool walk files, named like `SUBJ002-1.c3d` | may read, after D2 |
| `arrays/` | `TRAIN-INPUTS.npz`, `TRAIN-TARGETS.npz`, `TRAIN-WALKS.json` | may read, after D2 |
| `eval-walks/` and `eval-walks/receipts/` | The evaluation walk files (D3), their request log and download receipt. Copies of the log and the receipt are committed in this folder's `receipts` | never |
| `eval-arrays/` | `EVAL-INPUTS.npz`, `EVAL-TARGETS.npz`, `EVAL-WALKS.json` | never |
| `fits/` | One checkpoint per fit (`.safetensors` for runtime A, `.joblib` for runtime B) with a small record file each, and the fit stage's lock, attempt, result, F4 choice, P1 and readback files | never |
| `forecasts/` | Three forecast files per runtime and the issue records | never |
| the output folder | Gate parts, test reports, score locks, `RESULTS.json` (its copy is committed), `REPLAY.json` | never |
| the supplement's output folder | `RESULTS-SUPPLEMENT.json` (its copy is committed) and its score lock | never |
| the configuration file, the scratch folder, the CPU-slot folder, the runtimes | Local paths and temporary files | none |

Model inputs and targets are kept in separate files. The targets are what actually happened in the 100 ms after each forecast time. The extraction program (`prepare.py`) read the evaluation walks, computed the targets and wrote them into a file of their own, `EVAL-TARGETS.npz`. It also wrote into `EVAL-WALKS.json`, for each walk, how many rows have an impulse target and how many have a new-load label. The program that makes the forecasts opens the inputs file, `EVAL-INPUTS.npz`, and it opens `EVAL-WALKS.json` to check the fingerprint of the inputs. It never opens the targets file. A separate scoring program joins the targets to the forecasts later.

After the run the private folder holds 1,005,701,390 bytes, about 1.0 GB: forecasts 408,303,877; fitted models 266,748,297; decompressed training-pool walks 165,541,248; decompressed evaluation walks with their receipts 92,820,207; training arrays 50,442,403; evaluation arrays 21,471,554; receipts 373,804. The protocol had estimated under 0.7 GB (item 18 of [DECISIONS.md](DECISIONS.md)).

## Checking the published records

These checks use only the files in this folder, unless a step says otherwise. They are run in a terminal inside this folder. `python3` is any recent Python 3; steps 1 to 5, 8, 9 and 11 need no add-on package, and step 10 needs NumPy.

1. **Check the fixed files.** Type:

   ```
   sha256sum PROTOCOL.json allocate.py POOL.json ORDER.json
   ```

   The fingerprints must start with `1768c4df`, `f40c66f8`, `c5b5041d` and `c3c202d4`. The fingerprint of PROTOCOL.json is also the salt of every hash order, so the group order could not be known before the protocol was final. The protocol itself records the fingerprints of `allocate.py` and `POOL.json`.

2. **Check that the code is the code the gates ran on.** [S0-GATES.json](S0-GATES.json) records the fingerprints of all 27 code files (22 scripts and 5 test files) as they were when the gates ran. `supplement.py` was written after the final scoring and is not in that list. This command compares the 27 recorded fingerprints with the files in the folder and prints `all equal` when every one matches, or the names of the files that differ:

   ```
   python3 -c "import json,hashlib,pathlib; d=json.load(open('S0-GATES.json'))['code_sha256']; print([k for k,v in d.items() if hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest()!=v] or 'all equal')"
   ```

3. **Check the candidate list and the hash orders.** This step needs the archive's central directory, 87,971 bytes. It can be fetched with one ranged read of archive bytes 463,071,776 to 463,159,746 from the dataset's stable address, for example:

   ```
   curl -L -r 463071776-463159746 -o CD.bin https://ndownloader.figshare.com/files/42450060
   sha256sum CD.bin
   ```

   The fingerprint must be `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b`. Then:

   ```
   python3 -B allocate.py check --directory CD.bin --protocol PROTOCOL.json
   ```

   It rebuilds `POOL.json` and `ORDER.json` from the central directory and the protocol and compares them with the published files byte for byte. It prints `{"POOL.json": true, "ORDER.json": true}` when both match.

4. **Recompute the groups from the probe's verdicts.**

   ```
   python3 -B assign.py --qualification QUALIFICATION.json --directory CD.bin --out /tmp/ALLOCATION.json
   cmp /tmp/ALLOCATION.json ALLOCATION.json
   ```

   `assign.py` repeats every check described in [Stage C2](#stage-c2-the-allocation-done-and-reviewed) and writes a fresh allocation to the stated file. `cmp` compares two files and prints nothing when they are identical. The published `ALLOCATION.json` has fingerprint `d1f28610…`. Without `--directory CD.bin`, the first line skips the rebuild of step 3. This check gave identical bytes with Python 3.14.8. Running `allocate.py assign` alone gives a file with a different fingerprint, for the reason explained in [Stage C2](#stage-c2-the-allocation-done-and-reviewed).

5. **Look at the probe's request log.** Each line of `receipts/D1-requests.jsonl` describes one ranged read. Every line shows status 206, attempt 0 (no repeat), the archive fingerprint (ETag) `"85235c73455d4df8434810d61517efbb"`, the archive version `c9jtqYlgGUVrgEUy1JMXkChG6zGtCpvu` and 8,704 bytes, and none contains the temporary signed part of an address. In `QUALIFICATION.json`, each walk gives the byte range read and the fingerprint of the bytes received, so a reader can request any of those ranges again and compare. A reader can also repeat the whole probe with a configuration whose private and publishing folders point to new, empty folders (see [The private configuration file](#the-private-configuration-file)). That makes 482 requests and takes about 9 minutes. The `counts` and `people` entries of the new file should equal the published ones; the times and the lease note will differ.

6. **Run the two tests that need only the public files and the central directory.** `tests/test_trend_score.py` (runtime B) checks the trend calculations, the bootstrap, the correction for three tests, the labels and the p-value formula on made-up numbers. `tests/test_assign.py` (any Python) checks the group split on made-up verdicts and shows that altered receipts are refused. Each takes a configuration file with three entries, `central_directory_file`, `out_dir` and `scratch_dir`, and writes a report with `"passed": true` into `out_dir/tests/`. They took 0.3 s and 0.1 s.

7. **The gates and the two other tests.** `gates.py`, `tests/test_fetch_probe.py` and `tests/smoke_pipeline.py` read the 36 walks of the 12 earlier people, and the gates also read files of the earlier fits (the earlier forecast rows, an encoded data file, the tree-input rows, the sealed checkpoints, a comparator file and the sealed tree file). Those earlier files are not in this repository. The 36 walks (31,290,834 compressed bytes) can be downloaded from the same archive and checked against the central directory, and the small readback file the code expects can be written from that download (its fields are listed in [The private configuration file](#the-private-configuration-file)). The encoded data file, the tree-input rows, the tree file and the three sealed M1 checkpoints are identified by fingerprints in PROTOCOL.json and `gates.py`, so a copy can be checked before use; the earlier forecast rows, the comparator file and the three earlier LSTM checkpoints (a second kind of recurrent model, replayed beside M1 but not part of the protocol) have no recorded fingerprint.

8. **Check the order of the seals.** The protocol asks for three things: `FIT-COMPLETE.json` public before any evaluation walk is downloaded, `FORECASTS-SEAL.json` committed before any scoring, and `P2-TREND-PREDICTION.json` public before the final scoring (S-c). In the public history the commits come in that order: `4652d69` (fit seal), `c6e6909` (D2 receipts), `be66803` (forecast seal), `46d27d6` (P2 prediction), and then the commit of `RESULTS.json`. The clock times are this computer's own records: the dates in a commit are set by the computer that makes it, and the push times come from this computer's record of each push. By those records, the fit seal was pushed at 14:03:24 and the first read of an evaluation walk is stamped 14:06:21 in `receipts/D-evaluation-requests.jsonl`; the P2 prediction was pushed at 15:08:44 and S-c began at 15:11:08. The forecast seal was committed at 14:54:24, 8 seconds before S-b began, but pushed only at 15:08:44, after S-b. So a reader cannot confirm from a public time that the forecast seal came before S-b.

9. **Check the chain of fingerprints.** Type:

   ```
   sha256sum PROTOCOL.json FIT-COMPLETE.json FORECASTS-SEAL.json P2-TREND-PREDICTION.json RESULTS.json
   ```

   The fingerprints must start with `1768c4df`, `7280ea43`, `98a0b76f`, `e8d1c457` and `e7cf4061`; [README-SIMPLE.md](README-SIMPLE.md) lists them in full. Each later file names the fingerprints of the earlier ones, so none of them can be exchanged afterwards without the change showing. `FIT-COMPLETE.json` names the protocol and the allocation (`protocol_sha256`, `allocation_sha256`). `FORECASTS-SEAL.json` names the protocol and the fit seal (`fit_complete_sha256`). `P2-TREND-PREDICTION.json` names those two and the forecast seal (`forecasts_seal_sha256`). `RESULTS.json` names all four (`protocol_sha256`, `fit_complete_sha256`, `forecasts_seal_sha256`, `p2_sha256`). `RESULTS-SUPPLEMENT.json` names the same four and `RESULTS.json` (`results_sha256`).

10. **Recompute the three main results from each person's errors.** `RESULTS.json` gives each evaluation person's impulse error for every model family at every rung. The short program below takes, for M1, M2 and M3, each person's error at 47 people minus the same person's error at 12 people; where a family has several fits at a rung, the file gives the person's average over them. It averages this change over the 20 people and repeats the calculation on the 10,000 fixed resamples. Save it as `check.py` outside this folder and run `python3 check.py RESULTS.json` with NumPy installed (checked with NumPy 2.5.5):

    ```python
    import json, sys
    import numpy as np
    R = json.load(open(sys.argv[1]))
    n_max = str(R['n_max'])
    people = sorted(R['curves']['impulse']['M1']['12']['per_person'])
    idx = np.random.default_rng(20261127).integers(0, len(people), size=(10000, len(people)))
    for fam in ('M1', 'M2', 'M3'):
        c = R['curves']['impulse'][fam]
        a = np.array([c[n_max]['per_person'][p] for p in people])
        b = np.array([c['12']['per_person'][p] for p in people])
        d = a - b
        boot, base = d[idx].mean(axis=1), b[idx].mean(axis=1)
        lo, hi = np.percentile(boot / base, [2.5, 97.5])
        p = min(1., 2 * min(1 + int((boot >= 0).sum()), 1 + int((boot <= 0).sum())) / 10001)
        print(fam, f'{d.mean():+.4f} N·s, {100 * d.mean() / b.mean():+.2f}% ({100 * lo:+.2f}% to {100 * hi:+.2f}%), p = {p:.4f}, lower error for {int((d < 0).sum())} of {len(d)}')
    ```

    It must print:

    ```
    M1 -0.1230 N·s, -5.30% (-6.77% to -3.85%), p = 0.0002, lower error for 20 of 20
    M2 -0.1723 N·s, -4.76% (-5.42% to -4.07%), p = 0.0002, lower error for 20 of 20
    M3 -0.2398 N·s, -11.07% (-14.92% to -7.52%), p = 0.0002, lower error for 18 of 20
    ```

    Each line gives the average change in N·s, the same change as a percentage of the error at 12 people with its 95% interval, the p-value, and the number of people whose error is lower at 47 people. These are the `primary_impulse` entries of `RESULTS.json`. With three tests corrected together by the Holm method, each p-value of 0.0002 becomes 0.0006: the smallest is multiplied by 3, and because the three are equal and a corrected value is never allowed to be smaller than the one before it, the other two get the same value.

11. **Look at the download records.** Every line of `receipts/D-training_pool-requests.jsonl` (105 lines) and of `receipts/D-evaluation-requests.jsonl` (60 lines) shows status 206, attempt 0 and the archive fingerprint and version of check 5, and none contains the temporary signed part of an address. `receipts/D2-RECEIPT.json` and `receipts/D3-RECEIPT.json` give, for each walk, the archive member, the byte range, the compressed and decompressed sizes with their fingerprints, and the CRC-32. The numbers of walks and the sums of the compressed sizes equal the figures under `downloads_by_this_track` in `ALLOCATION.json` (105 walks and 98,793,925 bytes; 60 walks and 55,828,652 bytes), and the people are those of its training-pool and evaluation groups. The positions, sizes and CRC-32 values can be compared with the central directory of check 3, and any byte range can be requested again from the stable address and compared with the fingerprint in the request log. Everything after the downloads (the extraction, the fits, the forecasts and the scores) needs the recordings and the private files, so it cannot be checked from this folder alone. `FIT-COMPLETE.json` and `FORECASTS-SEAL.json` give the fingerprints that a complete rerun must reproduce.

## Setting up the software

Two runtimes are used:

| Runtime | Python | Packages | Used for |
| --- | --- | --- | --- |
| A | CPython 3.13.15 | torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0 | M1 and every variant of it (C4, S1, S2-M1, S3, S4-M1, S6-M1 and the G8 M1 sets), and the frozen checkpoint F1 |
| B | CPython 3.12.14 | numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0 | M2, M3, S5, G9, the frozen checkpoints F2, F3 and F4, extraction, scoring, the replay, the supplement and three of the tests |

The scripts that use only Python's standard library (the downloader, the probe, the allocation and a few helpers) run in either runtime; the tests run them in runtime B. For S0, the runtimes were built with uv (a Python package tool) from installed CPython 3.13.15 and 3.12.14 interpreters. These commands build equivalent runtimes in two folders called `venv-A` and `venv-B`:

```
uv venv --python 3.13.15 venv-A
uv pip install --python venv-A/bin/python --index-url https://download.pytorch.org/whl/cpu "torch==2.14.1+cpu"
uv pip install --python venv-A/bin/python numpy==2.5.3 safetensors==0.8.0
uv venv --python 3.12.14 venv-B
uv pip install --python venv-B/bin/python numpy==2.5.5 scikit-learn==1.9.1 joblib==1.6.0 onnxruntime==1.32.0
```

The second line installs the CPU-only build of torch from the PyTorch package site. The packages installed in the end, including the ones pulled in automatically, were:

- Runtime A: filelock 4.2.4, fsspec 2026.9.0, jinja2 3.1.6, markupsafe 3.0.3, mpmath 1.3.0, networkx 3.7, numpy 2.5.3, safetensors 0.8.0, setuptools 78.1.0, sympy 1.14.0, torch 2.14.1+cpu, typing-extensions 4.16.0.
- Runtime B: cloudpickle 3.1.3, flatbuffers 25.12.19, joblib 1.6.0, narwhals 2.29.0, numpy 2.5.5, onnxruntime 1.32.0, packaging 26.4, protobuf 7.36.2, scikit-learn 1.9.1, scipy 1.18.1, threadpoolctl 3.8.0.

Every calculation runs on one processor thread. Before NumPy, torch or scikit-learn is loaded, the code sets six environment variables that control their thread counts (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `BLIS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`) to 1. The protocol (section 16) gives the reason: with two threads the fitted weights change, so results would not repeat exactly.

## The private configuration file

Every script except `allocate.py` and `assign.py` needs `--config` followed by the name of a configuration file. This is a small JSON file (a plain text file of names and values) that tells the code where the local folders and input files are. It is private and never committed, so that no local folder name appears in the public files. The code reads the following entries and ignores any others:

| Entry | Read by | What it points to |
| --- | --- | --- |
| `central_directory_file` | the walk helpers (extraction of the training group, gates, tests) and the allocation test | The archive's central directory: 87,971 bytes, archive bytes 463,071,776 to 463,159,746, fingerprint `96a6b5d9…`. The code checks its size and fingerprint every time it reads it. |
| `fit_cache_dir` | the walk helpers | A folder with the decompressed C3D files of the 36 walks of the 12 earlier people, named as in the archive (for example `SUBJ24 (1).c3d`) |
| `fit_readback_file` | the walk helpers | A JSON file whose `records` give, for each of those walks, `subject_code`, `author_trial_index` (the walk number), `archive_member`, `member_crc32` and `decoded_sha256` (the fingerprint of the decompressed file) |
| `features_ref_dir` | the gates | The earlier forecast rows of the 12 people (`FEATURES.npz`, `TARGETS.npz`, `SUPPORT.npz`), for gate G1 |
| `generalization_dir` | the gates | The earlier encoded data of the 12 people (`private/prepared/belgium.npz`, fingerprint `d81af885…`) and the sealed 12-person checkpoints and controls (`private/fit/`) |
| `matched_dir` | the gates | The earlier tree-input rows (`private/FIT.npz`, `dfe83f82…`) and the sealed 12-person tree file (`private/trees/MODELS.joblib`, `2c3f642e…`) |
| `repo_root` | the fit, issue, scoring and gate scripts | A copy of this repository. The code reads the published checkpoints and the force-baseline grid from it, and the final scoring checks that the P2 prediction is committed there. |
| `private_dir` | most stages | The private folder described above |
| `out_dir` | the gates, the scoring, the replay, the supplement and the tests | Where gate parts, test reports, score locks, `RESULTS.json`, `REPLAY.json` and `RESULTS-SUPPLEMENT.json` are written |
| `scratch_dir` | the gates and the tests | A folder for temporary files. The tests delete and recreate its subfolders `test-assign` and `smoke`. |
| `publish_dir`, `publish_repo` | optional | The folder and repository for the committed stage files. If absent, this folder and `repo_root` are used. Only the made-up test runs set them. |

The files behind the first six entries are earlier work, read where they lie and never changed. Each walk file is checked for size, CRC-32 and its recorded fingerprint before use. The earlier encoded data, tree-input rows and tree file are checked against fingerprints recorded in `gates.py` and PROTOCOL.json, and the three sealed M1 checkpoints against their fingerprints in PROTOCOL.json. The three earlier LSTM checkpoints that the gates replay beside them have no recorded fingerprint; their fingerprints are written into `S0-GATES.json`.

The fit stage and the smoke run also need an environment variable called `NS_CPU_SLOTS`. It names a folder of CPU slots, one small lock file per processor core, through which training jobs take cores one at a time (see [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done)). The folder is meant to be shared by every training job on the machine, but in this run only this code used it; the physics-source part chose its own cores, and the limit of 16 threads was kept by another arrangement, described under [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done) (see also [Open items](#open-items)).

An example configuration, with made-up paths:

```json
{
 "central_directory_file": "/data/van-criekinge/central-directory.bin",
 "fit_cache_dir": "/data/van-criekinge/fit-walks",
 "fit_readback_file": "/data/van-criekinge/fit-walks-readback.json",
 "features_ref_dir": "/data/earlier/features",
 "generalization_dir": "/data/earlier/generalization",
 "matched_dir": "/data/earlier/matched-baselines",
 "repo_root": "/work/NeuroTranslation",
 "private_dir": "/work/walking-scale/private",
 "out_dir": "/work/walking-scale/run/out",
 "scratch_dir": "/tmp/walking-scale"
}
```

Stage S0 used a configuration of its own, with private, output and scratch folders separate from those of the real run, because the gates write files about the 12 earlier people into the private folder. The supplement used a copy of the run's configuration with an output folder of its own, so that it could not overwrite any file of the run.

## Running each stage, in order

All commands are typed in this folder. First set four names, replacing the made-up paths with real ones:

```
PY_A=/path/to/venv-A/bin/python          # runtime A
PY_B=/path/to/venv-B/bin/python          # runtime B
CFG=/path/to/config.json                 # private configuration
export NS_CPU_SLOTS=/path/to/cpu-slots   # shared CPU-slot folder (fit stage and smoke run)
```

The `-B` after the Python name stops Python from writing cache files into this folder.

A stage may start only after the commit, review or lease named for it. Several scripts protect what they have already written. The downloader, the extraction and the forecast stage refuse to overwrite their own output files, and the probe refuses to run at all once `QUALIFICATION.json` exists. The fit stage, if interrupted, resumes only the fits that are missing, and refuses to continue if the job list, the code or the inputs have changed since its first attempt.

### Stage S0: engineering checks and tests (done)

```
$PY_B -B tests/test_fetch_probe.py --config "$CFG"
$PY_B -B tests/test_assign.py --config "$CFG"
$PY_B -B tests/test_trend_score.py --config "$CFG"
$PY_B -B gates.py part-b --config "$CFG"
$PY_A -B gates.py part-a --config "$CFG"
$PY_B -B tests/smoke_pipeline.py --config "$CFG" --python-a "$PY_A" --python-b "$PY_B"
$PY_B -B gates.py report --config "$CFG"
```

**What it does.** The first three lines run three tests. `gates.py part-b` runs the gates that need runtime B (the reader, the forecast rows, the trees, the linear models, the force baselines), and `part-a` the gates that need runtime A (the checkpoint replays, reload equality, the random-readout control). `part-a` must come after `part-b`, because it reads files that `part-b` writes into the private folder. The smoke run then carries every stage on the 12 earlier people. Finally, `gates.py report` gathers the two gate parts and the four test reports from the output folder into `S0-GATES.json` in this folder.

**What it reads.** The 36 earlier walks, the earlier sealed files named in the configuration, and the published checkpoints in the repository copy. Nothing is downloaded.

**Note.** `report` replaces the committed `S0-GATES.json`. The measured times inside it change from run to run, so a rerun should be compared by its `gates` and `tests` entries, not byte for byte.

**How long.** In the S0 rerun of 27 November: `part-b` 17 s, `part-a` 35 s, `test_fetch_probe` about 40 s, `test_assign` and `test_trend_score` under 1 s each, and the smoke run about 6 minutes (68 runtime-A fits in 168 s and 58 runtime-B fits in 146 s, spread over 3 processor cores).

**Result.** All 15 gates and all 4 tests passed (see [Engineering checks](#engineering-checks-on-the-12-earlier-people-s0)).

### Stage D1: the header probe (done; it runs only once)

```
$PY_B -B fetch.py probe --config "$CFG" --lease-note "TEXT"
```

**What must happen first.** The protocol pushed (C1), the code reviewed (C1b) and the owner's download lease. `TEXT` is the lease note, which is copied word for word into `QUALIFICATION.json` and into the first line of the walk log.

**What it does.** For each walk it reads 8,704 bytes from the local header, more in steps of 8,192 bytes up to 65,536 bytes if needed, and decompresses only up to the end of the parameter section, as described in [The header probe](#the-header-probe-d1). It probes a person's 4th and 5th walks only when one of the first three is not Q6. It refuses to run if the candidate list contains anyone of the earlier validation or test groups or SUBJ099.

**What it writes.** `QUALIFICATION.json` in this folder, and two logs in the private `receipts` folder (`D1-requests.jsonl`, one line per read, and `D1-walks.jsonl`, one line per walk). No header byte is saved.

**When it stops.** If a ranged read gets an unexpected answer (wrong status, archive fingerprint, version, byte range or length), if a local header differs from the central directory, or if a read is answered 429 or 5xx twice, the stage halts and writes no `QUALIFICATION.json`. After one 429 or 5xx answer it waits 60 s and repeats the whole read once, starting again with a new redirect, because the temporary address lives only about 10 s.

**How long.** 8 minutes 51 seconds for 482 requests. The spacing of at least 1.1 s between requests sets the time.

### Stage C2: the allocation (done and reviewed)

```
$PY_B -B assign.py --qualification QUALIFICATION.json --directory CD.bin
```

`CD.bin` stands for the central directory file (the `central_directory_file` of the configuration).

**What it checks before splitting.** With `--directory`, it first rebuilds `POOL.json` and `ORDER.json` from the central directory and requires them to match the published files byte for byte. It checks that `allocate.py`, `POOL.json` and `ORDER.json` have their recorded fingerprints; that `QUALIFICATION.json` carries the fingerprints of the protocol and the candidate list; that each person's probed walks follow the probe rule; that each person's class follows from their walk verdicts; and that the listed walks are the three lowest-numbered qualified ones.

**What it does.** It then runs the split of `allocate.py`, unchanged, and checks the result: every candidate is in exactly one group, the groups follow the fixed order, and their sizes follow the rule.

**What it writes.** `ALLOCATION.json` in this folder. It refuses if that file already exists; `--out` followed by a file name writes the result elsewhere, as in check 4 above.

**How it differs from `allocate.py assign`.** The protocol names `allocate.py assign` as the allocation step, and `assign.py` runs exactly that step. It then adds two entries to the result: `pool_sha256`, the fingerprint of `POOL.json`, and `checked_by`, the fingerprints of `assign.py`, `qualify.py` and `allocate.py`. A reader who runs `python3 -B allocate.py assign --qualification QUALIFICATION.json --out FILE` therefore gets a file whose fingerprint starts with `93af4a89` instead of `d1f28610`. Apart from those two entries, the two files are identical.

**How long.** Under 1 second.

### Stage D2: downloading the training pool (done; it runs only once)

```
$PY_B -B fetch.py download --config "$CFG" --group training_pool --lease-note "TEXT"
```

**What must happen first.** The allocation (C2) reviewed and pushed. In the run it was pushed at 13:04:52, and D2 began at 13:08:41.

**What it does.** For each of the 105 training-pool walks, it asks for a new redirect and then reads the whole member in one ranged read, from its local header to the next member's local header. It checks the answer (status 206, archive fingerprint, version, byte range and length), checks the local header against the central directory, decompresses the walk and checks its size and CRC-32. It refuses anyone of group P, the physics supplement, the earlier validation and test groups and SUBJ099.

**What it writes.** The walk files into the private `walks` folder, named like `SUBJ002-1.c3d`, a request log, and a download receipt `D2-RECEIPT.json` listing for each walk its byte range, its compressed and decompressed sizes and fingerprints, and its CRC-32.

**How long.** 5 minutes 36 seconds for 210 requests and 98,801,524 bytes, up to the time written in the receipt. The spacing of at least 1.1 s between requests accounts for 3 minutes 51 seconds of that. The protocol had estimated about 10 minutes of transfer for all downloads together; D1, D2 and D3 took 17 minutes 46 seconds in all.

### Extraction of the training group (done)

```
$PY_B -B prepare.py --config "$CFG" --allocation ALLOCATION.json --group training
```

**What it does.** It reads the 36 walks of the 12 earlier people (where they lie) and the 105 new training walks, checks each against its size, CRC-32 and recorded fingerprint, and turns them into model inputs and targets: one row per plate every 20 ms, with the inputs taken only from the 200 ms before the forecast time and the targets from the 100 ms after it (protocol section 6).

**What it writes.** `TRAIN-INPUTS.npz`, `TRAIN-TARGETS.npz` and `TRAIN-WALKS.json` in the private `arrays` folder. A training walk with no usable rows stays in the list and is counted; in this run every walk had usable rows.

**How long.** About 2 seconds on one core, for 141 walks and 42,030 rows.

### The fits, the F4 choice, P1 and seal C3 (done)

```
$PY_A -B fit.py run --config "$CFG" --runtime torch --lanes 8
$PY_B -B fit.py run --config "$CFG" --runtime sk --lanes 8
$PY_B -B fit.py f4 --config "$CFG"
$PY_A -B fit.py p1 --config "$CFG" --runtime torch
$PY_B -B fit.py p1 --config "$CFG" --runtime sk
$PY_B -B fit.py seal --config "$CFG"
```

**What must happen first.** Extraction, and an arrangement that keeps all the training on the machine within 16 threads (see "How it was shared in this run" below).

**What it does.** `plan.py` lists every fit from `ALLOCATION.json`: 1,742 fits for this allocation. Runtime A does 1,450 of them: 250 fits of M1 itself, 250 of S2-M1, 250 of S3, 200 of S1, 200 of S4-M1, 100 of C4, 100 of S6-M1 and 50 for each of the two G8 sets. Runtime B does 292: 32 each of M2, M3, S2-M2, S2-M3, S5, G9-M2 and G9-M3, 31 each of S4-M2 and S4-M3, 2 of S6-M2 and 4 for the G8 sets. M1 and its variants are fitted with 50 seeds (20261124 to 20261173) at 12 people, at N_max and for the two G8 sets, and with 5 seeds for each of the 10 draws at the middle rungs (draw d uses seeds 20261124 + 5d to 20261124 + 5d + 4). M2, M3 and their variants give the same result every time on the same data, so each is fitted once per training set.

**How this matches the protocol's estimate.** Section 16 of the protocol estimates about 550 tree fits and 650 straight-line fits, more than the 292 runtime-B fits listed here. The difference is the tuned arm G9: each of its 32 tree fits first fits 3 leaf settings on 4 inner folds (12 extra fits), and each of its 32 straight-line fits first fits 4 penalties on 4 inner folds (16 extra fits). The 161 tree fits in the list (32 each of M3, S2-M3, S5 and G9-M3, 31 of S4-M3 and 2 for G8) plus 384 inner-fold fits make 545 tree fits. The 131 straight-line fits (32 each of M2, S2-M2 and G9-M2, 31 of S4-M2, 2 of S6-M2 and 2 for G8) plus 512 inner-fold fits make 643.

**How the processor is shared.** Each fit runs as a separate worker on one processor core. A worker first takes a lock on a small file for one core in the shared CPU-slot folder and then confines itself to that core. Fits take the first free cores among cores 20 to 31, at most 12 at once; 12 is the value of `--lanes` when it is left out.

**How it was shared in this run.** The machine's rule is that all training together uses at most 16 threads, on cores 16 to 31. When the fits began, the simulator of the physics-source part of the project was running 8 workers on cores 16 to 23, which it had chosen without the slot folder. A small private helper program therefore held the slot files of cores 20 to 23, so that no fit could take those cores, and the fits ran 8 at a time (`--lanes 8`) on cores 24 to 31. Together that made 16 threads. The simulator ended while the runtime-A fits were running, and the fits stayed at 8 at a time until the end. The helper is not part of this folder. The number of fits running side by side changes how long the stage takes, not the fitted numbers: each fit runs on one thread with fixed seeds, and the C3 reviewer fitted 22 models again on other cores and got the same bytes.

**What is recorded.** Before the first fit, a lock file records the job list and the fingerprints of the code and inputs. Each fit writes its checkpoint, loads it again and recomputes its forecasts on every row it was trained on, and then writes its own record file. The fit counts as done only if the two sets of forecasts are identical; otherwise it is recorded as failed. A failed fit keeps its record and is never replaced. At the end of a run a result file lists every fit, and the seal later reads every file back.

**The other steps.** `f4` chooses the penalty of each published force baseline (F4) on the training-pool people, as the protocol requires before any evaluation byte. `p1` scores the 12-person and middle-rung fits on each draw's 11 unseen training-pool people. `seal` reads every file back, checks its fingerprint, fits the trend forms to the P1 curve and writes `FIT-COMPLETE.json` in this folder, with every checkpoint's fingerprint, the failed fits, the F4 choice and the P1 prediction. This file is committed and pushed as C3.

**Result.** 1,742 of 1,742 fits were completed and none failed; every saved model, loaded again, gave identical forecasts. The chosen F4 penalties and the P1 prediction are in `FIT-COMPLETE.json`.

**How long.** Runtime A took 23 minutes 38 seconds for its 1,450 fits; on average one S3 fit took 27.4 s, one S1 fit 7.8 s, one M1 fit 2.9 s and one C4 fit 1.2 s. Runtime B took 7 minutes 53 seconds for its 292 fits; a G9-M3 fit, together with its inner-fold fits, took 89.8 s on average and at most 151 s. The 8 cores were busy for about 31 and a half minutes in all, which is at most 4.2 core-hours (a core-hour is one core busy for one hour). `p1` took 712 s in runtime A, on one core beside the runtime-B fits, and 53 s in runtime B; `f4` took 2 s and `seal` 1 s. The protocol had estimated 4 to 8 core-hours of computing and 30 to 60 minutes from start to end.

**For comparison, on one core in S0:** one M1 fit (900 training steps) 2.0 s; one S3 fit (the wider model) 8.1 s at 900 steps; one C4 fit 0.77 s; one pair of tree models on 9,586 rows 4.1 s. S1 and S3 take more steps at larger rungs, so that each row is seen as often as at 12 people.

### Stage D3: downloading the evaluation group, and its extraction (done; it runs only once)

```
$PY_B -B fetch.py download --config "$CFG" --group evaluation --fit-complete FIT-COMPLETE.json --lease-note "TEXT"
$PY_B -B prepare.py --config "$CFG" --allocation ALLOCATION.json --group evaluation
```

**What must happen first.** `FIT-COMPLETE.json` committed and pushed (C3). The downloader refuses to start unless `FIT-COMPLETE.json` names the fingerprint of this `ALLOCATION.json`. It does not itself check that the file has been committed or pushed. In the run the seal was pushed at 14:03:24, and D3 began at 14:06:17, after the public main branch was seen to hold it.

**What it writes.** The 60 evaluation walks, their log and `D3-RECEIPT.json` into the private `eval-walks` folders; then `EVAL-INPUTS.npz`, `EVAL-TARGETS.npz` and `EVAL-WALKS.json` into `eval-arrays`.

**How long.** 3 minutes 19 seconds for 120 requests and 55,832,987 bytes; the spacing accounts for 2 minutes 12 seconds of that. The extraction took 1 second.

### The forecasts and seal C4 (done)

```
$PY_A -B issue.py run --config "$CFG" --runtime torch
$PY_B -B issue.py run --config "$CFG" --runtime sk
$PY_B -B issue.py seal --config "$CFG"
```

**What it does.** Every fitted model, frozen checkpoint and control makes its forecasts for the evaluation people. The program opens `EVAL-INPUTS.npz`, and `EVAL-WALKS.json` to check the fingerprint of the inputs. It never opens `EVAL-TARGETS.npz`. Forecasts are made in one fixed order and fixed batch sizes, so a repeat gives identical bytes, and stored as 64-bit numbers.

**What it writes.** Three forecast files per runtime in the private `forecasts` folder: one for M1, M2 and M3 below N_max (the only file stage S-b may open), one for every fit at N_max, and one for everything else. `seal` writes `FORECASTS-SEAL.json` in this folder with the fingerprint of each forecast file. It is committed as C4.

**A note on the seal's wording.** The `custody` entry of `FORECASTS-SEAL.json` reads: "The issuing processes read evaluation inputs only; targets were never opened before this seal." The second half says more than is true, because the extraction program had already computed the targets and written them into their own file. The exact statement is this: the extraction program computed the targets, and the programs that made the forecasts never read them. The sealed file is kept as it was committed, because `P2-TREND-PREDICTION.json` and `RESULTS.json` name its fingerprint.

**How long.** Runtime A 43 minutes 20 seconds and runtime B 5 minutes 2 seconds, each on one core, both at the same time; `seal` under 1 second.

### Stage S-b and seal C5 (done)

```
$PY_B -B score.py below --config "$CFG"
```

**What it does.** It opens only the forecast files for M1, M2 and M3 below N_max, scores those rungs, fits the trend forms to them and predicts the error at N_max, including a prediction in each of the 10,000 resamples of people. Before scoring it writes a score lock with the fingerprints of the files it reads.

**What it writes.** `P2-TREND-PREDICTION.json` in this folder, which is committed and pushed as C5 before the final scoring.

**How long.** Under 1 second, at 14:54:32. C5 was committed at 14:55:40 and pushed together with C4 at 15:08:44.

### Stage S-c and the independent replay (done)

```
$PY_B -B score.py final --config "$CFG" --p2-sha "$(git show HEAD:models/walking-force-scale/P2-TREND-PREDICTION.json | sha256sum | cut -d' ' -f1)"
$PY_B -B replay.py --config "$CFG"
```

**What must happen first.** The P2 prediction committed. The part in `$( … )` computes the fingerprint of the committed P2 file. The final scoring refuses to run unless the P2 file in the folder has that fingerprint, the same bytes are committed in the repository copy, and P2 was made for the same scoreable people (the evaluation people who have rows that can be scored) and the same forecast seal.

**What it does.** It scores N_max, the frozen checkpoints, the controls and every variant, applies the success rule of the protocol, and writes a score lock and `RESULTS.json` into the output folder. `replay.py` is written separately from the scorer. With plain loops it recomputes each evaluation person's impulse error for M1, M2 and M3 at every rung (300 numbers), and it recomputes 20 targets per plate directly from the evaluation walk files (`--rows-per-plate` changes the number). It then writes `REPLAY.json`. It passes when every difference is at most 1e-9. In the run the largest differences were 7.9e-14 on the 300 numbers and 0 on the 40 targets.

**What the replay covers.** Section 14 of the protocol asks for an independent recomputation of every average. `replay.py` covers the main impulse averages. The other averages of S-b and S-c were recomputed by private checks (largest differences 6.7e-15 and 5.3e-15), and a later independent recomputation compared 3,318 numbers of `RESULTS.json` (largest difference 2.5e-10). Those checks are not code in this folder, and `REPLAY.json` stays private (see [Open items](#open-items)).

**How long.** The final scoring took 9 seconds and the replay 2 seconds. From the start of D3 to the end of S-c the run took 65 minutes, 43 of them for the runtime-A forecasts. The protocol had estimated minutes of download and under an hour of computing.

### The supplement (done)

```
$PY_B -B supplement.py --config "$CFG" --results-sha "$(git show HEAD:models/walking-force-scale/RESULTS.json | sha256sum | cut -d' ' -f1)"
```

**What it is.** A program written and run after the final scoring, when `RESULTS.json` had already been read. It is not a stage of the protocol, and it changes no number of `RESULTS.json`.

**What must happen first.** `RESULTS.json` committed. The part in `$( … )` computes the fingerprint of the committed file. The program refuses to run unless `RESULTS.json` in this folder has that fingerprint and the same bytes are committed in the repository copy.

**What it does.** It uses the scoring code of `score.py` unchanged, with the same sealed forecasts, the same weights that make each person count equally and the same resamples. Every value that it recomputes on all forecast times is compared with `RESULTS.json`, and the program stops on any difference; the largest difference was 0.0. Its tables are:

- every method on the 24-position schedule, a smaller set of forecast times (8 groups of 3 in a row per walk) that the project's published model cards use;
- the arms that use an earlier muscle window, on the rows where that window is complete;
- each side arm against its own model family at the same rung;
- rankings that include the controls and the frozen checkpoints;
- counts and row-by-row errors for subgroups;
- the counts of every training set, from `FIT-COMPLETE.json`.

All of these tables describe; none of them changes a label. The labels of the success rule are those of `RESULTS.json`.

**What it writes.** `RESULTS-SUPPLEMENT.json` and a score lock, `SCORE-LOCK-SUP.json`, into its output folder. It refuses to overwrite either file.

**How long.** 14 seconds on one core.

### Stage C6: the results

Section 18 of the protocol lists what is published at C6. In this folder are: the results in a Simple and a Technical edition ([README-SIMPLE.md](README-SIMPLE.md), [README.md](README.md)), `RESULTS.json`, `RESULTS-SUPPLEMENT.json`, the sources and terms in [NOTICE.md](NOTICE.md), and the download receipts without signed addresses.

One part is not done yet: the export of one fitted model of each main family at N_max under CC0 with the notice. The protocol names the M1 checkpoint of seed 20261124, saved without embedded notes and with its small record file; the M3 trees in the ONNX format (a common file format for exchanging fitted models), checked against scikit-learn; and the M2 coefficients. `FIT-COMPLETE.json` holds the fingerprint of every fit, so a later export can be checked against the seal.

## The files in this folder

### Records of the stages

- `PROTOCOL.json`, `PROTOCOL.md`, `PROTOCOL-SIMPLE.md`: the fixed protocol in machine-readable form and in two editions (C1).
- `POOL.json`: all 138 healthy subject codes with the reason each is or is not a candidate, and the archive positions of the 80 candidates' walks. Written by `allocate.py pool` (C1).
- `ORDER.json`: the hash orders: the primary order, the 10 draw orders, the inner folds used by the tuned arm, and the variety-walk choice. Written by `allocate.py order` (C1).
- `S0-GATES.json`: the gate results, the test reports, the timings on one core and the fingerprints of every code file, without local paths. Written by `gates.py report` (S0).
- `DECISIONS.md`: the 18 details the protocol leaves to the code, written with the fixes for the C1b review, before the header probe.
- `QUALIFICATION.json`: for each candidate, the class, the three walks used, and for each probed walk the byte range, the fingerprint of the bytes received, the verdict and the reasons. Written by `fetch.py probe` (D1).
- `receipts/D1-requests.jsonl`: one line per read, with the stable address, the storage host and path, the archive version and fingerprint, the status, the byte range, the bytes and their fingerprint. No signed part of any address. Written by `fetch.py probe` (D1).
- `receipts/D1-walks.jsonl`: the lease note and start time on the first line, then one line per walk with its range, the bytes decompressed and the limit, the verdict, the reasons and the channel counts. Written by `fetch.py probe` (D1).
- `ALLOCATION.json`: the groups, sizes, rungs and draws, inner folds, the P1 groups, the variety sets and the download lists. Written by `assign.py` (C2).
- `receipts/D-training_pool-requests.jsonl` and `receipts/D2-RECEIPT.json`: the request log of the training-pool download, and its receipt, which gives for each walk the archive member, the byte range, the compressed and decompressed sizes with their fingerprints, and the CRC-32. Written by `fetch.py download` (D2).
- `FIT-COMPLETE.json`: the fingerprint of every fitted model, the list of failed fits (none), the chosen F4 penalties and the P1 prediction. Written by `fit.py seal` (C3).
- `receipts/D-evaluation-requests.jsonl` and `receipts/D3-RECEIPT.json`: the same two records for the evaluation download. Written by `fetch.py download` (D3).
- `FORECASTS-SEAL.json`: the fingerprints of the six forecast files. Written by `issue.py seal` (C4).
- `P2-TREND-PREDICTION.json`: the average errors of the rungs below N_max, each evaluation person's errors there, the fitted trend forms and the prediction for N_max, as one number per trend form and in each of the 10,000 resamples. Written by `score.py below` (C5).
- `RESULTS.json`: every score, with each evaluation person's errors under their archive code. Written by `score.py final` (S-c).
- `RESULTS-SUPPLEMENT.json`: the extra tables of the supplement. Written by `supplement.py`, after S-c.
- `README.md` and `README-SIMPLE.md`: the results, in a Technical and a Simple edition (C6).
- `NOTICE.md`: the sources of the recordings and of the earlier published models, and the terms of the files in this folder (C6).

The six files in `receipts` are exact copies of the private logs and receipts, and `RESULTS.json` and `RESULTS-SUPPLEMENT.json` are exact copies of the files in the private output folders.

### The code

| File | What it does | Runtime |
| --- | --- | --- |
| `common.py` | Shared settings (seeds, the new-load prevalence of the 12 earlier people, muscle names, the list of the 36 earlier walks), fingerprints, JSON writing, the configuration, the private folder layout, and the stop signal used when a stop rule fires | standard library |
| `c3dread.py` | Reads C3D files, decoding only the allowed fields, and applies the walk checks Q6, QP and X; its function `read_columns` reads measured values | standard library; NumPy for `read_columns` |
| `qualify.py` | Probes one walk with the decompression limit, applies the person rule, writes the qualification record and checks it | standard library |
| `fetch.py` | The downloader: `probe` for D1, `download` for D2 and D3 | standard library |
| `allocate.py` | The group split, unchanged since C1 and recorded by fingerprint in the protocol; its steps are `pool`, `order`, `assign`, `sizes` (prints the group sizes for every possible number of qualified people) and `check` | standard library |
| `assign.py` | Runs the split of `allocate.py` with the extra checks of stage C2 | standard library |
| `walks.py` | Finds walks in the archive, numbers walks and people, reads walk files with checks | standard library |
| `extract.py` | Turns a walk into forecast rows: inputs from the past only, targets in separate arrays | A, B |
| `compact.py` | The compact input used by M1, M2 and S5, the published weights that make each person count equally, and per-person errors | A, B |
| `threepass.py` | M1 and its variants C4, S1, S2, S3, S4 and S6: training, saving, loading, forecasting | A |
| `trees.py` | M3 (boosted trees on the published tree input), S5 (trees on the compact input) and the tuned trees of G9 | B |
| `linear.py` | M2 (ridge and logistic regression), the tuned M2 of G9, the refit of the published force baselines and the F4 penalty choice | B |
| `frozen.py` | Runs the frozen published checkpoints F1 to F4 through their published code, the controls C1 to C3, and lists the published checkpoints that are not scored, with reasons | A for F1, B otherwise |
| `plan.py` | Lists every fit from `ALLOCATION.json` | standard library |
| `prepare.py` | The extraction after D2 and after D3 | B |
| `fit.py` | The fits, the F4 choice, P1 and the C3 seal | A, B |
| `issue.py` | The forecasts and the C4 seal | A, B |
| `trend.py` | The trend forms, the P1 and P2 predictions and the trend test | B |
| `score.py` | Stage S-b (`below`) and stage S-c (`final`) | B |
| `replay.py` | The independent replay at S-c: each person's main impulse errors and a sample of targets | B |
| `supplement.py` | The supplement: extra tables from the sealed forecasts, written and run after S-c | B |
| `lanes.py` | The CPU slots: one lock file per core for cores 16 to 31; fits use cores 20 to 31. Meant to be shared by every training job on the machine; in this run only this code used them | standard library |
| `gates.py` | The S0 gates (`part-b`, `part-a`) and the merged report (`report`) | B, A, either |

### The tests

| File | What it checks | Runtime |
| --- | --- | --- |
| `tests/synthetic.py` | Helpers for the other tests: a small local archive built from the 36 earlier walks and altered copies of them, and a local web server that behaves like the dataset's redirect and storage | none (used by the tests) |
| `tests/test_fetch_probe.py` | The downloader and the probe: a new redirect for every read; spacing between requests; one repeat after a 429 and a halt after two 5xx answers, both for the redirect and for the ranged read, where the repeat takes a new redirect (the test server refuses a used signed address); checks of fingerprint, version, byte range, size and CRC-32; a local-header mismatch halts D1 without writing `QUALIFICATION.json`; no signed address in the logs; the decompression limit; the Q6, QP and X verdicts; the person rule; altered records are caught | B |
| `tests/test_assign.py` | The group split on made-up verdicts for the real candidates (all 80 Q6, a mixed case, a low case, and a cancelled ladder); altered records are refused; `allocate.py` is unchanged | standard library |
| `tests/test_trend_score.py` | The trend forms, the bootstrap against a plain loop, the correction for three tests (Holm), the labels and the p-value formula, on made-up numbers | B |
| `tests/smoke_pipeline.py` | Every stage end to end on the 12 earlier people with fewer seeds, with the custody checks: D3 refuses before the fit seal, evaluation files land only in the evaluation folders, S-b opens only its file, and S-c refuses an uncommitted P2 | B (starts A and B) |

The tests use much shorter waits than the real downloader (0.05 s between requests and 0.2 s before a repeat) because they talk only to the local test server. No test uses the network.

## What the reviews found

### The admission review of the protocol

Before the protocol was published, a separate reviewer named 10 items. Five of them are handled in this code without changing the protocol:

- Item 3: the number of repeat fits of every side arm is written out in `plan.py`.
- Item 5: the gate "Q6 on the 36 fit walks" shows that all 36 earlier walks pass, through the same probe code that D1 uses.
- Item 6: `allocate.py` is left exactly as published, because the protocol records its fingerprint; `assign.py` adds the checks on the candidate-list fingerprint, the probe order and the lowest-numbered walks, and `tests/test_assign.py` shows that altered records are refused.
- Item 7: the NeuroTranslate 0.1 paired-plates checkpoints, the other published checkpoints that are not scored, and F5 are listed in `frozen.py` with reasons.
- Item 9: `lanes.py` keeps one lock file per core; the first finding of the code review, below, says how the limit of 16 threads was kept in the run.

Items 1, 2, 4, 8 and 10 concern the protocol text, its Simple edition or the limits of the claims, not the code.

### The review of the code (C1b)

The reviewer found 8 minor problems:

1. **Sharing the processor across projects.** The limit of 16 threads in total on cores 16 to 31 holds only if every training job on the machine takes its cores through the same slot folder. The physics-source part of the project chooses its own cores, and the short control steps of this code are not confined to cores. This was not settled through the shared folder. In the run a private helper held the slot files of cores 20 to 23 while the other work's simulator used cores 16 to 23, and the fits ran 8 at a time on cores 24 to 31 (see [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done)). The control steps (extraction, P1, the F4 choice, the seals, the forecasts and the scoring) each ran confined to one core taken through the slot folder.
2. **The repeat after a 429 or 5xx on the ranged read** used the old temporary address, which would already have expired. Fixed: the whole read now starts again with a new redirect, and a test shows this.
3. **A local-header mismatch in D1** gave the walk verdict X instead of halting. Fixed: it halts and no `QUALIFICATION.json` is written; tested.
4. **Positive new-load labels.** The code requires a known plate state for positive labels, as the published code does, while the protocol text states the condition only for negative labels. Kept as published and recorded as item 2 of DECISIONS.md.
5. **Choices left to the code** were only partly written down. Now recorded as items 1 to 18 of DECISIONS.md.
6. **Custody.** Evaluation files went into the same folders as training files that the physics-source part may read. Fixed: they now have folders of their own. The reviewer also noted that D3 checks only that `FIT-COMPLETE.json` names the same allocation, not that it is committed. No such check was added to the code; in the run the seal was pushed at 14:03:24 and D3 began at 14:06:17.
7. **Gate records.** The reference checkpoints were not checked against their fingerprints in the protocol, and reload equality was checked on only 2,048 rows. Fixed: the fingerprints are checked (all three match), and every row is checked.
8. **Publication housekeeping.** This guide needed a rewrite, a Simple edition and a separate reader; a configuration entry carried a name tied to another tool; the code branch had to be joined to the published protocol; and the forecast files take more disk space than the protocol estimated. The rewrite and this Simple edition are done; this version, brought up to date after the run, still needs its separate reader (see [Open items](#open-items)); the entry was renamed; the code branch now starts from the main branch, which holds the published protocol; the disk use is recorded as item 18 of DECISIONS.md.

These fixes were made after the C1b review and before the header probe, and were first checked in the C2 review.

### The review of the header probe and the allocation (C2)

A separate reviewer checked the probe records, `QUALIFICATION.json`, `ALLOCATION.json` and the code fixes on 27 November 2026, as described in [The single allocation](#the-single-allocation-c2). The reviewer also reran the downloader test on the fixed code, where it passes, and on the code checked at C1b, where it stops at the case of a repeated ranged read, as expected before the fix. No blocking or major problem was found in the records, the groups or the code fixes. The reviewer found one blocking problem and two major problems in the texts, and five minor points:

1. **Blocking: review history in DECISIONS.md.** DECISIONS.md said that all 18 choices had been reviewed with the code at C1b. Items 13 to 17 are the fixes made after that review, and they were first reviewed at C2. Corrected; DECISIONS.md also says that its first wording made the same claim.
2. **Major: unexplained terms in this guide.** Several terms were used without explanation, among them hash order and salt, bootstrap, p-value, trend forms, the G8 variety sets, inner folds and the tuned arm, penalty and the random-readout control. They are now explained in [Words used in this guide](#words-used-in-this-guide).
3. **Major: unexplained terms in the Technical edition and DECISIONS.md.** Names such as Q6, QP and X, the six-name rule, the names of the stages, arms and gates, and TAG appeared with no explanation where they were first used. The Technical edition now has a list of terms with the protocol section of each, and the word list of DECISIONS.md is extended.
4. **The probe ran on fixes not yet reviewed.** The reviewer then checked them and found them correct, and they changed only paths that the probe never took. This is now stated in both editions and in DECISIONS.md (see [Which code ran](#the-header-probe-d1)).
5. **`allocate.py assign` and `assign.py` give different fingerprints.** Explained under [Stage C2](#stage-c2-the-allocation-done-and-reviewed).
6. **The fit counts did not match the protocol's estimate.** Explained under [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done): the protocol's estimate includes the inner-fold fits of G9.
7. **Precision.** The CPU slots were described as shared by every training job, though only this code's fits used them; all reference checkpoints were described as checked against fingerprints, though only the three M1 checkpoints have one; DECISIONS.md said that the training arrays hold the training pool only, though they also hold the 12 earlier people; and its item 18 gave the disk estimate for 80 qualified people instead of the actual 65. All corrected in the texts. The description at the top of `lanes.py` still describes the shared design; it is left unchanged because its fingerprint is recorded in `S0-GATES.json`, and changing it would break the code check in [Checking the published records](#checking-the-published-records).
8. **Open items already disclosed.** The plan for sharing the processor, the commit check in D3, F5 and the date in the lease note were open at that time. The first two were handled in the run as the code review's list above says, no forecast was made with F5, and the date in the lease note stays as recorded (see [Open items](#open-items)). The reviewer also noted that the probe logs were committed with C2 rather than with the results; that only adds files and contains no signed address.

### The review of the fits and the fit seal (C3)

A separate reviewer checked this stage on 27 November 2026, before the fit seal was pushed. The reviewer compared the D2 records with the archive's table of contents, using an independent reader; compared the job list with the protocol's rules; fitted 22 of the 1,742 models again with the committed code and got files identical byte for byte to the sealed ones; ran the F4 choice again, with an identical result; recomputed P1; and compared every fingerprint in `FIT-COMPLETE.json` with the private files. No blocking or major problem was found. There were three minor points:

1. **Guides out of date.** Both guides to the run code still described D2, the extraction, the fits and C3 as not run. They are brought up to date in this version.
2. **The start condition of the fits.** This guide said that a plan for sharing the processor had to be settled before `fit.py run`. It was not met as written: a private arrangement kept the total at 16 threads (see [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done)). The fitted numbers are not affected.
3. **No commit check in D3.** The downloader does not check that `FIT-COMPLETE.json` is committed or pushed, so the public time of the seal depends on the push. The code is unchanged; the seal was pushed at 14:03:24, before D3 began at 14:06:17.

### The review of the forecasts, the forecast seal and the P2 prediction (C5)

A separate reviewer checked these stages on 27 November 2026, before C4 and C5 were pushed. The reviewer checked the D3 records in the same way; compared the forecast seal with the six forecast files; made the forecasts of 24 methods (fitted models, controls and frozen checkpoints) again from the saved model files and the inputs alone, and found them identical to the sealed ones on all 17,888 rows; confirmed that S-b had opened only the two forecast files of M1, M2 and M3 below N_max; and recomputed the S-b errors and every P2 prediction with separate code. No blocking or major problem was found. There were three minor points:

1. **The public time of the forecast seal.** The seal became public only when it was pushed, and that was after S-b. Check 8 of this guide had said that the order could be read from the public repository. Check 8 is corrected, and the results editions state the order.
2. **The custody sentence.** The sentence in `FORECASTS-SEAL.json`, and in the message of its commit, says more than is true: the extraction program had computed the targets, and the forecasting program opens `EVAL-WALKS.json`, which holds each walk's counts of rows with a target. The sealed file is unchanged. The exact custody is stated under [The forecasts](#the-forecasts-and-seal-c4-done), under [What stays private](#what-stays-private-and-why) and in the results editions.
3. **Guides out of date.** Both guides were still out of date. They are brought up to date in this version.

## Open items

1. **The fitted models of the largest rung.** Section 18 of the protocol lists, for C6, the M1 checkpoint of seed 20261124 at 47 people, the M3 trees at 47 people in the ONNX format and the M2 coefficients, under CC0 with the notice. They are not exported yet. The fitted models are private, and their fingerprints are in `FIT-COMPLETE.json`.
2. **Separate reader.** The results editions, `NOTICE.md`, this guide, its Technical edition and DECISIONS.md, as brought up to date after the run, need a separate reader.
3. **The replay in this folder.** `replay.py` covers the main impulse averages and 40 targets, where section 14 of the protocol asks for every average. The other averages were recomputed by private checks. `REPLAY.json` and the three score locks stay private.
4. **The forecast seal's wording and public time.** The `custody` sentence of `FORECASTS-SEAL.json` says more than is true, and the seal became public after S-b (see [The forecasts](#the-forecasts-and-seal-c4-done) and check 8 in [Checking the published records](#checking-the-published-records)). Neither can be changed afterwards; both are stated in the results editions.
5. **Sharing the processor.** In this run the limit of 16 threads was kept by a private arrangement (see [The fits](#the-fits-the-f4-choice-p1-and-seal-c3-done)). In a later run, either every training job takes its cores through the shared slot folder, or the other training work and this one run one after the other. The description at the top of `lanes.py` still describes the shared design; it is unchanged because the file's fingerprint is recorded in `S0-GATES.json` and `FIT-COMPLETE.json`.
6. **Commit check in D3.** The downloader does not check that `FIT-COMPLETE.json` is committed or pushed. D3 runs only once and has run, with the seal pushed first.
7. **Date in the lease note.** The note recorded in D1 says "C1b reviewed 28 Nov"; the review and the probe both took place on 27 November 2026, at the UTC times in the receipts.
8. **F5.** The optional Research Edition was not admitted and no forecast was made with it, so no result depends on it.

## Choices the protocol left to the code

The protocol fixes the data, the groups, the models and the scoring, but leaves 18 smaller details to the code. [DECISIONS.md](DECISIONS.md) lists each one with the reason and the code that applies it. All 18 were written into the code before any byte of the 80 people's recordings was read, and none was chosen by looking at a result. Items 1 to 12 and 18 were in the code checked in the C1b review; items 13 to 17 are the fixes for that review, first checked in the C2 review. No choice changed during the run. In short:

1. **Numbering.** Walks and people get numbers that only fix the order of rows. The 36 earlier walks keep their earlier numbers, so the 12-person rung repeats the earlier fits row for row.
2. **New-load labels.** A row is labelled only when the plate's state at the forecast time is known, as in the published code.
3. **Training rows.** A row is used for training if either target can be scored. With 12 people, every such row has an impulse target (9,586 impulse rows, 9,150 new-load rows, none with a new-load label only).
4. **Fixed number of rows (S4).** The side arm that holds the number of rows fixed uses 9,586 rows at every rung, chosen by fingerprint ranking.
5. **Force-only trees (S2-M3).** The absent muscle channels get a neutral scale, so the scaling stays defined.
6. **Earlier muscle signals (S6 and two F4 arms).** These are trained and compared only on rows where the earlier 200 ms window is complete, and the normal arm is scored on the same rows.
7. **Floor for new-load labels.** At least 10 evaluation people who each have both a new load and no new load.
8. **Smallest detectable effect.** Uses the sample standard deviation (dividing by the number of people minus one).
9. **Second bootstrap.** The sensitivity check that also resamples fits uses its own seed, 20261128, so the main resampling stays as fixed.
10. **What S-b opens.** Only M1, M2 and M3 below N_max; the side arms are first scored at S-c.
11. **Extra walks.** When one of the first three walks fails, both the 4th and 5th walks are probed if they exist.
12. **Spacing.** At least 1.1 s between requests.
13. **One repeat.** After a 429 or 5xx answer, the whole read is tried once more after 60 s with a new redirect; a second such answer stops the stage.
14. **Local-header mismatch.** Stops the stage in every download.
15. **Reference checkpoints.** Checked against their fingerprints in the protocol before comparison.
16. **Reload equality.** Every saved model is reloaded and checked on every training row.
17. **Custody folders.** Evaluation files are kept in folders that the physics-source part is never given.
18. **Disk.** Forecasts are stored as 64-bit numbers, which takes more disk space than the protocol estimated: after the run the private folder holds about 1.0 GB (1,005,701,390 bytes), against the estimate of under 0.7 GB. No number changes.
