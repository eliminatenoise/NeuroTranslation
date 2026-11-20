# NeuroTranslation

Reach for a cup. Your brain gives the order, the muscles of your forearm pull, and the hand moves. One act, recorded three ways: in nerve, in muscle and in motion.

NeuroTranslation is the attempt to translate between those records: take one, predict another, and check the prediction against what the body did. Everything here is built on recordings that other people measured and shared openly.

**The hand's own history still beats the brain signal.** That is the result so far, from 23 small studies of wrists, elbows, palms, grips and fingers:

- A forecast fitted to the hand's own recent past beat "repeat the last value" in **8 of 8** studies.
- Adding a brain recording taken at the scalp (EEG) to that forecast made it worse in **8 of 12** comparisons. EEG passed none of the 4 tests set for it in advance.
- Adding a muscle recording from the forearm (EMG) lowered the error in **10 of 17**. Only in the wrist was the gain clear of the spread between people.
- Change the task or the target, and a one-line rule beat the best fitted model in **6 of 6** settings.

What exists today is those studies, 14 pages that run them in a browser, two draft papers and a sister game, NeuroSurge. What does not exist is a general model. **NeuroTranslate 0.0** is the name of the one being built, not of anything you can download. The browser app has that name in its title; the model is not in it.

## Where to click

- **[Start page](https://eliminatenoise.github.io/NeuroTranslation/START.html).** Runs in a browser, nothing to install. Try an invented example, or pick the recording you hold and open the page that reads it. Behind it are the study readers, and an app that lines up your own recordings on one clock.
- **[The studies](benchmarks/README.md).** All 23, each with its plan and its results file, and the counts above worked out row by row.
- **[The papers](papers/README.md).** Two working drafts, each in a Technical and a Simple English edition.
- **[Launchers and offline copies](LAUNCHERS.md)** for Windows, macOS and Linux.
- **[NeuroSurge](https://github.com/eliminatenoise/NeuroSurge)**, the sister project: a browser game in which you look at a motor area of the brain and the body part it drives moves.

## A translation needs both texts from the same moment

The model this project is working towards is a *large movement model*: one model that learns how nerve, muscle and movement go together. It is meant to learn from four kinds of data.

| Kind of data | What it is | What it is not |
| --- | --- | --- |
| **Neural recordings** | Electrical activity of the nervous system, at the places where the electrodes sat: brain, spinal cord or the nerves of the body. | A recording at one place is not a recording at another. EEG from the scalp says nothing direct about a nerve in the arm. |
| **Muscle recordings** | EMG: the electrical activity of muscle, picked up on the skin over it. | A recording of muscle, not of nerve. Not a force either: getting force out of EMG takes a second measurement or a mechanical model. |
| **Motion capture** | Where the body went: joint angles and hand positions, with their units and their clock. The studies here also forecast measured force. | The movement itself. It is a tracker's estimate, with the tracker's error. |
| **Physics-based simulation of the body** | Movement and force computed from a model of bones, joints and muscles. | Measured. A simulation is tested against a measurement of the same task, never the other way round. |

A fifth thing is needed, and it is not data. It is the pairing.

Suppose the motion recording belongs to a different reach. It can still teach a model what reaches look like. It cannot say where *this* hand was when *this* nerve fired. A translation can be checked only when both recordings come from the same person, the same movement and the same clock, and even two files that name the same clock can be offset from each other. Every study below uses signals that were recorded together.

The bet behind a large model is that more data, and more varied data, makes a model that carries further. That is the project's working presumption. It is untested: no study here varies how much data a model sees, or how varied it is.

NeuroTranslation is one part of **Brain2Body**, the name of the whole programme and of its second paper, which asks what a person keeps once a machine stops guiding their hand.

## History did the work: every study in one table

Each row sets a reference forecast against a challenger that was given something extra. Every score is an error, the average miss between forecast and measurement, so lower is better. The recordings a model is scored on were never used to fit it, except in the last row. Units change from block to block: compare along a row, never down a column.

| Study | Tested on | Reference forecast | Challenger | Who won |
| --- | --- | --- | --- | --- |
| **Wrist angle, a quarter of a second ahead** (degrees) | | | | |
| [Wrist pointing: does a brain signal help a learned forecast?](benchmarks/wrist-pointing-temporal/) | 3 people | Learned forecast from wrist history: 4.05° | With scalp EEG added: 4.52° | **History.** EEG made the forecast 0.47° worse. |
| [Wrist pointing: does a muscle signal help a straight-line fit?](benchmarks/wrist-pointing-muscle/) | the same 3 | Straight-line fit on wrist history: 6.53° | With forearm EMG added: 6.17° | **EMG**, by 0.36°. EMG taken from the wrong trial did worse than none: 6.94°. |
| [Wrist pointing: does the muscle signal still help the learned forecast?](benchmarks/wrist-forearm-transfer/) | the same 3 | Learned forecast, corrected from wrist motion: 3.96° | With EMG added: 3.85° | **EMG**, by 0.10°, for 3 of 3 people. |
| [Everyday tasks: does a muscle signal help estimate the wrist angle?](benchmarks/uji-wrist-emg/) | 4 people | Which activity it is and how long it has run: 36.2° | With EMG added: 34.7° | **EMG**, by 1.5°, for 3 of 4 people. Bending up and down got 2.4° better; tilting side to side got 0.7° worse. |
| **Elbow angle** (degrees) | | | | |
| [Hand to mouth: can one person's muscle signal follow another person's elbow?](benchmarks/surface-emg-elbow/) | 1 person | The average path, started when the movement starts: 30.8° | EMG alone, fitted on someone else: 62.4° | **The average path**, by 31.6° on the measure that punishes large misses. EMG lost on the plain average miss too. |
| **Sideways position of the palm** (millimetres) | | | | |
| [Palm, first try: can three scalp electrodes place the palm?](benchmarks/scalp-eeg-hand/) | 1 person | The time within the task and nothing else: 7.38 mm | Scalp EEG alone: 7.51 mm | **The clock**, by 0.13 mm. |
| [Palm: does a brain signal help once you know where the hand was?](benchmarks/scalp-eeg-palm-history/) | 3 people | Time, and where the palm has been: 1.09 mm | With EEG added: 1.22 mm | **History.** EEG helped 0 of 3 people. |
| [Palm: does one recording of a person improve the forecast on their next?](benchmarks/scalp-eeg-personal-calibration/) | 3 new people | The model as fitted on other people: 1.85 mm | Adjusted on the person's own first recording: 1.70 mm | **The adjustment**, by 0.15 mm, for 3 of 3. EEG still added nothing. |
| **Grip force during a lift, 120 ms ahead** (newtons) | | | | |
| [Pinch and lift: does a brain signal help forecast grip force?](benchmarks/way-grip-force/) | 3 people | Force and motion history: 0.444 N | With EEG added: 0.440 N | **Nobody.** EEG from a different lift did better still (0.439 N), so the test set in advance was failed. |
| [Pinch and lift, timed from the squeeze: the same question](benchmarks/way-contact-force/) | the same 3 | Force and motion history: 0.677 N | With EEG added: 0.695 N | **History.** EEG helped 0 of 3 people. |
| **Sensor voltage during a paced grip or a finger press, 120 ms ahead** (millivolts) | | | | |
| [Paced grip: does a brain signal help forecast the grip sensor?](benchmarks/hygrip-force/results-2026-11-19/) | 3 people | Cue timing and recent voltage: 0.360 mV | With EEG added: 0.461 mV | **History.** EEG helped 0 of 3 people. |
| [Paced grip: does a muscle signal help forecast the grip sensor?](benchmarks/hygrip-force/forearm-results/) | the same 3 | Cue timing and recent voltage: 0.360 mV | With EMG added: 0.345 mV | **Nobody.** Lower on average but for only 1 of 3 people, and EMG moved to the wrong moment did better still (0.343 mV). |
| [Paced grip: does letting the fit change with the cue help?](benchmarks/hygrip-force/cue-phase/) | the same 3 | The plain fit: 0.360 mV | A fit allowed to differ between squeeze and rest: 0.374 mV | **The plain fit.** The other helped 0 of 3 people. |
| [One finger: does a muscle signal help forecast the finger sensor?](benchmarks/hyser-index/RESULTS.md) | 4 people | The sensor's last 41 readings: 14.35 mV | With EMG added: 14.46 mV | **History**, by 0.10 mV. EMG helped 2 of 4 people. |
| [One finger, next day: does a personal adjustment from day one help on day two?](benchmarks/hyser-index/crossday/) | the same 4, on their second day | The shared model, unchanged: 14.91 mV | Adjusted on the person's own first day: 15.09 mV | **The unchanged model.** The adjustment helped 1 of 4. In the 12 people the model was fitted on it gained 0.02 mV. |
| [One finger: do the other four fingers' sensors help?](benchmarks/hyser-index/whole-hand/) | the same 4 | Index-finger history: 14.35 mV | With the other four fingers added: 14.16 mV | **Split.** Lower on average in these 4 people, though for only 2 of 4; higher in the 12 the model was fitted on. |
| [One finger, new task: do the fitted models carry over to prescribed presses?](benchmarks/hyser-index/prescribed/) | the same 4, on a new task | Index-finger history: 7.99 mV | Five fingers: 7.80 mV | **Five fingers beat one**, for 4 of 4. Repeating the last reading beat both: 7.22 mV. |
| **Pinch force between two fingers, 120 ms ahead** (% of the person's hardest squeeze that day) | | | | |
| [Pinch: does a muscle signal help forecast the force gauge?](benchmarks/cemhsey-pinch/) | 4 people | Force history and the on-screen cue: 0.4634% | With EMG added: 0.4632% | **No measurable difference.** |
| [Pinch: does keeping the five electrode grids apart help?](benchmarks/cemhsey-arrays/) | 4 new people | EMG as one overall amplitude: 0.51663% | EMG as five separate grids: 0.51659% | **No measurable difference.** Better for 2 of 4 people, and the sign flipped between the two days. |
| [Pinch: how wide must the band around a forecast be?](benchmarks/cemhsey-intervals/) | 2 people | One band width for the whole pinch: 2.21% wide, holds 94.5% of later readings | A width for each part of the pinch: 2.16% wide, holds 95.1% | **The band set part by part**: narrower, and it holds more. Both were meant to hold 90%, and both fell short while the pinch was released (87.1% and 88.0%). |
| [Pinch at new targets: does the model fitted at 30% cope with 50%?](benchmarks/cemhsey-transfer/) | 4 people | A one-line rule, the current reading plus the change the on-screen schedule calls for: 0.572% | The fitted five-grid model after one practice pinch: 0.699% | **The one-line rule.** The model beat it for 0 of 4 people. |
| [Pinch, next day: does yesterday's personal number still help?](benchmarks/cemhsey-carry/) | the same 4, a day later | The fitted model with a fresh personal number: 0.70643% | With yesterday's number: 0.70578% | **No measurable difference.** The one-line rule beat both: 0.584%. |
| [Pinch: can a correction learned from other people fix the rise and the release?](benchmarks/cemhsey-phase/) | 3 people | The one-line rule: 0.70007% | With a correction learned from 3 other people: 0.69509% | **The correction**, by 0.005%, for 3 of 3. The fitted model lost to both: 0.822%. |
| **Reported only in the papers** (units scaled to the data) | | | | |
| [Macaque fingers from motor cortex (the LINK study): does a network that reads brain history beat a straight-line fit?](papers/current/research-evidence-reading-aid.md#separate-studies) | 1 macaque | Straight-line fit on the latest brain sample: 0.03150 | A network that reads recent brain history: 0.02996 | **Failed its test.** Lower on average, but worse for the index finger on the second test day. All five further claims failed too. |
| [First run of one network shared by two signals: does it beat repeating the last value?](papers/current/research-evidence-reading-aid.md#one-acquisition-two-forecasting-tasks) | nobody held out | Repeat the last value: 0.0245 | One network shared by a muscle signal and a glove signal, after 990 training steps: 0.372 | **Repeating the last value**, on the network's own training recording. |

Two more counts. Adjusting a model to one person, one day or one group lowered the error in 5 of 6 comparisons, but in only 1 of them by more than 1% of the error. And 11 studies fixed a pass rule before any scoring: 7 failed it, 2 gave a split answer, 1 passed in name only, and 1 passed on a question about band widths. No rule about adding a signal to a forecast was passed outright.

Read the table for what it is. No test group is larger than 4 people, the 23 studies draw on 8 datasets, and several rows score the same three or four people again. The brain signal in every study on people is EEG from 3 to 32 electrodes on the scalp: nothing here was recorded inside a human brain. And nothing was forecast live: every "ahead" is a distance along a stored recording.

[The studies page](benchmarks/README.md) has every number with its range and its controls.

## Twenty-two people have never been scored

When each dataset was split, some people were set aside and their recordings left unopened: 22 people in 7 datasets, and four recordings of the macaque. Until one of those groups is opened, every number above comes from people the project has already looked at.

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

The six pinch studies set nobody aside. Each fixed its test group in advance and scored it once.

## Two papers, each written twice

| | Technical | Simple English |
| --- | --- | --- |
| *NeuroTranslation: A New Paradigm In Brain-Body Mapping.* | [PDF, 153 pages](papers/current/neurotranslation-technical.pdf) | [PDF, 188 pages](papers/current/neurotranslation-explained.pdf) |
| *Brain2Body: The Next Generation In Body-Brain Interfacing.* | [PDF, 136 pages](papers/current/brain2body-article.pdf) | [PDF, 152 pages](papers/current/brain2body-simple-english.pdf) |

The first paper asks what a recording of brain or muscle adds once a model already knows how the body has been moving. It carries the macaque study and most of the human studies above. The second asks what a person keeps when a machine guides their hand through a skill and then stops. It is a proposal: it reports no experiment of its own on that question.

Both are working drafts, and nobody outside the project has reviewed them. They were last built on 19 November 2026 and do not yet contain study 23. [How to read them, and where each study sits in each one](papers/README.md).

## Run it yourself

**In a browser.** Open the [start page](https://eliminatenoise.github.io/NeuroTranslation/START.html). A recording you open is read on your own computer and goes nowhere.

**Offline.** Most readers have a ZIP that runs without a network, with a launcher for Windows, macOS and Linux. [LAUNCHERS.md](LAUNCHERS.md) lists them.

**A study, from the original recordings.** Each folder under [`benchmarks/`](benchmarks/README.md) holds the study's plan and its results file. Several also hold the code that scores the recordings again. You fetch the recordings yourself, from their own archive. The palm study, for example, with Python 3.13:

```
cd benchmarks/scalp-eeg-palm-history
python -m pip install -r requirements.txt
python fetch_inputs.py --output ../iackd-data
python -m unittest -v
python run.py --input ../iackd-data --output ../availability-run
```

**The app, from source.** `cd demo`, then `npm test` and `npm run build`. [demo/README.md](demo/README.md) says what the app does with a file you give it.

## Whose recordings these are

None of the recordings is ours. Ten open datasets, measured by other people, carry everything on this page:

EEG-EMG-WristMotion · KIN-MUS UJI · the upper-limb dataset of Lucchetti and colleagues · IACKD · WAY-EEG-GAL · HYGRIP · Hyser · CEMHSEY GRASP · LINK · Reach&Grasp

**[Who made each one, its licence and the credit it is owed are in one file: docs/RIGHTS.md](docs/RIGHTS.md).** The licences are CC BY 4.0, CC0 1.0, ODC-By 1.0 and MIT. You fetch each recording from its own archive. What is published here is fitted models and summary results derived from them.

What the project itself wrote, text and code, is dedicated to the public domain under [CC0 1.0](LICENSE). That covers none of the recordings, nor the fonts inside the PDFs.

## The other two projects

**[NeuroSurge](https://github.com/eliminatenoise/NeuroSurge)** is a game for learning which part of the brain moves which part of the body. Its numbers are made up by the rules of the game. They are not forecasts from the studies here.

**[Interoceptomics](https://github.com/eliminatenoise/Interoceptomics)** is a proposed field of science: how the body senses its own interior, joined to the mapping of nerve connections. Today it is a 3D atlas of the human brain that you can turn, cut and measure.
