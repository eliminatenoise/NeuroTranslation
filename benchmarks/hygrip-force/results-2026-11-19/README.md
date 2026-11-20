[The studies](../../README.md) › Study 11 · Paced grip: brain signal

# Scalp EEG raised the grip-sensor error for all three people

The hand has already started squeezing in time with the cue. For three test people, a straight-line fit on the sensor's recent readings and the cue schedule forecast its voltage 120 ms ahead with an error of **0.3601 mV**. Given scalp EEG as well, it missed by **0.4613 mV**, and all three people did worse. EEG from the next trial, 0.4228 mV, and EEG from 400 ms earlier, 0.3850 mV, both beat the correctly timed EEG.

Every score here is the measure that punishes large misses (root mean squared error), in millivolts of the sensor's output: volts multiplied by 1,000. The target and the fitted models work in volts, and the release has no conversion to newtons. EEG is electrical activity of the brain, picked up on the scalp. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small.

| Forecast | Seven fitting people, each scored by a fit without them (mV) | Three test people (mV) |
| --- | ---: | ---: |
| Cue timing only | 0.854152 | 0.889869 |
| Repeat the last voltage | 0.531851 | 0.516850 |
| Carry the last 80 ms of change forward | 0.558423 | 0.496622 |
| Sensor history and timing | 0.393763 | 0.360083 |
| Sensor history, timing and scalp EEG timed to the forecast | 0.417955 | 0.461331 |
| Sensor history, timing and EEG from the next trial | 0.402970 | 0.422755 |
| Sensor history, timing and EEG from 400 ms earlier | 0.415367 | 0.384986 |

Every person counts equally in the group's score. Within a person, trials count equally, and each forecast counts equally within its trial: for each person, the square root of the weighted average squared error, then the average of those roots.

## EEG lost to both of its controls

The next-trial control takes EEG from the next right-hand trial of the same person and protocol, at the same time after Go. The earlier control takes the same trial's EEG, ending 400 ms sooner, so its history does not overlap the timed window. Both keep the original trial's force inputs and target. The pass rule set before scoring required timed EEG to lower the average error against the history fit and against both controls.

| Test people: timed EEG minus | Average change (mV) | 95% range of the change across the three people (mV) | People lower / higher / tied |
| --- | ---: | ---: | ---: |
| The history fit | +0.101248 | [−0.276644, +0.479140] | 0 / 3 / 0 |
| EEG from the next trial | +0.038576 | [−0.039377, +0.116528] | 0 / 3 / 0 |
| EEG from 400 ms earlier | +0.076345 | [−0.295544, +0.448234] | 2 / 1 / 0 |

The rule failed in both groups: timed EEG raised the average error against all three comparisons, among the fitting people and the test people alike. Against the earlier control, two test people did better with timed EEG and one worse, but the average still favoured the earlier control. All three ranges for the test people include zero. With three people, even three out of three going the same way would happen by chance one time in four (the 0.25 in the results file), so no row rules out chance.

## Who was scored

Seven of the eight people assigned to fitting passed the clock check. One whole run, still assigned to fitting, was withheld because the intervals between its paired Go markers on the force and EEG clocks differed by 249.5 ms, over the 40 ms limit set in advance. The seven usable fitting people supplied **79 right-hand trials and 16,195 scored forecasts**. Their scores come from fits that each left one person out; the same fits chose the penalties. The models were then fitted on all seven and fixed before the test people were scored.

All three test people passed the same check. All **39 right-hand trials and 7,995 scheduled forecasts** were scored, with the same rows for every version, using the fixed weights and settings. The three people set aside were not opened. The plan was published before anything from the test people was seen; the split and the original design had been fixed before any waveform was read, followed by a check on the fitting recordings only and an amendment before fitting. [The plan, with this study's background](../README.md) · [Record of when the plan was published](https://github.com/eliminatenoise/NeuroTranslation/actions/runs/44432686103)

## What the forecast uses

HYGRIP measured a hand-held sensor during power grip paced by a cue on a screen. The nominal cue schedule follows Go and is a timing input; the reference actually shown on the screen, and when it was shown, were not measured. The target is the released signed sensor voltage exactly six samples ahead on the 50 Hz force grid. The EEG was released at 1 kHz, and its window ends at least 20 ms before the forecast's time on the released clocks. That designed margin leaves the physical synchronisation, the phase of the filters and the delay of a live system unmeasured. [HYGRIP descriptor](https://doi.org/10.3389/fnins.2020.00919) · [Figshare version 1 data and licence](https://doi.org/10.6084/m9.figshare.12383639.v1)

## What it does not show

Three people cannot show how large the effect would be in anyone else, or even which way it would go. Nor can the result say where the scalp signal came from, or what EEG would add in another task.

## Open it

[Open the voltage forecast](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) · [Download the offline page and launchers](HYGRIP-voltage-forecast-20261119-r2.zip) · [The plan as published before the test people were scored](https://github.com/eliminatenoise/NeuroTranslation/blob/dd3526d4e5d67986febe01983dbdf875504d6643/benchmarks/hygrip-force/DESIGN.json) · [Results file, unrounded](AGGREGATES.json)

The page starts with an invented example and runs three fixed models fitted on the seven fitting people: timing, sensor history, and sensor history with timed EEG. Its numbers are forecasts of invented inputs; the tables above come from the measured HYGRIP study. The offline ZIP has launchers for Windows, macOS and Linux, input instructions and the same readable HTML and JavaScript as the hosted page. Open a compatible JSON window on your computer, or open the example. [SHA-256 checksums](SHA256SUMS)

The recordings are HYGRIP, described by Pablo Ortega, Tong Zhao and A. Aldo Faisal and deposited under the MIT licence. Full credit: [docs/RIGHTS.md](../../../docs/RIGHTS.md).
