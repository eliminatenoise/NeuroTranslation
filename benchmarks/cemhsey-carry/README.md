[The studies](../README.md) › Study 22 · Pinch, next day

# Yesterday's practice correction did as well as a fresh one, and the one-line rule beat both

How long does one practice pinch last? [Study 21](../cemhsey-transfer/README.md) fitted a correction on the first of two attempts and checked it on the second. Here the same four people came back on their next recording day, and the earlier correction was used again. At the 50% target, the five-grid forecast of the gauge 120 ms ahead missed by **0.70643%** with a correction fitted fresh on the new day's first pinch, and by **0.70578%** with yesterday's: the same to within 0.00065%, with the four people's gains running from −0.00249% to +0.00391%. Three people did a little better with yesterday's correction and one worse. Meanwhile the rule "take the current reading and add the change the on-screen schedule calls for" missed by 0.58356%, and beat the corrected forecast for three of the four.

Every error here is the plain average miss (mean absolute error) over the whole trial, in % of the person's hardest squeeze that day (their maximum voluntary contraction, MVC). Against the five-grid forecast adjusted for the target with no personal correction, reusing yesterday's correction gained 0.00226% on average.

At each of the three targets, yesterday's correction faced two alternatives: fit it again from the new day's first pinch, or use the scheduled cue with no personal correction. All eleven forecasts faced the same second pinch. The forearm electrodes and the gauge record a new session; the target on the screen follows the same schedule. [The plan](PROTOCOL.md) · [Study design](DESIGN.json) · [Acquisition study](https://doi.org/10.1038/s41597-025-05733-y)

### The same targets, with and without another practice pinch

Average miss over the whole trial, in % of that day's hardest squeeze. The first repeat of the new day supplied the fresh correction; no score uses that practice repeat.

| Target | Current force plus cue change | Force history, yesterday's practice | Force history, fresh practice | Five grids, yesterday's practice | Five grids, fresh practice |
|---|---:|---:|---:|---:|---:|
| 10% | 0.38493 | 0.56114 | 0.56137 | 0.57129 | 0.57145 |
| 30% | 0.48173 | 0.44688 | 0.44668 | 0.44756 | 0.44749 |
| 50% | 0.58356 | 0.72046 | 0.72111 | 0.70578 | 0.70643 |

### When the two corrections differed

For the 50% five-grid forecast, the gain is the error with fresh practice minus the error with yesterday's practice: a positive gain means yesterday's correction missed by less. Each row uses the same four people and cutoffs.

| Stage of the cue at the forecast | Cutoffs | Average gain (% of the hardest squeeze) | Range across the four people | People lower / equal / higher with yesterday's practice |
|---|---:|---:|---:|---:|
| First rest | 376 | +0.00152 | +0.00089 to +0.00316 | 4 / 0 / 0 |
| Rise | 400 | +0.07360 | +0.00508 to +0.18285 | 4 / 0 / 0 |
| Hold | 800 | −0.00066 | −0.00149 to −0.00029 | 0 / 0 / 4 |
| Release | 400 | −0.06986 | −0.15969 to −0.02028 | 0 / 0 / 4 |
| Final rest | 392 | 0.00000 | 0.00000 to 0.00000 | 0 / 4 / 0 |

Yesterday's correction helped during the rise and hurt during the release, for every person, and the two nearly cancelled. All eleven forecasts were made at 592 cutoffs on each of twelve second attempts. At 30% the target adjustment is zero by construction, and during the final rest both corrections multiply a cue change of zero.

## What it does not show

The 7,104 overlapping forecasts come from four adults at three targets. The people, and their results in study 21, were known before the new day's recordings were chosen. The study saw one step from one recording day to the next, with a fixed order of repeats: it cannot say how long a correction lasts, or whether it carries to a new person or task. No group was set aside for this study.

[Explore all targets, stages and forecasts](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-carry/) · [Compare your own two days on your computer](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/) · [Offline reader for Windows, macOS and Linux](../../docs/cemhsey-transfer/CEMHSEY-Pinch-Transfer.zip) · [Results file](RESULTS.json)
