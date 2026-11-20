# The hand's own history is the forecast to beat

Every study in this repository asks one question of one open dataset. Most ask the same one: a model already knows something about a movement, so does one more signal help it forecast what comes next?

Mostly it does not. A model fitted to the target's own recent history beat "repeat the last value" every time it was tried on the task it was fitted for. A brain signal from the scalp, added on top, usually made the forecast worse. A muscle signal helped at the wrist, and nowhere else beyond the noise; the general model, given the same muscle signal at the wrist, got worse. And when the task or the target moved, a one-line rule beat every fitted model.

This page holds the numbered table and what it adds up to: 25 studies in 20 folders here (two folders hold more than one), two more studies that are reported only in the papers, and two rows that are not tests, each in a folder of its own: the general model's five-sensor walking fit (`daily-sports-limbs/`) and a correction scored on the people the wrist models were fitted on (`wrist-forearm-correction/`). Every count on this page is a count of those numbered rows.

Later studies are listed at the end of this page, outside the numbered counts. [The README](../README.md) has the short version.

## How to read the numbers

Every score in the numbered table is an error: how far the forecasts fell from what was measured. Lower is better. Studies 1 to 13 and 28, and row 29, use the measure that punishes large misses (root mean squared error), studies 14 to 23 and 26, and the general model's fit in row 27, the plain average miss (mean absolute error), and studies 24 and 25 a squared error in units scaled to the data. Study 20 scores bands, not forecasts, and has a note of its own below.

"Tested on" names people whose test recordings were never used to fit the model. Rows 25 and 27 are the exceptions: both are scored on the recordings they were fitted on, and the table says so. Row 29 scores each person with models fitted on the other five, but all six are the people studies 1 to 3 and 28 were fitted on, so it is not a test either. A forecast that "repeats the last value" does nothing clever: it says the reading being forecast will equal the latest one. Where a cell says "not given", the study's results file does not hold that count.

A *straight-line fit* is the plainest kind of model, a weighted sum of its inputs. A *learned forecast* is a small network that reads a stretch of recent history. A *transformer* is a kind of network that learns which of the earlier readings matter most to the forecast, the same kind that runs today's chatbots: study 26 tried a small one, and the general model is built round one too.

**EEG** is electrical activity of the brain, picked up on the scalp. **EMG** is electrical activity of muscle, picked up on the skin. It is a recording of muscle, not of nerve. **MVC** is the hardest squeeze a person could manage that day; pinch force is given as a percentage of it.

Units and measures change from study to study. Compare along a row, never between rows. Each study's own page gives its measure, its plan and its results file.

## Every study

### Wrist angle

Errors in degrees, both wrist axes together. Row 29 enters none of the counts below.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Wrist pointing: brain signal on a learned forecast](wrist-pointing-temporal/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) | The two wrist angles a quarter of a second ahead (250 ms), at six moments after the cue | 3 people (fitted on 6 others) | Learned forecast from wrist history: **4.053°** | The same with scalp EEG added: **4.523°** | 0.469° higher | not given |
| 2 | [Wrist pointing: muscle signal on a straight-line fit](wrist-pointing-muscle/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-pointing/) | The same two wrist angles, 250 ms ahead | the same 3 (fitted on 6 others) | Straight-line fit on wrist history: **6.530°** | The same with forearm EMG added: **6.174°** | 0.355° lower (0.232 to 0.469 lower) | not given (the change stays negative whichever person is left out) |
| 3 | [Wrist pointing: muscle signal on the learned forecast](wrist-forearm-transfer/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) | The same two wrist angles, 250 ms ahead | the same 3 (fitted on 6 others) | Learned forecast, corrected from wrist motion: **3.957°** | The same correction with EMG added: **3.853°** | 0.104° lower (0.072 to 0.125 lower) | 3 of 3 |
| 28 | [Wrist pointing: the general model with muscle and brain signals](paired-wrist-forecast/) | The same two wrist angles, 250 ms ahead, at six moments after the cue | the same 3 as study 1 (fitted on 6 others) | The general model on wrist history: **5.432°** | The same model fitted with forearm EMG added: **5.866°** | 0.434° higher (0.400 to 0.467 higher) | not given (the change stays positive whichever person is left out) |
| 29 | [Wrist pointing: a muscle correction, scored on the people used for fitting](wrist-forearm-correction/) | The same two wrist angles, 250 ms ahead, at six moments from 0.75 to 2 seconds after the cue | nobody new: the 6 people studies 1 to 3 and 28 were fitted on, each scored by models fitted on the other five | Learned forecast, corrected from wrist motion: **3.665°** | The same correction with forearm EMG added: **3.549°** | 0.116° lower (0.083 to 0.131 lower) | 6 of 6 |
| 4 | [Everyday tasks: wrist angle from the muscle signal](uji-wrist-emg/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) | The two wrist angles at least 250 ms after the last EMG sample, during 26 everyday activities | 4 people (fitted on 14 others) | Which activity it is and how long it has run: **36.187°** | The same with EMG added: **34.718°** | 1.468° lower (0.016 to 2.936 lower) | 3 of 4 |

Ranges: study 1, the results file gives no range across people; studies 2, 3 and 28, whichever one of the three people is left out; study 4, the middle 95% when the four people are resampled; study 29, whichever one of the six people is left out.

Study 28 holds the general model's first fits on a recording that also has muscle and brain signals: three fits, one for each set of inputs, on the six people studies 1 to 3 were fitted on, scored on those studies' three test people (959 of their 960 trials; one trial that had been published as an example elsewhere was removed). The straight-line fits beside them are study 2's own fits, re-scored on the same trials: they are not new, and they count nowhere.

| What the forecast read | The general model | Study 2's straight-line fit, re-scored |
| --- | ---: | ---: |
| Wrist history | **5.432°** | 6.530° |
| Wrist history and forearm EMG | **5.866°** | 6.174° |
| Wrist history, forearm EMG and scalp EEG | **5.822°** | 6.127° |
| Wrist history and forearm EMG, the EMG taken from the next trial | **5.867°** | 6.940° |
| Wrist history, EMG and EEG, the EEG taken from the next trial | **5.826°** | 6.378° |

Repeating the last angle scored 7.924°. Study 1's learned forecast, which reads only the wrist's history, re-scored on the same trials, scored 4.053°: lower than every fit above. EMG made the general model worse whichever of the three people was left out (0.400 to 0.467 higher). Given the next trial's EMG instead of its own, the general model's error rose by only 0.0009°, and given the next trial's EEG, by 0.0046°; the straight-line fits rose by 0.766° and 0.252°. The straight-line fits depended on each trial's own electrical signals; the general model hardly did. The study set no pass rule.

In row 29, each of the six people was scored in turn by models fitted on the other five: a learned forecast of study 1's design (3.618°), then the same forecast with a correction learned from its mistakes on the other five, from wrist motion alone (3.665°) or with forearm EMG as well (3.549°), over 1,879 trials. The EMG correction beat the motion-only one for 6 of 6 people, but against the uncorrected forecast only 3 of 6 did better. It helped early, 0.75 and 1 second after the cue (at 0.75 seconds, 6.949° against 7.441°), and made the forecast worse at the four later moments. Given another person's EMG the correction scored 3.828°, and given its own EMG in reverse order, 3.720°. The folder notes that movement and the contact of the electrodes can both change the EMG reading, and that neither control tells the two apart.

### Elbow angle

Errors in degrees.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 5 | [Hand to mouth: one person's muscle signal, another's elbow](surface-emg-elbow/) | The elbow angle 40 ms ahead, during five hand-to-mouth movements | 1 person (fitted on 1 other) | The average path, started when the movement starts: **30.77°** | EMG alone, fitted on someone else: **62.36°** | 31.59° higher (one test person; the EMG fit lost in all five repetitions) | 0 of 1 |

The table gives the measure that punishes large misses (root mean squared error). On the plain average miss the EMG fit lost as well: 58.24° against 26.37° for the timed average path and 25.10° for one fixed angle. The person and the arm changed together, left arm to fit and right arm to test, so the study cannot say which of the two broke the fit.

### Palm position

Errors in millimetres, along the one sideways axis the tracker reports.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 6 | [Palm, first try: brain signal alone](scalp-eeg-hand/) | Sideways palm position 10 ms after the last EEG sample, at nine moments after the cue | 1 person (fitted on 1 other) | The time within the task and nothing else: **7.383 mm** | Scalp EEG alone: **7.514 mm** | 0.131 mm higher (0.093 to 0.148 higher) | 0 of 1 |
| 7 | [Palm: brain signal on top of hand history](scalp-eeg-palm-history/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay) | Sideways palm position 100 ms ahead, at nine moments in each trial | 3 people (fitted on 3 others) | Time, and where the palm has been: **1.093 mm** | The same with EEG added: **1.223 mm** | 0.131 mm higher (0.030 to 0.170 higher) | 0 of 3 |
| 8 | [Palm: adjusted on the person's first recording](scalp-eeg-personal-calibration/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/index.html#personal-calibration) | The same, on each person's second recording | 3 new people, on their second recording | The model with EEG, as fitted on other people: **1.849 mm** | The same model, adjusted on the person's own first recording: **1.700 mm** | 0.150 mm lower (0.069 to 0.284 lower) | 3 of 3 |

Ranges: study 6, whichever one test trial is left out; studies 7 and 8, the smallest and largest change among the three people.

### Grip force during a lift

Errors in newtons.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 9 | [Pinch and lift: grip force](way-grip-force/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) | Grip force 120 ms ahead, on a schedule tied to the go cue | 3 people (fitted on 6 others) | Force and motion history: **0.4442 N** | The same with EEG added: **0.4402 N** | 0.0040 N lower | 2 of 3 |
| 10 | [Pinch and lift: grip force, timed from the squeeze](way-contact-force/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) | Grip force 120 ms ahead, at five moments after the plates register a squeeze | the same 3 (fitted on 6 others) | Force and motion history: **0.6770 N** | The same with EEG added: **0.6955 N** | 0.0185 N higher (from 0.0034 lower to 0.0404 higher) | 0 of 3 |

Ranges: study 9, the results file gives no range; study 10, a 95% interval across the three people.

### Sensor voltage during a paced grip or a finger press

Errors in millivolts. Neither dataset says how many newtons a volt is, so these are errors in the sensor's voltage, not in force.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 11 | [Paced grip: brain signal](hygrip-force/results-2026-11-19/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | The grip sensor's voltage 120 ms ahead, during ten paced squeezes per trial | 3 people (fitted on 7 others) | Cue timing and recent voltage: **0.3601 mV** | The same with EEG added: **0.4613 mV** | 0.1012 mV higher (from 0.2766 lower to 0.4791 higher) | 0 of 3 |
| 12 | [Paced grip: muscle signal](hygrip-force/forearm-results/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | The same as study 11 | the same 3 | Cue timing and recent voltage: **0.3601 mV** | The same with EMG added: **0.3455 mV** | 0.0146 mV lower (from 0.1203 lower to 0.0912 higher) | 1 of 3 |
| 13 | [Paced grip: a fit that changes with the cue](hygrip-force/cue-phase/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | The same as study 11 | the same 3 | The plain fit on recent voltage: **0.3601 mV** | A fit allowed to differ between squeeze and rest: **0.3741 mV** | 0.0140 mV higher (from 0.0171 lower to 0.0451 higher) | 0 of 3 |
| 14 | [One finger: muscle signal](hyser-index/RESULTS.md) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The index-finger sensor's voltage 120 ms ahead, during freely chosen presses | 4 people (fitted on 12 others) | The sensor's last 41 readings: **14.355 mV** | The same with EMG added: **14.457 mV** | 0.103 mV higher (from 0.115 lower to 0.321 higher) | 2 of 4 |
| 15 | [One finger: next-day adjustment](hyser-index/crossday/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The same, on the person's second recording day | the same 4, on their second day | The shared model, unchanged: **14.912 mV** | Adjusted on the person's own first day: **15.091 mV** | 0.180 mV higher (0.171 to 0.188 higher) | 1 of 4 |
| 16 | [One finger: the other four fingers](hyser-index/whole-hand/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The same as study 14 | the same 4 | Index-finger history: **14.355 mV** | The other four fingers' histories added: **14.161 mV** | 0.193 mV lower (from 0.573 lower to 0.187 higher) | 2 of 4 |
| 17 | [One finger: new task](hyser-index/prescribed/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The same voltage, during 15 prescribed finger combinations | the same 4, on a task the models never saw | Index-finger history: **7.992 mV** | Five fingers' histories: **7.802 mV** | 0.190 mV lower (0.124 to 0.279 lower) | 4 of 4 |

Ranges: studies 11 to 13, a 95% interval across the three people; studies 14, 16 and 17, the middle 95% when the four people are resampled; study 15, the middle 95% when the two donor pairs are resampled, which is not a range across people.

### Pinch force between two fingers

Errors in % of the hardest squeeze the person could manage that day (their MVC, maximum voluntary contraction).

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 18 | [Pinch: muscle signal](cemhsey-pinch/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) | The gauge reading 120 ms ahead, during a pinch held at 30% of the hardest squeeze | 4 people (fitted on 3 others) | Force history and the on-screen cue: **0.4634%** | The same with EMG added: **0.4632%** | 0.0002% lower (from 0.0007 lower to 0.0005 higher) | 3 of 4 |
| 19 | [Pinch: five electrode grids](cemhsey-arrays/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) | The same as study 18 | 4 new people (fitted on the same 3) | EMG as one overall amplitude: **0.51663%** | EMG as five separate grids: **0.51659%** | 0.00004% lower (from 0.00110 lower to 0.00102 higher) | 2 of 4 |
| 20 | [Pinch: width of the band](cemhsey-intervals/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/) | A band meant to hold 90% of the gauge readings 120 ms ahead | 2 people (band widths set on 4 others) | One band width for the whole pinch, around the five-grid forecast: **2.21%** wide, 4476 of 4736 later readings inside | A width for each part of the pinch: **2.16%** wide, 4502 inside | narrower and holds more; the note below has all three forecasts | not counted per person |
| 21 | [Pinch at new targets](cemhsey-transfer/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/results/) | The gauge reading 120 ms ahead, at a 50% target (10% and 30% were scored too) | 4 people, one day each | A one-line rule: the current reading plus the change the on-screen schedule calls for: **0.5721%** | The fitted five-grid model after one practice pinch: **0.6987%** | 0.1266% higher (0.0502 to 0.1938 higher) | 0 of 4 |
| 22 | [Pinch, next day](cemhsey-carry/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-carry/) | The same, on the next recording day | the same 4, a day later | The fitted five-grid model, corrected on one practice pinch from the new day: **0.70643%** | The same model, corrected on yesterday's practice pinch instead: **0.70578%** | 0.00065% lower (from 0.00391 lower to 0.00249 higher) | 3 of 4 |
| 23 | [Pinch: a correction learned from other people](cemhsey-phase/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/) | The gauge reading 120 ms ahead, at a 50% target | 3 people (corrections fitted on 3 others) | The one-line rule: **0.70007%** | The rule with separate corrections for the rise and the release, learned from 3 other people: **0.69509%** | 0.00498% lower (from 0.05000 lower to no change) | 3 of 3 |

Ranges: studies 18 and 19, the middle 95% when the four people are resampled; studies 21 and 22, the smallest and largest change among the four people; study 23, the range across the three people, which the study gives rounded outwards.

### Arm acceleration while walking

Errors in the units the sensor stores: acceleration along its own three axes, gravity included, not converted to physical units.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 26 | [Walking: a small transformer on an arm sensor](daily-sports-arm/) | The right-arm sensor's three readings 120 ms ahead, from its last 16 readings, while walking | 2 people (fitted on 4 others) | Straight-line fit on the last 16 readings: **0.781** | A small transformer on the same 16 readings: **0.855** | 0.074 higher (higher by 0.046 for one person and 0.101 for the other) | 0 of 2 |

Both forecasts in study 26 beat repeating the last value (1.182). The straight-line fit was lower for both people (0.717 against 0.764, and 0.845 against 0.946) and on both walks, so the transformer failed the pass rule set before scoring. With the first 15 of the 16 readings shuffled, the straight-line fit rose to 1.056 and the transformer to 0.957: both had been using the order of the readings.

Two later comparisons used the same two people again, so they are not fresh tests. The general model, fitted to the right arm alone on the same four people, scored 0.869: behind the straight-line fit for both people, behind the transformer for one (0.837 against 0.764) and ahead of it for the other (0.902 against 0.946). And a comparison of how far ahead to forecast found the straight-line fit with one equation per horizon lowest for both people at every horizon from 120 ms on:

| How far ahead | One straight-line fit for each horizon | One straight-line fit fed its own guesses | A downloaded pretrained model, used as it came | Repeat the last value |
| --- | ---: | ---: | ---: | ---: |
| 40 ms | **0.549** | **0.549** | 0.654 | 0.647 |
| 120 ms | **0.781** | 0.807 | 1.096 | 1.182 |
| 240 ms | **0.880** | 0.913 | 1.487 | 1.685 |
| 480 ms | **0.918** | 1.001 | 1.415 | 1.412 |

The pretrained model is Chronos-Bolt tiny, a forecasting model trained by others on many kinds of time series and downloaded as it is. [The comparison](daily-sports-arm/architecture/README.md) also times each forecast; its closing advice on what to build next is a proposal, not a result.

### The general model's five-sensor walking fit, scored on the people it was fitted on: not a test

Every score here is on the four people the model was fitted on. Nobody was held out, so nothing in this row is a test, and it enters none of the counts below. Errors in the units the sensors store.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 27 | [Walking: the general model's five-sensor fit](daily-sports-limbs/) | Each of five body sensors' three readings 120 ms ahead, from that sensor's own last 16 readings, while walking | nobody new: the 4 people it was fitted on | Straight-line fit made for the left-leg sensor alone: **1.929** | The general model, one fit for all five sensors: **1.837** at the left leg | not a test (scored on the people it was fitted on); the table below has all five sensors | 4 of 4 at the left leg; at most 3 of 4 at the other four sensors |

| Sensor | Repeat the last value | Straight-line fit for that sensor | Study 26's transformer, fitted for the right arm alone | The general model, one fit for all five | People for whom the general model beat every other forecast |
| --- | --- | --- | --- | --- | --- |
| Torso | 1.284 | **0.696** |  | 0.722 | 1 of 4 |
| Right arm | 1.165 | 0.869 | **0.668** | 0.806 | 0 of 4 |
| Left arm | 1.057 | 0.770 |  | **0.727** | 3 of 4 |
| Right leg | 3.150 | 1.967 |  | **1.891** | 3 of 4 |
| Left leg | 3.168 | 1.929 |  | **1.837** | 4 of 4 |

Study 26's transformer, fitted for the right-arm sensor alone on the same four people, was lower than the general model there for all four. The rule set before fitting asked the general model to beat every other forecast for every person, sensor by sensor. That happened at the left leg only. Because the people are the ones it was fitted on, the rule says nothing about a new walker, and the plan itself rules out any such claim.

### Reported only in the papers

No folder under `benchmarks/`: each study is told in the NeuroTranslation paper, and its result file is published with the papers ([`link-macaque.json`](../papers/current/results/link-macaque.json), [`training-diagnostic-summary.json`](../papers/current/training-diagnostic-summary.json)). Both use units scaled to the data, so the numbers mean nothing outside their own row.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 24 | [Macaque fingers from motor cortex (LINK)](../papers/current/neurotranslation-technical.pdf#nameddest=appendix.A) | The position of the index finger, and of the other three fingers as a group, from the brain recording | 1 macaque, 2 later days (fitted on 4 days) | Straight-line fit on the latest brain sample: **0.0314982** | The better of two networks that read recent brain history: **0.0299609** | 0.0015373 lower (0.0003470 to 0.0027587 lower) | one animal |
| 25 | [One network shared by two signals: first run](../papers/current/neurotranslation-technical.pdf#nameddest=sec:self-forecast) | Each signal's own next values from its own past. Nothing is predicted from one signal to the other | nobody: scored on its own training recording | Repeat the last value (glove signal): **0.0245** | One network shared by both signals, after 990 training steps (glove signal): **0.3722** | 0.3477 higher (one recording, no range) | one recording |

Ranges: study 24, the 95% interval given in the paper.

**Which comparison is shown.** The one the study's own plan names as its main one. Where a plan names none, the comparison its results file calls primary. Where a plan fixes a measure but no single comparison (studies 21 to 23), the one the study's own page leads with. Study 15 is the exception: its page leads with the 12 people the model was fitted on, and the table shows the 4 test people, so that studies 14 to 17 all show the same four.

**Study 20 compares bands, not forecasts.** A band is a range meant to hold 90% of the readings that follow. For each of three forecasts the study sets a band whose width is fixed for each part of the pinch against one width for the whole pinch, on the same 4736 readings from two people.

| Band around | One width: how wide, readings inside, score | A width per part of the pinch: how wide, readings inside, score |
| --- | --- | --- |
| "Repeat the last value" | 2.89%, 4493, 3.32 | 2.54%, 4499, 2.90 |
| The fit on force history and the cue | 2.20%, 4466, 2.60 | 2.15%, 4494, 2.47 |
| The five-grid fit | 2.21%, 4476, 2.60 | 2.16%, 4502, 2.48 |

The score charges a band for its width and for every reading it misses, so lower is better. All six bands held more than the 90% asked of them over the whole pinch (94.3% to 95.1%). All six fell short while the pinch was being released (86.1% to 89.6%).

## What it adds up to

A "comparison" is one pair of scores on the same forecasts. Several studies share the same handful of people, so the comparisons are not independent of one another; statement 7 says how far that goes. In each table the lower score of the pair is in bold.

### 1. A model fitted to the target's own history beat "repeat the last value" in 9 of 9 studies

| Study | "Repeat the last value" | Fitted to the target's own history |
| ---: | --- | --- |
| 1 | Last angle repeated: 7.925° | Learned forecast on wrist history: **4.053°** |
| 7 | Last palm position repeated: 4.439 mm | Straight-line fit on time and past palm: **1.093 mm** |
| 9 | Last force repeated: 0.7878 N | Straight-line fit on force and motion history: **0.4442 N** |
| 10 | Last force repeated: 1.7173 N | Straight-line fit on force and motion history: **0.6770 N** |
| 11 | Last voltage repeated: 0.5168 mV | Straight-line fit on timing and recent voltage: **0.3601 mV** |
| 14 | Last reading repeated: 17.945 mV | Straight-line fit on the last 41 readings: **14.355 mV** |
| 18 | Last reading repeated: 0.5464% | Straight-line fit on force history and the cue: **0.4634%** |
| 19 | Last reading repeated: 0.64513% | Straight-line fit on force history and the cue: **0.51675%** |
| 26 | Last reading repeated: 1.182 | Straight-line fit on the last 16 readings: **0.781** |

That is every study that scores "repeat the last value" and scores the model on the task it was fitted for. Studies 2, 3 and 28 reuse the people of study 1 and are not counted twice; in study 28 the general model beat it too (5.432° against 7.924°). Study 4 has no "repeat the last value" score. In study 26 the small transformer beat it too (0.855 against 1.182) and lost to the straight-line fit shown here. Rows 27 and 29 are not counted: their people had already been used for fitting.

Two of the nine wins carry a footnote. In study 9, whenever the force to be forecast was at or below 0.5 N, repeating the last force beat every fitted model. In study 7, a straight line through the palm's recent speed beat the fitted model on the plain average miss and lost to it on the measure that punishes large misses.

The fitted models of studies 5 and 6 never saw the target's history. They lost to a fixed average and to a clock.

### 2. Move the task or the target, and a one-line rule won 6 times out of 6

The first one-line rule is "repeat the last value".

| Study | What changed | "Repeat the last value" | Best fitted model |
| ---: | --- | --- | --- |
| 17 | A new task (prescribed presses) | **7.222 mV** | 7.802 mV (five finger histories) |
| 21 | A new target level (10%) | **0.3819%** | 0.5635% (force history) |
| 21 | The fitted level (30%), new people | 0.5461% | **0.4265%** (force history, without the practice pinch) |
| 21 | A new target level (50%) | 0.7369% | **0.6987%** (five grids) |
| 22 | A new target level (10%) on the next day | **0.40148%** | 0.56114% (force history, corrected on yesterday's practice pinch) |
| 22 | The fitted level (30%) on the next day | 0.56534% | **0.44618%** (force history, no correction) |
| 22 | A new target level (50%) on the next day | 0.75791% | **0.70578%** (five-grid fit, corrected on yesterday's practice pinch) |
| 23 | A new target level (50%), new people | **0.81104%** | 0.82204% (five grids with separate rise and release corrections) |

The second rule exists only in the pinch studies, where the screen shows the person a target that changes on a known schedule: take the current reading and add the change the schedule calls for.

| Study | Target | Current reading plus the scheduled change | Best fitted model | People better with the fitted model |
| ---: | --- | --- | --- | --- |
| 21 | 10% | **0.3693%** | 0.5635% | 0 of 4 |
| 21 | 30%, the fitted level | 0.4480% | **0.4265%** | 4 of 4 |
| 21 | 50% | **0.5721%** | 0.6987% | 0 of 4 |
| 22 | 10%, next day | **0.38493%** | 0.56114% | 0 of 4 |
| 22 | 30%, the fitted level, next day | 0.48173% | **0.44618%** | 4 of 4 |
| 22 | 50%, next day | **0.58356%** | 0.70578% | 1 of 4 |
| 23 | 50%, new people | **0.69509%** (with the correction learned from three other people; the plain rule scored 0.70007%) | 0.82204% | 0 of 3 |

At a new task or a new target level there are 6 settings. In all of them one of the two rules beat the best fitted model. The fitted model stayed ahead of plain repeating in 2 of the 6, and ahead of the schedule rule in none of 5. Across those five it was better for 1 person in 19 tries.

The model was not broken. At 30%, the level it had been fitted at, the same new people put it ahead of both rules on both days (2 of 2 settings). It had learned one target.

Study 17 splits by measure: on the measure that punishes large misses, both fitted models beat the last reading. Studies 21 to 23 come from one dataset and largely the same people.

### 3. Scalp EEG lowered the error in 5 of 13 comparisons, and met no pass rule

| Study | EEG added to | Without | With EEG | People better | The same model fed EEG from the wrong trial or moment | Main question? |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Learned forecast that already has wrist history | **4.053°** | 4.523° | not given | EEG from another trial: 4.880° | yes |
| 1 | Straight-line fit that already has wrist history | 6.530° | **6.439°** | not given | EEG from another trial: 6.782° | no |
| 2 | Straight-line fit that already has wrist history and EMG | 6.174° | **6.127°** | not given | EEG from another trial: 6.379° | no |
| 28 | General model that already has wrist history and EMG | 5.866° | **5.822°** | not given | EEG from the next trial: 5.826° | no |
| 7 | Straight-line fit that already has past palm position | **1.093 mm** | 1.223 mm | 0 of 3 | EEG from the next trial: 1.203 mm | yes |
| 8 | Adjusted straight-line fit that already has past palm position | **1.691 mm** | 1.700 mm | 0 of 3 | EEG from the next trial: 1.694 mm | yes |
| 9 | Straight-line fit that already has force and motion history | 0.4442 N | **0.4402 N** | 2 of 3 | EEG from another lift: 0.4388 N | yes |
| 9 | Straight-line fit with force, motion and EMG | 0.4571 N | **0.4546 N** | 1 of 3 | not run | no |
| 10 | Straight-line fit that already has force and motion history | **0.6770 N** | 0.6955 N | 0 of 3 | EEG from the next lift: 0.6919 N | yes |
| 10 | Learned forecast that already has force and motion history | **0.9780 N** | 0.9936 N | 1 of 3 | EEG from the next lift: 0.9873 N | no |
| 10 | Straight-line fit with force, motion and EMG | **0.7168 N** | 0.7220 N | 1 of 3 | EEG from the next lift: 0.7188 N | no |
| 11 | Straight-line fit that already has recent sensor voltage | **0.3601 mV** | 0.4613 mV | 0 of 3 | EEG from the next trial: 0.4228 mV | yes |
| 12 | Straight-line fit with recent sensor voltage and EMG | **0.3455 mV** | 0.4739 mV | 0 of 3 | EEG from the next trial: 0.4453 mV | no |

EEG raised the error in 8 of the 13. Of the 6 that were a study's main question it lowered the error in 1: grip force in study 9, by 0.0040 N, and there EEG taken from a different lift lowered it further.

Twelve of the comparisons also fed the model EEG from the wrong trial or the wrong moment. Properly timed EEG did better than the wrong EEG in 4. It both lowered the error and beat its control in 3: the straight-line wrist fits of studies 1 and 2 and the general model of study 28, all on the same three people, and never as the main question. In study 28 EEG took 0.045° off the error, and the same model given another trial's EEG did only 0.0046° worse than with its own: almost all of the gain survived the swap.

Where the model had no history of the hand at all, EEG lost too: alone against a clock in study 6, and added to elapsed time in study 7.

Four studies set a pass rule for EEG in advance: 6, 9, 10 and 11. All four failed it.

### 4. Forearm EMG lowered the error in 10 of 18 comparisons, clearly only at the wrist

| Study | EMG added to | Without | With EMG | People better | The same model fed EMG from the wrong trial or moment | Main question? |
| ---: | --- | --- | --- | --- | --- | --- |
| 2 | Straight-line fit that already has wrist history | 6.530° | **6.174°** | not given | EMG from the next trial: 6.941° | yes |
| 3 | Learned forecast already corrected from wrist motion | 3.957° | **3.853°** | 3 of 3 | EMG from the next trial: 4.140° | yes |
| 28 | General model that already has wrist history | **5.432°** | 5.866° | not given | EMG from the next trial: 5.867° | yes |
| 4 | Fit that knows the activity and elapsed time (no wrist history) | 36.187° | **34.718°** | 3 of 4 | EMG shifted in time: 35.385° | yes |
| 9 | Straight-line fit that already has force and motion history | **0.4442 N** | 0.4571 N | not given | not run | no |
| 10 | Straight-line fit that already has force and motion history | **0.6770 N** | 0.7168 N | 0 of 3 | not run | no |
| 12 | Straight-line fit that already has recent sensor voltage | 0.3601 mV | **0.3455 mV** | 1 of 3 | EMG moved within the trial: 0.3427 mV | yes |
| 14 | Straight-line fit that already has recent sensor readings | **14.355 mV** | 14.457 mV | 2 of 4 | EMG from another trial: 14.424 mV | yes |
| 18 | Straight-line fit that already has force history and the cue | 0.4634% | **0.4632%** | 3 of 4 | EMG from the other repeat: 0.4640% | yes |
| 19 | Straight-line fit that already has force history and the cue (new people) | 0.51675% | **0.51663%** | 3 of 4 | EMG from the other repeat: 0.51742% | no |
| 19 | Fit that already has force history, the cue and overall EMG amplitude (adds the five grid profiles) | 0.51663% | **0.51659%** | 2 of 4 | Five grids from the other repeat: 0.51737% | yes |
| 21 | Force-history fit after practice, at the 50% target (adds five grids) | 0.7085% | **0.6987%** | 2 of 4 | not run | no |
| 21 | Force-history fit after practice, at the 10% target (adds five grids) | **0.5635%** | 0.5734% | 0 of 4 | not run | no |
| 21 | Force-history fit after practice, at the 30% target (adds five grids) | **0.4274%** | 0.4306% | 0 of 4 | not run | no |
| 22 | Force-history fit corrected on yesterday's practice pinch, at the 50% target, next day (adds five grids) | 0.72046% | **0.70578%** | 2 of 4 | not run | no |
| 22 | Force-history fit corrected on yesterday's practice pinch, at the 10% target, next day (adds five grids) | **0.56114%** | 0.57129% | 1 of 4 | not run | no |
| 22 | Force-history fit corrected on yesterday's practice pinch, at the 30% target, next day (adds five grids) | **0.44688%** | 0.44756% | 2 of 4 | not run | no |
| 23 | Force-history fit with separate rise and release corrections, at the 50% target (adds five grids) | 0.82834% | **0.82204%** | not given | not run | no |

In 6 of the 8 comparisons that were a study's main question, the average error fell. Only in three did the range in the results file stay clear of zero on EMG's side, and all three are wrist studies. A fourth wrist study, 28, stayed clear of zero on the other side: EMG made the general model worse whichever of the three people was left out (0.400 to 0.467 higher).

Studies 2 and 3 are the same three people on one pointing task. The gain holds whichever person is left out, and EMG from the next trial does worse than no EMG. Study 4 is four other people on everyday tasks: three of the four gained, the range only just clears zero, and one of the two wrist axes got worse.

Lower on average but inside the noise, or beaten by mistimed EMG: studies 12, 18 and 19, and the 50% rows of 21, 22 and 23. Higher: studies 9, 10, 14 and 28, and the 10% and 30% targets of 21 and 22. At those two targets in study 21 all four people did worse with the five grids.

Nine comparisons had a wrong-trial or mistimed control. Properly timed EMG beat it in 7 and lost to it in studies 12 and 14. One of the 7 is study 28, by 0.0009°, which is no difference at all.

EMG with no other input, fitted on one person and tried on another, lost to a fixed angle (study 5).

Not counted: row 29, scored on the six people the wrist models were fitted on. There a correction that also read EMG beat the same correction without it for 6 of 6 people (3.549° against 3.665°), but beat the uncorrected forecast for only 3 of 6.

Pass rules set in advance on EMG: study 12 failed; study 18 passed by margins too small to tell from zero; study 19 passed the weaker half of its rule and failed the stronger.

### 5. Adjusting a model to a person, a day or a group lowered the error 5 times in 6, once by more than 1%

| Study | Adjustment | Before | After | People better |
| ---: | --- | --- | --- | --- |
| 8 | Adjust the palm model on the person's first recording | 1.849 mm | **1.700 mm** | 3 of 3 |
| 15 | Adjust the finger-sensor forecast on the person's own day one (4 test people) | **14.912 mV** | 15.091 mV | 1 of 4 |
| 15 | The same adjustment, 12 people the model was fitted on | 17.610 mV | **17.589 mV** | 4 of 12 |
| 21 | One practice pinch at the 50% target (five-grid fit) | 0.6995% | **0.6987%** | 2 of 4 |
| 22 | Reuse yesterday's practice correction instead of none (five-grid fit, 50%) | 0.70804% | **0.70578%** | 3 of 4 |
| 23 | A correction learned from other people, applied to the simple forecast | 0.70007% | **0.69509%** | 3 of 3 |

One comparison is counted per tested group, at each study's main setting. The one that mattered is study 8: a single earlier recording of the same person helped all three people, by 0.150 mm on 1.849 mm. In studies 21, 22 and 23, and in the 12-person half of study 15, the change was under 1% of the error. In the 4-person half of study 15 the adjustment made things worse.

Carrying a model to new people with no adjustment at all worked on the same task in studies 1, 4, 7, 9, 11, 14, 18 and 19: every one beat the simple forecast it was set against, on people it had never seen. That forecast was "repeat the last value", except in study 4, where it was the average angle of the people the model was fitted on: 37.560°, against 36.187° for the fit that knows only the activity and the time. It failed outright in the two one-to-one trials, studies 5 and 6.

### 6. Twelve studies set a pass rule in advance. Eight failed it.

- **Failed:** studies 6, 9, 10, 11, 12, 13, 24 and 26.
- **Split answer:** studies 16 and 19.
- **Passed by a margin too small to tell from zero:** study 18. Both averages were lower, by amounts whose ranges cross zero.
- **Passed:** study 20, on whether a band set per part of the pinch is narrower, holds at least as many readings and scores lower than one width throughout. It was, for all three forecasts. That says nothing about which forecast is better.
- **Set no rule:** the other 15.
- **Not counted:** row 27, the general model's five-sensor walking fit. Its rule, set before fitting, was to beat every other forecast for every person, sensor by sensor, and it held at one sensor of five, the left leg. But it was applied to the people the model was fitted on, and every rule counted here was applied to people held out of the fit.
- **Not counted either:** row 29. Its plan said before fitting that a forearm gain needs the EMG correction to beat both the correction without EMG and the uncorrected forecast. Both held on the overall score, but only 3 of 6 people beat the uncorrected forecast, and all six had been used for fitting before.

Every failed rule concerned EEG, EMG, a cue term or a network set against a plainer fit: the two networks of study 24 and the transformer of study 26. None concerned the plain history fit. No rule about adding a signal to a forecast was passed outright.

### 7. The general model has not yet been tested on a new person, and the evidence is narrower than 29 rows suggest

What exists is 25 separate small studies, each with its own straight-line fit or small network for one signal in one task; one macaque study in which two larger networks failed their pass rule, across 18 runs and 720 saved passes through the fitting data (study 24); and one run of a single network shared by a muscle signal and a glove signal, on one recording, which lost to "repeat the last value" on its own training data and predicts nothing from one signal to the other (study 25).

That shared network was an earlier, separate attempt. The general model being built now, NeuroTranslate 0.0, had its first five fits to real recordings on 20 November:

- Two on the walking data of study 26, with motion sensors only. One fit forecast five sensors on the body and was scored only on the four people it was fitted on (row 27): it beat repeating the last value at all five and met its own rule at one, the left leg. An earlier version, fitted to the right arm alone, was scored on study 26's two test people, who had already been scored once, and lost to the straight-line fit for both (0.869 against 0.781).
- Three on the wrist data of studies 1 to 3, with muscle and brain signals (study 28), scored on the three people those studies had already scored. Forearm EMG made the forecast worse (5.432° to 5.866°). Scalp EEG on top brought it to 5.822°, but another trial's EEG did almost as well (5.826°). Study 1's learned forecast, which reads only the wrist, beat all three (4.053°).

A shared fit, published after the numbered table and in no count here, learned a headset's tracking of people's wrists (HoloAssist) and the rat study's tracking at once; it beat the same model fitted on either dataset alone by margins within the noise, and lost to a straight-line fit on the rat ([`models/`](../models/)). A wrist-angle task added to it later was scored on the six people studies 1 to 3 were fitted on, like row 29, and did worse than row 29's correction (4.291° with EMG, against 3.549°). A correction fitted on top of that task, with forearm EMG, reached 4.054°, still above row 29; row 29's model, refitted on all six people, is now a download ([`models/wrist-specialist/`](../models/wrist-specialist/)).

No fit of the general model has been tested on a new person, so nothing here yet translates between nerve, muscle and movement.

The project's working presumption is that more data, and more varied data, gives a more general model. No study of the numbered table tests it: none varies how much data a model sees, or how varied it is. The general model's fits in the table do not test it either. The five-sensor fit has no comparison with a fit on less data, and at the one sensor where a separate network exists, the right arm, the separate network was better. At the wrist, more kinds of signal did not help it.

The test groups are small, between 1 and 4 people. And the 25 studies draw on 9 datasets and fewer independent groups than that. Studies 1 to 3 and 28 score the same three people (row 29 scores the six people those studies were fitted on). So do 9 and 10, and 11 to 13. Studies 14 to 17 score the same four, and 21 and 22 the same four, who had already appeared in earlier pinch studies on other days. Studies 14 to 17 also score the 12 people the finger models were fitted on; those results are on each study's page, and are not the main comparison in the table above.

Every result comes from stored recordings scored after the fact. None is a live forecast. Every "120 ms" or "250 ms" is a distance along the stored clock.

## Twenty-four people and four recordings were set aside and are still unopened

When each dataset was split, some people were set aside and their recordings never opened. Until one of these groups is opened, every number on this page describes data the project has already looked at.

| Recordings | Studies | Set aside, never opened |
| --- | --- | --- |
| Wrist pointing (EEG-EMG-WristMotion) | 1 to 3 and 28 | 6 people |
| Everyday tasks (KIN-MUS UJI) | 4 | 4 people |
| Hand to mouth (Lucchetti and colleagues) | 5 | 1 person |
| Palm (IACKD) | 6 | 1 person |
| Pinch and lift (WAY-EEG-GAL) | 9 and 10 | 3 people |
| Paced grip (HYGRIP) | 11 to 13 | 3 people |
| One finger (Hyser) | 14 to 17 | 4 people |
| Walking (Daily and Sports Activities) | 26 | 2 people |
| Macaque fingers (LINK) | 24 | 4 recordings |

In the palm data the reserve was named for the first, two-person trial (study 6) and only its description was read. Studies 7 and 8 name no reserve.

In the wrist data, studies 1 to 3 and 28 keep the same six people aside, and row 29 kept them out of its study as well.

In the walking data, study 26 set aside two people. The general model's fit in row 27 opened none of the four people outside its fitting group; two of them are study 26's test people, already scored, and the other two are the pair set aside.

The pinch studies (18 to 23) set nobody aside. Each fixed its test group in advance and scored it once, and the first plan says there is no further group. Later pinch studies reuse people from earlier ones on new days, and say so.

Not known either, because nothing in the repository measures it: any live result; any result in newtons for studies 11 to 17, whose datasets give no conversion from volts; any effect of more or more varied training data on people a model has not seen (the shared fit's comparison of two datasets with one, above, was not scored on such people); any model that predicts one kind of signal from another across datasets; any score of the general model on a person who had not been looked at before.

## Four newer studies: neither a rat's brain cells nor an instructor's words helped, and a sentence rarely found its movement

These were published after the table was made. Each has its own plan and results file, and none is in the table or in any count above. The first two ask the table's question of new signals: does a signal help a forecast that already knows the recent movement? The next two ask something else: given a sentence a person wrote about a movement, can a model find the recording it describes? Those two score each search by how often the right recording came first, so for them a higher score is better, unlike the errors above.

- **[Can brain-cell firing improve a rat’s movement forecast?](wtrack-neural-motion/)** (`wtrack-neural-motion/`). No. A camera tracked a rat running round a W-shaped track while electrodes in its brain picked up electrical spikes, which the recording sorts into 72 sources, each probably one brain cell. A forecast of where the rat would be a quarter of a second later, from its recent positions alone, missed by 2.010 cm on average. With one second of firing added it missed by 2.237 cm, and the positions alone were closer on 7 of the 9 later trips that were scored. Given firing from an earlier trip instead, the same fitted model did worse again (2.429 cm): it used the timing of the firing, and still did not beat the positions. This is one rat in one recording, and five later trips were set aside and never opened.

- **[Can an instructor’s words improve a one-second wrist forecast?](preceding-instructions/)** (`preceding-instructions/`). Not here. A headset tracked a person's right wrist while an instructor talked them through a task. A quarter of a second after each instruction ended, a model forecast how far the wrist would move in the next second, from its recent movement, the task and facts about the finished instruction such as its length. It missed by 9.79 cm on average. Told also which of six recurring words the instruction held ("turn", "on", "off" and the like), it missed by 10.04 cm. Repeating the wrist's movement over the previous second did best, at 7.38 cm. Only 26 forecasts were scored, from seven recordings in four groups (the dataset groups recordings by a code, not by person), and the model was fitted on 44 examples. These recordings had been open earlier, while a different task was built on them, so this is not a fresh test.

- **[Find a recorded hand movement from a sentence](hand-language-retrieval/)** (`hand-language-retrieval/`). Timing beat the hand. A headset tracked the right hand of people doing tasks such as setting up a printer, and observers later wrote a sentence about each step. Given one of those sentences, a model ranked the steps of the same recording, and the score is how often the right step came first: here higher is better. On 60 sentences from ten recordings in six groups kept out of fitting, a model that read the shape and movement of the hand put the right step first 23.89% of the time (a second model, built on attention, the mechanism a transformer uses to weigh one part of its input against another: 23.59%), against 20.66% for a random order. Ranking by each step's length, its place in the recording and how often the hand was tracked, with no hand shape at all, reached 35.56%. The groups are the dataset's recording codes, not verified people, and the same person may appear under different codes. Ten more recordings, in three groups, were set aside and never opened. [Inspect five recorded movements in your browser](https://eliminatenoise.github.io/NeuroTranslation/hand-search/).

- **[Which recording does the sentence describe?](text-motion-retrieval/)** (`text-motion-retrieval/`). The simpler model did better. Volunteers watched recorded whole-body movements, most of them walks, and described each one. Given a description, a model ranked 38 recordings of six performers, as the dataset's catalogue names them, all kept out of fitting, and the score is how often the right recording came first, averaged so that each of the 38 recordings counts equally: higher is better. A model built on attention put it first 5.6% of the time; a simpler one, built on word counts and plain summaries of the movement, 6.6%; a random order, 2.6%. Ranking the recordings by the action name the dataset's catalogue gives each one, matched to the sentence's words, with no movement at all, did better than both: 7.7%. The attention model failed the pass rule set for it in advance, which asked it to beat that ranking too. 31 of the 38 recordings are walks, so many descriptions fit several of them, and the folder says that repeated clips of the same people limit any claim about new people. Another 31 recordings, of four other performers, were set aside and never opened.

A four-page supplement reports the two searches with words together: [*How precisely do words identify a recorded movement?*](../docs/papers/language-and-observed-movement/README.md) It is separate from the two papers, and neither paper's current draft contains these studies.

## Three forecasts from recorded movement

### Where will the knees be 15 stored frames later?

Five snapshots of both hips, knees and ankles predict the two knee angles 15 frames later in a stored 60 Hz treadmill recording. On 40,201 forecasts from 12 held-out walkers, replaying a stride from four seconds of knee history gave 3.54° mean absolute error. The transformer, with 0.4 seconds of joint history, gave 4.46° on the same windows. Six of the 51 recordings used whole-file Xsens HD processing, including test recording S48. The other 45 carry the Live label. Physical prediction latency was never measured. Only reconstructed joint angles entered the forecast. [Fitted model, full comparison and source](../models/knee-motion/) · [Try the knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/)

### Where will the next step land?

Eleven observations at 20 Hz capture half a second of a walk or run. The source cameras recorded at 60 or 120 Hz, so the analysis keeps every third or sixth frame. Across 351 overlapping windows from twelve fresh recordings in six source groups, the model told the action missed the 18 body sites by 69.1 mm on average after removing pelvic translation. Movement alone scored 71.9 mm. In room coordinates the measured centre of the pelvis tells a different story. The linear model missed it by 59.0 mm, the action-labelled model by 66.7 mm. Five groups walked and only one ran. The group numbers need not identify distinct people. Repeating the training-stride retrieval comparison requires rebuilding the gallery from the cited CMU originals. [Method and reproduction](../models/stride-continuation/REPRODUCE.md) · [Results by source group](../models/stride-continuation/fresh-results.json) · [Continue a measured stride](https://eliminatenoise.github.io/NeuroTranslation/stride/)

### How far will another rat move?

Three rats supplied the training data. On three different rats, 549 forecasts estimated the straight-line distance between the last observed camera position and the first frame at least a quarter of a second after the cutoff. Each rat’s 15 scored trips received equal weight. Across rats the average error was 2.898 cm from movement alone, 2.870 cm with correctly timed brain-cell firing, and 2.887 cm with firing from an earlier trip. Only KL8 met both firing comparisons. Continuing at its last observed speed gave the lowest error for that rat. A distance forecast gives neither a direction of travel nor a limb position. [Methods and rat-by-rat results](../models/population-motion/) · [Explore a recorded trip](https://eliminatenoise.github.io/NeuroTranslation/population-motion/)

## Whose recordings these are

Every dataset, who made it, its licence and the credit it is owed: [docs/RIGHTS.md](../docs/RIGHTS.md). The newer studies' datasets are there too.
