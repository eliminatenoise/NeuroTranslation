# The hand's own history is the forecast to beat

Every study in this repository asks one question of one open dataset. Most ask the same one: a model already knows something about a movement, so does one more signal help it forecast what comes next?

Mostly it does not. A model that learned from the recent history of the very thing it forecast (it was *fitted* to that history) beat "repeat the last value" every time it was tried on the task it was fitted for. A brain signal from the scalp, added on top, usually made the forecast worse. A muscle signal helped at the wrist, and nowhere else beyond the noise. The general model this project is building, one model meant to learn from many kinds of body signal at once, got worse when it was given the same muscle signal at the wrist. And when the task changed, or the person had to follow a new force level shown on a screen, a one-line rule beat every fitted model.

This page holds the numbered table and what it adds up to: 25 studies in 20 folders here (two folders hold more than one), two more studies that are reported only in the papers, and two rows that are not tests, each in a folder of its own: the general model's five-sensor walking fit (`daily-sports-limbs/`) and a correction scored on the people the wrist models were fitted on (`wrist-forearm-correction/`). Every count on this page is a count of those numbered rows.

How to use this page:

- [Every study](#every-study) is the table: one row per study, its scores, and a link to the study's own folder, which holds its plan and its results file.
- [What it adds up to](#what-it-adds-up-to) works out the counts behind the README's findings, one statement at a time, each with the rows it counts.
- [The groups set aside](#twenty-four-people-and-four-recordings-were-set-aside-and-are-still-unopened) lists the test groups that nobody has opened yet.
- [Newer studies](#after-the-table-brain-and-muscle-signals-still-made-most-forecasts-worse-and-words-helped-one-forecast-a-little), published after the table, are at the end, grouped by the question they ask and outside every count.

[The README](../README.md) has the short version.

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

### 7. No fit of the general model in the table was tested on a new person, and the evidence is narrower than 29 rows suggest

What exists is 25 separate small studies, each with its own straight-line fit or small network for one signal in one task; one macaque study in which two larger networks failed their pass rule, across 18 runs and 720 saved passes through the fitting data (study 24); and one run of a single network shared by a muscle signal and a glove signal, on one recording, which lost to "repeat the last value" on its own training data and predicts nothing from one signal to the other (study 25).

That shared network was an earlier, separate attempt. The general model being built now, NeuroTranslate 0.0, had its first five fits to real recordings on 20 November:

- Two on the walking data of study 26, with motion sensors only. One fit forecast five sensors on the body and was scored only on the four people it was fitted on (row 27): it beat repeating the last value at all five and met its own rule at one, the left leg. An earlier version, fitted to the right arm alone, was scored on study 26's two test people, who had already been scored once, and lost to the straight-line fit for both (0.869 against 0.781).
- Three on the wrist data of studies 1 to 3, with muscle and brain signals (study 28), scored on the three people those studies had already scored. Forearm EMG made the forecast worse (5.432° to 5.866°). Scalp EEG on top brought it to 5.822°, but another trial's EEG did almost as well (5.826°). Study 1's learned forecast, which reads only the wrist, beat all three (4.053°).

The general model's fits published after the table are described [at the end of this page](#the-general-models-later-fits-models-made-for-the-job-beat-it-on-the-angles-of-wrist-and-knee-trained-for-the-knees-turning-moments-it-led-the-methods-that-saw-only-angles), in no count here.

No fit of the general model in the table was tested on a new person. Five later fits were, on the force under a walker's right foot, on five new people's arms after a cue, on three new people's back sensors, on four new people's shin muscles and on two new people's pull against a fixed pedal: simpler forecasts beat it on the first, second and fourth, a straight-line fit matched it on the back sensors, and on the pedal it beat them, from the pedal's own readings, while the muscle signal made it worse ([below](#the-general-models-later-fits-models-made-for-the-job-beat-it-on-the-angles-of-wrist-and-knee-trained-for-the-knees-turning-moments-it-led-the-methods-that-saw-only-angles)), so nothing here yet translates between nerve, muscle and movement.

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

Not known either, because nothing in the repository measures it: any live result; any result in newtons for studies 11 to 17, whose datasets give no conversion from volts; any effect of more or more varied training data on people a model has not seen (the shared fit's comparison of two datasets with one, below, was not scored on such people); any model that predicts one kind of signal from another across datasets; any fit of the general model in which a brain, nerve or muscle signal helps it beat simpler forecasts on a person who had not been looked at before (on a fixed pedal it beat them for two new people from the pedal's own readings, and the muscle signal made it worse).

## After the table: brain and muscle signals still made most forecasts worse, and words helped one forecast a little

These were published after the table was made. Each has its own plan and results file, and none is in the table or in any count above. They are grouped by the question they ask: does a signal help a forecast of the next movement or force; does a recording at the armpit help forecast a voltage at the neck; do voltages from the skin over the spine help forecast how far a sensor on the back will turn; does a muscle bundle's angle in ultrasound help forecast its length; does a shin muscle's electrical signal help forecast the load on a fixed pedal; what beats the last stride on a treadmill; what can words do with a movement; and how did the general model do on the tasks it learned after the table.

### Brain and muscle signals made seven of these nine forecasts worse on average, and the two small gains failed the tests set for them in advance

Each of these asks the table's question of a new signal: does it help a forecast that already knows the recent movement?

- **[Can brain-cell firing improve a rat’s movement forecast?](wtrack-neural-motion/)** (`wtrack-neural-motion/`). No. A camera tracked a rat running round a W-shaped track while electrodes in its brain picked up electrical spikes, which the recording sorts into 72 sources, each probably one brain cell. A forecast of where the rat would be a quarter of a second later, from its recent positions alone, missed by 2.010 cm on average. With one second of firing added it missed by 2.237 cm, and the positions alone were closer on 7 of the 9 later trips that were scored. Given firing from an earlier trip instead, the same fitted model did worse again (2.429 cm): it used the timing of the firing, and still did not beat the positions. This is one rat in one recording, and five later trips were set aside and never opened.

- **[How far will another rat move?](../models/population-motion/)** Three rats supplied the training data, and three others were scored. From each rat's last camera position, 549 forecasts estimated how far away, in a straight line, it would be at the first frame a quarter of a second or more later, and each rat's 15 scored trips counted equally. The average miss was 2.898 cm from the rat's movement alone, 2.870 cm with the correctly timed firing of its brain cells, and 2.887 cm with firing taken from an earlier trip. Only KL8 did better with its own firing than both with its movement alone and with an earlier trip's firing. Continuing at its last observed speed gave the lowest error for that rat. A forecast of distance says nothing about the direction of travel or where the limbs were. [Methods and rat-by-rat results](../models/population-motion/) · [Explore a recorded trip](https://eliminatenoise.github.io/NeuroTranslation/population-motion/)

- **[Can a recording from the surface of the brain beat the last glove reading?](../models/cortical-glove/)** One person saw a finger named on a screen and bent it, wearing a glove that measures all five fingers, while electrodes laid on the surface of the brain recorded. Models were fitted on 52 trials and scored on the 23 that followed in the same recording, forecasting the glove about 120 ms ahead. The error is scaled by each finger's spread and averaged over the five. Keeping the last reading did best (0.1774). A straight-line model given the recent glove readings and the screen scored 0.2502, and 0.2849 with the brain recording added: worse on every finger and in every trial, by 0.03470 (from 0.02396 to 0.04630 when the trials were resampled). The right trial's brain recording did not clearly beat an earlier trial's, and a small transformer also got worse with the recording (0.1868 to 0.2517). One person, one recording, and only its first 362 seconds. [Study, fitted models and its rights](../models/cortical-glove/) · [Try invented inputs](https://eliminatenoise.github.io/NeuroTranslation/finger-signals/)

- **[How much will each finger move?](../models/finger-motion/)** The same person, glove, screen and brain-surface recording as the study above, but no model is given a recent glove reading: each forecasts how much every finger will move, step by step, over the next 160 ms. The models were fitted on the same 52 trials and scored on the same 23, with the error scaled by each finger's spread and averaged over the five. Given the screen alone, a straight-line model scored 0.288 and a small transformer 0.289; given the brain recording as well, 0.354 and 0.321, both worse with ranges that stayed clear of zero. The brain recording alone did little better than the training average for the straight-line model (0.454 against 0.455). [Study, weights and its rights](../models/finger-motion/) · [Try the six models](https://eliminatenoise.github.io/NeuroTranslation/finger-motion/)

- **[Does a finger forecast carry over to a new person?](../models/finger-transfer/)** Five people from the same library of recordings saw a finger named on a screen and moved it, wearing a glove, while electrodes on the surface of the brain recorded; their recordings place the electrodes differently, so the study groups them by the brain area each sat over. Each person in turn was held out: the other four supplied every training example, and the first 80 seconds of the held person's recording only set the scale of their readings. The models forecast how much each finger would move over the next three glove readings of 40 ms, with the error scaled by each finger's spread and each person counting equally. A table that knew only the finger on the screen and the time since it appeared did best (0.4770). A straight-line model given the screen scored 0.4811, and 0.5011 with the brain recording added; a small transformer, 0.4832 and 0.5134. The brain recording alone did worst (0.6100 and 0.6077). The right trial's recording did a little better than an earlier trial's, with a range that stayed above zero, and for two of the five people a model given the brain recording beat the table; neither model met the rule set in advance for carrying over to a new person. With five people, whose training sets overlap from one turn to the next, these numbers describe this group, not the next person. [Methods, per-person results and rights](../models/finger-transfer/) · [Run the five-person model](https://eliminatenoise.github.io/NeuroTranslation/finger-transfer/) · [Four-page note on the three finger studies](https://eliminatenoise.github.io/NeuroTranslation/papers/finger-cues/)

- **[Can a leg's muscle signals tell how hard a foot will press on the floor?](../models/walking-force/)** People walked slowly across two force plates, panels in the floor that measure how hard a foot presses down, while cameras tracked markers on their feet and hips and eight electrodes on the skin of the right leg picked up its muscles. Six models estimated the load the two plates would record a tenth of a second later. On 17 walks by 8 people kept out of fitting, a small transformer given the markers missed by 65.19 newtons on average and, given the muscle signals as well, by 70.20, better for only two of the eight; the rule set in advance for the muscle signals was not met. Carrying forward the plates' current reading did best (63.43). The recordings were filtered forwards and backwards in time before they were released, so the tenth of a second is a distance along the stored signals, not a live forecast. Ten more walkers were set aside and remain unopened. [Two-plate methods and full results](../models/walking-force/) · [Try the two-plate model](https://eliminatenoise.github.io/NeuroTranslation/walking-force/) · [The study](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-and-floor/)

- **[Do six scalp electrodes help forecast the next arm movement?](../models/scalp-forecast/)** The five new people of the arm study at the end of this page, on a fourth run of the task that stayed unopened until the models were frozen; their first three runs had been scored before. A quarter of a second after a picture asked for a movement, a small transformer forecast how the elbow, forearm and finger sensors would change over the next 0.5, 1 and 1.5 seconds, from the cue and the early arm readings, with or without the early readings of six scalp electrodes. On 210 trials its error was 0.50853 without them and 0.50856 with them, lower for three of the five people; the rule set in advance asked for 5% less and for every person, and neither it nor the rule for the scalp beyond three electrodes around the eyes was met. With the eye electrodes instead of the scalp it was 0.50965. The usual change for each cue, learned from the seven fitting people, did better than all of them (0.49278), for four of the five. [Transformer scores](../models/scalp-forecast/assessment-summary.json) · [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/scalp-forecast/) · [Compare scalp and eye recordings](https://eliminatenoise.github.io/Interoceptomics/scalp-and-arm/) · [The four-page illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/scalp-forecast/)

- **[Where will a walker's ankles, knees and wrists be a fifth of a second later?](../models/walking-landmarks/)** The same slow overground walking as the study above, from the Rehazenter Adult Walking Dataset. From 40 camera frames, spanning 0.39 seconds, of eight markers on the skin (both outer ankles, outer knees and thumb sides of the wrists, and two at the front of the hips), models forecast where each of the first six would be 20 frames, 200 milliseconds, later; some were also given the eight muscle signals of the right leg. Thirty walkers supplied the training data. The ten scored were kept out of fitting but had already been studied for other questions, and ten more remain unopened. On 1220 moments from 30 walks, a straight-line fit given the markers alone missed by 17.78 mm on average, and by 17.90 mm with the muscle signals. A small transformer missed by 18.22 mm from the markers and 18.02 mm with the muscle signals, better for six of the ten walkers, a difference within the noise. Carrying on at each marker's latest speed missed by 53.00 mm. The right muscle signals did beat another walk's put in their place, but the rule set in advance asked for both, and neither it nor the rule for the transformer was met. The recordings were filtered forwards and backwards in time before release, so the 200 milliseconds are a distance along the stored signals. [Six-point results](../models/walking-landmarks/results.json) · [Try six points in 3D](https://eliminatenoise.github.io/NeuroTranslation/walking-landmarks/) · [See the measured movement](https://eliminatenoise.github.io/Interoceptomics/stride-signals/) · [The four-page study, with the general model's single-marker task](https://eliminatenoise.github.io/NeuroTranslation/papers/walking-landmarks/)

- **[Does a scalp electrode help forecast the elbow after a cue?](../models/cue-elbow/)** One person sat with the right arm in a support while electrodes on the scalp recorded, and a picture asked for the elbow to bend or to straighten. A quarter of a second after the picture appeared, a model knew which of the two was asked for and the elbow sensor's last half-second, and forecast how much its reading would change by one second after the picture. On 36 trials in three runs, each run scored by a fit on the other two, the cue and the elbow's readings missed by 0.07237 on average, in the sensor's own units, which have no verified conversion to an angle. Adding the early readings of electrode C3, over the left side of the head, raised the error to 0.07859; with another trial's C3 readings in their place it was 0.07780, slightly lower, and with the eye channels in place of C3, 0.09082. C3 helped in one run of three and for neither of the two movements, so the rule set in advance was not met. A simple form of attention, a secondary comparison in the plan, let the last scalp reading weigh the three before it and missed by 0.07122: lower overall, higher on the bending trials, and without the controls the plan set for C3. One bending trial had been seen before the plan was fixed; the other outcomes were unopened. [Elbow results](../models/cue-elbow/scores.json) · [Run the elbow experiment](https://eliminatenoise.github.io/NeuroTranslation/elbow-cue/) · [Read both studies](https://eliminatenoise.github.io/NeuroTranslation/papers/cued-arm/)

### At the neck, the last reading beat a transformer, and a recording at the armpit passed neither model's test

- **[What will the neck electrode read four milliseconds later?](../models/cervical-forecast/)** People lay still while a nerve at the left wrist was stimulated again and again with a brief pulse, and electrodes on the skin recorded at the back of the neck, at the armpit over the same nerve, on the scalp, over a thumb muscle and on the chest. From the readings up to 8 milliseconds after each pulse, two models forecast how far the neck electrode's voltage 12 to 14 milliseconds after the pulse would be from its level before it. Four people supplied 80 pulses each for fitting; six others from the same study supplied 480, opened only after the models were fixed, and each person counted equally. Carrying the last neck reading forward missed by 8.09 µV on average. A small transformer given the armpit's recording missed by 23.28 µV, against 24.67 µV without it and 22.36 µV when the same fitted model was given the armpit's recording from a different pulse; only one of the six people did better with the right recording than with both of the others. The second model, a straight-line correction to the last neck reading, fitted so that a few large errors cannot pull it far, missed by 7.77 µV from the neck, scalp, thumb and chest, by 9.65 µV with the armpit added, and by 10.05 µV with another pulse's armpit recording; three of the six did better with the right recording than with both. Neither model met the rule set for the armpit's recording in advance. The second model also runs in the general model's program, with coefficients of its own and none of the general model's learned part. A voltage on the skin can mix signals from several tissues, so none of this says where the neck's signal began. [Rules and paired gains](../models/cervical-forecast/ASSESSMENT.md) · [All assessment errors](../models/cervical-forecast/assessment.json) · [The second model](../models/neurotranslate-0.0/cervical/) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/cervical-forecast/) · [Try the transformer](https://eliminatenoise.github.io/NeuroTranslation/cervical-forecast/)

### On the back, voltages from the skin over the spine made both forecasts of a sensor's turn worse

- **[How far will a sensor on the back turn in the next tenth of a second?](../models/back-rotation/)** People stood still and walked as they were told, with a sensor strapped to the back that records which way it points and two grids of 32 electrodes on the skin over the spine, one on the upper back and one on the lower, from a dataset made to record the spinal cord's activity; at the skin these voltages can also carry the muscles, the heartbeat and the electrodes' own movement. From the tenth of a second before, and knowing whether the person was walking or standing, two models forecast how many degrees the sensor would turn in the next tenth, a turn to the left counted the same as one to the right: a small transformer trained for the task, and the general model with its shared part left as it was (its entry is at the end of this page). Four people supplied the training data, two trials each. Four others were kept for the test and opened only after both models and their tests were fixed, but both trials of one of them name only three of the four numbers that give the sensor's direction, beside a channel labelled a buffer, so that person's turns could not be measured and neither planned test could be completed. On the other three people (1,152 standing and 1,152 walking forecasts, each person and each task counted equally), the transformer missed by 0.361° on average from the sensor's turns alone, 0.377° with the upper grid, 0.372° with the lower, 0.382° with both, and 0.381° with both grids' readings taken from another moment of the same trial. A straight-line fit on the turns alone missed by 0.377°, and repeating the last tenth of a second's turn by 0.445°. The general model scored 0.376° from the turns and 0.385° with both grids. The two models take another moment's voltages from different places and weigh each trial a little differently, so their scores cannot be compared exactly. A voltage at the skin can mix several tissues, and the turn of a sensor worn on the back is not the movement of any one joint. [Controls, averaging and results](../models/back-rotation/ASSESSMENT.md) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/back-rotation/) · [Try the transformer](https://eliminatenoise.github.io/NeuroTranslation/back-rotation/)

### In the shin, a straight-line fit on a muscle bundle's recent length beat both models, and its angle helped them only a little

- **[Will this bundle of shin muscle fibres shorten?](../models/muscle-tracking/)** People sat and pulled the front of the foot upward while an ultrasound probe on the shin filmed the muscle there (the tibialis anterior), in the AnkleImage dataset; tracking software followed one bundle of its fibres through the images, its length in millimetres and its angle to a sheet of connective tissue. Two models forecast how much longer or shorter the bundle would look ten tracking steps later, from its last 21 lengths and, if they are given, its angles: a small transformer trained for the task, and the general model with its shared part left as it was (its entry is at the end of this page). The recordings were tracked at different rates, so ten steps is not a fixed time. Four people supplied the training data, two recordings each; four others were opened only after both models and their tests were fixed, and all 776 of their forecasts could be scored, each person and each recording counted equally. The transformer missed by 0.236 mm on average from the lengths alone and 0.233 mm with the angles, closer for three of the four people, and 0.270 mm with the angles of the person's other recording; but a straight-line fit on the lengths alone missed by 0.223 mm, and the test set in advance for the angle failed. Repeating the last ten steps' change missed by 0.242 mm, and holding the last length by 0.401 mm. The general model scored 0.226 mm from the lengths and 0.219 mm with the angles. Length and angle come from the same images, so they can share the tracker's errors, and a length in the image says nothing of the muscle's force. [Every method's error](../models/muscle-tracking/assessment.json) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-tracking/) · [Try the transformer](https://eliminatenoise.github.io/NeuroTranslation/muscle-tracking/)

### On a fixed pedal, the shin muscle's signal helped the transformer for one of two new people, and the general model for neither

- **[Can the shin signal predict the next pedal reading?](../models/pedal-load/)** People sat with the front of a foot strapped to a pedal that could not move and tried to lift it, in the AnkleImage dataset, while an electrode on the skin of the shin picked up the electrical activity of the muscle there (EMG) and a sensor under the pedal recorded the load on it, in the sensor's own units, since no conversion to newtons was available. From the last 201 readings of both and the pedal's setting, two models forecast how much the pedal's reading would change 100 readings later, nominally a tenth of a second: a small transformer trained for the task, and the general model with its shared part left as it was (its entry is at the end of this page). Two people supplied the training data. Two others were kept for the test and opened only after both models were fixed, but one of the second person's four planned recordings holds two columns named as the pedal's sensor and no verified clock, so the planned test could not be completed, and the seven others are described person by person, with no verdict for the pair. For the person with all four recordings, the transformer missed by 0.06257 on average from the pedal's readings and setting and 0.05452 with the muscle signal, closer than every simpler forecast, among them repeating the last change (0.05635); with another recording's muscle signal it missed by 0.06251. For the other person the muscle signal made it worse: 0.12013 to 0.16696 on the two recordings at one setting, and 0.11189 to 0.15106 on the single recording at the other. The general model, from the pedal's readings, was closer than every simpler forecast for both people, and worse with the muscle signal for both. The pedal's reading is not the force of any one muscle. [Every specialist error](../models/pedal-load/assessment.json) · [Illustrated study, with the general model's comparison](https://eliminatenoise.github.io/NeuroTranslation/papers/pedal-load/) · [Try the transformer](https://eliminatenoise.github.io/NeuroTranslation/pedal-load/) · [Development results](../models/pedal-load/development.json)

### On a treadmill, the last stride is the forecast to beat, and the leg muscles' strongest rhythm matches the knees'

- **[Can four seconds of walking beat the last stride?](../models/knee-stride/)** Three forecasts were given the same 240 earlier readings of both knees, four seconds at 60 Hz, and asked for both angles 15 frames later, a quarter of a second on: copying the matching moment of the previous stride, that copy with a straight-line correction, and that copy with a correction from a small transformer trained for the knees. The corrections were fitted on 39 walkers. On 40,201 forecasts from the 12 walkers of the short-look study below, they missed by 3.535°, 3.411° and 2.679° on average, and the transformer was closer than both for every one of the 12. Those walkers were kept out of fitting, but their earlier results were known when this comparison was designed. In a second laboratory, ten other people walking faster and measured with cameras and markers, the unchanged transformer missed by 3.242° against 3.398° for the copied stride: closer for only six of the ten, a lead within the noise, though it beat the straight-line correction for nine. [Fitted model, every comparison and source](../models/knee-stride/) · [The test in a second laboratory](../models/knee-stride/external-optical/) · [Compare the forecasts](https://eliminatenoise.github.io/NeuroTranslation/knee-stride/)

- **[Can a short look at the hips, knees and ankles beat replaying a stride?](../models/knee-motion/)** From five snapshots of both hips, knees and ankles, spanning 0.4 seconds, a small transformer predicts the two knee angles 15 frames later, about a quarter of a second in a treadmill recording made at 60 frames a second. On 40,201 forecasts from 12 walkers kept out of fitting, replaying a stride from four seconds of knee history missed by 3.54° on average; the transformer missed by 4.46° on the same moments. The angles are the motion sensors' own reconstructions: six of the 51 recordings, including test recording S48, were refined using the whole recording (Xsens HD processing), and the other 45 carry the Live label. Nothing was forecast live, so the delay a live system would add was never measured, and the forecast saw only the reconstructed joint angles. [Fitted model, full comparison and source](../models/knee-motion/) · [Try the knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/)

- **[Do the muscles and knees repeat at the same rate?](../models/gait-rhythm/)** For 11 test walkers at 0.5 m/s, the strongest rhythms in the leg-muscle recordings and knee angles differed by 0.027 cycles per minute on average. Pairing each walk with another walker’s muscle recording raised the difference to 3.055. Each instrument supplied its own 40-second window. Agreement in rate leaves the timing of individual steps unresolved. [Study, fitted comparisons and source](../models/gait-rhythm/) · [Open the rhythm reader](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/)

A five-page supplement reports the treadmill studies together and adds the knee turning moments: [read it online](https://eliminatenoise.github.io/NeuroTranslation/papers/walking-rhythm/) or [download the PDF](../docs/papers/walking-rhythm/gait-clocks.pdf).

### Words helped one forecast a little; something simpler matched or beat every other use of them

Each of these gives a model words along with a movement: an instructor's speech, a sentence written about a recording, or the single word walk or run. Two of them search recordings with a sentence; for those two the score is how often the right recording came first, so a higher score is better, unlike the errors above.

- **[Can an instructor’s words improve a one-second wrist forecast?](preceding-instructions/)** (`preceding-instructions/`). Not here. A headset tracked a person's right wrist while an instructor talked them through a task. A quarter of a second after each instruction ended, a model forecast how far the wrist would move in the next second, from its recent movement, the task and facts about the finished instruction such as its length. It missed by 9.79 cm on average. Told also which of six recurring words the instruction held ("turn", "on", "off" and the like), it missed by 10.04 cm. Repeating the wrist's movement over the previous second did best, at 7.38 cm. Only 26 forecasts were scored, from seven recordings in four groups (the dataset groups recordings by a code, not by person), and the model was fitted on 44 examples. These recordings had been open earlier, while a different task was built on them, so this is not a fresh test.

- **[Find a recorded hand movement from a sentence](hand-language-retrieval/)** (`hand-language-retrieval/`). Timing beat the hand. A headset tracked the right hand of people doing tasks such as setting up a printer, and observers later wrote a sentence about each step. Given one of those sentences, a model ranked the steps of the same recording, and the score is how often the right step came first: here higher is better. On 60 sentences from ten recordings in six groups kept out of fitting, a model that read the shape and movement of the hand put the right step first 23.89% of the time (a second model, built on attention, the mechanism a transformer uses to weigh one part of its input against another: 23.59%), against 20.66% for a random order. Ranking by each step's length, its place in the recording and how often the hand was tracked, with no hand shape at all, reached 35.56%. The groups are the dataset's recording codes, not verified people, and the same person may appear under different codes. Ten more recordings, in three groups, were set aside and never opened. [Inspect five recorded movements in your browser](https://eliminatenoise.github.io/NeuroTranslation/hand-search/).

- **[Which recording does the sentence describe?](text-motion-retrieval/)** (`text-motion-retrieval/`). The simpler model did better. Volunteers watched recorded whole-body movements, most of them walks, and described each one. Given a description, a model ranked 38 recordings of six performers, as the dataset's catalogue names them, all kept out of fitting, and the score is how often the right recording came first, averaged so that each of the 38 recordings counts equally: higher is better. A model built on attention put it first 5.6% of the time; a simpler one, built on word counts and plain summaries of the movement, 6.6%; a random order, 2.6%. Ranking the recordings by the action name the dataset's catalogue gives each one, matched to the sentence's words, with no movement at all, did better than both: 7.7%. The attention model failed the pass rule set for it in advance, which asked it to beat that ranking too. 31 of the 38 recordings are walks, so many descriptions fit several of them, and the folder says that repeated clips of the same people limit any claim about new people. Another 31 recordings, of four other performers, were set aside and never opened.

A four-page supplement reports the two searches with words together: [*How precisely do words identify a recorded movement?*](../docs/papers/language-and-observed-movement/README.md) It is separate from the two papers, and neither paper's current draft contains these studies.

- **[Where will the next step land?](../models/stride-continuation/)** Given half a second of a measured walk or run, a model forecasts the next 0.60 seconds at 18 points on the body. The half second is eleven poses at 20 a second, every third or sixth frame of cameras that recorded at 60 or 120 frames a second. Across 351 overlapping windows from twelve recordings in six groups it had not been fitted on, the model told whether the person walked or ran missed the 18 points by 69.1 mm on average, measured from the hips. A second model, given the movement alone, missed by 71.9 mm. Where the hips themselves went through the room tells a different story: a straight-line model missed them by 59.0 mm, the model told the action by 66.7 mm. Five groups walked and only one ran. The group numbers need not identify distinct people. One more comparison looks up similar strides among the training recordings; repeating it means rebuilding that collection from the original CMU recordings. [Method and reproduction](../models/stride-continuation/REPRODUCE.md) · [Results by source group](../models/stride-continuation/fresh-results.json) · [Continue a measured stride](https://eliminatenoise.github.io/NeuroTranslation/stride/) · [Two-page supplement, with the three-rat study](https://eliminatenoise.github.io/NeuroTranslation/papers/forecasting-movement/)

- **[Can a word generate a stride?](../models/word-motion/)** Type **walk** or **run** and a small model generates 0.60 seconds of movement at 18 points on the body, the same movement each time for the same word. On three recordings kept out of fitting, two walks and one run, it missed the measured points by 89.82 mm on average, almost the same as the average walk or run from training (89.88 mm). [The fitted model and study](../models/word-motion/) · [Try a walk or run](https://eliminatenoise.github.io/NeuroTranslation/word-motion/)

### The general model's later fits: models made for the job beat it on the angles of wrist and knee; trained for the knees' turning moments, it led the methods that saw only angles

After its first five fits, all in the table, the general model learned two datasets at once and then more tasks ([`models/`](../models/)). Only four were scored on people who gave it no training data and whose recordings nobody had inspected when the test was designed: the right-foot task, the arm task refitted on seven people and the shin-muscle task, where simpler forecasts did better; the back-sensor task, where a straight-line fit did as well and one of the four people could not be scored; and the fixed-pedal task, where it beat them from the pedal's own readings and one of eight recordings could not be scored. A later test with scalp readings used unopened fourth runs of those five arm-task people, whose first three runs had already been scored.

- A shared fit learned a headset's tracking of people's wrists (HoloAssist) and the rat study's tracking at once; it beat the same model fitted on either dataset alone by margins within the noise, and lost to a straight-line fit on the rat.
- A wrist-angle task added to it later was scored on the six people studies 1 to 3 were fitted on, like row 29, and did worse than row 29's correction (4.291° with EMG, against 3.549°). A correction fitted on top of that task, with forearm EMG, reached 4.054°, still above row 29; row 29's model, refitted on all six people, is now a download ([`models/wrist-specialist/`](../models/wrist-specialist/)).
- On the walkers of the four-second knee study above, the general model, its shared part left as it was and a new final step fitted for the knees, missed by 3.465°: no better than the same final step without the shared part (3.460°), and a copy with its shared part scrambled did better (3.422°). The small transformer trained for the knees alone missed by 2.679°. [The general model's knee task](../models/neurotranslate-0.0/knee/)
- In another laboratory's treadmill walking, the general model learned to estimate the turning moment at each knee a quarter of a second ahead from four seconds of six leg angles: the net push of the forces around the knee, which the laboratory estimated from cameras and the forces under the feet, in newton-metres per kilogram of the walker's mass. Seven walkers supplied the training examples and three were scored. With its shared part left as it was, it missed by 0.10190 on average, behind a straight-line fit (0.09761) and matching the walk to other walkers' steps (0.09373), and a scrambled copy missed by 0.10349. Trained for the task, it missed by 0.08874, the lowest of the methods that saw only angles, but it beat the straight-line fit for two of the three walkers and the walker match for one, and did not meet the rule set for a consistent gain. Copying an earlier measured moment from the matching part of the previous stride did better than all of them where it was possible (0.06785). The three walkers' turning moments were first looked at after fitting, but their angles had been used in an earlier knee-angle comparison. [The knee-moment task](../models/neurotranslate-0.0/load/) · [Try it](https://eliminatenoise.github.io/NeuroTranslation/knee-moment/)
- Given recorded brain-cell firing alongside a rat's recent camera track, correctly timed firing lowered its average distance error from 2.805 to 2.778 cm, but beat both movement alone and an earlier-trip firing control in only one of the three animals. This reanalysis used previously examined test recordings. [The firing comparison](../models/neurotranslate-0.0/population/)
- In overground walking from another laboratory, the general model learned to estimate the upward force on the floor plate under the right foot about a tenth of a second ahead, from 240 milliseconds of two markers on that foot and, if they are given, the right leg's eight muscle signals. Its shared part was left as it was. It was scored on the 8 walkers of the two-plate study above, and its design was fixed before anyone inspected their force or muscle recordings. With the muscle signals it missed by 85.18 newtons on average, against 93.93 without them, lower for five of the eight; a straight-line fit given the same signals did better (82.04), and carrying forward the plate's current reading better still (76.45). Neither the gain from the muscle signals nor any gain from the shared part's earlier learning passed the test set for it in advance. [Right-foot plate methods and results](../models/neurotranslate-0.0/right-plate/) · [Try it](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#right-plate) · [The study](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-and-floor/)
- In the same walking, the general model learned where one marker on the skin will be 200 milliseconds later from nine of its positions, 50 milliseconds apart, with no name for the marker and nothing from the rest of the body. Its shared part was left as it was, and a new final step was fitted at the six places of the six-marker study above, on 30 walkers. Tried at 46 other places, among them the heels, toes, pelvis, trunk, elbows and hands, on the ten walkers of that study, it missed by 31.00 mm on average, against 43.29 mm for carrying on at the marker's latest speed, 30.64 mm for a straight-line fit, 30.20 mm for the same final step on a shuffled copy of the shared part and 28.73 mm for a look-up of similar paths among the training examples. The test set in advance for a gain from the shared part failed. [Transfer to other locations](../models/neurotranslate-0.0/point-motion/results.json) · [Methods](../models/neurotranslate-0.0/point-motion/) · [Try one point](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#point-motion)
- With one person's right arm, the general model learned to forecast three sensors, at the elbow, the turn of the forearm and the base of the index finger, half a second, one second and one and a half seconds after its last input, from half a second of their readings and the cue a picture gave: one of six movements, or rest. This task uses no brain signal, and its shared part was left as it was. On 126 trials in three runs, each run scored by a version fitted on the other two, the cue lowered its error from 0.751 to 0.641 in all three runs, passing the rule set for the cue; the error is scaled by how much each sensor's reading varied in the runs used for fitting. But the cue alone did best (0.525), and keeping the last reading (0.556), a straight-line fit given the cue and the readings (0.607) and a shuffled copy of the shared part (0.632) all beat the general model, so the rule for a gain from its shared part failed. The elbow study above used 36 of these trials. [Three-sensor results](../models/neurotranslate-0.0/cued-arm/results.json) · [Methods](../models/neurotranslate-0.0/cued-arm/) · [Try an instruction](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#cued-arm) · [The four-page study, with the elbow study](https://eliminatenoise.github.io/NeuroTranslation/papers/cued-arm/)
- The same arm task was then fitted on seven people of that dataset (882 trials) and scored on five others (630 trials in 15 runs), whose files were opened only after the plan, the code and the fitted model had been sealed; three more people remain unopened. It beat the version fitted on one person (0.505 against 0.793, for all five), and the cue helped it, against the same model without the cue (0.561) or with a wrong one (0.682): both rules set in advance were met. But the fitting group's median change for each cue did best (0.435, lower for every one of the five), predicting no change scored 0.489 and the same readout on a shuffled copy of the shared part 0.501, so the rule for a gain from the shared part failed. With one earlier run of each new person, a correction fitted on that run brought the error on the later 420 trials from 0.521 to 0.484, lower for all five, but the person's own median change for each cue in the earlier run did better (0.429) and that rule failed too. A small transformer trained for this task alone, frozen and scored on the same five, missed by 0.493, behind the average change for each cue (0.467) and predicting no change (0.489); it beat a plain network and itself without the cue, but not the cue alone. [Shared model and calibration scores](../models/neurotranslate-0.0/arm-transfer/results.json) · [Task-trained model scores](../models/arm-transfer/assessment-summary.json) · [Try the transformer](https://eliminatenoise.github.io/NeuroTranslation/arm-transfer/) · [Try a first-run correction](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#arm-transfer) · [The four-page study](https://eliminatenoise.github.io/NeuroTranslation/papers/arm-transfer/)
- On those five people's fourth runs, the general model was given the early readings of six scalp electrodes: a correction to the fitting group's usual change for each cue, fitted on the seven, read the arm's early movement, the scalp, the eyes or both. Its error went from 0.49777 with the arm alone to 0.49628 with the scalp as well, lower for two of the five; the usual change for each cue scored 0.49696, the arm with the eye electrodes 0.50245, and the arm with the eyes and what the eyes leave unexplained of the scalp 0.50314. Both rules set in advance, for the scalp and for the scalp beyond the eyes, failed. [Shared model scores](../models/neurotranslate-0.0/scalp-residual/results.json) · [Try the eye adjustment](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#early-signals) · [Read the illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/scalp-forecast/)
- In recordings of people standing and walking, the general model learned how far a sensor strapped to the back will turn in the next tenth of a second, from the tenth before and, if they are given, the voltages of two grids of electrodes on the skin over the spine. Its shared part was left as it was, and a new final step was fitted on four people. Of the four people kept for the test, opened only after the fit was fixed, one could not be scored, so the planned test was never completed. On the other three it missed by 0.376° from the sensor's turns alone, the same as a straight-line fit (0.376°); with both grids it missed by 0.385°, against 0.380° for the straight-line fit given the same grids and 0.382° for a copy whose shared part was left untrained, at random settings, and with both grids it was worse than from the turns alone for all three people. Repeating the last tenth of a second's turn missed by 0.445°. The transformer trained for the task is in [its own entry above](#on-the-back-voltages-from-the-skin-over-the-spine-made-both-forecasts-of-a-sensors-turn-worse). [Try the back-sensor task](https://eliminatenoise.github.io/NeuroTranslation/shared-back-rotation/) · [Methods and results](../models/neurotranslate-0.0/back_rotation/)
- With people pulling the foot upward while ultrasound filmed the muscle at the front of the shin, the general model learned how much longer or shorter one tracked bundle of its fibres would look ten tracking steps later, from its last 21 lengths and, if they are given, its angles to a sheet of connective tissue. Its shared part was left as it was, and a new final step was fitted on four people. On four others, opened only after the fit was fixed, it missed by 0.226 mm from the lengths and 0.219 mm with the angles, behind straight-line fits given the same readings (0.217 and 0.215 mm); a copy whose shared part was left untrained scored 0.222 mm with the angles, and the test set in advance for the angle failed. Repeating the last ten steps' change missed by 0.242 mm, and a calculation from the bundle's geometry by 0.249 mm. The transformer trained for the task, which did worse than the general model, is in [its own entry above](#in-the-shin-a-straight-line-fit-on-a-muscle-bundles-recent-length-beat-both-models-and-its-angle-helped-them-only-a-little). [Try the shin-muscle task](https://eliminatenoise.github.io/NeuroTranslation/shared-muscle-tracking/) · [Methods and results](../models/neurotranslate-0.0/muscle_tracking/) · [Every score](../models/neurotranslate-0.0/muscle_tracking/assess-summary.json)
- With people trying to lift a foot strapped to a pedal that could not move, the general model learned how much the pedal's reading would change a tenth of a second ahead, from the last 201 readings of the pedal's sensor, the pedal's setting and, if it is given, the electrical activity of the shin muscle. Its shared part was left as it was, and a new final step was fitted on two people. Of the two people kept for the test, opened only after the fit was fixed, one recording could not be scored, so the planned test was never completed. From the pedal's readings and setting it beat every simpler forecast for both people: for the person with all four recordings it missed by 0.0434, against 0.0476 for a straight-line fit and 0.0563 for repeating the last change; for the other person's two recordings at one setting, 0.1023 against 0.1199 and 0.1793. Given the muscle signal it did worse for both (0.0437 and 0.1533). The transformer trained for the task is in [its own entry above](#on-a-fixed-pedal-the-shin-muscles-signal-helped-the-transformer-for-one-of-two-new-people-and-the-general-model-for-neither). [Try the pedal task](https://eliminatenoise.github.io/NeuroTranslation/shared-pedal-load/) · [Methods and results](../models/neurotranslate-0.0/pedal_load/)

## Whose recordings these are

Every dataset, who made it, its licence and the credit it is owed: [docs/RIGHTS.md](../docs/RIGHTS.md). The newer studies' datasets are there too.

## The heel and the force plate

A tenth of a second after the cutoff, where did the right heel marker move and what load did the plate under that foot measure? Eight people supplied 53 paired instants in 16 recordings. The joint Transformer missed the heel endpoint by 1.156 mm and the plate by 92.36 N on average. The separately trained specialists missed by 1.183 mm and 93.73 N. The participant-bootstrap intervals for both differences crossed zero. Six of the same people supplied 31 more instants in ten later recordings. Both intervals again crossed zero. Neither assessment established that adding muscle activity met the prespecified benefit criteria. [All methods and results](../models/heel-and-force/aggregate.json) · [Study and movement-model comparison](https://eliminatenoise.github.io/NeuroTranslation/papers/heel-and-force/)
