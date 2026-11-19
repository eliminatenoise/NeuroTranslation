# NeuroTranslation

Reach for a cup. A neural recording captures activity at the recording site. An electrode over a muscle picks up electrical activity as the arm moves. Calibrated cameras estimate where the hand went. NeuroTranslation asks how well one of these observations can predict another. The hand’s measured path gives us something to check the prediction against.

[Open Palm replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay). Choose **Import a trial** and **Compare estimates** to put a measured palm position beside the model's estimates. On a first recording (R1), compare hand history with and without EEG. On a second recording (R2), see how the estimates change after calibration on that person's R1. You can inspect and export each of the nine positions. [Prepare an R1 trial](benchmarks/scalp-eeg-palm-history/#replay-a-recorded-trial) · [Prepare an R2 trial](benchmarks/scalp-eeg-personal-calibration/#replay-a-second-recording)

The companion also inspects your own JSON or CSV locally. It can align streams when they declare the same organism, subject, recording and clock and their partitions are compatible. Choose **Load example**, then **Metadata checks**, to see how the invented example records those fields. The companion runs without installation. [Import and alignment guide](demo/README.md) · [Desktop launchers for Windows, macOS and Linux](https://eliminatenoise.github.io/NeuroTranslation/START.html)

## Predicting measured movement

### Wrist pointing

How far will the wrist turn in the next quarter second? In a separate pointing experiment, six people supplied the training recordings and three other people supplied 960 development trials. A temporal convolutional model using recent wrist angles and cue timing had a two-axis error of **4.053°**. Repeating the last measured angle gave **7.925°**. Adding eight scalp EEG channels to the temporal model raised error to **4.523°**. These are root mean squared errors on a 250 ms horizon in the stored recordings. [Model, results and runnable preview](benchmarks/wrist-pointing-temporal/)

You can now replay any of the 960 development trials with the same six fitted temporal models. Compare the measured and forecast wrist angles at six times after the cue, or explore the published errors by axis without a file. [Open the recorded wrist replay](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) · [Prepare a trial from the original deposit](benchmarks/wrist-pointing-temporal/#replay-a-recorded-trial)

Surface muscle signals gave a different result in a linear model on the same trials. Adding four forearm EMG pairs to wrist history reduced error from **6.530° to 6.174°**. Adding EEG after EMG gave **6.127°** across both axes, with a small increase in error on the radial–ulnar axis. Both studies preserve a separate test cohort. [Run the fitted wrist models in your browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-pointing/) · [Muscle comparison and controls](benchmarks/wrist-pointing-muscle/)

We also tested the forearm signal against the stronger temporal motion model. Once the motion features were used to correct its forecast, error was **3.957°**. The same correction with paired forearm EMG scored **3.853°**. Substituting EMG from the next trial gave **4.140°**. This exploratory comparison reused the three development participants. [Open a recording directly in the browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) · [Study and desktop runner](benchmarks/wrist-forearm-transfer/)

### Everyday wrist movements

A distinct Spanish study asked what seven forearm electrodes add once a model knows the activity and time within it. On four new development participants, earlier muscle activity lowered two-axis error from **36.187° to 34.718°**. Error fell for flexion and extension but rose for radial and ulnar deviation. The glove targets were filtered in both time directions, so neither model received earlier glove angles. These are separately fitted models on daily activities. [Try the daily-activity estimator](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) · [Study, figure and downloadable estimators](benchmarks/uji-wrist-emg/)

### Grip force during a lift

How hard will the thumb and forefinger squeeze 120 ms from now? In stored WAY-EEG-GAL recordings from three development participants, force and motion history gave **0.44418 N** mean participant RMSE. Aligned scalp EEG lowered it to **0.44018 N**, but EEG from a phase-matched trial scored **0.43880 N**. Aligned EEG also slightly increased error when the measured target exceeded 0.5 N. [Grip-force study, controls and desktop forecast](benchmarks/way-grip-force/)

Move the cutoff on an invented grip and see what four fitted models predict from the samples they receive. Bring a compatible recorded window to run the same comparison locally. [Open the browser forecast](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) · [Download the offline browser and launchers](benchmarks/way-grip-force/WAY-EEG-GAL-grip-force-browser.zip)

What changes if we start the clock when the plates confirm a squeeze? On 882 lifts from the same three previously explored development participants, force and motion alone scored **0.676974 N** in the contact-triggered ridge forecast. Adding aligned EEG raised error to **0.695471 N**. The temporal model also had higher average error with aligned EEG. The European Commission supported the original recordings through WAY (FP7-ICT-288551). [Contact-triggered study and both desktop forecasts](benchmarks/way-contact-force/) · [Original study acknowledgments](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/#ack1)

Compare the ridge and temporal CNN forecasts at all five issue times. Start with an invented squeeze or open a compatible local JSON capture, then reveal the target row when the capture contains it. [Compare forecasts in your browser](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) · [Download the offline browser and launchers](benchmarks/way-contact-force/NeuroTranslation-Grip-After-Contact-Comparison.zip)

A separate HYGRIP experiment asks the same EEG question during visually paced power grip. The protocol and source checks were recorded before development scoring. [Read the HYGRIP protocol](benchmarks/hygrip-force/)

In the first three-person HYGRIP development check, force history and timing averaged **0.360083 mV** of error. Adding aligned scalp EEG raised it to **0.461331 mV**. The models were frozen before this check. [Read the first HYGRIP results](benchmarks/hygrip-force/results-2026-11-19/) · [Replay a grip trial](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) · [What changed when the model saw forearm EMG](benchmarks/hygrip-force/forearm-results/)

### Palm and elbow measurements

How much do three scalp EEG channels add once you know where the hand was? In the palm replay study, both fits had elapsed time and earlier palm position and velocity. One fit also had EEG. We trained on three people and evaluated on three others. Across 173 development trials, the person-weighted root mean squared error rose from 1.093 to 1.223 mm when EEG was added, and it rose for each development participant. The latest inputs preceded the target by 100 ms on the stored clock. The recordings were processed after collection, so live decoding latency remains untested.

The first analysis started its clock at the task cue and found no eligible trials because required palm observations were missing. The replay follows the alternate analysis, which starts at the first available palm sample at or after that cue. [Six-person study, fitted parameters and reproduction](benchmarks/scalp-eeg-palm-history/)

Can the palm model learn one person's movements from one recording and carry that improvement to another? We calibrated on one right-hand recording for each of three new participants and evaluated on a second recording from each. With scalp EEG and hand history, the equal-person error fell from 1.849 to 1.700 mm. With hand history alone, it fell from 1.839 to 1.691 mm. Personal calibration helped all three participants. Adding EEG to the calibrated model slightly increased error for each one. [Explore the participant results](https://eliminatenoise.github.io/NeuroTranslation/index.html#personal-calibration) · [Study and controls](benchmarks/scalp-eeg-personal-calibration/) · [Download the runnable study](benchmarks/scalp-eeg-personal-calibration/neurotranslation-cross-run-calibration-preview.zip)

In a hand-to-mouth task, did muscle activity predict elbow angle better than knowing when the movement began? A ridge regression trained on one participant had 62.4° root mean squared error on a second participant. A trajectory based on movement onset had 30.8°. Each participant contributed five repetitions, and their dominant arms differed. The benchmark includes the code, data sources and errors for each repetition. [Read and reproduce the experiment](benchmarks/surface-emg-elbow/README.md)

In the earlier IACKD palm pilot, a ridge model using three EEG channels had 7.51 mm root mean squared error on 59 development trials. A template using only time within the trial had 7.38 mm. The pilot used stored recordings from one participant for training and another for development. [Read and reproduce the two-person pilot](benchmarks/scalp-eeg-hand/README.md)

Hyser shifts the question to one finger. On a separate two-day task, recent sensor voltage gave 14.35 mV mean absolute error across four development participants. Adding aligned forearm activity gave 14.46 mV. [Open the index-finger reader](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) · [Read the comparison](benchmarks/hyser-index/RESULTS.md) · [Compare Day 1 calibration on Day 2](benchmarks/hyser-index/crossday/README.md) · [Does adding the other four fingers help?](benchmarks/hyser-index/whole-hand/README.md) · [Test the same models on prescribed presses](benchmarks/hyser-index/prescribed/README.md). To try a personal correction in the reader, choose **Personalize across two days**.

The CEMHSEY pinch reader compares recent force, cue phase and compact forearm EMG features in a separate acquisition. Its target is the normalized force between two fingers. The public reader opens with an invented model and can also load locally fitted weights and original trial packets. [Open the reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) · [Read the held-out comparison](benchmarks/cemhsey-pinch/README.md) · [Download for Windows, macOS or Linux](benchmarks/cemhsey-pinch/downloads/CEMHSEY-Pinch-Reader.zip).

On four new participants, five recorded electrode grids beat five interleaved groups on both recording days. Their mean advantage over overall EMG amplitude was only 0.00000042 of maximum voluntary contraction and reversed sign by day. Channel-rank persistence failed its declared comparison. [Measured five-grid results](benchmarks/cemhsey-arrays/README.md)

[The five-grid pinch protocol](benchmarks/cemhsey-arrays/PROTOCOL.md) compares documented electrode groups with interleaved channels from the same recordings. Explore the two measurement windows electrode by electrode in the array reader, or open a compatible recording on your own computer. [Open the reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) · [Download the offline tools](benchmarks/cemhsey-arrays/downloads/CEMHSEY-Array-Reader.zip)

Fixed-width bands around the five-grid forecast covered 94.5% of later readings on two new people. Changing width by cue phase covered 95.1%. [Compare the measured bands](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/) · [Methods and full results](benchmarks/cemhsey-intervals/README.md)

## Read the papers

A hand can close by the same amount and squeeze harder. The four papers follow that distinction from wrist angle to a lifted object, a paced grip and a single finger pressing on a sensor. A personal adjustment fitted on the first day raised average absolute error on the second day. When the task changed from freely chosen to prescribed presses, five fingers gave a better forecast than the index alone, but repeating the latest index reading had the smallest average absolute miss. The five-history forecast gave the lowest root mean squared error in both cohorts. In a separate two-finger pinch recording, four forearm EMG features lowered mean absolute error by about 0.052% over force and cue phase. The four-person descriptive range included zero. The five-grid profile lowered mean absolute error against all four refitted controls on the new CEMHSEY pinch panel. It beat overall amplitude alone by 0.0081%, with opposite signs on the two indexed days and higher root mean squared error. Adding channel rank persistence fell short of its three-control criterion. The forecast asks for one dynamometer reading 120 ms later on the nominal released force record. Giving each cue phase its own force band made all three forecasts' bands narrower on average, with more gauge readings inside and lower interval scores. The check used eight trials from two other people. All six bands covered more than 90% of readings overall and fell below 90% during release. [Read the four paper editions](https://eliminatenoise.github.io/NeuroTranslation/papers/current/) · [Download the PDFs and reading aid](papers/downloads/NeuroTranslation-Brain2Body-CEMHSEY-Pinch-Intervals-2026-11-19.zip) · [Download the selected manuscript sources](papers/downloads/NeuroTranslation-Brain2Body-Selected-CEMHSEY-Pinch-Intervals-Source-2026-11-19.zip)

The previously selected scientific-layout edition is listed below.

| Paper | Technical edition | Plain-English edition |
| --- | --- | --- |
| *NeuroTranslation: A New Paradigm In Brain-Body Mapping.* | [NeuroTranslation technical edition](papers/experimental/scientific-layout-2026-11-15/neurotranslation-technical.pdf) | [Read NeuroTranslation explained](papers/experimental/scientific-layout-2026-11-15/neurotranslation-explained.pdf) |
| *Brain2Body: The Next Generation In Body-Brain Interfacing.* | [Brain2Body technical edition](papers/experimental/scientific-layout-2026-11-15/brain2body-article.pdf) | [Read Brain2Body explained](papers/experimental/scientific-layout-2026-11-15/brain2body-simple-english.pdf) |

Both editions develop the methods and their limits. The plain-English editions give more space to the steps between them. [Download all four papers with their companions](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/papers/downloads/NeuroTranslation-Brain2Body-Paper-Previews-2026-11-15.zip), or use the [reading aid](papers/experimental/scientific-layout-2026-11-15/research-evidence-reading-aid.md) to trace the studies behind the argument. Extract the ZIP with its folder structure intact so links between files work.

These are experimental drafts. The recorded visual reviews cover selected issues on 26 of 546 pages. The [paper index](papers/) identifies the selected builds, the 520 pages outside that review and the historical source editions.

## What goes into a translation?

**NeuroTranslate 0.0** is the model under development. Its longer-term aim is a **Large Movement Model** connecting neural observations with muscle activity, body mechanics and measured movement. Recording site and task matter. A model trained on cortical activity during a reach has yet to earn a claim about spinal, peripheral, autonomic or visceral signals in another task.

| Source | What it contributes to the reach |
| --- | --- |
| Neural recordings | Activity from the brain, spinal cord or peripheral nerves, at the sites actually recorded. Autonomic and visceral pathways enter the analysis where relevant recordings exist. |
| Muscle recordings | Electromyography (EMG) measures electrical activity in named muscles. A direct nerve recording measures activity at a different site. Estimating force from EMG requires additional measurements or a mechanical model. |
| Displacement recordings | A tracker estimates hand position or joint angle. The coordinate frame, calibration, units and timestamps give those numbers meaning. |
| Mechanics data | Instruments can measure force. A physics simulation can generate a force estimate under stated assumptions. An independent force measurement from the same task, in the same units, gives that estimate a test. |

Suppose the motion trace belongs to a different reach. It might help a model learn common movement patterns. It cannot tell us where *this* hand was when *this* neural sample was recorded. A supervised prediction needs evidence linking the subject, event and time across the recordings. Even two files with the same clock label can carry an offset.

## What has been tested?

The public companion imports, plots and aligns samples. Its invented example exercises those tools. Palm replay instead runs the fitted regressions for the specified IACKD study on an imported trial. The published development result and the error for the imported trial have different denominators.

The separate general learner passed 29 synthetic software checks across its four input families. Those checks exercised timing and mask handling, training-only normalization and the transition between pretraining, training and fine-tuning. All three recorded parameter updates used mock data. The study regressions have a narrow input and task contract. A validated general-model download and a GUI for that model are still pending.

For a biological result, specify which inputs were available at prediction time, the organism, task, target and units. Keep evaluation subjects or sessions outside training and model selection. A hand tends to keep moving in its current direction, so a predictor can obtain a low error using only recent motion. Compare against that baseline and test what changes when the neural input is withheld.

The papers retain a negative result from a separate forecasting comparison. Across 18 fits and 720 saved epochs, neither model-admission rule passed and none of the five benefit claims held. Reconstructing recorded features leaves sensory delivery and skill transfer as separate experimental questions. [Read the forecasting results](papers/experimental/scientific-layout-2026-11-15/research-evidence-reading-aid.md)

## Code, related projects and reuse

- [Portable interface source](interfaces/experimental/portable/) contains the Python and HTML proposal for a recording-specific interface. The package contains no weights.
- [Historical R11 manuscript source](papers/experimental/r11-source/) preserves an unbuilt snapshot. Its external figures and fonts are incomplete, its proposed terminology was never adopted, and the selected PDFs have separate build provenance. [R9 metadata erratum](papers/errata/r9-reading-aid-metadata.txt)
- [Interoceptomics](https://github.com/eliminatenoise/Interoceptomics) explores internal-body sensing and neural connectivity through anatomical models. [NeuroSurge](https://github.com/eliminatenoise/NeuroSurge) uses a virtual cortex and limb to explore left-hand and arm control in a first-person game. [Shared terminology and project scope](PROJECT-CONTEXT.json)

Original project contributions are dedicated to the public domain under [CC0 1.0](LICENSE) to the extent the project holds the rights. Fonts, cited works and incorporated figures may carry separate terms. [Paper and font notices](papers/experimental/scientific-layout-2026-11-15/NOTICE.md)
