# NeuroTranslation

**What a hand has just done still beats a brain signal read at the scalp.**

That was the finding across the [original 23 movement-forecast studies](benchmarks/README.md). Each takes open recordings of people, measured and shared by others, and forecasts what a hand or an arm does a fraction of a second later: the angle of a wrist, the position of a palm, the force of a grip. A hand tends to keep moving the way it was moving, so its own recent past is a hard forecast to beat. A brain or muscle signal earns its place only by beating it.

- Adding a brain recording taken at the scalp (EEG) to a forecast that already had the hand's history made it worse in **8 of 12** comparisons. At the wrist, a quarter of a second ahead, the error grew from 4.05° to 4.52°. EEG met none of the 4 pass rules set for it before any scoring.
- Adding a muscle recording from the forearm (EMG) lowered the error in **10 of 17**. Only at the wrist was the gain clear of the spread between people.
- On the task it was fitted for, a forecast fitted to the hand's recent past beat simply repeating the last value in **8 of 8** studies: 4.05° against 7.92° at the wrist.
- Change the task or the target, and a rule you could write in one line, such as "repeat the last value", beat the best fitted model in **6 of 6** settings.

NeuroTranslation is the larger attempt those studies belong to. Reach for a cup: your brain gives the order, the muscles of your forearm pull, and the hand moves. One act, written down three times, in nerve, in muscle and in motion. To translate is to take one of those records, predict another, and check the prediction against what the body did. It is one part of **Brain2Body**, the name of the whole programme and of its second paper, which asks what a person keeps once a machine stops guiding their hand.

The project includes the studies, [recordings and models you can open in a browser](https://eliminatenoise.github.io/NeuroTranslation/START.html), two draft papers and a sister game, NeuroSurge. What does not exist is a general model. **NeuroTranslate 0.0** is the name of the one being built. It has not been fitted to a real recording, and it is not inside the browser app that carries its name.

**Which recording do the words describe?** Given a volunteer’s description and 38 recordings, a small attention model ranked the matching clip first 5.6% of the time. A simpler word-count model reached 6.6%. You can also follow 41 body markers through a scoop, a jump and a hop in a separate set of recordings. [Language study](benchmarks/text-motion-retrieval/) · [Turn and replay the three movements](https://eliminatenoise.github.io/NeuroTranslation/whole-body/)

**Try a wrist forecast.** Three models predict where a recorded wrist will be a quarter-second later. Run them on your own computer and compare what changes when they receive electrical readings from the forearm and scalp. [Browser model and example](interfaces/paired-wrist-browser/) · [Recorded movement in the NeuroSurge game preview](https://github.com/eliminatenoise/NeuroSurge/pull/2) A separate experiment tested whether muscle recordings can correct the early part of a wrist forecast. [Six-person correction study](benchmarks/wrist-forearm-correction/)

## Where to click

- **[Start page](https://eliminatenoise.github.io/NeuroTranslation/START.html).** Runs in a browser, nothing to install. Try an invented example, or pick the kind of recording you have and open the page that reads it. Behind it are the study readers, and an app that lines up your own recordings on one clock.
- **[The studies](benchmarks/README.md).** The original comparison explains the counts above row by row. The newer wrist-correction and language studies link to their own methods and results.
- **[The papers](papers/README.md).** Two working drafts, each in a Technical and a Simple English edition.
- **[Launchers and offline copies](LAUNCHERS.md)** for Windows, macOS and Linux.
- **[NeuroSurge](https://github.com/eliminatenoise/NeuroSurge)**, the sister game.

## A translation needs both texts from the same moment

NeuroTranslate 0.0 is meant to be a *large movement model*: one model that learns how nerve, muscle and movement go together, from four kinds of data.

| Kind of data | What it is | What it is not |
| --- | --- | --- |
| **Neural recordings** | Electrical activity of the nervous system, at the places where the electrodes sat: brain, spinal cord or the nerves of the body. | A recording at one place is not a recording at another. EEG from the scalp says nothing direct about a nerve in the arm. |
| **Muscle recordings** | EMG: the electrical activity of muscle, picked up on the skin over it. | A recording of muscle, not of nerve. Not a force either: getting force out of EMG takes a second measurement or a mechanical model. |
| **Motion capture** | Where the body went: joint angles and hand positions, with their units and their clock. | The movement itself. It is a tracker's estimate, with the tracker's error. |
| **Physics-based simulation of the body** | Movement and force computed from a model of bones, joints and muscles. | Measured. A simulation is tested against a measurement of the same task, never the other way round. |

A fifth thing is needed, and it is not data. It is the pairing.

Suppose the motion recording belongs to a different reach. It can still teach a model what reaches look like. It cannot say where *this* hand was when *this* nerve fired. A translation can be checked only when both recordings come from the same person, the same movement and the same clock, and even two files that name the same clock can be offset from each other. Every study below uses signals that were recorded together.

The project's working presumption is that more data, and more varied data, makes a model that carries further. It is untested: no study here varies how much data a model sees, or how varied it is.

## How the original movement forecasts compared

Each row sets a reference forecast against a challenger that was given something extra. Some rows forecast a movement, some the force at a gauge, some the voltage of a force sensor.

Every score is an error: how far the forecasts fell from what was measured. Lower is better. Rows 1 to 13 are scored by the measure that punishes large misses, rows 14 to 23 by the plain average miss, and the last two by a squared error in units of their own. Row 20 is the odd one: it compares the width of bands, not errors. Units change from block to block, so compare along a row, never down a column.

A *straight-line fit* is the plainest kind of model, a weighted sum of its inputs. A *learned forecast* is a small network that reads a stretch of recent history. The recordings a model is scored on were never used to fit it, except in the last row.

| Study | Tested on | Reference forecast | Challenger | Who won |
| --- | --- | --- | --- | --- |
| **Wrist angle, a quarter of a second ahead** (degrees) | | | | |
| 1 · [Wrist pointing: brain signal on a learned forecast](benchmarks/wrist-pointing-temporal/) | 3 people | Learned forecast from wrist history: 4.05° | With scalp EEG added: 4.52° | **History.** EEG made the forecast 0.47° worse. |
| 2 · [Wrist pointing: muscle signal on a straight-line fit](benchmarks/wrist-pointing-muscle/) | the same 3 | Straight-line fit on wrist history: 6.53° | With forearm EMG added: 6.17° | **EMG**, by 0.36°. EMG taken from the wrong trial did worse than none: 6.94°. |
| 3 · [Wrist pointing: muscle signal on the learned forecast](benchmarks/wrist-forearm-transfer/) | the same 3 | Learned forecast, corrected from wrist motion: 3.96° | With EMG added: 3.85° | **EMG**, by 0.10°, for 3 of 3 people. |
| 4 · [Everyday tasks: wrist angle from the muscle signal](benchmarks/uji-wrist-emg/) | 4 people | Which activity it is and how long it has run: 36.2° | With EMG added: 34.7° | **EMG**, by 1.5°, for 3 of 4 people. Bending up and down got 2.4° better; tilting side to side got 0.7° worse. |
| **Elbow angle** (degrees) | | | | |
| 5 · [Hand to mouth: one person's muscle signal, another's elbow](benchmarks/surface-emg-elbow/) | 1 person | The average path, started when the movement starts: 30.8° | EMG alone, fitted on someone else: 62.4° | **The average path**, by 31.6°. |
| **Sideways position of the palm** (millimetres) | | | | |
| 6 · [Palm, first try: brain signal alone](benchmarks/scalp-eeg-hand/) | 1 person | The time within the task and nothing else: 7.38 mm | Scalp EEG alone: 7.51 mm | **The clock**, by 0.13 mm. |
| 7 · [Palm: brain signal on top of hand history](benchmarks/scalp-eeg-palm-history/) | 3 people | Time, and where the palm has been: 1.09 mm | With EEG added: 1.22 mm | **History.** EEG helped 0 of 3 people. |
| 8 · [Palm: adjusted on the person's first recording](benchmarks/scalp-eeg-personal-calibration/) | 3 new people | The model as fitted on other people: 1.85 mm | Adjusted on the person's own first recording: 1.70 mm | **The adjustment**, by 0.15 mm, for 3 of 3. EEG still added nothing. |
| **Grip force during a lift, 120 ms ahead** (newtons) | | | | |
| 9 · [Pinch and lift: grip force](benchmarks/way-grip-force/) | 3 people | Force and motion history: 0.444 N | With EEG added: 0.440 N | **Nobody.** EEG from a different lift did better still (0.439 N), so EEG failed the pass rule set for it. |
| 10 · [Pinch and lift: grip force, timed from the squeeze](benchmarks/way-contact-force/) | the same 3 | Force and motion history: 0.677 N | With EEG added: 0.695 N | **History.** EEG helped 0 of 3 people. |
| **Sensor voltage during a paced grip or a finger press, 120 ms ahead** (millivolts) | | | | |
| 11 · [Paced grip: brain signal](benchmarks/hygrip-force/results-2026-11-19/) | 3 people | Cue timing and recent voltage: 0.360 mV | With EEG added: 0.461 mV | **History.** EEG helped 0 of 3 people. |
| 12 · [Paced grip: muscle signal](benchmarks/hygrip-force/forearm-results/) | the same 3 | Cue timing and recent voltage: 0.360 mV | With EMG added: 0.345 mV | **Nobody.** Lower on average but for only 1 of 3 people, and EMG moved to the wrong moment did better still (0.343 mV). |
| 13 · [Paced grip: a fit that changes with the cue](benchmarks/hygrip-force/cue-phase/) | the same 3 | The plain fit: 0.360 mV | A fit allowed to differ between squeeze and rest: 0.374 mV | **The plain fit.** The other helped 0 of 3 people. |
| 14 · [One finger: muscle signal](benchmarks/hyser-index/RESULTS.md) | 4 people | The sensor's last 41 readings: 14.35 mV | With EMG added: 14.46 mV | **History**, by 0.10 mV. EMG helped 2 of 4 people. |
| 15 · [One finger: next-day adjustment](benchmarks/hyser-index/crossday/) | the same 4, on their second day | The shared model, unchanged: 14.91 mV | Adjusted on the person's own first day: 15.09 mV | **The unchanged model.** The adjustment helped 1 of 4. |
| 16 · [One finger: the other four fingers](benchmarks/hyser-index/whole-hand/) | the same 4 | Index-finger history: 14.35 mV | With the other four fingers added: 14.16 mV | **Split.** Lower on average in these 4 people, though for only 2 of 4; higher in the 12 the model was fitted on. |
| 17 · [One finger: new task](benchmarks/hyser-index/prescribed/) | the same 4, on a new task | Index-finger history: 7.99 mV | Five fingers: 7.80 mV | **Five fingers beat one**, for 4 of 4. Repeating the last value beat both (7.22 mV); on the measure that punishes large misses it lost to both. |
| **Pinch force between two fingers, 120 ms ahead** (% of the person's hardest squeeze that day) | | | | |
| 18 · [Pinch: muscle signal](benchmarks/cemhsey-pinch/) | 4 people | Force history and the on-screen cue: 0.4634% | With EMG added: 0.4632% | **No measurable difference.** |
| 19 · [Pinch: five electrode grids](benchmarks/cemhsey-arrays/) | 4 new people | EMG as one overall amplitude: 0.51663% | EMG as five separate grids: 0.51659% | **No measurable difference.** Better for 2 of 4 people, and the sign flipped between the two days. |
| 20 · [Pinch: width of the band](benchmarks/cemhsey-intervals/). A band is a range around a forecast, meant to hold 90% of the readings that follow. | 2 people | One band width for the whole pinch: 2.21% wide, holds 94.5% of later readings | A width for each part of the pinch: 2.16% wide, holds 95.1% | **The band set part by part**: narrower, and it holds more. Both fell short while the pinch was released (87.1% and 88.0%). |
| 21 · [Pinch at new targets](benchmarks/cemhsey-transfer/) | 4 people | A one-line rule, the current reading plus the change the on-screen schedule calls for: 0.572% | The fitted five-grid model after one practice pinch: 0.699% | **The one-line rule.** The model beat it for 0 of 4 people. |
| 22 · [Pinch, next day](benchmarks/cemhsey-carry/) | the same 4, a day later | The fitted model, corrected on one practice pinch from the new day: 0.70643% | Corrected on yesterday's practice pinch instead: 0.70578% | **No measurable difference.** The one-line rule beat both: 0.584%. |
| 23 · [Pinch: a correction learned from other people](benchmarks/cemhsey-phase/) | 3 people | The one-line rule: 0.70007% | With separate corrections for the rise and the release, learned from 3 other people: 0.69509% | **The correction**, by 0.005%, for 3 of 3. One correction for both directions did as well (0.69507%). The fitted model lost to both: 0.822%. |
| **Reported only in the papers** (units scaled to the data) | | | | |
| 24 · [Macaque fingers from motor cortex (LINK)](papers/current/neurotranslation-technical.pdf#page=13) | 1 macaque | Straight-line fit on the latest brain sample: 0.03150 | The better of two networks that read recent brain history: 0.02996 | **Both failed their pass rule.** Lower on average, but worse for the index finger on the second test day. All five further claims failed too. |
| 25 · [One network shared by two signals: first run](papers/current/research-evidence-reading-aid.md#one-acquisition-two-forecasting-tasks) | nobody held out | Repeat the last value: 0.0245 | One network shared by a muscle signal and a glove signal, after 990 training steps: 0.372 | **Repeating the last value**, on the network's own training recording. |

Two more counts. Adjusting a model to one person, one day or one group lowered the error in 5 of 6 comparisons, but in only 1 of them by more than 1% of the error. And 11 studies fixed a pass rule before any scoring: 7 failed it, 2 gave a split answer, 1 passed by a margin too small to tell from zero, and 1 passed on a question about band widths. No rule about adding a signal to a forecast was passed outright.

No test group is larger than 4 people, the 23 studies draw on 8 datasets, and several rows score the same three or four people again. The brain signal in every study on people is EEG from 3 to 32 electrodes on the scalp: nothing here was recorded inside a human brain. And nothing was forecast live: every "ahead" is a distance along a stored recording.

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

Both are working drafts, and nobody outside the project has reviewed them. They were last built on 19 November 2026 and do not yet contain studies 8, 10, 13 or 23. [How to read them, and where each study sits in each one](papers/README.md).

## Run it yourself

In a browser: open the [start page](https://eliminatenoise.github.io/NeuroTranslation/START.html). A recording you open is read on your own computer and goes nowhere.

Offline: most readers have a ZIP that runs without a network, with a launcher for Windows, macOS and Linux. [LAUNCHERS.md](LAUNCHERS.md) lists them.

To score a study again from the original recordings: each folder under [`benchmarks/`](benchmarks/README.md) holds the study's plan and its results file, and several also hold the code that does the scoring. You fetch the recordings yourself, from their own archive. The palm study, for example, with Python 3.13:

```
cd benchmarks/scalp-eeg-palm-history
python -m pip install -r requirements.txt
python fetch_inputs.py --output ../iackd-data
python -m unittest -v
python run.py --input ../iackd-data --output ../availability-run
```

To build the app from source: `cd demo`, then `npm test` and `npm run build`. [demo/README.md](demo/README.md) says what the app does with a file you give it.

## Whose recordings these are

None of the recordings is ours. Ten open datasets, measured by other people, carry everything on this page: eight behind the 23 studies, and two behind the two results reported only in the papers.

EEG-EMG-WristMotion · KIN-MUS UJI · the upper-limb dataset of Lucchetti and colleagues · IACKD · WAY-EEG-GAL · HYGRIP · Hyser · CEMHSEY GRASP · LINK · Reach&Grasp

Who made each one, its licence and the credit it is owed: [docs/RIGHTS.md](docs/RIGHTS.md). The licences are CC BY 4.0, CC0 1.0, ODC-By 1.0 and MIT. What is published here is fitted models and summary results derived from the recordings, not the recordings themselves.

What the project itself wrote, text and code, is dedicated to the public domain under [CC0 1.0](LICENSE). That covers none of the recordings, nor the fonts inside the PDFs.

## The other two projects

**[NeuroSurge](https://github.com/eliminatenoise/NeuroSurge)** is a game for learning which part of the brain moves which part of the body. Its numbers are made up by the rules of the game. They are not forecasts from the studies here.

**Interoceptomics (Interotomics for short)** is a proposed field that studies how the body senses its own interior and how the nerve connections involved are arranged. [Project and proposed experiments](https://github.com/eliminatenoise/Interoceptomics) Today it is a 3D atlas of the human brain that you can turn, cut and measure.
