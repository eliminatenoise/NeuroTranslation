# Walking-force quantity ladder: run code

Technical edition · [Simple edition](README-CODE-SIMPLE.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Machine-readable protocol](PROTOCOL.json) · [Choices left to the code](DECISIONS.md)

This folder holds the code that carries out protocol version 1 of the walking-force quantity ladder, from the header probe (stage D1) to the scored results (stage S-c), and the records of the stages run so far. For every stage this file gives the exact command, the software runtime, what the stage reads and writes, how long it took or is expected to take, and what stays private. It also lists the checks a reader can repeat from the public files. Where this file and [PROTOCOL.json](PROTOCOL.json) disagree, PROTOCOL.json governs.

## Terms

The protocol's names, with the protocol section that defines each:

- **Stages** (14): S0 engineering gates on the 12 earlier fit people; C1 protocol commit; C1b separate review of the run code; D1 header probe; C2 qualification receipt and allocation, with their review; D2 training-pool download; C3 fit seal; D3 evaluation-group download; C4 forecast seal; S-b scoring of the rungs below N_max; C5 seal of the P2 prediction; S-c final scoring and independent replay; C6 results. C stages end in a commit, D stages download.
- **Q6, QP, X** (4.3): walk and person classes of the header probe. Q6 passes every walk gate, including the six-name rule: `Voltage.LBF`, `Voltage.LERS`, `Voltage.LGAS`, `Voltage.LRF`, `Voltage.LST` and `Voltage.RERS` each present once, in volts. QP passes every walk gate except the six-name rule and has at least four `Voltage.*` channels in volts. X fails another walk gate. A person is Q6 with at least three Q6 walks, QP with at least three walks that are Q6 or QP, and X otherwise.
- **Hash order, TAG** (5.1): codes sorted by the sha256 of TAG + a label + the code. TAG = `10.6084/m9.figshare.24192480.v1|walking-scale|` + the sha256 of PROTOCOL.json, so the sha256 of PROTOCOL.json salts every order.
- **Q, E, P, T** (5.2): Q is the number of Q6 people. Along the primary hash order of Q6 people: evaluation group E, physics-source group P, training pool T. QP people form the physics supplement; X people are unusable.
- **Rung, draw, N_max, inner folds** (5.3): a rung is a training-set size N = 12 + a, with a people added to the 12 earlier fit people. Rung a of draw d (d = 0 to 9) adds the first a people of draw order d, so the rungs of one draw are nested. N_max = 12 + T. Inner folds split a fit's training people into 4 by hash rank; only G9 uses them.
- **M1, M2, M3** (7): the compact three-pass recurrent model; ridge and logistic regression on the compact input; boosted trees on the published tree input.
- **Controls C1 to C4 and frozen checkpoints F1 to F5** (8): C1 persistence, C2 unconditional, C3 linear trend, C4 random recurrent readout (M1 with only its output layer trained); F1 to F5 are published checkpoints scored as published (F5 only if admitted), except that the F4 force baselines get their penalty chosen on the training pool. The control names C1 to C4 overlap with the stage names C1 to C6; lists of fits and forecasts mean the controls.
- **Secondary arms** (9): S1 epoch-matched M1; S2 force only; S3 M1 at width 96; S4 fixed example budget; S5 trees on the compact input; S6 EMG window ending 500 ms before the issue; G8 variety, at N_max: the 12 earlier fit people plus one walk from each of the T pool people, against the 12 plus three walks from each of the first floor(T / 3) people of draw order 0 (the two variety sets); G9 tuned, M3 leaves and M2 penalty chosen by the inner folds.
- **P1, P2, trend forms** (11): sealed predictions of the N_max result, P1 from each draw's pool tail before D3 and P2 from the rungs below N_max before S-c. Trend forms, for the mean absolute impulse error MAE(N) at N training people: L + a / sqrt(N) (primary) and c + b log2 N, against carry-forward of the second-largest rung.
- **Gates** (13): G0 training replay, G1 feature port, G2 end to end, G3 past only, the tree gates and the F4 refit.

## State on 27 November 2026

| Stage | State | Record in this folder |
| --- | --- | --- |
| C1, protocol | Published at NeuroTranslation commit `3f2bae7` | `PROTOCOL.md`, `PROTOCOL-SIMPLE.md`, `PROTOCOL.json`, `allocate.py`, `POOL.json`, `ORDER.json` |
| S0, engineering gates | Done, on the 12 earlier fit people only: 15 of 15 gates and 4 of 4 tests pass | `S0-GATES.json` |
| C1b, run code | Reviewed against the protocol: no blocker, no major, 8 minor findings. The fixes for these findings were committed after that review and before D1, and reviewed at C2 ([Review findings](#review-findings)) | the `.py` files, `tests/` |
| D1, header probe | Run on 27 November 2026 from 11:55:07 to 12:03:58 UTC, on the C1b code plus the review fixes | `QUALIFICATION.json`, `receipts/D1-requests.jsonl`, `receipts/D1-walks.jsonl` |
| C2, allocation | Computed, and reviewed separately on 27 November 2026: no blocker or major finding in the D1 records, the allocation or the code fixes; its findings on the texts are corrected in this version | `ALLOCATION.json` |
| D2 to C6 | Not run | none yet |

**D1.** 241 walks were probed: the three lowest-numbered walks of each of the 80 candidates (240) and the 4th walk of SUBJ060, whose 2nd walk failed the six-name rule. Each walk took one ranged read of 8,704 bytes from its local header: 482 requests in all (one redirect and one ranged read per walk) and 2,097,664 compressed bytes. Every ranged read answered 206 with the pinned ETag and storage version; no read was retried and none needed a continuation read. Inflation stopped at the end of the C3D parameter section on all 241 walks, so no sample byte was produced. Walk verdicts: 205 Q6, 30 QP, 6 X. People: 65 Q6, 11 QP, 4 X. A Q6 person uses their three lowest-numbered Q6 walks, so SUBJ060 uses walks 1, 3 and 4. D1 ran on the code reviewed at C1b plus the fixes for that review, which were committed 20 s before D1 started and first reviewed at C2. The fixes that D1 uses ([DECISIONS.md](DECISIONS.md) items 13 and 14) change only the retry and halt paths, and neither path was taken: every read was a first attempt and no local header differed from the central directory.

**C2.** With Q = 65 qualified people, the size rule gives an evaluation group E of 20 people, a physics-source group P of 10 and a training pool T of 35. The rungs are N = 12, 18, 24, 36 and 47 people (6, 12, 24 and 35 people added to the 12 earlier fit people), with 10 nested draws at each intermediate rung. Because T is at least 32, the pool-tail prediction P1 applies, with 11 people per draw. The 11 QP people form the physics supplement and the 4 X people are unusable, each with its reasons. SUBJ099 stays out of every role, unopened. The group lists are in `ALLOCATION.json`. The separate C2 review rebuilt `QUALIFICATION.json` byte for byte from the two receipt files and `ALLOCATION.json` byte for byte through `assign.py`, and recomputed the groups, rungs, draws, folds, pool tails and variety sets from the protocol rules with its own code; it found no blocker or major problem in either file.

**Downloads still to come** (from `ALLOCATION.json`): D2, the training pool, 35 people, 105 walks, 98,793,925 compressed bytes; D3, the evaluation group, 20 people, 60 walks, 55,828,652 compressed bytes. This track never downloads group P (30 walks, 25,425,332 bytes) or the supplement (33 walks, 34,449,181 bytes).

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
| `FIT-COMPLETE.json` | `fit.py seal` | C3 | Every checkpoint and tree file by sha256, failed fits, F4 penalties, P1 (not yet written) |
| `FORECASTS-SEAL.json` | `issue.py seal` | C4 | sha256 of every private forecast file (not yet written) |
| `P2-TREND-PREDICTION.json` | `score.py below` | C5 | Trend predictions for N_max from the rungs below it (not yet written) |

The two receipt files are byte copies of the private D1 logs. `RESULTS.json` (written by `score.py final` into the private output folder) is published with the results editions at C6.

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
| `replay.py` | Independent replay of every primary aggregate and of sample rows of each plate (S-c) | B |
| `lanes.py` | CPU slots, one lock file per CPU 16 to 31; fit lanes on 20 to 31. Meant to be shared by every training track on the machine; so far only this track's fit lanes use it ([Open items](#open-items)) | standard library |
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
| B | CPython 3.12.14 | numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0 | M2, M3, S5, G9, F2, F3, F4, extraction, scoring, replay, three of the tests |

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
| `out_dir` | `gates.py`, `score.py`, `replay.py`, tests | Gate parts, test reports, score locks, `RESULTS.json`, `REPLAY.json` |
| `scratch_dir` | `gates.py`, tests | Temporary files; the tests delete and recreate `test-assign/` and `smoke/` inside it |
| `publish_dir`, `publish_repo` | optional | Folder and repository for the committed stage files. Default: this folder and `repo_root`. Only the synthetic tests set them. |

The files behind `central_directory_file`, `fit_cache_dir`, `fit_readback_file`, `features_ref_dir`, `generalization_dir` and `matched_dir` are earlier work, read in place and never written. Fit walks are checked for size, CRC-32 and readback sha256. The encoded cache, the tree-input rows and the tree file are checked against sha256 pins in `gates.py` and PROTOCOL.json, and the three three-pass reference checkpoints against their pins in PROTOCOL.json. The LSTM reference checkpoints replayed beside them have no pin; their sha256 is recorded in `S0-GATES.json`.

The fit stage and the smoke run also need the environment variable `NS_CPU_SLOTS`, the path of the CPU-slot folder (`lanes.py`). The slots keep the 16-thread limit across tracks only if every training track takes its CPUs through the same folder; the physics-source track does not yet ([Open items](#open-items)).

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

S0 used its own configuration, with `private_dir`, `out_dir` and `scratch_dir` separate from those of the run, because the gates write files about the 12 earlier people into `private_dir`.

## Private files

Nothing below is committed. Recordings, arrays, targets, fits and forecasts stay private under protocol section 17, and local paths stay out of committed files.

| Location | Holds | Physics-source access |
| --- | --- | --- |
| `private_dir/receipts/` | D1 logs (`D1-requests.jsonl`, `D1-walks.jsonl`; their copies are committed in `receipts/`), D2 logs and `D2-RECEIPT.json` | none |
| `private_dir/walks/` | Decoded training-pool walks, `SUBJnnn-t.c3d` (D2) | read only, after D2 |
| `private_dir/arrays/` | `TRAIN-INPUTS.npz`, `TRAIN-TARGETS.npz`, `TRAIN-WALKS.json` | read only, after D2 |
| `private_dir/eval-walks/`, `eval-walks/receipts/` | Decoded evaluation walks (D3), their logs and `D3-RECEIPT.json` | never |
| `private_dir/eval-arrays/` | `EVAL-INPUTS.npz`, `EVAL-TARGETS.npz`, `EVAL-WALKS.json` | never |
| `private_dir/fits/` | Per arm: checkpoints (`.safetensors` for runtime A, `.joblib` for runtime B) with a JSON sidecar each; `LOCK-*.json`, `ATTEMPT-*.jsonl`, `RESULT-*.json`, `F4-CHOICE.json`, `P1-*.json`, `READBACK.json` | never |
| `private_dir/forecasts/` | `FORECASTS-PRIMARY-BELOW-NMAX-*`, `FORECASTS-NMAX-*`, `FORECASTS-OTHER-*` (`.npz`, one set per runtime), `ISSUED-*.json` | never |
| `out_dir/` | `S0-PART-A.json`, `S0-PART-B.json`, `tests/*.json`, `SCORE-LOCK-SB.json`, `SCORE-LOCK-SC.json`, `RESULTS.json`, `REPLAY.json` | never |
| the configuration file, `scratch_dir`, the `NS_CPU_SLOTS` folder, the runtimes | local paths and temporary files | none |

Inputs (keys, histories, input masks) and targets (labels, impulses, target masks) are written to separate files. The issuing process opens only `EVAL-INPUTS.npz`.

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

### D2, training-pool walks (not run)

```
$PY_B -B fetch.py download --config "$CFG" --group training_pool --lease-note "TEXT"
```

- Needs: C2 reviewed and pushed.
- Reads: for each of the 105 walks, one ranged read from its local header to the next local header, after a fresh redirect. Checks status 206, ETag, version, content range and length, the local header against the central directory, and the decoded size and CRC-32. Refuses any person of P, the supplement, the earlier validation and test groups and SUBJ099.
- Writes: `private_dir/walks/SUBJnnn-t.c3d`; `private_dir/receipts/D-training_pool-requests.jsonl` and `D2-RECEIPT.json` (per walk: range, compressed and decoded bytes and sha256, CRC-32).
- Time: at least 3 min 51 s of pacing (210 requests at 1.1 s) plus the transfer of 98,793,925 bytes. The protocol estimates about 10 minutes of transfer for all downloads together.

### Extraction of the training group (not run)

```
$PY_B -B prepare.py --config "$CFG" --allocation ALLOCATION.json --group training
```

- Reads: the 36 earlier fit walks in place and the 105 training-pool walks, each checked against size, CRC-32 and recorded sha256.
- Writes: `private_dir/arrays/TRAIN-INPUTS.npz`, `TRAIN-TARGETS.npz`, `TRAIN-WALKS.json`. Training walks with no supported rows stay listed and are counted.

### Fits, F4 choice, P1 and the C3 seal (not run)

```
$PY_A -B fit.py run --config "$CFG" --runtime torch --lanes 12
$PY_B -B fit.py run --config "$CFG" --runtime sk --lanes 12
$PY_B -B fit.py f4 --config "$CFG"
$PY_A -B fit.py p1 --config "$CFG" --runtime torch
$PY_B -B fit.py p1 --config "$CFG" --runtime sk
$PY_B -B fit.py seal --config "$CFG"
```

- Needs: extraction done, and the lane plan settled ([Open items](#open-items)).
- Jobs: `plan.py` gives 1,742 fits for this allocation: 1,450 in runtime A (250 primary M1; S2-M1 250; S3 250; S1 200; S4-M1 200; C4 100; S6-M1 100; G8 50 + 50) and 292 in runtime B (32 each of M2, M3, S2-M2, S2-M3, S5, G9-M2, G9-M3; 31 each of S4-M2 and S4-M3; 2 of S6-M2; 4 of G8). Seeds: 20261124 + j, j = 0 to 49, for the fixed sets (N = 12, N_max, the two G8 sets); 20261124 + 5d + s for draw d and s = 0 to 4 at intermediate rungs; one deterministic fit per set for M2, M3 and their arms.
- Protocol budget: section 16 gives about 550 tree fits and 650 linear fits. Those figures also count the fits inside G9's inner folds: each of the 32 G9-M3 jobs fits 3 leaf settings on 4 folds, and each of the 32 G9-M2 jobs 4 penalties on 4 folds. The 161 tree jobs (32 each of M3, S2-M3, S5 and G9-M3, 31 of S4-M3, 2 of G8) plus 384 inner-fold fits make 545 tree fits; the 131 linear jobs (32 each of M2, S2-M2 and G9-M2, 31 of S4-M2, 2 of S6-M2, 2 of G8) plus 512 inner-fold fits make 643 linear fits.
- Lanes: each worker holds an exclusive lock on one CPU-slot file and pins itself to that CPU; lanes use CPUs 20 to 31, at most 12.
- Record chain: `LOCK-*.json` (job list, code and input sha256), `ATTEMPT-*.jsonl`, then per fit the checkpoint and a sidecar that records reload equality on every row of the fit's training table (status `done` only when the reloaded forecasts are identical, otherwise `failed-reload`), `RESULT-*.json` for the run, and at the seal `READBACK.json` of every file. A failed fit keeps its sidecar and is never replaced.
- `f4` chooses the F4 penalties on the training-pool people; `p1` scores the 12-person and intermediate fits on each draw's pool tail (11 people); `seal` reads every file back, fits the trend forms to the P1 curve and writes `FIT-COMPLETE.json` (this folder) for commit C3.
- Time, measured on one thread in S0: M1 at 900 updates 2.0 s; S3 (width 96) at 900 updates 8.1 s; C4 0.77 s; a tree pair at 9,586 rows 4.1 s. S1 and S3 get more updates at larger rungs (epoch-matched). The protocol estimates 4 to 8 core-hours and 30 to 60 minutes of wall time.

### D3, evaluation walks, and their extraction (not run)

```
$PY_B -B fetch.py download --config "$CFG" --group evaluation --fit-complete FIT-COMPLETE.json --lease-note "TEXT"
$PY_B -B prepare.py --config "$CFG" --allocation ALLOCATION.json --group evaluation
```

- Needs: C3 committed and pushed. The downloader refuses unless `FIT-COMPLETE.json` names the sha256 of this `ALLOCATION.json`; it does not check that the file is committed ([Open items](#open-items)).
- Writes: `private_dir/eval-walks/`, `eval-walks/receipts/` (with `D3-RECEIPT.json`), then `private_dir/eval-arrays/EVAL-INPUTS.npz`, `EVAL-TARGETS.npz`, `EVAL-WALKS.json`.
- Time: at least 2 min 12 s of pacing (120 requests) plus the transfer of 55,828,652 bytes.

### Issue and the C4 seal (not run)

```
$PY_A -B issue.py run --config "$CFG" --runtime torch
$PY_B -B issue.py run --config "$CFG" --runtime sk
$PY_B -B issue.py seal --config "$CFG"
```

- Reads: `EVAL-INPUTS.npz` only, and the fits listed in `FIT-COMPLETE.json`; never the targets.
- Writes, per runtime: `FORECASTS-PRIMARY-BELOW-NMAX-*` (M1, M2, M3 below N_max), `FORECASTS-NMAX-*` (every fit at N_max, with the G8 sets), `FORECASTS-OTHER-*` (secondary arms below N_max, frozen checkpoints, controls), and `ISSUED-*.json`, in `private_dir/forecasts/`. Forecasts go out in one fixed order and fixed batches, as 64-bit floats. `seal` writes `FORECASTS-SEAL.json` (this folder) for commit C4.

### S-b and the C5 seal (not run)

```
$PY_B -B score.py below --config "$CFG"
```

- Opens only the `PRIMARY-BELOW-NMAX` forecast files and scores M1, M2 and M3 at the rungs below N_max. Fits the trend forms to the rung means and predicts N_max, as a point prediction and in each of the 10,000 bootstrap resamples of people. Writes `out_dir/SCORE-LOCK-SB.json` (sha256 of the files it reads) and `P2-TREND-PREDICTION.json` (this folder), which is committed and pushed as C5.

### S-c and the replay (not run)

```
$PY_B -B score.py final --config "$CFG" --p2-sha "$(git show HEAD:models/walking-force-scale/P2-TREND-PREDICTION.json | sha256sum | cut -d' ' -f1)"
$PY_B -B replay.py --config "$CFG"
```

- `final` refuses unless `P2-TREND-PREDICTION.json` has the given sha256 and the same bytes are committed at HEAD of `repo_root`, and unless P2 names the same scoreable people and forecast seal. It then scores N_max, the frozen checkpoints, the controls and every secondary arm, and writes `out_dir/SCORE-LOCK-SC.json` and `out_dir/RESULTS.json`.
- `replay.py` recomputes every primary aggregate with plain loops and 20 rows per plate from the decoded evaluation walks (`--rows-per-plate`), and writes `out_dir/REPLAY.json`; it passes when every difference is at most 1e-9.
- Time for D3 to S-c, protocol estimate: minutes of download and under 1 hour of computing.

### C6, results

Results in a Technical and a Simple edition, `RESULTS.json`, the published N_max checkpoints under CC0 with a NOTICE, and the download receipts without signed addresses (protocol section 18). Not written yet.

## Checks a reader can repeat

These use the public files only, unless stated.

1. **Fixed files.** `sha256sum PROTOCOL.json allocate.py POOL.json ORDER.json` gives `1768c4df…`, `f40c66f8…`, `c5b5041d…` and `c3c202d4…`. The first is the salt of every hash order; the next two are pinned in PROTOCOL.json.
2. **Code identity.** `S0-GATES.json` lists the sha256 of all 27 code files (22 scripts and 5 test files) as they were when the gates ran; they equal the files in this folder:

   ```
   python3 -c "import json,hashlib,pathlib; d=json.load(open('S0-GATES.json'))['code_sha256']; print([k for k,v in d.items() if hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest()!=v] or 'all equal')"
   ```

3. **Pool and orders.** Get the central directory with one ranged read of archive bytes 463,071,776 to 463,159,746 from `https://ndownloader.figshare.com/files/42450060`, for example `curl -L -r 463071776-463159746 -o CD.bin https://ndownloader.figshare.com/files/42450060`, and check that its sha256 is `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b`. Then `python3 -B allocate.py check --directory CD.bin --protocol PROTOCOL.json` prints `{"POOL.json": true, "ORDER.json": true}`.
4. **Allocation from the probe receipt.** `python3 -B assign.py --qualification QUALIFICATION.json --directory CD.bin --out /tmp/ALLOCATION.json` followed by `cmp /tmp/ALLOCATION.json ALLOCATION.json` gives no output: the file is byte-identical (sha256 `d1f28610…`). Without `--directory` it skips step 3's recomputation. This was checked with CPython 3.14.8. `allocate.py assign` alone gives the same content without the keys `pool_sha256` and `checked_by`, so its sha256 differs ([C2](#c2-allocation-done-and-reviewed)).
5. **Probe receipts.** Every line of `receipts/D1-requests.jsonl` has status 206, attempt 0, ETag `"85235c73455d4df8434810d61517efbb"`, version `c9jtqYlgGUVrgEUy1JMXkChG6zGtCpvu` and 8,704 bytes, and carries no signed query. In `QUALIFICATION.json` each walk gives its byte range and the sha256 of the bytes received, so any range can be requested again and compared. Repeating the whole probe takes a configuration whose `private_dir` and `publish_dir` point to new empty folders (482 requests, about 9 minutes); compare the `counts` and `people` entries, since times and the lease note differ.
6. **Tests that need only the public files and the central directory.** `test_trend_score.py` (runtime B) and `test_assign.py` (any Python) run with a configuration holding `central_directory_file`, `out_dir` and `scratch_dir`; they wrote `"passed": true` in 0.3 s and 0.1 s.
7. **Gates and the two other tests.** `gates.py`, `test_fetch_probe.py` and `smoke_pipeline.py` read the 36 earlier fit walks and, for the gates, the earlier issue rows, encoded cache, tree-input rows, sealed checkpoints, comparator file and tree file. Those files are not in this repository. The 36 walks (31,290,834 compressed bytes, members listed by `walks.fit12_members`) can be downloaded from the same archive and checked against the central directory; a readback file with the fields in the configuration table can be written from that download. The encoded cache, the tree-input rows, the tree file and the three-pass reference checkpoints are pinned by sha256 in PROTOCOL.json and `gates.py`; the earlier issue rows, the comparator file and the LSTM reference checkpoints are not.
8. **Later seals.** `FIT-COMPLETE.json` must be committed before any evaluation walk is downloaded, `FORECASTS-SEAL.json` before scoring, and `P2-TREND-PREDICTION.json` before S-c; the commit times on the public repository show the order. `RESULTS.json` will carry the per-person errors by archive code, and `REPLAY.json` the independent recomputation.

## Review findings

The admission review of the protocol named 10 items; items 3, 5, 6, 7 and 9 are handled in this code without changing PROTOCOL.json:

- Item 3: the replicate scheme of the secondary arms is written out in `plan.py`.
- Item 5: gate `Q6_on_36_fit_walks` shows all 36 fit walks Q6 through the same bounded-inflation probe code D1 uses.
- Item 6: `allocate.py` stays byte for byte as pinned; `assign.py` adds the pool sha256, probe-order and lowest-numbered-walk checks, and `tests/test_assign.py` shows tampered receipts refused.
- Item 7: the NeuroTranslate 0.1 paired-plates checkpoints, the other unscored checkpoints and F5 are listed in `frozen.NOT_SCORED`.
- Item 9: `lanes.py` holds one lock file per CPU; see the lane plan below.

Items 1, 2, 4, 8 and 10 concern the protocol text, its Simple edition or claim limits and are outside the code.

The C1b review found 8 minor problems:

| Finding | State |
| --- | --- |
| The 16-thread limit across tracks holds only if every training track takes its CPUs through the same slot folder; the physics-source track pins its own CPUs, and control steps of this track are not pinned | Open; must be settled before `fit.py run` |
| A retry after a 429 or 5xx on the ranged read reused the expired signed address | Fixed: the whole read restarts at the stable address; tested |
| In D1, a local-header mismatch gave verdict X instead of halting | Fixed: it halts and no QUALIFICATION.json is written; tested |
| The code requires a known plate state for positive new-load labels; the protocol text states it for negatives only | Kept, as in the published adapter; recorded as DECISIONS.md item 2 |
| Choices the protocol leaves open were only partly recorded | Recorded in DECISIONS.md, items 1 to 18 |
| Evaluation files shared folders with files physics-source may read; D3 does not check that FIT-COMPLETE.json is committed | Folders fixed (`eval-walks/`, `eval-arrays/`); the commit check is open |
| Reference checkpoints were not checked against their protocol pins; reload equality covered only 2,048 rows | Fixed: pins checked (all three match); every row checked |
| Publication housekeeping: rewrite and Simple edition of this file, a neutral configuration key name, joining the protocol branch, float64 forecast storage | Rewrite and Simple edition done, separate reader pending; key renamed; branch based on the main branch that holds the published protocol; storage recorded as DECISIONS.md item 18 |

The fixes in this table were committed after the C1b review and before D1, and were first reviewed at C2.

The C2 review, on 27 November 2026, checked the D1 receipts against the pinned central directory with its own parser, rebuilt `QUALIFICATION.json` and `ALLOCATION.json` byte for byte, recomputed the allocation from the protocol rules with its own code, checked the five code fixes, and reran `test_fetch_probe.py` (it passes on the fixed code and halts at the GET-retry case on the C1b code) and `test_assign.py`. It found no blocker or major problem in the D1 records, the allocation or the code fixes. It found one blocker and two major problems in the texts, and five minor points:

| Finding | State |
| --- | --- |
| Blocker: DECISIONS.md said all 18 choices were reviewed with the code at C1b; items 13 to 17 are fixes made after that review and were first reviewed at C2 | Corrected in DECISIONS.md, which also records that its first wording made the same claim |
| Major: the Simple edition used terms it never explained (hash order and salt, bootstrap, p-value, trend forms, G8 and the variety sets, inner folds and the tuned arm, penalty, the random-readout control) | Explained in its word list |
| Major: this file and DECISIONS.md used protocol names (Q6, QP, X, the six-name rule, the stage, arm and gate names, TAG) with no gloss or pointer where they first appear | [Terms](#terms) added here; DECISIONS.md word list extended |
| D1 ran on review fixes that had not yet been reviewed; the C2 review found them correct | Stated in both editions and in DECISIONS.md: the fixes D1 uses change only the retry and halt paths, and neither was taken in D1 |
| `allocate.py assign` does not reproduce `ALLOCATION.json` byte for byte, because `assign.py` adds two keys | Explained under [C2](#c2-allocation-done-and-reviewed) |
| The 292 runtime-B fits were not reconciled with the protocol's figures of about 550 tree and 650 linear fits | Reconciled under [Fits](#fits-f4-choice-p1-and-the-c3-seal-not-run): the protocol figures include the G9 inner-fold fits |
| Precision: the CPU slots were described as shared by every track; all reference checkpoints were described as pinned; DECISIONS.md item 17 said `arrays/` holds the training pool only; item 18 quoted the Q = 80 disk figure | Corrected in the texts. The docstring of `lanes.py` still describes the shared design; it is left unchanged because its sha256 is recorded in `S0-GATES.json` |
| Disclosed open items (lane plan, D3 commit check, F5, the lease-note date); the D1 receipts were committed at C2 rather than C6, which only adds files and exposes no signed query | Unchanged; see [Open items](#open-items) |

## Open items

1. **C2 push.** The separate review of `QUALIFICATION.json` and `ALLOCATION.json`, which the protocol requires before D2, found no blocker or major problem in them. The corrected texts need their separate reading (item 5), and the lead pushes C2 before D2 starts.
2. **Lane plan.** Before `fit.py run`, either every training track takes its CPUs through the `NS_CPU_SLOTS` folder or the tracks run one after the other.
3. **D3 commit check.** D3 checks only that `FIT-COMPLETE.json` names the same allocation. The lead pushes C3 before D3, which gives the seal its public time.
4. **Lease note date.** The note recorded in D1 says "C1b reviewed 28 Nov". The C1b review was finished, and D1 run, on 27 November 2026; the receipts carry the UTC times.
5. **Separate reader.** This file, its Simple edition and DECISIONS.md need a separate reader before publication.
6. **F5.** The optional Research Edition is not admitted and is not run in this stage.

## Choices left to the code

[DECISIONS.md](DECISIONS.md) lists the 18 details the protocol leaves open (indices, labels, training tables, the S4 size, scaling in the force-only tree arm, the earlier-EMG rows, the Brier floor, the standard deviation of the detectable effect, the sensitivity seed, what S-b opens, extra walks, pacing, the retry, local-header mismatches, reference pins, reload equality, custody folders, forecast storage), with the code that applies each. They were fixed in the code before any byte of the pool was read, and none was chosen by looking at a result. Items 1 to 12 and 18 were in the code reviewed at C1b; items 13 to 17 are the fixes for that review, reviewed at C2.
