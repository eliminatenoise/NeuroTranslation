# Walking-force quantity ladder: run code (commit C1b)

Technical edition, first draft for the C1b review. The Simple edition is written with the results, as section 18 of [PROTOCOL.md](PROTOCOL.md) states. If this file and [PROTOCOL.json](PROTOCOL.json) disagree, PROTOCOL.json governs.

This folder holds the code that carries out protocol version 1 from the header probe (D1) to the scored results (S-c), and the receipt of the engineering gates of stage S0 ([S0-GATES.json](S0-GATES.json)). Every part was tested on the 12 earlier fit people (36 walks, already used for fitting before) or on synthetic inputs. No byte of the 80-person pool was downloaded or opened.

## Files

| File | Role | Runtime |
| --- | --- | --- |
| `common.py` | Constants, hashing, JSON writing, the private configuration | any |
| `c3dread.py` | Whitelist C3D reader and the walk gates Q6, QP and X (protocol 4.2, 4.3) | any |
| `qualify.py` | Header probe with bounded inflation, the person rule, the qualification receipt and its checker | any |
| `fetch.py` | Downloader for D1, D2 and D3: fresh redirect per request, ranged reads, pacing, retries, receipts | any |
| `assign.py` | Checked front end for `allocate.py assign` | any |
| `allocate.py` | Unchanged from C1 (pinned in PROTOCOL.json) | any |
| `walks.py` | Member and participant indices; checked reads of walk files | any |
| `extract.py` | Input adapter: walk to history-only issue rows, and targets in a separate array set | B |
| `compact.py` | Compact input, published person weights, per-person errors | A, B |
| `threepass.py` | M1 and its arms C4, S1, S2, S3, S4, S6 | A |
| `trees.py` | M3, S5 and tuned trees (G9) | B |
| `linear.py` | M2, tuned ridge (G9), the F4 refit and the F4 penalty choice | B |
| `frozen.py` | F1 to F4 through the published code, controls C1 to C3, the list of checkpoints not scored | A (F1), B |
| `plan.py` | Every fit of the ladder, derived from ALLOCATION.json | any |
| `prepare.py` | Extraction stage after D2 and after D3 | B |
| `fit.py` | Fit lanes, record chain, F4 choice, P1, the seal FIT-COMPLETE.json | A, B |
| `issue.py` | Forecasts on history-only inputs; FORECASTS-SEAL.json | A, B |
| `trend.py` | Trend forms, P1 and P2 predictions, the trend test | B |
| `score.py` | Stage S-b (writes P2-TREND-PREDICTION.json) and stage S-c (writes RESULTS.json) | B |
| `replay.py` | Independent replay of every primary aggregate and of sample rows of each plate | B |
| `lanes.py` | CPU slots shared by every training track | any |
| `gates.py` | Stage S0 gates; writes S0-GATES.json | A, B |
| `tests/` | Downloader and probe test, allocation test, numeric tests, end-to-end smoke run | A, B |

Runtime A: CPython 3.13.15, torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0. Runtime B: CPython 3.12.14, numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0. One thread per fit.

## Configuration

Local paths are never written into committed files. Each script takes `--config CFG`, a private JSON object with these keys: `codex_root`, `fit_cache_dir`, `fit_readback_file`, `central_directory_file`, `roster_file`, `features_ref_dir`, `baselines_candidates_file`, `generalization_dir`, `matched_dir` (read-only sources of the earlier fits), `repo_root` (this repository, for the published checkpoints), `private_dir` (walk files, arrays, fits, forecasts; never committed), `scratch_dir`, `out_dir`. The variable `NS_CPU_SLOTS` names the shared CPU-slot folder.

## Order of work

Each command runs only after the commit or lease named beside it.

| Stage | Command | Needs |
| --- | --- | --- |
| D1 | `fetch.py probe --lease-note TEXT` | C1 pushed, this C1b reviewed, the owner's download lease |
| C2 | `assign.py --qualification QUALIFICATION.json --directory CD` | D1 |
| D2 | `fetch.py download --group training_pool` | C2 reviewed and pushed |
| extract | `prepare.py --group training` | D2 |
| fits | `fit.py run --runtime torch` (runtime A); `fit.py run --runtime sk` (runtime B) | extraction |
| F4, P1 | `fit.py f4`; `fit.py p1 --runtime torch` and `--runtime sk` (only when T is 32 or more) | fits |
| C3 | `fit.py seal` writes FIT-COMPLETE.json | F4, P1 |
| D3 | `fetch.py download --group evaluation --fit-complete FIT-COMPLETE.json` | C3 pushed |
| extract | `prepare.py --group evaluation` | D3 |
| issue | `issue.py run --runtime torch`; `issue.py run --runtime sk` | extraction |
| C4 | `issue.py seal` writes FORECASTS-SEAL.json | issue |
| S-b, C5 | `score.py below` writes P2-TREND-PREDICTION.json | C4 |
| S-c | `score.py final --p2-sha SHA`; `replay.py` | C5 committed and pushed |

## What each stage enforces

- **D1.** For each of the first three walks of the 80 candidates, one ranged read of 8,704 bytes from the local header, then 8,192 more bytes at a time up to 65,536 bytes. The local header must equal the central directory. Inflation stops at the end of the C3D parameter section, so no sample byte is produced. Fourth and fifth walks are probed only for a person whose first three include a walk that is not Q6. Only the reasons, counts and sha256 of the compressed bytes are kept; no header byte is written. Requests to reserved, boundary or out-of-pool people are refused.
- **Downloads.** Each request takes a fresh redirect from the stable address, then one ranged read. Status 206, ETag, storage version, content range and length must equal the pins. Requests start at least 1.1 s apart, so that network jitter cannot bring two requests closer than 1 s at the server. A 429 or 5xx answer gets one retry after 60 s, then the stage halts. Whole members are checked for size and CRC-32. Receipts keep the storage host and path but drop the signed query. D3 refuses to run without a FIT-COMPLETE.json made for the same allocation. The physics-source and physics-supplement groups are never downloaded.
- **Allocation.** `assign.py` checks that allocate.py, POOL.json and ORDER.json equal their committed versions, that QUALIFICATION.json carries the protocol and pool sha256 values, that each person's probed walks follow the rule, and that the listed walks are the lowest-numbered qualified ones. It then calls allocate.py unchanged and checks the groups, sizes and rungs.
- **Indices.** The 36 earlier fit walks keep member indices 0 to 35 in the earlier cache order, so the 12-person rung reproduces the sealed fits row for row. Other walks follow in ascending code and walk number.
- **Fits.** Replicates follow PROTOCOL.json: 50 seeds (20261124 + j) at N = 12, at N_max and for both G8 sets; 10 draws × 5 seeds (20261124 + 5d + s) at intermediate rungs; one deterministic fit per training set for M2, M3 and their arms. The secondary M1 arms use the same scheme, which gives 1,450 M1-type fits and 292 tree and linear fits at Q = 80. Checkpoints are safetensors without metadata. Every checkpoint is reloaded and its forecasts recomputed before its record is written. A failed fit keeps its record and is never replaced.
- **Record chain.** LOCK (job list, code and input hashes), ATTEMPT, checkpoint, reload equality, RESULT, READBACK at the seal, SCORE-LOCK before each scoring stage.
- **Custody.** The issuer opens only the evaluation inputs. Forecasts sit in three files per runtime: the primary families below N_max (the only file S-b opens), everything at N_max, and the rest. S-c refuses to run unless the P2 file has the given sha256 and the same bytes are committed at the repository HEAD.

## Admission-review items handled in this code

Items 5, 6, 7 and 9 of the admission review could be handled without changing PROTOCOL.json:

- Item 5. Gate `Q6_on_36_fit_walks`: all 36 fit walks are Q6, through the same bounded-inflation probe code that D1 uses (each walk re-deflated, since the archive bytes of the fit walks are not cached).
- Item 6. allocate.py is unchanged, because PROTOCOL.json pins its sha256. `assign.py` adds the checks on the pool sha256, the probe order and the lowest-numbered-walk rule. `tests/test_assign.py` shows that tampered receipts are refused.
- Item 7. The NeuroTranslate 0.1 paired-plates checkpoints are listed as not scored in `frozen.NOT_SCORED`, together with the other unscored checkpoints and F5.
- Item 9. `lanes.py`: each single-thread worker holds an exclusive lock on one CPU-slot file for CPUs 16 to 31 and pins itself to that CPU. If every training track takes its CPUs through the same slot folder, all tracks together stay within 16 threads on CPUs 16 to 31. This track uses at most 12 lanes on CPUs 20 to 31. The physics-source track must take its CPUs through the same folder for this to hold.

Item 3 (replicate counts of the secondary arms) is written out in `plan.py`. Items 1, 2, 4, 8 and 10 concern protocol text, the Simple edition or claim limits, and are left to the lead.

## Not covered here

- F5 (Research Edition) is optional and is not run in this stage.
- Stage D1 and every later stage have not been run on the real pool. They run only after the C1b review and the owner's lease.
