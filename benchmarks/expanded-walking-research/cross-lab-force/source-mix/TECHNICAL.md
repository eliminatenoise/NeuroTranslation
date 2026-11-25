# Native force impulse across fitting sources

The paired-belt study compares two 150-window fits and a 222-window fit on the same nine held participants. [Paired-belt methods and results](paired-belts/TECHNICAL.md)

A separate Dijon cohort tests the published methods and weights on native overground plate histories. [Dijon evaluation protocol and scores](dijon/TECHNICAL.md)

Adding a mixed-activity archive to overground walking increased the recurrent correction’s error by **0.2033 N·s** on the separate treadmill archive and reduced it by **0.3296 N·s** on three held participants from the mixed-activity archive. The setting is retrospective. [Simple edition](SIMPLE.md) · [Aggregate scores](results.json)

## Inputs and split

Each input is ten successive 20-sample means of signed upward force from a single plate or belt at 1 kHz, up to and including issue tick $t$. Impulse is $\sum_{i=1}^{100} F_{t+i} / 1000$ in N·s. We retained the verified positive loading direction in both fitting sources. Watch, muscle-voltage and motion data were outside this study.

The walking fit has 1,728 windows from 36 recordings of 12 people in Van Criekinge and colleagues’ healthy overground cohort. The additional fit has 5,763 windows from six people in Ghaffarzadeh and colleagues’ force-plate study, including walking, jogging, running, heel drops and step drops. All mixed fits weight the two archives equally. Within an archive, weight is equal across people and then recordings.

The external check uses the exact 384 belt windows from eight people who walked at 4 km/h in Krumm and colleagues’ recorded treadmill cohort. No fit includes that archive. The second check uses 2,537 force windows from three other people in the Ghaffarzadeh study. Their recordings were excluded from both fits. [Overground dataset](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Mixed-activity dataset](https://doi.org/10.5281/zenodo.17376717) · [Treadmill dataset](https://doi.org/10.17605/OSF.IO/KCQTF)

## Methods and scores

Persistence multiplies the last mean by 0.1 seconds. The trend rule extrapolates the last two bin means from their centres. Ridge regression and a single-layer 24-state gated recurrent unit learn a correction to persistence. The direct recurrent variant uses the same network and estimates impulse without adding persistence. Each recurrent network has 1,969 parameters. The reported recurrent forecast averages three independently initialized networks. [Fit specification](METHOD.md)

Values below are average absolute errors in N·s. We average rows within recording, recordings within participant, and participants within each cohort.

| Method | External treadmill | Other people from mixed-activity lab |
| --- | ---: | ---: |
| Persistence | 11.188 | 2.980 |
| Recent trend | 9.644 | 4.081 |
| Frozen Research Edition, three passes | 10.692 | — |
| Walking-only ridge correction | 9.270 | 4.148 |
| Mixed ridge correction | 10.720 | 4.165 |
| Walking-only recurrent correction | 8.717 | 3.277 |
| Mixed recurrent correction | 8.920 | 2.947 |
| Mixed direct recurrent forecast | 9.231 | 2.839 |

For the walking-only recurrent correction against trend, the treadmill gain was 0.9277 N·s. The middle 95% of 4,000 paired resamples by participant was −0.6610 to 2.6948. For mixing versus walking-only correction, the gain was −0.2033 N·s on the treadmill, with interval −0.5627 to 0.2226, and 0.3296 N·s on the mixed-activity lab, with interval 0.1854 to 0.5822. The three-person interval describes resampling those three participants. The archived scores include each individual seed’s average. [Scores and counts](results.json)

The full-model comparison reuses its previously sealed three-pass predictions on identical treadmill rows. This comparison does not isolate model size, objective or training inputs. Both archives were previously scored. An initial implementation incorrectly reversed already upward-positive force in the mixed-activity source. The accepted fit uses the verified source polarity and preserves the original settings and rows. Its forecasts were sealed before scoring the corrected run. The reserved final tests were not opened.

The browser exercise embeds the fitted arrays and scores from the published archives. It runs with ten signed force means and displays impulse for all seven methods. **Download this page** saves the same HTML with the weights and runtime included. A Node.js run of the browser’s JavaScript on 22,767 previously evaluated inputs found a maximum absolute difference of 0.000024 N·s from the sealed reference forecasts. The comparison checked each of the three recurrent predictions before averaging. The test table reports the original measured-data errors. [Run the browser exercise](https://eliminatenoise.github.io/NeuroTranslation/force-forecast/) · [Page source and build script](browser/)

The bundle contains the fitted variants, the NumPy runner, launchers for Linux, macOS and Windows, and the aggregate scores. It includes generated example inputs. The extracted runner and the Linux launcher were tested with Python 3 and NumPy. [Setup and example](SIMPLE.md#run-an-example) · [Download the models and runner](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/expanded-walking-research/cross-lab-force/source-mix/Force-Source-Mix.zip)
