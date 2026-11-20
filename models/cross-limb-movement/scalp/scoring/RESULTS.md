# Scalp history helped one muscle forecast. Both marker paths got worse.

A light cues someone to reach for an object. You have the last 625 milliseconds of wrist position and muscle activity. Does voltage recorded at three places on the scalp help predict the next 125 milliseconds? In these reach-and-lift recordings, adding the measured scalp history increased average wrist-path error from 3.9055 to 4.1199 mm. All six held-out participants had larger errors. The wrist-muscle result was close to a tie.

A second experiment asked the same forecasting question while people stood or walked on a balance beam and a headset rotated their visual field. Here, adding scalp measurements reduced leg-muscle error by 0.0143 µV against a reference error of 11.3846 µV. The sacrum-marker path still got worse. **One of four outcomes passed the prespecified test. This experiment does not support adding these three scalp histories for a combined improvement across muscle and movement in both tasks.** [Balance experiment](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Grasp-and-lift experiment](https://doi.org/10.6084/m9.figshare.c.988376.v2)

## What changed between the two forecasts?

Each model saw the same task information, marker positions and available muscle activity. One also saw the mean and root-mean-square voltage in 20 short intervals at C3, Cz and C4, three nominal positions on the scalp. The reference model saw the fitting participants’ average feature values in the same measured slots. Both retained the same flags marking which sites had usable recordings. The experiment held the model size, starting weights, training draws and number of updates fixed and trained the two branches independently. Both have 4,068 parameters. Six columns of constant standardized amplitudes in the reference branch carry no varying measurements.

Each of the 18 balance participants and six wrist participants received forecasts from three fits with different training seeds. All three fits had excluded that person from training. The primary outcome averages losses across those seeds. It gives equal weight to participants and, within a participant, equal weight to the observed wrist series or the four combinations of balance posture and rotation direction. Whole-path error is the average three-dimensional distance from the measured marker over all 32 future samples. Muscle error is the average absolute difference from measured root-mean-square amplitude over available muscles. The wrist archive's amplitudes retain their exported units.

| Study and outcome | Central | Reference | Difference | Paired 95% interval | One-sided 98.75% upper limit | People with lower error |
|---|---:|---:|---:|---|---:|---:|
| Balance muscle (µV) | 11.3703 | 11.3846 | −0.0143 | −0.0230 to −0.0063 | −0.0053 | 14 / 18 |
| Balance marker path (mm) | 2.6992 | 2.6674 | +0.0317 | 0.0013 to 0.0760 | +0.0854 | 6 / 18 |
| Wrist muscle (WAY exported amplitude units) | 0.0100 | 0.0100 | +0.0000146 | −0.0001204 to 0.0001333 | +0.0001504 | 3 / 6 |
| Wrist marker path (mm) | 4.1199 | 3.9055 | +0.2145 | 0.1178 to 0.3062 | +0.3302 | 0 / 6 |

Differences subtract the reference error from the error with measured scalp history. Each interval resamples whole people 5,000 times. The selection rule required a negative mean and a negative one-sided upper limit for all four outcomes. These intervals describe participant variation conditional on these fits. The training folds overlap. Six people constrain how precisely we can describe variation in the wrist study.

## What survived a change of training seed?

| Study and outcome | Seed 1641 | Seed 2718 | Seed 3917 | Sample SD |
|---|---:|---:|---:|---:|
| Balance muscle (µV) | −0.0243 | −0.0160 | −0.0027 | 0.0109 |
| Balance marker path (mm) | +0.1245 | −0.0153 | −0.0141 | 0.0804 |
| Wrist muscle (WAY exported amplitude units) | −0.0000547 | +0.0000076 | +0.0000909 | 0.0000730 |
| Wrist marker path (mm) | +0.2946 | +0.2567 | +0.0922 | 0.1076 |

All three fits improved mean balance-muscle error. Five of the 18 balance participants improved on both primary errors, nine improved on muscle error alone, one improved on path error alone and three improved on neither. The balance-path difference changed sign across seeds. The wrist path worsened across all three seeds and in every participant after averaging seeds. The balance-path estimate was particularly sensitive to the first seed, whose increase exceeded the two other seeds’ reductions combined.

## Could the model tell which trial supplied the scalp history?

Keep the model fixed and give it the earlier scalp history from a different trial. The substitute must come from the same person, task, session, direction and block with exactly the same central sites available. The two complete event windows must be disjoint on the recorded clock. This left 4,963 balance events and 1,602 wrist events. The 216 unmatched balance events and 162 unmatched wrist events are absent from **both** sides of this comparison. All 24 people still contributed.

On the eligible balance events, the measured and substituted histories gave mean path errors of 2.6958 and 2.7008 mm. For the wrist, the corresponding values were 4.1518 and 4.1430 mm. The ordinary 95% intervals for both path differences and both muscle differences span zero. These fits gave little evidence that the trial-specific timing of the scalp history mattered to either forecast. A different model trained from the start on misaligned histories poses a separate question.

## What could simpler forecasts do?

In balance, carrying the last muscle amplitude forward gave 11.3554 µV error, below even the measured-scalp model's 11.3703 µV. Extending the last 31.25 ms of marker motion in a straight line gave 2.5829 mm error, compared with 2.6992 mm for that model. The wrist model beat a stationary marker and had lower mean path error than the exact-duration velocity controls. The wrist-only specialist with the full update budget gave 3.6863 mm, below the central model's 4.1199 mm.

The frontal, eye and neck branches each learned their own weights. Relative to the central model, recorded balance eye and neck channels each gave lower mean path error. The frontal fit also gave lower mean wrist-path error. All of these electrical measurements can contain movement-related activity. Comparing predictive errors cannot identify a cortical source. The wrist study lacked dedicated eye and neck channels.

The following comparisons show central minus comparator error on their common events. Parentheses give ordinary paired 95% intervals. Muscle units are µV for balance and exported amplitude units for the wrist. Each of the five motion rules uses the same independent muscle persistence forecast. The archived single-study models used either the same number of target-study draws as the joint model, or all the joint model's updates on one study. Absolute errors for both sides of each comparison appear in the [aggregate score file](results.json).

| Study | Compared with central | Events / people | Muscle error difference | Path error difference (mm) |
|---|---|---:|---|---|
| Balance | Earlier trial, same central model | 4,963 / 18 | +0.0000355 (−0.0012 to 0.0014) | −0.0050 (−0.0178 to 0.0044) |
| Balance | Frontal scalp | 4,010 / 14 | +0.0052 (0.0007037 to 0.0100) | +0.0278 (−0.0087 to 0.0786) |
| Balance | Eye recordings | 5,179 / 18 | −0.0065 (−0.0168 to 0.0032) | +0.0266 (0.0069 to 0.0460) |
| Balance | Neck recordings | 5,179 / 18 | −0.0010 (−0.0134 to 0.0107) | +0.0417 (0.0070 to 0.0895) |
| Balance | Original movement and muscle model | 5,179 / 18 | −0.0016 (−0.0064 to 0.0029) | +0.0551 (0.0241 to 0.0969) |
| Balance | Per-study specialist, equal target-study exposure | 5,179 / 18 | +0.0120 (0.0030 to 0.0207) | +0.2021 (0.1590 to 0.2603) |
| Balance | Per-study specialist, equal total steps | 5,179 / 18 | +0.0120 (−0.0007937 to 0.0235) | +0.2180 (0.1745 to 0.2742) |
| Balance | Stationary marker + muscle persistence | 5,179 / 18 | +0.0149 (0.0056 to 0.0246) | −2.2928 (−2.5124 to −2.0696) |
| Balance | Exact 31.25 ms velocity + muscle persistence | 5,179 / 18 | +0.0149 (0.0056 to 0.0246) | +0.1162 (0.0749 to 0.1721) |
| Balance | Exact 125 ms velocity + muscle persistence | 5,179 / 18 | +0.0149 (0.0056 to 0.0246) | −0.5583 (−0.6875 to −0.4184) |
| Balance | One patch-knot velocity + muscle persistence | 5,179 / 18 | +0.0149 (0.0056 to 0.0246) | +0.1162 (0.0749 to 0.1721) |
| Balance | Four patch-knot velocity + muscle persistence | 5,179 / 18 | +0.0149 (0.0056 to 0.0246) | −0.5583 (−0.6875 to −0.4184) |
| Wrist | Earlier trial, same central model | 1,602 / 6 | −0.0000022 (−0.0000228 to 0.0000144) | +0.0088 (−0.0124 to 0.0271) |
| Wrist | Frontal scalp | 1,764 / 6 | −0.0000539 (−0.0001275 to 0.0000103) | +0.2290 (0.1389 to 0.3180) |
| Wrist | Eye recordings | 0 / 0 | unavailable | unavailable |
| Wrist | Neck recordings | 0 / 0 | unavailable | unavailable |
| Wrist | Original movement and muscle model | 1,764 / 6 | −0.0001464 (−0.0004141 to 0.0000421) | +0.1839 (0.0323 to 0.3256) |
| Wrist | Per-study specialist, equal target-study exposure | 1,764 / 6 | +0.0001196 (−0.0001108 to 0.0003517) | +0.1033 (−0.1369 to 0.3783) |
| Wrist | Per-study specialist, equal total steps | 1,764 / 6 | −0.0003241 (−0.0010 to 0.0002850) | +0.4336 (0.2138 to 0.6749) |
| Wrist | Stationary marker + muscle persistence | 1,764 / 6 | +0.0004959 (−0.0005308 to 0.0016) | −9.7536 (−19.0184 to −0.7915) |
| Wrist | Exact 31.25 ms velocity + muscle persistence | 1,764 / 6 | +0.0004959 (−0.0005308 to 0.0016) | −1.6374 (−3.5064 to 0.1780) |
| Wrist | Exact 125 ms velocity + muscle persistence | 1,764 / 6 | +0.0004959 (−0.0005308 to 0.0016) | −5.1536 (−10.1435 to −0.3192) |
| Wrist | One patch-knot velocity + muscle persistence | 1,764 / 6 | +0.0004959 (−0.0005308 to 0.0016) | −1.6683 (−3.5688 to 0.1725) |
| Wrist | Four patch-knot velocity + muscle persistence | 1,764 / 6 | +0.0004959 (−0.0005308 to 0.0016) | −5.1837 (−10.1988 to −0.3224) |

The exact velocities use the previous trajectory in native coordinates. The one- and four-knot versions instead use the model's sampled marker positions and their actual ages. Both histories span 31.25 and 125 ms for balance. For the wrist, adjacent knots in these comparisons span 32 and 126 ms.

## Where did the path errors and missing measurements fall?

The absolute coordinate error rose on all three axes in each study. In balance the largest increase was along the superior–inferior axis. For the wrist the largest increases were in Y and Z of the recording system. A positive signed bias means the forecast coordinate lay above its measured value on average. The mean three-dimensional error at the final 125-ms sample rose from 5.8346 to 5.8862 mm for the sacrum and from 9.6260 to 10.1414 mm for the wrist.

| Study | Axis | Central absolute error (mm) | Reference absolute error (mm) | Difference (mm) | Central signed bias (mm) |
|---|---|---:|---:|---:|---:|
| Balance | ML | 1.4732 | 1.4683 | 0.0049 | 0.0103 |
| Balance | SI | 1.2828 | 1.2565 | 0.0262 | 0.0840 |
| Balance | AP | 1.3212 | 1.3027 | 0.0185 | −0.1218 |
| Wrist | X | 1.3509 | 1.2952 | 0.0557 | −0.2079 |
| Wrist | Y | 2.3345 | 2.1990 | 0.1355 | 0.6022 |
| Wrist | Z | 2.4935 | 2.3560 | 0.1374 | −0.1791 |

In balance, C3 was usable in 4,887 events from 17 people, Cz in 3,713 from 13 and C4 in 4,330 from 15. Every wrist event had all three. Both balance groups in the table showed a small reduction in muscle error and larger path error when given the recorded scalp history. The groups contained different people. These numbers cannot assign an effect to individual sites. The [aggregate tables](results.json) give the overlapping per-site groups and their exact counts, plus condition, muscle-channel and coordinate results. Groups represented by a single person contribute counts only.

| Study | Usable central sites | Events / people | Muscle error difference | Path error difference (mm) |
|---|---:|---:|---:|---:|
| Balance | 1 | 0 / 0 | unavailable | unavailable |
| Balance | 2 | 2,607 / 9 | −0.0158 | +0.0445 |
| Balance | 3 | 2,572 / 9 | −0.0129 | +0.0190 |
| Wrist | 1 | 0 / 0 | unavailable | unavailable |
| Wrist | 2 | 0 / 0 | unavailable | unavailable |
| Wrist | 3 | 1,764 / 6 | +0.0000146 | +0.2145 |

The balance archive includes retrospective channel screening and signal processing. The original movement and muscle inclusion rules checked future measurements. The wrist recording systems have published synchronization uncertainty of up to 2 ms. These limits matter even for a forecast built from samples indexed at or before cutoff. What was tested here was additional information in these archived recordings, under these tasks and checks. Testing whether a new person can be forecast in real time requires an independent prospective recording. [Balance data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC8711048/) · [WAY data descriptor](https://doi.org/10.1038/sdata.2014.47)
