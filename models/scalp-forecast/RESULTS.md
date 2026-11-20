# The cue forecast was hard to beat

A person sees an instruction to move the arm. We asked whether six scalp electrodes could add anything to what the instruction and the first quarter-second of measured movement already told us. Across 210 trials from five people, the forecast errors were **0.50856 with the scalp signals and 0.50853 without them**. Three people had slightly lower error with scalp signals. Two had higher error. The average difference was +0.00003, with an exploratory paired 95% interval from −0.00105 to +0.00137.

A simpler forecast used the typical movement after each instruction, learned from the seven fitting participants. It scored **0.49278** and came closer than the six-electrode model in four of the five people. Predicting no change scored 0.56489. The scalp model improved on that last forecast by 9.97% and did so for every person. The cue and early movement history already account for nearly all of that gain in this comparison.

## Does the trial's own scalp recording matter?

We exchanged scalp recordings between trials from the same participant, run and instruction, leaving each trial's actual arm readings and future movement in place. Error shifted from 0.50856 to 0.50877. A separately trained model that had learned from those wrong pairings scored 0.50882 when given wrong pairings at assessment. The small differences fell short of the 5% improvement required for all-participant evidence.

Adding the three eye channels to the cue and mechanics gave an error of 0.50965. Giving the model the scalp channels as well brought it to 0.50876, with a reduction for two of the five people. The training recordings had already shown that some scalp and eye signals covary. These forecasting comparisons give no consistent evidence that the scalp voltages supplied additional movement information beyond the early measurements and cues. The experiment cannot identify the biological source of a voltage change.

The five fourth runs came from people whose earlier recordings had appeared in a separate mechanical study. They contributed no training or normalization data here. The task was a seated participant's supported right arm, seven instructions, three movement instruments and one laboratory. The figures are offline errors against those instruments. A quarter-second of stored signal does not establish the timing of the participant's perception, the start of a movement or the performance of a live controller. [Source experiment](https://doi.org/10.1371/journal.pone.0182578) · [Released recordings](https://doi.org/10.5281/zenodo.834976)

## Errors across people

Lower scores mean closer forecasts. An error of one is one training standard deviation, averaged over nine separately scaled changes. The development column holds out one of the seven fitting participants in turn. The fourth-run column gives each of the five assessment participants equal weight.

| Forecast | Development | Fourth runs |
|---|---:|---:|
| Six scalp electrodes, cue and mechanics | 0.3877 | 0.5086 |
| Three eye channels, cue and mechanics | 0.3871 | 0.5097 |
| Cue and mechanics | 0.3864 | 0.5085 |
| Scalp, eyes, cue and mechanics | 0.3885 | 0.5088 |
| Three bilateral scalp differences, cue and mechanics | 0.3898 | 0.5078 |
| Scalp signals alone | 0.4512 | 0.5716 |
| Eye signals alone | 0.4502 | 0.5775 |
| Mismatched-training scalp fit, correctly paired input | 0.3872 | 0.5082 |
| Mismatched-training scalp fit, mismatched input | 0.3871 | 0.5088 |
| Scalp forecast, mismatched scalp | 0.3877 | 0.5088 |
| Combined forecast, mismatched scalp | 0.3885 | 0.5089 |
| Linear fit with scalp, cue and mechanics | 0.4381 | 0.5307 |
| Linear fit with cue and mechanics | 0.4324 | 0.5286 |
| Typical change for the cue (median) | 0.3693 | 0.4928 |
| Average change for the cue (mean) | 0.4099 | 0.5269 |
| Zero change | 0.4415 | 0.5649 |

## What the difference amounts to

The differences below compare errors on the same person, then average across people. A negative difference favors the first forecast. The interval comes from 10,000 resamples of whole participants. Five people provide limited precision. Each comparison needs at least a 5% reduction in overall error and a reduction for every participant to pass its prespecified gate.

| Forecast | Compared with | Difference | Exploratory 95% interval | People with lower error | Gate |
|---|---|---:|---:|---:|---|
| Six scalp electrodes, cue and mechanics | Cue and mechanics | +0.0000 | -0.0010 to +0.0014 | 3/5 | Missed |
| Six scalp electrodes, cue and mechanics | Scalp forecast, mismatched scalp | -0.0002 | -0.0008 to +0.0004 | 3/5 | Missed |
| Six scalp electrodes, cue and mechanics | Mismatched-training scalp fit, mismatched input | -0.0003 | -0.0026 to +0.0015 | 2/5 | Missed |
| Six scalp electrodes, cue and mechanics | Three eye channels, cue and mechanics | -0.0011 | -0.0041 to +0.0026 | 4/5 | Missed |
| Three bilateral scalp differences, cue and mechanics | Three eye channels, cue and mechanics | -0.0018 | -0.0068 to +0.0031 | 3/5 | Missed |
| Scalp, eyes, cue and mechanics | Three eye channels, cue and mechanics | -0.0009 | -0.0028 to +0.0005 | 2/5 | Missed |
| Scalp, eyes, cue and mechanics | Combined forecast, mismatched scalp | -0.0001 | -0.0009 to +0.0007 | 3/5 | Missed |
| Six scalp electrodes, cue and mechanics | Linear fit with scalp, cue and mechanics | -0.0222 | -0.0320 to -0.0105 | 5/5 | Missed |
| Six scalp electrodes, cue and mechanics | Linear fit with cue and mechanics | -0.0200 | -0.0298 to -0.0089 | 5/5 | Missed |
| Six scalp electrodes, cue and mechanics | Typical change for the cue (median) | +0.0158 | +0.0035 to +0.0278 | 1/5 | Missed |
| Six scalp electrodes, cue and mechanics | Average change for the cue (mean) | -0.0184 | -0.0278 to -0.0085 | 5/5 | Missed |
| Six scalp electrodes, cue and mechanics | Zero change | -0.0563 | -0.0772 to -0.0354 | 5/5 | Pass |
| Scalp signals alone | Eye signals alone | -0.0058 | -0.0074 to -0.0044 | 5/5 | Missed |

## Error on the instrument's scale

For the six-scalp forecast with the cue and movement history, the mean absolute error is shown below in each instrument's native units. The original files leave physical units unspecified. Numerical values cannot be compared across these three columns as if they were on a common biological scale.

| Time after cutoff | Elbow | Forearm | Index glove |
|---|---:|---:|---:|
| 0.5 s | 0.081196 | 0.02629 | 0.0010333 |
| 1.0 s | 0.23689 | 0.18661 | 0.0036185 |
| 1.5 s | 2.4057 | 2.1875 | 0.039564 |

The full numerical reports give every method's nine native-unit errors, alongside paired differences sorted independently for each comparison. [Development](development-summary.json) · [Fourth runs](assessment-summary.json) · [Protocol](PROTOCOL.md)

