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

## Run the released estimator

[Download the fitted forearm model](UJI-Wrist-Supported-Forearm-Model.zip). Extract the ZIP and use the launcher for your system. The example supplies invented inputs to the real fitted models. To try your own compatible file, use the same seven electrode channels, numerical convention, activity coding and timing as the source. The README inside the ZIP documents the input format.

The download uses a separately specified pair of models. Each retained feature had to be active in at least seven training participants. The rule removed 22 time predictors that were active in the primary study and retained all 112 EMG predictors. The more common features gave nearly the same result on the same four people: **36.165°** for task and time, and **34.700°** with EMG. Compared with its own time-shifted EMG, the released model gained **0.678°** from accurate alignment. The primary comparison above gained **0.667°**. Both are two-axis RMSE differences on the same four people.

[Download the study source and synthetic example](UJI-Wrist-Study-Source.zip) · [Aggregate development results](DEVELOPMENT-AGGREGATE.json) · [Figure source](plot_forearm_effect.py). The [earlier wrist-pointing experiment](../wrist-forearm-transfer/) used a different cohort, different electrodes and earlier wrist angles. This UJI comparison was fitted independently.
