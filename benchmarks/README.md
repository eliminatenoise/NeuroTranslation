# The hand's own history is the forecast to beat

Every study in this repository asks one question of one open dataset. Most ask the same one: a model already knows something about a movement, so does one more signal help it forecast what comes next?

Mostly it does not. A model fitted to the target's own recent history beat "repeat the last value" every time it was tried on the task it was fitted for. A brain signal from the scalp, added on top, usually made the forecast worse. A muscle signal helped at the wrist, and nowhere else beyond the noise. And when the task or the target moved, a one-line rule beat every fitted model.

The numbered comparison below covers the original 23 repository studies and two studies reported in the papers. The wrist correction and language studies have their own results and score definitions. [The README](../README.md) has the short version.

**Can muscle recordings correct a wrist forecast?** In 1,879 pointing trials from six people already used for training, adding the forearm signal reduced error from 3.665° to 3.549° against a correction that used wrist motion alone. All six people improved on that comparison. Only three improved over the original uncorrected model. The gains were concentrated early in the movement. [Study, results and reproduction instructions](wrist-forearm-correction/)

**Can the words pick the right hand movement within one task?** Across 60 assessment intervals, hand geometry reached 23.89% first-place retrieval with the simpler model. A comparison based on duration, timing and tracking coverage reached 35.56%. [Study and fitted models](hand-language-retrieval/) · [Inspect five recorded movements](https://eliminatenoise.github.io/NeuroTranslation/hand-search/)

**Which movement do the words describe?** Two models rank recordings against descriptions written by people who saw them. The simpler calculation had the higher first-place score. [Language and motion study](text-motion-retrieval/)

## How to read the numbers

For the numbered movement forecasts, error measures how far a forecast fell from the recorded value. Lower is better. In the language study, we first calculate how often the matching movement comes first for each recording’s descriptions. We average those 38 scores so that every recording counts equally. Higher is better. Studies 1 to 13 use the measure that punishes large misses (root mean squared error), studies 14 to 23 the plain average miss (mean absolute error), and studies 24 and 25 a squared error in units scaled to the data. Study 20 scores bands, not forecasts, and has a note of its own below.

"Tested on" names people whose test recordings were never used to fit the model. A forecast that "repeats the last value" does nothing clever: it says the next reading will equal the latest one. Where a cell says "not given", the study's results file does not hold that count.

A *straight-line fit* is the plainest kind of model, a weighted sum of its inputs. A *learned forecast* is a small network that reads a stretch of recent history.

**EEG** is electrical activity of the brain, picked up on the scalp. **EMG** is electrical activity of muscle, picked up on the skin. It is a recording of muscle, not of nerve. **MVC** is the hardest squeeze a person could manage that day; pinch force is given as a percentage of it.

Units and measures change from study to study. Compare along a row, never between rows. Each study's own page gives its measure, its plan and its results file.

## Every study

### Wrist angle

Errors in degrees, both wrist axes together.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Wrist pointing: brain signal on a learned forecast](wrist-pointing-temporal/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) | The two wrist angles a quarter of a second ahead (250 ms), at six moments after the cue | 3 people (fitted on 6 others) | Learned forecast from wrist history: **4.053°** | The same with scalp EEG added: **4.523°** | 0.469° higher | not given |
| 2 | [Wrist pointing: muscle signal on a straight-line fit](wrist-pointing-muscle/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-pointing/) | The same two wrist angles, 250 ms ahead | the same 3 (fitted on 6 others) | Straight-line fit on wrist history: **6.530°** | The same with forearm EMG added: **6.174°** | 0.355° lower (0.232 to 0.469 lower) | not given (the change stays negative whichever person is left out) |
| 3 | [Wrist pointing: muscle signal on the learned forecast](wrist-forearm-transfer/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) | The same two wrist angles, 250 ms ahead | the same 3 (fitted on 6 others) | Learned forecast, corrected from wrist motion: **3.957°** | The same correction with EMG added: **3.853°** | 0.104° lower (0.072 to 0.125 lower) | 3 of 3 |
| 4 | [Everyday tasks: wrist angle from the muscle signal](uji-wrist-emg/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) | The two wrist angles at least 250 ms after the last EMG sample, during 26 everyday activities | 4 people (fitted on 14 others) | Which activity it is and how long it has run: **36.187°** | The same with EMG added: **34.718°** | 1.468° lower (0.016 to 2.936 lower) | 3 of 4 |

Ranges: study 1, the results file gives no range across people; studies 2 and 3, whichever one of the three people is left out; study 4, the middle 95% when the four people are resampled.

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

### Reported only in the papers

No folder under `benchmarks/`. The first has no result file in the repository at all: its numbers are copied from the technical paper. Both use units scaled to the data, so the numbers mean nothing outside their own row.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 24 | [Macaque fingers from motor cortex (LINK)](../papers/current/neurotranslation-technical.pdf#page=13) | The position of the index finger, and of the other three fingers as a group, from the brain recording | 1 macaque, 2 later days (fitted on 4 days) | Straight-line fit on the latest brain sample: **0.0314982** | The better of two networks that read recent brain history: **0.0299609** | 0.0015373 lower (0.0003470 to 0.0027587 lower) | one animal |
| 25 | [One network shared by two signals: first run](../papers/current/research-evidence-reading-aid.md#one-acquisition-two-forecasting-tasks) | Each signal's own next values from its own past. Nothing is predicted from one signal to the other | nobody: scored on its own training recording | Repeat the last value (glove signal): **0.0245** | One network shared by both signals, after 990 training steps (glove signal): **0.3722** | 0.3477 higher (one recording, no range) | one recording |

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

### 1. A model fitted to the target's own history beat "repeat the last value" in 8 of 8 studies

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

That is every study that scores "repeat the last value" and scores the model on the task it was fitted for. Studies 2 and 3 reuse the people of study 1 and are not counted twice. Study 4 has no "repeat the last value" score.

Two of the eight wins carry a footnote. In study 9, whenever the force to be forecast was at or below 0.5 N, repeating the last force beat every fitted model. In study 7, a straight line through the palm's recent speed beat the fitted model on the plain average miss and lost to it on the measure that punishes large misses.

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

### 3. Scalp EEG lowered the error in 4 of 12 comparisons, and met no pass rule

| Study | EEG added to | Without | With EEG | People better | The same model fed EEG from the wrong trial or moment | Main question? |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Learned forecast that already has wrist history | **4.053°** | 4.523° | not given | EEG from another trial: 4.880° | yes |
| 1 | Straight-line fit that already has wrist history | 6.530° | **6.439°** | not given | EEG from another trial: 6.782° | no |
| 2 | Straight-line fit that already has wrist history and EMG | 6.174° | **6.127°** | not given | EEG from another trial: 6.379° | no |
| 7 | Straight-line fit that already has past palm position | **1.093 mm** | 1.223 mm | 0 of 3 | EEG from the next trial: 1.203 mm | yes |
| 8 | Adjusted straight-line fit that already has past palm position | **1.691 mm** | 1.700 mm | 0 of 3 | EEG from the next trial: 1.694 mm | yes |
| 9 | Straight-line fit that already has force and motion history | 0.4442 N | **0.4402 N** | 2 of 3 | EEG from another lift: 0.4388 N | yes |
| 9 | Straight-line fit with force, motion and EMG | 0.4571 N | **0.4546 N** | 1 of 3 | not run | no |
| 10 | Straight-line fit that already has force and motion history | **0.6770 N** | 0.6955 N | 0 of 3 | EEG from the next lift: 0.6919 N | yes |
| 10 | Learned forecast that already has force and motion history | **0.9780 N** | 0.9936 N | 1 of 3 | EEG from the next lift: 0.9873 N | no |
| 10 | Straight-line fit with force, motion and EMG | **0.7168 N** | 0.7220 N | 1 of 3 | EEG from the next lift: 0.7188 N | no |
| 11 | Straight-line fit that already has recent sensor voltage | **0.3601 mV** | 0.4613 mV | 0 of 3 | EEG from the next trial: 0.4228 mV | yes |
| 12 | Straight-line fit with recent sensor voltage and EMG | **0.3455 mV** | 0.4739 mV | 0 of 3 | EEG from the next trial: 0.4453 mV | no |

EEG raised the error in 8 of the 12. Of the 6 that were a study's main question it lowered the error in 1: grip force in study 9, by 0.0040 N, and there EEG taken from a different lift lowered it further.

Eleven of the comparisons also fed the model EEG from the wrong trial or the wrong moment. Properly timed EEG did better than the wrong EEG in 3. It both lowered the error and beat its control in 2: the straight-line wrist fits of studies 1 and 2, on three people, and never as the main question.

Where the model had no history of the hand at all, EEG lost too: alone against a clock in study 6, and added to elapsed time in study 7.

Four studies set a pass rule for EEG in advance: 6, 9, 10 and 11. All four failed it.

### 4. Forearm EMG lowered the error in 10 of 17 comparisons, clearly only at the wrist

| Study | EMG added to | Without | With EMG | People better | The same model fed EMG from the wrong trial or moment | Main question? |
| ---: | --- | --- | --- | --- | --- | --- |
| 2 | Straight-line fit that already has wrist history | 6.530° | **6.174°** | not given | EMG from the next trial: 6.941° | yes |
| 3 | Learned forecast already corrected from wrist motion | 3.957° | **3.853°** | 3 of 3 | EMG from the next trial: 4.140° | yes |
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

In 6 of the 7 comparisons that were a study's main question, the average error fell. Only in three did the range in the results file stay clear of zero on EMG's side, and all three are wrist studies.

Studies 2 and 3 are the same three people on one pointing task. The gain holds whichever person is left out, and EMG from the next trial does worse than no EMG. Study 4 is four other people on everyday tasks: three of the four gained, the range only just clears zero, and one of the two wrist axes got worse.

Lower on average but inside the noise, or beaten by mistimed EMG: studies 12, 18 and 19, and the 50% rows of 21, 22 and 23. Higher: studies 9, 10 and 14, and the 10% and 30% targets of 21 and 22. At those two targets in study 21 all four people did worse with the five grids.

Eight comparisons had a wrong-trial or mistimed control. Properly timed EMG beat it in 6 and lost to it in studies 12 and 14.

EMG with no other input, fitted on one person and tried on another, lost to a fixed angle (study 5).

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

### 6. Eleven studies set a pass rule in advance. Seven failed it.

- **Failed:** studies 6, 9, 10, 11, 12, 13 and 24.
- **Split answer:** studies 16 and 19.
- **Passed by a margin too small to tell from zero:** study 18. Both averages were lower, by amounts whose ranges cross zero.
- **Passed:** study 20, on whether a band set per part of the pinch is narrower, holds at least as many readings and scores lower than one width throughout. It was, for all three forecasts. That says nothing about which forecast is better.
- **Set no rule:** the other 14.

Every failed rule concerned EEG, EMG, a cue term or a larger network. None concerned the plain history fit. No rule about adding a signal to a forecast was passed outright.

### 7. No general model has been fitted, and the evidence is narrower than 25 rows suggest

What exists is 23 separate small studies, each with its own straight-line fit or small network for one signal in one task; one macaque study in which two larger networks failed their pass rule, across 18 runs and 720 saved training epochs (study 24); and one run of a single network shared by a muscle signal and a glove signal, on one recording, which lost to "repeat the last value" on its own training data and predicts nothing from one signal to the other (study 25).

That shared network was an earlier, separate attempt. NeuroTranslate 0.0 is the name of the general model being built now. Its code has passed 29 checks on invented data. It has not been fitted to a real recording.

The project's working presumption is that more data, and more varied data, gives a more general model. No study here tests it: none varies how much data a model sees, or how varied it is.

The test groups are small, between 1 and 4 people. And the 23 studies draw on 8 datasets and fewer independent groups than that. Studies 1 to 3 score the same three people. So do 9 and 10, and 11 to 13. Studies 14 to 17 score the same four, and 21 and 22 the same four, who had already appeared in earlier pinch studies on other days. Studies 14 to 17 also score the 12 people the finger models were fitted on; those results are on each study's page, and are not the main comparison in the table above.

Every result comes from stored recordings scored after the fact. None is a live forecast. Every "120 ms" or "250 ms" is a distance along the stored clock.

## Twenty-two people and four recordings are still unopened

When each dataset was split, some people were set aside and their recordings never opened. Until one of these groups is opened, every number on this page describes data the project has already looked at.

| Recordings | Studies | Set aside, never opened |
| --- | --- | --- |
| Wrist pointing (EEG-EMG-WristMotion) | 1 to 3 | 6 people |
| Everyday tasks (KIN-MUS UJI) | 4 | 4 people |
| Hand to mouth (Lucchetti and colleagues) | 5 | 1 person |
| Palm (IACKD) | 6 | 1 person |
| Pinch and lift (WAY-EEG-GAL) | 9 and 10 | 3 people |
| Paced grip (HYGRIP) | 11 to 13 | 3 people |
| One finger (Hyser) | 14 to 17 | 4 people |
| Macaque fingers (LINK) | 24 | 4 recordings |

In the palm data the reserve was named for the first, two-person trial (study 6) and only its description was read. Studies 7 and 8 name no reserve.

The pinch studies (18 to 23) set nobody aside. Each fixed its test group in advance and scored it once, and the first plan says there is no further group. Later pinch studies reuse people from earlier ones on new days, and say so.

Not known either, because nothing in the repository measures it: any live result; any result in newtons for studies 11 to 17, whose datasets give no conversion from volts; any effect of more or more varied training data; any model that predicts one kind of signal from another across datasets.

## Whose recordings these are

Every dataset, who made it, its licence and the credit it is owed: [docs/RIGHTS.md](../docs/RIGHTS.md).
