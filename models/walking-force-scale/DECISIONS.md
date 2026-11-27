# Walking-force quantity ladder: choices the protocol leaves to the code

Protocol version 1 ([PROTOCOL.json](PROTOCOL.json)) fixes the data, the allocation, the models and the scoring. A few details it leaves open. The run code fixed each of them before any byte of the 80-person pool was read: they were written into the code reviewed at C1b, and this list was committed before the header probe (D1) ran. Each item names the code that applies it. If this file and PROTOCOL.json disagree, PROTOCOL.json governs.

The results will cite this file. None of these choices was made by looking at a result on the pool.

## Data and indices

1. **Member and participant indices.** The 36 walks of the 12 earlier fit people keep member indices 0 to 35, in the order of the earlier fit caches (`common.FIT12_WALKS`). The walks of the training pool and the evaluation group follow in ascending order of subject code, then walk number. Participant indices put the 12 fit people first, in the earlier salted order (`common.fold_order`), then everyone else in ascending code order. Indices only order rows and group weights; they do not enter any model. With this rule the 12-person rung reproduces the sealed earlier fits row for row. (`walks.walk_table`)

2. **Positive new-load labels need a known plate state at the issue.** The code makes a row positive only when the plate state at sample t is UNLOADED or LOADED, the same condition the protocol states for negative rows. The protocol text states the condition for negatives only. The code follows the published adapter (sha256 `1666536b…`, `label_issues`), and gate G1 shows our rows are bit-identical to the published ones on the 36 fit walks. Section 6 of the protocol says the task is the published task unchanged, so the published rule is applied. (`extract.issue_targets`)

## Training tables

3. **The training table is the union of impulse and new-load support.** A row enters a fit's training table when it has impulse support or new-load support. Rows with new-load support but no impulse support count in the new-load weights and in the prior, but M1 never draws them, because M1 samples rows in proportion to impulse weight; the impulse regressors of M2 and M3 leave them out. At N = 12 there are no such rows (9,586 impulse rows, 9,150 new-load rows, 0 new-load-only rows), so this matches the published recipe there. The published fit packet asserted that every row had impulse support. (`compact.training_table`, `threepass.TrainingBatch`)

4. **S4 size.** The fixed example budget of arm S4 equals the number of rows in the 12-person rung's training table (the union of item 3; 9,586 rows). Rows are ranked by sha256 of TAG + `|example-budget|` + N, draw, subject, walk, tick and plate, and the lowest-ranked rows are kept. At N_max, which has no draws, the draw number in this hash is 0. (`fit.budget_subsample`, `plan.py`)

5. **Neutral scaling in the force-only tree arm (S2-M3).** In S2 the six EMG channels are absent by design: they are encoded as 0 with availability mask 0. Their standardisation is set to centre 0 and scale 1, so their missing values do not make the scaling undefined. The other channels are standardised as published. M3 itself is untouched, and the tree gate checks it bit for bit against the sealed tree file. (`trees.fit_scaling`)

6. **Earlier-EMG arms.** S6 and the two F4 earlier-EMG arms need a valid EMG window ending 500 ms before the issue. They are trained on, and compared on, rows where that earlier window is valid; the contemporaneous arm is scored on the same rows for the paired comparison. (`compact.training_table` with `emg_mode='earlier'`; `score.py`, masks `impulse_early` and `event_early`)

## Scoring

7. **Brier floor.** "At least 10 with both outcomes" is read as at least 10 scoreable evaluation people who each have at least one positive and one negative new-load row. (`score.py`, `both_classes`)

8. **Minimum detectable effect.** The standard deviation of the per-person differences uses the sample formula (ddof = 1). (`score.Scorer.contrast`)

9. **Sensitivity bootstrap.** The bootstrap over people and then replicates draws its indices from `numpy.random.default_rng(20261128)`, one more than the primary seed 20261127, so the primary index matrices stay as the protocol fixes them. (`score.hierarchical`)

10. **What stage S-b opens.** S-b scores only M1, M2 and M3 at the rungs below N_max; their forecasts are in the only file S-b can open. The secondary arms below N_max sit in the file of other forecasts and are first scored at S-c. (`issue.group_of`)

## Header probe and downloads

11. **Extra walks.** When one of a person's first three walks is not Q6, every further numbered walk of that person (the 4th and, if present, the 5th) is probed, lowest number first, even if the 4th alone would be enough. The protocol allows at most 8 such requests. (`qualify.probe_person`)

12. **Pacing.** Requests start at least 1.1 s apart, rather than 1.0 s, so that network jitter cannot bring two requests closer than 1 s at the server. Candidates are probed in ascending code order. (`fetch.Client`)

13. **One retry per read.** A read is one redirect from the stable address and one ranged GET. If either answers 429 or 5xx, the whole read is tried once more after 60 s, starting again at the stable address with a fresh redirect, because the signed address lives about 10 s. A second 429 or 5xx in that read halts the stage. (`fetch.Client.read`)

14. **Local-header mismatch.** A local header that differs from the central directory is a failed download check and halts the stage in D1, D2 and D3 alike. In D1 it is never turned into a walk verdict, and no QUALIFICATION.json is written. (`qualify.probe_walk`, `fetch.whole_member`)

## Gates and storage

15. **Reference checkpoints.** Gates G0 and G2 check each sealed three-pass reference checkpoint (seeds 20261124 to 20261126) against its sha256 pin in PROTOCOL.json before comparing tensors. The LSTM checkpoints replayed beside them are not protocol models and have no pin; their sha256 is recorded in the gate receipt. (`gates.part_a`)

16. **Reload equality.** Each saved checkpoint is reloaded and its forecasts are recomputed on every row of its training table (in the gates, the whole 12-person table) before its record is written. (`fit._fit_job`, `gates.part_a`)

17. **Custody folders.** Evaluation walks (D3) and their receipts go to `eval-walks/`, and the EVAL-* arrays to `eval-arrays/`, inside the private folder. The physics-source track may be given read access to `walks/` and `arrays/` (training pool only) and is never given the evaluation folders, fits or forecasts. (`common.PRIVATE_FOLDERS`)

18. **Forecast precision and disk.** Forecasts are stored as 64-bit floats. At Q = 80 they take roughly 0.5 GB uncompressed, so the private folder may exceed the protocol's estimate of under 0.7 GB. This changes storage only, not any number. (`issue.py`)
