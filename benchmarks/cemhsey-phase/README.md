# Learning the squeeze and the release

On the screen, a force target rises and falls at the same speed. In the preceding pinch study, an earlier practice correction helped on the rise and hurt on release. Would two corrections work better, one for each direction? Could they work for somebody who supplied no practice recording?

Three adults supply the training recordings and three others supply the evaluation recordings. Each person makes two 50% pinches. The simple forecast starts with the current gauge reading and adds the change scheduled on the screen. Two other forecasts use force history, one with additional forearm EMG. Each forecast can keep its original form, learn one correction across both directions, or learn separate corrections for the squeeze and release. [Prespecified methods](PROTOCOL.md) · [Design and data sources](DESIGN.json) · [Earlier two-day comparison](../cemhsey-carry/README.md)

The public tables use outward-rounded bounds for the three-person range. [Range reporting rule](PUBLIC-REPORTING.md)

## Six pinches from the other three people

At a target of 50% MVC, current force plus the scheduled cue change gave a mean absolute error of 0.70007 percentage points of maximum voluntary contraction. Giving that forecast separate rise and fall corrections changed its error to 0.69509, a reduction of 0.00498 percentage points. Across the three people, the split forecast produced 3 lower, 0 equal and 0 higher errors. The corrections came entirely from the fitting group.

One shared coefficient gave 0.69507 percentage points of error for the same simple model. Splitting it by direction produced an increase of 0.00002 percentage points. With separate coefficients in both models, the five-grid forecast reached 0.82204 percentage points compared with 0.69509 for the simple forecast. The five-grid model had 0 lower, 0 equal and 3 higher individual errors.

### Whole-trial errors by forecast

Mean absolute errors in percentage points of MVC. Both test repeats enter each person’s score before the three scores are averaged.

| Forecast before fitting | Original | One coefficient | Separate rise and fall |
|---|---:|---:|---:|
| Current force + scheduled change | 0.70007 | 0.69507 | 0.69509 |
| Force history | 0.84317 | 0.84679 | 0.82834 |
| Force history + five forearm grids | 0.83624 | 0.83945 | 0.82204 |

Carrying forward the latest gauge reading by itself gave 0.81104 percentage points of error. Following the scheduled target by itself gave 2.10117.

### Where did splitting the simple correction help?

Gain is the one-coefficient error minus the split-coefficient error. Positive means the separate rise and fall coefficients gave a smaller error. The range bounds enclose the three gains in steps of 0.05 percentage points. [Public range reporting](PUBLIC-REPORTING.md)

| Phase at forecast time | Cutoffs | Mean gain (% MVC) | Enclosing bounds (% MVC) | Lower / equal / higher |
|---|---:|---:|---:|---:|
| Whole trial | 3552 | −0.00002 | −0.05 to 0.05 | 1 / 0 / 2 |
| Initial rest | 564 | +0.00004 | 0.00 to 0.05 | 3 / 0 / 0 |
| Rise | 600 | +0.00070 | 0.00 to 0.05 | 3 / 0 / 0 |
| Hold | 1200 | −0.00001 | −0.05 to 0.05 | 0 / 1 / 2 |
| Release | 600 | −0.00081 | −0.05 to −0.00 | 0 / 0 / 3 |
| Final rest | 588 | 0.00000 | 0.00 to 0.00 | 0 / 3 / 0 |

The 3,552 evaluation cutoffs overlap within the six recordings. The three evaluation participants supplied no recordings to the population fit or the original point-model training, though other records from them had been seen during earlier programme development. The comparison covers a single prescribed target and one indexed recording day. The participant counts describe this group.

[Explore forecast errors and paired gains](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/) · [Fit a correction locally](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/reader/) · [Offline reader with desktop launchers](../../docs/cemhsey-phase/reader/CEMHSEY-Population-Forecasts.zip) · [Numerical summary](RESULTS.json)
