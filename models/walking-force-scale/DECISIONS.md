# Walking-force quantity ladder: choices the protocol leaves to the code

[Run code, Technical edition](README-CODE.md) · [Run code, Simple edition](README-CODE-SIMPLE.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Machine-readable protocol](PROTOCOL.json)

Protocol version 1 ([PROTOCOL.json](PROTOCOL.json)) fixes the data, the split of people into groups, the models and the scoring. It leaves 18 smaller details to the code. This file lists each one: what the code does, why, and which function does it. The results will cite these items by their numbers. If this file and PROTOCOL.json disagree, PROTOCOL.json governs.

## When these choices were fixed

All 18 choices were written into the code before any byte of the 80 new people's recordings was read, and none was made by looking at a result. They were reviewed with the code at stage C1b.

The first wording of this file was committed before the header probe (stage D1) began: the commit's author time is 11:54:47 UTC on 27 November 2026, and D1 started at 11:55:07 UTC. That commit was not pushed before D1, so this order rests on the local commit record, not on a public time. After D1 and the allocation (stage C2), the file was rewritten in plainer words. No choice changed. The first wording has sha256 `55f8f68d9a3ffa56cd262c92e5b1a1358f51212921d1d65c13ce85fde6ae2e95` (git blob `9bc409b59bd61907a078711668a195911539fb05`) and stays in this folder's history. D1 read only the file headers of the candidates' walks, and no forecast or score exists yet.

## Words used here

- **Walk**: one recorded pass along the walkway, stored as one file in the dataset's archive.
- **Issue time** and **row**: a forecast is made every 20 ms of a walk (at sample t). Each issue time gives one row per force plate (plates 1 and 2).
- **Impulse**: the force on a plate added up over the next 100 ms, in newton-seconds (N·s). **New load**: the moment a plate starts carrying a foot.
- **Support**: a row has impulse support when its impulse target can be scored, and new-load support when its new-load label can be scored (protocol section 6).
- **Rung**: one training-set size, counted in people. **Draw**: one fixed way of picking which extra people join a rung. **N_max**: the largest rung, all training people.
- **M1, M2, M3**: the three model families (the compact three-pass recurrent model, ridge and logistic regression, boosted trees). An **arm** is a variant of a family, such as S2 (force only) or S4 (fixed number of rows).
- **EMG**: muscle voltage measured on the skin. It is not a nerve recording.

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

17. **Custody folders.** Evaluation walks (D3) and their receipts go to `eval-walks/`, and the EVAL-* arrays to `eval-arrays/`, inside the private folder. The physics-source track may be given read access to `walks/` and `arrays/` (training pool only) and is never given the evaluation folders, fits or forecasts. (`common.PRIVATE_FOLDERS`)

18. **Forecast precision and disk.** Forecasts are stored as 64-bit floats. At Q = 80 they take roughly 0.5 GB uncompressed, so the private folder may exceed the protocol's estimate of under 0.7 GB. This changes storage only, not any number. (`issue.py`)
