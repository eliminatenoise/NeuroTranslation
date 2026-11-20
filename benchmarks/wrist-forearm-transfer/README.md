[The studies](../README.md) › Study 3 · Wrist pointing: muscle signal on the learned forecast

# Forearm EMG still took 0.104° off a forecast that knew the wrist's path

The learned forecast of [study 1](../wrist-pointing-temporal/) already knows the wrist's recent path and the time since the cue. Here it was kept fixed and a correction was fitted on top of it. Corrected from wrist motion alone, the forecast of both wrist angles 250 ms ahead missed by **3.957°**. Given four pairs of forearm EMG signals as well, it missed by **3.853°**: 0.104° better, for each of the three test people. EMG from the next trial pushed it up to 4.140°.

Every score here is the measure that punishes large misses (root mean squared error), over both wrist axes, with each person counting equally. EMG is electrical activity of muscle, picked up on the skin: a recording of muscle, not of nerve. A *learned forecast* is a small network that reads a stretch of recent history; three were trained, and their forecasts averaged.

![Change from the motion-only correction. The paired forearm signal reduced two-axis error by 0.104 degrees. Moving the forearm signal to the next trial increased it by 0.183 degrees.](wrist-forearm-correction.png)

| Forecast | Both axes | Bending up and down | Tilting side to side |
| --- | ---: | ---: | ---: |
| The three learned forecasts, unchanged | 4.053° | 5.098° | 2.622° |
| Corrected from wrist motion | 3.957° | 4.947° | 2.615° |
| Corrected from wrist motion and EMG of the same trial | 3.853° | 4.806° | 2.568° |
| The same, with EMG of the next trial | 4.140° | 5.225° | 2.642° |

The correction is a new output layer that reads the network's internal activity, the last two measured angles and the time since the cue. The last row keeps its fitted weights, the earlier wrist angles and the target time; only the forearm signal changes, taken from the next pointing trial of the same person and block at the same time after the cue. That shift raised the error by 0.287° against correctly paired EMG. Electrodes on the skin also pick up nearby muscles, movement and changes in contact; the shift shows that the gain needs the EMG recorded with this movement, in this task.

Six people supplied 1,879 training trials. The corrections were fitted and fixed before this comparison was scored. The three test people supplied 960 trials and 5,760 pairs of angles; both axes improved for each of them. Whichever one of the three is left out, the gain stays between 0.072° and 0.125°.

## What it does not show

The three test people were scored twice before, in studies 1 and 2. Six more people were set aside when the dataset was split and have not been scored. The source reports that the encoders update at 100 Hz, so 250 ms on the 512 Hz recording clock leaves the real delay of the device unknown: this is a forecast along a stored recording.

## The plan

The plan, `DESIGN.json` inside the [model ZIP](WristMotion-Forearm-Correction.zip), fixed the comparison before scoring and says: "Do not substitute this experiment for independent confirmation." It set no pass threshold. The results file calls the study an exploratory reuse of three people already scored, with no estimate from the set-aside group.

## Run it yourself

[Open the forearm forecast in your browser](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) or [download the offline page and launchers](WristMotion-Forearm-Browser.zip). Choose an invented example to see the three forecasts, or open an unmodified ZIP from [the deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) and pick its block and trial. For a real recording, **Forecast error** shows the predicted angle minus the measured angle at each target time. Files are read on your computer, in a background worker.

- [Download the recorded-trial runner](WristMotion-Forearm-Recorded-Trial.zip). Extract the whole folder and follow its README to forecast one movement from an original ZIP. Each printed row sets the measured angle beside the unchanged forecast and the two corrections.
- [Download the fitted models and invented examples](WristMotion-Forearm-Correction.zip). The twelve invented windows run with Python's standard library. The archive also holds both learned correction matrices, the three unchanged wrist models, the fitting code and the study's plan.
- [Read the results file](DEVELOPMENT-AGGREGATE.json) or [draw the figure again](plot_wrist_transfer.py). The [wrist replay](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) runs study 1's forecasts in your browser.

The browser model and archive checker can be rebuilt from the two published ZIPs with Python's standard library. From this folder, run `python browser-source/build_browser.py rebuilt` and compare the hashes it prints with [the recorded source and file hashes](SOURCE.json). The study's software reads the original ZIP on your computer, checks its fingerprint, then reads the block and trial you chose. The recording itself is never part of the browser download.

## Whose recordings

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz deposited the *EEG-EMG-WristMotion Dataset*, version 3, under CC BY 4.0. NeuroTranslation worked out the earlier wrist and forearm features, fitted the corrections and drew the figure from the summary errors. [Dataset](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Study descriptor](https://doi.org/10.1038/s41597-026-07287-z) · [Licence](https://creativecommons.org/licenses/by/4.0/)

[Study 4 · Everyday tasks: wrist angle from the muscle signal](../uji-wrist-emg/) asks a related question in other people: later wrist angles from a glove, estimated from the task, the time and seven forearm signals, in the KIN-MUS UJI dataset recorded in Spain. Its inputs and task differ from the pointing study here.
