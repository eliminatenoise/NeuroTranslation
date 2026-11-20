# The hand's own history is the forecaster to beat

Every study in this repository asks one question of one open dataset. Most ask the same one: a model already knows something about a movement, so does one more signal help it forecast what comes next?

Mostly it does not. A model fitted to the target's own recent history beat "repeat the last value" every time it was tried on the task it was fitted for. A brain signal from the scalp, added on top, usually made the forecast worse. A muscle signal helped at the wrist, and nowhere else beyond the noise. And when the task or the target moved, a one-line rule beat every fitted model.

This page holds the numbers: 23 studies in the 18 folders here (two folders hold more than one), and two more that are reported only in the papers. [The front page](../README.md) has the short version.

## How to read the numbers

Every score is an error: the average miss between a forecast and what was measured. Lower is better.

"Tested on" names people whose test recordings were never used to fit the model. A forecast that "repeats the last value" does nothing clever: it says the next reading will equal the latest one.

A *straight-line fit* is the plainest kind of model, a weighted sum of its inputs. A *learned forecast* is a small network that reads a stretch of recent history.

**EEG** is electrical activity of the brain, picked up on the scalp. **EMG** is electrical activity of muscle, picked up on the skin. It is a recording of muscle, not of nerve. **MVC** is the hardest squeeze a person could manage that day; pinch force is given as a percentage of it.

Units and measures change from study to study. Compare along a row, never between rows. Each study's own page gives its measure, its plan and its results file.

## Every study

### Wrist angle

Errors in degrees, both wrist axes together.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Wrist pointing: does a brain signal help a learned forecast?](wrist-pointing-temporal/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) | The two wrist angles a quarter of a second ahead (250 ms), at six moments after the cue | 3 people (fitted on 6 others) | Learned forecast from wrist history: **4.053°** | The same with scalp EEG added: **4.523°** | 0.469° higher (no range across people is published) | not published |
| 2 | [Wrist pointing: does a muscle signal help a straight-line fit?](wrist-pointing-muscle/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-pointing/) | The same two wrist angles, 250 ms ahead | the same 3 (fitted on 6 others) | Straight-line fit on wrist history: **6.530°** | The same with forearm EMG added: **6.174°** | 0.355° lower (0.232 to 0.469 lower; whichever one of the three people is left out) | not published (the change stays negative whichever person is left out) |
| 3 | [Wrist pointing: does the muscle signal still help the learned forecast?](wrist-forearm-transfer/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) | The same two wrist angles, 250 ms ahead | the same 3 (fitted on 6 others) | Learned forecast, corrected from wrist motion: **3.957°** | The same correction with EMG added: **3.853°** | 0.104° lower (0.072 to 0.125 lower; whichever one of the three people is left out) | 3 of 3 |
| 4 | [Everyday tasks: does a muscle signal help estimate the wrist angle?](uji-wrist-emg/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) | The two wrist angles at least 250 ms after the last EMG sample, during 26 everyday activities | 4 people (fitted on 14 others) | Which activity it is and how long it has run: **36.187°** | The same with EMG added: **34.718°** | 1.468° lower (0.016 to 2.936 lower; middle 95% when the four people are resampled) | 3 of 4 |

### Elbow angle

Errors in degrees.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 5 | [Hand to mouth: can one person's muscle signal follow another person's elbow?](surface-emg-elbow/) | The elbow angle 40 ms ahead, during five hand-to-mouth movements | 1 person (fitted on 1 other) | The average path, started when the movement starts: **30.77°** | EMG alone, fitted on someone else: **62.36°** | 31.59° higher (one test person; the EMG fit lost in all five repetitions) | 0 of 1 |

The table gives the measure that punishes large misses (root mean squared error). On the plain average miss the EMG fit lost as well: 58.24° against 26.37° for the timed average path and 25.10° for one fixed angle. The person and the arm changed together, left arm to fit and right arm to test, so the study cannot say which of the two broke the fit.

### Palm position

Errors in millimetres, along the one sideways axis the tracker reports.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 6 | [Palm, first try: can three scalp electrodes place the palm?](scalp-eeg-hand/) | Sideways palm position 10 ms after the last EEG sample, at nine moments after the cue | 1 person (fitted on 1 other) | The time within the task and nothing else: **7.383 mm** | Scalp EEG alone: **7.514 mm** | 0.131 mm higher (0.093 to 0.148 higher; whichever one test trial is left out) | 0 of 1 |
| 7 | [Palm: does a brain signal help once you know where the hand was?](scalp-eeg-palm-history/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay) | Sideways palm position 100 ms ahead, at nine moments in each trial | 3 people (fitted on 3 others) | Time, and where the palm has been: **1.093 mm** | The same with EEG added: **1.223 mm** | 0.131 mm higher (0.030 to 0.170 higher; across the three people) | 0 of 3 |
| 8 | [Palm: does one recording of a person improve the forecast on their next?](scalp-eeg-personal-calibration/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/index.html#personal-calibration) | The same, on each person's second recording | 3 new people, on their second recording | The model with EEG, as fitted on other people: **1.849 mm** | The same model, adjusted on the person's own first recording: **1.700 mm** | 0.150 mm lower (0.069 to 0.284 lower; across the three people) | 3 of 3 |

### Grip force during a lift

Errors in newtons.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 9 | [Pinch and lift: does a brain signal help forecast grip force?](way-grip-force/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) | Grip force 120 ms ahead, on a schedule tied to the go cue | 3 people (fitted on 6 others) | Force and motion history: **0.4442 N** | The same with EEG added: **0.4402 N** | 0.0040 N lower (no range is published) | 2 of 3 |
| 10 | [Pinch and lift, timed from the squeeze: the same question](way-contact-force/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) | Grip force 120 ms ahead, at five moments after the plates register a squeeze | the same 3 (fitted on 6 others) | Force and motion history: **0.6770 N** | The same with EEG added: **0.6955 N** | 0.0185 N higher (from 0.0034 lower to 0.0404 higher; 95% interval across the three people) | 0 of 3 |

### Sensor voltage during a paced grip or a finger press

Errors in millivolts. Neither dataset says how many newtons a volt is, so these are errors in the sensor's voltage, not in force.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 11 | [Paced grip: does a brain signal help forecast the grip sensor?](hygrip-force/results-2026-11-19/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | The grip sensor's voltage 120 ms ahead, during ten paced squeezes per trial | 3 people (fitted on 7 others) | Cue timing and recent voltage: **0.3601 mV** | The same with EEG added: **0.4613 mV** | 0.1012 mV higher (from 0.2766 lower to 0.4791 higher; 95% interval across the three people) | 0 of 3 |
| 12 | [Paced grip: does a muscle signal help forecast the grip sensor?](hygrip-force/forearm-results/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | The same as study 11 | the same 3 | Cue timing and recent voltage: **0.3601 mV** | The same with EMG added: **0.3455 mV** | 0.0146 mV lower (from 0.1203 lower to 0.0912 higher; 95% interval across the three people) | 1 of 3 |
| 13 | [Paced grip: does letting the fit change with the cue help?](hygrip-force/cue-phase/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | The same as study 11 | the same 3 | The plain fit on recent voltage: **0.3601 mV** | A fit allowed to differ between squeeze and rest: **0.3741 mV** | 0.0140 mV higher (from 0.0171 lower to 0.0451 higher; 95% interval across the three people) | 0 of 3 |
| 14 | [One finger: does a muscle signal help forecast the finger sensor?](hyser-index/RESULTS.md) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The index-finger sensor's voltage 120 ms ahead, during freely chosen presses | 4 people (fitted on 12 others) | The sensor's last 41 readings: **14.355 mV** | The same with EMG added: **14.457 mV** | 0.103 mV higher (from 0.115 lower to 0.321 higher; middle 95% when the four people are resampled) | 2 of 4 |
| 15 | [One finger, next day: does a personal adjustment from day one help on day two?](hyser-index/crossday/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The same, on the person's second recording day | the same 4, on their second day | The shared model, unchanged: **14.912 mV** | Adjusted on the person's own first day: **15.091 mV** | 0.180 mV higher (0.171 to 0.188 higher; middle 95% when the two donor pairs are resampled, not a range across people) | 1 of 4 |
| 16 | [One finger: do the other four fingers' sensors help?](hyser-index/whole-hand/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The same as study 14 | the same 4 | Index-finger history: **14.355 mV** | The other four fingers' histories added: **14.161 mV** | 0.193 mV lower (from 0.573 lower to 0.187 higher; middle 95% when the four people are resampled) | 2 of 4 |
| 17 | [One finger, new task: do the fitted models carry over to prescribed presses?](hyser-index/prescribed/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | The same voltage, during 15 prescribed finger combinations | the same 4, on a task the models never saw | Index-finger history: **7.992 mV** | Five fingers' histories: **7.802 mV** | 0.190 mV lower (0.124 to 0.279 lower; middle 95% when the four people are resampled) | 4 of 4 |

### Pinch force between two fingers

Errors in % of the hardest squeeze the person could manage that day (their MVC, maximum voluntary contraction).

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 18 | [Pinch: does a muscle signal help forecast the force gauge?](cemhsey-pinch/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) | The gauge reading 120 ms ahead, during a pinch held at 30% of the hardest squeeze | 4 people (fitted on 3 others) | Force history and the on-screen cue: **0.4634%** | The same with EMG added: **0.4632%** | 0.0002% lower (from 0.0007 lower to 0.0005 higher; middle 95% when the four people are resampled) | 3 of 4 |
| 19 | [Pinch: does keeping the five electrode grids apart help?](cemhsey-arrays/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) | The same as study 18 | 4 new people (fitted on the same 3) | EMG as one overall amplitude: **0.51663%** | EMG as five separate grids: **0.51659%** | 0.00004% lower (from 0.00110 lower to 0.00102 higher; middle 95% when the four people are resampled) | 2 of 4 |
| 20 | [Pinch: how wide must the band around a forecast be?](cemhsey-intervals/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/) | A band meant to hold 90% of the gauge readings 120 ms ahead | 2 people (band widths set on 4 others) | One band width for the whole pinch, around the five-grid forecast: **2.21%** wide, 4476 of 4736 later readings inside | A width for each part of the pinch: **2.16%** wide, 4502 inside | narrower and holds more; the note below has all three forecasts | not counted per person |
| 21 | [Pinch at new targets: does the model fitted at 30% cope with 50%?](cemhsey-transfer/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/results/) | The gauge reading 120 ms ahead, at a 50% target (10% and 30% were scored too) | 4 people, one day each | A one-line rule: the current reading plus the change the on-screen schedule calls for: **0.5721%** | The fitted five-grid model after one practice pinch: **0.6987%** | 0.1266% higher (0.0502 to 0.1938 higher; across the four people) | 0 of 4 |
| 22 | [Pinch, next day: does yesterday's personal number still help?](cemhsey-carry/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-carry/) | The same, on the next recording day | the same 4, a day later | The fitted model with a fresh personal number: **0.70643%** | The fitted model with yesterday's number: **0.70578%** | 0.00065% lower (from 0.00391 lower to 0.00249 higher; across the four people) | 3 of 4 |
| 23 | [Pinch: can a correction learned from other people fix the rise and the release?](cemhsey-phase/) · [open in the browser](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/) | The gauge reading 120 ms ahead, at a 50% target | 3 people (corrections fitted on 3 others) | The one-line rule: **0.70007%** | The rule with a correction learned from 3 other people: **0.69509%** | 0.00498% lower (from 0.05000 lower to no change; rounded bounds that enclose the three people; the exact ends are withheld) | 3 of 3 |

### Reported only in the papers

No folder under `benchmarks/`. The first has no result file in the repository at all: its numbers are copied from the technical paper. Both use units scaled to the data, so the numbers mean nothing outside their own row.

| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 24 | [Macaque fingers from motor cortex (the LINK study): does a network that reads brain history beat a straight-line fit?](../papers/current/research-evidence-reading-aid.md#separate-studies) | The position of the index finger, and of the other three fingers as a group, from the brain recording | 1 macaque, 2 later days (fitted on 4 days) | Straight-line fit on the latest brain sample: **0.0314982** | A network that reads recent brain history: **0.0299609** | 0.0015373 lower (0.0003470 to 0.0027587 lower; 95% interval given in the paper) | one animal |
| 25 | [First run of one network shared by two signals: does it beat repeating the last value?](../papers/current/research-evidence-reading-aid.md#one-acquisition-two-forecasting-tasks) | Each signal's own next values from its own past. Nothing is predicted from one signal to the other | nobody: scored on its own training recording | Repeat the last value (glove signal): **0.0245** | One network shared by both signals, after 990 training steps (glove signal): **0.3722** | 0.3477 higher (one recording, no range) | one recording |

**Which comparison is shown.** The one the study's own plan names as its main one. Where a plan names none, the comparison its results file calls primary. Where a plan fixes a measure but no single comparison (studies 21 to 23), the one the study's own page leads with. Study 15 is the exception: its page leads with the 12 people the model was fitted on, and the table shows the 4 test people, so that studies 14 to 17 all show the same four.

**Study 20 compares bands, not forecasts.** A band is a range meant to hold 90% of the readings that follow. For each of three forecasts the study sets a band whose width is fixed for each part of the pinch against one width for the whole pinch, on the same 4736 readings from two people.

| Band around | One width: how wide, readings inside, score | A width per part of the pinch: how wide, readings inside, score |
| --- | --- | --- |
| "Repeat the last value" | 2.89%, 4493, 3.32 | 2.54%, 4499, 2.90 |
| The fit on force history and the cue | 2.20%, 4466, 2.60 | 2.15%, 4494, 2.47 |
| The five-grid fit | 2.21%, 4476, 2.60 | 2.16%, 4502, 2.48 |

The score charges a band for its width and for every reading it misses, so lower is better. All six bands held more than the 90% asked of them over the whole pinch (94.3% to 95.1%). All six fell short while the pinch was being released (86.1% to 89.6%).

## What it adds up to

Counts, not impressions. A "comparison" is one pair of scores on the same forecasts. Several studies share the same handful of people, so the comparisons are not independent of one another; the last statement says how far that goes. In each table the lower score of the pair is in bold.

### 1. A model fitted to the target's own history beat "repeat the last value" in 8 of 8 studies

| Study | "Repeat the last value" | Fitted to the target's own history |
| ---: | --- | --- |
| 1 | Last angle repeated: 7.925° | Learned forecast on wrist history: **4.053°** |
| 7 | Last palm position repeated: 4.439 mm | Straight-line fit on time and past palm: **1.093 mm** |
| 9 | Last force repeated: 0.7878 N | Straight-line fit on force and motion history: **0.4442 N** |
| 10 | Current force repeated: 1.7173 N | Straight-line fit on force and motion history: **0.6770 N** |
| 11 | Current voltage repeated: 0.5168 mV | Straight-line fit on timing and recent voltage: **0.3601 mV** |
| 14 | Current reading repeated: 17.945 mV | Straight-line fit on the last 41 readings: **14.355 mV** |
| 18 | Current reading repeated: 0.5464% | Straight-line fit on force history and the cue: **0.4634%** |
| 19 | Current reading repeated: 0.64513% | Straight-line fit on force history and the cue: **0.51675%** |

That is every study that has such a baseline and scores the model on the task it was fitted for. Studies 2 and 3 reuse the people of study 1 and are not counted twice. Study 4 has no such baseline.

Two of the eight wins carry a footnote. In study 9, whenever the force to be forecast was at or below 0.5 N, repeating the last force beat every fitted model. In study 7, a straight line through the palm's recent speed beat the fitted model on the average miss and lost to it on the measure that punishes large misses.

The fitted models of studies 5 and 6 never saw the target's history. They lost to a fixed average and to a clock.

### 2. Move the task or the target, and a one-line rule won 6 times out of 6

The first one-line rule is "repeat the last value".

| Study | What changed | "Repeat the last value" | Best fitted model |
| ---: | --- | --- | --- |
| 17 | A new task (prescribed presses) | **7.222 mV** | 7.802 mV (five finger histories) |
| 21 | A new target level (10%) | **0.3819%** | 0.5635% (force history) |
| 21 | The fitted level (30%), new people and a practice pinch | 0.5461% | **0.4274%** (force history) |
| 21 | A new target level (50%) | 0.7369% | **0.6987%** (five grids) |
| 22 | A new target level (10%) on the next day | **0.40148%** | 0.56114% (force history with yesterday's personal number) |
| 22 | The fitted level (30%) on the next day | 0.56534% | **0.44618%** (force history, no personal number) |
| 22 | A new target level (50%) on the next day | 0.75791% | **0.70578%** (five-grid fit with yesterday's personal number) |
| 23 | A new target level (50%), new people | **0.81104%** | 0.82204% (five grids with separate rise and release corrections) |

The second rule exists only in the pinch studies, where the screen shows the person a target that changes on a known schedule: take the current reading and add the change the schedule calls for.

| Study | Target | Current reading plus the scheduled change | Best fitted model | People better with the fitted model |
| ---: | --- | --- | --- | --- |
| 21 | 10% | **0.3693%** | 0.5635% | 0 of 4 |
| 21 | 30%, the fitted level | 0.4480% | **0.4274%** | 4 of 4 |
| 21 | 50% | **0.5721%** | 0.6987% | 0 of 4 |
| 22 | 10%, next day | **0.38493%** | 0.56114% | 0 of 4 |
| 22 | 30%, the fitted level, next day | 0.48173% | **0.44618%** | 4 of 4 |
| 22 | 50%, next day | **0.58356%** | 0.70578% | 1 of 4 |
| 23 | 50%, new people | **0.69509%** | 0.82204% | 0 of 3 |

At a new task or a new target level there are 6 settings. In all of them one of the two rules beat the best fitted model. The fitted model stayed ahead of plain repeating in 2 of the 6, and ahead of the schedule rule in 0 of 5, where it was better for 1 person out of 19 person-by-setting comparisons.

The model was not broken. At 30%, the level it had been fitted at, the same new people put it ahead of both rules on both days (2 of 2 settings). It had learned one target.

Study 17 splits by measure: on the measure that punishes large misses, the fitted model beat the last reading. Studies 21 to 23 come from one dataset and largely the same people.

### 3. Scalp EEG lowered the error in 4 of 12 comparisons, and passed no test

| Study | EEG added to | Without | With EEG | People better | The same model fed EEG from the wrong trial or moment | Main question? |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Learned forecast that already has wrist history | **4.053°** | 4.523° | not published | EEG from another trial: 4.880° | yes |
| 1 | Straight-line fit that already has wrist history | 6.530° | **6.439°** | not published | EEG from another trial: 6.782° | no |
| 2 | Straight-line fit that already has wrist history and EMG | 6.174° | **6.127°** | not published | EEG from another trial: 6.379° | no |
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
| 2 | Straight-line fit that already has wrist history | 6.530° | **6.174°** | not published | EMG from the next trial: 6.941° | yes |
| 3 | Learned forecast already corrected from wrist motion | 3.957° | **3.853°** | 3 of 3 | EMG from the next trial: 4.140° | yes |
| 4 | Fit that knows the activity and elapsed time (no wrist history) | 36.187° | **34.718°** | 3 of 4 | EMG shifted in time: 35.385° | yes |
| 9 | Straight-line fit that already has force and motion history | **0.4442 N** | 0.4571 N | not published | not run | no |
| 10 | Straight-line fit that already has force and motion history | **0.6770 N** | 0.7168 N | 0 of 3 | not run | no |
| 12 | Straight-line fit that already has recent sensor voltage | 0.3601 mV | **0.3455 mV** | 1 of 3 | EMG moved within the trial: 0.3427 mV | yes |
| 14 | Straight-line fit that already has recent sensor readings | **14.355 mV** | 14.457 mV | 2 of 4 | EMG from another trial: 14.424 mV | yes |
| 18 | Straight-line fit that already has force history and the cue | 0.4634% | **0.4632%** | 3 of 4 | EMG from the other repeat: 0.4640% | yes |
| 19 | Straight-line fit that already has force history and the cue (new people) | 0.51675% | **0.51663%** | 3 of 4 | EMG from the other repeat: 0.51742% | no |
| 19 | Fit that already has force history, the cue and overall EMG amplitude (adds the five grid profiles) | 0.51663% | **0.51659%** | 2 of 4 | Five grids from the other repeat: 0.51737% | yes |
| 21 | Force-history fit after practice, at the 50% target (adds five grids) | 0.7085% | **0.6987%** | 2 of 4 | not run | no |
| 21 | Force-history fit after practice, at the 10% target (adds five grids) | **0.5635%** | 0.5734% | 0 of 4 | not run | no |
| 21 | Force-history fit after practice, at the 30% target (adds five grids) | **0.4274%** | 0.4306% | 0 of 4 | not run | no |
| 22 | Force-history fit with yesterday's number, at the 50% target, next day (adds five grids) | 0.72046% | **0.70578%** | 2 of 4 | not run | no |
| 22 | Force-history fit with yesterday's number, at the 10% target, next day (adds five grids) | **0.56114%** | 0.57129% | 1 of 4 | not run | no |
| 22 | Force-history fit with yesterday's number, at the 30% target, next day (adds five grids) | **0.44688%** | 0.44756% | 2 of 4 | not run | no |
| 23 | Force-history fit with separate rise and release corrections, at the 50% target (adds five grids) | 0.82834% | **0.82204%** | not published | not run | no |

In 6 of the 7 comparisons that were a study's main question, the average error fell. Only in three did the published range stay clear of zero on EMG's side, and all three are wrist studies.

Studies 2 and 3 are the same three people on one pointing task. The gain holds whichever person is left out, and EMG from the next trial does worse than no EMG. Study 4 is four other people on everyday tasks: three of the four gained, the range only just clears zero, and one of the two wrist axes got worse.

Lower on average but inside the noise, or beaten by mistimed EMG: studies 12, 18 and 19, and the 50% rows of 21, 22 and 23. Higher: studies 9, 10 and 14, and the 10% and 30% targets of 21 and 22. At those two targets in study 21 all four people did worse with the five grids.

Eight comparisons had a wrong-trial or mistimed control. Properly timed EMG beat it in 6 and lost to it in studies 12 and 14.

EMG with no other input, fitted on one person and tried on another, lost to a fixed angle (study 5).

Rules set in advance on EMG: study 12 failed; study 18 passed in name, with ranges that cross zero; study 19 passed its weaker tier and failed its stronger one.

### 5. Adjusting a model to a person, a day or a group lowered the error 5 times in 6, once by more than 1%

| Study | Adjustment | Before | After | People better |
| ---: | --- | --- | --- | --- |
| 8 | Adjust the palm model on the person's first recording | 1.849 mm | **1.700 mm** | 3 of 3 |
| 15 | Adjust the finger-sensor forecast on the person's own day one (4 test people) | **14.912 mV** | 15.091 mV | 1 of 4 |
| 15 | The same adjustment, 12 people the model was fitted on | 17.610 mV | **17.589 mV** | 4 of 12 |
| 21 | One practice pinch at the 50% target (five-grid fit) | 0.6995% | **0.6987%** | 2 of 4 |
| 22 | Reuse yesterday's personal number instead of none (five-grid fit, 50%) | 0.70804% | **0.70578%** | 3 of 4 |
| 23 | A correction learned from other people, applied to the simple forecast | 0.70007% | **0.69509%** | 3 of 3 |

One comparison is counted per tested group, at each study's main setting. The one that mattered is study 8: a single earlier recording of the same person helped all three people, by 0.150 mm on 1.849 mm. In studies 21, 22 and 23, and in the 12-person half of study 15, the change was under 1% of the error. In the 4-person half of study 15 the adjustment made things worse.

Carrying a model to new people with no adjustment at all worked on the same task in studies 1, 4, 7, 9, 11, 14, 18 and 19: every one beat its naive baseline on people it had never seen. It failed outright in the two one-to-one trials, studies 5 and 6.

### 6. Eleven studies set a pass rule in advance. Seven failed it.

- **Failed:** studies 6, 9, 10, 11, 12, 13 and 24.
- **Split answer:** studies 16 and 19.
- **Passed in name only:** study 18. Both averages were lower, by amounts whose ranges cross zero.
- **Passed:** study 20, on whether a band set per part of the pinch is narrower, holds at least as many readings and scores lower than one width throughout. It was, for all three forecasts. That says nothing about which forecast is better.
- **Set no rule:** the other 14.

Every failed rule concerned EEG, EMG, a cue term or a larger network. None concerned the plain history fit. No rule about adding a signal to a forecast was passed outright.

### 7. No general model has been fitted, and the evidence is narrower than 25 rows suggest

What exists is 23 separate small studies, each with its own straight-line fit or small network for one signal in one task; one macaque study in which two larger networks failed their test (study 24); and one run of a single network shared by a muscle signal and a glove signal, on one recording, which lost to "repeat the last value" on its own training data and predicts nothing from one signal to the other (study 25).

NeuroTranslate 0.0 is the name of the general model being built. Its code has passed 29 checks on made-up data. It has not been fitted to a real recording.

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
