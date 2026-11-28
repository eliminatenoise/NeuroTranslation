# Walking-force quantity ladder: run code

Technical edition · [Simple edition](README-CODE-SIMPLE.md) · [Results](README.md) · [Results, Simple edition](README-SIMPLE.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Machine-readable protocol](PROTOCOL.json) · [Choices left to the code](DECISIONS.md) · [Sources and terms](NOTICE.md)

This folder holds the code that carries out protocol version 1 of the walking-force quantity ladder, from the header probe (stage D1) to the scored results (stage S-c), and the records of every stage. Every stage up to the final scoring (S-c), and the supplement, ran on 27 November 2026 (UTC). The results are in [README.md](README.md) and, at more length, in [README-SIMPLE.md](README-SIMPLE.md). For every stage this file gives the exact command, the software runtime, what the stage reads and writes, how long it took, and what stays private. It also lists the checks a reader can repeat from the public files. Where this file and [PROTOCOL.json](PROTOCOL.json) disagree, PROTOCOL.json governs.

## Terms

The protocol's names, with the protocol section that defines each:

- **Stages** (14): S0 engineering gates on the 12 earlier fit people; C1 protocol commit; C1b separate review of the run code; D1 header probe; C2 qualification receipt and allocation, with their review; D2 training-pool download; C3 fit seal; D3 evaluation-group download; C4 forecast seal; S-b scoring of the rungs below N_max; C5 seal of the P2 prediction; S-c final scoring and independent replay; C6 results. C stages end in a commit, D stages download.
- **Q6, QP, X** (4.3): walk and person classes of the header probe. Q6 passes every walk gate, including the six-name rule: `Voltage.LBF`, `Voltage.LERS`, `Voltage.LGAS`, `Voltage.LRF`, `Voltage.LST` and `Voltage.RERS` each present once, in volts. QP passes every walk gate except the six-name rule and has at least four `Voltage.*` channels in volts. X fails another walk gate. A person is Q6 with at least three Q6 walks, QP with at least three walks that are Q6 or QP, and X otherwise.
- **Hash order, TAG** (5.1): codes sorted by the sha256 of TAG + a label + the code. TAG = `10.6084/m9.figshare.24192480.v1|walking-scale|` + the sha256 of PROTOCOL.json, so the sha256 of PROTOCOL.json salts every order.
- **Q, E, P, T** (5.2): Q is the number of Q6 people. Along the primary hash order of Q6 people: evaluation group E, physics-source group P, training pool T. QP people form the physics supplement; X people are unusable.
- **Rung, draw, N_max, inner folds** (5.3): a rung is a training-set size N = 12 + a, with a people added to the 12 earlier fit people. Rung a of draw d (d = 0 to 9) adds the first a people of draw order d, so the rungs of one draw are nested. N_max = 12 + T. Inner folds split a fit's training people into 4 by hash rank; only G9 uses them.
- **M1, M2, M3** (7): the compact three-pass recurrent model; ridge and logistic regression on the compact input; boosted trees on the published tree input.
- **Controls C1 to C4 and frozen checkpoints F1 to F5** (8): C1 persistence, C2 unconditional, C3 linear trend, C4 random recurrent readout (M1 with only its output layer trained); F1 to F5 are published checkpoints scored as published (F5 only if admitted; it was not issued), except that the F4 force baselines get their penalty chosen on the training pool. The control names C1 to C4 overlap with the stage names C1 to C6; lists of fits and forecasts mean the controls.
- **Secondary arms** (9): S1 epoch-matched M1; S2 force only; S3 M1 at width 96; S4 fixed example budget; S5 trees on the compact input; S6 EMG window ending 500 ms before the issue; G8 variety, at N_max: the 12 earlier fit people plus one walk from each of the T pool people, against the 12 plus three walks from each of the first floor(T / 3) people of draw order 0 (the two variety sets); G9 tuned, M3 leaves and M2 penalty chosen by the inner folds.
- **P1, P2, trend forms** (11): sealed predictions of the N_max result, P1 from each draw's pool tail before D3 and P2 from the rungs below N_max before S-c. Trend forms, for the mean absolute impulse error MAE(N) at N training people: L + a / sqrt(N) (primary) and c + b log2 N, against carry-forward of the second-largest rung.
- **Gates** (13): G0 training replay, G1 feature port, G2 end to end, G3 past only, the tree gates and the F4 refit.

## State on 27 November 2026

Every stage up to the final scoring (S-c) has run, and C6 is done except for the export of the N_max weights. All times in this file are UTC on 27 November 2026. Commit times are the author times in the commit records; push times are from this machine's record of each push.

| Stage | State | Record in this folder |
| --- | --- | --- |
| C1, protocol | Published at NeuroTranslation commit `3f2bae7`, pushed 11:33:22 | `PROTOCOL.md`, `PROTOCOL-SIMPLE.md`, `PROTOCOL.json`, `allocate.py`, `POOL.json`, `ORDER.json` |
| S0, engineering gates | Done, on the 12 earlier fit people only: 15 of 15 gates and 4 of 4 tests pass | `S0-GATES.json` |
| C1b, run code | Reviewed against the protocol: no blocker, no major, 8 minor findings. The fixes for these findings were committed after that review (11:54:47) and before D1, and reviewed at C2 ([Review findings](#review-findings)) | the `.py` files, `tests/` |
| D1, header probe | Run from 11:55:07 to 12:03:58, on the C1b code plus the review fixes | `QUALIFICATION.json`, `receipts/D1-requests.jsonl`, `receipts/D1-walks.jsonl` |
| C2, allocation | Computed and reviewed separately: no blocker or major finding in the D1 records, the allocation or the code fixes; its findings on the texts were corrected before the push. The allocation was committed at 12:04:59 (commit `8a8fab5`) and the corrected texts at 12:53:48 (commit `0fc1bb7`); both were pushed at 13:04:52 | `ALLOCATION.json` |
| D2, training-pool download | 13:08:41 to 13:14:17: 105 walks of 35 people | `receipts/D2-RECEIPT.json`, `receipts/D-training_pool-requests.jsonl` |
| Extraction of the training group | 13:14:45, about 2 s: 47 people, 141 walks, 42,030 issue rows | none (private arrays) |
| Fits | Runtime A 13:15:28 to 13:39:06 (1,450 fits), runtime B 13:39:17 to 13:47:10 (292 fits), on 8 lanes; 1,742 of 1,742 done, none failed | the sha256 of every fit, in `FIT-COMPLETE.json` |
| P1 and the F4 choice | P1 13:39:28 to 13:51:20; F4 penalties chosen 13:49:59 | in `FIT-COMPLETE.json` |
| C3, fit seal | Written 13:51:31, committed 13:52:48 (commit `4652d69`), reviewed separately (no blocker or major finding), pushed 14:03:24 | `FIT-COMPLETE.json` |
| D3, evaluation download | 14:06:17 to 14:09:36: 60 walks of 20 people | `receipts/D3-RECEIPT.json`, `receipts/D-evaluation-requests.jsonl` |
| Extraction of the evaluation group | 14:09:47 to 14:09:48: 20 people, 60 walks, 17,888 issue rows | none (private arrays) |
| Issue | Runtime A 14:09:58 to 14:53:18, runtime B 14:10:02 to 14:15:04; every fit issued | none (private forecasts) |
| C4, forecast seal | Written 14:54:10, committed 14:54:24 (commit `be66803`), pushed 15:08:44 | `FORECASTS-SEAL.json` |
| S-b | 14:54:32, under 1 s | none (private score lock) |
| C5, P2 prediction | Written 14:54:32, committed 14:55:40 (commit `46d27d6`); C4, S-b and C5 reviewed separately (no blocker or major finding); pushed 15:08:44 | `P2-TREND-PREDICTION.json` |
| S-c | 15:11:08 to 15:11:17 | `RESULTS.json`, committed 15:14:37 |
| Replay | 15:11:32 to 15:11:34; passed | none (private) |
| Supplement | 22:08:28 to 22:08:42, computed after S-c from the same sealed forecasts | `supplement.py`, `RESULTS-SUPPLEMENT.json`, committed 22:14:39 |
| C6, results | Results editions and notice written. The N_max weights are not exported yet ([Open items](#open-items)) | `README.md`, `README-SIMPLE.md`, `NOTICE.md` |

**D1.** 241 walks were probed: the three lowest-numbered walks of each of the 80 candidates (240) and the 4th walk of SUBJ060, whose 2nd walk failed the six-name rule. Each walk took one ranged read of 8,704 bytes from its local header: 482 requests in all (one redirect and one ranged read per walk) and 2,097,664 compressed bytes. Every ranged read answered 206 with the pinned ETag and storage version; no read was retried and none needed a continuation read. Inflation stopped at the end of the C3D parameter section on all 241 walks, so no sample byte was produced. Walk verdicts: 205 Q6, 30 QP, 6 X. People: 65 Q6, 11 QP, 4 X. A Q6 person uses their three lowest-numbered Q6 walks, so SUBJ060 uses walks 1, 3 and 4. D1 ran on the code reviewed at C1b plus the fixes for that review, which were committed 20 s before D1 started and first reviewed at C2. The fixes that D1 uses ([DECISIONS.md](DECISIONS.md) items 13 and 14) change only the retry and halt paths, and neither path was taken: every read was a first attempt and no local header differed from the central directory.

**C2.** With Q = 65 qualified people, the size rule gives an evaluation group E of 20 people, a physics-source group P of 10 and a training pool T of 35. The rungs are N = 12, 18, 24, 36 and 47 people (6, 12, 24 and 35 people added to the 12 earlier fit people), with 10 nested draws at each intermediate rung. Because T is at least 32, the pool-tail prediction P1 applies, with 11 people per draw. The 11 QP people form the physics supplement and the 4 X people are unusable, each with its reasons. SUBJ099 stays out of every role, unopened. The group lists are in `ALLOCATION.json`. The separate C2 review rebuilt `QUALIFICATION.json` byte for byte from the two receipt files and `ALLOCATION.json` byte for byte through `assign.py`, and recomputed the groups, rungs, draws, folds, pool tails and variety sets from the protocol rules with its own code; it found no blocker or major problem in either file.

**D2.** The 105 walks of the 35 training-pool people took 210 requests (one redirect and one ranged read per walk). Every ranged read was a first attempt and answered 206 with the pinned ETag and storage version. 98,801,524 bytes were received: each read runs from a walk's local header to the next local header, and 98,793,925 of the bytes are compressed member data, the figure of `ALLOCATION.json`. The walks decode to 165,541,248 bytes. Every decoded walk matched the size and CRC-32 of the central directory, and a second private pass over the size, CRC-32 and sha256 of all 105 stored walks found no mismatch. The receipts were committed at 13:52:58 (commit `c6e6909`).

**Extraction of the training group.** 47 people, 141 walks and 42,030 issue rows; no walk is without supported rows. The 12 earlier fit people give 9,946 rows (9,586 with an impulse target, 9,150 with a new-load label), the same counts as in the S0 gates. The 35 pool people add 32,084 rows (31,034 with an impulse target, 30,579 with a new-load label).

**Fits.** `plan.py` gives 1,742 fits; all were done, none failed, and every fit reloaded to identical forecasts. Runtime A took 23 min 38 s for its 1,450 fits and runtime B 7 min 53 s for its 292 fits, each on 8 single-thread lanes on CPUs 24 to 31 ([Fits](#fits-f4-choice-p1-and-the-c3-seal-done) gives the CPU arrangement).

**P1, the F4 choice and C3.** P1 for M1 (runtime A) ran on one more CPU beside the runtime-B fits and took 712 s; P1 for M2 and M3 took 53 s and the F4 choice 2 s. A private check compared the 12-person fits of this run with the earlier sealed files: the M1 checkpoints of seeds 20261124 to 20261126 have the sha256 pinned in PROTOCOL.json, and M2, M3 and S5 at N = 12 give bit-identical forecasts on 9,586 rows. The seal `FIT-COMPLETE.json` was written at 13:51:31, 42 min 50 s after D2 began. The separate C3 review refitted 22 of the fits with the committed code, every checkpoint byte-identical to the sealed one, before the seal was pushed at 14:03:24 ([Review findings](#review-findings)).

**D3 and the extraction of the evaluation group.** D3 began at 14:06:17, after the remote main branch held the fit seal. The 60 walks of the 20 evaluation people took 120 requests; every ranged read was a first attempt and answered 206 with the pinned ETag and storage version. 55,832,987 bytes were received, 55,828,652 of them compressed member data, and the walks decode to 92,761,088 bytes. The extraction gave 20 people, 60 walks and 17,888 issue rows: 17,288 with an impulse target and 17,040 with a new-load label. The receipts were committed at 15:14:59.

**Issue and C4.** Each runtime issued its forecasts on one CPU, side by side: runtime A 1,451 methods in 43 min 20 s (200 primary fits below N_max, 450 fits at N_max, 801 others including F1) and runtime B 305 methods in 5 min 2 s (62 below N_max, 14 at N_max, 229 others including the controls C1 to C3, F2, the four F3 models and the five F4 arms). All 1,742 fits were issued. Every forecast is finite except those of `F4_early_force_earlier_emg` on the 3,000 rows without a valid earlier-EMG window, which that arm does not score ([DECISIONS.md](DECISIONS.md) item 6). The seal `FORECASTS-SEAL.json` names the sha256 of the six forecast files.

**S-b and C5.** S-b began 8 s after the forecast seal was committed. It read the two files of the primary fits below N_max and wrote `P2-TREND-PREDICTION.json`. The forecast seal and P2 were pushed together at 15:08:44, so the forecast seal became public after S-b, not before it. The protocol asks for C1, C2, C3 and C5 to be pushed before the next stage and does not list C4; that the seal preceded S-b rests on local records. The separate C5 review re-issued the forecasts of 24 methods from the checkpoints and the inputs alone, bit-identical to the sealed ones, and recomputed S-b and P2 with its own code ([Review findings](#review-findings)).

**S-c and the replay.** S-c began at 15:11:08, after P2 was public, and took 9 s. `replay.py` then recomputed 300 per-person aggregates with plain loops (largest difference 7.9e-14) and 40 target rows from the decoded walks (difference 0), and passed.

**Supplement.** `supplement.py` was written and run after S-c, when `RESULTS.json` had been read. It uses the scorer of `score.py` unchanged on the same sealed forecasts, changes no number of `RESULTS.json` (largest difference of the recomputed values 0.0) and adds descriptive tables only.

**C6.** The results editions and [NOTICE.md](NOTICE.md) are written. The N_max weights that protocol section 18 lists are not exported yet.

This track downloaded no walk of group P (30 walks, 25,425,332 compressed bytes) or of the physics supplement (33 walks, 34,449,181 compressed bytes); of those people it read only the header bytes of D1.

## Files in this folder

### Stage records

| File | Written by | Stage | Content |
| --- | --- | --- | --- |
| `PROTOCOL.json`, `PROTOCOL.md`, `PROTOCOL-SIMPLE.md` | hand | C1 | The fixed protocol and its two editions |
| `POOL.json` | `allocate.py pool` | C1 | All 138 healthy codes with the reason each is or is not a candidate; archive members of the 80 candidates |
| `ORDER.json` | `allocate.py order` | C1 | The hash orders: primary order, 10 nesting draws, inner folds, variety walks |
| `S0-GATES.json` | `gates.py report` | S0 | Gate results, test reports, one-thread timings, sha256 of every code file; no local paths |
| `DECISIONS.md` | hand | C1b fixes, before D1 | The 18 choices the protocol leaves to the code |
| `QUALIFICATION.json` | `fetch.py probe` | D1 | Per candidate: class, the three walks used, and per walk the byte range, sha256 of the compressed bytes received, verdict and reasons |
| `receipts/D1-requests.jsonl` | `fetch.py probe` | D1 | One line per read: stable address, storage host and path, version, ETag, status, byte range, bytes, sha256; no signed query |
| `receipts/D1-walks.jsonl` | `fetch.py probe` | D1 | First line: the lease note and start time. Then one line per walk: range, bytes inflated and the inflation limit, verdict, reasons, channel counts |
| `ALLOCATION.json` | `assign.py` | C2 | Groups, sizes, rungs and draws, inner folds, P1 pool tails, variety sets, download lists |
| `receipts/D2-RECEIPT.json` | `fetch.py download` | D2 | Per training-pool walk: byte range, compressed and decoded bytes and sha256, CRC-32; the lease note, the request count and the bytes received |
| `receipts/D-training_pool-requests.jsonl` | `fetch.py download` | D2 | One line per ranged read, with the same fields as `receipts/D1-requests.jsonl` |
| `FIT-COMPLETE.json` | `fit.py seal` | C3 | Every checkpoint and tree file by sha256, the failed fits (none), the counts of every training set, the F4 penalties, P1 |
| `receipts/D3-RECEIPT.json`, `receipts/D-evaluation-requests.jsonl` | `fetch.py download` | D3 | The same two records for the evaluation walks |
| `FORECASTS-SEAL.json` | `issue.py seal` | C4 | sha256 of every private forecast file |
| `P2-TREND-PREDICTION.json` | `score.py below` | C5 | Trend predictions for N_max from the rungs below it |
| `RESULTS.json` | `score.py final` | S-c | Every aggregate of the success rule with its interval and label, the curves with the per-person errors by archive code, the predictions against the observed values, the controls, the frozen checkpoints and the secondary arms |
| `RESULTS-SUPPLEMENT.json` | `supplement.py` | after S-c | The predeclared tables that `RESULTS.json` does not hold: the 24-position schedule for every method, the arms scored on the rows with a valid earlier-EMG window, each secondary arm against its family at the same rung, rankings, subgroups, and the counts of every training set |
| `README.md`, `README-SIMPLE.md` | hand | C6 | The results, Technical and Simple edition |
| `NOTICE.md` | hand | C6 | Credit for the recordings, what this track did with them, the sources of the scored checkpoints, terms |

The six receipt files are byte copies of the private logs. `RESULTS.json` and `RESULTS-SUPPLEMENT.json` are byte copies of the files that `score.py final` and `supplement.py` wrote into their private output folders.

### Code

| File | Role | Runtime |
| --- | --- | --- |
| `common.py` | Constants (seeds, prevalence, muscle names, the 36 earlier fit walks), hashing, canonical JSON writing, the private configuration and folder layout, the `Halt` stop signal | standard library |
| `c3dread.py` | Whitelist C3D reader (protocol 4.2) and the walk gates Q6, QP and X (4.3); `read_columns` reads sample columns | standard library; NumPy for `read_columns` |
| `qualify.py` | Header probe of one walk with bounded inflation, the person rule, the qualification receipt and its checker | standard library |
| `fetch.py` | Downloader: `probe` (D1) and `download` (D2, D3). Fresh redirect per read, ranged reads, pacing, one retry, receipts | standard library |
| `allocate.py` | The single allocation, unchanged since C1 and pinned by sha256 in PROTOCOL.json: `pool`, `order`, `assign`, `sizes`, `check` | standard library |
| `assign.py` | Checked front end for `allocate.py assign` (C2) | standard library |
| `walks.py` | Archive members, member and participant indices, checked reads of walk files and of the 36 earlier fit walks | standard library |
| `extract.py` | Input adapter: decoded walk to history-only issue rows, with targets in separate arrays (protocol 6) | A, B |
| `compact.py` | Compact input of M1, M2, S5 and their arms; published person weights; per-person errors | A, B |
| `threepass.py` | M1, the compact three-pass recurrent model, and its arms C4, S1, S2, S3, S4, S6 | A |
| `trees.py` | M3 (boosted trees on the published tree input), S5 (trees on the compact input), tuned trees (G9) | B |
| `linear.py` | M2 (ridge and logistic regression on the compact input), tuned M2 (G9), the F4 refit and the F4 penalty choice | B |
| `frozen.py` | Frozen published checkpoints F1 to F4 issued through the published code, controls C1 to C3, and `NOT_SCORED`, the checkpoints left unscored | A for F1, B otherwise |
| `plan.py` | Every fit of the ladder, derived from `ALLOCATION.json` | standard library |
| `prepare.py` | Extraction after D2 (`--group training`) and after D3 (`--group evaluation`) | B |
| `fit.py` | `run` (fit lanes), `f4` (F4 penalty choice), `p1` (pool-tail prediction), `seal` (writes FIT-COMPLETE.json) | A, B |
| `issue.py` | `run` (forecasts on history-only inputs), `seal` (writes FORECASTS-SEAL.json) | A, B |
| `trend.py` | Trend forms, the P1 and P2 predictions, the trend test | B |
| `score.py` | `below` (stage S-b, writes P2-TREND-PREDICTION.json), `final` (stage S-c, writes RESULTS.json) | B |
| `replay.py` | Independent replay of the primary impulse aggregates (per person, family and rung) and of sample target rows of each plate (S-c) | B |
| `supplement.py` | Supplement to the S-c results, written and run after S-c: further predeclared tables from the same sealed forecasts, with the scorer of `score.py` unchanged; stops on any difference from `RESULTS.json` | B |
| `lanes.py` | CPU slots, one lock file per CPU 16 to 31; fit lanes on 20 to 31. Meant to be shared by every training track on the machine; in this run only this track used it ([Fits](#fits-f4-choice-p1-and-the-c3-seal-done)) | standard library |
| `gates.py` | Stage S0 gates: `part-b`, `part-a`, `report` | B, A, either |

### Tests

| File | Checks | Runtime |
| --- | --- | --- |
| `tests/synthetic.py` | Helpers: a local archive built from the 36 earlier fit walks and patched copies of them, and a local HTTP emulator of the redirect and the storage | none (imported) |
| `tests/test_fetch_probe.py` | Fresh redirect per read; pacing; one retry after a 429 and a halt after two 5xx, on the redirect and on the ranged read, where the retry takes a fresh redirect (the emulator refuses a used signed address); ETag, version, range, size and CRC-32 checks; a local-header mismatch halts D1 without writing QUALIFICATION.json; no signed query in receipts; bounded inflation; Q6, QP and X verdicts; the person rule; tampered receipts caught | B |
| `tests/test_assign.py` | Checked allocation on synthetic verdicts for the real pool (all 80 Q6, mixed, low, cancelled ladder); tampered receipts refused; allocate.py unchanged | standard library |
| `tests/test_trend_score.py` | Trend forms, vectorised bootstrap against a loop, Holm adjustment, labels, the p-value formula, on synthetic numbers | B |
| `tests/smoke_pipeline.py` | Every stage end to end on the 12 earlier fit people with reduced seed counts, with custody checks | B (calls A and B) |

The tests use reduced pacing (0.05 s between requests) and a 0.2 s retry wait against the local emulator. No test touches the network.

## Software runtimes

| Runtime | Python | Packages | Used for |
| --- | --- | --- | --- |
| A | CPython 3.13.15 | torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0 | M1 and every M1-type arm (C4, S1, S2-M1, S3, S4-M1, S6-M1, the G8 M1 sets), F1 |
| B | CPython 3.12.14 | numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0 | M2, M3, S5, G9, F2, F3, F4, extraction, scoring, replay, the supplement, three of the tests |

The standard-library scripts run in either runtime; the tests run them in runtime B. The runtimes for S0 were built with uv from installed CPython 3.13.15 and 3.12.14 interpreters. Equivalent commands:

```
uv venv --python 3.13.15 venv-A
uv pip install --python venv-A/bin/python --index-url https://download.pytorch.org/whl/cpu "torch==2.14.1+cpu"
uv pip install --python venv-A/bin/python numpy==2.5.3 safetensors==0.8.0
uv venv --python 3.12.14 venv-B
uv pip install --python venv-B/bin/python numpy==2.5.5 scikit-learn==1.9.1 joblib==1.6.0 onnxruntime==1.32.0
```

Resolved packages at S0 (`uv pip freeze`):

- A: filelock 4.2.4, fsspec 2026.9.0, jinja2 3.1.6, markupsafe 3.0.3, mpmath 1.3.0, networkx 3.7, numpy 2.5.3, safetensors 0.8.0, setuptools 78.1.0, sympy 1.14.0, torch 2.14.1+cpu, typing-extensions 4.16.0.
- B: cloudpickle 3.1.3, flatbuffers 25.12.19, joblib 1.6.0, narwhals 2.29.0, numpy 2.5.5, onnxruntime 1.32.0, packaging 26.4, protobuf 7.36.2, scikit-learn 1.9.1, scipy 1.18.1, threadpoolctl 3.8.0.

Every numeric step runs on one thread: `common.single_thread_env()` sets `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `BLIS_NUM_THREADS`, `NUMEXPR_NUM_THREADS` and `VECLIB_MAXIMUM_THREADS` to 1 before NumPy, torch or scikit-learn is imported. Protocol section 16 gives the reason: two threads change the fitted weights.

## Configuration

Every script except `allocate.py` and `assign.py` takes `--config CFG`, a private JSON object of local paths. It is never committed. The code reads these keys and ignores any other:

| Key | Read by | Holds |
| --- | --- | --- |
| `central_directory_file` | `walks.py` (training extraction, gates, tests), `tests/test_assign.py` | The archive's central directory: 87,971 bytes, archive bytes 463,071,776 to 463,159,746, sha256 `96a6b5d9…`; checked on every read |
| `fit_cache_dir` | `walks.py` | Decoded C3D files of the 36 walks of the 12 earlier fit people, named as in the archive (for example `SUBJ24 (1).c3d`) |
| `fit_readback_file` | `walks.py` | That cache's readback receipt: a JSON object whose `records` give, per walk, `subject_code`, `author_trial_index`, `archive_member`, `member_crc32` and `decoded_sha256` |
| `features_ref_dir` | `gates.py` | Earlier 12-person issue rows (`FEATURES.npz`, `TARGETS.npz`, `SUPPORT.npz`) for gate G1 |
| `generalization_dir` | `gates.py` | Earlier encoded 12-person cache (`private/prepared/belgium.npz`, sha256 `d81af885…`), the sealed 12-person checkpoints and controls (`private/fit/`) |
| `matched_dir` | `gates.py` | Earlier tree-input rows (`private/FIT.npz`, `dfe83f82…`) and the sealed 12-person tree file (`private/trees/MODELS.joblib`, `2c3f642e…`) |
| `repo_root` | `fit.py`, `issue.py`, `score.py`, `gates.py`, `frozen.py` | A checkout of this repository: the published checkpoints, the F4 grid, and git HEAD for the S-c check |
| `private_dir` | most stages | Walk files, arrays, fits, forecasts ([Private files](#private-files)) |
| `out_dir` | `gates.py`, `score.py`, `replay.py`, `supplement.py`, tests | Gate parts, test reports, score locks, `RESULTS.json`, `REPLAY.json`, `RESULTS-SUPPLEMENT.json` |
| `scratch_dir` | `gates.py`, tests | Temporary files; the tests delete and recreate `test-assign/` and `smoke/` inside it |
| `publish_dir`, `publish_repo` | optional | Folder and repository for the committed stage files. Default: this folder and `repo_root`. Only the synthetic tests set them. |

The files behind `central_directory_file`, `fit_cache_dir`, `fit_readback_file`, `features_ref_dir`, `generalization_dir` and `matched_dir` are earlier work, read in place and never written. Fit walks are checked for size, CRC-32 and readback sha256. The encoded cache, the tree-input rows and the tree file are checked against sha256 pins in `gates.py` and PROTOCOL.json, and the three three-pass reference checkpoints against their pins in PROTOCOL.json. The LSTM reference checkpoints replayed beside them have no pin; their sha256 is recorded in `S0-GATES.json`.

The fit stage and the smoke run also need the environment variable `NS_CPU_SLOTS`, the path of the CPU-slot folder (`lanes.py`). The slots keep the 16-thread limit across tracks only if every training track takes its CPUs through the same folder. The physics-source track did not, so this run kept the limit by another arrangement ([Fits](#fits-f4-choice-p1-and-the-c3-seal-done)).

Example, with placeholder paths:

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

S0 used its own configuration, with `private_dir`, `out_dir` and `scratch_dir` separate from those of the run, because the gates write files about the 12 earlier people into `private_dir`. The supplement used a copy of the run's configuration with an `out_dir` of its own.

## Private files

Nothing below is committed. Recordings, arrays, targets, fits and forecasts stay private under protocol section 17, and local paths stay out of committed files.

| Location | Holds | Physics-source access |
| --- | --- | --- |
| `private_dir/receipts/` | D1 logs (`D1-requests.jsonl`, `D1-walks.jsonl`), the D2 log `D-training_pool-requests.jsonl` and `D2-RECEIPT.json`; copies of all four are committed in `receipts/` | none |
| `private_dir/walks/` | Decoded training-pool walks, `SUBJnnn-t.c3d` (D2) | read only, after D2 |
| `private_dir/arrays/` | `TRAIN-INPUTS.npz`, `TRAIN-TARGETS.npz`, `TRAIN-WALKS.json` | read only, after D2 |
| `private_dir/eval-walks/`, `eval-walks/receipts/` | Decoded evaluation walks (D3), the log `D-evaluation-requests.jsonl` and `D3-RECEIPT.json`; copies of the last two are committed in `receipts/` | never |
| `private_dir/eval-arrays/` | `EVAL-INPUTS.npz`, `EVAL-TARGETS.npz`, `EVAL-WALKS.json` | never |
| `private_dir/fits/` | Per arm: checkpoints (`.safetensors` for runtime A, `.joblib` for runtime B) with a JSON sidecar each; `LOCK-*.json`, `ATTEMPT-*.jsonl`, `RESULT-*.json`, `F4-CHOICE.json`, `P1-*.json`, `READBACK.json` | never |
| `private_dir/forecasts/` | `FORECASTS-PRIMARY-BELOW-NMAX-*`, `FORECASTS-NMAX-*`, `FORECASTS-OTHER-*` (`.npz`, one set per runtime), `ISSUED-*.json` | never |
| `out_dir/` | `S0-PART-A.json`, `S0-PART-B.json`, `tests/*.json`, `SCORE-LOCK-SB.json`, `SCORE-LOCK-SC.json`, `RESULTS.json` (its copy is committed), `REPLAY.json` | never |
| the supplement's `out_dir/` | `RESULTS-SUPPLEMENT.json` (its copy is committed), `SCORE-LOCK-SUP.json` | never |
| the configuration file, `scratch_dir`, the `NS_CPU_SLOTS` folder, the runtimes | local paths and temporary files | none |

Inputs (keys, histories, input masks) and targets (labels, impulses, target masks) are written to separate files. The extractor (`prepare.py`) decodes the evaluation walks and computes the targets; it also writes each walk's counts of rows with a target (`impulse_rows`, `event_rows`) into `EVAL-WALKS.json`. The issuing process opens `EVAL-INPUTS.npz`, and `EVAL-WALKS.json` to check the sha256 of the inputs. It never opens `EVAL-TARGETS.npz`.

After the run `private_dir` holds 1,005,701,390 bytes: forecasts 408,303,877; fits 266,748,297; decoded training-pool walks 165,541,248; decoded evaluation walks with their receipts 92,820,207; training arrays 50,442,403; evaluation arrays 21,471,554; receipts 373,804. The protocol had estimated under 0.7 GB ([DECISIONS.md](DECISIONS.md) item 18).

## Rerunning each stage

Commands run from this folder. Set these first (placeholders):

```
PY_A=/path/to/venv-A/bin/python          # runtime A
PY_B=/path/to/venv-B/bin/python          # runtime B
CFG=/path/to/config.json                 # private configuration
export NS_CPU_SLOTS=/path/to/cpu-slots   # shared CPU-slot folder (fit stage and smoke run)
```

Each stage starts only after the commit, review or lease named for it. `fetch.py`, `prepare.py` and `issue.py` refuse to overwrite their outputs, and `fetch.py probe` refuses to run when `QUALIFICATION.json` exists. `fit.py run` resumes only missing fits and refuses to run when its `LOCK` file no longer matches the job list, code or inputs.

### S0, engineering gates and tests (done)

```
$PY_B -B tests/test_fetch_probe.py --config "$CFG"
$PY_B -B tests/test_assign.py --config "$CFG"
$PY_B -B tests/test_trend_score.py --config "$CFG"
$PY_B -B gates.py part-b --config "$CFG"
$PY_A -B gates.py part-a --config "$CFG"
$PY_B -B tests/smoke_pipeline.py --config "$CFG" --python-a "$PY_A" --python-b "$PY_B"
$PY_B -B gates.py report --config "$CFG"
```

- Order: `part-a` reads files that `part-b` writes into `private_dir`. `report` merges `out_dir/S0-PART-A.json`, `out_dir/S0-PART-B.json` and `out_dir/tests/*.json` into `S0-GATES.json` in this folder, replacing the committed file; the timings change from run to run, so compare the `gates` and `tests` entries, not the bytes.
- Reads: the 36 earlier fit walks and the earlier sealed files (configuration keys above), and the published checkpoints under `repo_root`. Nothing is downloaded.
- Time in the S0 rerun of 27 November: `part-b` 17 s, `part-a` 35 s, `test_fetch_probe` about 40 s, `test_assign` and `test_trend_score` under 1 s each, the smoke run about 6 minutes (68 runtime-A fits in 168 s and 58 runtime-B fits in 146 s, on 3 lanes).
- Gates: `G0_training_replay`, `G1_feature_port`, `G2_end_to_end`, `trees_R0`, `M2_S5_R0`, `G3_past_only`, `one_row_vs_batch_and_fixed_order`, `F4_refit`, `Q6_on_36_fit_walks`, `whitelist_reader`, `tree_input_cache`, `C1_C2_reference`, `reload_equality`, `reference_checkpoints_match_protocol_pins`, `C4_readout_smoke` (protocol section 13 defines G0 to G3, the tree gates and the F4 refit).
- Result: all 15 gates and all 4 tests pass; the smoke run did 126 of 126 fits, and its replay differed from the scorer by at most 5.3e-14 on 36 aggregates and by 0 on 12 row targets.

### D1, header probe (done; runs once)

```
$PY_B -B fetch.py probe --config "$CFG" --lease-note "TEXT"
```

- Needs: C1 pushed, C1b reviewed, the owner's download lease. The lease note is recorded verbatim in `QUALIFICATION.json` and in the first line of `D1-walks.jsonl`.
- Reads, per walk: bytes [o, o + 8,704) of the archive, where o is the local header offset, then 8,192 more bytes at a time up to 65,536 bytes if the parameter section has not been reached. Inflation has a hard output limit at the end of the parameter section, and only the whitelisted header words and parameters of protocol 4.2 are decoded. 4th and 5th walks are probed only for a person whose first three walks include one that is not Q6. The probe refuses a pool that contains a reserved or boundary person.
- Writes: `QUALIFICATION.json` (this folder); `private_dir/receipts/D1-requests.jsonl` and `D1-walks.jsonl`. No header byte is written; only verdicts, counts and sha256 values are kept.
- Stops: a failed range check (status, ETag, version, content range, length), a local header that differs from the central directory, or a second 429 or 5xx answer in one read halts the stage, and then no `QUALIFICATION.json` is written.
- Time: 8 min 51 s for 482 requests; the pacing of at least 1.1 s between request starts sets it.

### C2, allocation (done and reviewed)

```
$PY_B -B assign.py --qualification QUALIFICATION.json --directory CD.bin
```

- `CD.bin` is the central directory (`central_directory_file`). With `--directory`, `assign.py` first recomputes `POOL.json` and `ORDER.json` byte for byte.
- Checks: `allocate.py`, `POOL.json` and `ORDER.json` equal their pins; `QUALIFICATION.json` carries the protocol and pool sha256; each person's probed walks follow the probe rule, the class follows from the verdicts, and the listed walks are the three lowest-numbered qualified ones. It then calls `allocate.py`'s allocation unchanged and checks that the groups partition the 80 candidates, follow the primary order and have the sizes of the rule.
- Writes: `ALLOCATION.json` (this folder); refuses if it exists. `--out PATH` writes elsewhere.
- Difference from `allocate.py assign`: the protocol names `allocate.py assign` as the allocation step. Run alone (`python3 -B allocate.py assign --qualification QUALIFICATION.json --out FILE`), it writes the same content without two keys that `assign.py` adds: `pool_sha256` and `checked_by` (the sha256 of `assign.py`, `qualify.py` and `allocate.py`). Its output therefore has sha256 `93af4a89…` instead of `d1f28610…`; with those two keys removed, the two files are equal.
- Time: under 1 s.

### D2, training-pool walks (done; runs once)

```
$PY_B -B fetch.py download --config "$CFG" --group training_pool --lease-note "TEXT"
```

- Needs: C2 reviewed and pushed. C2 was pushed at 13:04:52 and D2 began at 13:08:41.
- Reads: for each of the 105 walks, one ranged read from its local header to the next local header, after a fresh redirect. Checks status 206, ETag, version, content range and length, the local header against the central directory, and the decoded size and CRC-32. Refuses any person of P, the physics supplement, the earlier validation and test groups and SUBJ099.
- Writes: `private_dir/walks/SUBJnnn-t.c3d`; `private_dir/receipts/D-training_pool-requests.jsonl` and `D2-RECEIPT.json` (per walk: range, compressed and decoded bytes and sha256, CRC-32).
- Time: 5 min 36 s for 210 requests and 98,801,524 bytes, to the time written in the receipt. The pacing of at least 1.1 s between request starts accounts for 3 min 51 s of it. The protocol had estimated about 10 minutes of transfer for all downloads together; D1, D2 and D3 took 17 min 46 s.

### Extraction of the training group (done)

```
$PY_B -B prepare.py --config "$CFG" --allocation ALLOCATION.json --group training
```

- Reads: the 36 earlier fit walks in place and the 105 training-pool walks, each checked against size, CRC-32 and recorded sha256.
- Writes: `private_dir/arrays/TRAIN-INPUTS.npz`, `TRAIN-TARGETS.npz`, `TRAIN-WALKS.json`. Training walks with no supported rows stay listed and are counted; this run had none.
- Time: about 2 s on one CPU, for 141 walks and 42,030 issue rows.

### Fits, F4 choice, P1 and the C3 seal (done)

```
$PY_A -B fit.py run --config "$CFG" --runtime torch --lanes 8
$PY_B -B fit.py run --config "$CFG" --runtime sk --lanes 8
$PY_B -B fit.py f4 --config "$CFG"
$PY_A -B fit.py p1 --config "$CFG" --runtime torch
$PY_B -B fit.py p1 --config "$CFG" --runtime sk
$PY_B -B fit.py seal --config "$CFG"
```

- Needs: extraction done, and a CPU arrangement that keeps all training on the machine within 16 threads (the Lanes item below).
- Jobs: `plan.py` gives 1,742 fits for this allocation: 1,450 in runtime A (250 primary M1; S2-M1 250; S3 250; S1 200; S4-M1 200; C4 100; S6-M1 100; G8 50 + 50) and 292 in runtime B (32 each of M2, M3, S2-M2, S2-M3, S5, G9-M2, G9-M3; 31 each of S4-M2 and S4-M3; 2 of S6-M2; 4 of G8). Seeds: 20261124 + j, j = 0 to 49, for the fixed sets (N = 12, N_max, the two G8 sets); 20261124 + 5d + s for draw d and s = 0 to 4 at intermediate rungs; one deterministic fit per set for M2, M3 and their arms.
- Protocol budget: section 16 gives about 550 tree fits and 650 linear fits. Those figures also count the fits inside G9's inner folds: each of the 32 G9-M3 jobs fits 3 leaf settings on 4 folds, and each of the 32 G9-M2 jobs 4 penalties on 4 folds. The 161 tree jobs (32 each of M3, S2-M3, S5 and G9-M3, 31 of S4-M3, 2 of G8) plus 384 inner-fold fits make 545 tree fits; the 131 linear jobs (32 each of M2, S2-M2 and G9-M2, 31 of S4-M2, 2 of S6-M2, 2 of G8) plus 512 inner-fold fits make 643 linear fits.
- Lanes: each worker holds an exclusive lock on one CPU-slot file and pins itself to that CPU; lanes take the first free slots among CPUs 20 to 31, at most 12 (the default of `--lanes`). This run used 8. When the fits began, the simulator of the physics-source track was using CPUs 16 to 23 with 8 workers pinned outside the slot folder. A small private helper process therefore held the slot files of CPUs 20 to 23, the 8 lanes took CPUs 24 to 31, and the two tracks together stayed at 16 threads. The simulator ended while the runtime-A fits ran, and the 8 lanes were kept to the end. The helper is not part of this folder. Each fit runs on one thread with fixed seeds, so the number of lanes changes the wall time and not the fitted values: the C3 review refitted 22 fits on other CPUs and got the same checkpoint bytes.
- Record chain: `LOCK-*.json` (job list, code and input sha256), `ATTEMPT-*.jsonl`, then per fit the checkpoint and a sidecar that records reload equality on every row of the fit's training table (status `done` only when the reloaded forecasts are identical, otherwise `failed-reload`), `RESULT-*.json` for the run, and at the seal `READBACK.json` of every file. A failed fit keeps its sidecar and is never replaced.
- `f4` chooses the F4 penalties on the training-pool people; `p1` scores the 12-person and intermediate fits on each draw's pool tail (11 people); `seal` reads every file back, fits the trend forms to the P1 curve and writes `FIT-COMPLETE.json` (this folder) for commit C3.
- Result: 1,742 of 1,742 fits done, none failed; every fit reloaded to identical forecasts. The chosen F4 penalties and P1 are in `FIT-COMPLETE.json`.
- Time in the run: runtime A 23 min 38 s for 1,450 fits (mean seconds per fit: S3 27.4, S1 7.8, M1 2.9, C4 1.2); runtime B 7 min 53 s for 292 fits (a G9-M3 job, with its inner-fold fits, 89.8 s on average and at most 151 s). The 8 lanes were busy for about 31.5 min in all, at most 4.2 core-hours. `p1` took 712 s in runtime A, on one CPU beside the runtime-B fits, and 53 s in runtime B; `f4` 2 s; `seal` 1 s. The protocol had estimated 4 to 8 core-hours and 30 to 60 minutes of wall time.
- Time on one thread in S0, for comparison: M1 at 900 updates 2.0 s; S3 (width 96) at 900 updates 8.1 s; C4 0.77 s; a tree pair at 9,586 rows 4.1 s. S1 and S3 get more updates at larger rungs (epoch-matched).

### D3, evaluation walks, and their extraction (done; runs once)

```
$PY_B -B fetch.py download --config "$CFG" --group evaluation --fit-complete FIT-COMPLETE.json --lease-note "TEXT"
$PY_B -B prepare.py --config "$CFG" --allocation ALLOCATION.json --group evaluation
```

- Needs: C3 committed and pushed. The downloader refuses unless `FIT-COMPLETE.json` names the sha256 of this `ALLOCATION.json`; it does not check that the file is committed or pushed. In this run the seal was pushed at 14:03:24 and D3 began at 14:06:17, after the remote main branch was seen to hold it.
- Writes: `private_dir/eval-walks/`, `eval-walks/receipts/` (with `D3-RECEIPT.json`), then `private_dir/eval-arrays/EVAL-INPUTS.npz`, `EVAL-TARGETS.npz`, `EVAL-WALKS.json`.
- Time: 3 min 19 s for 120 requests and 55,832,987 bytes; the pacing accounts for 2 min 12 s of it. The extraction took 1 s.

### Issue and the C4 seal (done)

```
$PY_A -B issue.py run --config "$CFG" --runtime torch
$PY_B -B issue.py run --config "$CFG" --runtime sk
$PY_B -B issue.py seal --config "$CFG"
```

- Reads: `EVAL-INPUTS.npz`, `EVAL-WALKS.json` (to check the sha256 of the inputs) and the fits listed in `FIT-COMPLETE.json`; never `EVAL-TARGETS.npz`.
- Writes, per runtime: `FORECASTS-PRIMARY-BELOW-NMAX-*` (M1, M2, M3 below N_max), `FORECASTS-NMAX-*` (every fit at N_max, with the G8 sets), `FORECASTS-OTHER-*` (secondary arms below N_max, frozen checkpoints, controls), and `ISSUED-*.json`, in `private_dir/forecasts/`. Forecasts go out in one fixed order and fixed batches, as 64-bit floats. `seal` writes `FORECASTS-SEAL.json` (this folder) for commit C4.
- Custody wording: the seal's `custody` entry reads "The issuing processes read evaluation inputs only; targets were never opened before this seal." The second half overstates it, because the extractor had decoded the targets and written them to their own file. The exact statement is that the extractor decoded the targets and the issuing processes never read them. The sealed file is kept as committed, since changing it would break the sha256 that `P2-TREND-PREDICTION.json` and `RESULTS.json` name.
- Time: runtime A 43 min 20 s and runtime B 5 min 2 s, each on one CPU, side by side; `seal` under 1 s.

### S-b and the C5 seal (done)

```
$PY_B -B score.py below --config "$CFG"
```

- Opens only the `PRIMARY-BELOW-NMAX` forecast files and scores M1, M2 and M3 at the rungs below N_max. Fits the trend forms to the rung means and predicts N_max, as a point prediction and in each of the 10,000 bootstrap resamples of people. Writes `out_dir/SCORE-LOCK-SB.json` (sha256 of the files it reads) and `P2-TREND-PREDICTION.json` (this folder), which is committed and pushed as C5.
- Time: under 1 s, at 14:54:32. C5 was committed at 14:55:40 and pushed with C4 at 15:08:44.

### S-c and the replay (done)

```
$PY_B -B score.py final --config "$CFG" --p2-sha "$(git show HEAD:models/walking-force-scale/P2-TREND-PREDICTION.json | sha256sum | cut -d' ' -f1)"
$PY_B -B replay.py --config "$CFG"
```

- `final` refuses unless `P2-TREND-PREDICTION.json` has the given sha256 and the same bytes are committed at HEAD of `repo_root`, and unless P2 names the same scoreable people and forecast seal. It then scores N_max, the frozen checkpoints, the controls and every secondary arm, and writes `out_dir/SCORE-LOCK-SC.json` and `out_dir/RESULTS.json`.
- `replay.py` recomputes the per-person impulse errors of M1, M2 and M3 at every rung with plain loops (300 numbers) and the targets of 20 rows per plate from the decoded evaluation walks (`--rows-per-plate`), and writes `out_dir/REPLAY.json`; it passes when every difference is at most 1e-9. In this run the largest differences were 7.9e-14 and 0.
- Scope of the replay: protocol section 14 asks for an independent replay of every aggregate, and `replay.py` covers the primary impulse aggregates. The other aggregates of S-b and S-c were recomputed by private checks (largest differences 6.7e-15 and 5.3e-15), and a later independent replay compared 3,318 numbers of `RESULTS.json` (largest difference 2.5e-10). Those checks are not code in this folder, and `REPLAY.json` stays private ([Open items](#open-items)).
- Time: S-c 9 s, the replay 2 s. From the start of D3 to the end of S-c the run took 65 min, 43 of them for the runtime-A forecasts; the protocol had estimated minutes of download and under 1 hour of computing.

### Supplement (done)

```
$PY_B -B supplement.py --config "$CFG" --results-sha "$(git show HEAD:models/walking-force-scale/RESULTS.json | sha256sum | cut -d' ' -f1)"
```

- Written and run after S-c, when `RESULTS.json` had been read; it is not a stage of the protocol and changes no number of `RESULTS.json`. It refuses to run unless `RESULTS.json` in this folder has the given sha256 and the same bytes are committed at HEAD of `repo_root`.
- Uses the scorer of `score.py` unchanged: the same sealed forecasts, person weights and bootstrap resamples. Every value it recomputes on all issue times is compared with `RESULTS.json`, and the run stops on any difference; the largest difference was 0.0.
- Writes: `out_dir/RESULTS-SUPPLEMENT.json` and `out_dir/SCORE-LOCK-SUP.json`; refuses to overwrite. Its tables are the 24-position schedule for every method, the arms scored on the rows with a valid earlier-EMG window, each secondary arm against its family at the same rung, the rankings with the fixed methods, subgroup counts and row-wise errors, and the counts of every training set from `FIT-COMPLETE.json`. All of them are descriptive; the labels of the success rule are those of `RESULTS.json`.
- Time: 14 s on one CPU.

### C6, results

Protocol section 18 lists the C6 deliverables. In this folder: the results in a Technical and a Simple edition ([README.md](README.md), [README-SIMPLE.md](README-SIMPLE.md)), `RESULTS.json`, `RESULTS-SUPPLEMENT.json`, [NOTICE.md](NOTICE.md), and the download receipts without signed addresses. Not done: the export of the N_max weights under CC0 1.0 (the M1 checkpoint of seed 20261124 without metadata with its sidecar, the M3 trees as ONNX checked against scikit-learn, the M2 coefficients). `FIT-COMPLETE.json` holds the sha256 of every fit, so a later export can be checked against the seal.

## Checks a reader can repeat

These use the public files only, unless stated.

1. **Fixed files.** `sha256sum PROTOCOL.json allocate.py POOL.json ORDER.json` gives `1768c4df…`, `f40c66f8…`, `c5b5041d…` and `c3c202d4…`. The first is the salt of every hash order; the next two are pinned in PROTOCOL.json.
2. **Code identity.** `S0-GATES.json` lists the sha256 of all 27 code files (22 scripts and 5 test files) as they were when the gates ran; they equal the files in this folder (`supplement.py` was written after S-c and is not in the list):

   ```
   python3 -c "import json,hashlib,pathlib; d=json.load(open('S0-GATES.json'))['code_sha256']; print([k for k,v in d.items() if hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest()!=v] or 'all equal')"
   ```

3. **Pool and orders.** Get the central directory with one ranged read of archive bytes 463,071,776 to 463,159,746 from `https://ndownloader.figshare.com/files/42450060`, for example `curl -L -r 463071776-463159746 -o CD.bin https://ndownloader.figshare.com/files/42450060`, and check that its sha256 is `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b`. Then `python3 -B allocate.py check --directory CD.bin --protocol PROTOCOL.json` prints `{"POOL.json": true, "ORDER.json": true}`.
4. **Allocation from the probe receipt.** `python3 -B assign.py --qualification QUALIFICATION.json --directory CD.bin --out /tmp/ALLOCATION.json` followed by `cmp /tmp/ALLOCATION.json ALLOCATION.json` gives no output: the file is byte-identical (sha256 `d1f28610…`). Without `--directory` it skips step 3's recomputation. This was checked with CPython 3.14.8. `allocate.py assign` alone gives the same content without the keys `pool_sha256` and `checked_by`, so its sha256 differs ([C2](#c2-allocation-done-and-reviewed)).
5. **Probe receipts.** Every line of `receipts/D1-requests.jsonl` has status 206, attempt 0, ETag `"85235c73455d4df8434810d61517efbb"`, version `c9jtqYlgGUVrgEUy1JMXkChG6zGtCpvu` and 8,704 bytes, and carries no signed query. In `QUALIFICATION.json` each walk gives its byte range and the sha256 of the bytes received, so any range can be requested again and compared. Repeating the whole probe takes a configuration whose `private_dir` and `publish_dir` point to new empty folders (482 requests, about 9 minutes); compare the `counts` and `people` entries, since times and the lease note differ.
6. **Tests that need only the public files and the central directory.** `test_trend_score.py` (runtime B) and `test_assign.py` (any Python) run with a configuration holding `central_directory_file`, `out_dir` and `scratch_dir`; they wrote `"passed": true` in 0.3 s and 0.1 s.
7. **Gates and the two other tests.** `gates.py`, `test_fetch_probe.py` and `smoke_pipeline.py` read the 36 earlier fit walks and, for the gates, the earlier issue rows, encoded cache, tree-input rows, sealed checkpoints, comparator file and tree file. Those files are not in this repository. The 36 walks (31,290,834 compressed bytes, members listed by `walks.fit12_members`) can be downloaded from the same archive and checked against the central directory; a readback file with the fields in the configuration table can be written from that download. The encoded cache, the tree-input rows, the tree file and the three-pass reference checkpoints are pinned by sha256 in PROTOCOL.json and `gates.py`; the earlier issue rows, the comparator file and the LSTM reference checkpoints are not.
8. **Order of the seals.** The protocol asks for `FIT-COMPLETE.json` to be public before any evaluation walk is downloaded, `FORECASTS-SEAL.json` to be committed before scoring, and `P2-TREND-PREDICTION.json` to be public before S-c. In the public history the commits follow that order: `4652d69` (fit seal), `c6e6909` (D2 receipts), `be66803` (forecast seal), `46d27d6` (P2), then the commit of `RESULTS.json`. The clock times are local records: a commit's dates are set by the machine that makes it, and the push times are from this machine's record of each push. By those records the fit seal was pushed at 14:03:24 and the first evaluation read is stamped 14:06:21 in `receipts/D-evaluation-requests.jsonl`; P2 was pushed at 15:08:44 and S-c began at 15:11:08. The forecast seal was committed at 14:54:24, 8 s before S-b began, and pushed only at 15:08:44, after S-b; that it preceded S-b cannot be read from a public time.
9. **Chain of pins.** `sha256sum PROTOCOL.json FIT-COMPLETE.json FORECASTS-SEAL.json P2-TREND-PREDICTION.json RESULTS.json` gives `1768c4df…`, `7280ea43…`, `98a0b76f…`, `e8d1c457…` and `e7cf4061…` ([README.md](README.md) lists them in full). Each later file names the earlier ones: `FIT-COMPLETE.json` names the protocol and the allocation; `FORECASTS-SEAL.json` the protocol and the fit seal (`fit_complete_sha256`); `P2-TREND-PREDICTION.json` those and the forecast seal (`forecasts_seal_sha256`); `RESULTS.json` all four (`protocol_sha256`, `fit_complete_sha256`, `forecasts_seal_sha256`, `p2_sha256`); `RESULTS-SUPPLEMENT.json` the same four and `RESULTS.json` (`results_sha256`).
10. **Primary contrasts from the per-person errors.** `RESULTS.json` holds each evaluation person's impulse error for every family and rung. The script below recomputes the three primary contrasts of protocol section 10 (the mean of the fits at N = 47 minus the 12-person fits, paired over the 20 people), the bootstrap intervals and the p-values. Save it as `check.py` outside this folder and run `python3 check.py RESULTS.json` with NumPy installed (checked with NumPy 2.5.5):

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

    It prints:

    ```
    M1 -0.1230 N·s, -5.30% (-6.77% to -3.85%), p = 0.0002, lower error for 20 of 20
    M2 -0.1723 N·s, -4.76% (-5.42% to -4.07%), p = 0.0002, lower error for 20 of 20
    M3 -0.2398 N·s, -11.07% (-14.92% to -7.52%), p = 0.0002, lower error for 18 of 20
    ```

    These equal the `primary_impulse` entries of `RESULTS.json`. With three tests, the Holm adjustment turns each p-value of 0.0002 into 0.0006.
11. **Download receipts.** Every line of `receipts/D-training_pool-requests.jsonl` (105 lines) and `receipts/D-evaluation-requests.jsonl` (60 lines) has status 206, attempt 0, the ETag and version of check 5, and no signed query. `receipts/D2-RECEIPT.json` and `receipts/D3-RECEIPT.json` give, for each walk, the archive member, the byte range, the compressed and decoded sizes with their sha256, and the CRC-32; the walk counts and the sums of the compressed sizes equal the figures under `downloads_by_this_track` in `ALLOCATION.json` (105 walks and 98,793,925 bytes; 60 walks and 55,828,652 bytes), the people are those of its training-pool and evaluation groups, and the offsets, sizes and CRC-32 values can be compared with the central directory of check 3. Any range can be requested again from the stable address and compared with the sha256 in the request log. Everything after the downloads (extraction, fits, forecasts, scores) needs the recordings and the private files and cannot be checked from this folder alone; `FIT-COMPLETE.json` and `FORECASTS-SEAL.json` give the sha256 that a full rerun must reproduce.

## Review findings

The admission review of the protocol named 10 items; items 3, 5, 6, 7 and 9 are handled in this code without changing PROTOCOL.json:

- Item 3: the replicate scheme of the secondary arms is written out in `plan.py`.
- Item 5: gate `Q6_on_36_fit_walks` shows all 36 fit walks Q6 through the same bounded-inflation probe code D1 uses.
- Item 6: `allocate.py` stays byte for byte as pinned; `assign.py` adds the pool sha256, probe-order and lowest-numbered-walk checks, and `tests/test_assign.py` shows tampered receipts refused.
- Item 7: the NeuroTranslate 0.1 paired-plates checkpoints, the other unscored checkpoints and F5 are listed in `frozen.NOT_SCORED`.
- Item 9: `lanes.py` holds one lock file per CPU; the first row of the next table says how the 16-thread limit was kept in the run.

Items 1, 2, 4, 8 and 10 concern the protocol text, its Simple edition or claim limits and are outside the code.

The C1b review found 8 minor problems:

| Finding | State |
| --- | --- |
| The 16-thread limit across tracks holds only if every training track takes its CPUs through the same slot folder; the physics-source track pins its own CPUs, and control steps of this track are not pinned | Not settled through the shared folder. In the run the slot files of CPUs 20 to 23 were held by a private helper while the other track's simulator used CPUs 16 to 23, and the fits ran on 8 lanes, CPUs 24 to 31 ([Fits](#fits-f4-choice-p1-and-the-c3-seal-done)). The control steps (extraction, P1, the F4 choice, the seals, issue, scoring) each ran pinned to one CPU taken through the slot folder |
| A retry after a 429 or 5xx on the ranged read reused the expired signed address | Fixed: the whole read restarts at the stable address; tested |
| In D1, a local-header mismatch gave verdict X instead of halting | Fixed: it halts and no QUALIFICATION.json is written; tested |
| The code requires a known plate state for positive new-load labels; the protocol text states it for negatives only | Kept, as in the published adapter; recorded as DECISIONS.md item 2 |
| Choices the protocol leaves open were only partly recorded | Recorded in DECISIONS.md, items 1 to 18 |
| Evaluation files shared folders with files physics-source may read; D3 does not check that FIT-COMPLETE.json is committed | Folders fixed (`eval-walks/`, `eval-arrays/`). No commit check was added to the code; in the run the seal was pushed at 14:03:24 and D3 began at 14:06:17 |
| Reference checkpoints were not checked against their protocol pins; reload equality covered only 2,048 rows | Fixed: pins checked (all three match); every row checked |
| Publication housekeeping: rewrite and Simple edition of this file, a neutral configuration key name, joining the protocol branch, float64 forecast storage | Rewrite and Simple edition done; this version, updated after the run, awaits its separate reader ([Open items](#open-items)); key renamed; branch based on the main branch that holds the published protocol; storage recorded as DECISIONS.md item 18 |

The fixes in this table were committed after the C1b review and before D1, and were first reviewed at C2.

The C2 review, on 27 November 2026, checked the D1 receipts against the pinned central directory with its own parser, rebuilt `QUALIFICATION.json` and `ALLOCATION.json` byte for byte, recomputed the allocation from the protocol rules with its own code, checked the five code fixes, and reran `test_fetch_probe.py` (it passes on the fixed code and halts at the GET-retry case on the C1b code) and `test_assign.py`. It found no blocker or major problem in the D1 records, the allocation or the code fixes. It found one blocker and two major problems in the texts, and five minor points:

| Finding | State |
| --- | --- |
| Blocker: DECISIONS.md said all 18 choices were reviewed with the code at C1b; items 13 to 17 are fixes made after that review and were first reviewed at C2 | Corrected in DECISIONS.md, which also records that its first wording made the same claim |
| Major: the Simple edition used terms it never explained (hash order and salt, bootstrap, p-value, trend forms, G8 and the variety sets, inner folds and the tuned arm, penalty, the random-readout control) | Explained in its word list |
| Major: this file and DECISIONS.md used protocol names (Q6, QP, X, the six-name rule, the stage, arm and gate names, TAG) with no gloss or pointer where they first appear | [Terms](#terms) added here; DECISIONS.md word list extended |
| D1 ran on review fixes that had not yet been reviewed; the C2 review found them correct | Stated in both editions and in DECISIONS.md: the fixes D1 uses change only the retry and halt paths, and neither was taken in D1 |
| `allocate.py assign` does not reproduce `ALLOCATION.json` byte for byte, because `assign.py` adds two keys | Explained under [C2](#c2-allocation-done-and-reviewed) |
| The 292 runtime-B fits were not reconciled with the protocol's figures of about 550 tree and 650 linear fits | Reconciled under [Fits](#fits-f4-choice-p1-and-the-c3-seal-done): the protocol figures include the G9 inner-fold fits |
| Precision: the CPU slots were described as shared by every track; all reference checkpoints were described as pinned; DECISIONS.md item 17 said `arrays/` holds the training pool only; item 18 quoted the Q = 80 disk figure | Corrected in the texts. The docstring of `lanes.py` still describes the shared design; it is left unchanged because its sha256 is recorded in `S0-GATES.json` |
| Disclosed open items (lane plan, D3 commit check, F5, the lease-note date); the D1 receipts were committed at C2 rather than C6, which only adds files and exposes no signed query | The lane plan and the commit check were handled in the run as the first table says; F5 was not issued; the lease-note date stays as recorded ([Open items](#open-items)) |

The C3 review, on 27 November 2026 before C3 was pushed, checked the D2 receipts against the pinned central directory with its own parser, compared the job list with the protocol rules, refitted 22 of the 1,742 fits with the committed code (every checkpoint byte-identical to the sealed one), reran the F4 choice (byte-identical), recomputed P1, and compared every sha256 in `FIT-COMPLETE.json` with the private files. It found no blocker or major problem, and three minor points:

| Finding | State |
| --- | --- |
| Both run-code guides still described D2, the extraction, the fits and C3 as not run | Brought up to date in this version |
| The guide's precondition for `fit.py run`, "the lane plan settled", was not met as written; a private arrangement kept the total at 16 threads. The fitted values are unaffected | Described under [Fits](#fits-f4-choice-p1-and-the-c3-seal-done) |
| D3 has no code check that `FIT-COMPLETE.json` is committed or pushed, so the public time of the seal depends on the push | Code unchanged; the seal was pushed at 14:03:24, before D3 began at 14:06:17 |

The C5 review, on 27 November 2026 before C4 and C5 were pushed, checked the D3 receipts the same way, compared the forecast seal with the six forecast files, re-issued the forecasts of 24 methods from the checkpoints and the inputs alone (bit-identical to the sealed ones on all 17,888 rows), confirmed that S-b had read only the two files of the primary fits below N_max, and recomputed the S-b errors and every P2 prediction with its own code. It found no blocker or major problem, and three minor points:

| Finding | State |
| --- | --- |
| The forecast seal gets its public time only at its push, which came after S-b; check 8 of this file said the order could be read from public commit times | Check 8 corrected; stated in the results editions |
| The custody sentence in `FORECASTS-SEAL.json` and in the message of its commit says more than is true: the extractor decoded the targets, and the issuing process opens `EVAL-WALKS.json`, which holds per-walk counts of rows with a target | The sealed file is unchanged; the exact custody is stated under [Issue](#issue-and-the-c4-seal-done), under [Private files](#private-files) and in the results editions |
| Both run-code guides were still out of date | Brought up to date in this version |

## Open items

1. **N_max weights.** Protocol section 18 lists, for C6, the M1 checkpoint of seed 20261124 at N = 47 without metadata with its sidecar, the M3 trees at N = 47 as ONNX checked against scikit-learn, and the M2 coefficients, under CC0 1.0 with the notice. They are not exported yet. The fits are private and their sha256 values are in `FIT-COMPLETE.json`.
2. **Separate reader.** The results editions, `NOTICE.md`, this file, its Simple edition and DECISIONS.md, as updated after the run, need a separate reader.
3. **Replay in this folder.** `replay.py` covers the primary impulse aggregates and 40 target rows, where protocol section 14 asks for every aggregate. The other aggregates were recomputed by private checks. `REPLAY.json` and the three score locks stay private.
4. **Forecast-seal wording and public time.** The `custody` sentence of `FORECASTS-SEAL.json` overstates, and the seal became public after S-b ([Issue](#issue-and-the-c4-seal-done), check 8). Neither can be changed after the fact; both are stated in the results editions.
5. **CPU slots.** The 16-thread limit was kept in this run by a private arrangement ([Fits](#fits-f4-choice-p1-and-the-c3-seal-done)). A later run needs every training track to take its CPUs through the `NS_CPU_SLOTS` folder, or the tracks to run one after the other. The docstring of `lanes.py` still describes the shared design and is unchanged because the file's sha256 is recorded in `S0-GATES.json` and `FIT-COMPLETE.json`.
6. **D3 commit check.** The downloader has no check that `FIT-COMPLETE.json` is committed or pushed. D3 runs once and has run, with the seal pushed first.
7. **Lease note date.** The note recorded in D1 says "C1b reviewed 28 Nov". The C1b review was finished, and D1 run, on 27 November 2026; the receipts carry the UTC times.
8. **F5.** The optional Research Edition was not admitted and was not issued, so no result depends on it.

## Choices left to the code

[DECISIONS.md](DECISIONS.md) lists the 18 details the protocol leaves open (indices, labels, training tables, the S4 size, scaling in the force-only tree arm, the earlier-EMG rows, the Brier floor, the standard deviation of the detectable effect, the sensitivity seed, what S-b opens, extra walks, pacing, the retry, local-header mismatches, reference pins, reload equality, custody folders, forecast storage), with the code that applies each. They were fixed in the code before any byte of the pool was read, and none was chosen by looking at a result. Items 1 to 12 and 18 were in the code reviewed at C1b; items 13 to 17 are the fixes for that review, reviewed at C2. No choice changed during the run.
