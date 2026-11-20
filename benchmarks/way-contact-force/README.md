[The studies](../README.md) › Study 10 · Pinch and lift: grip force, timed from the squeeze

# Timed from the squeeze, EEG made the grip forecast worse for all three people

The plates register a squeeze: how hard will the fingers be pressing 120 ms later? For the three test people of [study 9](../way-grip-force/), across 882 lifts, a straight-line fit on the earlier force and motion missed by **0.6770 N**. Given scalp EEG as well, it missed by **0.6955 N**: 0.0185 N worse, and worse for each of the three. A learned forecast also did worse with EEG than without it. The pass rule set before scoring asked EEG to beat both the fit without it and EEG from another lift; it beat neither.

Every score here is the measure that punishes large misses (root mean squared error), worked out for each person and averaged over the three. EEG is electrical activity of the brain, picked up on the scalp. A *straight-line fit* is a weighted sum of its inputs, with a penalty that keeps the weights small; a *learned forecast* is a small network that reads a stretch of recent history.

| Forecast (every row scored on the same 4,410 forecasts) | Error, averaged over the three people (N) |
| --- | ---: |
| Repeat the last force | 1.717316 |
| Carry the last 80 ms of change forward | 1.347735 |
| Straight-line fit · force and motion | **0.676974** |
| Straight-line fit · force, motion and EEG timed with the lift | 0.695471 |
| Straight-line fit · force, motion and EEG from another lift | 0.691861 |
| Learned forecast · timing only | 2.399912 |
| Learned forecast · force and motion | **0.977953** |
| Learned forecast · force, motion and EEG timed with the lift | 0.993569 |
| Learned forecast · force, motion and EEG from another lift | 0.987271 |
| Learned forecast · force, motion and EEG from 300 ms earlier | 0.983329 |

For each person the error counts every lift equally, and every scored moment equally within a lift; then the three people's errors are averaged. Every row uses the same 4,410 forecasts from 882 lifts. The five forecasts from each lift are repeated looks at the same lift, so the person is the unit for the paired comparisons below.

| Paired comparison (first minus second) | Average change (N) | 95% range of the change across the three people (N) | People with lower error on the first |
| --- | ---: | ---: | ---: |
| Straight-line fit · EEG timed with the lift − no EEG | +0.018497 | [−0.003430, +0.040424] | 0 of 3 |
| Straight-line fit · EEG timed with the lift − EEG from another lift | +0.003610 | [−0.022002, +0.029222] | 2 of 3 |
| Learned forecast · EEG timed with the lift − no EEG | +0.015616 | [−0.136012, +0.167244] | 1 of 3 |
| Learned forecast · EEG timed with the lift − EEG from another lift | +0.006298 | [−0.045941, +0.058538] | 2 of 3 |
| Learned forecast · EEG timed with the lift − EEG from 300 ms earlier | +0.010239 | [−0.119302, +0.139781] | 1 of 3 |

With three people, even three out of three going the same way would happen by chance one time in four (the 0.25 in the results file), so no row here rules out chance. The ranges are worked out from the three people's changes alone: they show how much these three varied, not what anyone else would see. The best result here was the straight-line fit on force and motion. It used different inputs and fitting choices from the learned forecast, so the gap between the two says nothing about which kind of model is better. [Results file, unrounded, with where the data came from](RESULTS.json)

## Time zero is the tenth force sample at or above 0.5 N

[Study 9](../way-grip-force/) forecast on a schedule tied to the go cue. A cue tells a person when to start; a force plate tells us when the squeeze reaches a level that can be seen. Here the cue starts the search for that moment, and the force sets the schedule.

On the 500 Hz recording clock, wait after the LED cue for a grip sample below 0.5 N. Then count ten samples in a row at or above 0.5 N; a dip below 0.5 N breaks the run. Time zero is the **tenth** sample, 18 ms after the first sample of the run, so the rule confirms the crossing when it happens instead of dating it back. A trial already at or above the threshold at the first sample after the cue has a crossing that cannot be known, and is left out. The rule marks a moment in the recorded force; the first touch of the skin and the source study's own touch annotations are different events.

Forecasts are made at **0, 100, 200, 300 and 400 ms** after that moment. Each window takes the 200 sensor rows ending at the moment of the forecast, 398 ms from first to last sample. The target is the measured force pressing straight into the two fingertip plates, averaged over the two plates, compression positive, **60 samples (120 ms) later**. The straight-line fit uses the average grip and the summed load columns of the source's windowed files, with the grip's sign turned so that compression is positive, and keeps the source's scales for position and the electrical signals. The trial cutting, processing and synchronising of the source all come before this study. The 120 ms is time on the recording clock; the sensing, processing and display delays of a live system were never measured.

## What EEG was given, and what it was tested against

The straight-line fit uses features of the earlier grip, load and four position tracks, with a penalty that keeps its weights small. Its timing inputs are the time since the cue and the time since the squeeze was confirmed. The EEG version adds summaries of the 32 scalp channels over the same history. The learned forecast instead reads the series in order, seeing only samples up to the moment of the forecast, after averaging the 200 rows into 50 bins of four samples; its timing-only version sees the trial's timing. Both kinds of model had their settings fixed on six fitting people, with 1,763 confirmed lifts and 8,815 forecast windows for the common group. The test applied those fixed fits; nothing new was chosen or fitted.

Moving the scalp recording in time tests whether the right pairing matters. The other-lift control keeps the original force and motion and takes EEG from the next usable lift of the same person, recording series, object weight and surface, scored at the same time after that lift's own squeeze. The 300 ms control keeps the same lift and moves the EEG window 300 ms earlier; its history still overlaps the timed window by 100 ms. These controls keep parts of the task's stage and the recording's context. Movement and muscle activity can reach scalp EEG, and this comparison cannot say where any effect comes from.

## What it does not show

Three healthy adults, already scored in study 9, doing one pinch-lift task; the ranges leave room for effects either way. Three more people were set aside when the people were split, and their recordings have not been opened. The original recordings, the results of single people and the set-aside group are not published here.

## Run the forecasts

Put the straight-line fit and the learned forecast side by side on the same past readings. Move the moment of the forecast, change the inputs, or reveal the recorded target when your recording has it. The page opens on an invented squeeze and reads a compatible recording on your computer without sending it anywhere. [Open the browser comparison](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) · [Download the offline comparison and launchers](NeuroTranslation-Grip-After-Contact-Comparison.zip) · [Rebuild it from the fitted model ZIPs](browser-release/) · [SHA-256 checksums](SHA256SUMS)

The command-line runners are here too.

| Download | What runs | Needs |
| --- | --- | --- |
| [Grip after contact · straight-line fit ZIP](NeuroTranslation-Grip-After-Contact-Experimental-Preview.zip) | Five fitted forecasts and two force formulas. The runner can find the confirmed squeeze in a compatible recording of your own. | Python 3.10+ and NumPy |
| [Grip after contact · learned forecast ZIP](grip-contact-temporal-preview.zip) | Three fitted forecasts. Give the runner a window prepared up to the moment of the forecast to compare timing, force and motion, and timed EEG. | Python 3.10+ |

Extract either ZIP. On Linux run `sh ./Run-Linux.sh` in the extracted folder; on macOS use `sh ./Run-macOS.command`; on Windows open `Run-Windows.cmd`. Each starts with invented readings and prints forecasts in newtons. Both packages ran on Linux; their macOS and Windows launchers have been checked by reading, not by running.

To use recorded inputs, see the array layouts and units in each archive's README. The straight-line runner takes a local NumPy file with a compatible recording and its go-cue time; the learned-forecast runner takes a JSON window that you align and cut yourself. Both run offline. The examples run the shipped weights on invented inputs, and the straight-line runner can return forecasts outside what is physically possible. The errors above come from measured lifts. The archives hold the input recipes, code, fitted weights, fitting checks and summary results.

The same question in a different grip task, where EEG raised the error too: [Study 11 · Paced grip: brain signal](../hygrip-force/results-2026-11-19/).

## Whose recordings

Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin recorded healthy adults pinching and lifting an object while its weight and surface varied. They measured fingertip force, hand and object position, scalp potentials and surface muscle activity. The European Commission supported the original recordings through the WAY project (FP7-ICT-288551). The descriptor and the data deposit document the original measurements, clocks and terms of reuse. [Scientific Data descriptor](https://doi.org/10.1038/sdata.2014.47) · [WAY-EEG-GAL Figshare collection, version 2](https://doi.org/10.6084/m9.figshare.988376)
