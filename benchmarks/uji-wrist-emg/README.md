[The studies](../README.md) › Study 4 · Everyday tasks: wrist angle from the muscle signal

# Forearm EMG cut the wrist-angle error for three of four people in everyday tasks

Knowing what someone is doing already says a good deal about their wrist. A model fitted on 14 people was told only which of 26 everyday activities four other people were doing and how long the movement had run, and it forecast their wrist angles with an error of **36.187°**. Given half a second of earlier activity from seven forearm electrodes as well, it missed by **34.718°**: 1.468° better, and better for three of the four people. The gain came from one axis. Bending up and down got 2.421° better; tilting towards the thumb or the little finger got 0.700° worse.

Every score here is the measure that punishes large misses (root mean squared error), over both wrist axes, with each person counting equally. The forearm signal is surface EMG, the electrical activity of muscle picked up on the skin: a recording of muscle, not of nerve.

![Compared with task and elapsed time alone, adding aligned forearm EMG reduced overall error by 1.47 degrees and flexion–extension error by 2.42 degrees. Radial–ulnar error increased by 0.70 degrees. The interval for the overall change is broad with four people.](uji-forearm-effect.png)

| What the model is given | Both axes | Bending up and down | Tilting side to side |
| --- | ---: | ---: | ---: |
| The activity and the time it has run | 36.187° | 48.786° | 15.457° |
| The same, and EMG timed with the movement | 34.718° | 46.365° | 16.156° |
| The same fitted model, with the EMG moved in time | 35.385° | 46.979° | 17.240° |

In the last row each movement keeps its own muscle signal, but the half-second stretches of muscle signal are moved halfway round the trial. Even so they helped against activity and time alone; putting them back at the right moment took off another 0.667°. A mistimed stretch still says who is moving and what they are doing.

## What was measured

The KIN-MUS UJI dataset holds glove angles and surface EMG from 22 adults doing 26 activities of daily living. Fourteen people were used to fit the models. Four other people supplied all 104 test trials and 20,073 usable target times. Four more were set aside when the people were split, and their recordings have not been scored. The many target times are repeated measurements of four people, so the range for the overall change comes from resampling those four: from 0.016° to 2.936° better (the middle 95% of the resamples).

The muscle inputs end 250 ms before each target on the stored clock. The dataset's authors smoothed the glove angles forwards and backwards in time, so a "past" angle already carries information from later movement; earlier glove angles were therefore kept out of both models. What the models forecast is a later stored angle. The glove's real delay, and how accurately it measures these two wrist axes, are not known. [How the comparison was made](METHOD.md) gives the timing, the four fitting records rejected because their clocks ran backwards, and the activity missing from the source. [Dataset and rights](https://doi.org/10.5281/zenodo.3469380) · [Original study](https://doi.org/10.1038/s41597-019-0285-1)

## Keeping part of the muscle correction did not help the four test people

A later experiment learned, for each axis, how much of the EMG model's correction to keep, using only the 14 people the models were fitted on. Each of 14 rounds set one person aside; the other 13 gave forecasts for people the fit had not seen, so the person being scored never shaped either the models or the weight. Fitted on all 14, the weights came out at 0.73734 for bending up and down and 0.73757 for tilting side to side. A weight of zero gives the activity-and-time forecast; one gives the full EMG correction.

| Both axes, each person counting equally | Activity and time | Full EMG correction | Weighted mix |
| --- | ---: | ---: | ---: |
| The 14 fitting people, each scored by a fit without them | 21.106° | 20.538° | 20.468° |
| The four test people, with the released pair of models (below) | 36.165° | 34.700° | 34.971° |

Inside the fitting group the mix beat the full correction by 0.070°, with a range from 0.350° better to 0.143° worse when people are resampled. On the four test people (scored with the released pair, which gives 36.165° and 34.700° where the main comparison gives 36.187° and 34.718°) it was 0.271° worse than the full correction: side to side got 0.312° better, up and down 0.512° worse, and side to side was still 0.390° worse than with activity and time alone. The experiment was designed after the first result, on four people who had already been scored. The four set-aside people stayed unopened.

[Download the fitted mix and desktop launchers](UJI-Wrist-Axis-Blend-Preview.zip) · [Results inside the fitting group and on the test people](AXIS-BLEND-RESULTS.json)

## What it does not show

Four test people, scored after the fact on stored recordings, with no written plan or pass rule published for this study. The 22 people were split 14, 4 and 4 before any numbers were looked at, and the models were fixed before the four test people were scored ([methods](METHOD.md)).

## Run the released estimator

[Run the everyday-task models in the browser](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) or [download the offline page](UJI-Daily-Wrist-Browser.zip). It compares the forecast extension and radial deviation from the same input. With an invented example you can change the activity, the elapsed time or the muscle amplitude; a JSON window you supply uses its own task and clock. The numbers going into the model can be read bin by bin. [Download an invented JSON window](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/example-window.json)

To supply your own window, start from the example. Set `task_id` to the activity's UJI number (1–26) and `elapsed_anchor_s` to the time from the start of the stored segment to the end of the EMG window (at least 0.5 s). Keep the archive's own amplitude convention and set `amplitude_scale` to `kin-mus-uji-v1.0-native-amplitude`. Keep electrode spots 1–7 in their original order.

- For amplitude input, give `rms_bins`: 16 rows in time order, each of seven amplitudes of zero or more. Each row covers 31.25 ms.
- For raw input, replace `rms_bins` with `clock_ms_from_anchor` and `emg`. Use whole milliseconds rising from −499 to 0 and one row of seven amplitudes per time. Each 31.25 ms bin needs at least 25 samples, with no gap of more than 5 ms between samples.

[Download the fitted forearm model](UJI-Wrist-Supported-Forearm-Model.zip). Extract the ZIP and use the launcher for your system. The example feeds invented inputs to the real fitted models. To try your own file, use the same seven electrode channels, number convention, activity numbering and timing as the source; the README inside the ZIP gives the input format.

The download holds a separately specified pair of models. Each input it keeps had to be active in at least seven of the fitting people. That rule removed 22 time inputs that were active in the main study and kept all 112 EMG inputs. On the same four people the leaner pair gave nearly the same result: 36.165° for activity and time, and 34.700° with EMG. Against its own EMG moved in time, the released model gained 0.678° from correct timing, where the main comparison above gained 0.667°. Both are differences in the error over both axes, on the same four people.

[Download the study source and an invented example](UJI-Wrist-Study-Source.zip) · [Results file](DEVELOPMENT-AGGREGATE.json) · [Figure source](plot_forearm_effect.py)

The [browser build source](browser-source/) recreates the fitted JavaScript files with standard Python. From the study folder, run `python browser-source/build_engine.py UJI-Wrist-Supported-Forearm-Model.zip`. Extract `AXIS-BLEND.json` from the weighted-mix ZIP, then run `python browser-source/build_axis_blend.py /path/to/AXIS-BLEND.json`. Both builders check that their inputs are the published files before writing. The browser page serves the second output, `uji-axis-blend.js`, as `axis-blend.js`.

## Whose recordings

KIN-MUS UJI, version 1.0, is by Néstor J. Jarque-Bou, Margarita Vergara, Joaquín L. Sancho-Bru, Verónica Gracia-Ibáñez and Alba Roda-Sales, under CC BY 4.0. NeuroTranslation selected the two wrist axes, worked out the earlier muscle features and fitted the comparison models. [Versioned record](https://doi.org/10.5281/zenodo.3469380) · [Data descriptor](https://doi.org/10.1038/s41597-019-0285-1) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The [wrist-pointing studies](../wrist-forearm-transfer/) used other people, other electrodes and earlier wrist angles. This comparison was fitted separately.
