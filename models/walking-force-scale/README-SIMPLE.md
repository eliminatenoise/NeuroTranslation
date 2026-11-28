# Walking-force quantity ladder: results, Simple edition

[Technical edition](README.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Run code](README-CODE.md) · [Run code, Simple edition](README-CODE-SIMPLE.md) · [Choices left to the code](DECISIONS.md) · [Results file](RESULTS.json) · [Supplement](RESULTS-SUPPLEMENT.json) · [Sources and terms](NOTICE.md)

This is the Simple edition of the results of the walking-force quantity ladder, protocol version 1. It reports the same results as the Technical edition, with the same tables, numbers and limits, in more words. The plan (the protocol) was fixed and published before any new person's recording was read. It named in advance every number that would be reported, and this file reports all of them, whether or not they favour the project's own models.

The numbers come from two files in this folder. [RESULTS.json](RESULTS.json) was written by the scoring program at the last scoring stage. [RESULTS-SUPPLEMENT.json](RESULTS-SUPPLEMENT.json) holds further descriptive tables that were computed afterwards from the same sealed forecasts; it changes no number in RESULTS.json, and section 8 says which tables come from it. If a sentence here and those two files disagree, the files govern. Impulse errors are rounded to four decimals, Brier scores to six and percentages to two. All times are in UTC (Coordinated Universal Time) on 27 November 2026. Sections 1 to 14 have the same order and subjects as the sections of the Technical edition after its summary.

## The results in brief

**What was tested.** The project has published computer models that read the last fifth of a second of measurements from a person's walk and forecast what one force plate in the floor will measure over the next tenth of a second. All of them had learned from the same 12 people. This experiment fitted three fixed recipes on 12, 18, 24, 36 and 47 people from the same laboratory and measured their forecasts on 20 other people whom no model had seen (60 walks, 17,888 forecasts). Only the number of training people changed.

**The main result.** With 47 training people instead of 12, the average forecast error fell for all three recipes: by 5.30% for M1, the project's compact recurrent model (the 95% interval runs from −6.77% to −3.85%), by 4.76% for M2, two straight-line models (−5.42% to −4.07%), and by 11.07% for M3, boosted decision trees (−14.92% to −7.52%). Under the rule fixed in advance, all three get the label HELPED. The plan allowed the statement that the compact model gains from more people only if M1 received this label, and it did. The statement holds for this setting: one laboratory, one walking task, these 12 starting people and this pool of added people.

**Forecasts of a new load.** The models also forecast the chance that a foot is about to land on the plate. Only the decision trees (M3) became better at this with more people (−5.83%, with an interval from −7.61% to −4.05%, HELPED). M1 and M2 are labelled PRACTICALLY NO CHANGE, and both stay within 2% of a forecast that always gives the same number.

**Predictions written down beforehand.** Three predictions of the main result were recorded before it was scored. The planning figure (P0) expected falls of 2.9%, 2.8% and 9.7%. A prediction sealed before the 20 evaluation people were downloaded (P1) came within 0.9 percentage points of each observed fall, and one sealed just before the last step was scored (P2) within 0.4. By the plan's own test, the error at 47 people fell slightly more slowly than the main trend curve predicted for M1 and M2 (by 0.0089 and 0.0059 N·s), and the curve held for M3.

**The 0.0 preview on new people.** The walking-force model of the NeuroTranslate 0.0 preview had never been tested on people outside the 12 it learned from. On the 20 new people its error is 6.02% below that of the simplest control, persistence (−7.57% to −4.39%), on all forecasts, and 3.28% below (−5.81% to −0.39%) on the smaller schedule its model card uses. Its error is still 52.39% above that of M1 fitted on 47 people, and it cannot be told apart from M2 fitted on 47 people.

**What the extra comparisons showed.** M1 is trained for a fixed 900 steps at every size. When the steps grow with the data (arm S1), its error at 47 people is 1.5964 N·s instead of 2.1957, and a wider version (arm S3) reaches 1.5484. So the level of M1's error depends on its fixed training budget and size more than on the number of people. Taking the muscle voltages away raised the error at 47 people by only 2.03% (M1), 0.69% (M2) and 1.50% (M3, where the interval includes zero): most of the forecast comes from the plate's own recent force. These comparisons are outside the corrected tests.

**What the result does not show.** One laboratory, one task, healthy adults, two force plates, and only people whose files name six particular muscle channels. Muscle voltage on the skin (surface EMG) is not a recording from nerves. Every training set contains the same 12 starting people. A curve over five training sizes is not a general law of scaling.

**Two statements in the sealed records that need qualifying.** The program that unpacked the evaluation recordings also computed the correct answers and stored them in a separate file. The forecasting programs never read that file, but a sentence in the sealed forecast record says the answers "were never opened", which is too strong. And the forecast record was committed on the project's computer before the first scoring step but reached the public repository only after it. Section 11 sets out both.

**Not yet published.** The plan lists three fitted models from the largest training size for release. They are not in this folder yet (section 12).

## Words used in these results

- **Force plate**: a flat measuring plate set into the floor. It records how hard a foot pushes on it, 1,000 times per second. This laboratory has four; plates 1 and 2 are used.
- **Newton (N) and newton-second (N·s)**: the newton is the unit of force; a person of 80 kg standing still presses down with about 785 N. A newton-second is force added up over time: 500 N held for 0.1 s gives 50 N·s.
- **Impulse**: force added up over a stretch of time, in N·s. The models forecast the impulse on one plate over the next 100 ms.
- **EMG (surface electromyography)**: the small voltage that working muscles produce, measured with sensors on the skin. It is not a recording from nerves.
- **Walk**: one recorded pass along the laboratory's 12 m walkway. Each person contributes three walks.
- **Issue time and row**: a forecast is made (issued) every 20 ms during a walk, separately for each of the two plates. A row is one forecast for one plate at one issue time.
- **Persistence**: the simplest forecast: the plate's latest force reading stays as it is for the next 100 ms.
- **New load**: the start of a load on a plate that was unloaded, for example a foot arriving on it. The exact rule is in section 1.
- **Impulse error**: the average size of the miss of the impulse forecasts, in N·s, whether the forecast was too high or too low (the mean absolute error). Lower is better.
- **Brier score**: the score of the new-load forecasts: the average of (forecast chance − outcome)², where the outcome is 1 if a new load began and 0 if not. Lower is better; a perfect forecast scores 0.
- **Person-equal**: every person counts the same in an average, however many rows they have.
- **Family or recipe**: a model design with all its settings and its amount of training fixed. The three families are M1, M2 and M3.
- **Rung**: one training-set size, counted in people. The rungs are 12, 18, 24, 36 and 47 people; together they are the "ladder" of the title. N stands for the number of training people, and N_max for the largest rung, 47.
- **Draw**: one fixed way of choosing which pool people join the in-between rungs. There are 10 draws.
- **Seed**: the starting number of a model's random choices. Fitting the same model with different seeds shows how much a result varies by chance.
- **Fit**: one run of training a model on a training set.
- **Evaluation group**: the 20 people on whom the scores are measured. Their recordings were downloaded only after every model had been fitted.
- **Training pool**: the 35 people who were added to the 12 starting people on the higher rungs.
- **Control**: a simple forecast that needs no fitting on the pool, used as a reference point.
- **Frozen checkpoint**: a model file the project had already published. It is scored exactly as it is; no refit replaces it.
- **Secondary arm**: an extra comparison that helps to explain the main result. It is reported with its uncertainty but cannot change a label.
- **95% interval**: a range that shows how much a figure could vary by chance with a different sample of people. Here it comes from a bootstrap.
- **Bootstrap**: a way to measure that uncertainty. The 20 evaluation people are drawn again at random 10,000 times, each time 20 people with repeats allowed, and the figure is recomputed each time. The 95% interval holds the middle 95% of the 10,000 values.
- **p-value**: a number between 0 and 1 that is small when a change of this size would be unlikely to arise by chance alone.
- **Holm correction**: an adjustment for running three tests at once. The smallest of the three p-values is multiplied by 3, the next by 2 and the largest by 1, and no adjusted value may be smaller than the one before it.
- **Label**: one of four verdicts fixed in advance: HELPED, HARMED, PRACTICALLY NO CHANGE or INCONCLUSIVE (section 3).
- **Hash (sha256)**: a fingerprint of a file, written as 64 letters and digits. Any change to the file gives a different fingerprint.
- **Commit and push**: a commit is one saved version of the project's files, made on the project's own computer and named by a short code such as `3f2bae7`. Pushing copies commits to the public repository, where anyone can see them, so a pushed step has a public time.
- **Seal**: a file of fingerprints committed at a fixed point, so that a later change to the sealed files would be noticed.
- **Stages**: the plan's steps have short names. D1, D2 and D3 are the three downloads. C1 to C6 are points where files are committed. S-b and S-c are the two scoring steps. Section 11 lists them with their times.

## 1. What was run

### The recordings

Every recording comes from one public dataset: the healthy adults of Van Criekinge and colleagues, released on figshare (`10.6084/m9.figshare.24192480.v1`) under CC0 1.0, a public-domain dedication. [NOTICE.md](NOTICE.md) gives the full citation of the data and of the article that describes them. The people walked barefoot along a walkway at the speed they preferred. Markers on the body were recorded 100 times per second, and the force plates and the surface EMG 1,000 times per second. The same release also holds recordings of people after a stroke; the project has never accessed them.

### Which people could take part

The archive lists 138 healthy participant codes ([POOL.json](POOL.json)). 58 of them were set aside before any byte of a recording was read:

- 26 that the dataset's authors list as having no force-plate or EMG data;
- the 30 people of the project's earlier work on this dataset: 12 used for fitting, 6 for validation and 12 for testing;
- 1 person who had been used for engineering work;
- 1 boundary case, which has never been opened.

The other 80 were candidates. None of them had been used by the project for anything.

The published models need six particular EMG channels, named `Voltage.LBF`, `Voltage.LERS`, `Voltage.LGAS`, `Voltage.LRF`, `Voltage.LST` and `Voltage.RERS` in the files. Not every file has them: in some, a channel carries a generic label instead. To find out which candidates qualify, stage D1 read only the first 8,704 bytes of each walk's compressed file: 241 walks and 2,097,664 bytes in all. That is enough to read a file's list of channels, and the program stopped unpacking at the end of that list, so it produced no measurement sample.

Each walk received one of three classes. Q6 means the walk passes every check of protocol section 4, including the rule that each of the six names is present once, in volts. QP means it fails only the six-name rule and has at least four voltage channels. X means anything else. A person is Q6 with at least three Q6 walks, and the three lowest-numbered ones are used. The result was 65 Q6 people, 11 QP people and 4 X people ([QUALIFICATION.json](QUALIFICATION.json)). The plan had expected about 67 Q6 people, with a 95% interval of roughly 47 to 77.

### The groups

The 65 qualifying people were divided by a hash order: a sorting of the codes by fingerprint, which nobody can steer. The order was fixed and published before the header check, so the outcome of the check could not influence who went where ([ALLOCATION.json](ALLOCATION.json)).

- **Evaluation group: 20 people.** The scores are measured on them.
- **Physics-source group: 10 people.** They are kept for another part of the project. This experiment never downloads them.
- **Training pool: 35 people.** They are added to the 12 starting people.

The 11 QP people form a physics supplement for that other part of the project; this experiment never opens their recordings.

### The ladder

A rung is a training-set size. The lowest rung is the 12 people on whom the project's published walking-force models were fitted; this text calls them the 12 earlier fit people. The higher rungs add 6, 12, 24 or all 35 pool people, which gives 18, 24, 36 and 47 people. For the three in-between rungs it matters which pool people are added, so this was done in 10 different ways, called draws, each from its own published hash order. Within one draw the rungs are nested: the 18 people are among the 24, and the 24 among the 36. At 12 and at 47 people there is only one possible training set.

Because 65 people qualified and not the 67 of the planning figure, the largest rung is 47 people and not 49.

### The forecasting task

The task is the project's published walking-force task, unchanged (protocol section 6). During each walk a forecast is issued every 20 ms for each of plates 1 and 2. In the files' own numbering, the issue times are the samples t = 199 + 20k of the 1,000-per-second signal, with k = 0, 1, 2 and so on. The models are given the 200 ms before the issue time, cut into ten slices (bins) of 20 ms. For each slice they receive the strength of the voltage on the six EMG channels (its root mean square, RMS) and the average vertical force on the plate. They are not given the body markers, the gait events that the laboratory worked out afterwards, any modelled force, a person's body measurements, the identity of the person, the walk or the laboratory, or the time within the recording.

Two things are forecast:

- **The impulse.** The vertical force on the plate added up over the next 100 ms, in N·s, with its sign.
- **The chance of a new load.** The probability that a new load on the plate begins within the next 100 ms. A plate counts as unloaded after 20 samples in a row between −10 N and +10 N. A new load begins when the force of an unloaded plate rises above +20 N and stays at or above +20 N for the next 19 samples.

### The two scores

The impulse forecasts are scored by the impulse error: the average size of the miss, in N·s. For a sense of scale, an impulse error of 2.2 N·s over 100 ms is the same as being wrong by 22 N on average during that time.

The new-load forecasts are scored by the Brier score: the average of (forecast chance − outcome)². A forecast of 0.03 for a new load that does not come scores 0.0009; the same forecast for one that does come scores 0.9409. New loads are rare (about 3.4% of the rows), so all Brier scores here are small numbers, and small differences between them matter.

For both scores lower is better, and both are person-equal: people count equally; within a person the walks count equally; within a walk the issue times count equally; and at one issue time the plates that are present count equally. All methods are scored on the same rows.

Two sets of rows are reported:

- **All issue times.** Every forecast of every walk. This is the plan's main set, called the full grid in the protocol, and all labels come from it.
- **The 24-position schedule.** A smaller set: 8 groups of 3 issue times in a row per walk, which gives 48 rows per walk for the two plates. The project's published model cards use this schedule, so it is reported for every method as a secondary table.

### The three recipes

Three recipes were fitted at every rung, with the settings fixed in protocol section 7. The protocol calls them families.

- **M1, the compact recurrent model.** A small neural network with 7,634 adjustable numbers (parameters). It reads the ten slices in order through a convolution (kernel 3, width 24) and a recurrent layer of the GRU type, then applies one shared GRU cell three times and ends in a linear output. Each fit takes 900 training steps (updates) of 128 rows, at every rung. Because a neural network starts from random numbers, it was fitted 50 times per rung: with 50 seeds at 12 and at 47 people, and with 10 draws of 5 seeds at the rungs between. Each person's error is first averaged over the 50 fits, and only then are people compared. M1 receives the compact input: per slice the plate's force and two summaries, across the available channels, of how the EMG has changed within the window. The channel names are not used.
- **M2, ridge and logistic regression.** Two straight-line models: ridge regression (penalty 1) for the impulse and logistic regression (C = 1) for the new load. They use the compact input laid out flat with a few summaries, 61 columns. Fitting them again on the same data gives the same result, so there is one fit per training set.
- **M3, boosted trees.** Many small decision trees fitted one after another (histogram gradient boosting, 128 rounds), on the published tree input: 185 columns holding, per slice, the six EMG values and the force on both plates, with summaries. One fit per training set.

All three forecast the impulse as a correction to persistence, that is, to the latest 20 ms average force held for 100 ms.

The 12-person rung is this experiment's own refit of the 12 earlier fit people with the same recipe. It is not one of the published model files; those are scored separately in section 6. A private check after the fits found that the refit reproduces the earlier sealed 12-person models exactly: the first three M1 seeds gave files with the fingerprints pinned in PROTOCOL.json, and M2 and M3 gave forecasts identical in every bit on the 9,586 training rows.

### The fits

In all, 1,742 fits were made ([FIT-COMPLETE.json](FIT-COMPLETE.json) lists each with a fingerprint): 250 for M1, 32 each for M2 and M3, and 1,428 for the control C4 and the secondary arms of section 7. None failed. Every saved fit was loaded again and gave identical forecasts.

## 2. Counts

The evaluation group has 20 people and 60 walks, from one site and one task. All 20 people can be scored for the impulse. All 20 can also be scored for the new load, which needs a person to have rows of both outcomes. The plan's floors, below which a result would only be described and not labelled, were 12 people for the impulse and 10 for the new load, so both are met.

There are 17,888 issued rows, 8,944 per plate. 17,288 of them have an impulse target and 17,040 a new-load outcome. 579 of the outcomes are positive (a new load began within 100 ms). Several neighbouring rows can see the same new load coming, and the 579 positive rows belong to 118 separate new loads (onsets). On the 24-position schedule there are 2,880 impulse rows and 2,863 new-load rows, of which 95 are positive, from 41 separate onsets.

The training sets by rung. Where a rung has 10 draws, the table gives the mean over the draws with the smallest and largest value in parentheses:

| Training people | Training sets | Walks | Issue rows | Impulse rows | New-load rows | Positive rows | Distinct onsets |
|---|---|---|---|---|---|---|---|
| 12 | 1 | 36 | 9,946 | 9,586 | 9,150 | 324 | 67 |
| 18 | 10 | 54 | 15,303 (14,604 to 16,152) | 14,763 (14,064 to 15,612) | 14,250 (13,552 to 15,095) | 497.0 (481 to 504) | 102.3 (100 to 103) |
| 24 | 10 | 72 | 20,793 (20,196 to 21,472) | 20,073 (19,476 to 20,752) | 19,481 (18,885 to 20,153) | 672.4 (658 to 681) | 138.1 (136 to 139) |
| 36 | 10 | 108 | 31,797 (31,144 to 32,344) | 30,717 (30,064 to 31,264) | 29,969 (29,320 to 30,511) | 1,017.6 (1,012 to 1,024) | 208.6 (208 to 210) |
| 47 | 1 | 141 | 42,030 | 40,620 | 39,729 | 1,339 | 274 |

Fits and training steps by rung. M1 takes the same 900 updates at every rung. S1 and S3 are the two secondary arms whose updates grow with the number of training rows (section 7):

| Training people | M1 fits | M1 updates per fit | M1 examples drawn per fit | S1 and S3 updates per fit | S1 and S3 examples drawn per fit | M2 fits | M3 fits |
|---|---|---|---|---|---|---|---|
| 12 | 50 | 900 | 115,200 | 900 | 115,200 | 1 | 1 |
| 18 | 50 | 900 | 115,200 | 1,320 to 1,466 | 168,960 to 187,648 | 10 | 10 |
| 24 | 50 | 900 | 115,200 | 1,829 to 1,948 | 234,112 to 249,344 | 10 | 10 |
| 36 | 50 | 900 | 115,200 | 2,823 to 2,935 | 361,344 to 375,680 | 10 | 10 |
| 47 | 50 | 900 | 115,200 | 3,814 | 488,192 | 1 | 1 |

## 3. Impulse error against the number of training people

### The rule fixed in advance

The plan's success rule (protocol section 10) has three main tests of equal rank, one per family. Each compares the impulse error at 47 people with the error at 12 people, on all issue times.

1. For each of the 20 evaluation people, take the family's error at 47 people minus its error at 12 people. A negative number means the error fell for that person.
2. Average the 20 differences. This is the change. Divided by the average error at 12 people, it is the relative change, in percent.
3. Measure the uncertainty with the bootstrap: 10,000 redraws of the 20 people. This gives a 95% interval for the change and for the relative change, and a two-sided p-value.
4. Adjust the three p-values with the Holm correction, so that the chance of any false alarm among the three tests stays at 5%.
5. Give a label, checking in this order. HARMED: the adjusted p is below 0.05 and the error rose. HELPED: the adjusted p is below 0.05, the error fell, and the relative change is −3% or better. PRACTICALLY NO CHANGE: the 95% interval of the relative change lies inside −3% to +3%. INCONCLUSIVE: anything else.

The 3% line was set at about twice the seed-to-seed spread of the published three-pass curve. The planning study had projected about 3% for M1, right on the line, and the protocol said in advance that M1 might well end as practically no change or inconclusive.

### The curves

Impulse error (N·s) by rung, on both sets of rows:

| Family | Rows | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | all issue times | 2.3187 | 2.2652 | 2.2555 | 2.1986 | 2.1957 |
| M1, compact recurrent model | 24-position schedule | 2.1062 | 2.0590 | 2.0477 | 1.9971 | 1.9944 |
| M2, ridge and logistic regression | all issue times | 3.6196 | 3.5472 | 3.5133 | 3.4689 | 3.4474 |
| M2, ridge and logistic regression | 24-position schedule | 3.4024 | 3.3307 | 3.2944 | 3.2510 | 3.2307 |
| M3, boosted trees | all issue times | 2.1653 | 2.0826 | 2.0245 | 1.9507 | 1.9255 |
| M3, boosted trees | 24-position schedule | 2.0409 | 1.9406 | 1.8919 | 1.8298 | 1.8088 |

The error falls at every step for all three families. The trees (M3) have the lowest error at every rung, M1 comes next, and the straight-line models (M2) are well above both.

### The main test

Change from 12 to 47 people, all issue times, in N·s. "People with lower error" counts the evaluation people whose own error fell:

| Family | Change | 95% interval | Relative change | 95% interval (relative) | p | Holm p | People with lower error | Label |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | −0.1230 | −0.1532 to −0.0945 | −5.30% | −6.77% to −3.85% | 0.0002 | 0.0006 | 20 of 20 | HELPED |
| M2, ridge and logistic regression | −0.1723 | −0.1852 to −0.1605 | −4.76% | −5.42% to −4.07% | 0.0002 | 0.0006 | 20 of 20 | HELPED |
| M3, boosted trees | −0.2398 | −0.3128 to −0.1669 | −11.07% | −14.92% to −7.52% | 0.0002 | 0.0006 | 18 of 20 | HELPED |

All three families are labelled HELPED.

- **The p-values.** In none of the 10,000 redraws was the change zero or positive. Each p-value is therefore the smallest this bootstrap can give, 2 divided by 10,001, shown as 0.0002. The Holm correction multiplies the first of the three by 3, which gives 0.0006. The other two would be multiplied by 2 and by 1; they are raised to 0.0006 as well, because no adjusted value may be smaller than the one before it.
- **The size.** The rule asks that the estimated relative change be −3% or better. Beyond what the rule asks, each 95% interval of the relative change lies wholly below −3%.
- **The people.** The error fell for all 20 evaluation people with M1 and with M2. With M3 it fell for 18 of the 20 and rose for two, SUBJ059 and SUBJ078.
- **The compact model.** The protocol allowed the statement that the NeuroTranslate compact model gains from more people only if M1 was labelled HELPED. It was; RESULTS.json records this as `compact_model_claim_allowed` set to true. The statement holds for this setting: these 12 fit people, this pool, this laboratory and task, and a fixed 900 updates.
- **The shape of M1's curve.** M1's error fell from 2.3187 N·s at 12 people to 2.1986 at 36 and 2.1957 at 47. Its last step is nearly flat. The label rests on the comparison of 12 with 47 people only, and says nothing about what a further step would bring.

### Further figures for the same comparison

| Family | Error at N = 12 | SD of per-person differences | Smallest detectable change, 5% level | Smallest detectable change, first Holm step | Sensitivity interval (relative) | Slope per doubling | Gain per doubling, 12 to 24 | Gain per doubling, 24 to 47 |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | 2.3187 | 0.0688 | 1.86% | 2.15% | −6.88% to −3.81% | −0.0642 | −0.0631 | −0.0617 |
| M2, ridge and logistic regression | 3.6196 | 0.0289 | 0.50% | 0.58% | −5.42% to −4.07% | −0.0861 | −0.1063 | −0.0680 |
| M3, boosted trees | 2.1653 | 0.1700 | 4.92% | 5.68% | −14.92% to −7.52% | −0.1244 | −0.1408 | −0.1020 |

- **SD of per-person differences.** The spread (standard deviation) of the 20 per-person changes. For M1 it was 0.0688 N·s, where the planning study had assumed 0.19 N·s. The people agreed with each other more than expected, which is why the intervals are narrow.
- **Smallest detectable change.** The smallest relative change that an experiment with this spread and 20 people would find in 80 of 100 repetitions, at the ordinary 5% level and at the strictest level of the Holm correction. It was below 3% for M1 and M2. For M3 it was 4.92% at the ordinary level and 5.68% at the strictest Holm level, against an observed change of 11.07%.
- **Sensitivity interval.** A second bootstrap that redraws the people and then, for each person, the replicate fits. M2 and M3 have one fit at each of the two rungs, so for them it equals the main interval. For M1 it is slightly wider.
- **Slope and gain per doubling.** The slope is that of a straight line through the rung means against the base-2 logarithm of N, so it is the fall in error for each doubling of the number of people. The last two columns give the gain per doubling separately for the lower half of the ladder (12 to 24 people) and the upper half (24 to 47).

These figures are descriptive.

### Each evaluation person

Impulse error (N·s) of each evaluation person, by archive code. The errors of SUBJ080 are about twice those of the others under every family:

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

## 4. New-load probability

The three Brier-score comparisons form a second group of three tests with the same correction and the same labels. The protocol ranks this group as secondary.

A useful reference is a forecast that gives the same number for every row: the share of positive rows among the 12 earlier fit people, 0.03725847908677051. On the evaluation group this constant forecast scores 0.034276. A model has to beat that figure to show that it knows when a new load is coming.

Brier score by rung:

| Family | Rows | N = 12 | N = 18 | N = 24 | N = 36 | N = 47 |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | all issue times | 0.033700 | 0.033711 | 0.033739 | 0.033713 | 0.033707 |
| M1, compact recurrent model | 24-position schedule | 0.031209 | 0.031230 | 0.031237 | 0.031217 | 0.031238 |
| M2, ridge and logistic regression | all issue times | 0.033713 | 0.033708 | 0.033718 | 0.033711 | 0.033677 |
| M2, ridge and logistic regression | 24-position schedule | 0.030924 | 0.030876 | 0.030862 | 0.030830 | 0.030816 |
| M3, boosted trees | all issue times | 0.031092 | 0.030448 | 0.029930 | 0.029505 | 0.029278 |
| M3, boosted trees | 24-position schedule | 0.029446 | 0.028861 | 0.028752 | 0.028619 | 0.028451 |

Change from 12 to 47 people, all issue times:

| Family | Change | 95% interval | Relative change | 95% interval (relative) | p | Holm p | People with a lower score | Label |
|---|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | +0.000007 | −0.000051 to +0.000068 | +0.02% | −0.16% to +0.19% | 0.826 | 0.826 | 12 of 20 | PRACTICALLY NO CHANGE |
| M2, ridge and logistic regression | −0.000036 | −0.000113 to +0.000042 | −0.11% | −0.34% to +0.12% | 0.358 | 0.715 | 14 of 20 | PRACTICALLY NO CHANGE |
| M3, boosted trees | −0.001814 | −0.002428 to −0.001225 | −5.83% | −7.61% to −4.05% | 0.0002 | 0.0006 | 19 of 20 | HELPED |

M3's Brier score fell by 5.83%, it improved for 19 of 20 people, and it is labelled HELPED. M1 and M2 are labelled PRACTICALLY NO CHANGE: their intervals lie inside −3% to +3%. At every rung their scores stay within 2% of the constant forecast, so M1 and M2 hardly forecast new loads at all, with 12 people or with 47. The evaluation group holds 118 separate onsets, so every Brier result here rests on few events.

## 5. Predictions sealed beforehand, against the observed result

A result is more convincing when it was predicted before it was known. The protocol (section 11) therefore had three predictions of the error at the largest rung written down before that rung was scored:

- **P0, the planning figure.** From an earlier study on the 12 fit people alone, for a step from 12 to 49 people. The trees in that study used the compact input, so its figure for M3 is approximate.
- **P1, from the training pool.** In each draw, the 11 pool people who come after the largest in-between rung were not used by that draw's fits at 12 to 36 people. Those fits were scored on these 11 people, which gives an error curve from pool people only. A trend curve was fitted to it and read off at 47 people. P1 was sealed in FIT-COMPLETE.json at stage C3, before any byte of the evaluation group was downloaded.
- **P2, from the lower rungs of the evaluation group.** The first scoring step, S-b, scored only the rungs below 47 on the evaluation group. Trend curves were fitted to those four rung means and read off at 47 people, for the point prediction and in each of the 10,000 bootstrap redraws. P2 was sealed in [P2-TREND-PREDICTION.json](P2-TREND-PREDICTION.json) at stage C5. Only then did the second scoring step, S-c, score the largest rung.

Three trend forms were used. The primary form is L + a/sqrt(N): the error approaches a floor L as the number of people N grows, with L at least 0. The second is c + b log2 N: the error falls by the same amount b with every doubling of N. The third is carry-forward: the error at 47 people is predicted to equal the error at 36.

Relative change in impulse error from 12 people to the largest rung, predicted and observed:

| Family | P0, planning prior (12 to 49 people) | P1, from the training pool (sealed at C3) | P2, primary trend form (sealed at C5) | Observed |
|---|---|---|---|---|
| M1, compact recurrent model | −2.9% | −5.68% | −5.69% | −5.30% |
| M2, ridge and logistic regression | −2.8% | −4.93% | −4.92% | −4.76% |
| M3, boosted trees | −9.7% | −10.19% | −11.38% | −11.07% |

P0 underestimated all three gains, by 2.4, 2.0 and 1.4 percentage points, and it was stated for 49 people, not 47. P1 predicts the error on pool people, not on the evaluation group; its relative changes came within 0.9 percentage points of the observed ones. Those of P2 came within 0.4.

P1 in full: the error on the pool people by rung (N·s) and the prediction of each form for 47 people, with the relative change from 12 people in parentheses:

| Family | Pool-tail error, N = 12 | Pool-tail error, N = 18 | Pool-tail error, N = 24 | Pool-tail error, N = 36 | Predicted at N = 47, L + a/sqrt(N) | Predicted at N = 47, c + b log2 N | Predicted at N = 47, carry-forward |
|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | 2.3005 | 2.2433 | 2.2343 | 2.1843 | 2.1699 (−5.68%) | 2.1582 (−6.19%) | 2.1843 (−5.05%) |
| M2, ridge and logistic regression | 3.5519 | 3.4758 | 3.4451 | 3.4059 | 3.3768 (−4.93%) | 3.3626 (−5.33%) | 3.4059 (−4.11%) |
| M3, boosted trees | 2.1587 | 2.0878 | 2.0376 | 1.9640 | 1.9387 (−10.19%) | 1.9176 (−11.17%) | 1.9640 (−9.02%) |

P2 in full: the fitted numbers of the two curves and the prediction of each form (N·s):

| Family | L | a | c | b | Predicted at N = 47, L + a/sqrt(N) | Predicted at N = 47, c + b log2 N | Predicted at N = 47, carry-forward |
|---|---|---|---|---|---|---|---|
| M1, compact recurrent model | 2.0507 | 0.9331 | 2.5765 | −0.0724 | 2.1868 (−5.69%) | 2.1742 (−6.23%) | 2.1986 (−5.18%) |
| M2, ridge and logistic regression | 3.2621 | 1.2295 | 3.9497 | −0.0942 | 3.4415 (−4.92%) | 3.4263 (−5.34%) | 3.4689 (−4.16%) |
| M3, boosted trees | 1.6629 | 1.7553 | 2.6499 | −0.1357 | 1.9190 (−11.38%) | 1.8960 (−12.44%) | 1.9507 (−9.91%) |

### The trend test

The protocol tests each prediction with the same bootstrap as the main result. In each of the 10,000 redraws, the form is fitted again to the redrawn rung means and compared with the error at 47 people in the same redraw. The reading follows from the 95% interval of observed minus predicted. If it contains zero, the trend held. If it lies wholly above zero, the error fell more slowly than predicted. If it lies wholly below zero, it fell faster.

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

- **Primary form.** For M1 and M2 it was slightly optimistic: the error at 47 people was 0.0089 and 0.0059 N·s above the prediction, and both intervals exclude zero. These misses are small against errors of 2.1957 and 3.4474 N·s. For M3 the primary form held.
- **Logarithmic form.** It predicted too low an error for all three families. The curves flatten more than a fixed gain per doubling would give.
- **Carry-forward.** It held for M1, whose last step is nearly flat. For M2 and M3 it was too pessimistic: their error still fell from 36 to 47 people.

Absolute miss of each form (N·s), and whether the primary form came closer than carry-forward:

| Family | Absolute miss, L + a/sqrt(N) | Absolute miss, c + b log2 N | Absolute miss, carry-forward | Primary form closer than carry-forward |
|---|---|---|---|---|
| M1, compact recurrent model | 0.0089 | 0.0214 | 0.0029 | no |
| M2, ridge and logistic regression | 0.0059 | 0.0210 | 0.0215 | yes |
| M3, boosted trees | 0.0066 | 0.0295 | 0.0251 | yes |

## 6. Controls and frozen published checkpoints

Controls are simple forecasts that need no fitting on the pool. Frozen checkpoints are model files that the project had already published (at repository commit `03e76d4`). Each was scored once, exactly as published, on the same rows as the fitted families (protocol section 8).

- **C1, persistence.** The plate's latest 20 ms average force is held for 100 ms. For the new load it gives the constant 0.03725847908677051, the share of positive rows among the 12 earlier fit people.
- **C2, unconditional.** The same constant, and for the impulse always the same value: the person-weighted median impulse of the 12 earlier fit people. It ignores the input altogether.
- **C3, linear trend.** A straight line through the last three slice averages of the force, continued over the next 100 ms. For the new load, the constant of C1.
- **C4, random recurrent readout.** M1 with its convolution and recurrent layers left at their random starting values; only the output layer is trained. It was fitted at 12 and at 47 people with 50 seeds each. It is reported in section 7.
- **F1.** The published three-pass model file of [the walking neural-scaling benchmark](../../benchmarks/walking-neural-scaling/README.md). It was fitted on the 12 earlier fit people and on 8 people recorded in İzmir, and its training was continued with augmented data. It differs from M1 in its data and in the length of its training, so its comparison is descriptive.
- **F2.** The published tree model of the same benchmark, stored in the ONNX file format. At 12 people it is the same model as M3.
- **F3.** The walking-force models of the NeuroTranslate 0.0 preview ([model card](../neurotranslate-0.0/recorded-force/expanded/MODEL-CARD.md)). There are four: the past-load gate with a trainable core, the same gate with a frozen core, and two earlier expanded cores. All were fitted on the 12 earlier fit people and had never been tested on other people.
- **F4.** The published linear [force baselines](../force-baselines/README.md) (`common-six.npz`), fitted on the 12 earlier fit people, in three versions: EMG only, force only, and force and EMG. The published file holds each version at four strengths of a penalty setting, and its README asks that one be chosen on separate recordings. That was done here: for each score and version, the penalty with the lowest person-equal error on the training-pool people was chosen and sealed at C3, before the evaluation group was downloaded.
- **F5.** The NeuroTranslate 0.1 Research Edition. The protocol made it optional. It was not issued in this stage.

Some published model files were not scored because they need all 14 muscle names and were fitted on 2 people: the 0.1 Inkling adapter, `strict-fourteen.npz` and the three top-level 0.0 recorded-force checkpoints.

The scored checkpoints carry data from elsewhere. F1 inherits recordings from İzmir (CC BY 4.0, `10.48623/aperta.286865`). The core of F3 inherits training on worm imaging (Zenodo `10.5281/zenodo.19388374`) and on SLEAP sample tracks. These files were scored only. None of that material enters the fits of this experiment.

Impulse error (N·s). The first two number columns give the method's own error on the two sets of rows. Each later column compares the method with one of the fitted families: the method's error minus the fit's error, as a share of the fit's error, with the 95% interval. A positive value means the fixed method has the higher error:

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

Brier score, in the same layout:

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

- **Persistence and the families.** M1 and M3 are far below persistence at both rungs. M2 cannot be told apart from persistence at either rung: the difference is −1.64% at 12 people (−6.28% to +2.43%) and +3.28% at 47 (−1.19% to +7.14%), and both intervals include zero.
- **F1.** Of the families, controls and frozen checkpoints, F1 has the lowest impulse error, 1.8099 N·s. That is 17.57% below M1 at 47 people (−21.59% to −13.41%) and 6.00% below M3 at 47 people (−10.38% to −1.83%). F1 saw a second laboratory and longer training, so this does not show what caused its advantage.
- **F2.** F2 and M3 at 12 people are the same model. Against M3 at 47 people, F2's error is 12.45% higher (+8.14% to +17.54%). This is M3's gain from more people, seen from the published model file.
- **The expanded cores of F3.** Both are at the level of the unconditional control: 10.6723 and 10.0999 N·s against 10.6517. Their model card reported the same picture on the fit people (10.810 and 10.202 N·s).
- **F4.** The EMG-only baseline (17.4080 N·s) is worse than the unconditional control, which uses no input at all. The force-only and the force-and-EMG baselines (3.6513 and 3.8146 N·s) are above M2 at both rungs.
- **Brier score.** Among the families, controls and frozen checkpoints, only the tree models M3 and F2 are clearly below the constant forecast of 0.034276. Every other one lies between 0.033677 and 0.034276.

### First test of the 0.0 preview on people outside its fitting group

The protocol names one comparison for F3, outside the corrected tests: the impulse error of the past-load gate with trainable core minus that of persistence, on both sets of rows. The gate has lower or higher error than persistence if the 95% interval excludes zero; otherwise there is no detectable difference.

| Rows | F3 gate, trainable | C1, persistence | Difference | 95% interval | Relative | 95% interval (relative) | p | People with lower error | Reading |
|---|---|---|---|---|---|---|---|---|---|
| all issue times | 3.3460 | 3.5604 | −0.2144 | −0.2804 to −0.1455 | −6.02% | −7.57% to −4.39% | 0.0002 | 17 of 20 | lower error than persistence |
| 24-position schedule | 3.1320 | 3.2381 | −0.1061 | −0.1987 to −0.0113 | −3.28% | −5.81% to −0.39% | 0.0298 | 14 of 20 | lower error than persistence |

The gate has lower error than persistence on both sets of rows: by 6.02% on all issue times and by 3.28% on the 24-position schedule, where the interval comes close to zero (−5.81% to −0.39%). Its model card had reported 3.042 N·s for the gate against 3.422 N·s for persistence, on 1,728 forecasts from the 12 people who also supplied its fitting data. On the 20 new people the gap is smaller. Compared with the families at 47 people, the gate's error is 52.39% above M1 (+48.44% to +56.26%) and 73.77% above M3, and it cannot be told apart from M2 (−2.94%, with an interval from −6.85% to +0.51%).

### Export check of F2 against M3

F2 is the ONNX export of the model that M3 refits at 12 people, so the two should give the same forecasts. Over all 17,888 issued rows the largest difference is 0.011366 N·s for the impulse and 0.00000067 for the probability. 45 rows lie beyond the published tolerance for the impulse (0.000017 N·s) and 50 beyond the tolerance for the probability (0.00000026). The protocol set this as a check of the export and not as a reason to stop: the ONNX files compare inputs with the trees' thresholds at a lower numerical precision (32 bits), so a row lying very close to a threshold can fall on the other side. The person-equal errors of F2 and of M3 at 12 people agree to the four decimals shown.

### F4 penalties chosen on the training pool

The choices, from the four values 0.001, 0.01, 0.1 and 1, are sealed in FIT-COMPLETE.json. For the impulse: 1 for EMG only and 0.001 for every other version, including both versions on the rows with an earlier EMG window (section 7). For the new load: 1 for EMG only, 0.001 for force only and 1 for force and EMG. For the new load on the rows with an earlier EMG window: 1 for force and EMG and 0.1 for force and earlier EMG.

## 7. Secondary arms

A secondary arm changes one thing about a recipe to help explain the main result. The protocol (section 9) reports these arms with intervals, keeps them outside the corrected tests, and does not let them change a label. Their intervals are not adjusted for the number of comparisons, so a single interval that just excludes zero is weak evidence.

- **S1, updates scaled to the data.** M1 with more training steps on larger training sets: 900 × (rows at this rung) / (rows at 12 people), rounded. At 12 people S1 is M1.
- **S3, a wider model.** M1 with width 96 instead of 24, and updates scaled as in S1.
- **S2, without EMG.** Each family fitted on the force history alone.
- **S4, a fixed number of rows.** Each family fitted on 9,586 rows at every rung, picked by hash from the larger training table. More people then no longer means more rows. S4 has no fit at 12 people, because the 12-person table has exactly 9,586 rows; its change from 12 to 47 people is measured against the family's own 12-person fit.
- **S5, trees on the compact input.** Boosted trees given the input of M1 and M2 instead of their own.
- **G9, tuned settings.** M2 and M3 with one setting chosen instead of fixed: the penalty of M2 from 0.001, 0.01, 0.1 and 1, and the number of leaves of M3's trees from 7, 15 and 31. The choice is made for each score by setting aside training people four times in turn.
- **C4, random recurrent readout.** Described in section 6.
- **S6, an earlier EMG window.** M1 and M2 at 12 and at 47 people, with an EMG window that ends 500 ms before the issue time. The force history is unchanged.
- **G8, variety.** Two training sets of nearly equal size at the largest rung: the 12 earlier fit people plus all 35 pool people with one walk each (19,990 training rows), against the 12 plus the first 11 pool people of draw order 0 with three walks each (18,500 rows).

One arm of the designs that were reviewed, S7, an ensemble of replicate forecasts, was not run. The protocol says so.

### The arms by rung

Impulse error (N·s) by rung. The last three columns give the arm's change from 12 to 47 people, the arm against its own family at 47 people (for C4, against M1), and the change from 12 to 47 people on the 24-position schedule:

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

Each arm against its own family at the same rung, impulse error:

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

Each arm against its own family at the same rung, Brier score:

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

### Training budget and width (S1, S3)

When the updates grow with the rows, M1's error at 47 people is 1.5964 N·s. That is 27.29% below M1 (−29.64% to −25.05%), and the gap opens step by step, from −10.51% at 18 people. The wider model is already 18.70% below M1 at 12 people, where both take 900 updates, and 29.48% below at 47 (1.5484 N·s). At 47 people both arms are below F1 (1.8099 N·s).

The fixed recipe of M1 is therefore held back by its 900 updates and by its width more than by the number of people. In S1 and S3 more people and more updates come together, so their changes from 12 to 47 people (−31.15% and −17.86%) do not measure the effect of people alone.

### A fixed number of rows (S4)

With 9,586 rows at every rung, M1 and M2 keep most of their gain from 12 to 47 people: −4.18% (−5.47% to −2.99%) and −3.28% (−3.85% to −2.70%). For the trees the gain is not detectable (−2.15%, with an interval from −5.85% to +1.40%), and S4-M3 falls further behind M3 at each rung, from +3.14% at 18 people to +10.04% at 47. At an equal number of rows M1 and M2 still gain in this setting (uncorrected intervals, no label); for the trees no gain is detectable at an equal number of rows.

### The contribution of EMG (S2)

Without EMG, the impulse error at 47 people is 2.03% higher for M1 (+0.91% to +3.27%), 0.69% higher for M2 (+0.18% to +1.29%) and 1.50% higher for M3 (−0.64% to +3.73%). The EMG gain is the force-only error minus the full model's error at the same rung; a positive value means EMG helps. In N·s:

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

The EMG gain is small at every rung. Its change with more people can be detected for M2 on the impulse and for M3 on the Brier score, and not for the others.

### Trees on the compact input (S5)

For the impulse, S5 is close to M3: +2.92% at 47 people, with an interval from −0.24% to +6.33%. For the new load it is clearly worse (+12.46%, +8.70% to +16.69%). The trees' good new-load forecasts therefore depend on their own, fuller input.

### Tuned settings (G9)

Tuned M2 chose the impulse penalty 0.001 in all 32 fits, where the fixed recipe uses 1. It is slightly better than M2 for the impulse, by 1.34% at 12 people and 0.39% at 47. For the new load it kept the penalty 1, except in 6 of the 10 draws at 36 people and in the fit at 47.

Tuned M3 chose 15 leaves for the impulse at 12 people and in 2 of the 10 draws at 18 people, and the recipe's 31 leaves otherwise. From 24 people on it is therefore the same as M3, and at 18 people it is slightly worse (+0.64%). For the new load it kept the recipe's 7 leaves except in one draw at 24 people.

The chosen settings are in the private fit records. The published files carry only the scores.

### Random recurrent readout (C4)

With only the output layer trained, the error stays at the level of persistence at both rungs and does not move with more people (−0.13%). M1's result therefore needs trained recurrent weights:

| Rung | C4 error | Against M1 at the same rung | Against M2 at the same rung | Against M3 at the same rung |
|---|---|---|---|---|
| N = 12 | 3.5625 | +53.64% (+47.86% to +59.29%) | −1.58% (−6.13% to +2.41%) | +64.52% (+53.32% to +75.56%) |
| N = 47 | 3.5579 | +62.04% (+56.84% to +67.23%) | +3.21% (−1.19% to +7.01%) | +84.77% (+73.20% to +97.36%) |

### An earlier EMG window (S6)

These arms are scored on the rows where the earlier window is valid: 14,288 impulse rows and 14,067 new-load rows, from all 20 people and 60 walks. They are compared with the standard fits on the same rows. The table also holds the two F4 versions fitted for these rows. Impulse error (N·s):

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

No change can be detected for M1 or M2 when the EMG window ends 500 ms earlier. The protocol treats this as a check of timing and not as a removal of muscle information, because the rhythm of walking can still be read from the earlier window.

The F4 version with the earlier window has a lower impulse error than its version with EMG up to the issue time (−3.46%, −6.10% to −1.04%). In impulse error neither version is below persistence on these rows. In Brier score the version with EMG up to the issue time is 0.93% below C1 (−1.29% to −0.61%), and the version with the earlier window cannot be told apart from it (−1.94%, −4.32% to +0.56%). The two F4 versions against persistence and against the families on the same rows, first for the impulse error and then for the Brier score:

| Arm | Against C1 | Against M1 at N = 12 | Against M1 at N = 47 | Against M2 at N = 12 | Against M2 at N = 47 | Against M3 at N = 12 | Against M3 at N = 47 |
|---|---|---|---|---|---|---|---|
| F4, force and EMG up to the issue | +6.05% (+1.77% to +11.39%) | +68.55% (+60.31% to +77.41%) | +78.88% (+71.10% to +87.02%) | +7.22% (+4.31% to +10.39%) | +12.39% (+9.23% to +15.91%) | +78.32% (+63.82% to +93.67%) | +103.87% (+87.66% to +120.35%) |
| F4, force and earlier EMG | +2.38% (−1.11% to +5.89%) | +62.72% (+54.87% to +71.65%) | +72.69% (+65.21% to +80.79%) | +3.51% (+0.78% to +6.24%) | +8.50% (+5.66% to +11.41%) | +72.16% (+58.29% to +86.93%) | +96.82% (+80.48% to +113.75%) |

| Arm | Against C1 | Against M1 at N = 12 | Against M1 at N = 47 | Against M2 at N = 12 | Against M2 at N = 47 | Against M3 at N = 12 | Against M3 at N = 47 |
|---|---|---|---|---|---|---|---|
| F4, force and EMG up to the issue | −0.93% (−1.29% to −0.61%) | +0.54% (−0.36% to +1.23%) | +0.68% (+0.03% to +1.19%) | +0.58% (−1.03% to +1.80%) | +0.77% (−0.81% to +1.98%) | +11.97% (+5.99% to +18.34%) | +19.36% (+12.26% to +26.12%) |
| F4, force and earlier EMG | −1.94% (−4.32% to +0.56%) | −0.48% (−3.11% to +2.25%) | −0.35% (−2.88% to +2.34%) | −0.45% (−3.48% to +2.65%) | −0.26% (−3.25% to +2.77%) | +10.82% (+3.80% to +17.66%) | +18.14% (+10.48% to +24.89%) |

### Variety (G8)

With about the same number of rows, one walk from each of 35 pool people against three walks from each of 11:

| Family | Measure | Varied set: 35 pool people, one walk each | Repeated set: 11 pool people, three walks each | Varied minus repeated | Relative | 95% interval (relative) |
|---|---|---|---|---|---|---|
| M1, compact recurrent model | impulse error (N·s) | 2.2374 | 2.2402 | −0.0028 | −0.12% | −1.81% to +1.62% |
| M2, ridge and logistic regression | impulse error (N·s) | 3.4368 | 3.5554 | −0.1187 | −3.34% | −4.01% to −2.65% |
| M3, boosted trees | impulse error (N·s) | 2.0736 | 1.9884 | +0.0852 | +4.28% | +0.98% to +7.44% |
| M1, compact recurrent model | Brier score | 0.033701 | 0.033711 | −0.000010 | −0.03% | −0.18% to +0.11% |
| M2, ridge and logistic regression | Brier score | 0.033607 | 0.033681 | −0.000073 | −0.22% | −0.56% to +0.09% |
| M3, boosted trees | Brier score | 0.029608 | 0.030014 | −0.000406 | −1.35% | −3.60% to +0.72% |

The result is mixed. For the impulse, the more varied set is better for M2 (−3.34%), worse for M3 (+4.28%) and no different for M1. No difference in the Brier score can be detected.

## 8. The 24-position schedule

The protocol declares a secondary table on the 24-position schedule for every method. The scoring program of stage S-c wrote it only for the F3 test. The rest was computed afterwards, in the supplement, from the same sealed forecasts and with the same scoring code. Because that happened after the main results were known, these tables are descriptive.

From the supplement come: the rows and columns for the 24-position schedule in the tables of this file, the comparisons at the same rung and the F4 comparisons on the rows with an earlier EMG window in section 7, the means of the two variety sets, the subgroup counts and some subgroup rows in section 9, the ranking by Brier score, and the training-set counts in section 2.

The errors of the rungs on this schedule are in the curve tables of sections 3 and 4, and the changes of the secondary arms are in the last column of their tables. The success rule applied to these rows, as a description only, first for the impulse error and then for the Brier score:

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

The changes in impulse error are close to those on all issue times. The intervals are wider because there are fewer rows, and M1's interval now reaches −2.72%. M3's Brier change cannot be detected on this schedule, which holds 95 positive rows, and the rule gives INCONCLUSIVE there.

## 9. Subgroups, reliability and ranking

These tables are descriptive (protocol section 9, items S8 and S9).

### Rows by plate state and by plate

The rows are split by the state of the plate at the issue time and by plate. Pending means that the force has risen above +20 N and the 19 confirming samples are not yet complete. No row was issued with an unknown plate state:

| Subgroup | Issued rows | Impulse rows | New-load rows | Positive rows | Distinct onsets |
|---|---|---|---|---|---|
| plate unloaded at the issue | 14,065 | 13,465 | 13,346 | 579 | 118 |
| plate loaded or pending | 3,823 | 3,823 | 3,694 | 0 | 0 |
| plate state unknown | 0 | 0 | 0 | 0 | 0 |
| plate 1 | 8,944 | 8,644 | 8,518 | 281 | 58 |
| plate 2 | 8,944 | 8,644 | 8,522 | 298 | 60 |

Every positive row is a row whose plate is unloaded at the issue time, as the definition of a new load requires.

Mean absolute impulse error (N·s) over the rows of each subgroup. These are plain averages over rows and are not person-equal:

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

On rows where the plate is unloaded at the issue time, persistence (0.6584) and the unconditional control (0.6433) have lower error than M1 (0.7879 at 12 people, 0.7960 at 47). The advantage of the fitted models over persistence lies on the rows where the plate is loaded or pending. The gain of M1 from more people lies there too, and so does most of the gain of M3. M2's error on unloaded rows is more than twice that of persistence.

### Reliability of the new-load forecasts

A forecast chance is reliable when, among the rows that receive a chance of about 0.3, a new load follows in about 30% of them. The table sorts the rows into bands of the forecast chance and gives, for each band, the number of rows, the mean forecast and the observed share of new loads. For M1 the forecast is the mean over its 50 fits:

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

M1's mean forecast never exceeds 0.2, and its few rows above 0.1 have no more new loads than the rest. M2's forecast seldom exceeds 0.2; in its band from 0.1 to 0.2 the observed share is about 0.07, half the forecast. M3's forecasts spread up to 0.9 at 12 people and up to 0.8 at 47. At 47 people its observed shares rise with the forecast up to 0.6; the two bands above 0.6 hold 18 and 21 rows.

### Rankings

Ranking by impulse error on all issue times, with the fitted families at each rung. The ranking lists the families, the controls, the frozen checkpoints and C4. S1 and S3 are not part of it; S1 has a lower impulse error than F1 from 36 people on and S3 from 18 people on (at 47 people 1.5964 and 1.5484 N·s against 1.8099):

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

By impulse error the order of the three families is M3, M1, M2 at every rung, on both sets of rows. By Brier score on all issue times M3 is first at every rung; M1 is ahead of M2 at 12 people and M2 is ahead of M1 from 18 people on, each time by less than 0.0001. In impulse error M2 passes persistence between 12 and 18 people on all issue times. On the 24-position schedule it passes persistence only at 47 people.

## 10. Limits

- **One laboratory, one task.** Healthy adults walking barefoot overground at the speed they prefer, under one recording protocol. Nothing here speaks for other laboratories, for patients, or for other speeds, footwear, tasks, bodies or species.
- **Two plates, vertical force.** Plates 1 and 2 of four cover part of a 12 m walkway. The forecasts describe those two plates only.
- **Selection by channel names.** Only people whose walks carry the six literal EMG names qualified: 65 of the 80 candidates. If the naming of files follows the period in which a person was recorded, this is a hidden selection of people.
- **Surface EMG.** The input is muscle voltage at the skin, as RMS per 20 ms slice, with no filtering and no normalisation. It is not a recording from nerves.
- **Conditional on these 12 fit people and this pool.** Every rung contains the same 12 people, and the pool is the 35 people that the hash order gave. The intervals reflect the sampling of the 20 evaluation people. They do not reflect the choice of the 12 or of the pool, and at 47 people there is only one training set.
- **People as the unit.** Neighbouring forecasts overlap in what they see, so the rows are not independent, and all tests redraw whole people. With 20 people and 118 onsets, the new-load results rest on few events.
- **Fixed recipes.** The result concerns these three recipes as fixed in advance, not the best that each design could do. S1 and S3 show how much the level of M1 depends on its training budget and width.
- **A short curve.** A trend fitted to four rungs is a short-range extrapolation. It is not a scaling law.
- **Secondary and supplementary tables.** Their intervals are not adjusted for the number of comparisons. The supplement was computed after the main results were known, by code written afterwards.
- **Forecast accuracy only.** The scores measure how well the force on a plate is forecast 100 ms ahead. They are not evidence about how the nervous system controls walking.
- **The evaluation group is used.** A method chosen with knowledge of these results cannot treat these 20 people as unseen.

## 11. Custody and the order of events

Custody means who could read which file, and when. The protocol's safeguard is an order of events: the fitted models are sealed before the evaluation recordings are downloaded, the forecasts are sealed before they are scored, and the trend prediction is sealed before the largest rung is scored. Each of the protocol's seals (C1 to C5) was committed before the stage that depends on it began. [README-CODE.md](README-CODE.md) and [README-CODE-SIMPLE.md](README-CODE-SIMPLE.md) give the commands and the records.

Two kinds of time appear below. A commit time is the author time written in the commit record on the project's computer, that is, the time at which the commit was first made. A push time is the time at which the commit was copied to the public repository, taken from this computer's record of each push. Three commits also carry a later second time, the committer time, from a step made after D1; "The header check before the allocation" below sets this out.

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

### The targets

The targets are the correct answers: the impulse that was really measured and whether a new load really began. The program that unpacks the recordings (the extractor) decoded the evaluation walks at 14:09:47. It wrote the inputs (row keys, force and EMG histories, input masks) and the targets (outcomes, impulses, target masks) to two separate private files. It also wrote, for each walk, the number of rows that have a target into a third file, `EVAL-WALKS.json`.

The forecasting programs opened the input file, and they opened `EVAL-WALKS.json` to check the fingerprint of the input file. They never opened the target file.

FORECASTS-SEAL.json contains the sentence "targets were never opened before this seal", and the message of its commit says the same. That overstates what happened: the extractor had decoded the targets in order to write them. The sealed file cannot be changed, so the exact statement is made here: the extractor decoded the targets, and the forecasting programs never read them.

According to the code and the run logs, the first program to read the target file after the extractor was the S-b scoring program. No log of file accesses exists that could show this independently. At the review before S-c, the forecasts of 24 methods (fits of the ladder, controls and published checkpoints) were issued again from the model files and the input file alone, and they matched the sealed forecasts in every bit.

### The forecast seal and the first scoring step

The forecast seal was written at 14:54:10 and committed on the project's computer at 14:54:24, 8 s before S-b began at 14:54:32. It reached the public repository only with the push at 15:08:44, after S-b. That the seal came before S-b therefore rests on local records and not on a public time. The protocol asks for C1, C2, C3 and C5 to be pushed before the next stage and does not list C4. S-b reads only the forecasts of the rungs below 47; the forecasts for 47 people are kept in a separate file.

### The fit seal, P2 and the public order

The fit seal, with the F4 penalties and P1, was public at 14:03:24, before the first byte of the evaluation group was requested at 14:06:17. P2 was public at 15:08:44, before S-c began at 15:11:08. The S-c scoring program refuses to run unless the committed P2 file has the fingerprint it is given.

### The header check before the allocation

D1 read header bytes of people who later became evaluation people. The hash order that assigns the groups was fixed and published at C1, before D1, so the outcome of the check could not steer who went into which group.

D1 ran on fixes for the review of the run code. They were first committed at 11:54:47, 20 s before D1 began, and were first reviewed at C2. The two fixes that D1 uses ([DECISIONS.md](DECISIONS.md) items 13 and 14) change only what happens when a request has to be repeated or the stage has to halt, and neither happened.

A commit record holds two times: the author time, when the change was first committed, and the committer time, when the commit was last rewritten. The time 11:54:47 is the author time of commit `f5b7103`. That commit, the run-code commit before it (`f28ed67`) and the allocation commit after it (`8a8fab5`) also carry a committer time of 12:05:32, after D1 ended at 12:03:58. At 12:05:32 the branch was moved onto newer commits of the main branch (a rebase); none of those commits changes a file of this folder. The rebase gave the three commits their present ids and that committer time, and left their author times and this folder's content unchanged. The commit as first made at 11:54:47 is recorded only in this computer's own branch log, and it was not pushed before D1. That the fixes came before D1 therefore rests on local records and not on a public time.

### What has never been read

This experiment has read no recording byte of the 12 test people and the 6 validation people of the earlier work, or of the boundary case SUBJ099. Of the 10 physics-source people, the 11 people of the physics supplement and the 4 unusable candidates it has read only the header bytes of D1.

### Recomputation

Section 14 of the protocol asks for an independent recomputation (a replay) of every average and of sample rows from each plate. The program `replay.py` in this folder covers the main impulse averages and the sample rows. With plain loops it recomputed each evaluation person's impulse error for M1, M2 and M3 at the five rungs: 300 numbers (largest difference 7.9e-14, that is, 0.000000000000079). It also recomputed 40 target rows, 20 per plate, directly from the decoded walks (difference 0). The other averages of S-b and S-c were recomputed by separate private checks, which agreed to 6.7e-15 and 5.3e-15. A second independent recomputation, made before this text was written, compared 3,318 numbers of RESULTS.json (largest difference 2.5e-10). Those checks are not code in this folder, and the records of these recomputations are private.

### Differences from the plan

- The fits ran on 8 single-thread lanes on CPUs 24 to 31, inside the protocol's limit of 12 lanes.
- The private folder holds 1,005,701,390 bytes, above the protocol's estimate of under 0.7 GB ([DECISIONS.md](DECISIONS.md) item 18). This concerns storage only.
- The protocol's time plan assumed 28 November. Every stage up to the final scoring (S-c), and the supplement, ran on 27 November 2026 (UTC).
- The replay program in this folder covers the main impulse averages and 40 target rows, where section 14 of the protocol asks for every average. The other averages were recomputed by private checks (see Recomputation above).
- F5 was not issued.

## 12. What is published

In this folder:

- the protocol in two editions and as a machine-readable file;
- the code and its two guides;
- the receipts of the header check and of the two downloads, without signed addresses;
- the allocation of people to groups;
- the three seals: `FIT-COMPLETE.json`, `FORECASTS-SEAL.json` and `P2-TREND-PREDICTION.json`;
- `RESULTS.json`, which includes each evaluation person's errors by archive code, and `RESULTS-SUPPLEMENT.json`;
- these two results editions and [NOTICE.md](NOTICE.md).

Not yet published: the fitted models from 47 people that protocol section 18 lists for release under CC0 1.0. They are the M1 checkpoint of seed 20261124, the M3 trees in ONNX format and the M2 coefficients. FIT-COMPLETE.json holds a fingerprint for every fit, so a later export can be checked against the seal.

Never published: the recordings, the extracted arrays, the forecasts and the targets (protocol section 17). The recordings are public at their source.

## 13. Rerunning and checking

[README-CODE.md](README-CODE.md) gives the command, the software runtime, the inputs and the measured time of every stage. [README-CODE-SIMPLE.md](README-CODE-SIMPLE.md) explains the same at more length. Three checks need only the public files of this folder:

1. **The chain of fingerprints.** RESULTS.json names the sha256 of PROTOCOL.json, FIT-COMPLETE.json, FORECASTS-SEAL.json and P2-TREND-PREDICTION.json, and the supplement names that of RESULTS.json. Running `sha256sum` on the five files must give:

   | File | sha256 |
   | --- | --- |
   | `PROTOCOL.json` | `1768c4df8553095b2cd2a49c8f5297cd507fe90008d240bb3b189e526a447b33` |
   | `FIT-COMPLETE.json` | `7280ea43b4b4ac084e51cc709e7ce6ff059d9fcf49740c6681c852d887bf8b57` |
   | `FORECASTS-SEAL.json` | `98a0b76f7e0eacba02c6014704bd241fbd02ef490e8ca16a3fda1fac124bc2e2` |
   | `P2-TREND-PREDICTION.json` | `e8d1c45724945306a2d9112b9d36009209406e810552215a0b1006112cf951e2` |
   | `RESULTS.json` | `e7cf4061709d035b249bc941b9238b706b964d2bb6e6f286d1150d307f443c1f` |

2. **The main result.** The three main changes, their intervals and their p-values can be recomputed from the per-person errors in RESULTS.json with the short script under "Checking the published records" in README-CODE-SIMPLE.md (the same script is in README-CODE.md).
3. **The groups.** The pool, the hash orders and the allocation can be rebuilt from the archive's table of contents and the receipt of the header check (the same sections of the guides).

Everything from the training-pool download onward needs the recordings. They are public under CC0 1.0 and are not redistributed here. The receipts give each walk's position in the archive and the fingerprint of the bytes received, so a reader can fetch the same bytes and compare.

The fits are deterministic: on one thread and with the same software they give the same files, and FIT-COMPLETE.json lists a fingerprint for every fit. Two software runtimes were used (protocol section 16). Runtime A: CPython 3.13.15, torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0. Runtime B: CPython 3.12.14, numpy 2.5.5, scikit-learn 1.9.1, joblib 1.6.0, onnxruntime 1.32.0.

Measured times of this run: the header probe 8 min 51 s; the training-pool download 5 min 36 s; the fits 23 min 38 s (runtime A, 1,450 fits) and 7 min 53 s (runtime B, 292 fits) on 8 CPU lanes; the evaluation download 3 min 19 s; the forecasts 43 min 20 s (runtime A) beside 5 min 2 s (runtime B); each scoring step under 10 s.

## 14. Sources and terms

The recordings are by Van Criekinge and colleagues. The data are released under CC0 1.0 and the article that describes them under CC BY 4.0. [NOTICE.md](NOTICE.md) gives the citations, what this experiment did with the data, the origin of the scored model files and the terms of this folder's own files.
