# Can forearm activity help estimate the wrist angle during everyday tasks?

Knowing what someone is doing already tells us something about their wrist. To test what the muscles add, we gave a model the activity label and the time since the recorded movement began. We then gave a second model the same information plus half a second of earlier electrical activity from seven forearm electrodes.

The first model had a two-axis root mean square error (RMSE) of **36.187°**. Adding the muscle signals brought it to **34.718°**. The change depended on the direction of movement. Error fell **2.421°** for flexion and extension, but rose **0.700°** for movement towards the thumb or little finger. Three of the four development participants had a lower two-axis error with EMG.

![Compared with task and elapsed time alone, adding aligned forearm EMG reduced overall error by 1.47 degrees and flexion–extension error by 2.42 degrees. Radial–ulnar error increased by 0.70 degrees. The interval for the overall change is broad with four people.](uji-forearm-effect.png)

| Inputs to the model | Both axes | Flexion / extension | Radial / ulnar |
| --- | ---: | ---: | ---: |
| Activity and elapsed time | 36.187° | 48.786° | 15.457° |
| Activity, time and aligned EMG | 34.718° | 46.365° | 16.156° |
| Same fitted model with time-shifted EMG | 35.385° | 46.979° | 17.240° |

In the last row, each movement kept its muscle signal, but the feature windows were shifted halfway around that trial. The shifted signal still helped relative to activity and time alone. Restoring its original timing lowered two-axis error by another **0.667°**. Even a mistimed window can carry information about who is moving and what they are doing.

## What was measured

The KIN-MUS UJI dataset contains glove angles and surface EMG from 22 adults performing 26 daily activities. Fourteen people contributed training data. Four different people supplied all 104 development trials and 20,073 usable target times. Four people remain reserved. The many time points describe repeated measurements within four development participants. Resampling those four gave an exploratory interval of **−2.936° to −0.016°** for the overall difference.

The muscle inputs ended 250 ms before each target on the stored clock. The authors filtered the glove angles forwards and backwards, so we kept earlier glove angles out of both models. What the models estimate here is a later *stored angle*. The sensor’s physical delay and wrist-specific measurement error remain open. The [methods](METHOD.md) explain the timing, the four rejected backwards training records, and the original missing activity. [Dataset and rights](https://doi.org/10.5281/zenodo.3469380) · [Original study](https://doi.org/10.1038/s41597-019-0285-1)

## How much of the muscle adjustment should the model keep?

A later experiment learned a weight for each axis using only the 14 training people. Each outer fold set one person aside. The thirteen remaining people supplied inner held-person estimates, so the person being scored could not influence either the models or the weight. With all 14 training people, the final weights were 0.73734 for flexion–extension and 0.73757 for radial–ulnar deviation. A weight of zero gives the task-and-time estimate; one gives the estimate that uses the full EMG correction.

| Participant-balanced two-axis RMSE | Task and time | Full EMG adjustment | Weighted combination |
| --- | ---: | ---: | ---: |
| Nested participant checks within training | 21.106° | 20.538° | 20.468° |
| Previously evaluated development participants | 36.165° | 34.700° | 34.971° |

Within training, the weighted combination lowered two-axis error by 0.070° relative to the full EMG adjustment. The participant bootstrap interval for the difference ran from −0.350° to 0.143°. On the four development participants, the weighted combination raised two-axis error by 0.271° compared with the full EMG adjustment. Radial error fell by 0.312° and flexion–extension error rose by 0.512°. Radial error was still 0.390° higher than with task and time alone. The design followed the earlier development finding. The four people in the second row had already been evaluated. The four final test participants remained sealed.

[Download the fitted combination and desktop launchers](UJI-Wrist-Axis-Blend-Preview.zip) · [Nested-training and development results](AXIS-BLEND-RESULTS.json)

## Run the released estimator

[Run the daily-activity models in the browser](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) or [download the offline browser](UJI-Daily-Wrist-Browser.zip). Compare estimated extension and radial deviation from the same input. With an invented example you can change the activity, elapsed time or muscle amplitude. A supplied JSON window uses its own task and clock. The numerical input can be inspected bin by bin. [Download an invented JSON window](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/example-window.json)

To supply your own window, start with the example JSON. Set `task_id` to the activity’s UJI ID (1–26) and `elapsed_anchor_s` to the time from the stored segment start to the EMG cutoff (at least 0.5 s). Use the archive’s original amplitude convention and set `amplitude_scale` to `kin-mus-uji-v1.0-native-amplitude`. Keep spots 1–7 in their original order.

- For RMS input, give `rms_bins` 16 chronological rows of seven nonnegative amplitudes. Each row describes a 31.25 ms interval.
- For raw input, replace `rms_bins` with `clock_ms_from_anchor` and `emg`. Use increasing integer milliseconds from −499 through 0 and one seven-amplitude row per timestamp. Each 31.25 ms bin needs at least 25 samples, with no gap over 5 ms between successive samples.

[Download the fitted forearm model](UJI-Wrist-Supported-Forearm-Model.zip). Extract the ZIP and use the launcher for your system. The example supplies invented inputs to the real fitted models. To try your own compatible file, use the same seven electrode channels, numerical convention, activity coding and timing as the source. The README inside the ZIP documents the input format.

The download uses a separately specified pair of models. Each retained feature had to be active in at least seven training participants. The rule removed 22 time predictors that were active in the primary study and retained all 112 EMG predictors. The more common features gave nearly the same result on the same four people: **36.165°** for task and time, and **34.700°** with EMG. Compared with its own time-shifted EMG, the released model gained **0.678°** from accurate alignment. The primary comparison above gained **0.667°**. Both are two-axis RMSE differences on the same four people.

[Download the study source and synthetic example](UJI-Wrist-Study-Source.zip) · [Aggregate development results](DEVELOPMENT-AGGREGATE.json) · [Figure source](plot_forearm_effect.py). The [earlier wrist-pointing experiment](../wrist-forearm-transfer/) used a different cohort, different electrodes and earlier wrist angles. This UJI comparison was fitted independently.

The [browser build source](browser-source/) recreates the fitted JavaScript assets using standard Python. From the study directory, run `python browser-source/build_engine.py UJI-Wrist-Supported-Forearm-Model.zip`. Extract `AXIS-BLEND.json` from the axis-blend ZIP, then run `python browser-source/build_axis_blend.py /path/to/AXIS-BLEND.json`. Both builders check their input fingerprints before writing the runtime. The companion serves the second output, `uji-axis-blend.js`, as `axis-blend.js`.
