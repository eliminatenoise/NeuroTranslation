# Walking-force quantity ladder: choices the protocol leaves to the code

[Run code, Technical edition](README-CODE.md) · [Run code, Simple edition](README-CODE-SIMPLE.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Machine-readable protocol](PROTOCOL.json)

Protocol version 1 ([PROTOCOL.json](PROTOCOL.json)) fixes the data, the split of people into groups, the models and the scoring. It leaves 18 smaller details to the code. This file lists each one: what the code does, why, and which function does it. The results will cite these items by their numbers. If this file and PROTOCOL.json disagree, PROTOCOL.json governs.

## Words used here

- **Stages**: the steps of the protocol, in order (protocol section 14). S0: engineering gates on the 12 earlier fit people. C1b: the separate review of the run code against the protocol. D1: the header probe, which reads only the file headers of the candidates' walks. C2: the qualification receipt and the allocation of people to groups, with their separate review. D2 and D3: the downloads of the training pool and of the evaluation group. S-b: scoring of the rungs below N_max, before any N_max forecast is opened. S-c: the final scoring of everything else. A stage whose name starts with C ends in a commit.
- **Gates G0, G1, G2**: checks in S0 that our code repeats the earlier work exactly (protocol section 13). G0 re-trains the sealed 12-person three-pass checkpoints from the earlier encoded data. G1 rebuilds the 9,946 issue rows of the 36 fit walks from the C3D files. G2 runs the whole path from the C3D files to the checkpoints.
- **Q6, QP, X**: the classes a walk or a person gets in the header probe (protocol section 4.3). Q6 passes every check, including the six-name rule: the six EMG channels `Voltage.LBF`, `LERS`, `LGAS`, `LRF`, `LST` and `RERS` are each present once, in volts. QP passes every check except the six-name rule and has at least four EMG voltage channels. X fails some other check. A person is Q6 with at least three Q6 walks.
- **TAG** and **hash order**: TAG is the fixed text `10.6084/m9.figshare.24192480.v1|walking-scale|` followed by the sha256 of PROTOCOL.json (protocol section 5.1). A hash order sorts items by the sha256 of TAG plus a label and the item, so nobody could choose or foresee the order before the protocol was final.
- **Walk**: one recorded pass along the walkway, stored as one file in the dataset's archive.
- **Issue time** and **row**: a forecast is made every 20 ms of a walk (at sample t). Each issue time gives one row per force plate (plates 1 and 2).
- **Impulse**: the force on a plate added up over the next 100 ms, in newton-seconds (N·s). **New load**: the moment a plate starts carrying a foot.
- **Support**: a row has impulse support when its impulse target can be scored, and new-load support when its new-load label can be scored (protocol section 6).
- **Rung**: one training-set size, counted in people. **Draw**: one fixed way of picking which extra people join a rung. **N_max**: the largest rung, all training people.
- **M1, M2, M3**: the three model families (the compact three-pass recurrent model, ridge and logistic regression, boosted trees). An **arm** is a variant of a family, such as S2 (force only), S4 (fixed number of rows) or S6 (EMG window ending 500 ms before the issue); protocol section 9 lists them all.
- **F4**: the published force baselines (`common-six.npz`), straight-line models stored with four penalty settings each; one setting is chosen on the training-pool people (protocol section 8). Its two earlier-EMG arms, one for impulse and one for new load, use an EMG window that ends 500 ms before the issue.
- **EMG**: muscle voltage measured on the skin. It is not a nerve recording.

## When these choices were fixed

All 18 choices were written into the code before any byte of the 80 new people's recordings was read, and none was made by looking at a result. Items 1 to 12 and 18 were in the code reviewed at stage C1b. Items 13 to 17 are the fixes for that review's findings. They were committed after the review and before D1, and they were first reviewed with the allocation at stage C2, which found them correct.

D1 therefore ran on the code reviewed at C1b plus these fixes. Of the fixes, only items 13 and 14 change code that D1 uses, and they change only its retry and halt paths. Neither path was taken in D1: all 241 reads were first attempts, every ranged read was answered with status 206, and no local header differed from the central directory.

The first wording of this file was committed together with those fixes, before D1 began: the commit's author time is 11:54:47 UTC on 27 November 2026, and D1 started at 11:55:07 UTC. That commit was not pushed before D1, so this order rests on the local commit record, not on a public time. The first wording said that the choices were written into the code reviewed at C1b; that was wrong for items 13 to 17, as stated above. After D1 and the allocation, the file was reworded in plainer language; after the C2 review, the review history above was corrected and the word list was extended. No choice changed. The first wording has sha256 `55f8f68d9a3ffa56cd262c92e5b1a1358f51212921d1d65c13ce85fde6ae2e95` (git blob `9bc409b59bd61907a078711668a195911539fb05`) and stays in this folder's history. D1 read only the file headers of the candidates' walks, and no forecast or score exists yet.

## Data and indices

1. **Member and participant indices.** Each walk gets a number, its member index, and each person a participant index. These numbers only put rows in a fixed order and group them for weighting; no model sees them. The 36 walks of the 12 earlier fit people keep member indices 0 to 35, in the order of the earlier fit caches (`common.FIT12_WALKS`). The walks of the training pool and the evaluation group follow, in ascending order of subject code and then walk number. Participant indices put the 12 fit people first, in the earlier salted hash order (`common.fold_order`), then everyone else in ascending code order. With this rule the 12-person rung reproduces the sealed earlier fits row for row. (`walks.walk_table`)

2. **Positive new-load labels need a known plate state at the issue.** A row is positive when a new load starts in the next 100 ms, and negative when none does. The code makes a row positive only when the plate state at sample t is known, UNLOADED or LOADED, which is the same condition the protocol states for negative rows. The protocol text states the condition for negatives only. The code follows the published adapter (sha256 `1666536b…`, function `label_issues`), which applies it to both, and gate G1 shows that our rows are bit-identical to the published ones on the 36 fit walks. Protocol section 6 says the task is the published task unchanged, so the published rule applies. (`extract.issue_targets`)

## Training tables

3. **The training table is the union of impulse and new-load support.** A row enters a fit's training table when it has impulse support or new-load support. Rows with new-load support but no impulse support count in the new-load weights and in the prior (the weighted base rate of new loads in the training rows), but M1 never draws them, because M1 picks its training rows in proportion to impulse weight; the impulse regressions of M2 and M3 leave them out. At N = 12 there are no such rows (9,586 impulse rows, 9,150 new-load rows, 0 rows with new-load support only), so there this matches the published recipe. The published fit packet asserted that every row had impulse support. (`compact.training_table`, `threepass.TrainingBatch`)

4. **S4 size.** Arm S4 fits each model on the same number of rows at every rung, to separate more people from more rows. That number equals the size of the 12-person rung's training table (the union of item 3): 9,586 rows. Rows are ranked by the sha256 of TAG + `|example-budget|` + N, draw, subject, walk, tick and plate, and the lowest-ranked rows are kept. At N_max, which has no draws, the draw number in this text is 0. (`fit.budget_subsample`, `plan.py`)

5. **Neutral scaling in the force-only tree arm (S2-M3).** In S2 the six EMG channels are absent by design: they are entered as 0 with availability mask 0. The tree input standardises each channel by its mean and standard deviation over the available training values, which are undefined for a channel with no available value. So these six channels get centre 0 and scale 1. The other channels are standardised as published. M3 itself is untouched, and the tree gate checks it bit for bit against the sealed tree file. (`trees.fit_scaling`)

6. **Earlier-EMG arms.** S6 and the two F4 earlier-EMG arms use an EMG window that ends 500 ms before the issue. They are trained on, and compared on, rows where that earlier window is valid. The arm with EMG up to the issue is scored on the same rows, so the comparison is paired. (`compact.training_table` with `emg_mode='earlier'`; `score.py`, masks `impulse_early` and `event_early`)

## Scoring

7. **Brier floor.** The Brier score measures the new-load forecasts. The protocol makes Brier labels confirmatory only with "at least 10 with both outcomes". The code reads this as at least 10 scoreable evaluation people who each have at least one positive and one negative new-load row. (`score.py`, `both_classes`)

8. **Minimum detectable effect.** The smallest effect the test can detect uses the standard deviation of the per-person differences. The code uses the sample formula, which divides by the number of people minus one (ddof = 1). (`score.Scorer.contrast`)

9. **Sensitivity bootstrap.** Besides the primary bootstrap over people, a sensitivity check resamples people and then, for each person, the replicate fits of the rung. Its random indices come from `numpy.random.default_rng(20261128)`, one more than the primary seed 20261127, so the primary index matrices stay exactly as the protocol fixes them. (`score.hierarchical`)

10. **What stage S-b opens.** S-b scores only M1, M2 and M3 at the rungs below N_max; their forecasts are in the only file S-b can open. The secondary arms below N_max sit in the file of other forecasts and are first scored at S-c. (`issue.group_of`)

## Header probe and downloads

11. **Extra walks.** When one of a person's first three walks is not Q6, every further numbered walk of that person (the 4th and, if present, the 5th) is probed, lowest number first, even if the 4th alone would be enough. The protocol allows at most 8 such requests. (`qualify.probe_person`)

12. **Pacing.** Requests start at least 1.1 s apart, rather than 1.0 s, so that network delays cannot bring two requests closer than 1 s at the server. Candidates are probed in ascending code order. (`fetch.Client`)

13. **One retry per read.** A read is one redirect from the stable address (a request that returns a short-lived signed storage address) and one ranged GET (a request for a stated span of bytes). If either answers 429 (too many requests) or 5xx (a server error), the whole read is tried once more after 60 s, starting again at the stable address with a fresh redirect, because the signed address lives about 10 s. A second 429 or 5xx in that read halts the stage. (`fetch.Client.read`)

14. **Local-header mismatch.** Each file in the archive starts with a local header that repeats its name, compression method, CRC-32 checksum and sizes, which the archive's central directory also lists. A local header that differs from the central directory is a failed download check and halts the stage in D1, D2 and D3 alike. In D1 it is never turned into a walk verdict, and no QUALIFICATION.json is written. (`qualify.probe_walk`, `fetch.whole_member`)

## Gates and storage

15. **Reference checkpoints.** Gates G0 and G2 check each sealed three-pass reference checkpoint (seeds 20261124 to 20261126) against its sha256 pin in PROTOCOL.json before comparing tensors. The LSTM checkpoints replayed beside them are not protocol models and have no pin; their sha256 is recorded in the gate receipt. (`gates.part_a`)

16. **Reload equality.** Each saved checkpoint is reloaded and its forecasts are recomputed on every row of its training table (in the gates, the whole 12-person table) before its record is written. (`fit._fit_job`, `gates.part_a`)

17. **Custody folders.** Evaluation walks (D3) and their receipts go to `eval-walks/`, and the EVAL-* arrays to `eval-arrays/`, inside the private folder. The physics-source track may be given read access to `walks/` (the training pool's decoded walks) and `arrays/` (the TRAIN-* arrays, which hold the rows of the 12 earlier fit people and of the training pool), and is never given the evaluation folders, fits or forecasts. (`common.PRIVATE_FOLDERS`)

18. **Forecast precision and disk.** Forecasts are stored as 64-bit floats. Before D1, for the largest case of Q = 80 qualified people (24 evaluation people), they were estimated at roughly 0.5 GB uncompressed. The actual Q is 65, with 20 evaluation people, and the same estimate gives roughly 0.45 GB. The decoded walks of the training pool and the evaluation group add 258,302,336 bytes (from ALLOCATION.json), so the private folder may exceed the protocol's estimate of under 0.7 GB. This changes storage only, not any number. (`issue.py`)
