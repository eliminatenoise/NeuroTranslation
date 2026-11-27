# Walking-force quantity ladder: protocol

Technical edition, protocol version 1, 27 November 2026. The Simple edition is written with the results. [Machine-readable protocol](PROTOCOL.json) · [Allocation script](allocate.py) · [Candidate pool](POOL.json) · [Hash orders](ORDER.json)

This protocol is fixed before any evaluation byte is opened. It tests whether the published walking-force forecasters get better for new people when they are fitted on more people from the same laboratory. Every rule below is final. Group membership is the only item not yet known: it follows mechanically from the rules once a metadata probe has run (section 4).

## 1. Question and estimand

The published walking-force models forecast, for one force plate in the floor, the signed vertical impulse over the next 100 ms (force summed over time, in newton-seconds, N·s) and the chance that the plate starts carrying a new load. All of them were fitted on the same 12 healthy people of one laboratory (Van Criekinge and colleagues, CC0); one of them also used 8 people from a second laboratory. About 80 more healthy people in that release were never assigned to any role.

Question: if the same recipes are fitted on more of these people, does the forecast error fall for people who were never used before?

Primary estimand, for each model family f:

Delta_f = mean over scoreable evaluation people i of [MAE_i,f(N_max) − MAE_i,f(12)]

MAE_i,f(N) is person i's mean absolute impulse error (N·s) for family f fitted on N training people. For each person it is averaged over all replicate fits of that rung (several seeds and draws of people) before people are averaged, so the estimand describes the recipe, not one lucky fit. The relative change is Delta_f divided by the mean of MAE_i,f(12). Quantity is counted in people, with three walks per person. Walks, issue rows, distinct new-load onsets, optimizer updates and examples drawn are reported for every rung.

The 12-person rung is our own refit of the earlier 12 fit people with the identical recipe. It is not one of the published checkpoints; those are scored separately (section 8).

Limits stated in advance:

- One laboratory and one protocol: healthy adults walking barefoot overground at their preferred speed.
- Plates 1 and 2 cover part of a 12 m walkway. The forecast describes those plates only.
- Results cover sessions whose files carry six literal EMG channel names. If file naming follows the recording period, this is a hidden selection.
- EMG (surface electromyography) is muscle voltage measured at the skin. It is not a nerve recording.
- Neighbouring issue windows overlap, so the person is the unit of analysis. New loads are rare, about two distinct onsets per walk.
- A trend fitted to three or four rungs is a short-range extrapolation. It is not a scaling law and says nothing about other laboratories, bodies, tasks or species.

## 2. State at writing

No evaluation, reserved or test byte has been opened, and this track has downloaded nothing. The following checks were made read-only:

- The archive's central directory (the zip file's table of contents, 87,971 bytes, sha256 `96a6b5d9…`, 1,016 entries) was parsed against the earlier roster. 138 healthy codes = 26 listed by the authors as lacking analog data + SUBJ001 (engineering person) + 30 earlier-roster people + 81 never assigned. One of the 81, SUBJ099, is a boundary case (section 3.3), which leaves 80 candidates.
- In the earlier validation metadata, 3 of 6 people failed the six-name rule: a generic label such as `Voltage.12` stood where `Voltage.LBF` or `Voltage.LRF` should be. All 36 fit walks passed. So 15 of 18 people pass so far, and failures concern whole people or sessions, not single walks.
- Hashes of the frozen published checkpoints were confirmed at repository commit `03e76d4` (section 8).
- A faithful re-train of the six sealed 12-person compact checkpoints, from our own C3D reader and feature port, is tensor-identical to the sealed files. The file hashes differ only because safetensors writes its metadata keys in a varying order. Saved without metadata, three separate processes produced identical file bytes.
- The published 12-person tree pair, refitted from the same rows, gives predictions bit-identical to the sealed tree file.
- One consumed fit walk shows that a C3D file's parameter section also holds processed foot events (`EVENT:TIMES`, `EVENT:LABELS`), gait parameters (`ANALYSIS:VALUES`), `SUBJECTS` and `MANUFACTURER`. The probe in section 4 never decodes them.
- Planning studies used the 12 consumed fit people only (3, 6 or 9 training people, 3 held out). They are not evidence about new people.

## 3. Data

### 3.1 Source

- Van Criekinge healthy cohort, figshare `10.6084/m9.figshare.24192480.v1`, data CC0 1.0. Article: Van Criekinge T., Saeys W., Truijen S., Vereeck L., Sloot L. H., Hallemans A., Scientific Data 10, 852 (2023), `10.1038/s41597-023-02767-y`, CC BY 4.0.
- Archive `138_HealthyPiG.zip`, figshare file 42450060, 463,159,769 bytes, md5 `85235c73455d4df8434810d61517efbb`, storage version `c9jtqYlgGUVrgEUy1JMXkChG6zGtCpvu`. Central directory: archive bytes 463,071,776 to 463,159,746, sha256 `96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b`.
- Recording clocks: markers at 100 Hz; plate forces and EMG at 1,000 Hz, ten analog samples per marker frame. Four force plates; plates 1 and 2 are used.
- The stroke cohort of the same release has never been accessed and is not part of this protocol.

### 3.2 People in the pool

[`POOL.json`](POOL.json) lists every healthy code with the reason it is or is not a candidate, and the archive members (path, CRC-32 checksum, byte extent) of each candidate. It was produced by `allocate.py pool` from the central directory alone.

- 80 candidates: SUBJ002-007, 009, 010, 012, 013, 015, 017-019, 021, 022, 025-037, 041, 042, 045, 046, 049-052, 055, 058-060, 063-065, 067-071, 073, 076, 078-081, 083, 086-088, 090, 091, 093-095, 097, 098, 100-109, 111, 113, 114, 117.
- 73 have 3 numbered walks, 6 have 4 and 1 has 5. Their first three walks are 240 members, 228,181,413 compressed bytes; the median walk is 945,890 bytes and the largest 1,839,822 bytes.
- Each person contributes three walks: the three lowest-numbered walks that pass qualification. Walk numbers have no other role.
- The unnumbered file `SUBJ101/SUBJ101.c3d` is ignored.

### 3.3 Earlier roster and boundary items

An earlier metadata-only roster (sha256 `34bf97f3…`, still awaiting the project owner's admission) assigned 30 people: 12 fit, 6 validation and 12 test. This protocol does not reallocate or edit it.

- The 12 fit people (SUBJ024, 038, 039, 040, 043, 044, 061, 062, 082, 096, 110, 112) form the 12-person rung. Their 36 walks (31,290,834 compressed bytes) are read in place, read-only, from the earlier fit transport cache. Each is checked for CRC-32 and size against the central directory and for sha256 against that cache's readback file. They are re-fetched only if a check fails.
- The 6 validation people and the 12 test people (SUBJ008, 014, 016, 020, 053, 056, 057, 074, 077, 084, 089, 092) are never opened by this track.
- SUBJ099 is left out of every role and never opened. The earlier selector paired each archive entry with the next one, so the archive's last member, `SUBJ99 (3).c3d`, was dropped and SUBJ099 appeared to have only two walks. Under the intended rule SUBJ099 would have been the second person of the earlier test block and SUBJ089 would have dropped out. The sealed earlier roster still governs, so SUBJ089 stays reserved, and SUBJ099 waits for the owner's decision.

## 4. Header probe and qualification

The published comparison of tree, linear and 0.0 models needs six named EMG channels. The compact three-pass model does not: it accepts four or six unnamed voltage streams. The six-name rule exists for the matched comparison of families, and its possible selection effect is reported.

### 4.1 What is read

After this protocol is pushed, the code commit (C1b) is reviewed and the owner gives the download lease, one ranged request is made for each of the first three walks of the 80 candidates (240 members). It covers bytes [o, o + 8,704) of the archive, where o is the member's local header offset. The local header (signature, name, method 8, flags 0, CRC-32 and sizes) must equal the central directory. If the inflation below has not reached the C3D header end, the next 8,192 bytes are requested, until 65,536 compressed bytes have been read; then the walk fails with "header not reached". On fit walks the header needs 3,272 to 3,704 compressed bytes, so about 2.1 MB in total is expected, and never more than about 16.4 MB.

The compressed stream is inflated with a hard output limit, so no sample byte is ever produced:

1. Inflate 512 bytes and read the parameter start block p and DATA_START (header word 9).
2. Inflate to (p − 1) × 512 + 4 bytes and read the parameter block count c.
3. Inflate to H = (p − 1 + c) × 512 bytes, the end of the parameter section. The walk fails unless H ≤ (DATA_START − 1) × 512.

### 4.2 What is decoded

- File header: words 1 to 12 only (parameter block, point count, analog words per frame, first and last frame, scale, DATA_START, analog samples per frame, frame rate). The header's event table (words 150 to 234) is not decoded.
- The parameter records are walked by their offset fields. Group names are read to map group numbers. Parameter names are read only inside the groups below; elsewhere their bytes are stepped over without decoding.
- Values are decoded only for: `ANALOG` USED, LABELS, UNITS, SCALE, OFFSET, GEN_SCALE, RATE; every `FORCE_PLATFORM` parameter; `POINT` RATE, DATA_START, UNITS, FRAMES, USED, SCALE; `TRIAL:Z_DIRECTION`. All `ANALOG` parameter names are read so that unknown fields can be detected.
- Never decoded, logged or kept: `EVENT`, `EVENT_CONTEXT`, `ANALYSIS`, `SUBJECTS`, `MANUFACTURER`, `PROCESSING`, every other group and parameter, and all marker values.
- Stored per walk: archive path, byte ranges, sha256 of the compressed bytes received, verdict and reason codes, the number of analog channels, the number of channels named `Voltage.*` in volts, and which of the 14 literal muscle names are present (descriptive). The buffers stay in memory and are discarded after the verdict; no header byte is written to disk.

The same whitelist reader is used later for every person's full walks, including training people.

### 4.3 Verdicts

A walk is **Q6** if every gate passes:

- Native clocks: 100 Hz frames, 1,000 Hz analog, ten analog samples per frame, floating-point storage, Intel byte order.
- Header and parameters agree on point count, frame range, DATA_START and analog words per frame. The stored extent (DATA_START, frames, bytes per frame) matches the expanded size in the central directory to within one 512-byte block.
- Analog labels are unique. `Voltage.LBF`, `Voltage.LERS`, `Voltage.LGAS`, `Voltage.LRF`, `Voltage.LST` and `Voltage.RERS` are each present once, in volts. No `ANALOG` parameter outside USED, LABELS, DESCRIPTIONS, GEN_SCALE, SCALE, OFFSET, UNITS, RATE and GAIN.
- `FORCE_PLATFORM` USED 4, TYPE [2, 2, 2, 2], ZERO [1, 0], no CAL_MATRIX; `TRIAL:Z_DIRECTION` 5; `POINT:UNITS` mm.
- The plate channel table is 4 × 6 with 24 unique, valid columns that do not overlap the six EMG columns. For each plate, the labels are `Force.Fx`, `Force.Fy`, `Force.Fz`, `Moment.Mx`, `Moment.My`, `Moment.Mz` with the plate number, in N and Nmm.
- Four horizontal plates (corner z = 0), finite corners and origins, origin z > 0, plate normal z = −1.
- Finite, non-zero channel scales and general scale.

A walk is **QP** if every gate passes except the six-name rule and it has at least four `Voltage.*` channels in volts. Any other walk is **X**.

People: the first three walks are probed. If one of them is not Q6 and the person has a 4th or 5th walk, those are probed too, lowest number first (at most 8 extra requests). A person is Q6 with at least three Q6 walks, and the three lowest-numbered Q6 walks are used. A person is QP if not Q6 but with at least three walks that are Q6 or QP. Otherwise the person is X. From 15 of 18 earlier people passing, about 67 Q6 people are expected (95% interval roughly 47 to 77); this is a planning figure only.

The probe touches member bytes of people who will become evaluation or physics-source people before the allocation is applied. The hash order is fixed and published before the probe (ORDER.json, committed with this protocol), so verdicts cannot steer roles. The separate reviewer accepts this fence explicitly at admission. The receipt `QUALIFICATION.json` (class, three walk numbers and per-walk verdicts for each candidate) is committed with `ALLOCATION.json` in C2.

## 5. The single allocation

This track is the only allocation writer for the 80 candidates. The physics-source track copies its group from `ALLOCATION.json` and writes no second allocation.

### 5.1 Hash order

A hash order sorts codes by the SHA-256 hash of a fixed text, which gives a reproducible order that no one can choose. The salt is taken from this protocol file itself:

TAG = `10.6084/m9.figshare.24192480.v1|walking-scale|` + sha256 of the committed `PROTOCOL.json`

The primary order sorts the 80 candidates by ascending SHA-256 hex of TAG + `|SUBJnnn`. The order cannot be known before this file is final, so no previewed order could have been chosen. `allocate.py order` writes it to `ORDER.json`, together with the nesting orders, the inner-fold order and the variety-walk positions below; `allocate.py check` recomputes both output files byte for byte.

### 5.2 Group sizes

Let Q be the number of Q6 people. Walking down the primary order over Q6 people only:

- Evaluation group E: the first clamp(floor(0.30 Q + 0.5), 12, 24) people.
- Physics-source group P: the next clamp(floor(0.15 Q + 0.5), 8, 12) people. Its measured test belongs to the physics-source track; this track never downloads these walks.
- Training pool T: the remaining Q6 people.
- Physics supplement: every QP person. Never opened by this track; available to physics-source under its own protocol.
- Unusable: every X person, with the reason.
- If T < 6 the ladder is cancelled: no evaluation group is formed, P is taken from the start of the order, and the other Q6 people stay unallocated and unopened.

Both sizes are computed in whole numbers, as floor((3Q + 5) / 10) and floor((3Q + 10) / 20), so rounding cannot differ between computers.

E is favoured over T because the planning study projects that a few more training people barely change the gain, while a larger E lowers the smallest effect the test can detect (section 12).

| Q | E | P | T | Training people N per rung |
| ---: | ---: | ---: | ---: | --- |
| 80 | 24 | 12 | 44 | 12, 18, 24, 36, 56 |
| 67 | 20 | 10 | 37 | 12, 18, 24, 36, 49 |
| 52 | 16 | 8 | 28 | 12, 18, 24, 40 |
| 40 | 12 | 8 | 20 | 12, 18, 24, 32 |
| 26 | 12 | 8 | 6 | 12, 18 |
| 25 | 0 | 8 | 0 | ladder cancelled |

`allocate.py sizes` prints this table for every Q from 0 to 80.

### 5.3 Rungs and draws

A rung is one training-set size. The added people per rung are a in {6, 12, 24}, kept when a < T and (12 + T) / (12 + a) ≥ 1.25, plus a = T. The 12 earlier fit people are in every rung, so N = 12 + a.

There are 10 draw orders of the training pool, d = 0 to 9, each sorting T by SHA-256 of TAG + `|rung-draw-d|SUBJnnn`. Rung a of draw d takes the first a people of draw order d, so the rungs of one draw are nested. The 12-person rung and the largest rung (N_max = 12 + T) are single fixed sets.

Inner folds, used only by the secondary tuned arm (section 9): within a fit's training people, rank by SHA-256 of TAG + `|inner-fold|SUBJnnn`; fold = rank modulo 4.

### 5.4 Physics-source group

The physics-source protocol (folder `models/physics-source/`, version 1) takes its measured test from group P. P is drawn from six-name people, so it is exchangeable with the evaluation group and every baseline can run on it; the physics-source lead agrees this stratum and the size rule before this protocol is pushed. This protocol provides, for its binding file:

- `ALLOCATION.json`: the P codes and walk members (path, CRC-32, offset, byte extent), the training-pool codes, and the physics-supplement codes with their plate-qualified walks.
- The input adapter and the compact family code, with their sha256 values, from the code commit C1b.
- No marker inputs are admitted here, so physics-source runs its own lag-guarded marker variant.
- The EMG rule is the six-name gate; every P person passes it.
- Our inner folds cover the 12 fit people and each rung's added people, not the 6 earlier validation people, so physics-source uses its own fold rule.
- Plates 1 and 2 only.

After the training pool is downloaded, physics-source may read its walk files and arrays read-only from this track's private folder, so there is one downloader. It never reads evaluation-group files or forecasts.

## 6. Task

The task is the published walking-force task, unchanged.

- **Issues.** At analog sample t = 199 + 20k of each walk's stored 1,000 Hz clock, for every t that leaves a full history. The forecast is made immediately after sample t is read. Each issue gives one row for plate 1 and one for plate 2.
- **History.** Samples t − 199 to t in ten consecutive 20 ms bins. A bin is valid only if all 20 samples are finite.
- **EMG input.** Root-mean-square volts per bin of `Voltage.LBF`, `LERS`, `LGAS`, `LRF`, `LST` and `RERS`, after (raw − OFFSET) × SCALE × GEN_SCALE. Original voltages: no envelope, filter or amplitude normalisation.
- **Force input.** Mean vertical force per bin of the target plate: (raw − OFFSET) × SCALE × GEN_SCALE of its Fz channel, times the plate normal z (−1), so that upward force is positive, in N.
- **Impulse target.** The sum of the plate's upward force over samples t + 1 to t + 100, times 0.001 s, in N·s. All 100 samples must be valid.
- **Plate state.** Unknown at the start and after any invalid sample. Unloaded after 20 consecutive samples between −10 and +10 N. A crossing of +20 N from the unloaded state becomes a new load (dated at the crossing) when the next 19 samples also stay at or above +20 N; a drop below +20 N before that returns to unloaded.
- **New-load label.** Positive if an onset falls in t + 1 to t + 100 and every sample up to its confirmation is valid. Negative if the state at t is known, samples t + 1 to t + 119 are valid and no onset falls in t + 1 to t + 100. Otherwise undefined.
- **Support.** A row is scored for impulse when all six EMG channels and the target plate are valid in all ten bins and the impulse target is defined; for new load, when the inputs are valid and the label is defined. All methods are scored on exactly the same rows.
- **Weights.** People count equally. Within a person, walks count equally; within a walk, issue times; within an issue time, the plates represented (the published person weights).
- **Grids.** The full grid above is primary. The published 24-position schedule (per walk, 8 groups of 3 consecutive eligible times spread evenly over t < n − 119, 48 plate rows; walks with fewer than 24 eligible times are left out) is a secondary table for every method and the only grid for the optional Research Edition.
- **Excluded inputs.** Markers (their published trajectories are gap-filled and smoothed), processed gait events, analysis values, modelled forces, subject parameters, the identity of the person, walk or laboratory, and absolute time.

Model inputs:

- **Compact input** (M1, M2, S5, C4): per bin, target-plate force divided by 800 N; from bin 4 on, the median and 80th percentile across available channels of log(1 + RMS / RMS of the earlier bins of the same window); a force mask and an EMG-summary mask. Channel names do not enter.
- **Tree input** (M3): per bin, the six EMG values, own-plate force and other-plate force, standardised with the rung's training mean and standard deviation, plus eight availability masks; flattened, with the last bin, window means, last minus first, and the persistence impulse (185 columns).
- **Persistence**: the latest bin mean times 0.1 s.

## 7. Models fitted at every rung

No model is chosen anywhere in the primary analysis. Each family uses the same published recipe at every rung; only the data change.

- **M1, compact three-pass recurrent model.** A causal convolution (kernel 3, width 24) with SiLU, a GRU (a gated recurrent layer), then one shared GRU cell applied three times, and a linear head for the new-load logit and the impulse correction to persistence: 7,634 parameters. AdamW, learning rate 0.002, weight decay 0.001, 900 updates of 128 rows drawn with replacement in proportion to person-equal impulse weight. Loss: 0.5 × (smooth L1 on the impulse correction + new-load cross-entropy with the rung's prior as a logit offset, weighted by event against impulse weight). FP32 on CPU, deterministic algorithms, one thread.
- **M2, ridge and logistic regression on the compact input.** 61 columns (flattened input, last bin, window mean, last minus first force). Ridge penalty 1 for the impulse correction; logistic regression with C = 1 for new load; person-equal weights.
- **M3, boosted trees on the published tree input.** Histogram gradient boosting, 128 iterations, learning rate 0.065, at least 24 rows per leaf, L2 penalty 0.3, 95 bins, no early stopping, random state 20261124; 7 leaves (log loss) for new load and 31 leaves (absolute error) for the impulse correction. At N = 12 this is exactly the published tree model.

Replicates:

- M1 at N = 12 and at N_max: 50 seeds, 20261124 + j for j = 0 to 49. Seeds 20261124 to 20261126 at N = 12 must reproduce the sealed earlier checkpoints tensor for tensor.
- M1 at each intermediate rung: 10 draws × 5 seeds; draw d uses seeds 20261124 + 5d + s, s = 0 to 4.
- M2 and M3 are deterministic: one fit at N = 12 and N_max, one per draw at each intermediate rung.
- A failed fit stays visible as failed and is never replaced.

Checkpoints are saved as safetensors without metadata, so their bytes repeat exactly, with metadata in a sidecar file. Earlier files are compared by tensor bytes.

## 8. Controls and frozen checkpoints

Controls, scored once on the same rows:

- **C1, persistence.** The latest bin mean held for 100 ms; new-load probability = the prevalence in the 12 earlier fit people (0.03725847908677051).
- **C2, unconditional.** The same prevalence and the person-weighted median impulse of the 12 earlier fit people.
- **C3, linear trend.** A least-squares line through the last three bin means, placed at the bin centres (t − 49.5, t − 29.5 and t − 9.5 samples), integrated over t + 1 to t + 100 without clipping: 0.1 s × (intercept + 50.5 × slope per sample). Probability as C1.
- **C4, random recurrent readout** (secondary). M1 with its convolution and recurrent layers frozen at their seeded starting values and only the output layer trained, at N = 12 and N_max, 50 seeds each. It shows how much of M1's result needs trained recurrent weights.

Frozen published checkpoints (repository commit `03e76d4`), scored once:

| | Checkpoint | sha256 | Fitted on |
| --- | --- | --- | --- |
| F1 | `benchmarks/walking-neural-scaling/checkpoints/three-pass.safetensors` | `9feb39a8…` | 12 Belgian + 8 İzmir people, augmented continuation; descriptive comparison only |
| F2 | `load.onnx` and `impulse-residual.onnx` in the same folder | `d08f2d79…`, `b6cbe5c0…` | 12 Belgian people; at N = 12 the same model as M3 |
| F3 | NeuroTranslate 0.0 expanded: past-load gate with trainable core, with frozen core, and the two earlier expanded cores | `dd795a15…`, `3197e25e…`, `da97baca…`, `b371040d…` | 12 Belgian people; never tested on other people before |
| F4 | `models/force-baselines/common-six.npz` | `aa499793…` | 12 Belgian people; penalty chosen on the training pool |
| F5 | NeuroTranslate 0.1 Research Edition, `SENSOR-LOOP-JOINT.safetensors` | `3d9a5a2c…` | 12 Belgian people; optional |

- F1 and F2 are issued with the published preprocessing files. F3 is issued through its published code with six EMG values and the target plate per bin.
- F2 and M3 at N = 12 are the same model in two formats. Their agreement is reported on fit rows (S0) and evaluation rows (S-c): the largest difference and the number of rows beyond the published tolerance (0.000017 N·s and 0.00000026 probability). This checks the export and is not a stop rule, because the ONNX graphs compare inputs with tree thresholds in 32-bit precision and a row lying very close to a threshold can fall on the other side. F2 is scored from the ONNX graphs as published.
- F3 is the first test of the 0.0 walking-force preview on people outside its fitting group. Its named comparison is the trainable-core past-load gate against persistence (section 10).
- F4: for each endpoint, input group and arm, the penalty with the lowest person-equal error on the training-pool people is chosen (impulse MAE, new-load Brier score); ties go to the larger penalty. The choice is sealed in C3, before the evaluation group is downloaded. This is the separate validation its README asks for.
- F5 runs only if the owner admits it: about 50 to 55 GB of memory and 3 to 6 hours, alone, reading its base model files read-only by sha256. It is issued on the 24-position grid, one issue time (both plates) per call, because its outputs depend on batch shape. If it is not run, it is reported as not issued.
- Not scored, because they need all 14 muscle names and were fitted on 2 people: the 0.1 Inkling adapter, `strict-fourteen.npz` and the three top-level 0.0 recorded-force checkpoints.

## 9. Secondary arms

Secondary arms are reported with intervals. They are outside the corrected families and never change a primary label.

- **S1, epoch-matched M1.** round(900 × rows_N / rows_12) updates, so that larger rungs see the data as often as the 12-person rung.
- **S2, force only.** M1, M2 and M3 without EMG at every rung. Reports the EMG gain per rung and its change from N = 12 to N_max.
- **S3, capacity.** M1 at width 96, epoch-matched as S1.
- **S4, fixed example budget.** M1, M2 and M3 at each rung above 12 on a hash subsample of training rows equal in number to the 12-person rung (rows ranked by SHA-256 of TAG + `|example-budget|` + N, draw, person, walk, tick and plate). This separates more people from more examples.
- **S5, trees on the compact input** (the published comparator settings), every rung.
- **S6, earlier-EMG timing control.** M1 and M2 at N = 12 and N_max with the EMG window ending 500 ms before the issue in the same walk and the force history unchanged, compared with contemporaneous inputs on the same rows. Gait rhythm can survive in the earlier window, so this is a timing check, not a removal of muscle information.
- **S8, subgroups** (descriptive): plate loaded or unloaded at the issue (state from samples through t only), plate 1 or 2, ten probability reliability bins, distinct onsets.
- **S9, ranking** (descriptive) of all families, controls and frozen checkpoints at each rung.
- **G8, variety.** At N_max, for M1 (50 seeds), M2 and M3: the 12 earlier people plus every training-pool person with one walk each (the walk picked by SHA-256 of TAG + `|variety-walk|SUBJnnn`, modulo 3), against the 12 plus the first floor(T / 3) people of draw order 0 with three walks each. Row counts are nearly equal, so this tests more varied people against more walks per person.
- **G9, tuned.** M3 leaves from {7, 15, 31} and M2 penalty from {0.001, 0.01, 0.1, 1} (logistic C = 1 / penalty), chosen per endpoint by the four inner person folds of each fit's training people; ties go to fewer leaves and the larger penalty.

Arm S7 of the reviewed designs (an ensemble of replicate forecasts) is not run.

## 10. Metrics, uncertainty and success rule

- **Impulse error.** Mean absolute error of signed impulse (N·s), people weighted equally, on the common support.
- **New-load error.** Brier score: the mean squared difference between forecast probability and outcome coded 0 or 1, people weighted equally.
- **Per person.** Each replicate's error is computed with the published weights, then averaged over the rung's replicates and draws, before people are averaged or resampled.
- **Intervals.** Paired bootstrap over scoreable evaluation people: 10,000 resamples of people with replacement, percentile 95% intervals for Delta and for the relative change. The resampling indices come from `numpy.random.default_rng(20261127)`, drawn once for the people scoreable for impulse and once (fresh generator, same seed) for those scoreable for new load, with people in ascending code order; each index matrix is shared by every contrast and the trend test on that set. Two-sided p = min(1, 2 × min(1 + #(Delta* ≥ 0), 1 + #(Delta* ≤ 0)) / 10,001). A bootstrap over people and then replicates is reported as a sensitivity check.
- **Minimum detectable effect.** (1.960 + 0.842) × SD of the per-person differences / √E_s / mean MAE(12), and the same with 2.394 in place of 1.960 for the strictest corrected level.

Success rule. Three co-primary tests, one per family (M1, M2, M3), on impulse error over the full grid, with Holm correction at a familywise level of 0.05. Holm correction multiplies the smallest of the three p-values by 3, the next by 2 and the largest by 1, keeping the adjusted values in order. Labels, checked in this order:

1. **Harmed**: adjusted p < 0.05 and Delta > 0.
2. **Helped**: adjusted p < 0.05, Delta < 0 and a relative change of −3% or better.
3. **Practically no change**: the 95% interval of the relative change lies inside −3% to +3%.
4. **Inconclusive**: otherwise, reported with the minimum detectable effect.

The 3% threshold is about twice the seed-to-seed spread of the published three-pass curve. A statement that the NeuroTranslate compact model gains from more people requires M1 to be labelled helped. The planning study projects about 3% for M1, at the threshold, so M1 may well end practically no change or inconclusive; this is stated in advance. The three Brier contrasts form a second, secondary Holm family with the same labels. The slope of rung means on log2 N, the gain per doubling in the upper against the lower half of the ladder, and the share of people who improved are descriptive.

Floors: confirmatory impulse labels need at least 12 scoreable evaluation people, and Brier labels at least 10 with both outcomes. Below a floor every result is descriptive. Assigned people who turn out unscoreable are reported as such and count against the floors; MAE uses the scoreable people.

First held test of the 0.0 preview, outside the Holm family: F3 trainable-core past-load gate minus C1 persistence, impulse error, with a 95% interval, on the full grid and on the 24-position grid of its model card. The gate has lower or higher error than persistence if the interval excludes zero; otherwise there is no detectable difference.

Every frozen checkpoint and control is also reported against our N = 12 and N_max fits with paired intervals. Every predeclared result is reported, whichever way it falls.

## 11. Sealed predictions and the trend test

- **P0, planning prior.** From the fit-people study (288 three-pass fits and matching linear and tree fits), with L + a / √N fitted to the 3, 6 and 9 person means: relative gain from 12 to 49 people of −2.9% for M1, −2.8% for M2 and −9.7% for boosted trees. The planning trees used the compact input, so the M3 figure is approximate. A prior expectation only.
- **P1, pool-tail curve.** Only if T ≥ 32. Sealed in C3, before any evaluation byte. For each draw, the training-pool people after the largest intermediate rung are unseen by that draw's intermediate fits and by the 12-person fits. Those fits are scored on them, the trend forms below are fitted to the draw-averaged curve, and the gain at N_max is predicted.
- **P2, trend prediction.** After all forecasts are sealed (C4), stage S-b scores only the rungs below N_max. The trend forms are fitted to those rung means. The point predictions and the predicted N_max value in every bootstrap resample are written to `P2-TREND-PREDICTION.json` and committed (C5). Only then does stage S-c score N_max, the frozen checkpoints and the controls. The S-c scorer refuses to run without the committed P2 file's sha256.

Trend forms, for M1, M2 and M3, fitted only when at least three rungs lie below N_max:

- primary: MAE(N) = L + a / √N, least squares on rung means with L ≥ 0 (the form used by the repository's training-scale study);
- competitors: MAE(N) = c + b log2 N, and carry-forward of the second-largest rung.

The trend is tested with the shared bootstrap: in each resample, the form is refitted to the resampled rung means and the difference actual minus predicted at N_max is taken on the same resample. If the 95% interval of that difference contains zero, the trend held; if it lies entirely below zero, error fell faster than predicted; entirely above, slower. Each form's absolute miss and whether the primary form beat carry-forward are reported. The trend code is deterministic and committed in C1b.

## 12. Power

From the fit-people planning study: the M1 seed-to-seed standard deviation is 0.146 N·s per person; the person-level standard deviation of the paired change, after removing seed noise, is 0.19 N·s (about 7%); the projected M1 gain from 12 to N_max is about 3%.

At a per-person standard deviation of 6% of the error, the smallest relative effect detectable with 80% power at two-sided 0.05 is 4.9% at E = 12, 4.2% at 16, 3.8% at 20 and 3.4% at 24. M3 (projected about 10%) is well powered; M1 sits at the decision threshold. S1 and S3 show whether a null M1 result comes from the matched budget or the model size rather than from the data.

## 13. Engineering gates and stop rules

Before any new byte is read, in our own runtimes and on the 12 earlier fit people only:

- **G0.** Our training code on the encoded 12-person cache reproduces the sealed three-pass checkpoints for seeds 20261124 to 20261126 tensor for tensor, with the same last-batch loss.
- **G1.** Our C3D reader and feature port reproduce the 9,946 issue rows of the 36 fit walks bit for bit (9,586 impulse, 9,150 new-load and 324 positive rows).
- **G2.** From C3D files to encoded cache (bit-identical on every key) to checkpoint: tensor-identical.
- **Trees.** M3 at N = 12 gives predictions bit-identical to the sealed tree file; M2 and S5 at N = 12 equal the sealed 12-person comparator predictions.
- **G3.** Replacing every sample after t with noise on fit walks leaves every input and forecast of every method unchanged. Forecasts issued one row at a time and in batches agree within 0.0001 N·s and 0.000001 probability (32-bit rounding). Forecasts are always issued in one fixed batch order, so they repeat bit for bit.
- **F4 refit.** Refitting the 40 common-six candidates with the earlier baseline method (ridge in closed form, logistic regression by Newton steps) reproduces `common-six.npz` array for array.
- Every saved checkpoint is reloaded and its forecasts recomputed before sealing. A failed gate stops the work before the next download.

Stop rules:

- No protocol change after P1 or after any interim number. A change needs a new version, a separate admission and new evaluation people.
- Training walks with no scoreable rows are dropped and counted; nothing is substituted after qualification.
- Evaluation people who turn out unscoreable stay in the denominator as assigned-unscoreable.
- Failed fits stay visible.
- A failed download check (ETag, version, size or CRC-32) halts the stage.

## 14. Stages, commits and custody

| Stage | Content |
| --- | --- |
| S0 | Build runtimes, write and test code on the 12 fit people, re-run the gates. No new data. |
| C1 | This protocol, `POOL.json`, `ORDER.json`, `allocate.py`. A separate reviewer admits it; the lead pushes it before any download. |
| C1b | Code (fetch, qualify, extract, three-pass, trees, linear, fit, issue, score, trend) with gate receipts; reviewed against this protocol before D1. |
| D1 | Header probe (section 4). |
| C2 | `QUALIFICATION.json` and `ALLOCATION.json`, reviewed before any sample byte. |
| D2 | Training-pool walks. |
| Fits | All fits, the F4 penalty choice, P1. |
| C3 | `FIT-COMPLETE.json`: sha256 of every checkpoint and tree file (by tensor bytes), F4 penalties, P1. |
| D3 | Evaluation-group walks. |
| Issue | History-only packets; forecasts of every method; N_max forecasts in a separate file. |
| C4 | `FORECASTS-SEAL.json`: sha256 of every private forecast file. |
| S-b | Score the rungs below N_max; fit the trends. |
| C5 | `P2-TREND-PREDICTION.json`. |
| S-c | Score N_max, frozen checkpoints and controls; independent replay of every aggregate and of sample rows from each plate. |
| C6 | Results in a Technical and a Simple edition (first draft, rewrite, separate reader). |

Custody:

- The extractor writes inputs (keys, histories, input masks) and targets (labels, impulses, target masks) to separate private files. The issuing process reads inputs only; a separate scorer joins targets.
- N_max forecasts sit in their own file, which the S-b scorer cannot read.
- Each stage keeps the record chain LOCK, ATTEMPT, checkpoint, reload equality, RESULT, READBACK, SCORE-LOCK.
- The lead pushes C1, C2, C3 and C5 before the next stage starts, so each seal has a public time.

## 15. Downloads

| Stage | Members | Bytes |
| --- | --- | --- |
| D1 header probe | 240 to 248 walks, partial reads | about 2.1 MB, at most 16.4 MB |
| D2 training pool | 3 × T walks | about 100 to 130 MB (about 0.95 MB per walk) |
| D3 evaluation group | 3 × E walks | about 34 to 68 MB |

- Never downloaded by this track: physics-source and physics-supplement walks, static trials, SUBJ099, the earlier validation and test people, the stroke cohort.
- Each request starts at the stable file address `https://ndownloader.figshare.com/files/42450060` and takes a fresh redirect, because the signed storage address lives about 10 seconds. Then one ranged request reads from the member's local header to the next local header. ETag and storage version must equal the values in section 3.1. Whole members are checked for size and CRC-32 against the central directory, and their sha256 is recorded.
- At most one request per second, paced inside the downloader by a monotonic clock. On a 429 or 5xx reply, one retry after 60 seconds, then halt.
- Private receipts record the stable address, storage host and path, version, ETag, byte range, bytes, CRC-32 and sha256. Signed query parameters are removed.
- About 10 minutes of transfer in total.

## 16. Compute and runtimes

- Runtime A: CPython 3.13.15, torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0 (M1, C4, S1, S3, F1).
- Runtime B: CPython 3.12.14, numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0 (M2, M3, S5, G9, F2, F3, F4 and scoring).
- Exactly one thread per fit: two threads change the weights, and a different torch build changes weights by up to 0.22.
- At most 12 single-thread lanes on CPUs 20 to 31, with control on CPUs 16 to 19; at most 16 threads in total.
- Measured: M1, 900 updates, 1.5 to 4 s; trees 4.6 s at 9,586 rows and about 52 s for three leaf settings and both endpoints at 48,000 rows. In all, about 250 primary and 1,450 total M1 fits, about 550 tree fits and 650 linear fits: about 4 to 8 core-hours, 30 to 60 minutes of wall time.
- Under 0.7 GB in the private folder.

## 17. Rights

- Van Criekinge recordings: CC0 1.0. Article: CC BY 4.0. Both are credited.
- Ladder weights come only from Van Criekinge CC0 recordings. They are released under CC0 1.0 with a NOTICE that credits the dataset and the article and describes our processing.
- Scored only, never refitted or redistributed here: F1 inherits İzmir data (CC BY 4.0, `10.48623/aperta.286865`); F3's core inherits training on worm imaging (Zenodo `10.5281/zenodo.19388374`) and SLEAP sample tracks; F5's base is Apache-2.0 with its acceptable-use policy. Scoring a checkpoint is not training on its sources; the results state each lineage.
- İzmir, MoVi, the worm data, SLEAP, MuscleMimic and MyoGen material never enter the ladder weights.
- C3D files, arrays, forecasts and targets stay in this track's private folder and are never committed.

## 18. What will be published

- Now: `PROTOCOL.md`, `PROTOCOL.json`, `allocate.py`, `POOL.json`, `ORDER.json`.
- C1b: code and gate receipts. C2: `QUALIFICATION.json`, `ALLOCATION.json`. C3: `FIT-COMPLETE.json`. C4: `FORECASTS-SEAL.json`. C5: `P2-TREND-PREDICTION.json`.
- C6: `RESULTS.json` with every predeclared number, interval and count and the per-person errors by archive code; the results in a Technical and a Simple edition; the M1 N_max checkpoint (seed 20261124) without metadata plus its sidecar, the M3 N_max trees as ONNX checked against scikit-learn, and the M2 N_max coefficients, under CC0 with a NOTICE; download receipts without signed addresses.

## 19. Time estimates

Assuming the owner gives the download lease and admission on 28 November 2026:

| Step | When | Machine time |
| --- | --- | --- |
| S0 and code commit C1b | 28 November | about half a day |
| D1 and C2 | 28 to 29 November | minutes of download, hours of review |
| D2, fits and C3 | 29 November | about 10 min download, 30 to 60 min compute |
| D3 to S-c | 29 to 30 November | minutes of download, under 1 h compute |
| Results editions and separate reader | 30 November to 1 December | about a day |
| F5, if admitted | after S-c | 3 to 6 h, alone |

The wall time, about two days after admission, is set by the review gates, not by computing.

## 20. Decisions pending with the owner

1. A task lease and scientific admission for the downloads after this protocol is pushed: header probe about 2 to 16 MB, training pool about 100 to 130 MB, evaluation group about 34 to 68 MB.
2. Agreement to spend the last fresh healthy Van Criekinge pool (80 people) on this ladder, the physics-source group and the physics supplement. Afterwards only the earlier 12-person test and the stroke cohort remain unopened.
3. SUBJ099: keep it unopened (the default here) or include it.
4. Optional scoring of the Research Edition (F5).
5. A courtesy confirmation that this track is the sole allocation writer for the 80 never-assigned people, since the earlier roster's owner holds the source line and its roster awaits admission.
