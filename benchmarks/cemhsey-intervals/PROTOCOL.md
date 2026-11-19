# How far could the next pinch-force reading move?

The CEMHSEY GRASP study recorded adult volunteers pinching a gauge while five forearm surface EMG grids recorded electrical activity through the skin. We ask how wide an error band those readings warrant around a forecast of the gauge reading 24 nominal ticks later. The target is the released Session 5, Task 2 P200 gauge force, expressed as a fraction of the participant’s same-day and grasp maximum voluntary contraction (MVC). [Source study](https://doi.org/10.1038/s41597-025-05733-y) · [GRASP Part I v2](https://doi.org/10.5281/zenodo.15077957) · [GRASP Part II v2](https://doi.org/10.5281/zenodo.15070187)

## Fixed forecasts and new trials

Carry forward three prespecified point forecasts from the earlier array study: persistence, force history with issue phase, and force history with issue phase plus same-trial global EMG summaries and five-grid contrasts (`persistence`, `history_phase`, `history_phase_paired_grid`). Persistence returns the current force. The other two use the unchanged saved TRAIN parameters. No point refit, model selection, alignment change, rescaling or force clipping enters this study.

Each trial contributes issue ticks 60, 70, …, 5970 inclusive. Its target at tick i is f[i+24]. Use force through the issue. Global EMG and grid contrasts use the prior guarded 100 ms windows [i−60,i−40) and [i−40,i−20) expressed in force ticks, with integer edges mapped by ceil(2048b/200) and the existing amplitude and grid order. Fixed phase boundaries at 0, 1000, 2000, 4000, 5000 and 6000 belong to the nominal force record. An interval uses the phase at issue, even when the forecast target lies in the next phase. Tables follow acquisition indices. The nominal 200 Hz conversion gives 120 ms and does not establish a physiological clock, synchronization accuracy or online latency.

| Role | Participants | Indexed days | Repeats | Trials | Issue windows |
| --- | --- | --- | --- | ---: | ---: |
| CAL | 4 | D7 | 1 and 2 | 8 | 4,736 |
| EVAL | 2 | D7 and D8 | 1 and 2 | 8 | 4,736 |

Use each exact Session 5, Task 2 member named by the respective Root grant. CAL and EVAL share neither source members nor participants. Both panels use different source records from the preceding runs and never enter TRAIN. CAL can reuse people from an earlier panel on its new day and must be described as new trial records, while EVAL uses different people from CAL. Freeze and independently check the CAL profile before opening EVAL. Verify exact members, frozen input hashes, separate phase grants, all repeats and complete finite issue support before a stage succeeds. Missing, invalid or changed values stop the stage. Every eligible window counts once. No replacement, imputation, trimming or split reassignment.

## Two ways to set the width

For each fixed point forecast take the absolute CAL residuals |y − forecast|. The pooled scheme uses every CAL issue. The issue-phase scheme uses one CAL pool per issue phase. In each pool of size n, take the value at one-based rank min(n, ceil(0.90(n+1))) in ascending order, with no interpolation. The resulting half-width r gives forecast ± r, including endpoints in coverage. For initial rest, ramp up, hold, release and final rest, the respective per-trial counts are 94, 100, 200, 100 and 98. CAL phase counts are 752, 800, 1,600, 800 and 784 with ranks 678, 721, 1,441, 721 and 707. The pooled rank is 4,264 of 4,736.

## Score the interval and show both kinds of miss

On EVAL, report count and fraction covered, count and fraction below the lower bound and above the upper bound, mean full width, and mean interval score. A covered observation receives the full width as its score. A miss receives the full width plus 20 times the distance to the closest bound. Width and score both use fractions of MVC. Report total issue windows and distinct trials, people and indexed days in each view. The primary summary pools all EVAL issues. Separate phase, indexed-day and participant summaries are descriptive. Participant summaries stay private, as do all trial inputs, forecasts, residuals and fitted parameters.

For each of the three unchanged forecasts, compare issue-phase with pooled bands on exactly the same EVAL issues. Read score, coverage and width together. Call a narrower band with at least the pooled coverage and a lower interval score a descriptive gain on this panel. Call a narrower band that misses more often a width–coverage trade-off, even if its interval score is lower. Equal widths or higher scores give no evidence of the prespecified gain. Report realized coverage relative to the 90% calibration target, including shortfalls when both schemes miss it. Retain all six model–scheme results regardless of how they compare. No retuning, subgroup-based choice, significance test or coverage guarantee follows from these dependent windows, repeated trials and days, or EVAL’s two people.

Measured gauge values provide the reference. Band endpoints and the forecast are derived from offline records. The design supports no inference about individual digit forces, nerves, intent, causal control, other grasp tasks, or the uncertainty of a Brain2Body model outside this specific experiment. Release only independently reproduced, approved rounded aggregate metrics and declared denominators. Public artifacts carry neither participant/window-level values nor trained parameters or a calibrated local profile.

Shared glossary revision 36, SHA-256 `40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406`.
