# Walking-force quantity ladder: results

Technical edition · [Simple edition](README-SIMPLE.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Run code](README-CODE.md) · [Run code, Simple edition](README-CODE-SIMPLE.md) · [Choices left to the code](DECISIONS.md) · [Results file](RESULTS.json) · [Supplement](RESULTS-SUPPLEMENT.json) · [Sources and terms](NOTICE.md)

Protocol version 1 of the walking-force quantity ladder asked whether three fixed recipes forecast vertical ground force better, for people they have not seen, when they are fitted on more people from the same laboratory. This file reports every result the protocol declared in advance, whichever way it fell.

The numbers come from two files in this folder. [RESULTS.json](RESULTS.json) was written by the scorer at the last scoring stage (S-c). [RESULTS-SUPPLEMENT.json](RESULTS-SUPPLEMENT.json) holds descriptive tables computed afterwards from the same sealed forecasts: the 24-position schedule for every method, contrasts at the same rung, the rows with an earlier EMG window, the means of the two variety sets, subgroup counts and further subgroup rows, the Brier ranking and the training-set counts. It changes no number in RESULTS.json. Where this text and those files disagree, the files govern. Impulse errors are rounded to four decimals, Brier scores to six and percentages to two. All times are UTC on 27 November 2026.

## Summary

- **Setting.** Healthy adults walking barefoot overground at their preferred speed in one laboratory. Every 20 ms a forecast is made from the last 200 ms of six surface EMG channels and one force plate's vertical force: the plate's vertical impulse over the next 100 ms, and the probability that a new load on the plate begins in that time. Three fixed recipes were fitted on 12, 18, 24, 36 and 47 people and scored on 20 other people (60 walks, 17,888 forecast rows).
- **Main result.** From 12 to 47 training people the impulse error, the mean absolute error of the impulse forecast, fell by 5.30% for M1, the compact recurrent model (95% interval −6.77% to −3.85%), by 4.76% for M2, ridge and logistic regression (−5.42% to −4.07%), and by 11.07% for M3, boosted trees (−14.92% to −7.52%). All three are labelled HELPED under the protocol's rule, each with a p-value of 0.0006 after Holm correction, the adjustment for testing three families at once. The protocol's condition for stating that the compact model gains from more people is met, for this setting.
- **New-load probability.** The Brier score is the mean squared difference between the forecast probability and the outcome (0 or 1); lower is better. Only M3's Brier score improved (−5.83%, −7.61% to −4.05%, HELPED). M1 and M2 are labelled PRACTICALLY NO CHANGE, and both stay within 2% of a constant forecast.
- **Sealed predictions.** The planning prior P0 expected −2.9%, −2.8% and −9.7%. The prediction sealed before the evaluation group was downloaded (P1) came within 0.9 percentage points of each observed change, and the one sealed before the largest rung was scored (P2) within 0.4. The protocol's trend test compares the error observed at 47 people with the value predicted by a curve fitted to the four smaller rungs. By that test, error at 47 people fell slightly more slowly than the primary trend form predicted for M1 and M2 (by 0.0089 and 0.0059 N·s), and the trend held for M3.
- **First test of the 0.0 preview on other people.** The walking-force model of the NeuroTranslate 0.0 preview, the past-load gate with trainable core (F3), had been fitted on the 12 earlier fit people and never tested on other people. Persistence is the control that holds the plate's latest 20 ms mean force for the next 100 ms. The gate had 6.02% lower impulse error than persistence on all issue times (−7.57% to −4.39%) and 3.28% lower on the 24-position schedule of its model card, which takes 24 issue times per walk (−5.81% to −0.39%). Its error is still 52.39% above M1 at 47 people and cannot be told apart from M2 at 47 people.
- **Secondary arms.** M1's fixed budget of 900 updates holds its error up: the same model with updates scaled to the training rows (S1) reached 1.5964 N·s at 47 people, against 2.1957 for M1, and a wider model (S3) 1.5484. Removing EMG raised the impulse error at 47 people by 2.03% (M1), 0.69% (M2) and 1.50% (M3, interval includes zero). These arms are outside the corrected tests.
- **Scope.** One laboratory, one task, plates 1 and 2, people whose files carry six named EMG channels, and a ladder that always contains the same 12 people. Surface EMG is muscle voltage at the skin, not a nerve recording. The curve is a short-range result on four steps, not a scaling law.
- **Custody.** Two statements in the sealed records need qualifying, and both are set out under [Custody and the order of events](#custody-and-the-order-of-events): the extractor decoded the evaluation targets before the forecasts were issued, although the issuing processes never read them, and the forecast seal became public only after the first scoring step.

## What was run

### Data, qualification and groups

The recordings are the healthy cohort of Van Criekinge and colleagues (figshare `10.6084/m9.figshare.24192480.v1`, CC0 1.0; see [NOTICE.md](NOTICE.md)): markers at 100 Hz, and force plates and surface EMG at 1,000 Hz. Surface EMG is the voltage that muscles produce at the skin. The stroke cohort of the same release has never been accessed.

The archive lists 138 healthy participant codes ([POOL.json](POOL.json)). 58 were excluded before any recording byte was read: 26 that the authors list without analog data, the 30 people of the project's earlier work on this dataset (12 used for fitting, 6 for validation, 12 for testing), 1 person used for engineering and 1 boundary case that has never been opened. The other 80 were candidates.

The header probe (stage D1) read 8,704 compressed bytes at the start of 241 walk files, 2,097,664 bytes in all, and produced no sample byte. It classed each walk. A walk is Q6 if it passes every gate of protocol section 4, including the six-name rule: the EMG channels `Voltage.LBF`, `Voltage.LERS`, `Voltage.LGAS`, `Voltage.LRF`, `Voltage.LST` and `Voltage.RERS` each present once, in volts. A walk is QP if it fails only the six-name rule and has at least four `Voltage.*` channels in volts, and X otherwise. A person is Q6 with at least three Q6 walks, and the three lowest-numbered Q6 walks are used. The probe found 65 Q6 people, 11 QP and 4 X ([QUALIFICATION.json](QUALIFICATION.json)). The protocol had planned for about 67 Q6 people (95% interval roughly 47 to 77).

The 65 Q6 people were divided along a hash order that was fixed and published before the probe ([ALLOCATION.json](ALLOCATION.json)): an evaluation group of 20 people, a physics-source group of 10 people that this track never downloads, and a training pool of 35 people. The 11 QP people form a physics supplement that this track never opens.

A rung is a training-set size. The rungs are N = 12, 18, 24, 36 and 47 people: the 12 people on whom the project's published walking-force models were fitted (the 12 earlier fit people), plus 6, 12, 24 or all 35 pool people. N_max = 47 is the largest rung. At N = 18, 24 and 36 there are 10 draws of pool people, taken from 10 published hash orders and nested within each draw; at N = 12 and N = 47 there is one training set. With 65 qualified people instead of 67, the largest rung is 47 rather than the 49 of the planning figures.

### Task and scores

The task is the project's published walking-force task, unchanged (protocol section 6). A forecast is issued every 20 ms, at analog sample t = 199 + 20k, for each of plates 1 and 2. Its input is the preceding 200 ms in ten 20 ms bins: the RMS voltage of the six EMG channels and the mean vertical force on the plate. Markers, processed gait events, modelled forces, subject parameters, the identity of the person, walk or laboratory, and absolute time are not inputs. Two quantities are forecast:

- **Impulse.** The signed vertical impulse on the plate over the next 100 ms, in newton seconds (N·s). Its score is the mean absolute error.
- **New load.** The probability that a new load on the plate begins within the next 100 ms. A new load begins when the vertical force of an unloaded plate crosses +20 N and stays at or above it for the next 19 samples. Its score is the Brier score, the mean squared difference between the forecast probability and the outcome (0 or 1).

Lower is better for both scores. Both are person-equal: people count equally, a person's walks count equally, a walk's issue times count equally, and at one issue time the plates present count equally. A row is one forecast for one plate at one issue time. All methods are scored on the same rows.

Two sets of rows are reported. "All issue times" is the protocol's full grid; the labels below come from it. The "24-position schedule" takes 8 groups of 3 consecutive issue times per walk (48 plate rows per walk); it is the schedule of the published model cards and is reported for every method as a secondary table.

### Recipes and fits

Three recipes, called families, were fitted at every rung with the settings fixed in protocol section 7:

- **M1, compact recurrent model.** A causal convolution (kernel 3, width 24), a GRU, one shared GRU cell applied three times, and a linear output: 7,634 parameters. Every fit takes 900 updates of 128 rows, at every rung. There are 50 fits per rung (50 seeds at N = 12 and N = 47; 10 draws of 5 seeds at the other rungs), and each person's error is averaged over the 50 fits before people are compared. Its input is the compact input: per bin the plate's force and two summaries, across the available channels, of the change in EMG within the window. Channel names do not enter.
- **M2, ridge and logistic regression.** Ridge regression (penalty 1) for the impulse and logistic regression (C = 1) for the new load, on the compact input flattened with summaries to 61 columns. One fit per training set.
- **M3, boosted trees.** Histogram gradient-boosted trees (128 iterations) on the published tree input: 185 columns, per bin the six EMG values and both plates' force, with summaries. One fit per training set.

All three forecast the impulse as a correction to persistence, the latest 20 ms mean force held for 100 ms.

The 12-person rung is this track's own refit of the 12 earlier fit people with the identical recipe. It is not one of the published checkpoints, which are scored separately below. A private check after the fits found that the refit reproduces the earlier sealed 12-person models exactly: the first three M1 seeds gave files with the sha256 values pinned in PROTOCOL.json, and M2 and M3 gave bit-identical forecasts on the 9,586 training rows.

In all 1,742 fits were made ([FIT-COMPLETE.json](FIT-COMPLETE.json)): 250 for M1, 32 each for M2 and M3, and 1,428 for the control C4 and the secondary arms. None failed, and every saved fit gave identical forecasts after it was loaded again.

## Counts

The evaluation group has 20 people, 60 walks, one site and one task. All 20 people are scoreable for the impulse and, with both outcomes present, for the new load, so the protocol's floors of 12 and 10 people are met. There are 17,888 issued rows (8,944 per plate), of which 17,288 have an impulse target and 17,040 a new-load label; 579 labels are positive, from 118 distinct onsets. On the 24-position schedule there are 2,880 impulse rows and 2,863 new-load rows, 95 of them positive, from 41 distinct onsets.

Training sets by rung. Where a rung has 10 draws, the mean is given with the range in parentheses:

| Training people | Training sets | Walks | Issue rows | Impulse rows | New-load rows | Positive rows | Distinct onsets |
|---|---|---|---|---|---|---|---|
| 12 | 1 | 36 | 9,946 | 9,586 | 9,150 | 324 | 67 |
| 18 | 10 | 54 | 15,303 (14,604 to 16,152) | 14,763 (14,064 to 15,612) | 14,250 (13,552 to 15,095) | 497.0 (481 to 504) | 102.3 (100 to 103) |
| 24 | 10 | 72 | 20,793 (20,196 to 21,472) | 20,073 (19,476 to 20,752) | 19,481 (18,885 to 20,153) | 672.4 (658 to 681) | 138.1 (136 to 139) |
| 36 | 10 | 108 | 31,797 (31,144 to 32,344) | 30,717 (30,064 to 31,264) | 29,969 (29,320 to 30,511) | 1,017.6 (1,012 to 1,024) | 208.6 (208 to 210) |
| 47 | 1 | 141 | 42,030 | 40,620 | 39,729 | 1,339 | 274 |

Fits and updates by rung. S1 and S3 are the two arms whose updates grow with the training rows:

| Training people | M1 fits | M1 updates per fit | M1 examples drawn per fit | S1 and S3 updates per fit | S1 and S3 examples drawn per fit | M2 fits | M3 fits |
|---|---|---|---|---|---|---|---|
| 12 | 50 | 900 | 115,200 | 900 | 115,200 | 1 | 1 |
| 18 | 50 | 900 | 115,200 | 1,320 to 1,466 | 168,960 to 187,648 | 10 | 10 |
| 24 | 50 | 900 | 115,200 | 1,829 to 1,948 | 234,112 to 249,344 | 10 | 10 |
| 36 | 50 | 900 | 115,200 | 2,823 to 2,935 | 361,344 to 375,680 | 10 | 10 |
| 47 | 50 | 900 | 115,200 | 3,814 | 488,192 | 1 | 1 |

## Impulse error against the number of training people

The success rule (protocol section 10) has three co-primary tests, one per family: the change in impulse error from N = 12 to N = 47 on all issue times. Each is tested with a paired bootstrap over the 20 evaluation people (10,000 resamples of people, percentile 95% intervals, a two-sided p), with Holm correction over the three tests at a familywise level of 0.05. Holm correction multiplies the smallest of the three p-values by 3, the next by 2 and the largest by 1, and no adjusted value may be smaller than the one before it. The labels are checked in this order: HARMED (adjusted p below 0.05 and error rose); HELPED (adjusted p below 0.05, error fell, and the relative change is −3% or better); PRACTICALLY NO CHANGE (the 95% interval of the relative change lies inside −3% to +3%); INCONCLUSIVE otherwise.

The 3% threshold is about twice the seed-to-seed spread of the published three-pass curve. The planning study had projected about 3% for M1, at the threshold, and the protocol stated in advance that M1 might well end PRACTICALLY NO CHANGE or INCONCLUSIVE.

Impulse error (N·s) by rung:

| Family | Rows | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | all issue times | 2.3187 | 2.2652 | 2.2555 | 2.1986 | 2.1957 |
| M1, compact recurrent model | 24-position schedule | 2.1062 | 2.0590 | 2.0477 | 1.9971 | 1.9944 |
| M2, ridge and logistic regression | all issue times | 3.6196 | 3.5472 | 3.5133 | 3.4689 | 3.4474 |
| M2, ridge and logistic regression | 24-position schedule | 3.4024 | 3.3307 | 3.2944 | 3.2510 | 3.2307 |
| M3, boosted trees | all issue times | 2.1653 | 2.0826 | 2.0245 | 1.9507 | 1.9255 |
| M3, boosted trees | 24-position schedule | 2.0409 | 1.9406 | 1.8919 | 1.8298 | 1.8088 |

Change from N = 12 to N = 47, all issue times (N·s):

| Family | Change | 95% interval | Relative change | 95% interval (relative) | p | Holm p | People with lower error | Label |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | −0.1230 | −0.1532 to −0.0945 | −5.30% | −6.77% to −3.85% | 0.0002 | 0.0006 | 20 of 20 | HELPED |
| M2, ridge and logistic regression | −0.1723 | −0.1852 to −0.1605 | −4.76% | −5.42% to −4.07% | 0.0002 | 0.0006 | 20 of 20 | HELPED |
| M3, boosted trees | −0.2398 | −0.3128 to −0.1669 | −11.07% | −14.92% to −7.52% | 0.0002 | 0.0006 | 18 of 20 | HELPED |

All three families are labelled HELPED.

- **p-values.** In none of the 10,000 resamples was the change zero or positive, so each p-value is the smallest this bootstrap can give, 2/10,001, and each Holm-adjusted value is 0.0006: 3 × 2/10,001 for the first, and the other two are raised to that value.
- **Size.** The rule asks for a point estimate of −3% or better. Beyond that, each 95% interval of the relative change lies wholly below −3%.
- **People.** Error fell for all 20 evaluation people with M1 and with M2, and for 18 of 20 with M3; it rose for SUBJ059 and SUBJ078.
- **The compact model.** The protocol allowed the statement that the NeuroTranslate compact model gains from more people only if M1 was labelled HELPED. It was (`compact_model_claim_allowed` is true in RESULTS.json). The statement holds for this setting: these 12 fit people, this pool, this laboratory and task, and a fixed 900 updates.
- **Shape of the curve.** M1's error fell from 2.3187 N·s at 12 people to 2.1986 at 36 and 2.1957 at 47, so its last step is nearly flat. The label rests on the contrast of 12 against 47 people only.

Further figures for the same contrast:

| Family | Error at N = 12 | SD of per-person differences | Smallest detectable change, 5% level | Smallest detectable change, first Holm step | Sensitivity interval (relative) | Slope per doubling | Gain per doubling, 12 to 24 | Gain per doubling, 24 to 47 |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | 2.3187 | 0.0688 | 1.86% | 2.15% | −6.88% to −3.81% | −0.0642 | −0.0631 | −0.0617 |
| M2, ridge and logistic regression | 3.6196 | 0.0289 | 0.50% | 0.58% | −5.42% to −4.07% | −0.0861 | −0.1063 | −0.0680 |
| M3, boosted trees | 2.1653 | 0.1700 | 4.92% | 5.68% | −14.92% to −7.52% | −0.1244 | −0.1408 | −0.1020 |

The smallest detectable change is the relative change that 20 people with this standard deviation would detect with 80% power, at the two-sided 5% level and at the level of the first Holm step (protocol sections 10 and 12). The standard deviation of the per-person differences was 0.0688 N·s for M1, where planning had assumed 0.19 N·s, so the smallest detectable change was below 3% for M1 and M2. For M3 it was 4.92% and 5.68%, against an observed change of 11.07%. The sensitivity interval resamples people and then each person's replicate fits; M2 and M3 have one fit at each of the two rungs, so theirs equals the primary interval. The slope is that of the rung means on log2 N; the gains per doubling compare the lower and the upper half of the ladder. These figures are descriptive.

Per-person impulse error (N·s) by archive code. SUBJ080's errors are about twice those of the others under every family:

| Person | M1 at N = 12 | M1 at N = 47 | M2 at N = 12 | M2 at N = 47 | M3 at N = 12 | M3 at N = 47 |
|---|---|---|---|---|---|---|
| SUBJ005 | 1.0285 | 0.9975 | 2.1791 | 2.0026 | 0.8742 | 0.8006 |
| SUBJ029 | 2.7064 | 2.5878 | 4.1529 | 3.9948 | 2.3239 | 1.9692 |
| SUBJ034 | 1.9566 | 1.8446 | 3.0989 | 2.9514 | 1.8104 | 1.6434 |
| SUBJ035 | 1.8887 | 1.7375 | 2.8502 | 2.6974 | 2.1509 | 1.6624 |
| SUBJ042 | 2.4625 | 2.3699 | 3.7872 | 3.6044 | 2.1745 | 1.9626 |
| SUBJ055 | 2.3445 | 2.2516 | 3.6692 | 3.5071 | 1.9711 | 1.8470 |
| SUBJ059 | 2.5025 | 2.2865 | 3.8426 | 3.6870 | 1.9100 | 2.0153 |
| SUBJ064 | 1.9356 | 1.7785 | 2.7009 | 2.5340 | 1.9570 | 1.7365 |
| SUBJ067 | 2.3001 | 2.1332 | 3.5918 | 3.4123 | 2.3532 | 1.9479 |
| SUBJ068 | 1.8109 | 1.7262 | 3.2698 | 3.0932 | 1.6431 | 1.4990 |
| SUBJ070 | 2.1118 | 2.0218 | 3.4805 | 3.2385 | 1.8023 | 1.5688 |
| SUBJ076 | 2.1438 | 1.9181 | 3.3642 | 3.1700 | 2.2076 | 1.6529 |
| SUBJ078 | 2.0638 | 1.9519 | 3.2902 | 3.1327 | 1.5248 | 1.5384 |
| SUBJ080 | 4.9642 | 4.9528 | 7.4662 | 7.3138 | 4.6049 | 4.5318 |
| SUBJ087 | 2.9216 | 2.6398 | 3.8322 | 3.6449 | 3.0205 | 2.7721 |
| SUBJ094 | 1.6346 | 1.6200 | 2.8869 | 2.7142 | 1.7310 | 1.3287 |
| SUBJ097 | 3.1465 | 3.0364 | 4.3354 | 4.0965 | 3.2340 | 3.0578 |
| SUBJ100 | 2.0950 | 1.9168 | 3.4563 | 3.3301 | 1.9505 | 1.5719 |
| SUBJ109 | 2.1552 | 2.0676 | 3.7179 | 3.5811 | 2.0158 | 1.6031 |
| SUBJ117 | 2.2009 | 2.0753 | 3.4205 | 3.2416 | 2.0465 | 1.8013 |

## New-load probability

The three Brier contrasts form a second, secondary Holm family with the same labels. A forecast that always gives the prevalence among the 12 earlier fit people (0.03725847908677051) scores 0.034276 on the evaluation group.

Brier score by rung:

| Family | Rows | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | all issue times | 0.033700 | 0.033711 | 0.033739 | 0.033713 | 0.033707 |
| M1, compact recurrent model | 24-position schedule | 0.031209 | 0.031230 | 0.031237 | 0.031217 | 0.031238 |
| M2, ridge and logistic regression | all issue times | 0.033713 | 0.033708 | 0.033718 | 0.033711 | 0.033677 |
| M2, ridge and logistic regression | 24-position schedule | 0.030924 | 0.030876 | 0.030862 | 0.030830 | 0.030816 |
| M3, boosted trees | all issue times | 0.031092 | 0.030448 | 0.029930 | 0.029505 | 0.029278 |
| M3, boosted trees | 24-position schedule | 0.029446 | 0.028861 | 0.028752 | 0.028619 | 0.028451 |

Change from N = 12 to N = 47, all issue times:

| Family | Change | 95% interval | Relative change | 95% interval (relative) | p | Holm p | People with a lower score | Label |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | +0.000007 | −0.000051 to +0.000068 | +0.02% | −0.16% to +0.19% | 0.826 | 0.826 | 12 of 20 | PRACTICALLY NO CHANGE |
| M2, ridge and logistic regression | −0.000036 | −0.000113 to +0.000042 | −0.11% | −0.34% to +0.12% | 0.358 | 0.715 | 14 of 20 | PRACTICALLY NO CHANGE |
| M3, boosted trees | −0.001814 | −0.002428 to −0.001225 | −5.83% | −7.61% to −4.05% | 0.0002 | 0.0006 | 19 of 20 | HELPED |

M3's Brier score fell by 5.83% and is labelled HELPED; it improved for 19 of 20 people. M1 and M2 are labelled PRACTICALLY NO CHANGE: their intervals lie inside −3% to +3%, and at every rung their scores stay within 2% of the constant forecast. The evaluation group holds 118 distinct onsets, so these scores rest on few events.

## Sealed predictions against the observed result

Three predictions of the result at the largest rung were written down before it was scored (protocol section 11):

- **P0, planning prior.** From an earlier study on the fit people alone, for 12 to 49 people. The planning trees used the compact input, so the M3 figure is approximate.
- **P1, pool-tail curve.** Sealed in FIT-COMPLETE.json at stage C3, before any evaluation byte was downloaded. For each draw, the 11 pool people after the largest intermediate rung are unseen by that draw's fits at N = 12 to 36. Those fits were scored on them and the trend forms fitted to the draw-averaged curve.
- **P2, trend prediction.** Sealed in [P2-TREND-PREDICTION.json](P2-TREND-PREDICTION.json) at stage C5. Stage S-b scored only the rungs below 47 on the evaluation group, and the trend forms were fitted to those four rung means, as point predictions and in each of the 10,000 bootstrap resamples.

The trend forms are L + a/sqrt(N) with L at least 0 (primary), c + b log2 N, and carry-forward of the error at N = 36.

Relative change in impulse error from 12 people to the largest rung:

| Family | P0, planning prior (12 to 49 people) | P1, from the training pool (sealed at C3) | P2, primary trend form (sealed at C5) | Observed |
|---|---|---|---|---|
| M1, compact recurrent model | −2.9% | −5.68% | −5.69% | −5.30% |
| M2, ridge and logistic regression | −2.8% | −4.93% | −4.92% | −4.76% |
| M3, boosted trees | −9.7% | −10.19% | −11.38% | −11.07% |

P0 underestimated all three gains, by 2.4, 2.0 and 1.4 percentage points, and it was stated for 49 people, not 47. P1 is a prediction of the error on pool people, not on the evaluation group; its relative changes came within 0.9 percentage points of the observed ones, and those of P2 within 0.4.

P1, pool-tail error (N·s) and its predictions:

| Family | Pool-tail error, N = 12 | Pool-tail error, N = 18 | Pool-tail error, N = 24 | Pool-tail error, N = 36 | Predicted at N = 47, L + a/sqrt(N) | Predicted at N = 47, c + b log2 N | Predicted at N = 47, carry-forward |
|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | 2.3005 | 2.2433 | 2.2343 | 2.1843 | 2.1699 (−5.68%) | 2.1582 (−6.19%) | 2.1843 (−5.05%) |
| M2, ridge and logistic regression | 3.5519 | 3.4758 | 3.4451 | 3.4059 | 3.3768 (−4.93%) | 3.3626 (−5.33%) | 3.4059 (−4.11%) |
| M3, boosted trees | 2.1587 | 2.0878 | 2.0376 | 1.9640 | 1.9387 (−10.19%) | 1.9176 (−11.17%) | 1.9640 (−9.02%) |

P2, fitted parameters and predictions (N·s):

| Family | L | a | c | b | Predicted at N = 47, L + a/sqrt(N) | Predicted at N = 47, c + b log2 N | Predicted at N = 47, carry-forward |
|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | 2.0507 | 0.9331 | 2.5765 | −0.0724 | 2.1868 (−5.69%) | 2.1742 (−6.23%) | 2.1986 (−5.18%) |
| M2, ridge and logistic regression | 3.2621 | 1.2295 | 3.9497 | −0.0942 | 3.4415 (−4.92%) | 3.4263 (−5.34%) | 3.4689 (−4.16%) |
| M3, boosted trees | 1.6629 | 1.7553 | 2.6499 | −0.1357 | 1.9190 (−11.38%) | 1.8960 (−12.44%) | 1.9507 (−9.91%) |

The trend test uses the shared bootstrap: in each resample the form is refitted to the resampled rung means and compared with the error at N = 47 in the same resample. If the 95% interval of observed minus predicted contains zero, the trend held; if it lies wholly above zero, error fell more slowly than predicted; wholly below, faster.

| Family | Trend form | Predicted error at N = 47 | Observed | Observed minus predicted | 95% interval | Reading |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | L + a/sqrt(N) (primary) | 2.1868 | 2.1957 | +0.0089 | +0.0037 to +0.0146 | slower |
| M1, compact recurrent model | c + b log2 N | 2.1742 | 2.1957 | +0.0214 | +0.0153 to +0.0280 | slower |
| M1, compact recurrent model | carry-forward of N = 36 | 2.1986 | 2.1957 | −0.0029 | −0.0114 to +0.0049 | held |
| M2, ridge and logistic regression | L + a/sqrt(N) (primary) | 3.4415 | 3.4474 | +0.0059 | +0.0044 to +0.0075 | slower |
| M2, ridge and logistic regression | c + b log2 N | 3.4263 | 3.4474 | +0.0210 | +0.0189 to +0.0232 | slower |
| M2, ridge and logistic regression | carry-forward of N = 36 | 3.4689 | 3.4474 | −0.0215 | −0.0232 to −0.0198 | faster |
| M3, boosted trees | L + a/sqrt(N) (primary) | 1.9190 | 1.9255 | +0.0066 | −0.0159 to +0.0291 | held |
| M3, boosted trees | c + b log2 N | 1.8960 | 1.9255 | +0.0295 | +0.0061 to +0.0536 | slower |
| M3, boosted trees | carry-forward of N = 36 | 1.9507 | 1.9255 | −0.0251 | −0.0438 to −0.0071 | faster |

For M1 and M2 the primary form was slightly optimistic: error at 47 people was 0.0089 and 0.0059 N·s above its prediction, with intervals that exclude zero. For M3 the primary form held. The logarithmic form predicted too low an error for all three families. Carry-forward held for M1, whose last step is nearly flat, and was too pessimistic for M2 and M3.

Absolute miss of each form (N·s):

| Family | Absolute miss, L + a/sqrt(N) | Absolute miss, c + b log2 N | Absolute miss, carry-forward | Primary form closer than carry-forward |
|---|---|---|---|---|
| M1, compact recurrent model | 0.0089 | 0.0214 | 0.0029 | no |
| M2, ridge and logistic regression | 0.0059 | 0.0210 | 0.0215 | yes |
| M3, boosted trees | 0.0066 | 0.0295 | 0.0251 | yes |

## Controls and frozen published checkpoints

Controls need no fitting on the pool. Frozen checkpoints are models the project had already published (repository commit `03e76d4`); each was scored once, as published, on the same rows (protocol section 8).

- **C1, persistence.** The latest 20 ms mean force held for 100 ms. New-load probability: the prevalence among the 12 earlier fit people.
- **C2, unconditional.** The same prevalence, and the person-weighted median impulse of the 12 earlier fit people.
- **C3, linear trend.** A least-squares line through the last three bin means, integrated over the next 100 ms. Probability as C1.
- **C4, random recurrent readout.** M1 with its convolution and recurrent layers left at their seeded starting values and only the output layer trained, at N = 12 and N = 47, 50 seeds each. It is reported with the secondary arms.
- **F1.** The published three-pass checkpoint of [the walking neural-scaling benchmark](../../benchmarks/walking-neural-scaling/README.md), fitted on the 12 earlier fit people and 8 people recorded in İzmir, with an augmented continuation of training. It differs from M1 in data and in training length, so its comparison is descriptive.
- **F2.** The published tree model of the same benchmark, as ONNX graphs. At N = 12 it is the same model as M3.
- **F3.** The NeuroTranslate 0.0 walking-force preview ([model card](../neurotranslate-0.0/recorded-force/expanded/MODEL-CARD.md)): the past-load gate with trainable core and with frozen core, and the two earlier expanded cores. All were fitted on the 12 earlier fit people and had never been tested on other people.
- **F4.** The published linear [force baselines](../force-baselines/README.md) (`common-six.npz`), fitted on the 12 earlier fit people: EMG only, force only, force and EMG. The published file holds weights for four penalties; for each endpoint and arm the penalty with the lowest person-equal error on the training-pool people was chosen and sealed at C3. This is the separate validation its README asks for.
- **F5.** The NeuroTranslate 0.1 Research Edition. It is optional in the protocol and was not issued in this stage.

Not scored, because they need all 14 muscle names and were fitted on 2 people: the 0.1 Inkling adapter, `strict-fourteen.npz` and the three top-level 0.0 recorded-force checkpoints. Lineage of the scored checkpoints: F1 inherits İzmir data (CC BY 4.0, `10.48623/aperta.286865`), and F3's core inherits training on worm imaging (Zenodo `10.5281/zenodo.19388374`) and SLEAP sample tracks. They were scored only; none of that material enters the ladder's fits.

Impulse error (N·s). Each contrast is the method minus the named fit, as a share of that fit's error, with its 95% interval; a positive value means the fixed method has the higher error:

| Method | Error, all issue times | Error, 24-position schedule | Against M1 at N = 12 | Against M1 at N = 47 | Against M2 at N = 12 | Against M2 at N = 47 | Against M3 at N = 12 | Against M3 at N = 47 |
|---|---|---|---|---|---|---|---|---|
| C1, persistence | 3.5604 | 3.2381 | +53.55% (+47.74% to +59.24%) | +62.15% (+56.90% to +67.31%) | −1.64% (−6.28% to +2.43%) | +3.28% (−1.19% to +7.14%) | +64.43% (+53.23% to +75.48%) | +84.90% (+73.36% to +97.44%) |
| C2, unconditional | 10.6517 | 9.6248 | +359.39% (+330.77% to +388.80%) | +385.12% (+353.06% to +418.39%) | +194.28% (+175.20% to +212.22%) | +208.98% (+189.02% to +228.03%) | +391.92% (+347.74% to +442.17%) | +453.18% (+402.32% to +510.06%) |
| C3, linear trend | 3.9467 | 3.7574 | +70.21% (+60.81% to +79.66%) | +79.75% (+71.20% to +88.06%) | +9.04% (+2.68% to +15.39%) | +14.48% (+8.28% to +20.52%) | +82.27% (+68.40% to +95.50%) | +104.97% (+89.50% to +119.88%) |
| F1 | 1.8099 | 1.6639 | −21.94% (−26.25% to −17.18%) | −17.57% (−21.59% to −13.41%) | −50.00% (−53.74% to −45.96%) | −47.50% (−51.32% to −43.46%) | −16.41% (−21.35% to −11.07%) | −6.00% (−10.38% to −1.83%) |
| F2 | 2.1653 | 2.0409 | −6.61% (−10.79% to −2.40%) | −1.38% (−6.06% to +3.82%) | −40.18% (−44.11% to −35.95%) | −37.19% (−41.29% to −32.71%) | −0.00% (−0.00% to +0.00%) | +12.45% (+8.14% to +17.54%) |
| F3, gate, trainable | 3.3460 | 3.1320 | +44.31% (+39.25% to +49.06%) | +52.39% (+48.44% to +56.26%) | −7.56% (−11.66% to −3.90%) | −2.94% (−6.85% to +0.51%) | +54.53% (+44.19% to +64.64%) | +73.77% (+63.45% to +84.71%) |
| F3, gate, frozen | 3.5385 | 3.2318 | +52.61% (+46.83% to +58.23%) | +61.16% (+55.93% to +66.33%) | −2.24% (−6.85% to +1.75%) | +2.64% (−1.83% to +6.49%) | +63.42% (+52.37% to +74.32%) | +83.77% (+72.30% to +96.31%) |
| F3, expanded, frozen | 10.6723 | 9.6701 | +360.27% (+331.96% to +389.77%) | +386.06% (+353.98% to +419.17%) | +194.84% (+176.07% to +212.58%) | +209.58% (+189.87% to +228.41%) | +392.87% (+348.76% to +443.29%) | +454.25% (+403.65% to +511.46%) |
| F3, expanded, trainable | 10.0999 | 9.1315 | +335.59% (+308.32% to +363.27%) | +359.99% (+329.86% to +391.10%) | +179.03% (+160.67% to +196.29%) | +192.97% (+173.75% to +211.22%) | +366.44% (+324.68% to +413.97%) | +424.52% (+377.08% to +477.69%) |
| F4, EMG only | 17.4080 | 16.8181 | +650.77% (+585.09% to +726.53%) | +692.83% (+616.84% to +776.63%) | +380.93% (+343.46% to +418.95%) | +404.96% (+362.69% to +447.46%) | +703.94% (+625.06% to +800.42%) | +804.06% (+701.97% to +922.29%) |
| F4, force only | 3.6513 | 3.4698 | +57.47% (+51.75% to +63.81%) | +66.29% (+60.08% to +73.36%) | +0.87% (+0.42% to +1.40%) | +5.92% (+4.96% to +6.93%) | +68.63% (+57.35% to +80.67%) | +89.62% (+75.76% to +104.84%) |
| F4, force and EMG | 3.8146 | 3.6515 | +64.52% (+57.87% to +72.40%) | +73.73% (+65.82% to +82.72%) | +5.39% (+2.96% to +8.24%) | +10.65% (+7.65% to +14.02%) | +76.17% (+64.41% to +89.46%) | +98.11% (+82.93% to +114.93%) |

Brier score, with the same contrasts:

| Method | Brier score, all issue times | Brier score, 24-position schedule | Against M1 at N = 12 | Against M1 at N = 47 | Against M2 at N = 12 | Against M2 at N = 47 | Against M3 at N = 12 | Against M3 at N = 47 |
|---|---|---|---|---|---|---|---|---|
| C1, persistence | 0.034276 | 0.031916 | +1.71% (+1.10% to +2.27%) | +1.69% (+1.25% to +2.09%) | +1.67% (+0.56% to +2.69%) | +1.78% (+0.74% to +2.78%) | +10.24% (+6.44% to +14.43%) | +17.07% (+13.03% to +21.67%) |
| C2, unconditional | 0.034276 | 0.031916 | +1.71% (+1.10% to +2.27%) | +1.69% (+1.25% to +2.09%) | +1.67% (+0.56% to +2.69%) | +1.78% (+0.74% to +2.78%) | +10.24% (+6.44% to +14.43%) | +17.07% (+13.03% to +21.67%) |
| C3, linear trend | 0.034276 | 0.031916 | +1.71% (+1.10% to +2.27%) | +1.69% (+1.25% to +2.09%) | +1.67% (+0.56% to +2.69%) | +1.78% (+0.74% to +2.78%) | +10.24% (+6.44% to +14.43%) | +17.07% (+13.03% to +21.67%) |
| F1 | 0.033767 | 0.031454 | +0.20% (−0.21% to +0.59%) | +0.18% (−0.09% to +0.43%) | +0.16% (−0.77% to +1.04%) | +0.27% (−0.60% to +1.11%) | +8.60% (+4.89% to +12.72%) | +15.33% (+11.32% to +19.84%) |
| F2 | 0.031092 | 0.029446 | −7.74% (−11.09% to −4.50%) | −7.76% (−11.09% to −4.55%) | −7.78% (−11.21% to −4.50%) | −7.68% (−11.09% to −4.41%) | −0.00% (−0.00% to +0.00%) | +6.20% (+4.22% to +8.24%) |
| F3, gate, trainable | 0.033820 | 0.031585 | +0.36% (−0.21% to +0.87%) | +0.33% (−0.13% to +0.76%) | +0.32% (−0.64% to +1.24%) | +0.42% (−0.49% to +1.34%) | +8.77% (+5.02% to +12.94%) | +15.51% (+11.44% to +20.00%) |
| F3, gate, frozen | 0.033870 | 0.031556 | +0.51% (−0.24% to +1.22%) | +0.48% (−0.19% to +1.12%) | +0.47% (−0.54% to +1.42%) | +0.57% (−0.42% to +1.51%) | +8.94% (+5.09% to +13.10%) | +15.69% (+11.69% to +20.16%) |
| F3, expanded, frozen | 0.034041 | 0.031673 | +1.01% (+0.21% to +1.76%) | +0.99% (+0.31% to +1.60%) | +0.97% (−0.15% to +2.05%) | +1.08% (−0.04% to +2.15%) | +9.48% (+5.56% to +13.74%) | +16.27% (+12.18% to +20.86%) |
| F3, expanded, trainable | 0.033689 | 0.031433 | −0.03% (−1.09% to +0.88%) | −0.05% (−1.05% to +0.81%) | −0.07% (−1.23% to +1.02%) | +0.03% (−1.18% to +1.13%) | +8.35% (+4.41% to +12.58%) | +15.07% (+11.03% to +19.57%) |
| F4, EMG only | 0.034030 | 0.031694 | +0.98% (+0.30% to +1.61%) | +0.96% (+0.42% to +1.44%) | +0.94% (−0.15% to +1.96%) | +1.05% (+0.00% to +2.06%) | +9.45% (+5.65% to +13.63%) | +16.23% (+12.21% to +20.75%) |
| F4, force only | 0.033830 | 0.031626 | +0.39% (−0.06% to +0.80%) | +0.37% (+0.06% to +0.65%) | +0.35% (−0.63% to +1.28%) | +0.45% (−0.46% to +1.34%) | +8.81% (+5.08% to +12.94%) | +15.55% (+11.53% to +20.05%) |
| F4, force and EMG | 0.033889 | 0.031577 | +0.56% (−0.10% to +1.18%) | +0.54% (+0.01% to +1.02%) | +0.52% (−0.55% to +1.54%) | +0.63% (−0.40% to +1.63%) | +9.00% (+5.21% to +13.15%) | +15.75% (+11.74% to +20.23%) |

- **Persistence against the families.** M1 and M3 are far below persistence at both rungs. M2 cannot be told apart from persistence at either rung (−1.64%, −6.28% to +2.43% at 12 people; +3.28%, −1.19% to +7.14% at 47).
- **F1.** F1 has the lowest impulse error of the families, controls and frozen checkpoints, 1.8099 N·s: 17.57% below M1 at 47 people (−21.59% to −13.41%) and 6.00% below M3 at 47 (−10.38% to −1.83%).
- **F2.** F2 and M3 at 12 people are the same model. Against M3 at 47 people F2's error is 12.45% higher (+8.14% to +17.54%), which is M3's gain seen from the published checkpoint.
- **F3 expanded cores.** Both expanded cores are at the level of the unconditional control (10.6723 and 10.0999 N·s against 10.6517), as on their model card (10.810 and 10.202 N·s on the fit people).
- **F4.** The EMG-only baseline (17.4080 N·s) is worse than the unconditional control. The force-only and force-and-EMG baselines (3.6513 and 3.8146 N·s) are above M2 at both rungs.
- **Brier score.** Among the families, controls and frozen checkpoints, only the tree models M3 and F2 are materially below the constant forecast of 0.034276. Every other one lies between 0.033677 and 0.034276.

### First test of the 0.0 preview on people outside its fitting group

The protocol names one comparison for F3, outside the Holm family: the past-load gate with trainable core minus persistence, on impulse error, on both sets of rows. The gate has lower or higher error than persistence if the 95% interval excludes zero.

| Rows | F3 gate, trainable | C1, persistence | Difference | 95% interval | Relative | 95% interval (relative) | p | People with lower error | Reading |
|---|---|---|---|---|---|---|---|---|---|
| all issue times | 3.3460 | 3.5604 | −0.2144 | −0.2804 to −0.1455 | −6.02% | −7.57% to −4.39% | 0.0002 | 17 of 20 | lower error than persistence |
| 24-position schedule | 3.1320 | 3.2381 | −0.1061 | −0.1987 to −0.0113 | −3.28% | −5.81% to −0.39% | 0.0298 | 14 of 20 | lower error than persistence |

The gate has lower error than persistence on both sets of rows. Its model card reported 3.042 N·s for the gate against 3.422 for persistence on 1,728 forecasts from the 12 people who also supplied its fitting data; on the 20 evaluation people the gap is smaller. Against the families at 47 people the gate's error is 52.39% above M1 (+48.44% to +56.26%) and 73.77% above M3, and it cannot be told apart from M2 (−2.94%, −6.85% to +0.51%).

### Export check of F2 against M3

F2 is the ONNX export of the model that M3 refits at N = 12. Over all 17,888 issued rows the largest difference is 0.011366 N·s for the impulse and 0.00000067 for the probability; 45 rows lie beyond the published impulse tolerance (0.000017 N·s) and 50 beyond the probability tolerance (0.00000026). The protocol set this as a check of the export and not as a stop rule, because the ONNX graphs compare inputs with tree thresholds in 32-bit precision. The person-equal errors of the two agree to the four decimals shown.

### F4 penalties chosen on the training pool

From the grid 0.001, 0.01, 0.1 and 1, sealed in FIT-COMPLETE.json. Impulse: 1 for EMG only and 0.001 for every other arm, including both arms on the rows with an earlier EMG window. New load: 1 for EMG only, 0.001 for force only and 1 for force and EMG; for the new load on the rows with an earlier EMG window, 1 for force and EMG and 0.1 for force and earlier EMG.

## Secondary arms

Secondary arms are reported with intervals, lie outside the corrected families and change no label (protocol section 9). Their intervals are not corrected for the number of comparisons.

- **S1.** M1 with updates scaled to the training rows, round(900 × rows at N / rows at 12). At N = 12, S1 is M1.
- **S3.** M1 at width 96, with updates scaled as in S1.
- **S2.** Each family without EMG (force only).
- **S4.** Each family on a fixed budget of 9,586 rows, drawn by hash from the larger training table. This separates more people from more rows. S4 has no fit at N = 12; its contrast of 47 against 12 uses the family's own 12-person fit, whose table has exactly 9,586 rows.
- **S5.** Boosted trees on the compact input.
- **G9.** Tuned M2 and M3: the M2 penalty from 0.001, 0.01, 0.1 and 1 and the M3 leaf count from 7, 15 and 31, chosen per endpoint by four inner folds of training people.
- **C4.** The random recurrent readout described above.
- **S6.** M1 and M2 at N = 12 and N = 47 with an EMG window that ends 500 ms before the issue; the force history is unchanged.
- **G8.** Variety at N = 47: the 12 earlier fit people plus all 35 pool people with one walk each (19,990 training rows), against the 12 plus the first 11 pool people of draw order 0 with three walks each (18,500 rows).

Arm S7 of the reviewed designs, an ensemble of replicate forecasts, was not run, as the protocol states.

Impulse error (N·s) by rung, the change from 12 to 47 people, the arm against its own family at 47 people (C4 against M1), and the change on the 24-position schedule:

| Arm | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 | 47 against 12 | Arm against its family at N = 47 | 47 against 12, 24-position schedule |
|---|---|---|---|---|---|---|---|---|
| S1, M1 with updates scaled to the rows | 2.3187 | 2.0270 | 1.8351 | 1.6606 | 1.5964 | −31.15% (−33.92% to −28.36%) | −27.29% (−29.64% to −25.05%) | −28.98% (−33.10% to −24.72%) |
| S3, wider M1 (96 units), updates scaled | 1.8851 | 1.7156 | 1.6411 | 1.5637 | 1.5484 | −17.86% (−19.78% to −16.16%) | −29.48% (−31.52% to −27.45%) | −16.20% (−20.62% to −12.33%) |
| S2, M1 without EMG | 2.3639 | 2.2968 | 2.2870 | 2.2532 | 2.2402 | −5.23% (−7.02% to −3.58%) | +2.03% (+0.91% to +3.27%) | −4.91% (−7.76% to −2.19%) |
| S2, M2 without EMG | 3.6173 | 3.5578 | 3.5272 | 3.4904 | 3.4710 | −4.04% (−4.52% to −3.54%) | +0.69% (+0.18% to +1.29%) | −4.49% (−5.17% to −3.90%) |
| S2, M3 without EMG | 2.1389 | 2.0998 | 2.0733 | 1.9992 | 1.9543 | −8.63% (−12.37% to −4.73%) | +1.50% (−0.64% to +3.73%) | −7.95% (−10.71% to −5.17%) |
| S4, M1 on 9,586 rows | not fitted | 2.2837 | 2.2653 | 2.2097 | 2.2218 | −4.18% (−5.47% to −2.99%) | +1.19% (+0.62% to +1.81%) | −3.97% (−6.61% to −1.53%) |
| S4, M2 on 9,586 rows | not fitted | 3.5720 | 3.5326 | 3.5025 | 3.5011 | −3.28% (−3.85% to −2.70%) | +1.56% (+1.31% to +1.88%) | −3.37% (−4.30% to −2.60%) |
| S4, M3 on 9,586 rows | not fitted | 2.1479 | 2.1515 | 2.1142 | 2.1188 | −2.15% (−5.85% to +1.40%) | +10.04% (+8.20% to +11.92%) | −1.31% (−7.24% to +4.37%) |
| S5, trees on the compact input | 2.1657 | 2.1163 | 2.0743 | 2.0115 | 1.9818 | −8.49% (−11.53% to −5.65%) | +2.92% (−0.24% to +6.33%) | −7.19% (−11.09% to −2.91%) |
| G9, tuned M2 | 3.5711 | 3.5129 | 3.4867 | 3.4514 | 3.4339 | −3.84% (−4.52% to −3.19%) | −0.39% (−0.46% to −0.32%) | −4.20% (−5.22% to −3.36%) |
| G9, tuned M3 | 2.1677 | 2.0960 | 2.0245 | 1.9507 | 1.9255 | −11.17% (−14.55% to −7.90%) | +0.00% (+0.00% to +0.00%) | −9.64% (−13.66% to −5.51%) |
| C4, random recurrent readout | 3.5625 | not fitted | not fitted | not fitted | 3.5579 | −0.13% (−0.15% to −0.10%) | +62.04% (+56.84% to +67.23%) | −0.15% (−0.19% to −0.11%) |

Brier score, in the same layout:

| Arm | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 | 47 against 12 | Arm against its family at N = 47 | 47 against 12, 24-position schedule |
|---|---|---|---|---|---|---|---|---|
| S1, M1 with updates scaled to the rows | 0.033700 | 0.033699 | 0.033707 | 0.033679 | 0.033654 | −0.14% (−0.32% to +0.06%) | −0.16% (−0.48% to +0.19%) | −0.66% (−1.24% to −0.18%) |
| S3, wider M1 (96 units), updates scaled | 0.033717 | 0.033714 | 0.033677 | 0.033622 | 0.033529 | −0.56% (−1.07% to −0.03%) | −0.53% (−1.20% to +0.17%) | −1.51% (−2.58% to −0.64%) |
| S2, M1 without EMG | 0.033994 | 0.033994 | 0.033971 | 0.033969 | 0.033966 | −0.08% (−0.16% to −0.02%) | +0.77% (+0.41% to +1.10%) | −0.16% (−0.47% to +0.04%) |
| S2, M2 without EMG | 0.033835 | 0.033824 | 0.033818 | 0.033812 | 0.033807 | −0.08% (−0.15% to −0.03%) | +0.39% (−0.56% to +1.31%) | −0.16% (−0.41% to +0.01%) |
| S2, M3 without EMG | 0.030858 | 0.030486 | 0.030309 | 0.029908 | 0.029801 | −3.43% (−5.29% to −1.63%) | +1.79% (−1.29% to +4.69%) | −1.51% (−5.35% to +2.84%) |
| S4, M1 on 9,586 rows | not fitted | 0.033728 | 0.033715 | 0.033727 | 0.033726 | +0.08% (+0.01% to +0.13%) | +0.06% (−0.07% to +0.19%) | −0.01% (−0.22% to +0.13%) |
| S4, M2 on 9,586 rows | not fitted | 0.033736 | 0.033726 | 0.033748 | 0.033749 | +0.11% (−0.24% to +0.48%) | +0.21% (+0.06% to +0.38%) | −0.47% (−1.55% to +0.46%) |
| S4, M3 on 9,586 rows | not fitted | 0.030695 | 0.030516 | 0.030033 | 0.029760 | −4.28% (−7.04% to −1.71%) | +1.65% (−0.31% to +3.52%) | −4.78% (−12.23% to +3.66%) |
| S5, trees on the compact input | 0.033322 | 0.033216 | 0.033104 | 0.032913 | 0.032927 | −1.19% (−1.91% to −0.41%) | +12.46% (+8.70% to +16.69%) | +0.21% (−2.06% to +2.66%) |
| G9, tuned M2 | 0.033713 | 0.033708 | 0.033718 | 0.033715 | 0.033680 | −0.10% (−0.41% to +0.24%) | +0.01% (−0.12% to +0.16%) | −0.45% (−1.33% to +0.34%) |
| G9, tuned M3 | 0.031092 | 0.030448 | 0.030033 | 0.029505 | 0.029278 | −5.83% (−7.61% to −4.05%) | +0.00% (+0.00% to +0.00%) | −3.38% (−8.94% to +1.94%) |
| C4, random recurrent readout | 0.034142 | not fitted | not fitted | not fitted | 0.034148 | +0.02% (−0.02% to +0.05%) | +1.31% (+0.90% to +1.68%) | −0.01% (−0.14% to +0.08%) |

Each arm against its family at the same rung, impulse error:

| Contrast | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 |
|---|---|---|---|---|---|
| S1 against M1 | same fits | −10.51% (−11.67% to −9.42%) | −18.64% (−20.72% to −16.64%) | −24.47% (−26.81% to −22.24%) | −27.29% (−29.64% to −25.05%) |
| S3 against M1 | −18.70% (−20.80% to −16.67%) | −24.26% (−26.82% to −21.86%) | −27.24% (−29.85% to −24.74%) | −28.88% (−31.18% to −26.65%) | −29.48% (−31.52% to −27.45%) |
| S2 (M1 without EMG) against M1 | +1.95% (+0.48% to +3.69%) | +1.40% (+0.10% to +2.90%) | +1.40% (+0.26% to +2.77%) | +2.49% (+1.18% to +4.04%) | +2.03% (+0.91% to +3.27%) |
| S2 (M2 without EMG) against M2 | −0.06% (−0.51% to +0.40%) | +0.30% (−0.06% to +0.71%) | +0.40% (−0.02% to +0.86%) | +0.62% (+0.13% to +1.21%) | +0.69% (+0.18% to +1.29%) |
| S2 (M3 without EMG) against M3 | −1.22% (−5.33% to +3.01%) | +0.83% (−2.29% to +4.31%) | +2.41% (−0.54% to +5.79%) | +2.49% (+0.24% to +4.80%) | +1.50% (−0.64% to +3.73%) |
| S4 (M1 on 9,586 rows) against M1 | not fitted | +0.82% (+0.43% to +1.24%) | +0.43% (+0.01% to +0.94%) | +0.51% (+0.21% to +0.81%) | +1.19% (+0.62% to +1.81%) |
| S4 (M2 on 9,586 rows) against M2 | not fitted | +0.70% (+0.56% to +0.87%) | +0.55% (+0.43% to +0.68%) | +0.97% (+0.77% to +1.16%) | +1.56% (+1.31% to +1.88%) |
| S4 (M3 on 9,586 rows) against M3 | not fitted | +3.14% (+2.45% to +3.73%) | +6.28% (+5.37% to +7.22%) | +8.38% (+7.47% to +9.41%) | +10.04% (+8.20% to +11.92%) |
| S5 against M3 | +0.02% (−2.37% to +2.48%) | +1.62% (−0.36% to +3.77%) | +2.46% (+0.00% to +5.13%) | +3.12% (+0.26% to +6.21%) | +2.92% (−0.24% to +6.33%) |
| G9 (tuned M2) against M2 | −1.34% (−1.57% to −1.11%) | −0.97% (−1.12% to −0.81%) | −0.76% (−0.88% to −0.63%) | −0.50% (−0.59% to −0.42%) | −0.39% (−0.46% to −0.32%) |
| G9 (tuned M3) against M3 | +0.11% (−1.76% to +2.15%) | +0.64% (+0.41% to +0.90%) | +0.00% (+0.00% to +0.00%) | +0.00% (+0.00% to +0.00%) | +0.00% (+0.00% to +0.00%) |

Each arm against its family at the same rung, Brier score:

| Contrast | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 |
|---|---|---|---|---|---|
| S1 against M1 | same fits | −0.04% (−0.18% to +0.11%) | −0.09% (−0.35% to +0.19%) | −0.10% (−0.42% to +0.24%) | −0.16% (−0.48% to +0.19%) |
| S3 against M1 | +0.05% (−0.35% to +0.48%) | +0.01% (−0.52% to +0.58%) | −0.19% (−0.71% to +0.38%) | −0.27% (−0.94% to +0.44%) | −0.53% (−1.20% to +0.17%) |
| S2 (M1 without EMG) against M1 | +0.87% (+0.40% to +1.32%) | +0.84% (+0.41% to +1.23%) | +0.69% (+0.24% to +1.11%) | +0.76% (+0.32% to +1.17%) | +0.77% (+0.41% to +1.10%) |
| S2 (M2 without EMG) against M2 | +0.36% (−0.61% to +1.29%) | +0.35% (−0.63% to +1.27%) | +0.30% (−0.70% to +1.25%) | +0.30% (−0.69% to +1.25%) | +0.39% (−0.56% to +1.31%) |
| S2 (M3 without EMG) against M3 | −0.75% (−4.15% to +2.27%) | +0.12% (−2.41% to +2.52%) | +1.27% (−1.36% to +3.76%) | +1.37% (−1.57% to +4.24%) | +1.79% (−1.29% to +4.69%) |
| S4 (M1 on 9,586 rows) against M1 | not fitted | +0.05% (+0.03% to +0.06%) | −0.07% (−0.09% to −0.05%) | +0.04% (+0.02% to +0.06%) | +0.06% (−0.07% to +0.19%) |
| S4 (M2 on 9,586 rows) against M2 | not fitted | +0.09% (+0.05% to +0.12%) | +0.02% (−0.07% to +0.11%) | +0.11% (+0.06% to +0.16%) | +0.21% (+0.06% to +0.38%) |
| S4 (M3 on 9,586 rows) against M3 | not fitted | +0.81% (+0.09% to +1.50%) | +1.96% (+1.16% to +2.77%) | +1.79% (+0.47% to +3.03%) | +1.65% (−0.31% to +3.52%) |
| S5 against M3 | +7.17% (+3.56% to +11.23%) | +9.09% (+5.98% to +12.44%) | +10.60% (+7.18% to +14.38%) | +11.55% (+7.89% to +15.65%) | +12.46% (+8.70% to +16.69%) |
| G9 (tuned M2) against M2 | +0.00% (+0.00% to +0.00%) | +0.00% (+0.00% to +0.00%) | +0.00% (+0.00% to +0.00%) | +0.01% (−0.03% to +0.05%) | +0.01% (−0.12% to +0.16%) |
| G9 (tuned M3) against M3 | +0.00% (+0.00% to +0.00%) | +0.00% (+0.00% to +0.00%) | +0.34% (+0.12% to +0.59%) | +0.00% (+0.00% to +0.00%) | +0.00% (+0.00% to +0.00%) |

**Update budget and width (S1, S3).** With updates scaled to the rows, M1's error at 47 people is 1.5964 N·s, 27.29% below M1 (−29.64% to −25.05%); the gap opens with the rung (−10.51% at 18 people). The wider model is 18.70% below M1 already at 12 people, where both take 900 updates, and 29.48% below at 47 (1.5484 N·s). At 47 people both arms are below F1 (1.8099 N·s). The fixed recipe of M1 is therefore limited by its 900 updates and its width more than by the number of people. In S1 and S3 more people and more updates come together, so their changes from 12 to 47 people (−31.15% and −17.86%) do not measure people alone.

**Fixed number of rows (S4).** With 9,586 rows at every rung, M1 and M2 keep most of their gain from 12 to 47 people (−4.18%, −5.47% to −2.99%, and −3.28%, −3.85% to −2.70%). For the trees the gain is not detectable (−2.15%, −5.85% to +1.40%), and S4-M3 falls further behind M3 at each rung, from +3.14% at 18 people to +10.04% at 47. At an equal number of rows M1 and M2 still gain in this setting (uncorrected intervals, no label); for the trees no gain is detectable at an equal number of rows.

**Contribution of EMG (S2).** Without EMG the impulse error at 47 people is 2.03% higher for M1 (+0.91% to +3.27%), 0.69% higher for M2 (+0.18% to +1.29%) and 1.50% higher for M3 (−0.64% to +3.73%). The EMG gain is the force-only error minus the full model's error at the same rung (N·s):

| Family | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 | Change, 47 minus 12 | 95% interval |
|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | +0.0452 | +0.0317 | +0.0315 | +0.0546 | +0.0445 | −0.0007 | −0.0330 to +0.0326 |
| M2, ridge and logistic regression | −0.0023 | +0.0106 | +0.0139 | +0.0214 | +0.0236 | +0.0260 | +0.0166 to +0.0370 |
| M3, boosted trees | −0.0264 | +0.0172 | +0.0489 | +0.0485 | +0.0288 | +0.0552 | −0.0211 to +0.1287 |

The same for the Brier score:

| Family | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 | Change, 47 minus 12 | 95% interval |
|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | +0.000294 | +0.000282 | +0.000232 | +0.000256 | +0.000259 | −0.000035 | −0.000077 to +0.000005 |
| M2, ridge and logistic regression | +0.000121 | +0.000116 | +0.000100 | +0.000101 | +0.000130 | +0.000009 | −0.000071 to +0.000088 |
| M3, boosted trees | −0.000234 | +0.000038 | +0.000379 | +0.000403 | +0.000523 | +0.000757 | +0.000068 to +0.001446 |

The EMG gain is small at every rung. Its change with more people is detectable for M2 on the impulse and for M3 on the Brier score, and not for the others.

**Trees on the compact input (S5).** For the impulse, S5 is close to M3 (+2.92% at 47 people, −0.24% to +6.33%). For the new load it is clearly worse (+12.46%, +8.70% to +16.69%).

**Tuned settings (G9).** Tuned M2 chose the impulse penalty 0.001 in all 32 fits, where the fixed recipe uses 1, and is slightly better for the impulse (−1.34% at 12 people to −0.39% at 47). For the new load it kept the penalty 1 except in 6 of the 10 draws at 36 people and in the fit at 47. Tuned M3 chose 15 leaves for the impulse at 12 people and in 2 of the 10 draws at 18 people, and the recipe's 31 leaves otherwise, so from 24 people on it equals M3; at 18 people it is slightly worse (+0.64%). For the new load it kept the recipe's 7 leaves except in one draw at 24 people. The chosen settings are in the private fit records; the published files carry only the scores.

**Random recurrent readout (C4).** With only the output layer trained, the error stays at the level of persistence at both rungs and does not move with more people (−0.13%), so M1's result needs trained recurrent weights:

| Rung | C4 error | Against M1 at the same rung | Against M2 at the same rung | Against M3 at the same rung |
|---|---|---|---|---|
| N = 12 | 3.5625 | +53.64% (+47.86% to +59.29%) | −1.58% (−6.13% to +2.41%) | +64.52% (+53.32% to +75.56%) |
| N = 47 | 3.5579 | +62.04% (+56.84% to +67.23%) | +3.21% (−1.19% to +7.01%) | +84.77% (+73.20% to +97.36%) |

**Earlier EMG window (S6).** These arms are scored on the 14,288 impulse rows and 14,067 new-load rows where the earlier window is valid (all 20 people and 60 walks), and compared with the standard fits on the same rows. The table also holds the two F4 arms fitted for these rows. Impulse error (N·s):

| Model | Error with the earlier EMG window | Error with EMG up to the issue | Difference | 95% interval | Relative | 95% interval (relative) | p |
|---|---|---|---|---|---|---|---|
| S6, M1 at N = 12 | 2.3985 | 2.3688 | +0.0297 | −0.0018 to +0.0640 | +1.25% | −0.07% to +2.81% | 0.0674 |
| S6, M1 at N = 47 | 2.2551 | 2.2320 | +0.0231 | −0.0016 to +0.0490 | +1.03% | −0.07% to +2.32% | 0.0668 |
| S6, M2 at N = 12 | 3.7104 | 3.7239 | −0.0135 | −0.0313 to +0.0040 | −0.36% | −0.85% to +0.11% | 0.134 |
| S6, M2 at N = 47 | 3.5440 | 3.5526 | −0.0086 | −0.0260 to +0.0086 | −0.24% | −0.72% to +0.25% | 0.329 |
| F4, force and EMG | 3.8546 | 3.9927 | −0.1381 | −0.2414 to −0.0412 | −3.46% | −6.10% to −1.04% | 0.0030 |

Brier score:

| Model | Brier score with the earlier EMG window | Brier score with EMG up to the issue | Difference | 95% interval | Relative | 95% interval (relative) | p |
|---|---|---|---|---|---|---|---|
| S6, M1 at N = 12 | 0.029444 | 0.029502 | −0.000058 | −0.000209 to +0.000095 | −0.20% | −0.80% to +0.30% | 0.446 |
| S6, M1 at N = 47 | 0.029413 | 0.029463 | −0.000049 | −0.000149 to +0.000057 | −0.17% | −0.56% to +0.18% | 0.347 |
| S6, M2 at N = 12 | 0.029301 | 0.029491 | −0.000190 | −0.000519 to +0.000145 | −0.64% | −1.90% to +0.46% | 0.268 |
| S6, M2 at N = 47 | 0.029247 | 0.029435 | −0.000188 | −0.000521 to +0.000144 | −0.64% | −1.90% to +0.46% | 0.273 |
| F4, force and EMG | 0.029359 | 0.029662 | −0.000303 | −0.000953 to +0.000421 | −1.02% | −3.32% to +1.37% | 0.385 |

No change is detectable for M1 or M2 when the EMG window ends 500 ms earlier. Gait rhythm can survive in the earlier window, so the protocol treats this as a timing check and not as a removal of muscle information. The F4 arm with the earlier window has a lower impulse error than its arm with EMG up to the issue (−3.46%, −6.10% to −1.04%). In impulse error neither arm is below persistence on these rows. In Brier score the arm with EMG up to the issue is 0.93% below C1 (−1.29% to −0.61%), and the arm with the earlier window cannot be told apart from it (−1.94%, −4.32% to +0.56%). The two F4 arms against persistence and against the families on the same rows, impulse error and then Brier score:

| Arm | Against C1 | Against M1 at N = 12 | Against M1 at N = 47 | Against M2 at N = 12 | Against M2 at N = 47 | Against M3 at N = 12 | Against M3 at N = 47 |
|---|---|---|---|---|---|---|---|
| F4, force and EMG up to the issue | +6.05% (+1.77% to +11.39%) | +68.55% (+60.31% to +77.41%) | +78.88% (+71.10% to +87.02%) | +7.22% (+4.31% to +10.39%) | +12.39% (+9.23% to +15.91%) | +78.32% (+63.82% to +93.67%) | +103.87% (+87.66% to +120.35%) |
| F4, force and earlier EMG | +2.38% (−1.11% to +5.89%) | +62.72% (+54.87% to +71.65%) | +72.69% (+65.21% to +80.79%) | +3.51% (+0.78% to +6.24%) | +8.50% (+5.66% to +11.41%) | +72.16% (+58.29% to +86.93%) | +96.82% (+80.48% to +113.75%) |

| Arm | Against C1 | Against M1 at N = 12 | Against M1 at N = 47 | Against M2 at N = 12 | Against M2 at N = 47 | Against M3 at N = 12 | Against M3 at N = 47 |
|---|---|---|---|---|---|---|---|
| F4, force and EMG up to the issue | −0.93% (−1.29% to −0.61%) | +0.54% (−0.36% to +1.23%) | +0.68% (+0.03% to +1.19%) | +0.58% (−1.03% to +1.80%) | +0.77% (−0.81% to +1.98%) | +11.97% (+5.99% to +18.34%) | +19.36% (+12.26% to +26.12%) |
| F4, force and earlier EMG | −1.94% (−4.32% to +0.56%) | −0.48% (−3.11% to +2.25%) | −0.35% (−2.88% to +2.34%) | −0.45% (−3.48% to +2.65%) | −0.26% (−3.25% to +2.77%) | +10.82% (+3.80% to +17.66%) | +18.14% (+10.48% to +24.89%) |

**Variety (G8).** With about the same number of rows, one walk from each of 35 pool people against three walks from each of 11:

| Family | Measure | Varied set: 35 pool people, one walk each | Repeated set: 11 pool people, three walks each | Varied minus repeated | Relative | 95% interval (relative) |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | impulse error (N·s) | 2.2374 | 2.2402 | −0.0028 | −0.12% | −1.81% to +1.62% |
| M2, ridge and logistic regression | impulse error (N·s) | 3.4368 | 3.5554 | −0.1187 | −3.34% | −4.01% to −2.65% |
| M3, boosted trees | impulse error (N·s) | 2.0736 | 1.9884 | +0.0852 | +4.28% | +0.98% to +7.44% |
| M1, compact recurrent model | Brier score | 0.033701 | 0.033711 | −0.000010 | −0.03% | −0.18% to +0.11% |
| M2, ridge and logistic regression | Brier score | 0.033607 | 0.033681 | −0.000073 | −0.22% | −0.56% to +0.09% |
| M3, boosted trees | Brier score | 0.029608 | 0.030014 | −0.000406 | −1.35% | −3.60% to +0.72% |

The result is mixed: for the impulse the varied set is better for M2 (−3.34%), worse for M3 (+4.28%) and no different for M1. No Brier difference is detectable.

## The 24-position schedule

The protocol declares a secondary table on the 24-position schedule for every method. The S-c scorer wrote it for the F3 test only; the rest was computed afterwards, in the supplement, from the same sealed forecasts. The rungs' errors on this schedule are in the tables above, and the secondary arms' changes are in the last column of their tables. The success rule applied to these rows, as a description only:

| Family | Change | 95% interval | Relative change | 95% interval (relative) | p | Holm p | People with lower error | Rule applied (descriptive) |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | −0.1118 | −0.1689 to −0.0586 | −5.31% | −8.20% to −2.72% | 0.0002 | 0.0006 | 17 of 20 | HELPED |
| M2, ridge and logistic regression | −0.1717 | −0.1921 to −0.1510 | −5.05% | −6.01% to −4.22% | 0.0002 | 0.0006 | 20 of 20 | HELPED |
| M3, boosted trees | −0.2321 | −0.3345 to −0.1315 | −11.37% | −16.19% to −6.65% | 0.0002 | 0.0006 | 17 of 20 | HELPED |

| Family | Change | 95% interval | Relative change | 95% interval (relative) | p | Holm p | People with a lower score | Rule applied (descriptive) |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | +0.000029 | −0.000076 to +0.000143 | +0.09% | −0.30% to +0.39% | 0.597 | 0.709 | 10 of 20 | PRACTICALLY NO CHANGE |
| M2, ridge and logistic regression | −0.000108 | −0.000302 to +0.000093 | −0.35% | −1.05% to +0.28% | 0.287 | 0.709 | 11 of 20 | PRACTICALLY NO CHANGE |
| M3, boosted trees | −0.000995 | −0.002703 to +0.000565 | −3.38% | −8.94% to +1.94% | 0.236 | 0.709 | 12 of 20 | INCONCLUSIVE |

The impulse changes are close to those on all issue times, with wider intervals from fewer rows; M1's interval now reaches −2.72%. M3's Brier change is not detectable on this schedule, which holds 95 positive rows, and the rule gives INCONCLUSIVE there.

## Subgroups, reliability and ranking

These are descriptive (protocol section 9, S8 and S9). Rows by plate state at the issue and by plate. Pending means that the force has crossed +20 N and the crossing is not yet confirmed. No row was issued with an unknown plate state:

| Subgroup | Issued rows | Impulse rows | New-load rows | Positive rows | Distinct onsets |
|---|---|---|---|---|---|
| plate unloaded at the issue | 14,065 | 13,465 | 13,346 | 579 | 118 |
| plate loaded or pending | 3,823 | 3,823 | 3,694 | 0 | 0 |
| plate state unknown | 0 | 0 | 0 | 0 | 0 |
| plate 1 | 8,944 | 8,644 | 8,518 | 281 | 58 |
| plate 2 | 8,944 | 8,644 | 8,522 | 298 | 60 |

Mean absolute impulse error over rows (N·s), not person-equal:

| Method | Plate unloaded | Plate loaded or pending | Plate 1 | Plate 2 |
|---|---|---|---|---|
| M1 at N = 12 | 0.7879 | 7.1600 | 2.1842 | 2.2099 |
| M1 at N = 47 | 0.7960 | 6.5838 | 2.0511 | 2.1007 |
| M2 at N = 12 | 1.9344 | 8.8822 | 3.4067 | 3.5350 |
| M2 at N = 47 | 1.7366 | 8.7944 | 3.2332 | 3.3615 |
| M3 at N = 12 | 0.6657 | 6.8969 | 2.0020 | 2.0854 |
| M3 at N = 47 | 0.6459 | 5.9245 | 1.8033 | 1.8232 |
| C1, persistence | 0.6584 | 12.7815 | 3.2677 | 3.4109 |
| C2, unconditional | 0.6433 | 44.0248 | 10.0163 | 10.4567 |
| C3, linear trend | 0.7961 | 13.8212 | 3.6301 | 3.7228 |
| F1 | 0.7138 | 5.1375 | 1.6807 | 1.7034 |
| F2 | 0.6657 | 6.8969 | 2.0020 | 2.0854 |
| F3, gate, trainable | 0.8059 | 11.4025 | 3.0740 | 3.2244 |
| F4, force only | 1.9360 | 9.0013 | 3.4333 | 3.5635 |

On rows where the plate is unloaded at the issue, persistence (0.6584) and the unconditional control (0.6433) have lower error than M1 (0.7879 at 12 people, 0.7960 at 47). The fitted models' advantage over persistence lies on rows where the plate is loaded or pending, and so does the gain from more people for M1 and most of it for M3. M2's error on unloaded rows is more than twice that of persistence.

Reliability of the new-load forecasts, in bins of the forecast probability (for M1 the mean over the 50 fits):

| Method | Forecast probability | Rows | Mean forecast | Observed rate of new loads |
|---|---|---|---|---|
| M1 at N = 12 | 0.0 to 0.1 | 16,944 | 0.0393 | 0.0341 |
| M1 at N = 12 | 0.1 to 0.2 | 96 | 0.1089 | 0.0208 |
| M1 at N = 47 | 0.0 to 0.1 | 17,032 | 0.0364 | 0.0340 |
| M1 at N = 47 | 0.1 to 0.2 | 8 | 0.1094 | 0.0000 |
| M2 at N = 12 | 0.0 to 0.1 | 16,170 | 0.0318 | 0.0324 |
| M2 at N = 12 | 0.1 to 0.2 | 849 | 0.1271 | 0.0648 |
| M2 at N = 12 | 0.2 to 0.3 | 21 | 0.2367 | 0.0000 |
| M2 at N = 47 | 0.0 to 0.1 | 16,207 | 0.0291 | 0.0323 |
| M2 at N = 47 | 0.1 to 0.2 | 786 | 0.1282 | 0.0674 |
| M2 at N = 47 | 0.2 to 0.3 | 43 | 0.2277 | 0.0465 |
| M2 at N = 47 | 0.3 to 0.4 | 4 | 0.3191 | 0.0000 |
| M3 at N = 12 | 0.0 to 0.1 | 16,170 | 0.0127 | 0.0231 |
| M3 at N = 12 | 0.1 to 0.2 | 511 | 0.1404 | 0.1722 |
| M3 at N = 12 | 0.2 to 0.3 | 152 | 0.2479 | 0.1908 |
| M3 at N = 12 | 0.3 to 0.4 | 92 | 0.3447 | 0.4022 |
| M3 at N = 12 | 0.4 to 0.5 | 44 | 0.4423 | 0.4091 |
| M3 at N = 12 | 0.5 to 0.6 | 37 | 0.5385 | 0.4865 |
| M3 at N = 12 | 0.6 to 0.7 | 21 | 0.6394 | 0.5238 |
| M3 at N = 12 | 0.7 to 0.8 | 4 | 0.7445 | 0.5000 |
| M3 at N = 12 | 0.8 to 0.9 | 9 | 0.8650 | 0.3333 |
| M3 at N = 47 | 0.0 to 0.1 | 15,958 | 0.0151 | 0.0199 |
| M3 at N = 47 | 0.1 to 0.2 | 620 | 0.1400 | 0.1306 |
| M3 at N = 47 | 0.2 to 0.3 | 186 | 0.2451 | 0.2581 |
| M3 at N = 47 | 0.3 to 0.4 | 112 | 0.3454 | 0.4286 |
| M3 at N = 47 | 0.4 to 0.5 | 84 | 0.4420 | 0.5119 |
| M3 at N = 47 | 0.5 to 0.6 | 41 | 0.5467 | 0.6098 |
| M3 at N = 47 | 0.6 to 0.7 | 18 | 0.6414 | 0.5000 |
| M3 at N = 47 | 0.7 to 0.8 | 21 | 0.7355 | 0.3810 |
| C2, unconditional | 0.0 to 0.1 | 17,040 | 0.0373 | 0.0340 |
| F1 | 0.0 to 0.1 | 17,040 | 0.0397 | 0.0340 |
| F2 | 0.0 to 0.1 | 16,170 | 0.0127 | 0.0231 |
| F2 | 0.1 to 0.2 | 511 | 0.1404 | 0.1722 |
| F2 | 0.2 to 0.3 | 152 | 0.2479 | 0.1908 |
| F2 | 0.3 to 0.4 | 92 | 0.3447 | 0.4022 |
| F2 | 0.4 to 0.5 | 44 | 0.4423 | 0.4091 |
| F2 | 0.5 to 0.6 | 37 | 0.5385 | 0.4865 |
| F2 | 0.6 to 0.7 | 21 | 0.6394 | 0.5238 |
| F2 | 0.7 to 0.8 | 4 | 0.7445 | 0.5000 |
| F2 | 0.8 to 0.9 | 9 | 0.8650 | 0.3333 |
| F3, gate, trainable | 0.0 to 0.1 | 17,022 | 0.0420 | 0.0340 |
| F3, gate, trainable | 0.1 to 0.2 | 18 | 0.1048 | 0.0000 |
| F4, force only | 0.0 to 0.1 | 17,040 | 0.0392 | 0.0340 |

M1's mean forecast never exceeds 0.2, and its few rows above 0.1 have no more new loads than the rest. M2's forecast seldom exceeds 0.2; in its bin from 0.1 to 0.2 the observed rate is about 0.07, half the forecast. M3's forecasts spread up to 0.9 at 12 people and 0.8 at 47. At 47 people its observed rates rise with the forecast up to 0.6; the two bins above 0.6 hold 18 and 21 rows.

Ranking by impulse error on all issue times, with the families at each rung. The ranking lists the families, the controls, the frozen checkpoints and C4. S1 and S3 are not in it; S1 has a lower impulse error than F1 from 36 people on and S3 from 18 people on (at 47 people 1.5964 and 1.5484 N·s against 1.8099):

- **N = 12:** F1 1.8099; F2 2.1653; M3 2.1653; M1 2.3187; F3, gate, trainable 3.3460; F3, gate, frozen 3.5385; C1, persistence 3.5604; C4 3.5625; M2 3.6196; F4, force only 3.6513; F4, force and EMG 3.8146; C3, linear trend 3.9467; F3, expanded, trainable 10.0999; C2, unconditional 10.6517; F3, expanded, frozen 10.6723; F4, EMG only 17.4080.
- **N = 18:** F1 1.8099; M3 2.0826; F2 2.1653; M1 2.2652; F3, gate, trainable 3.3460; F3, gate, frozen 3.5385; M2 3.5472; C1, persistence 3.5604; F4, force only 3.6513; F4, force and EMG 3.8146; C3, linear trend 3.9467; F3, expanded, trainable 10.0999; C2, unconditional 10.6517; F3, expanded, frozen 10.6723; F4, EMG only 17.4080.
- **N = 24:** F1 1.8099; M3 2.0245; F2 2.1653; M1 2.2555; F3, gate, trainable 3.3460; M2 3.5133; F3, gate, frozen 3.5385; C1, persistence 3.5604; F4, force only 3.6513; F4, force and EMG 3.8146; C3, linear trend 3.9467; F3, expanded, trainable 10.0999; C2, unconditional 10.6517; F3, expanded, frozen 10.6723; F4, EMG only 17.4080.
- **N = 36:** F1 1.8099; M3 1.9507; F2 2.1653; M1 2.1986; F3, gate, trainable 3.3460; M2 3.4689; F3, gate, frozen 3.5385; C1, persistence 3.5604; F4, force only 3.6513; F4, force and EMG 3.8146; C3, linear trend 3.9467; F3, expanded, trainable 10.0999; C2, unconditional 10.6517; F3, expanded, frozen 10.6723; F4, EMG only 17.4080.
- **N = 47:** F1 1.8099; M3 1.9255; F2 2.1653; M1 2.1957; F3, gate, trainable 3.3460; M2 3.4474; F3, gate, frozen 3.5385; C4 3.5579; C1, persistence 3.5604; F4, force only 3.6513; F4, force and EMG 3.8146; C3, linear trend 3.9467; F3, expanded, trainable 10.0999; C2, unconditional 10.6517; F3, expanded, frozen 10.6723; F4, EMG only 17.4080.

Ranking by Brier score:

- **N = 12:** F2 0.031092; M3 0.031092; F3, expanded, trainable 0.033689; M1 0.033700; M2 0.033713; F1 0.033767; F3, gate, trainable 0.033820; F4, force only 0.033830; F3, gate, frozen 0.033870; F4, force and EMG 0.033889; F4, EMG only 0.034030; F3, expanded, frozen 0.034041; C4 0.034142; C1, persistence 0.034276; C2, unconditional 0.034276; C3, linear trend 0.034276.
- **N = 18:** M3 0.030448; F2 0.031092; F3, expanded, trainable 0.033689; M2 0.033708; M1 0.033711; F1 0.033767; F3, gate, trainable 0.033820; F4, force only 0.033830; F3, gate, frozen 0.033870; F4, force and EMG 0.033889; F4, EMG only 0.034030; F3, expanded, frozen 0.034041; C1, persistence 0.034276; C2, unconditional 0.034276; C3, linear trend 0.034276.
- **N = 24:** M3 0.029930; F2 0.031092; F3, expanded, trainable 0.033689; M2 0.033718; M1 0.033739; F1 0.033767; F3, gate, trainable 0.033820; F4, force only 0.033830; F3, gate, frozen 0.033870; F4, force and EMG 0.033889; F4, EMG only 0.034030; F3, expanded, frozen 0.034041; C1, persistence 0.034276; C2, unconditional 0.034276; C3, linear trend 0.034276.
- **N = 36:** M3 0.029505; F2 0.031092; F3, expanded, trainable 0.033689; M2 0.033711; M1 0.033713; F1 0.033767; F3, gate, trainable 0.033820; F4, force only 0.033830; F3, gate, frozen 0.033870; F4, force and EMG 0.033889; F4, EMG only 0.034030; F3, expanded, frozen 0.034041; C1, persistence 0.034276; C2, unconditional 0.034276; C3, linear trend 0.034276.
- **N = 47:** M3 0.029278; F2 0.031092; M2 0.033677; F3, expanded, trainable 0.033689; M1 0.033707; F1 0.033767; F3, gate, trainable 0.033820; F4, force only 0.033830; F3, gate, frozen 0.033870; F4, force and EMG 0.033889; F4, EMG only 0.034030; F3, expanded, frozen 0.034041; C4 0.034148; C1, persistence 0.034276; C2, unconditional 0.034276; C3, linear trend 0.034276.

Ranking by impulse error on the 24-position schedule:

- **N = 12:** F1 1.6639; F2 2.0409; M3 2.0409; M1 2.1062; F3, gate, trainable 3.1320; F3, gate, frozen 3.2318; C1, persistence 3.2381; C4 3.2441; M2 3.4024; F4, force only 3.4698; F4, force and EMG 3.6515; C3, linear trend 3.7574; F3, expanded, trainable 9.1315; C2, unconditional 9.6248; F3, expanded, frozen 9.6701; F4, EMG only 16.8181.
- **N = 18:** F1 1.6639; M3 1.9406; F2 2.0409; M1 2.0590; F3, gate, trainable 3.1320; F3, gate, frozen 3.2318; C1, persistence 3.2381; M2 3.3307; F4, force only 3.4698; F4, force and EMG 3.6515; C3, linear trend 3.7574; F3, expanded, trainable 9.1315; C2, unconditional 9.6248; F3, expanded, frozen 9.6701; F4, EMG only 16.8181.
- **N = 24:** F1 1.6639; M3 1.8919; F2 2.0409; M1 2.0477; F3, gate, trainable 3.1320; F3, gate, frozen 3.2318; C1, persistence 3.2381; M2 3.2944; F4, force only 3.4698; F4, force and EMG 3.6515; C3, linear trend 3.7574; F3, expanded, trainable 9.1315; C2, unconditional 9.6248; F3, expanded, frozen 9.6701; F4, EMG only 16.8181.
- **N = 36:** F1 1.6639; M3 1.8298; M1 1.9971; F2 2.0409; F3, gate, trainable 3.1320; F3, gate, frozen 3.2318; C1, persistence 3.2381; M2 3.2510; F4, force only 3.4698; F4, force and EMG 3.6515; C3, linear trend 3.7574; F3, expanded, trainable 9.1315; C2, unconditional 9.6248; F3, expanded, frozen 9.6701; F4, EMG only 16.8181.
- **N = 47:** F1 1.6639; M3 1.8088; M1 1.9944; F2 2.0409; F3, gate, trainable 3.1320; M2 3.2307; F3, gate, frozen 3.2318; C1, persistence 3.2381; C4 3.2393; F4, force only 3.4698; F4, force and EMG 3.6515; C3, linear trend 3.7574; F3, expanded, trainable 9.1315; C2, unconditional 9.6248; F3, expanded, frozen 9.6701; F4, EMG only 16.8181.

By impulse error the order of the families is M3, M1, M2 at every rung on both sets of rows. By Brier score on all issue times M3 is first at every rung; M1 is ahead of M2 at 12 people and M2 is ahead of M1 from 18 people on, each time by less than 0.0001. In impulse error M2 passes persistence between 12 and 18 people on all issue times; on the 24-position schedule it passes persistence only at 47.

## Limits

- **One laboratory, one task.** Healthy adults walking barefoot overground at their preferred speed, one recording protocol. Nothing here speaks for other laboratories, patients, speeds, footwear, tasks, bodies or species.
- **Two plates, vertical force.** Plates 1 and 2 of four cover part of a 12 m walkway, and the forecasts describe those plates only.
- **Selection by channel names.** Only people whose walks carry the six literal EMG names qualified (65 of 80 candidates). If file naming follows the recording period, this is a hidden selection.
- **Surface EMG.** Muscle voltage at the skin, as RMS per 20 ms bin, without filtering or normalisation. It is not a nerve recording.
- **Conditional on these 12 fit people and this pool.** Every rung contains the same 12 people, and the pool is the 35 people the hash order gave. The intervals reflect the sampling of the 20 evaluation people, not the choice of the 12 or of the pool. At 47 people there is one training set.
- **People as the unit.** Neighbouring issue windows overlap, so rows are not independent; all tests resample people. With 20 people and 118 onsets, the new-load results rest on few events.
- **Fixed recipes.** The result concerns these three recipes as fixed in advance, not the best each could do; S1 and S3 show how much M1's level depends on its update budget and width.
- **A short curve.** A trend fitted to four rungs is a short-range extrapolation. It is not a scaling law.
- **Secondary and supplementary tables.** Their intervals are uncorrected. The supplement was computed after the results were known, by code written afterwards.
- **Forecast accuracy only.** The scores measure how well force on a plate is forecast 100 ms ahead. They are not evidence about how the nervous system controls walking.
- **The evaluation group is used.** A method chosen with knowledge of these results cannot treat these 20 people as unseen.

## Custody and the order of events

Each of the protocol's seals (C1 to C5) was committed before the stage that depends on it began; [README-CODE.md](README-CODE.md) gives the commands and records. Commit times are the author times in the commit records; push times are from this machine's record of each push. Three commits also carry a later committer time, from a rebase after D1; the paragraph "Header probe before allocation" below sets this out.

| Event | Time (UTC) | Record |
| --- | --- | --- |
| C1: protocol, pool and hash orders pushed | 11:33:22 | commit `3f2bae7` |
| Fixes from the run-code review committed | 11:54:47 | [DECISIONS.md](DECISIONS.md) items 13 to 17, commit `f5b7103` |
| D1: header probe | 11:55:07 to 12:03:58 | `QUALIFICATION.json`, `receipts/D1-requests.jsonl`, `receipts/D1-walks.jsonl` |
| C2: allocation committed; texts corrected after its review; both pushed | 12:04:59, 12:53:48, 13:04:52 | `ALLOCATION.json`, commits `8a8fab5` and `0fc1bb7` |
| D2: training pool downloaded | 13:08:41 to 13:14:17 | `receipts/D2-RECEIPT.json` |
| Training rows extracted | 13:14:45 | private |
| 1,742 fits | 13:15:28 to 13:47:10 | private |
| P1 computed, F4 penalties chosen, 12-person refits checked | 13:39:28 to 13:51:20 | private |
| C3: fit seal written, committed, pushed | 13:51:31, 13:52:48, 14:03:24 | `FIT-COMPLETE.json`, commit `4652d69` |
| D3: evaluation group downloaded | 14:06:17 to 14:09:36 | `receipts/D3-RECEIPT.json` |
| Evaluation rows extracted, inputs and targets to separate files | 14:09:47 to 14:09:48 | private |
| Forecasts issued | 14:09:58 to 14:53:18 | private |
| C4: forecast seal written, then committed locally | 14:54:10, 14:54:24 | `FORECASTS-SEAL.json`, commit `be66803` |
| S-b: rungs below 47 scored | 14:54:32 | private |
| C5: P2 committed | 14:55:40 | `P2-TREND-PREDICTION.json`, commit `46d27d6` |
| C4 and C5 pushed together | 15:08:44 | |
| S-c: the largest rung, controls, checkpoints and arms scored | 15:11:08 to 15:11:17 | `RESULTS.json` |
| Replay | 15:11:32 to 15:11:34 | private |
| Results file committed | 15:14:37 | `RESULTS.json` |
| Supplement computed | 22:08:28 to 22:08:42 | `RESULTS-SUPPLEMENT.json` |

**Targets.** The extractor decoded the evaluation walks at 14:09:47 and wrote the inputs (keys, histories, input masks) and the targets (labels, impulses, target masks) to two separate private files. It also wrote each walk's counts of rows with a target into a third file, `EVAL-WALKS.json`. The issuing processes opened the input file, and `EVAL-WALKS.json` to check the input file's sha256; they never opened the target file. FORECASTS-SEAL.json says "targets were never opened before this seal", and the message of its commit says the same. That overstates it: the extractor had decoded the targets, and the sealed file cannot be changed. The exact statement is that the extractor decoded the targets and the issuing processes never read them. By the code and the run logs, the first reader of the target file after the extractor was the S-b scorer; no file-access log exists. At the review before S-c, the forecasts of 24 methods (fits of the ladder, controls and published checkpoints) were issued again from the model files and the input file alone and matched the sealed forecasts bit for bit.

**Forecast seal and S-b.** The forecast seal was written at 14:54:10 and committed locally at 14:54:24, 8 s before S-b began, and it became public only with the push at 15:08:44, after S-b. That the seal preceded S-b therefore rests on local records, not on a public time. The protocol asks for C1, C2, C3 and C5 to be pushed before the next stage and does not list C4. S-b reads only the forecasts of the rungs below 47.

**Fit seal, P2 and the public order.** The fit seal, with the F4 penalties and P1, was public at 14:03:24, before the first evaluation byte was requested at 14:06:17. P2 was public at 15:08:44, before S-c began at 15:11:08; the S-c scorer refuses to run unless the committed P2 file has the sha256 it is given.

**Header probe before allocation.** D1 read header bytes of people who later became evaluation people. The hash order that assigns the groups was fixed and published at C1, before the probe, so the verdicts could not steer the roles. D1 ran on fixes for the run-code review that were first committed at 11:54:47, 20 s before it began, and first reviewed at C2. The two fixes that D1 uses ([DECISIONS.md](DECISIONS.md) items 13 and 14) change only the retry and halt paths, and neither path was taken. The time 11:54:47 is the author time of commit `f5b7103`. That commit, the run-code commit before it (`f28ed67`) and the allocation commit after it (`8a8fab5`) also carry a committer time of 12:05:32, after D1 ended at 12:03:58. At 12:05:32 the branch was rebased, that is, its commits were re-applied on top of newer commits of main, none of which changes a file of this folder. The rebase gave the three commits their present ids and that committer time, and left their author times and this folder's content unchanged. The commit as first made at 11:54:47 is recorded only in this machine's branch log, and it was not pushed before D1. That the fixes preceded D1 therefore rests on local records, not on a public time.

**Never read.** This track has read no recording byte of the 12 test people and the 6 validation people of the earlier work, or of the boundary case SUBJ099. Of the 10 physics-source people, the 11 people of the physics supplement and the 4 unusable candidates it has read only the header bytes of D1.

**Replay.** Protocol section 14 asks for an independent replay of every aggregate and of sample rows from each plate. The committed `replay.py` covers the primary impulse aggregates and the sample rows: it recomputed the 300 per-person impulse errors of M1, M2 and M3 at the five rungs with plain loops (largest difference 7.9e-14) and 40 target rows, 20 per plate, from the decoded walks (difference 0). The other aggregates of S-b and S-c were recomputed by separate private checks, which agreed to 6.7e-15 and 5.3e-15, and a second independent replay before this text was written compared 3,318 numbers of RESULTS.json (largest difference 2.5e-10). Those checks are not code in this folder, and the replay records are private.

**Differences from the plan.** The fits ran on 8 single-thread lanes, CPUs 24 to 31, inside the protocol's limit of 12. The private folder holds 1,005,701,390 bytes, above the protocol's estimate of under 0.7 GB ([DECISIONS.md](DECISIONS.md) item 18); this concerns storage only. The protocol's time plan assumed 28 November; every stage up to the final scoring (S-c), and the supplement, ran on 27 November 2026 (UTC). The committed replay covers the primary impulse aggregates and 40 target rows, where protocol section 14 asks for every aggregate; the other aggregates were recomputed by private checks (see Replay, above). F5 was not issued.

## What is published

In this folder: the protocol, the code, the probe and download receipts without signed addresses, the allocation, the three seals (`FIT-COMPLETE.json`, `FORECASTS-SEAL.json`, `P2-TREND-PREDICTION.json`), `RESULTS.json` with the per-person errors by archive code, `RESULTS-SUPPLEMENT.json`, these two results editions and [NOTICE.md](NOTICE.md).

Not yet published: the weights at N = 47 that protocol section 18 lists (the M1 checkpoint of seed 20261124, the M3 trees as ONNX and the M2 coefficients, under CC0 1.0). FIT-COMPLETE.json holds a sha256 for every fit, so a later export can be checked against the seal.

Never published: the recordings, the extracted arrays, the forecasts and the targets (protocol section 17).

## Rerunning and checking

[README-CODE.md](README-CODE.md) gives the command, the runtime, the inputs and the measured time of every stage, and [README-CODE-SIMPLE.md](README-CODE-SIMPLE.md) explains them at more length. From the public files alone a reader can:

1. Check the chain of pins. RESULTS.json names the sha256 of PROTOCOL.json, FIT-COMPLETE.json, FORECASTS-SEAL.json and P2-TREND-PREDICTION.json, and the supplement names that of RESULTS.json; `sha256sum` on the five files must give:

   | File | sha256 |
   | --- | --- |
   | `PROTOCOL.json` | `1768c4df8553095b2cd2a49c8f5297cd507fe90008d240bb3b189e526a447b33` |
   | `FIT-COMPLETE.json` | `7280ea43b4b4ac084e51cc709e7ce6ff059d9fcf49740c6681c852d887bf8b57` |
   | `FORECASTS-SEAL.json` | `98a0b76f7e0eacba02c6014704bd241fbd02ef490e8ca16a3fda1fac124bc2e2` |
   | `P2-TREND-PREDICTION.json` | `e8d1c45724945306a2d9112b9d36009209406e810552215a0b1006112cf951e2` |
   | `RESULTS.json` | `e7cf4061709d035b249bc941b9238b706b964d2bb6e6f286d1150d307f443c1f` |

2. Recompute the three primary contrasts, their intervals and p-values from the per-person errors in RESULTS.json, with the short script under "Checks a reader can repeat" in README-CODE.md.
3. Rebuild the pool, the hash orders and the allocation from the archive's central directory and the probe receipt (the same section).

Everything from the training-pool download onward needs the recordings, which are public under CC0 1.0 and are not redistributed here. The receipts give each walk's byte range in the archive and the sha256 of the bytes received, so the same bytes can be fetched and compared. The fits are deterministic on one thread in the two runtimes of protocol section 16 (A: CPython 3.13.15, torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0; B: CPython 3.12.14, numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0), and FIT-COMPLETE.json lists a sha256 for every fit.

Measured times of this run: the header probe 8 min 51 s, the training-pool download 5 min 36 s, the fits 23 min 38 s (runtime A, 1,450 fits) and 7 min 53 s (runtime B, 292 fits) on 8 CPU lanes, the evaluation download 3 min 19 s, the forecasts 43 min 20 s (runtime A) beside 5 min 2 s (runtime B), and each scoring step under 10 s.

## Sources and terms

The recordings are by Van Criekinge and colleagues: data under CC0 1.0, article under CC BY 4.0. [NOTICE.md](NOTICE.md) gives the citations, what this track did with the data, the lineage of the scored checkpoints and the terms of this folder's own files.
