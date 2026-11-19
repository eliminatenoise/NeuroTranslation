# Grip after contact

The force plates register a squeeze. How hard will the fingers be pressing in 120 milliseconds? In these recorded lifts, the hand and object already tell us quite a bit. Across 882 lifts from three people, a ridge regression using earlier force and motion averaged **0.676974 N** of error. Adding scalp EEG raised the average to **0.695471 N**. A temporal convolution also gave more error with aligned EEG than with mechanics alone. Both results come from the same previously explored development recordings.

## Run the forecasts

Put ridge and the temporal CNN side by side on the same past readings. Move the issue time, change the inputs, or reveal the recorded target when your capture supplies it. The browser opens with an invented squeeze and can read a compatible capture without uploading it. [Open the browser comparison](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) · [Download the offline comparison and launchers](NeuroTranslation-Grip-After-Contact-Comparison.zip) · [Rebuild from the fitted model ZIPs](browser-release/)

The command-line runners are also available.

| Download | What runs | Requirements |
| --- | --- | --- |
| [Grip after contact · ridge regression ZIP](NeuroTranslation-Grip-After-Contact-Experimental-Preview.zip) | Five fitted predictors and two force formulas. The runner can detect force confirmation in a compatible local capture. | Python 3.10+ and NumPy |
| [Grip after contact · temporal CNN ZIP](grip-contact-temporal-preview.zip) | Three fitted predictors. Give the runner a window prepared through the forecast time to compare timing, mechanics and aligned EEG. | Python 3.10+ |

Extract either ZIP. On Linux run `sh ./Run-Linux.sh` in the extracted folder. On macOS use `sh ./Run-macOS.command`. On Windows open `Run-Windows.cmd`. Each starts with invented readings and prints forecasts in newtons. Both packages ran on Linux. Their macOS and Windows launchers have had static checks.

To use recorded inputs, see the array layouts and units in each archive’s README. The ridge runner accepts a local NumPy file with a compatible capture and go-cue time. The temporal runner accepts a local JSON window aligned and cut by the caller. Both run offline. The examples exercise the shipped weights on invented inputs. The ridge runner can return forecasts outside physically plausible bounds. The errors below come from measured lifts. Control comparisons using a different or earlier EEG window are reported in the study results.

## When does the clock start?

The [earlier cue-grid study](../way-grip-force/) asked for predictions on a schedule tied to the go cue. A cue tells a person when to start. A force plate tells us when the squeeze reaches an observable level. Here the cue starts the search for a crossing, then the force signal sets the schedule.

On the 500 Hz recording clock, wait for a grip sample below 0.5 N after the LED cue. Count ten consecutive samples at or above 0.5 N after the crossing. A dip below 0.5 N breaks the run. Put time zero on the **tenth** sample, 18 ms after the first sample in the successful run. The rule can confirm the crossing at that point without backdating it. A trial already at or above the threshold at the first available post-cue sample has an unknown crossing and is treated as left-censored. This rule defines a recorded-force proxy. First anatomical touch and the source study’s digit-touch annotations describe separate events.

Make a forecast at **0, 100, 200, 300 and 400 ms** after confirmation. Each window takes the 200 sensor rows ending at the issue sample. Its first and last samples are 398 ms apart. The target is the measured mean normal force on the two fingertip plates, positive for compression, **60 samples (120 ms) later**. The ridge input uses the mean grip and summed load columns of the source windowed files, changing the grip sign to make compression positive. It retains the source scales for position and electrical signals. Stored trial segmentation, source preprocessing and synchronization precede the benchmark. The 120 ms describes time on the recording clock. Sensing, processing and display delays in a live setup remain unmeasured.

## What does EEG add?

The registered ridge study fits a penalty-regularized linear regression on engineered features from earlier grip, load and four position tracks. Its timing inputs are elapsed time since the cue and time since force confirmation. The EEG branch adds summaries of the 32 scalp channels from the same history. The CNN diagnostic instead feeds the time series through causal convolutions, which only see samples through issue. It averages the 200 rows into 50 consecutive four-sample bins. The timing-only branch sees trial timing. Both model families fixed their settings using six training people, with 1,763 confirmed lifts and 8,815 forecast windows for the common population. The development run applied the frozen fits without selecting or fitting a new model.

Changing when the scalp recording was made tests whether the correct pairing matters. The rotated control keeps the original mechanics and takes EEG from the next eligible lift in the same person, recording series, object mass and surface. The donor is evaluated at the same offset after its own confirmation. The lagged CNN control keeps the same lift and moves the EEG window 300 ms earlier. Its history still overlaps the aligned window by 100 ms. These controls preserve aspects of task phase and recording context. Movement and muscle activity can contribute to scalp EEG, and this comparison cannot establish the source of any effect.

| Forecast on matched development rows | Mean participant RMSE (N) |
| --- | ---: |
| Keep the current force | 1.717316 |
| Extend the backward 80 ms slope | 1.347735 |
| Ridge · force and motion | **0.676974** |
| Ridge · mechanics + aligned EEG | 0.695471 |
| Ridge · mechanics + rotated EEG | 0.691861 |
| CNN · timing only | 2.399912 |
| CNN · force and motion | **0.977953** |
| CNN · mechanics + aligned EEG | 0.993569 |
| CNN · mechanics + rotated EEG | 0.987271 |
| CNN · mechanics + lagged EEG | 0.983329 |

For each person, calculate the root mean squared error (RMSE) with equal weight per lift and per scored offset within that lift. Then average the three people’s RMSEs. The compared branches use the same **4,410 forecasts from 882 lifts**. The five windows from each lift are repeated observations from the same lift, so the person is the unit for the paired comparison.

| Paired comparison (first minus second) | Mean change (N) | Descriptive 95% paired t interval (N) | People with lower error on the first branch | Two-sided exact sign p |
| --- | ---: | ---: | ---: | ---: |
| Ridge · aligned EEG − mechanics | +0.018497 | [−0.003430, +0.040424] | 0 of 3 | 0.25 |
| Ridge · aligned EEG − rotated EEG | +0.003610 | [−0.022002, +0.029222] | 2 of 3 | 1.00 |
| CNN · aligned EEG − mechanics | +0.015616 | [−0.136012, +0.167244] | 1 of 3 | 1.00 |
| CNN · aligned EEG − rotated EEG | +0.006298 | [−0.045941, +0.058538] | 2 of 3 | 1.00 |
| CNN · aligned EEG − lagged EEG | +0.010239 | [−0.119302, +0.139781] | 1 of 3 | 1.00 |

The registered criterion required aligned EEG to beat both mechanics and rotated EEG on average. It lost both comparisons. Aligned EEG incurred higher error on average in the temporal diagnostic too. The best measured result here was the mechanical ridge. It used different input features and training choices from the CNN, so the gap does not isolate the effect of architecture. With just three previously explored healthy adults performing one pinch-lift task, the intervals leave room for effects in either direction. Different recordings, features and tasks can produce different results. The reserved final test cohort remained unopened.

The [aggregate results](RESULTS.json) give unrounded comparisons and data provenance. The archives include the input recipes, code, fitted parameters, training diagnostics and aggregate results. Their offline examples accept locally prepared inputs. The original recordings, participant-level results and final test set are outside this release. [SHA-256 checksums](SHA256SUMS)

A separate HYGRIP study asks what scalp EEG adds to a forecast during paced power grip against a hand-held transducer. [Read its prospective protocol](../hygrip-force/)

## Source recordings

Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin recorded healthy adults pinching and lifting an object while its weight and surface varied. They measured fingertip force, hand and object position, scalp potentials and surface muscle activity. The European Commission supported the original recordings through the WAY project (FP7-ICT-288551). The descriptor and data deposit document the original measurements, clocks and reuse terms. [Scientific Data descriptor](https://doi.org/10.1038/sdata.2014.47) · [WAY-EEG-GAL Figshare collection, version 2](https://doi.org/10.6084/m9.figshare.988376)
