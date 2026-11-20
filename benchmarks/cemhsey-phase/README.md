[The studies](../README.md) › Study 23 · Pinch: a correction learned from other people

# A correction learned from other people helped all three, and splitting it by direction added nothing

On the screen, the force target rises and falls at the same speed. In [study 22](../cemhsey-carry/README.md), yesterday's practice correction helped on the rise and hurt on the release. Would two corrections, one for each direction, do better, and could they work for someone who gave no practice recording at all? At a 50% target, the rule "take the current reading and add the change the on-screen schedule calls for" forecast the gauge 120 ms ahead with an average miss of **0.70007%** for three test people. With separate corrections for the rise and the release, learned entirely from three other people, it missed by **0.69509%**: 0.00498% better, for all three. One correction shared by both directions did as well, 0.69507%, so splitting it bought nothing. The fitted five-grid model, given the same separate corrections, missed by 0.82204%, worse than the corrected rule for all three people.

Every error here is the plain average miss (mean absolute error) over the whole trial, in % of the person's hardest squeeze that day (their maximum voluntary contraction, MVC). Both test repeats enter each person's score before the three scores are averaged. The forearm signal is surface EMG, electrical activity of muscle picked up on the skin.

Average miss over the whole trial, in % of the hardest squeeze:

| Forecast before correction | No correction | One correction | Separate corrections for rise and release |
|---|---:|---:|---:|
| Current force plus scheduled change | 0.70007 | 0.69507 | 0.69509 |
| Force history | 0.84317 | 0.84679 | 0.82834 |
| Force history and five forearm grids | 0.83624 | 0.83945 | 0.82204 |

Repeating the latest gauge reading on its own missed by 0.81104%, so the fitted five-grid model with its corrections lost even to that. Following the scheduled target on its own missed by 2.10117%.

## What was done

Three adults supplied the recordings the corrections were fitted on, and three others the test recordings. Each person made two pinches at the 50% target. The simple forecast starts from the current gauge reading and adds the change scheduled on the screen; the two others use force history, one of them with forearm EMG as well. Each forecast could keep its original form, learn one correction across both directions, or learn separate corrections for the squeeze and the release. The test recordings were opened once, after the fit was fixed. [The plan](PROTOCOL.md) · [Design and data sources](DESIGN.json)

### Where splitting the simple correction helped

The gain is the error with one correction minus the error with separate corrections: positive means the separate corrections missed by less. To keep the three people's individual results private, the bounds are rounded outwards, to steps of 0.05% of the hardest squeeze, so that they enclose all three gains. This reporting rule was fixed after the fitting and before any test recording was opened. [How the range is reported](PUBLIC-REPORTING.md)

| Stage of the cue at the forecast | Cutoffs | Average gain (% of the hardest squeeze) | Bounds enclosing the three people | People lower / equal / higher |
|---|---:|---:|---:|---:|
| Whole trial | 3552 | −0.00002 | −0.05 to 0.05 | 1 / 0 / 2 |
| First rest | 564 | +0.00004 | 0.00 to 0.05 | 3 / 0 / 0 |
| Rise | 600 | +0.00070 | 0.00 to 0.05 | 3 / 0 / 0 |
| Hold | 1200 | −0.00001 | −0.05 to 0.05 | 0 / 1 / 2 |
| Release | 600 | −0.00081 | −0.05 to −0.00 | 0 / 0 / 3 |
| Final rest | 588 | 0.00000 | 0.00 to 0.00 | 0 / 3 / 0 |

Split by direction, the correction helped all three people on the rise and hurt all three on the release, by less than 0.001% of the hardest squeeze either way. The same rounding gives the main result's range: from 0.05000% lower to no change.

## What it does not show

The 3,552 test cutoffs overlap within six recordings. The three test people gave no recordings to the correction fit or to the original model's training, though other recordings of theirs had been seen in earlier pinch studies. The comparison covers a single target and one recording day, and its counts describe these three people. No group was set aside for this study.

[Explore forecast errors and paired gains](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/) · [Fit a correction on your computer](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/reader/) · [Offline reader with desktop launchers](../../docs/cemhsey-phase/reader/CEMHSEY-Population-Forecasts.zip) · [Results file](RESULTS.json)
